# Parallel Development Workflow Guide

## 🎯 Standard Approach: Feature Branches (What We've Been Using)

### How It Works

**Each agent works on their own feature branch:**

```bash
# Agent starts work
git checkout main
git pull origin main
git checkout -b feature/agent-N-description

# Agent works on their files
# ... make changes ...

# Agent commits and pushes
git add [their files]
git commit -m "Agent N: [description]"
git push origin feature/agent-N-description

# When done, merge to main
git checkout main
git merge feature/agent-N-description
git push origin main
git branch -d feature/agent-N-description
```

### Advantages

- ✅ **Isolation**: Each agent's work is completely separate
- ✅ **No conflicts**: Agents don't interfere with each other
- ✅ **Easy to review**: Each branch can be tested independently
- ✅ **Standard Git workflow**: Works with any Git setup
- ✅ **Remote backup**: Branches can be pushed to remote

### When Another Agent Finishes

If Agent 2 finishes while Agent 1 is still working:

```bash
# Agent 1 updates their branch with latest main
git checkout feature/agent-1-description
git pull origin main  # Get Agent 2's changes
git rebase main       # Or: git merge main
# Resolve any conflicts if needed
git push origin feature/agent-1-description --force-with-lease  # If rebased
```

---

## 🔄 Git Worktree: REQUIRED for Multiple Agents on Same Machine

### ⚠️ Critical: If Agents Work on Same Machine

**If multiple agents are working on the SAME machine simultaneously, you MUST use git worktree** to avoid:
- ❌ File conflicts (agents editing same files)
- ❌ Git state conflicts (multiple agents committing)
- ❌ Service conflicts (backend/frontend can only run once per port)
- ❌ Working directory conflicts

### What Is Git Worktree?

Git worktree allows you to have **multiple working directories** from the same repository, each on a different branch.

### Setup for Parallel Agents on Same Machine

```bash
# Main worktree (on main branch) - this is your current repo
cd /Users/anar_enhsaihan/Documents/playground/composer/trading-bot-2

# Create worktree for Agent 1's branch
git worktree add ../trading-bot-2-agent1 feature/agent-1-threat-detection

# Create worktree for Agent 2's branch  
git worktree add ../trading-bot-2-agent2 feature/agent-2-ai-summarization

# Now you have:
# /Users/.../trading-bot-2              → main branch (original)
# /Users/.../trading-bot-2-agent1      → Agent 1's branch
# /Users/.../trading-bot-2-agent2      → Agent 2's branch

# Each agent works in their own directory:
# Agent 1: cd ../trading-bot-2-agent1
# Agent 2: cd ../trading-bot-2-agent2
```

### Workflow with Worktree

**Agent 1:**
```bash
# Agent 1 works in their worktree
cd ../trading-bot-2-agent1

# Create/switch to their branch (if not already created)
git checkout -b feature/agent-1-threat-detection

# Work on files
# ... edit threat_detection_service.py ...

# Commit
git add backend/services/threat_detection_service.py
git commit -m "Agent 1: Add threat detection service"
git push origin feature/agent-1-threat-detection

# Test (in their own directory)
python backend/run.py  # Runs on port 8000 (or different port)
```

**Agent 2 (in parallel):**
```bash
# Agent 2 works in their worktree
cd ../trading-bot-2-agent2

# Create/switch to their branch
git checkout -b feature/agent-2-ai-summarization

# Work on files (different files, no conflict)
# ... edit notification_message_service.py ...

# Commit
git add backend/services/notification_message_service.py
git commit -m "Agent 2: Add AI message summarization"
git push origin feature/agent-2-ai-summarization

# Test (in their own directory)
# Note: Can't run backend on same port, or just test sequentially
```

### Managing Worktrees

```bash
# List all worktrees
git worktree list

# Remove a worktree when agent is done
git worktree remove ../trading-bot-2-agent1

# Or force remove if there are uncommitted changes
git worktree remove --force ../trading-bot-2-agent1
```

### Port Conflicts

**If agents need to test simultaneously:**

**Option 1: Different ports**
```bash
# Agent 1
cd ../trading-bot-2-agent1
python backend/run.py  # Uses default port 8000

# Agent 2 (modify backend/run.py or use env var)
cd ../trading-bot-2-agent2
PORT=8001 python backend/run.py  # Different port
```

**Option 2: Test sequentially**
- Agent 1 tests, then stops
- Agent 2 tests, then stops
- Or use different machines/containers

### For Separate Machines/Environments

**If agents work on DIFFERENT machines:**
- Each agent has their own clone
- Standard feature branch workflow is sufficient
- No worktree needed

---

## 📋 Recommended Workflow for Parallel Agents

### Scenario: Agent 1 and Agent 2 Working in Parallel

**Agent 1 (Threat Detection):**
```bash
# Start
git checkout main
git pull origin main
git checkout -b feature/agent-1-threat-detection

# Work on files
# ... edit threat_detection_service.py ...

# Commit and push
git add backend/services/threat_detection_service.py
git commit -m "Agent 1: Add threat detection service"
git push origin feature/agent-1-threat-detection

# Continue working...
# ... more commits ...

# When done, merge to main
git checkout main
git merge feature/agent-1-threat-detection
git push origin main
```

**Agent 2 (AI Summarization) - Working in Parallel:**
```bash
# Start (at same time as Agent 1)
git checkout main
git pull origin main
git checkout -b feature/agent-2-ai-summarization

# Work on files (different files, no conflict)
# ... edit notification_message_service.py ...

# Commit and push
git add backend/services/notification_message_service.py
git commit -m "Agent 2: Add AI message summarization"
git push origin feature/agent-2-ai-summarization

# If Agent 1 finishes first, update before merging:
git pull origin main  # Get Agent 1's changes
git rebase main       # Rebase on top of Agent 1's work
# (or: git merge main)

# When done, merge to main
git checkout main
git merge feature/agent-2-ai-summarization
git push origin main
```

### Key Points

1. **Both agents start from same `main`** - They get the same base
2. **They work on different files** - No conflicts
3. **They push to different branches** - Complete isolation
4. **When one finishes, the other updates** - Pull latest `main` before merging
5. **Merge order doesn't matter** - Git handles it

---

## ⚠️ Handling Shared Files

### If Agents Need the Same File

**Example: Agent 3 and Agent 4 both modify `voice.ts`**

**Option 1: Sequential (Safest)**
```bash
# Agent 3 finishes first
git checkout main
git merge feature/agent-3-voice-quality
git push origin main

# Agent 4 then updates and works
git checkout feature/agent-4-voice-queue
git pull origin main  # Get Agent 3's changes
git rebase main        # Rebase on top
# Resolve conflicts if any
git push origin feature/agent-4-voice-queue --force-with-lease
```

**Option 2: Coordinate**
- Agents communicate about changes
- First agent commits their part
- Second agent pulls and continues

---

## 🎯 Best Practices

### ✅ DO

1. **Always start from latest `main`**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/agent-N-description
   ```

2. **Check for existing branches before starting**
   ```bash
   git fetch origin
   git branch -a | grep feature/agent-
   ```

3. **Update your branch if another agent finishes**
   ```bash
   git pull origin main
   git rebase main  # or: git merge main
   ```

4. **Push your branch regularly** (for backup)
   ```bash
   git push origin feature/agent-N-description
   ```

5. **Test on your branch before merging**
   ```bash
   git checkout feature/agent-N-description
   # Test everything works
   ```

### ❌ DON'T

1. **Don't work directly on `main`**
2. **Don't commit to another agent's branch**
3. **Don't force push to shared branches**
4. **Don't ignore conflicts** - resolve them properly
5. **Don't merge without testing**

---

## 🔍 Checking What's In Progress

### See All Agent Branches

```bash
# Fetch latest
git fetch origin

# See all feature branches
git branch -a | grep feature/agent-

# See recent activity
git log --oneline --all --graph --decorate -20

# See what's on each branch
git log --oneline feature/agent-1-threat-detection
git log --oneline feature/agent-2-ai-summarization
```

### Check File Ownership

```bash
# See who last modified a file
git log --oneline --all -- backend/services/voice.ts

# See detailed history
git log --all --format="%h %an %ad %s" --date=short -- backend/services/voice.ts
```

---

## 📊 Summary

### ⚠️ IMPORTANT: Same Machine vs Different Machines

**If agents work on the SAME machine:**
- ✅ **MUST use git worktree** - Each agent gets their own directory
- ✅ Prevents file conflicts, git state conflicts, service conflicts
- ✅ Each agent can work independently in their own worktree

**If agents work on DIFFERENT machines:**
- ✅ **Standard feature branch workflow** - Each agent has their own clone
- ✅ No worktree needed
- ✅ Work independently, push to remote, merge when done

### Recommended Workflow for Same Machine

**Setup (once):**
```bash
# In main repo
git worktree add ../trading-bot-2-agent1 feature/agent-1-threat-detection
git worktree add ../trading-bot-2-agent2 feature/agent-2-ai-summarization
```

**Each Agent:**
```bash
# Agent 1
cd ../trading-bot-2-agent1
# Work, commit, push, test

# Agent 2  
cd ../trading-bot-2-agent2
# Work, commit, push, test
```

**Cleanup (when done):**
```bash
git worktree remove ../trading-bot-2-agent1
git worktree remove ../trading-bot-2-agent2
```

### For Our Use Case (Multiple Agents on Same Machine)

**✅ Use git worktree:**
- Each agent gets their own working directory
- No conflicts between agents
- Can test independently (or on different ports)
- Clean separation of work

**This is the correct approach for parallel agents on the same machine!** ✅

