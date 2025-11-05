# 🌟 Softlight - Assessment

AI-powered web automation that combines DOM selectors with vision-based coordinates for reliable, intelligent UI interaction.

## 🎯 What It Does

Give Softlight a natural language task and it will:
- Navigate web applications intelligently
- Use stable DOM selectors (role, aria-label, name, id)
- Fall back to coordinates for icons and custom controls
- Capture screenshots of each step

**Example:** "Create a new issue named 'Test Issue'" → Softlight handles it end-to-end.

## 🚀 Quick Setup

### 1. Install Dependencies

```bash
# Install dependencies with uv
uv sync

# Activate virtual environment
source .venv/bin/activate

# Install Playwright browsers
playwright install chromium
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# Required
OPENAI_API_KEY=sk-your-key-here

# Optional (defaults shown)
AGENT_MODE=hybrid              # "hybrid" or "vision"
HEADLESS_MODE=false            # true for no browser window
MAX_STEPS=20                   # Max actions per task
```

### 3. Run Your First Task

```python
from softlight.main import main

dataset_path = main(
    question="create a new issue with name 'Test Issue'",
    url="https://linear.app/workspace/team/TES/active",
    app_name="Linear",
    use_profile=True,  # Remember login sessions
    mode="hybrid"      # or "vision"
)
```

Or run directly:

```bash
python softlight/main.py
```

## 📁 Output

Tasks generate structured datasets:

```
datasets/
  create_new_issue_20251104_123456/
    ├── metadata.json              # Task metadata + actions
    ├── step_0_initial.png         # Initial page
    ├── step_1_click_bid13.png     # After clicking
    └── step_2_type_bid5.png       # After typing
```

## 🔐 Login Sessions

Uses a separate Chrome profile at `~/.chrome-automation-profile`:
- **First run:** Manually log in when browser opens
- **Future runs:** Automatically logged in
- Your main Chrome stays independent

## 🏗️ Architecture

### Two-Agent System

- **Agent A (Executor):** Executes actions using Playwright
  - Tries semantic selectors first (stable)
  - Falls back to coordinates when needed
  
- **Agent B (Instructor):** Analyzes page and decides actions
  - Receives DOM elements + page text + screenshot
  - Returns actions with bid + coordinate fallback
  - Powered by GPT-4o

### Execution Strategy

1. **Perception:** Extract DOM + capture screenshot
2. **Decision:** Agent B analyzes and returns action
3. **Execution:** Agent A tries selectors first, then coordinates
4. **Repeat** until task complete

## 🔧 Modes

**Hybrid Mode** (Recommended):
- Uses DOM selectors first → faster and more stable
- Falls back to coordinates → works everywhere
- Best for standard web apps

**Vision Mode**:
- Uses coordinates only
- Good for canvas/custom UIs
- Slower but works anywhere

## 📊 Project Structure

```
softlight/
├── agent/                  # Instructor & Executor agents
├── actions/                # Playwright action primitives
├── browserController/      # Browser lifecycle
├── domProcessor/           # DOM extraction
├── state/                  # Page state management
├── dataset/                # Dataset organization
├── orchestrator_hybrid.py  # Main hybrid loop
└── main.py                 # Entry point
```

## 📚 Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed system design
- [SETUP_LINEAR.md](SETUP_LINEAR.md) - Linear-specific setup

## 🐛 Troubleshooting

**Playwright not found:**
```bash
playwright install chromium
```

**API errors:**
```bash
# Check your API key
echo $OPENAI_API_KEY
```

**Watch execution:**
```bash
# Set headless to false in .env
HEADLESS_MODE=false
```

---

**Softlight** - Intelligent UI automation combining DOM selectors with vision fallback
