# Spotify Downloader Web - Deployment Guide

## MongoDB Setup
- **Database Name**: spotify_downloader
- **Connection String Format**: 
```
mongodb+srv://USERNAME:PASSWORD@cluster0.2t38ibi.mongodb.net/spotify_downloader?retryWrites=true&w=majority
```
- **Cluster**: cluster0.2t38ibi.mongodb.net
- **Required Python Package**: `pymongo[srv]`

## Environment Variables Required
1. **MONGO_URI**: The complete MongoDB connection string

## Render Deployment Settings
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn web_app:app`
- **Environment**: Python
- **Plan**: Free

## Local Development Setup
1. Install MongoDB driver:
```bash
python -m pip install "pymongo[srv]"
```

2. Set up environment variables in a `.env` file:
```
MONGO_URI=mongodb+srv://USERNAME:PASSWORD@cluster0.2t38ibi.mongodb.net/spotify_downloader?retryWrites=true&w=majority
```

## Important Notes
- Keep your MongoDB password secure and never commit it to version control
- The web application is configured to let users provide their own Spotify API credentials
- MongoDB connection uses SRV protocol for enhanced security
- Database operations are handled asynchronously through a worker queue system

## Features
- User-provided Spotify credentials
- Secure credential storage in browser localStorage
- Multi-threaded download queue
- Progress tracking
- MongoDB-based download history
- High-quality audio downloads (320kbps MP3)
- Album artwork embedding 