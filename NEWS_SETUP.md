# News Integration Setup Guide

## Overview

News monitoring integration using CryptoCompare News API. Automatically fetches crypto news articles and converts them to notifications.

## Features

- ✅ **Polling-based monitoring** - Fetches latest news every 5 minutes
- ✅ **Automatic notification creation** - Converts articles to notifications
- ✅ **Symbol detection** - Extracts crypto symbols from articles
- ✅ **Priority determination** - Determines notification priority based on content
- ✅ **Auto-start** - Starts automatically on server startup
- ✅ **Category filtering** - Can filter by specific categories (optional)

## Setup

### 1. Get CryptoCompare API Key (Optional but Recommended)

1. Go to [CryptoCompare API Keys](https://www.cryptocompare.com/cryptopian/api-keys)
2. Create a new API key (free tier available)
3. Copy your API key

### 2. Configure Environment Variables

Add to your `.env` file:

```env
# CryptoCompare API Key (optional, but recommended for higher rate limits)
CRYPTOCOMPARE_API_KEY=your_api_key_here

# Enable/disable news monitoring (default: true)
ENABLE_NEWS_MONITORING=true

# Categories to monitor (optional, comma-separated)
# Leave empty to monitor all categories
# Examples: BTC,ETH,SOL,General,Regulation
NEWS_CATEGORIES=

# Language preference (default: EN)
NEWS_LANG=EN
```

### 3. Restart Backend

```bash
python backend/run.py
```

News monitoring will start automatically!

## API Endpoints

### Get Status
```bash
curl http://localhost:8000/news/status | python3 -m json.tool
```

### Start Monitoring
```bash
curl -X POST http://localhost:8000/news/start
```

### Stop Monitoring
```bash
curl -X POST http://localhost:8000/news/stop
```

## How It Works

1. **Polling**: Fetches latest news from CryptoCompare every 5 minutes
2. **Deduplication**: Tracks last 100 article IDs to avoid duplicates
3. **Conversion**: Converts articles to notifications with:
   - Symbol detection (BTC, ETH, etc.)
   - Priority determination (high/medium based on keywords)
   - Confidence/urgency/promise scores
   - AI summarization (StarCraft-style)
4. **Notification Creation**: Creates notifications in your notification system

## Notification Features

- **Symbol Detection**: Automatically detects crypto symbols in articles
- **Priority Levels**:
  - **HIGH**: Security breaches, regulations, major announcements, listings
  - **MEDIUM**: Updates, features, partnerships, general news
- **Scores**:
  - Confidence: 70% (news is generally reliable)
  - Urgency: 40-80% (based on keywords)
  - Promise: 30-70% (based on positive/negative keywords)

## Categories

You can monitor specific categories by setting `NEWS_CATEGORIES`:

- `BTC` - Bitcoin news
- `ETH` - Ethereum news
- `SOL` - Solana news
- `General` - General crypto news
- `Regulation` - Regulatory news
- `Security` - Security-related news
- And more...

Leave empty to monitor all categories.

## Rate Limits

- **Free tier**: 100,000 calls/month
- **With API key**: Higher rate limits
- Default poll interval: 5 minutes (12 calls/hour)

## Troubleshooting

### "News monitoring not starting"
- Check `ENABLE_NEWS_MONITORING=true` in `.env`
- Check server logs for errors
- Verify API key is valid (if using one)

### "No notifications appearing"
- Check if monitoring is running: `curl http://localhost:8000/news/status`
- Check server logs for API errors
- Verify CryptoCompare API is accessible

### "Rate limit errors"
- Add API key to `.env` for higher limits
- Increase poll interval in code (default: 300 seconds)

## Next Steps

1. Monitor news notifications in your frontend
2. Adjust categories based on your interests
3. Customize priority keywords in `news_notification_converter.py`
4. Add more symbols to detection list if needed

