# Notification System V2: StarCraft-Style Tactical Command Center

## 🎯 Vision

Transform notifications into a **StarCraft-like tactical command center** where:

- **Notifications drive all decisions** - They are the primary interface, not a sidebar
- **Voice is the commander** - Calm, intelligent, competent female voice directing attention
- **Market is a battlefield** - Positions are always under threat, requiring constant vigilance
- **AI is the tactical advisor** - Summarizes complex data into concise, actionable intelligence
- **Urgency is contextual** - System knows when to alert vs. when to wait

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    NOTIFICATION PIPELINE                        │
│                                                                 │
│  [Data Sources] → [AI Analysis] → [Message Generation] → [Voice] │
│       ↓                ↓                ↓              ↓         │
│   Technical      Summarization    StarCraft-style   TTS        │
│   Indicators     & Prioritization  Messages          Engine     │
│   Social Media                                                  │
│   News Feeds                                                     │
│   Position Data                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Component Breakdown

### Phase 1: Foundation (Sequential - Must be done first)

#### 1.1 Notification Threat Detection System

**Owner:** Agent 1  
**Branch:** `feature/notification-threat-detection`  
**Status:** ⬜ NOT STARTED

**Tasks:**

- Create position monitoring service
- **Real-time monitoring** (every price update)
- Detect when positions are "under attack" (stop loss approaching, rapid price movement)
- Calculate threat levels (low/medium/high/critical)
- Generate threat notifications with urgency scores
- **Queue notifications** (like StarCraft - reports come in order, not all at once)
- Integrate with existing position tracking

**Files:**

- `backend/services/threat_detection_service.py` - NEW
- `backend/services/trading_service.py` - MODIFY (add threat monitoring)
- `backend/api/routes/trading.py` - MODIFY (add threat endpoints)

**Dependencies:** None (foundation layer)

**Testing:**

- Create test positions
- Simulate price movements
- Verify threat detection triggers correctly
- Test urgency scoring

**Estimated Time:** 4-6 hours

---

#### 1.2 AI Message Summarization Service

**Owner:** Agent 2  
**Branch:** `feature/ai-message-summarization`  
**Status:** ✅ COMPLETED (Merged to main)

**Tasks:**

- Create AI service for notification message summarization
- Convert raw notification data into StarCraft-style concise messages
- **ALL notifications** get AI analysis (not just high-priority)
- Implement message templates based on notification type
- Add tone/urgency modifiers (stern, professional, calming)
- Cache summaries to avoid redundant API calls
- Messages should be concise (10-15 words for critical, 20-30 for normal)

**Files:**

- `backend/services/notification_message_service.py` - ✅ CREATED
- `backend/services/ai_service.py` - ✅ USED (via chat method)
- `backend/api/models/notification.py` - ✅ MODIFIED (added summarized_message field)
- `src/notifications/notification_types.py` - ✅ MODIFIED (added summarized_message field)
- `frontend/src/types/notification.ts` - ✅ MODIFIED (added summarized_message field)
- `frontend/src/components/ToastContainer.tsx` - ✅ MODIFIED (uses summarized_message for voice)
- `frontend/src/utils/voice.ts` - ✅ MODIFIED (fixed speech synthesis initialization)

**Dependencies:** None (can work in parallel with Agent 1)

**Message Examples:**

- Raw: "BTC/USDT has broken above resistance at $45,000 with 85% confidence, volume increased 200%, RSI at 72"
- Summarized: "BTC breaking resistance. High confidence. Volume surge detected." (stern, professional, calm)
- Critical: "Position under attack. Stop loss 0.5% away. Immediate action required." (urgent but controlled)
- Threat: "Long position approaching stop loss. 1.2% remaining. Consider adjustment." (calm, informative)

**Tone Guidelines:**

- **Stern but professional:** Like a military commander reporting to general
- **Calming:** Never panicked, always controlled
- **Concise:** Get to the point quickly
- **Actionable:** Always suggest what to do

**Testing:**

- ✅ Test with various notification types
- ✅ Verify message length and clarity
- ✅ Test tone consistency
- ✅ Performance testing (API rate limits)
- ✅ Voice alerts now use summarized_message
- ✅ Speech synthesis initialization fixed (requires user interaction)

**Estimated Time:** 5-7 hours  
**Actual Time:** ~6 hours

**Completion Notes:**

- All notifications now automatically get AI-generated summaries
- Summaries are cached to reduce API calls
- Fallback summarization when AI service unavailable
- Voice system updated to use concise summaries
- Comprehensive debug logging added
- Testing guide created: `TEST_AGENT_2.md`

---

### Phase 2: Voice System (Can work in parallel with Phase 1)

#### 2.1 Voice Quality Improvement

**Owner:** Agent 3  
**Branch:** `feature/voice-quality-improvement`  
**Status:** ⬜ NOT STARTED

**Tasks:**

- Research and integrate better TTS (ElevenLabs, Azure Neural TTS, or similar)
- Create voice configuration system
- Implement voice selection (female, calm, competent)
- Add voice parameter tuning (rate, pitch, volume based on priority)
- Create voice preview/testing interface

**Implementation:**

1. **Primary: ElevenLabs API** (best quality, use free credits first)
2. **Fallback: Azure Neural TTS** (good quality, cheaper, for testing after credits)
3. **Fallback: Google Cloud TTS** (alternative fallback)
4. **Final Fallback: Browser TTS** (only if all services fail)

**Strategy:**

- Start with ElevenLabs free tier
- Automatically fallback to Azure/Google when credits exhausted
- Multi-provider service with seamless switching
- Track usage per provider to manage costs
- Cache audio for repeated messages

**Implementation Details:**

1. **Backend Voice Service** (`backend/services/voice_service.py`):

   - Multi-provider TTS client (ElevenLabs, Azure, Google)
   - Provider selection based on availability/credits
   - Audio generation endpoint: `POST /api/voice/synthesize`
   - Returns audio URL or base64-encoded audio
   - Error handling with automatic fallback

2. **Frontend Voice Client** (`frontend/src/utils/voice.ts`):

   - Rewrite to use backend TTS service instead of browser TTS
   - Maintain existing queue system (StarCraft-style)
   - Fetch audio from backend and play via Audio API
   - Fallback to browser TTS if backend unavailable

3. **Configuration:**
   - Environment variables for API keys:
     - `ELEVENLABS_API_KEY`
     - `AZURE_TTS_KEY` and `AZURE_TTS_REGION`
     - `GOOGLE_TTS_KEY` (optional)
   - Provider priority order configurable

**Files:**

- `backend/services/voice_service.py` - NEW (multi-provider TTS)
- `backend/api/routes/voice.py` - NEW (voice API endpoints)
- `frontend/src/utils/voice.ts` - REWRITE (use backend TTS)
- `frontend/src/components/VoiceSettings.tsx` - NEW (optional, for testing)

**Dependencies:** None (independent)

**Testing:**

- Test voice quality across different priorities
- Test message delivery speed
- Test queue handling (StarCraft-style sequential delivery)
- Test fallback between TTS providers
- User preference testing
- Verify calm, professional tone

**Estimated Time:** 6-8 hours

---

#### 2.2 Voice Message Queue & Priority System

**Owner:** Agent 4  
**Branch:** `feature/voice-queue-priority`  
**Status:** ⬜ NOT STARTED

**Tasks:**

- Improve voice queue system (already exists but needs enhancement)
- Implement priority-based queue management
- **StarCraft-style queuing:** Messages come in logical order, not all at once
- Critical messages can jump queue but don't interrupt current message
- Prevent message overlap/stuttering
- Add voice message history
- Ensure calm, sequential delivery (like battlefield reports to general)

**Files:**

- `frontend/src/utils/voice.ts` - MODIFY (enhance queue)
- `frontend/src/hooks/useVoiceQueue.ts` - NEW (optional)

**Dependencies:** Can work with Agent 3 (coordinate on voice.ts)

**Testing:**

- Test queue with multiple priorities
- Test StarCraft-style sequential delivery (no simultaneous messages)
- Test critical message queue jumping (but no interruption)
- Test queue overflow handling
- Verify calm, ordered delivery even under high load

**Estimated Time:** 3-4 hours

---

### Phase 3: Notification Processing Pipeline (Sequential - After Phase 1)

#### 3.1 Notification Enrichment Service

**Owner:** Agent 5  
**Branch:** `feature/notification-enrichment`  
**Status:** ⬜ NOT STARTED

**Tasks:**

- Create service that enriches notifications with AI analysis
- Add summarized messages to all notifications
- Calculate threat levels for position-related notifications
- Add contextual data (similar historical events, risk assessment)
- Integrate with existing notification service

**Files:**

- `backend/services/notification_enrichment_service.py` - NEW
- `backend/services/notification_service.py` - MODIFY
- `backend/api/routes/notifications.py` - MODIFY

**Dependencies:**

- Requires Agent 1 (threat detection)
- Requires Agent 2 (AI summarization)

**Testing:**

- Test enrichment for **ALL notification types** (not just high-priority)
- Test performance (shouldn't slow down notification delivery)
- Test with high notification volume
- Verify AI summaries are concise and actionable
- Test tone consistency (stern, professional, calming)

**Estimated Time:** 4-5 hours

---

#### 3.2 Real-time Notification Streaming

**Owner:** Agent 6  
**Branch:** `feature/notification-streaming`  
**Status:** ⬜ NOT STARTED

**Tasks:**

- Enhance WebSocket notification streaming
- Add priority-based delivery
- Implement notification batching for high-volume periods
- Add notification deduplication
- Ensure voice messages sync with visual notifications

**Files:**

- `backend/services/websocket_manager.py` - MODIFY
- `backend/api/routes/websocket.py` - MODIFY
- `frontend/src/hooks/useNotifications.ts` - MODIFY

**Dependencies:** Can work in parallel with Phase 2

**Testing:**

- Test high-volume notification streaming
- Test priority ordering
- Test WebSocket reconnection handling

**Estimated Time:** 3-4 hours

---

### Phase 4: UI/UX Enhancements (Can work in parallel with Phase 2-3)

#### 4.1 Notification Display Improvements

**Owner:** Agent 7  
**Branch:** `feature/notification-display-v2`  
**Status:** ⬜ NOT STARTED

**Tasks:**

- Redesign notification cards with threat indicators
- Add visual urgency indicators (pulsing, colors, animations)
- Show summarized messages prominently
- Add quick action buttons (more prominent)
- Improve notification grouping/filtering

**Files:**

- `frontend/src/components/NotificationCard.tsx` - REWRITE
- `frontend/src/components/ToastContainer.tsx` - MODIFY
- `frontend/src/types/notification.ts` - MODIFY (add new fields)

**Dependencies:** None (can work independently)

**Testing:**

- Test visual design with various notification types
- Test responsiveness
- Test accessibility

**Estimated Time:** 5-6 hours

---

#### 4.2 Command Center Integration

**Owner:** Agent 8  
**Branch:** `feature/command-center-v2`  
**Status:** ⬜ NOT STARTED

**Tasks:**

- Enhance Command Center with notification context
- Add "battle mode" UI theme
- Improve AI chat for notification analysis
- Add quick decision prompts
- Integrate voice feedback in Command Center

**Files:**

- `frontend/src/components/CommandCenter.tsx` - MODIFY
- `frontend/src/components/Workspace.tsx` - MODIFY

**Dependencies:** Can work in parallel with Agent 7

**Testing:**

- Test notification → Command Center flow
- Test AI analysis quality
- Test decision-making workflow

**Estimated Time:** 4-5 hours

---

## 🔄 Parallel vs Sequential Work

### ✅ Can Work in Parallel

**Phase 1:**

- Agent 1 (Threat Detection) + Agent 2 (AI Summarization) = **PARALLEL**

**Phase 2:**

- Agent 3 (Voice Quality) + Agent 4 (Voice Queue) = **PARALLEL** (coordinate on voice.ts)
- Can also work in parallel with Phase 1

**Phase 4:**

- Agent 7 (Notification Display) + Agent 8 (Command Center) = **PARALLEL**

### ⚠️ Must Be Sequential

**Phase 1 → Phase 3:**

- Agent 5 (Notification Enrichment) **MUST WAIT** for:
  - Agent 1 (Threat Detection) ✅
  - Agent 2 (AI Summarization) ✅

**Phase 3:**

- Agent 6 (Notification Streaming) can work in parallel with Agent 5, but should coordinate

---

## 🧪 Testing Strategy

### Per-Branch Testing (CRITICAL)

**Rule:** Each agent tests on their own branch, NOT on main.

#### Testing Workflow:

1. **Agent creates branch:**

   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/agent-N-description
   ```

2. **Agent works on their files**

3. **Agent tests locally:**

   ```bash
   # Start backend
   cd backend && python run.py

   # Start frontend (in another terminal)
   cd frontend && npm run dev

   # Test the feature
   # - Manual testing in browser
   # - Check console for errors
   # - Test edge cases
   # - Verify voice works
   # - Test notification flow
   ```

4. **Agent documents test results:**

   - Create `TEST_RESULTS_AGENT_N.md` in branch
   - Document what was tested
   - Document any issues found
   - Document what works/doesn't work

5. **Agent commits and pushes:**

   ```bash
   git add [their files]
   git commit -m "Agent N: [description]"
   git push origin feature/agent-N-description
   ```

6. **You test the branch:**

   ```bash
   git checkout feature/agent-N-description
   git pull origin feature/agent-N-description
   # Test the feature
   # Provide feedback
   ```

7. **Merge to main only after your approval**

### Testing Checklist Template

Create `TEST_CHECKLIST_AGENT_N.md` for each agent:

```markdown
# Agent N Testing Checklist

## Setup

- [ ] Backend running on localhost:8000
- [ ] Frontend running on localhost:5173
- [ ] Voice enabled in settings
- [ ] Test notifications can be created

## Feature Tests

- [ ] [Specific feature test 1]
- [ ] [Specific feature test 2]
- [ ] [Edge case test 1]
- [ ] [Edge case test 2]

## Integration Tests

- [ ] Works with existing notification system
- [ ] Doesn't break existing features
- [ ] Voice messages play correctly
- [ ] UI updates correctly

## Performance Tests

- [ ] No lag with high notification volume
- [ ] Voice queue handles multiple messages
- [ ] WebSocket reconnects properly

## Issues Found

- [Issue 1]
- [Issue 2]
```

---

## 🎯 Success Criteria

### Voice System

- [ ] Voice quality is significantly better (natural, clear)
- [ ] Messages are concise and impactful (max 10-15 words for critical)
- [ ] Priority-based voice modulation works
- [ ] Queue handles high volume without stuttering
- [ ] Critical messages can interrupt non-critical

### Notification System

- [ ] All notifications have AI-summarized messages
- [ ] Threat detection works for all position types
- [ ] Urgency scoring is accurate
- [ ] Notifications feel like StarCraft alerts
- [ ] System knows when to alert vs. when to wait

### User Experience

- [ ] User feels like they're in a command center
- [ ] Voice directs attention effectively
- [ ] Notifications drive decision-making
- [ ] Quick actions are accessible
- [ ] System feels responsive and urgent when needed

---

## 📝 Agent Coordination Rules

### File Ownership

**Agent 1 (Threat Detection):**

- ✅ `backend/services/threat_detection_service.py`
- ✅ `backend/services/trading_service.py` (threat monitoring parts)
- ❌ Don't touch voice files

**Agent 2 (AI Summarization):** ✅ COMPLETED

- ✅ `backend/services/notification_message_service.py` - CREATED
- ✅ `backend/services/ai_service.py` - USED (via chat method)
- ✅ `backend/api/models/notification.py` - MODIFIED
- ✅ `src/notifications/notification_types.py` - MODIFIED
- ✅ `frontend/src/types/notification.ts` - MODIFIED
- ✅ `frontend/src/components/ToastContainer.tsx` - MODIFIED
- ✅ `frontend/src/utils/voice.ts` - MODIFIED (initialization fix)
- ❌ Don't touch threat detection

**Agent 3 (Voice Quality):**

- ✅ `backend/services/voice_service.py` (if backend TTS)
- ✅ `frontend/src/utils/voice.ts` (coordinate with Agent 4)
- ❌ Don't touch notification processing

**Agent 4 (Voice Queue):**

- ✅ `frontend/src/utils/voice.ts` (coordinate with Agent 3)
- ✅ `frontend/src/hooks/useVoiceQueue.ts`
- ❌ Don't touch voice quality implementation

**Agent 5 (Notification Enrichment):**

- ✅ `backend/services/notification_enrichment_service.py`
- ✅ `backend/services/notification_service.py` (enrichment integration)
- ⚠️ **MUST WAIT** for Agent 1 & 2

**Agent 6 (Notification Streaming):**

- ✅ `backend/services/websocket_manager.py`
- ✅ `backend/api/routes/websocket.py`
- Can work in parallel with Agent 5

**Agent 7 (Notification Display):**

- ✅ `frontend/src/components/NotificationCard.tsx`
- ✅ `frontend/src/components/ToastContainer.tsx`
- Can work independently

**Agent 8 (Command Center):**

- ✅ `frontend/src/components/CommandCenter.tsx`
- ✅ `frontend/src/components/Workspace.tsx`
- Can work in parallel with Agent 7

### Coordination Points

1. **Agent 3 + Agent 4:** Both modify `voice.ts`

   - **Solution:** Agent 3 does voice quality, Agent 4 does queue logic
   - **Or:** Agent 4 waits for Agent 3, then adds queue enhancements

2. **Agent 5 depends on Agent 1 + Agent 2:**

   - **Solution:** Agent 5 waits for both to complete
   - **Or:** Agent 5 works with stubs/mocks, integrates later

3. **All agents modify notification flow:**
   - **Solution:** Each agent works on their layer, coordinate via API contracts

---

## 🚀 Recommended Execution Order

### Week 1: Foundation

1. **Agent 1** (Threat Detection) - Start immediately
2. **Agent 2** (AI Summarization) - Start immediately (parallel)
3. **Agent 3** (Voice Quality) - Start after Agent 1/2 have progress (parallel)

### Week 2: Integration

4. **Agent 4** (Voice Queue) - After Agent 3 (or coordinate)
5. **Agent 5** (Notification Enrichment) - After Agent 1 & 2 complete
6. **Agent 6** (Notification Streaming) - Can start in parallel with Agent 5

### Week 3: Polish

7. **Agent 7** (Notification Display) - Can start anytime
8. **Agent 8** (Command Center) - Can start in parallel with Agent 7

---

## 🧪 Manual Testing Guide

### For Each Branch

1. **Checkout the branch:**

   ```bash
   git fetch origin
   git checkout feature/agent-N-description
   ```

2. **Start services:**

   ```bash
   # Terminal 1: Backend
   cd backend && python run.py

   # Terminal 2: Frontend
   cd frontend && npm run dev
   ```

3. **Test the feature:**

   - Open browser to `http://localhost:5173`
   - Enable voice in settings
   - Trigger test notifications
   - Verify feature works as expected
   - Check console for errors
   - Test edge cases

4. **Document results:**

   - What works
   - What doesn't work
   - Any bugs found
   - Performance issues
   - UX feedback

5. **Provide feedback to agent:**
   - Comment on PR or create issue
   - Request changes if needed
   - Approve when ready

### Test Scenarios

**Voice Testing:**

- [ ] Low priority notification → Calm, professional voice
- [ ] High priority notification → Stern but controlled voice
- [ ] Critical notification → Urgent but not panicked voice
- [ ] Multiple notifications → Queue delivers in order (StarCraft-style)
- [ ] Critical during non-critical → Jumps queue but doesn't interrupt
- [ ] High volume → Messages come sequentially, not all at once
- [ ] TTS fallback → Switches providers seamlessly when credits exhausted

**Threat Detection Testing:**

- [ ] Position approaching stop loss → Threat detected in real-time
- [ ] Rapid price movement → Threat detected in real-time
- [ ] Volume spike → Threat detected in real-time
- [ ] Multiple threats → All detected, but notifications queued (not simultaneous)
- [ ] Real-time monitoring → Updates on every price change
- [ ] Queue ordering → Threats reported in logical order

**AI Summarization Testing:**

- [ ] **ALL notification types** get AI summarization
- [ ] Technical signal → Concise, stern, professional summary
- [ ] News alert → Key points extracted, actionable message
- [ ] Social sentiment → Summary generated, tone appropriate
- [ ] Position threat → Urgent but controlled message
- [ ] Tone consistency → All messages are stern, professional, calming
- [ ] Message length → Concise (10-15 words critical, 20-30 normal)

---

## 📊 Progress Tracking

Each agent should update their status in this document:

### Agent Status

- **Agent 1:** ⬜ NOT STARTED
- **Agent 2:** ✅ COMPLETED (Merged to main - AI Message Summarization)
- **Agent 3:** ⬜ NOT STARTED
- **Agent 4:** ⬜ NOT STARTED
- **Agent 5:** ⬜ NOT STARTED (waiting for Agent 1 & 2)
- **Agent 6:** ⬜ NOT STARTED
- **Agent 7:** ⬜ NOT STARTED
- **Agent 8:** ⬜ NOT STARTED

---

## ✅ Decisions Made

1. **Voice TTS Service:**

   - **Primary:** ElevenLabs (best quality)
   - **Fallback Strategy:** Use free credits first, then fallback to cheaper services (Azure/Google) for testing
   - **Implementation:** Multi-provider TTS service with automatic fallback

2. **AI Summarization:**

   - **ALL notifications** get AI analysis and summarization
   - Every notification should have a concise, stern, professional, calming message
   - AI acts as tactical advisor, summarizing complex data into actionable intelligence

3. **Threat Detection Frequency:**

   - **Real-time monitoring** (every price update)
   - **But:** Messages are queued and delivered in logical order (like StarCraft)
   - No simultaneous shouting - reports come calmly, one at a time
   - Priority determines queue position, not delivery speed

4. **Testing Approach:**
   - **Manual testing** for UX/voice/notifications (get the feel right)
   - **Automated testing** for trading logic (orders, prices, stop losses, etc.)

---

## 🎯 Next Steps

1. ✅ **Decisions made** - All questions answered
2. **Assign agents** (or agents self-assign from the 8 tasks)
3. **Agents create branches** and start work
4. **You test each branch** before merging (manual testing guide above)
5. **Iterate based on feedback**

---

## 🚀 Ready to Start!

**Recommended Execution Order:**

1. **Phase 1 (Parallel):** Agents 1 & 2 can start immediately
2. **Phase 2 (Parallel):** Agents 3 & 4 can start immediately (independent)
3. **Phase 3 (Sequential):** Agent 5 waits for Agents 1 & 2, Agent 6 can start
4. **Phase 4 (Parallel):** Agents 7 & 8 can start after Phase 3

**First Steps:**

- Agents should create their feature branches from `main`
- Follow file ownership rules to avoid conflicts
- Update progress tracking section as work progresses
- Test manually before requesting merge

**API Keys Needed:**

- ElevenLabs API key (get from https://elevenlabs.io)
- Azure TTS key + region (optional, for fallback)
- Google Cloud TTS key (optional, for fallback)
- AI service API key (for summarization - check existing `ai_service.py`)

---

**Let's build this StarCraft-style command center!** 🎮
