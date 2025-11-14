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

## 🔄 Alternative: Git Worktree (When You Need Multiple Branches Simultaneously)

### What Is Git Worktree?

Git worktree allows you to have **multiple working directories** from the same repository, each on a different branch.

### When Would You Use It?

**Use worktree if:**
- You need to work on multiple branches **at the same time** on the **same machine**
- You want to test different branches simultaneously
- You're a single developer managing multiple features

**Example:**
```bash
# Main worktree (on main branch)
cd /path/to/repo

# Create additional worktree for Agent 1's branch
git worktree add ../repo-agent1 feature/agent-1-threat-detection

# Create additional worktree for Agent 2's branch
git worktree add ../repo-agent2 feature/agent-2-ai-summarization

# Now you have:
# /path/to/repo              → main branch
# /path/to/repo-agent1       → Agent 1's branch
# /path/to/repo-agent2       → Agent 2's branch

# Each can run independently:
cd /path/to/repo-agent1 && python backend/run.py  # Terminal 1
cd /path/to/repo-agent2 && python backend/run.py  # Terminal 2
```

### For Multiple Agents (Separate Developers/AI Instances)

**Worktree is NOT needed** because:
- Each agent has their own clone of the repository
- Each agent works on their own machine/environment
- They don't need multiple branches active simultaneously

**Standard feature branch workflow is sufficient.**

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

### Standard Workflow (Recommended)

- ✅ Each agent: **Feature branch from `main`**
- ✅ Work independently on different files
- ✅ Push to remote for backup
- ✅ Update branch when others finish
- ✅ Merge to `main` when done

### When to Use Worktree

- ✅ Only if you need **multiple branches active simultaneously** on **same machine**
- ✅ For testing different branches at the same time
- ❌ **NOT needed** for separate agents (they have separate clones)

### For Our Use Case

**Use standard feature branch workflow:**
- Each agent creates their branch from `main`
- They work independently
- They push to remote
- They merge when done
- Other agents pull latest `main` and continue

**This is what we've been doing and it works perfectly!** ✅

