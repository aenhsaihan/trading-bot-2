# Testing Agent 2: AI Message Summarization

## Prerequisites

1. **Ensure you're on the feature branch:**
   ```bash
   git checkout feature/ai-message-summarization
   ```

2. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

3. **Ensure AI service is configured** (optional but recommended):
   - Set `GROQ_API_KEY` in `.env` file (free tier available)
   - Or set `OPENAI_API_KEY` (paid)
   - If neither is set, fallback summarization will be used

## Step 1: Start the Backend

```bash
cd /Users/anar_enhsaihan/Documents/playground/composer/trading-bot-2
python backend/run.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Step 2: Test Creating Notifications

### Test 1: Critical Priority Notification

```bash
curl -X POST "http://localhost:8000/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "combined_signal",
    "priority": "critical",
    "title": "BTC/USDT Breaking Resistance",
    "message": "BTC/USDT has broken above resistance at $45,000 with 85% confidence, volume increased 200%, RSI at 72, strong buy signal detected across multiple timeframes",
    "source": "combined",
    "symbol": "BTC/USDT",
    "confidence_score": 85.0,
    "urgency_score": 90.0,
    "promise_score": 88.0
  }' | jq
```

**Expected Result:**
- Response should include `"summarized_message"` field
- Message should be **10-15 words** (critical priority)
- Tone should be **stern, professional, calming**
- Should mention key points: BTC, resistance, confidence, action

**Example good summary:**
```
"BTC breaking resistance. High confidence. Volume surge detected."
```

### Test 2: High Priority Notification

```bash
curl -X POST "http://localhost:8000/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "technical_breakout",
    "priority": "high",
    "title": "ETH/USDT Technical Breakout",
    "message": "ETH/USDT showing strong technical breakout pattern with 75% confidence, moving average crossover confirmed, volume increasing steadily",
    "source": "technical",
    "symbol": "ETH/USDT",
    "confidence_score": 75.0,
    "urgency_score": 80.0,
    "promise_score": 70.0
  }' | jq
```

**Expected Result:**
- `summarized_message` should be **15-20 words** (high priority)
- Should be concise and actionable

### Test 3: Medium Priority Notification

```bash
curl -X POST "http://localhost:8000/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "social_surge",
    "priority": "medium",
    "title": "Social Sentiment Shift",
    "message": "Social media sentiment for SOL/USDT has shifted positive with 60% confidence, increased mentions on Twitter and Reddit, community engagement rising",
    "source": "twitter",
    "symbol": "SOL/USDT",
    "confidence_score": 60.0,
    "urgency_score": 50.0,
    "promise_score": 55.0
  }' | jq
```

**Expected Result:**
- `summarized_message` should be **20-25 words** (medium priority)

### Test 4: Risk Alert (Critical)

```bash
curl -X POST "http://localhost:8000/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "risk_alert",
    "priority": "critical",
    "title": "Position Under Attack",
    "message": "Long position in BTC/USDT is approaching stop loss level. Current price is $44,500, stop loss set at $44,000. Only 1.1% remaining before stop loss triggers. Immediate action required to adjust position or accept loss.",
    "source": "system",
    "symbol": "BTC/USDT",
    "confidence_score": 95.0,
    "urgency_score": 100.0,
    "promise_score": 0.0
  }' | jq
```

**Expected Result:**
- Should be **urgent but controlled** (not panicked)
- Should mention: position, stop loss, action required
- **10-15 words**

**Example good summary:**
```
"Position under attack. Stop loss 1.1% away. Immediate action required."
```

## Step 3: Verify Summarized Messages

### Get All Notifications

```bash
curl "http://localhost:8000/notifications" | jq '.notifications[] | {id, title, priority, summarized_message}'
```

**Check:**
- ✅ All notifications have `summarized_message` field
- ✅ Message length matches priority (critical: 10-15, high: 15-20, etc.)
- ✅ Tone is stern, professional, calming
- ✅ Messages are actionable

### Get Specific Notification

```bash
# Replace {notification_id} with actual ID from previous response
curl "http://localhost:8000/notifications/{notification_id}" | jq
```

## Step 4: Test Fallback Behavior

### Test Without AI Service

1. **Temporarily disable AI service** (or don't set API keys)
2. **Create a notification:**
   ```bash
   curl -X POST "http://localhost:8000/notifications" \
     -H "Content-Type: application/json" \
     -d '{
       "type": "system_status",
       "priority": "info",
       "title": "System Status Update",
       "message": "All systems operational. Monitoring active positions. No immediate threats detected.",
       "source": "system"
     }' | jq
   ```

**Expected Result:**
- Should still have `summarized_message` field
- Should use fallback summarization (simple truncation)
- Should use title or truncated message

## Step 5: Test via API Docs (Interactive)

1. **Open browser:** http://localhost:8000/docs
2. **Navigate to:** `POST /notifications`
3. **Click "Try it out"**
4. **Fill in request body:**
   ```json
   {
     "type": "combined_signal",
     "priority": "critical",
     "title": "Test from API Docs",
     "message": "This is a detailed test message with lots of information that should be summarized into a concise StarCraft-style alert",
     "source": "system",
     "symbol": "BTC/USDT",
     "confidence_score": 85.0
   }
   ```
5. **Click "Execute"**
6. **Check response** for `summarized_message` field

## Step 6: Check Logs

Watch the backend terminal for:
- `[NotificationMessageService] Generated summary for notification...`
- `[NotificationService] Error generating summary:` (if AI fails)
- AI service initialization messages

## What to Look For

### ✅ Success Criteria

1. **All notifications have `summarized_message`:**
   - Field exists in response
   - Not null (unless AI service unavailable)

2. **Message length matches priority:**
   - Critical: 10-15 words
   - High: 15-20 words
   - Medium: 20-25 words
   - Low/Info: 20-30 words

3. **Tone is correct:**
   - Stern but professional
   - Calming (not panicked)
   - Direct and actionable
   - Like military commander reporting to general

4. **Content is relevant:**
   - Mentions key information (symbol, action, urgency)
   - Actionable (suggests what to do)
   - Concise (no fluff)

5. **Caching works:**
   - Creating same notification twice should use cache
   - Check logs for "Using cached summary"

### ❌ Common Issues

1. **`summarized_message` is null:**
   - Check if AI service is enabled
   - Check backend logs for errors
   - Fallback should still provide a message

2. **Message too long/short:**
   - Check priority is set correctly
   - AI might not always follow word count exactly (acceptable)

3. **Tone not right:**
   - Check AI service prompt
   - May need to adjust prompt in `notification_message_service.py`

4. **No summarization happening:**
   - Check `NotificationService.create_notification()` is calling `message_service.summarize()`
   - Check for import errors

## Advanced Testing

### Test Caching

Create the same notification twice (same data):
```bash
# First call - should call AI
curl -X POST "http://localhost:8000/notifications" \
  -H "Content-Type: application/json" \
  -d '{...}' | jq

# Second call - should use cache
curl -X POST "http://localhost:8000/notifications" \
  -H "Content-Type: application/json" \
  -d '{...}' | jq
```

Check logs for "Using cached summary" on second call.

### Test Different Notification Types

Try all notification types:
- `combined_signal`
- `technical_breakout`
- `social_surge`
- `news_event`
- `risk_alert`
- `system_status`
- `trade_executed`
- `user_action_required`

All should get summarization.

## Next Steps

Once testing is complete:
1. ✅ Verify all notifications have `summarized_message`
2. ✅ Verify message length matches priority
3. ✅ Verify tone is correct
4. ✅ Test fallback behavior
5. ✅ Check caching works

If everything looks good, you can merge the branch!

