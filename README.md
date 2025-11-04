# 🌟 Softlight - Hybrid DOM + Vision UI Automation

**Softlight** is an intelligent AI system that automates web UI interactions using a hybrid approach combining DOM selectors with vision-based coordinates.

## 🎯 What It Does

Give Softlight a task like "Create a new issue named 'Test Issue'" and it will:
1. **Navigate** the application intelligently
2. **Extract DOM** elements with semantic attributes
3. **Use stable selectors** (role, aria-label, name, id) to interact
4. **Fall back to coordinates** for icons and custom controls
5. **Capture** screenshots of each step

Perfect for UI automation, testing, and workflow documentation.

## 🏗️ Architecture

### Hybrid DOM + Vision System

Softlight uses a two-agent architecture:

- **Agent A (SimpleExecutor)**: Executes actions using Playwright
  - Tries semantic selectors first (stable)
  - Falls back to coordinates when needed
  - Reports success/failure with method used

- **Agent B (HybridInstructor)**: Analyzes page state and decides actions
  - Receives DOM elements + page text + screenshot
  - Returns actions with bid (DOM target) + coordinates (fallback)
  - Powered by OpenAI GPT-4o

### Execution Strategy

```
1. Perception:
   - Extract DOM elements (semantic attributes)
   - Capture page text
   - Take screenshot

2. Decision:
   - Agent B analyzes all inputs
   - Returns action with bid + coordinates

3. Execution (Selector-First):
   - Try data-bid selector (injected)
   - Try semantic selectors (role, aria-label, etc.)
   - Try text-based selectors
   - Fall back to coordinates
```

## ✨ Features

- 🤖 **Hybrid Approach**: DOM selectors + vision fallback
- 🎯 **Semantic Targeting**: Uses ARIA, roles, and labels
- 📸 **Auto Screenshots**: Every step captured
- 🔄 **Adaptive**: Works with any web app
- 💾 **Structured Output**: JSON metadata + screenshots
- 🔐 **Session Management**: Persistent Chrome profile
- 📊 **Observable**: Logs which method succeeded

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key
- `uv` package manager (recommended)

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd Softlight

# Install dependencies
uv sync
source .venv/bin/activate

# Install Playwright
playwright install chromium

# Set API key
export OPENAI_API_KEY=sk-your-key-here
```

### Run Your First Task

```python
python softlight/main.py
```

Or customize in code:

```python
from softlight.main import main

dataset_path = main(
    question="create a new issue with name 'Test Issue'",
    url="https://linear.app/workspace/team/TES/active",
    app_name="Linear",
    use_profile=True,  # Remember login sessions
    mode="hybrid"      # or "vision" for coordinates-only
)
```

## 📖 Usage Examples

### Linear - Create Issue

```python
from softlight.main import main

main(
    question="create a new issue with name 'Bot Issue 1'",
    url="https://linear.app/workspace/team/TES/active",
    app_name="Linear",
    use_profile=True
)
```

### Google Search

```python
main(
    question="Search for 'Playwright documentation'",
    url="https://www.google.com/",
    app_name="Google",
    use_profile=False
)
```

## 📁 Output Structure

```
datasets/
  create_new_issue_with_20251104_123456/
    ├── metadata.json              # Task metadata + action history
    ├── step_0_initial.png         # Initial page
    ├── step_1_click_bid13.png     # After clicking button
    └── step_2_type_bid5.png       # After typing text
```

### metadata.json

```json
{
  "task_id": "create_new_issue_with_20251104_123456",
  "question": "create a new issue with name 'Bot Issue 1'",
  "url": "https://linear.app/...",
  "app_name": "Linear",
  "mode": "hybrid",
  "duration_seconds": 12.5,
  "action_history": [
    {
      "step": 1,
      "action": "CLICK",
      "bid": "13",
      "reasoning": "Click 'Create new issue' button"
    }
  ]
}
```

## ⚙️ Configuration

### Environment Variables

Create `.env` file:

```bash
# Required
OPENAI_API_KEY=sk-your-key-here

# Optional
AGENT_MODE=hybrid              # "hybrid" or "vision"
OPENAI_MODEL_NAME=gpt-4o      # GPT-4o recommended
HEADLESS_MODE=false            # Set true for no browser window
MAX_STEPS=20                   # Max actions per task
MAX_ELEMENTS=100               # Max DOM elements to extract
```

### Mode Selection

**Hybrid Mode** (Recommended):
- Uses DOM selectors first
- Falls back to coordinates
- More stable and faster

**Vision Mode**:
- Uses only coordinates
- Good for canvas/custom UIs
- Slower but works anywhere

## 🔐 Login Sessions (Linear, GitHub, etc.)

Softlight uses a **separate Chrome profile** at `~/.chrome-automation-profile`:

✅ First run: Manually log into your app
✅ Future runs: Automatically logged in
✅ Your main Chrome stays independent
✅ No conflicts or data sharing

See [SETUP_LINEAR.md](SETUP_LINEAR.md) for detailed setup.

## 🏗️ Project Structure

```
softlight/
├── agent/
│   ├── hybrid_instructor.py    # Agent B (analyzes & decides)
│   ├── simple_executor.py      # Agent A (executes actions)
│   └── vision_instructor.py    # Vision-only mode agent
├── actions/
│   └── browser_actions.py      # Playwright action primitives
├── browserController/
│   └── browser_controller.py   # Browser lifecycle management
├── domProcessor/
│   ├── dom_extractor.py        # HTML → Elements extraction
│   └── element_info.py         # Element representation
├── state/
│   └── page_state.py           # PageState (DOM + text + screenshot)
├── dataset/
│   └── dataset_manager.py      # Dataset organization
├── core/
│   └── config/
│       ├── env.py              # Settings & configuration
│       └── logger.py           # Structured logging
├── orchestrator_hybrid.py      # Main hybrid loop
├── orchestrator_vision.py      # Vision-only loop
└── main.py                     # Entry point
```

## 🔧 How It Works

### Hybrid Mode Flow

```
1. Page Load
   ↓
2. Extract DOM Elements
   - Find buttons, inputs, links
   - Extract role, aria-label, name, id, text
   - Rank by priority
   ↓
3. Inject data-bid Attributes
   - Assign unique bid to each element
   - Inject into actual DOM
   ↓
4. Build PageState
   - Elements list
   - Page text
   - Screenshot
   ↓
5. Agent B Decides
   - Analyze DOM elements
   - Use screenshot for context
   - Return action with bid + coords
   ↓
6. Agent A Executes (Selector-First)
   - Try: [data-bid="13"]
   - Try: button[aria-label="Create"]
   - Try: #submit-button
   - Fallback: click(x, y)
   ↓
7. Wait & Repeat
```

## 📊 Execution Methods

When you run a task, you'll see logs like:

```
✅ CLICK successful (method: data-bid)
✅ TYPE successful (method: placeholder)
✅ CLICK successful (method: role+aria-label)
✅ CLICK successful (method: coordinates)  # Fallback for icon
```

Methods in priority order:
1. `data-bid` - Injected unique identifier
2. `role+aria-label` - Semantic attributes
3. `aria-label` - Label alone
4. `name` - Name attribute
5. `id` - Element ID
6. `text` - Text content matching
7. `coordinates` - Pixel position fallback

## 🐛 Troubleshooting

### Installation Issues

```bash
# Playwright not found
playwright install chromium

# UV not installed
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### API Issues

```bash
# Check API key
echo $OPENAI_API_KEY

# Test with simple task
python softlight/main.py
```

### Actions Failing

1. **Enable visual debugging**:
   ```bash
   export HEADLESS_MODE=false
   ```

2. **Check logs** - look for selector failures:
   ```
   ❌ CLICK failed: data-bid: Timeout 3000ms exceeded
   ```

3. **Verify DOM injection** - check if bids are injected:
   ```
   Injected 47/64 data-bid attributes into DOM
   ```

### Common Issues

**Issue**: "All selectors failed, using coordinates"
- **Cause**: Page lacks semantic attributes
- **Fix**: Falls back automatically, or improve page accessibility

**Issue**: "Injected 0/64 data-bid attributes"
- **Cause**: Selector generation failed
- **Fix**: Check if page is fully loaded

**Issue**: "Wrong element clicked"
- **Cause**: Multiple elements with same attributes
- **Fix**: System uses priority scoring, should work most times

## 🎯 Best Practices

1. **Use descriptive tasks**: "Create issue named X" > "Make new thing"
2. **Start with hybrid mode**: More stable than vision-only
3. **Enable persistent profile**: Saves login sessions
4. **Check logs**: Understand which methods work best
5. **Adjust MAX_ELEMENTS**: Reduce if page is slow

## 📈 Performance

- **Speed**: ~2-3 seconds per action (hybrid mode)
- **Stability**: High with semantic attributes
- **Cost**: ~$0.05-0.10 per task (GPT-4o)

## 🔮 Comparison: Hybrid vs Vision

| Aspect | Hybrid Mode | Vision Mode |
|--------|------------|-------------|
| **Primary Method** | DOM selectors | Coordinates |
| **Fallback** | Coordinates | None |
| **Stability** | High | Medium |
| **Speed** | Fast | Slower |
| **Works on Canvas** | Yes (fallback) | Yes |
| **Debugging** | Easy (see selectors) | Harder |
| **Best For** | Standard web apps | Custom UIs |

## 🤝 Contributing

Areas for improvement:
- Multi-tab support
- Better error recovery
- Performance optimizations
- More action types (drag-drop, etc.)

## 📝 License

[Your License Here]

## 🙏 Acknowledgments

- **OpenAI GPT-4o** - Vision + reasoning
- **Playwright** - Browser automation
- **browser-use** - Inspiration for hybrid approach

---

**Softlight** - Intelligent UI Automation with Hybrid DOM + Vision
