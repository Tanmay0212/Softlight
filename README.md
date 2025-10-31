# 🌟 Softlight - Two-Agent UI Capture System

**Softlight** is an intelligent multi-agent system that automatically demonstrates how to perform tasks in web applications. It uses two AI agents working together to navigate apps, capture UI states, and create comprehensive workflow datasets.

## 🎯 What It Does

Give Softlight a question like "How do I create a project in Linear?" and it will:
1. **Navigate** the live application
2. **Figure out** the steps automatically
3. **Capture screenshots** of each UI state
4. **Save** a complete workflow demonstration

Perfect for creating UI documentation, training datasets, and workflow guides.

## 🏗️ Two-Agent Architecture

Softlight uses a unique two-agent collaboration pattern:

### Agent A (Executor)
- **Observes** web pages and UI states
- **Executes** actions (clicks, typing, scrolling)
- **Reports** what it sees and what happened
- **Captures** screenshots automatically

### Agent B (Instructor)
- **Understands** the user's task/question
- **Analyzes** Agent A's observations
- **Provides** step-by-step instructions
- **Determines** when the task is complete

### Communication Flow

```
User Question: "Search for Softlight on Google"
      ↓
┌─────────────────────────────────────────────┐
│  Agent B (Instructor)                       │
│  "Navigate to search, type query, submit"   │
└────────────┬────────────────────────────────┘
             ↓ Instruction
┌────────────┴────────────────────────────────┐
│  Agent A (Executor)                         │
│  Observes → Executes → Captures → Reports   │
└────────────┬────────────────────────────────┘
             ↓ Observation
┌────────────┴────────────────────────────────┐
│  Agent B analyzes → Next instruction        │
└────────────┬────────────────────────────────┘
             ↓
      Repeat until complete
```

## ✨ Features

- 🤖 **Dual-Agent AI**: Two GPT-4o agents collaborating intelligently
- 📸 **Auto Screenshot Capture**: Every UI state automatically captured
- 🎯 **Task Generalization**: Handles any web app without hardcoding
- 💾 **Structured Datasets**: Organized workflows with metadata
- 🔄 **Adaptive Planning**: Agents adjust based on what they observe
- 📊 **Comprehensive Logging**: Full conversation history saved
- 🎨 **Beautiful CLI**: Easy-to-use command-line interface

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- OpenAI API key
- `uv` package manager (recommended) or `pip`

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd Softlight

# Install dependencies with uv
uv sync
source .venv/bin/activate

# Install Playwright browsers
playwright install chromium

# Set up environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Run Your First Task

```bash
# Simple example
python softlight/main.py
```

Or use the CLI:

```bash
# Single task
python -m softlight.cli run "Search for Softlight on Google" --url "https://www.google.com/" --app Google

# Batch process multiple tasks
python -m softlight.cli batch --tasks examples/task_questions.json

# Generate dataset summary
python -m softlight.cli summarize
```

## 📖 Usage Examples

### Example 1: Google Search

```python
from softlight.main import main

question = "Search for Softlight on Google"
url = "https://www.google.com/"
dataset_path = main(question, url, "Google")
```

**Result**: 3-4 screenshots showing the complete search process

### Example 2: Linear Project Creation

```python
question = "How do I create a project in Linear?"
url = "https://linear.app/workspace/projects"
dataset_path = main(question, url, "Linear")
```

**Result**: 5-7 screenshots demonstrating the full workflow

### Example 3: Issue Filtering

```python
question = "How do I filter issues by status in Linear?"
url = "https://linear.app/workspace/team/TES/active"
dataset_path = main(question, url, "Linear")
```

## 📁 Output Structure

After running a task, you'll get:

```
datasets/
  search_softlight_google_20251030_143022/
    ├── metadata.json              # Full conversation + metadata
    ├── step_0_initial.png         # Initial page state
    ├── step_1_type_5_softlight.png  # After typing
    └── step_2_click_10.png        # Search results
```

### metadata.json Format

```json
{
  "task_id": "search_softlight_google_20251030_143022",
  "user_question": "Search for Softlight on Google",
  "app": "Google",
  "url": "https://www.google.com/",
  "completed": true,
  "total_steps": 3,
  "duration": 25.3,
  "conversation": [
    {
      "step_num": 0,
      "agent_a_observation": "I see a search box (bid=5)...",
      "screenshot": "step_0_initial.png",
      "agent_b_instruction": "Type 'Softlight' in the search box (bid=5)",
      "agent_a_action": "TYPE 5 'Softlight'",
      "agent_a_result": "Typed successfully...",
      "agent_a_next_observation": "Search suggestions appeared..."
    }
  ]
}
```

## ⚙️ Configuration

All settings via environment variables (`.env` file):

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL_NAME=gpt-4o

# Agent A (Executor) Configuration
AGENT_A_MODEL=gpt-4o
AGENT_A_MAX_TOKENS=500

# Agent B (Instructor) Configuration
AGENT_B_MODEL=gpt-4o
AGENT_B_MAX_TOKENS=800

# Browser Configuration
HEADLESS_MODE=false
BROWSER_TIMEOUT=60000

# Dataset Configuration
DATASET_ROOT=datasets
MAX_STEPS=20
```

## 🔐 Using with Login-Required Apps (Linear, GitHub, etc.)

Softlight uses a **separate Chrome profile** for automation, which means:
- ✅ Your main Chrome browser can stay open while automation runs
- ✅ Log in once, sessions are remembered forever
- ✅ No conflicts with your regular browsing
- ✅ Clean separation between personal and automation data

### First Time Setup:
1. Run the script with `use_profile=True` (already set in `main.py`)
2. Chrome will open with a separate profile at `~/.chrome-automation-profile`
3. **Manually log into your app** (e.g., Linear) in the opened browser
4. Login credentials are automatically saved for future runs

### Future Runs:
You'll be automatically logged in! Just run the script as normal.

**📖 See [SETUP_LINEAR.md](SETUP_LINEAR.md) for detailed Linear setup instructions.**

## 🏗️ Project Structure

```
softlight/
├── agent/
│   ├── executor_agent.py      # Agent A (observes & executes)
│   └── instructor_agent.py    # Agent B (instructs & guides)
├── browserController/
│   └── browser_controller.py  # Playwright automation
├── domProcessor/
│   └── dom_serializer.py      # HTML simplification
├── capture/
│   └── screenshot_manager.py  # Screenshot handling
├── dataset/
│   └── dataset_manager.py     # Dataset organization
├── orchestrator.py            # Agent A ↔ B coordination
├── main.py                    # Main entry point
└── cli.py                     # Command-line interface

examples/
└── task_questions.json        # Example tasks

datasets/                      # Output directory
└── [task_id]/
    ├── metadata.json
    └── step_*.png
```

## 🎮 CLI Commands

### Run Single Task

```bash
python -m softlight.cli run "Your question here" \
  --url "https://example.com" \
  --app "AppName"
```

### Batch Processing

```bash
# Use provided examples
python -m softlight.cli batch --tasks examples/task_questions.json

# Use custom tasks file
python -m softlight.cli batch --tasks my_tasks.json
```

### Generate Summary

```bash
# Default location
python -m softlight.cli summarize

# Custom location
python -m softlight.cli summarize --dataset path/to/datasets
```

## 🔧 How It Works

### Step-by-Step Process

1. **Initialization**
   - Agent B receives user's question
   - Browser navigates to starting URL
   - Agent A captures initial screenshot

2. **Observation Loop**
   ```
   Agent A: "I see a search box (bid=5), button (bid=10)..."
   Agent B: "Type 'Softlight' in search box (bid=5)"
   Agent A: Executes → Captures → "Typed successfully, suggestions appeared..."
   Agent B: "Click the search button (bid=10)"
   ... continues ...
   ```

3. **Completion**
   - Agent B recognizes task is done
   - Sends "TASK_COMPLETE" signal
   - Dataset is saved with all screenshots and metadata

### Key Technologies

- **LangChain + OpenAI GPT-4o**: Multi-modal AI for vision and reasoning
- **Playwright**: Browser automation
- **BeautifulSoup**: HTML parsing
- **Click**: CLI interface
- **Structlog**: Structured logging

## 📊 Example Tasks

The system comes with 5 pre-configured example tasks:

1. **Google Search** (3-4 steps)
2. **Linear: Create Project** (5-7 steps)
3. **Linear: Filter Issues** (3-5 steps)
4. **Linear: Assign Issue** (4-6 steps)
5. **Linear: Create Label** (3-5 steps)

Edit `examples/task_questions.json` to add your own tasks!

## 🐛 Troubleshooting

### Playwright Errors
```bash
playwright install chromium
```

### OpenAI API Errors
- Check your API key in `.env`
- Verify you have credits
- Try increasing `MAX_STEPS` if tasks timeout

### Actions Failing
- Use `HEADLESS_MODE=false` to watch the browser
- Increase `MAX_ACTION_RETRIES` in settings
- Check browser console for JavaScript errors

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Support for more complex actions (drag-drop, hover)
- Multi-page navigation
- Session management
- Cost tracking
- More example tasks

## 📝 Assignment Deliverables

This project satisfies the Softlight take-home assignment:

### ✅ Code
Complete two-agent system with:
- Agent A (Executor) and Agent B (Instructor)
- Automatic UI state capture
- Generalizable across different apps
- No hardcoded workflows

### ✅ Dataset
5 captured workflows for Linear:
- Organized by task in `datasets/`
- Screenshots + metadata for each
- Full conversation history preserved

### ✅ Documentation
- This README with architecture explanation
- Code comments and docstrings
- Example usage and CLI commands

## 🎥 Demo Video

Record a Loom showing:
1. Running a task: `python softlight/main.py`
2. Agent A and Agent B conversation in terminal
3. Generated dataset with screenshots
4. Explain the two-agent architecture

## 📈 Performance

- **Speed**: ~3-5 seconds per action
- **Accuracy**: Depends on page complexity and GPT-4o
- **Cost**: ~$0.05-0.15 per task (varies with steps)

## 🔮 Future Enhancements

- [ ] Visual element highlighting in screenshots
- [ ] Multi-tab/window support
- [ ] Error recovery strategies
- [ ] Parallel task execution
- [ ] Web API for remote execution
- [ ] Support for authentication flows
- [ ] Database integration for large-scale datasets

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

- **OpenAI GPT-4o** - Multi-modal AI capabilities
- **Playwright** - Reliable browser automation
- **LangChain** - AI orchestration framework

---

**Built for the Softlight Engineering Assignment**

*Demonstrating how AI agents can automatically create UI workflow documentation*
