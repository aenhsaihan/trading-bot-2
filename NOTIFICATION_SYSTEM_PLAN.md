# Notification-First Trading System - Architecture Plan

## Vision Statement

Transform the trading bot into a **notification-first, autonomous collaboration system** that:
- **Always watches** - Continuously monitors technical and social indicators
- **Always listens** - Aggregates sentiment from multiple social platforms
- **Always notifies** - Proactive alerts about opportunities and risks
- **Always ready** - Collaborative decision-making with user
- **Autonomous when needed** - Acts in user's best interest when user is unavailable

---

## Core Principles

1. **Notification-First Design**: The UI prioritizes notifications and alerts
2. **Collaborative Autonomy**: System suggests actions, user approves, or system acts autonomously based on confidence
3. **Multi-Source Intelligence**: Combine technical indicators + social sentiment + news
4. **Transparent Reasoning**: Every autonomous action includes clear reasoning
5. **User Control**: User sets autonomy levels and response preferences

---

## System Architecture

### 1. Notification Hub (`src/notifications/`)

**Central notification manager that:**
- Receives signals from all sources (technical, social, news)
- Prioritizes notifications (critical, high, medium, low, info)
- Routes to appropriate channels (in-app, email, push, SMS)
- Tracks user responses and actions
- Manages notification history and filtering

**Key Components:**
- `notification_manager.py` - Central hub
- `notification_queue.py` - Priority queue for notifications
- `notification_channels.py` - Email, push, SMS, in-app
- `notification_history.py` - Store and retrieve notification history
- `notification_preferences.py` - User settings for notification types

### 2. Social Data Aggregators (`src/social/`)

**Collectors for social sentiment:**
- `twitter_aggregator.py` - Twitter/X API integration
- `telegram_aggregator.py` - Telegram channel monitoring
- `discord_aggregator.py` - Discord server monitoring
- `reddit_aggregator.py` - Reddit subreddit monitoring
- `news_aggregator.py` - Crypto news sources (CoinDesk, CoinTelegraph, etc.)
- `base_aggregator.py` - Base class for all aggregators

**Data Sources:**
- Twitter: Official API, search for crypto keywords, influencer tracking
- Telegram: Channel subscriptions, group monitoring
- Discord: Server channels, bot integration
- Reddit: r/cryptocurrency, r/bitcoin, coin-specific subreddits
- News: RSS feeds, API integrations

### 3. Sentiment Analysis Engine (`src/sentiment/`)

**NLP-powered sentiment analysis:**
- `sentiment_analyzer.py` - Main sentiment analysis engine
- `text_processor.py` - Text cleaning and preprocessing
- `sentiment_models.py` - ML models (can use pre-trained models like VADER, FinBERT)
- `sentiment_scorer.py` - Score sentiment (-1 to +1 scale)
- `keyword_extractor.py` - Extract relevant keywords and topics

**Features:**
- Real-time sentiment scoring
- Sentiment trends over time
- Sentiment by source (Twitter vs Reddit vs Telegram)
- Sentiment by coin/token
- Sentiment alerts (sudden shifts, extreme sentiment)

### 4. Opportunity Detection System (`src/opportunities/`)

**Combines signals to detect opportunities:**
- `opportunity_detector.py` - Main detection engine
- `signal_combiner.py` - Combine technical + social signals
- `opportunity_scorer.py` - Score opportunities (0-100 confidence)
- `opportunity_types.py` - Define opportunity types:
  - Technical breakout
  - Social sentiment surge
  - News-driven opportunity
  - Combined signal (technical + social alignment)
  - Risk alert (negative sentiment + technical breakdown)

**Detection Logic:**
- Technical signal + Positive sentiment = High confidence opportunity
- Technical signal + Negative sentiment = Lower confidence (wait)
- No technical signal + Extreme sentiment = Monitor closely
- Multiple sources agree = Higher confidence

### 5. Autonomous Decision Engine (`src/autonomy/`)

**Rules and reasoning for autonomous actions:**
- `autonomy_engine.py` - Main autonomous decision maker
- `decision_rules.py` - Rule-based decision logic
- `confidence_calculator.py` - Calculate confidence scores
- `action_executor.py` - Execute autonomous trades
- `reasoning_generator.py` - Generate human-readable reasoning

**Autonomy Levels:**
1. **Manual Only** - Always ask user
2. **Low Autonomy** - Act only on very high confidence (>90%) + user approval timeout
3. **Medium Autonomy** - Act on high confidence (>75%) after user notification timeout
4. **High Autonomy** - Act on medium confidence (>60%) with reasoning
5. **Full Autonomy** - Act on any opportunity above threshold

**Decision Factors:**
- Confidence score (technical + social alignment)
- Risk level (position size, stop loss)
- User's historical preferences
- Time since last user interaction
- Market volatility
- Portfolio balance

### 6. User Response System (`src/responses/`)

**Quick actions from notifications:**
- `response_handler.py` - Handle user responses
- `quick_actions.py` - Pre-defined quick actions:
  - "Approve & Execute"
  - "Approve with Custom Size"
  - "Reject"
  - "Snooze (remind in X minutes)"
  - "Ignore"
- `response_tracking.py` - Track user response patterns

**Response Channels:**
- In-app notifications (Streamlit UI)
- Email with action links
- SMS with reply codes
- Telegram bot commands
- Webhook callbacks

### 7. Notification UI (`src/monitoring/notifications/`)

**Notification-first dashboard:**
- `notification_center.py` - Main notification center UI
- `notification_card.py` - Individual notification component
- `notification_filters.py` - Filter by type, priority, source
- `notification_settings.py` - User preferences UI
- `autonomy_settings.py` - Configure autonomy levels

**UI Features:**
- Real-time notification stream
- Priority badges (🔴 Critical, 🟠 High, 🟡 Medium, 🔵 Low, ⚪ Info)
- Quick action buttons on each notification
- Notification grouping (similar opportunities)
- "Everything is OK" status indicator
- Activity timeline

---

## Data Flow

```
┌─────────────────┐
│ Technical       │
│ Indicators      │──┐
│ (RSI, MACD, MA)│  │
└─────────────────┘  │
                      │
┌─────────────────┐  │    ┌──────────────────┐
│ Social          │  │    │                  │
│ Aggregators     │──┼───▶│ Opportunity      │
│ (Twitter, etc.) │  │    │ Detector         │
└─────────────────┘  │    │                  │
                      │    └────────┬─────────┘
┌─────────────────┐  │             │
│ News            │──┘             │
│ Aggregators     │                │
└─────────────────┘                ▼
                            ┌──────────────────┐
                            │ Notification     │
                            │ Hub              │
                            └────────┬─────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │ User         │  │ Autonomous   │  │ Notification │
            │ Response     │  │ Decision     │  │ Channels     │
            │ System       │  │ Engine       │  │ (Email, etc.)│
            └──────────────┘  └──────────────┘  └──────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Create notification system architecture
- [ ] Build notification hub and queue
- [ ] Implement in-app notification UI
- [ ] Add notification history storage
- [ ] Create notification preferences system

### Phase 2: Social Integration (Week 3-4)
- [ ] Twitter/X API integration
- [ ] Telegram bot/channel monitoring
- [ ] Reddit API integration
- [ ] News aggregator (RSS feeds)
- [ ] Basic sentiment analysis (VADER or similar)

### Phase 3: Opportunity Detection (Week 5-6)
- [ ] Signal combiner (technical + social)
- [ ] Opportunity scorer
- [ ] Opportunity types and classification
- [ ] Confidence calculation
- [ ] Integration with existing strategies

### Phase 4: Autonomy Engine (Week 7-8)
- [ ] Autonomy levels and rules
- [ ] Decision reasoning generator
- [ ] Action executor with safeguards
- [ ] User approval timeout system
- [ ] Audit trail for autonomous actions

### Phase 5: User Response & Channels (Week 9-10)
- [ ] Quick action system
- [ ] Email notifications with action links
- [ ] SMS notifications (optional)
- [ ] Telegram bot for responses
- [ ] Response tracking and learning

### Phase 6: Polish & Testing (Week 11-12)
- [ ] Notification filtering and grouping
- [ ] "Everything OK" status indicator
- [ ] Performance optimization
- [ ] Comprehensive testing
- [ ] Documentation

---

## Technical Considerations

### APIs & Rate Limits
- **Twitter API**: Rate limits vary by tier (Free tier: 1,500 tweets/month)
- **Reddit API**: 60 requests/minute
- **Telegram**: Bot API has generous limits
- **News APIs**: Consider NewsAPI, CryptoCompare News API

### Sentiment Analysis Options
1. **VADER** (Valence Aware Dictionary) - Fast, rule-based, good for social media
2. **FinBERT** - Pre-trained BERT model for financial text
3. **Custom Model** - Train on crypto-specific data (future)

### Storage
- **Notifications**: SQLite or PostgreSQL for history
- **Social Data**: Time-series database (InfluxDB) or PostgreSQL
- **Sentiment Scores**: Store with timestamps for trend analysis

### Real-time Processing
- **WebSockets**: For real-time notification delivery
- **Background Workers**: Process social data asynchronously
- **Queue System**: Use Celery or similar for task processing

---

## User Experience Flow

### Scenario 1: Opportunity Detected
1. System detects: "SOL/USDT - Golden Cross + 85% positive Twitter sentiment"
2. Notification appears: "🚀 High Confidence Opportunity Detected"
3. Shows: Technical signal + Social sentiment + Confidence score
4. User options:
   - "Approve & Buy" (immediate)
   - "Approve with 2% position size" (custom)
   - "Reject" (dismiss)
   - "Remind me in 15 min" (snooze)
5. If no response in 5 minutes + high autonomy:
   - System executes with reasoning: "Executed buy: High confidence (87%) opportunity. Golden cross confirmed + strong positive sentiment across Twitter/Reddit. Position size: 1% of balance."

### Scenario 2: Risk Alert
1. System detects: "BTC/USDT - Death Cross + Negative news sentiment"
2. Notification: "⚠️ Risk Alert - Consider Reducing Position"
3. Shows: Technical breakdown + Negative news headlines + Sentiment shift
4. User options:
   - "Sell 50%" (partial exit)
   - "Set Stop Loss" (risk management)
   - "Ignore" (user knows better)
5. If no response + medium autonomy:
   - System: "Set trailing stop loss tighter due to negative sentiment shift"

### Scenario 3: Everything OK Status
- Continuous indicator: "✅ System Active - Monitoring 12 pairs, 5 social sources"
- Periodic updates: "All systems normal - No urgent actions needed"
- Reassurance that system is watching even when quiet

---

## Configuration & Settings

### User Preferences (`config/notifications.yaml`)
```yaml
notification_channels:
  in_app: true  # Primary - sexy and smart UI
  email: true
  sms: true
  telegram: true
  
notification_priorities:
  critical: [in_app, email, sms, telegram]
  high: [in_app, email, telegram]
  medium: [in_app, email]
  low: [in_app]
  info: [in_app]  # Only in notification center
  
# Dynamic autonomy based on urgency + promise scoring
autonomy_config:
  base_timeout: 300  # Base timeout in seconds
  urgency_multiplier: 0.5  # High urgency = shorter timeout
  promise_multiplier: 0.7  # High promise = shorter timeout
  min_timeout: 60  # Minimum timeout (1 minute)
  max_timeout: 1800  # Maximum timeout (30 minutes)
  
  # Autonomy thresholds (based on urgency + promise score)
  full_autonomy_threshold: 90  # Act immediately if score >= 90
  high_autonomy_threshold: 75  # Act after short timeout if >= 75
  medium_autonomy_threshold: 60  # Act after medium timeout if >= 60
  low_autonomy_threshold: 45  # Act after long timeout if >= 45
  
social_sources:
  # Primary sources
  twitter:
    enabled: true
    priority: "high"
    keywords: ["BTC", "ETH", "SOL", "crypto", "bitcoin", "altcoin"]
    influencers: ["@elonmusk", "@VitalikButerin"]
  telegram:
    enabled: true
    priority: "high"
    channels: ["@cryptosignals", "@tradingview"]
  news:
    enabled: true
    priority: "high"
    sources: ["coindesk", "cointelegraph", "decrypt", "theblock"]
  
  # Secondary sources (support)
  reddit:
    enabled: true
    priority: "medium"
    subreddits: ["r/cryptocurrency", "r/bitcoin", "r/ethereum"]
  discord:
    enabled: true
    priority: "medium"
    servers: []  # User-configurable
    
sentiment_thresholds:
  extreme_positive: 0.7
  extreme_negative: -0.7
  significant_shift: 0.3  # Change in sentiment score
  
opportunity_priorities:
  # Order of importance (highest to lowest)
  1: "combined_signal"  # Technical + Social alignment (highest confidence)
  2: "technical_breakout"  # Strong technical signal
  3: "social_surge"  # Extreme sentiment shift
  4: "news_event"  # Major news breaking
  5: "risk_alert"  # Negative signals (protect capital)
  
learning:
  track_responses: true
  learn_preferences: true
  adjust_confidence: true  # Adjust based on user approval/rejection patterns
```

---

## Success Metrics

1. **Notification Accuracy**: % of notifications that led to profitable trades
2. **Response Time**: Average time from notification to user action
3. **Autonomous Success Rate**: % of autonomous actions that were profitable
4. **User Satisfaction**: User feedback on notification relevance
5. **Coverage**: % of significant market moves detected

---

## Next Steps

1. **Review & Refine**: Discuss this plan, adjust priorities
2. **Start Phase 1**: Build notification foundation
3. **Iterate**: Build incrementally, test with real data
4. **Deploy**: Roll out features progressively

---

## Questions to Consider

1. **Which social sources are most important to you?** (Twitter, Telegram, Reddit, Discord, News?)
2. **What autonomy level are you comfortable with initially?** (Start conservative?)
3. **What notification channels do you prefer?** (In-app, email, SMS, Telegram bot?)
4. **What types of opportunities matter most?** (Breakouts, sentiment shifts, news events?)
5. **How should the system learn your preferences?** (Track your approvals/rejections?)

---

This is a comprehensive system that will transform your bot into a true trading partner. Ready to start building?

