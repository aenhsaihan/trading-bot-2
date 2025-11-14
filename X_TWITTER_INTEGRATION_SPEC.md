# X (Twitter) Integration Spec: Social Notification Ingestion

## 🎯 Vision

Integrate X (Twitter) as a **primary notification source** for the trading bot, allowing users to:
- Connect their X account (new or existing)
- Automatically receive notifications from accounts they follow
- Get AI-summarized, voice-delivered alerts from trusted sources
- Delegate account following to X (user manages who to follow on X)

---

## 📋 Phased Approach

### Phase 1: MVP - Basic X Integration (Start Here) ⭐

**Goal:** Get X notifications flowing into the system with minimal complexity.

**Scope:**
1. **OAuth Authentication** - Connect user's X account
2. **Account Following Monitor** - Monitor accounts the user follows on X
3. **Tweet Ingestion** - Pull tweets from followed accounts
4. **Notification Generation** - Convert tweets to notifications
5. **AI Summarization** - Use existing AI service to summarize tweets
6. **Voice Delivery** - Use existing voice system to deliver alerts

**User Flow:**
1. User clicks "Connect X Account" in settings
2. OAuth flow → User authorizes app
3. System fetches list of accounts user follows
4. System starts monitoring those accounts for new tweets
5. New tweets → AI analysis → Notification → Voice alert

**Technical Approach:**
- **Start Simple:** New X account, follow accounts manually on X
- **No Filtering Yet:** All tweets from followed accounts become notifications
- **Delegation:** User manages who to follow directly on X (we just monitor)

---

### Phase 2: Smart Filtering & Prioritization

**Goal:** Make notifications more relevant and actionable.

**Features:**
- Keyword filtering (BTC, ETH, trading signals, etc.)
- Sentiment analysis (positive/negative/neutral)
- Priority scoring (high-value accounts = higher priority)
- Duplicate detection (same news from multiple accounts)
- Rate limiting (don't spam user with too many notifications)

---

### Phase 3: Advanced Features

**Goal:** Full-featured social intelligence.

**Features:**
- Custom account lists (separate from X follows)
- Keyword-based monitoring (even if not following)
- Influencer tracking (specific high-value accounts)
- Thread detection (long-form analysis)
- Media analysis (charts, images in tweets)
- Reply monitoring (conversations, not just tweets)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    X INTEGRATION LAYER                       │
│                                                              │
│  [OAuth] → [X API Client] → [Tweet Monitor] → [Processor]    │
│     ↓              ↓              ↓              ↓           │
│  Auth Flow    Fetch Tweets   Real-time      AI Analysis     │
│               Followed Accts  Streaming      Summarization   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              EXISTING NOTIFICATION SYSTEM                    │
│                                                              │
│  [NotificationService] → [AI Summarization] → [Voice TTS]   │
│         ↓                        ↓                ↓          │
│   Create Notif            StarCraft-style      ElevenLabs   │
│   (source: TWITTER)       Messages            / Azure       │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Phase 1: MVP Implementation

### 1.1 OAuth Authentication

**Owner:** Agent 9 (or Agent 1 if available)  
**Branch:** `feature/x-oauth-integration`  
**Status:** ⬜ NOT STARTED

**Tasks:**
- Set up X Developer Account & App
- Implement OAuth 2.0 flow (Authorization Code with PKCE)
- Store OAuth tokens securely (encrypted in database or env)
- Token refresh mechanism
- Frontend: "Connect X Account" button in settings
- Backend: OAuth callback endpoint

**Files:**
- `backend/services/x_auth_service.py` - NEW (OAuth handling)
- `backend/api/routes/x_auth.py` - NEW (OAuth endpoints)
- `frontend/src/components/XAuthSettings.tsx` - NEW (connect/disconnect UI)
- `frontend/src/services/xApi.ts` - NEW (X API client)

**Dependencies:** None (independent)

**X API Requirements:**
- X Developer Account (free tier available)
- App with OAuth 2.0 enabled
- Read permissions (read tweets, read user follows)
- API keys: `X_API_KEY`, `X_API_SECRET`, `X_BEARER_TOKEN`

**Testing:**
- OAuth flow works end-to-end
- Token storage is secure
- Token refresh works automatically
- User can disconnect and reconnect

**Estimated Time:** 4-6 hours

---

### 1.2 X API Client & Tweet Monitoring

**Owner:** Agent 9 (or Agent 1 if available)  
**Branch:** `feature/x-tweet-monitoring`  
**Status:** ⬜ NOT STARTED

**Tasks:**
- Create X API client (using `tweepy` or `twitter-api-v2` Python library)
- Fetch list of accounts user follows
- Monitor followed accounts for new tweets (polling or streaming)
- Parse tweet data (text, author, timestamp, engagement metrics)
- Handle rate limits gracefully
- Store tweet metadata (avoid duplicates)

**Files:**
- `backend/services/x_api_client.py` - NEW (X API wrapper)
- `backend/services/x_monitor_service.py` - NEW (background monitoring)
- `backend/models/x_account.py` - NEW (data models)
- `backend/database/x_tweets.py` - NEW (optional, for deduplication)

**Dependencies:** Requires 1.1 (OAuth) to be completed first

**Implementation Details:**

**Option A: Polling (Simpler, Start Here)**
- Poll every 5-10 minutes for new tweets
- Track last tweet ID per account
- Only process new tweets since last check
- Pros: Simple, reliable, respects rate limits
- Cons: Not real-time (5-10 min delay)

**Option B: Streaming (More Complex)**
- Use X Streaming API (requires higher tier)
- Real-time tweet delivery
- Pros: Real-time, instant notifications
- Cons: More complex, requires paid tier, connection management

**Recommendation:** Start with **Polling (Option A)** for MVP.

**Testing:**
- Fetches followed accounts correctly
- Detects new tweets
- Handles rate limits
- Avoids duplicate processing
- Works with multiple followed accounts

**Estimated Time:** 6-8 hours

---

### 1.3 Tweet → Notification Conversion

**Owner:** Agent 9 (or Agent 1 if available)  
**Branch:** `feature/x-notification-conversion`  
**Status:** ⬜ NOT STARTED

**Tasks:**
- Convert tweets to notification format
- Extract relevant information (symbols, keywords, sentiment hints)
- Determine notification priority (based on account, engagement, keywords)
- Generate notification title and message
- Use existing `NotificationService` to create notifications
- Set `source=NotificationSource.TWITTER`

**Files:**
- `backend/services/x_notification_converter.py` - NEW (tweet → notification)
- `backend/services/notification_service.py` - MODIFY (ensure TWITTER source works)

**Dependencies:** 
- Requires 1.2 (Tweet Monitoring)
- Uses existing `NotificationService` (read-only, just call it)

**Notification Mapping:**

```python
Tweet → Notification:
- tweet.text → notification.message (full tweet)
- tweet.author.username → notification.metadata['author']
- tweet.created_at → notification.created_at
- tweet.engagement_metrics → notification.metadata['engagement']
- Extract symbols (BTC, ETH, etc.) → notification.symbol
- Determine priority → notification.priority (MEDIUM by default, HIGH for high-value accounts)
- source → NotificationSource.TWITTER
```

**Priority Logic (MVP):**
- Default: `MEDIUM`
- High-value accounts (configurable list): `HIGH`
- Accounts with high engagement: `HIGH`
- Later: Use AI to determine priority

**Testing:**
- Tweets convert to notifications correctly
- Notifications appear in UI
- Voice alerts work (uses existing system)
- AI summarization works (uses existing system)

**Estimated Time:** 3-4 hours

---

### 1.4 Frontend Integration

**Owner:** Agent 9 (or Agent 1 if available)  
**Branch:** `feature/x-frontend-integration`  
**Status:** ⬜ NOT STARTED

**Tasks:**
- Add "Connect X Account" button in settings
- Show connection status (connected/disconnected)
- Display X account username when connected
- Show list of followed accounts being monitored
- Display X-sourced notifications with X icon/badge
- Handle OAuth callback in frontend

**Files:**
- `frontend/src/components/XAuthSettings.tsx` - NEW (settings UI)
- `frontend/src/components/Settings.tsx` - MODIFY (add X section)
- `frontend/src/services/xApi.ts` - NEW (X API client)
- `frontend/src/types/x.ts` - NEW (TypeScript types)

**Dependencies:** Requires 1.1 (OAuth) to be completed first

**Testing:**
- OAuth flow works in browser
- Connection status displays correctly
- Followed accounts list shows
- X notifications display with X badge

**Estimated Time:** 3-4 hours

---

## 🔄 Integration with Existing System

### Notification Flow

```
X Tweet
  ↓
x_notification_converter.py (extract data, determine priority)
  ↓
NotificationService.create_notification(source=TWITTER)
  ↓
AI Summarization (existing NotificationMessageService)
  ↓
Voice TTS (existing VoiceService)
  ↓
Frontend Display (existing ToastContainer)
```

### Key Integration Points

1. **NotificationSource.TWITTER** - Already exists in `notification_types.py`
2. **NotificationService** - Already handles all sources, just call it
3. **AI Summarization** - Already works for all notifications (Agent 2)
4. **Voice TTS** - Already works for all notifications (Agent 3)
5. **Frontend** - Already displays all notification sources

**No changes needed to existing notification system!** Just create notifications with `source=TWITTER`.

---

## 🧪 Testing Strategy

### Phase 1 Testing

1. **OAuth Flow:**
   - [ ] Connect new X account
   - [ ] Connect existing X account
   - [ ] Disconnect and reconnect
   - [ ] Token refresh works

2. **Tweet Monitoring:**
   - [ ] Fetches followed accounts
   - [ ] Detects new tweets
   - [ ] Handles rate limits
   - [ ] Avoids duplicates

3. **Notification Generation:**
   - [ ] Tweets become notifications
   - [ ] Notifications appear in UI
   - [ ] AI summarization works
   - [ ] Voice alerts work
   - [ ] X badge/icon shows

4. **Edge Cases:**
   - [ ] No followed accounts
   - [ ] Rate limit exceeded
   - [ ] OAuth token expired
   - [ ] Network errors
   - [ ] Very long tweets

---

## 📊 Success Criteria

### Phase 1 MVP

- [ ] User can connect X account via OAuth
- [ ] System monitors accounts user follows
- [ ] New tweets become notifications
- [ ] Notifications get AI-summarized messages
- [ ] Voice alerts deliver X notifications
- [ ] User can see which accounts are being monitored
- [ ] System handles rate limits gracefully

---

## 🚀 Recommended Execution Order

### Week 1: Foundation

1. **Agent 9.1: OAuth Integration** (4-6 hours)
   - Set up X Developer Account
   - Implement OAuth flow
   - Frontend connect button

2. **Agent 9.2: X API Client** (6-8 hours)
   - Create API client
   - Fetch followed accounts
   - Implement polling mechanism

### Week 2: Integration

3. **Agent 9.3: Notification Conversion** (3-4 hours)
   - Convert tweets to notifications
   - Integrate with NotificationService

4. **Agent 9.4: Frontend Polish** (3-4 hours)
   - Settings UI
   - Connection status
   - Followed accounts display

**Total MVP Time:** ~16-22 hours

---

## 🔐 Security & Privacy

- **OAuth Tokens:** Store encrypted, never log
- **Rate Limits:** Respect X API rate limits (don't spam)
- **User Privacy:** Only access what user authorizes (read tweets, read follows)
- **Data Storage:** Store minimal data (tweet IDs for deduplication, not full tweets)
- **Token Refresh:** Automatic refresh before expiration

---

## 📝 API Keys & Setup

### X Developer Account Setup

1. **Create X Developer Account:**
   - Go to https://developer.twitter.com/
   - Apply for developer access (free tier available)
   - Create a new App

2. **Get API Keys:**
   - API Key (`X_API_KEY`)
   - API Secret (`X_API_SECRET`)
   - Bearer Token (`X_BEARER_TOKEN`)

3. **Configure OAuth:**
   - Enable OAuth 2.0
   - Set callback URL: `http://localhost:8000/api/x/callback` (dev)
   - Request permissions: `tweet.read`, `users.read`, `follows.read`

4. **Add to `.env`:**
   ```env
   X_API_KEY=your_api_key
   X_API_SECRET=your_api_secret
   X_BEARER_TOKEN=your_bearer_token
   X_CALLBACK_URL=http://localhost:8000/api/x/callback
   ```

---

## 🎯 Next Steps After MVP

### Phase 2: Smart Filtering
- Keyword filtering
- Sentiment analysis
- Priority scoring
- Duplicate detection

### Phase 3: Advanced Features
- Custom account lists
- Keyword-based monitoring
- Influencer tracking
- Thread detection

---

## ✅ Decisions Made

1. **Start Simple:** New X account, follow accounts manually on X
2. **Delegation:** User manages who to follow on X (we just monitor)
3. **No Filtering Yet:** All tweets from followed accounts become notifications (MVP)
4. **Polling First:** Use polling (5-10 min) instead of streaming (simpler, more reliable)
5. **Integration:** Use existing notification system (no changes needed)

---

## 🚀 Ready to Start!

**First Steps:**
1. Set up X Developer Account
2. Create feature branch: `feature/x-oauth-integration`
3. Implement OAuth flow
4. Test with real X account
5. Iterate based on feedback

**Let's get X notifications flowing!** 🐦

