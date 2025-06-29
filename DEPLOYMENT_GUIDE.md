# Deployment Guide for Spotify Track Downloader

This guide will help you deploy the Spotify Track Downloader web application on Render.com.

## Prerequisites

1. A Render.com account
2. A Spotify Developer account with API credentials
   - Client ID
   - Client Secret

## Deployment Steps

1. Fork or clone this repository to your GitHub account.

2. Log in to your Render.com account.

3. Click on "New +" and select "Web Service".

4. Connect your GitHub repository.

5. Configure the following settings:
   - Name: spotify-downloader (or your preferred name)
   - Environment: Python
   - Region: Choose the closest to your users
   - Branch: main
   - Build Command: Will be automatically set from render.yaml
   - Start Command: Will be automatically set from render.yaml

6. Add environment variables:
   - SPOTIPY_CLIENT_ID: Your Spotify API Client ID
   - SPOTIPY_CLIENT_SECRET: Your Spotify API Client Secret

7. Click "Create Web Service"

## Getting Spotify API Credentials

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account
3. Click "Create App"
4. Fill in the app details:
   - App name: Spotify Track Downloader (or your preferred name)
   - App description: Web application for downloading Spotify tracks
   - Website: Your Render deployment URL (can be added later)
   - Redirect URI: Not needed for this application
5. Accept the terms and create the app
6. Copy the Client ID and Client Secret

## Troubleshooting

1. If you see "Spotify API credentials not configured" error:
   - Check if you've correctly set the environment variables in Render
   - Verify your Spotify API credentials are valid

2. If downloads fail:
   - Check the application logs in Render
   - Verify your Spotify API credentials haven't expired
   - Ensure you're not hitting any rate limits

3. If the application crashes:
   - Check the Render logs for error messages
   - Verify all environment variables are set correctly
   - Make sure you're using the correct Python version (3.11.7)

## Support

If you encounter any issues, please:
1. Check the application logs in Render
2. Review this deployment guide
3. Create an issue in the GitHub repository

## Security Notes

- Never commit your Spotify API credentials to the repository
- Always use environment variables for sensitive information
- Regularly update your dependencies to get security patches

## MongoDB Setup
- **Database Name**: spotify_downloader
- **Connection String Format**: 
```mongodb+srv://USERNAME:PASSWORD@cluster0.2t38ibi.mongodb.net/spotify_downloader?retryWrites=true&w=majority
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