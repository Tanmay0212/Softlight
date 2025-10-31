# 🚀 Setting Up Softlight with Linear

## ✅ Implementation Complete - Separate Profile

The system now uses a **separate Chrome profile** for automation, which means:
- ✅ Your main Chrome browser can stay open
- ✅ Login once, use forever
- ✅ No conflicts with your regular browsing
- ✅ Clean separation between personal and automation

## 📍 Profile Location

The automation profile is stored at:
```
~/.chrome-automation-profile
```

## 🎯 First Time Setup

### Step 1: Run the script
```bash
python softlight/main.py
```

### Step 2: Log into Linear
When Chrome opens:
1. A **new Chrome window** will open (separate from your main Chrome)
2. It will navigate to your Linear workspace URL
3. **Manually log into Linear** in this window
4. Once logged in, the automation will continue

### Step 3: Done!
Your login is now saved. Future runs will automatically use the saved session.

## 🔄 Future Runs

Just run the script - you'll be automatically logged in:
```bash
python softlight/main.py
```

The system will:
1. Open Chrome with the saved profile
2. Already be logged into Linear
3. Start executing the task immediately

## 📝 Current Configuration

In `softlight/main.py`, update these lines:

```python
# Line 50-53
question = "How do I create a project in Linear?"
url = "https://linear.app/YOUR-WORKSPACE/team/YOUR-TEAM/active"  # Update this!
app_name = "Linear"
use_profile = True
```

Replace `YOUR-WORKSPACE` and `YOUR-TEAM` with your actual Linear workspace details.

## 🎮 Example Tasks

### Task 1: Create a Project
```python
question = "How do I create a project in Linear?"
url = "https://linear.app/softlight-assesment/team/SOF/active"
```

### Task 2: Filter Issues
```python
question = "How do I filter issues by status in Linear?"
url = "https://linear.app/softlight-assesment/team/SOF/active"
```

### Task 3: Create a Task
```python
question = "Create a new task and call it 'Test Task'"
url = "https://linear.app/softlight-assesment/team/SOF/active"
```

### Task 4: Assign an Issue
```python
question = "How do I assign an issue to someone in Linear?"
url = "https://linear.app/softlight-assesment/team/SOF/active"
```

## 🔧 CLI Usage

### Single task with profile:
```bash
python -m softlight.cli run \
  "How do I create a project in Linear?" \
  --url "https://linear.app/softlight-assesment/team/SOF/active" \
  --app Linear \
  --use-profile
```

### Batch tasks with profile:
```bash
python -m softlight.cli batch \
  --tasks examples/task_questions.json \
  --use-profile
```

## 🗑️ Resetting the Profile

If you need to log in again or clear the profile:

```bash
# Remove the automation profile directory
rm -rf ~/.chrome-automation-profile

# Next run will be treated as first-time setup
python softlight/main.py
```

## ⚠️ Troubleshooting

### Issue: Browser doesn't open
- Make sure you have Chrome installed (not just Chromium)
- Try: `which google-chrome-stable` or check `/Applications/Google Chrome.app`

### Issue: Login doesn't persist
- The profile directory might not have write permissions
- Check: `ls -la ~/.chrome-automation-profile`
- Fix: `chmod -R 755 ~/.chrome-automation-profile`

### Issue: "Channel 'chrome' not found"
- Install Google Chrome (not Chromium)
- Or change `channel="chrome"` to `channel="chromium"` in browser_controller.py

## 📊 What Gets Saved

In the automation profile:
- ✅ Login cookies (Linear session)
- ✅ Browser settings
- ✅ Cache and preferences
- ❌ Your personal bookmarks (separate profile)
- ❌ Your personal history (separate profile)

## 🎯 Benefits

1. **No Conflicts**: Your main Chrome stays independent
2. **Persistent Login**: Log in once, use forever
3. **Clean Separation**: Automation doesn't affect your browsing
4. **Easy Reset**: Delete the profile directory to start fresh
5. **Safe**: Can't accidentally mess with your main profile

## 🚀 You're Ready!

Just run:
```bash
python softlight/main.py
```

First time: Log into Linear manually
Every other time: Automatically logged in! 🎉

