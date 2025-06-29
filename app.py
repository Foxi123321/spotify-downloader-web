import os
import logging
import tempfile
from urllib.parse import quote
import time
import json
from flask import Flask, request, jsonify, send_file, render_template, Response, stream_with_context
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from mutagen.easyid3 import EasyID3
import shutil
import gc
import uuid
from threading import Thread

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Store download status
downloads = {}

# Initialize Spotify client
try:
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials())
except Exception as e:
    logger.error(f"Failed to initialize Spotify client: {str(e)}")
    sp = None

def get_yt_dlp_opts(is_search=False):
    # Common options for both search and download
    common_opts = {
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://www.youtube.com',
            'Referer': 'https://www.youtube.com/',
        },
        'socket_timeout': 30,
        'retries': 10,
        'file_access_retries': 10,
        'fragment_retries': 10,
        'retry_sleep_functions': {
            '403': lambda _: 10,
            '429': lambda _: 10,
            'generic': lambda _: 5
        },
        'extractor_retries': 10,
        'sleep_interval': 1,
        'max_sleep_interval': 5,
        'sleep_interval_requests': 1,
        'socket_timeout': 30,
        'extract_timeout': 30,
        'buffersize': 1024,
        'http_chunk_size': 10485760,  # 10MB chunks
    }

    if is_search:
        return {
            **common_opts,
            'extract_flat': True,
            'skip_download': True,
            'default_search': 'ytsearch1:',
            'format': 'best',
            'no_playlist': True,
            'playlist_items': '1',
        }
    else:
        return {
            **common_opts,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'youtube_include_dash_manifest': False,
            'youtube_include_hls_manifest': False,
            'extract_flat': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'no_playlist': True,
            'playlist_items': '1',
            'max_filesize': 100000000,  # ~100MB limit
            'max_downloads': 1,
        }

def find_youtube_url(track_name, artist_name):
    search_query = f"{track_name} {artist_name} official audio"
    logger.info(f"Searching for: {search_query}")
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            with yt_dlp.YoutubeDL(get_yt_dlp_opts(is_search=True)) as ydl:
                result = ydl.extract_info(f"ytsearch:{search_query}", download=False)
                
                if result and 'entries' in result and result['entries']:
                    video = result['entries'][0]
                    if video:
                        video_url = f"https://www.youtube.com/watch?v={video['id']}"
                        logger.info(f"Found YouTube URL: {video_url}")
                        return video_url
                        
                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"Search attempt {retry_count} failed, retrying...")
                    time.sleep(2)
                    
        except Exception as e:
            logger.error(f"Error searching YouTube (attempt {retry_count + 1}): {str(e)}")
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(2)
            else:
                logger.error("Max retries reached for YouTube search")
                break
    
    return None

def process_download(download_id, track_info, youtube_url):
    try:
        downloads[download_id]['status'] = 'downloading'
        
        temp_dir = tempfile.mkdtemp(dir='/dev/shm' if os.path.exists('/dev/shm') else None)
        downloads[download_id]['temp_dir'] = temp_dir
        
        ydl_opts = get_yt_dlp_opts(is_search=False)
        ydl_opts['outtmpl'] = os.path.join(temp_dir, '%(title)s.%(ext)s')
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            audio_file = os.path.join(temp_dir, f"{info['title']}.mp3")
            
            if not os.path.exists(audio_file):
                raise Exception("Audio file not found after download")
            
            # Set the filename to include track and artist name
            safe_filename = f"{track_info['name']} - {track_info['artists'][0]['name']}.mp3".replace('/', '_').replace('\\', '_')
            final_path = os.path.join(temp_dir, safe_filename)
            
            # Rename the file
            os.rename(audio_file, final_path)
            
            try:
                # Try to add ID3 tags
                audio = EasyID3(final_path)
                audio['title'] = track_info['name']
                audio['artist'] = track_info['artists'][0]['name']
                audio.save()
            except Exception as e:
                logger.warning(f"Could not add ID3 tags: {str(e)}")
            
            downloads[download_id].update({
                'status': 'completed',
                'file_path': final_path,
                'filename': safe_filename
            })
            
    except Exception as e:
        logger.error(f"Error processing download: {str(e)}")
        downloads[download_id].update({
            'status': 'error',
            'error': str(e)
        })
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up temp directory: {str(cleanup_error)}")

@app.route('/')
def index():
    if not sp:
        return render_template('index.html', error="Spotify API credentials not configured. Please set up SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET environment variables.")
    return render_template('index.html')

@app.route('/start-download', methods=['POST'])
def start_download():
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
        
    try:
        data = request.get_json()
        if not data or 'trackUrl' not in data:
            return jsonify({'error': 'Missing trackUrl in request'}), 400
            
        track_url = data.get('trackUrl')
        if not track_url or 'spotify.com/track/' not in track_url:
            return jsonify({'error': 'Invalid Spotify track URL'}), 400

        # Get track information from Spotify
        try:
            track_id = track_url.split('/')[-1].split('?')[0]
            track_info = sp.track(track_id)
        except Exception as e:
            logger.error(f"Error getting track info from Spotify: {str(e)}")
            return jsonify({'error': 'Invalid Spotify track or API error'}), 400
        
        track_name = track_info['name']
        artist_name = track_info['artists'][0]['name']
        logger.info(f"Processing track: {track_name} by {artist_name}")
        
        # Find YouTube URL
        youtube_url = find_youtube_url(track_name, artist_name)
        if not youtube_url:
            return jsonify({'error': 'Could not find track on YouTube'}), 404
        
        # Generate download ID and start processing
        download_id = str(uuid.uuid4())
        downloads[download_id] = {
            'status': 'starting',
            'track_info': track_info,
            'created_at': time.time()
        }
        
        # Start download in background
        Thread(target=process_download, args=(download_id, track_info, youtube_url)).start()
        
        return jsonify({
            'download_id': download_id,
            'status': 'starting'
        })
        
    except Exception as e:
        logger.error(f"Error starting download: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download-status/<download_id>')
def download_status(download_id):
    if download_id not in downloads:
        return jsonify({'error': 'Download not found'}), 404
    
    # Clean up old downloads
    current_time = time.time()
    for did, info in list(downloads.items()):
        if current_time - info.get('created_at', 0) > 3600:  # 1 hour timeout
            if 'temp_dir' in info and os.path.exists(info['temp_dir']):
                try:
                    shutil.rmtree(info['temp_dir'])
                except Exception as e:
                    logger.error(f"Error cleaning up old download: {str(e)}")
            del downloads[did]
    
    return jsonify(downloads[download_id])

@app.route('/download-file/<download_id>')
def download_file(download_id):
    if download_id not in downloads:
        return jsonify({'error': 'Download not found'}), 404
    
    download_info = downloads[download_id]
    if download_info['status'] != 'completed':
        return jsonify({'error': 'Download not ready'}), 400
    
    try:
        return send_file(
            download_info['file_path'],
            as_attachment=True,
            download_name=download_info['filename'],
            mimetype='audio/mpeg'
        )
    except Exception as e:
        logger.error(f"Error sending file: {str(e)}")
        return jsonify({'error': 'Error sending file'}), 500
    finally:
        # Clean up after successful download
        if 'temp_dir' in download_info and os.path.exists(download_info['temp_dir']):
            try:
                shutil.rmtree(download_info['temp_dir'])
            except Exception as e:
                logger.error(f"Error cleaning up temp directory: {str(e)}")
        del downloads[download_id]

if __name__ == '__main__':
    app.run(debug=True)
