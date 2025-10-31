# 🚀 Quick Start Guide

Get Softlight running in 5 minutes!

## Step 1: Install Dependencies

```bash
# Make sure you're in the Softlight directory
cd /Users/tanmaybhardwaj/Personal/Softlight

# Sync dependencies and create virtual environment
uv sync

# Activate virtual environment
source .venv/bin/activate

# Install Playwright browser
playwright install chromium
```

## Step 2: Configure API Key

Create a `.env` file:

```bash
# Copy the example
cp .env.example .env

# Edit and add your OpenAI API key
# You can use any text editor
nano .env
```

Add your key:
```
OPENAI_API_KEY=sk-your-actual-key-here
```

## Step 3: Run Your First Task

```bash
python softlight/main.py
```

This will run the default task:
- Navigate to Google
- Search for "Softlight"
- Return the first result

## Step 4: Try Your Own Tasks

Edit `softlight/main.py` (at the bottom):

```python
if __name__ == "__main__":
    # Change these two lines
    task = "Your task description here"
    url = "https://your-starting-url.com/"
    
    main(task=task, url=url)
```

### Example Tasks

**Simple Search:**
```python
task = "Search for 'Python documentation' and tell me the first link"
url = "https://www.google.com/"
```

**Information Retrieval:**
```python
task = "What is the latest Python version?"
url = "https://www.python.org/"
```

**Form Filling:**
```python
task = "Search for 'playwright python' in the GitHub search box"
url = "https://github.com/"
```

## 📊 Understanding Output

You'll see output like:
```
============================================================
Step 1/20
============================================================

🤖 Agent Action:
I can see a search input field at bid=3. I'll type the query there.
TYPE 3 "Softlight"

✓ Typed 'Softlight' into element with bid=3
```

Legend:
- `🤖` = Agent's decision
- `✓` = Successful action
- `⚠` = Warning/retry
- `✗` = Failed action
- `✅` = Task complete

## 🔧 Common Configuration

### Run Headless (No Browser Window)
In `.env`:
```
HEADLESS_MODE=true
```

### Increase Max Steps
In `.env`:
```
MAX_STEPS=30
```

### Disable Result Saving
In `.env`:
```
SAVE_RESULTS=false
```

## 📁 Finding Results

Results are saved to `results/` directory:
```
results/
└── task_20231031_143022.json
```

Each file contains:
- Task description
- All steps taken
- Success/failure status
- Execution time
- Full history

## 🐛 Troubleshooting

### "Playwright browser not found"
```bash
playwright install chromium
```

### "OpenAI API error"
- Check your API key in `.env`
- Make sure you have credits

### Actions failing repeatedly
Try increasing retries in `.env`:
```
MAX_ACTION_RETRIES=5
```

### Want to see what's happening?
Run in non-headless mode:
```
HEADLESS_MODE=false
```

## 🎯 Tips for Better Results

1. **Be Specific**: "Search for X" is better than "Find X"
2. **One Task at a Time**: Break complex tasks into steps
3. **Include Context**: "Click the blue button" vs "Click button"
4. **Set Realistic Goals**: Some sites are harder to automate
5. **Use MAX_STEPS**: Start with 10-15 for simple tasks

## 📖 Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [CHANGES.md](CHANGES.md) to see what was improved
- Look at example tasks in `main.py`
- Customize settings in `.env`

## 💡 Example Session

```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Run
python softlight/main.py

# Output will show:
# ============================================================
# Step 1/20
# ============================================================
# 
# 🤖 Agent Action:
# I see a search box. Let me type the query.
# TYPE 3 "Softlight"
# 
# ✓ Typed 'Softlight' into element with bid=3
# 
# ============================================================
# Step 2/20
# ============================================================
# ...
# 
# ✅ Task complete!
# 
# ============================================================
# 📊 Task Summary
# ============================================================
# Total Steps: 3
# Successful: 3
# Failed: 0
# Duration: 12.34s
# ============================================================
```

That's it! You're ready to automate! 🎉

