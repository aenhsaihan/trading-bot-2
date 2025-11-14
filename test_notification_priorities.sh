#!/bin/bash

# Test notification priorities with curl commands
# Base URL (adjust if your backend runs on a different port)
BASE_URL="http://localhost:8000/notifications"

echo "Testing notification priorities..."
echo ""

# CRITICAL - No cooldown (shows immediately)
echo "🚨 CRITICAL Priority (0ms cooldown - shows immediately):"
curl -X POST "${BASE_URL}/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "risk_alert",
    "priority": "critical",
    "title": "🚨 CRITICAL: Market Crash Detected",
    "message": "Extreme volatility detected. BTC/USDT dropped 15% in 5 minutes. Immediate action required to protect capital.",
    "source": "technical",
    "symbol": "BTC/USDT",
    "confidence_score": 95.0,
    "urgency_score": 100.0,
    "promise_score": 0.0,
    "metadata": {
      "price_change": -15.0,
      "timeframe": "5m"
    },
    "actions": ["set_stop_loss", "close_position", "ignore"]
  }'
echo -e "\n\n"

# HIGH - 3 second cooldown
echo "⚠️ HIGH Priority (3 second cooldown):"
curl -X POST "${BASE_URL}/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "combined_signal",
    "priority": "high",
    "title": "⚠️ HIGH: Strong Buy Signal",
    "message": "Technical breakout confirmed with high volume. RSI oversold reversal and social sentiment surge detected. High confidence opportunity.",
    "source": "combined",
    "symbol": "ETH/USDT",
    "confidence_score": 85.0,
    "urgency_score": 75.0,
    "promise_score": 80.0,
    "metadata": {
      "rsi": 25.0,
      "volume_surge": 250.0
    },
    "actions": ["approve", "reject", "custom"]
  }'
echo -e "\n\n"

# MEDIUM - 5 second cooldown
echo "📊 MEDIUM Priority (5 second cooldown):"
curl -X POST "${BASE_URL}/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "technical_breakout",
    "priority": "medium",
    "title": "📊 MEDIUM: Support Level Test",
    "message": "Price approaching key support level. Moderate confidence in potential bounce. Monitor closely.",
    "source": "technical",
    "symbol": "SOL/USDT",
    "confidence_score": 65.0,
    "urgency_score": 50.0,
    "promise_score": 60.0,
    "metadata": {
      "support_level": 95.50,
      "current_price": 96.20
    },
    "actions": ["approve", "reject"]
  }'
echo -e "\n\n"

# LOW - 8 second cooldown
echo "📈 LOW Priority (8 second cooldown):"
curl -X POST "${BASE_URL}/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "social_surge",
    "priority": "low",
    "title": "📈 LOW: Minor Sentiment Shift",
    "message": "Small increase in social media mentions detected. Low confidence signal. Informational only.",
    "source": "twitter",
    "symbol": "DOGE/USDT",
    "confidence_score": 40.0,
    "urgency_score": 30.0,
    "promise_score": 35.0,
    "metadata": {
      "mention_count": 150,
      "sentiment": "slightly_positive"
    },
    "actions": []
  }'
echo -e "\n\n"

# INFO - 10 second cooldown
echo "ℹ️ INFO Priority (10 second cooldown):"
curl -X POST "${BASE_URL}/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "system_status",
    "priority": "info",
    "title": "ℹ️ INFO: System Status Update",
    "message": "All monitoring systems operational. Tracking 12 trading pairs across 5 data sources. No urgent actions needed.",
    "source": "system",
    "symbol": null,
    "confidence_score": null,
    "urgency_score": null,
    "promise_score": null,
    "metadata": {
      "pairs_monitored": 12,
      "sources_active": 5,
      "status": "healthy"
    },
    "actions": []
  }'
echo -e "\n\n"

echo "✅ All test notifications sent!"
echo ""
echo "Expected behavior:"
echo "  - CRITICAL: Shows immediately (no cooldown)"
echo "  - HIGH: Waits 3 seconds after previous notification"
echo "  - MEDIUM: Waits 5 seconds after previous notification"
echo "  - LOW: Waits 8 seconds after previous notification"
echo "  - INFO: Waits 10 seconds after previous notification"
echo ""
echo "Note: Critical notifications can interrupt non-critical toasts!"

