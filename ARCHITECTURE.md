# Softlight Architecture - Hybrid DOM + Vision System

## Overview

Softlight uses a hybrid approach that combines **DOM selectors** (stable, semantic) with **vision-based coordinates** (flexible, works everywhere).

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User Task                            │
│  "Create a new issue named 'Test Issue'"                    │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                    1. PERCEPTION                             │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│   │ DOM Extract  │  │  Page Text   │  │  Screenshot  │    │
│   │ (64 elements)│  │ (1250 chars) │  │  (1280x720)  │    │
│   └──────────────┘  └──────────────┘  └──────────────┘    │
│                            ↓                                 │
│                      PageState                               │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                    2. DECISION                               │
│              HybridInstructor (Agent B)                      │
│                   GPT-4o Analysis                            │
│                                                              │
│  Input:  DOM elements + page text + screenshot              │
│  Output: {"action": "CLICK", "bid": "13", "x": 640, "y": 120}│
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                    3. EXECUTION                              │
│              SimpleExecutor (Agent A)                        │
│                Playwright Automation                         │
│                                                              │
│  Strategy (Selector-First):                                 │
│  1. Try: [data-bid="13"]                 ✅ Fast & stable   │
│  2. Try: button[aria-label="Create"]     ✅ Semantic        │
│  3. Try: #submit-button                  ✅ By ID           │
│  4. Fallback: click(640, 120)            🟡 Coordinates     │
│                                                              │
│  Returns: {"success": true, "method": "data-bid"}           │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
                   Wait 1.5s
                        ↓
                Capture New State
                        ↓
                  Repeat Until Done
```

## Core Components

### 1. DOM Extraction Layer

**File**: `softlight/domProcessor/dom_extractor.py`

Extracts actionable elements from HTML:

```python
# Finds these element types
INTERACTIVE_TAGS = ["button", "input", "textarea", "select", "a"]

# Extracts these attributes
- role (button, textbox, link, etc.)
- aria_label (screen reader text)
- placeholder (input hints)
- name (form field names)
- id (unique identifiers)
- text (visible text content)
```

**Output**: List of `ElementInfo` objects with semantic attributes

### 2. Element Representation

**File**: `softlight/domProcessor/element_info.py`

Each element contains:

```python
@dataclass
class ElementInfo:
    bid: str              # Unique ID (1, 2, 3...)
    tag: str              # HTML tag (button, input)
    role: str             # ARIA role
    text: str             # Visible text
    aria_label: str       # Accessibility label
    placeholder: str      # Input placeholder
    name: str             # Form name
    id: str               # Element ID
    selector: str         # Generated CSS selector
```

### 3. Page State Management

**File**: `softlight/state/page_state.py`

Combines all perception inputs:

```python
@dataclass
class PageState:
    elements: List[ElementInfo]  # Extracted DOM elements
    page_text: str               # Visible page content
    screenshot_path: str         # Path to screenshot
    url: str                     # Current URL
    title: str                   # Page title
    html: str                    # Full HTML
```

**Critical Feature**: Injects `data-bid` attributes into actual DOM:

```javascript
// Injected into page
<button data-bid="13">Create Issue</button>
```

This allows stable selector targeting: `[data-bid="13"]`

### 4. Hybrid Instructor (Agent B)

**File**: `softlight/agent/hybrid_instructor.py`

- **Input**: PageState (DOM + text + screenshot)
- **Model**: OpenAI GPT-4o
- **Output**: Action with bid + coordinate fallback

```json
{
  "action": "CLICK",
  "bid": "13",
  "x": 640,
  "y": 120,
  "reasoning": "Click 'Create new issue' button"
}
```

### 5. Simple Executor (Agent A)

**File**: `softlight/agent/simple_executor.py`

Executes actions using Playwright with fallback strategy:

```python
def execute_action(action, page_state):
    if action["bid"]:
        # 1. Try data-bid selector
        page.click(f'[data-bid="{bid}"]')
        
        # 2. Try semantic selectors
        page.get_by_role("button", name=aria_label).click()
        
        # 3. Try other attributes (name, id, text)
        
        # 4. Fallback to coordinates
        page.mouse.click(x, y)
    
    return {"success": True, "method": "data-bid"}
```

### 6. Browser Actions

**File**: `softlight/actions/browser_actions.py`

Pure Playwright action primitives:

```python
class BrowserActions:
    def click_coordinate(x, y)
    def type_text(text, x, y)
    def press_key(key)
    def scroll(direction, amount)
    def click_element_hybrid(bid, element_info, x, y)  # Selector-first
    def type_element_hybrid(text, bid, element_info, x, y)
```

### 7. Orchestration

**File**: `softlight/orchestrator_hybrid.py`

Main control loop:

```python
def run_task(question, url, app_name):
    # 1. Navigate to URL
    browser.navigate(url)
    
    # 2. Initialize agents
    agent_a = SimpleExecutor(browser)
    agent_b = HybridInstructor()
    
    # 3. Main loop
    for step in range(max_steps):
        # Build page state
        page_state = build_page_state(page, screenshot_path)
        
        # Agent B decides
        action = agent_b.provide_action(page_state, step)
        
        # Agent A executes
        result = agent_a.execute_action(action, page_state)
        
        if action["action"] == "TASK_COMPLETE":
            break
        
        # Wait for page to settle
        time.sleep(1.5)
```

## Key Design Decisions

### 1. Why Inject data-bid Attributes?

**Problem**: Generated selectors might not be unique or might fail
**Solution**: Inject unique `data-bid` into actual DOM after extraction

```python
# In page_state.py
def _inject_bids_into_dom(page, elements):
    for elem in elements:
        # Use multiple selector strategies
        selectors = [f"#{elem.id}", f"[name='{elem.name}']", elem.selector]
        
        # Try each until one works
        for selector in selectors:
            elem = page.querySelector(selector)
            if elem:
                elem.setAttribute('data-bid', bid)
                break
```

**Benefit**: `[data-bid="13"]` is guaranteed unique and fast

### 2. Why Selector-First Strategy?

**Stability**: DOM selectors don't break with:
- Layout changes
- CSS updates  
- Screen resolution changes
- Zoom levels

**Speed**: Direct selector lookup is faster than coordinate analysis

**Debugging**: Logs show which method worked:
```
✅ CLICK successful (method: role+aria-label)
✅ TYPE successful (method: placeholder)
✅ CLICK successful (method: coordinates)  # Fallback
```

### 3. Why Keep Coordinate Fallback?

**Icons**: No text/label to target
**Canvas**: Custom UI elements without DOM
**Shadow DOM**: Encapsulated components
**Dynamic**: Elements that change attributes

## Execution Method Priority

1. **data-bid** - Fastest, most stable (injected unique ID)
2. **role+aria-label** - Semantic, accessibility-first
3. **aria-label** - Label alone
4. **name** - Form field names
5. **id** - Element IDs (if unique)
6. **placeholder** - Input hints
7. **text** - Text content matching
8. **coordinates** - Pixel position fallback

## Data Flow Example

### Task: "Create a new issue named 'Test Issue'"

```
Step 1: Extract DOM
├─ Found 64 elements
├─ Element 13: button[aria-label="Create new issue"]
└─ Injected [data-bid="13"] into DOM

Step 2: Agent B Analyzes
├─ Input: 64 elements + page text + screenshot
├─ Decision: Click button bid=13
└─ Output: {"action": "CLICK", "bid": "13", "reasoning": "..."}

Step 3: Agent A Executes
├─ Try: page.click('[data-bid="13"]')
├─ Success! ✅
└─ Log: method=data-bid

Step 4: Wait & Capture New State
├─ Modal opened
├─ Found input field bid=5
└─ Ready for next action

Step 5: Agent B Decides
└─ Output: {"action": "TYPE", "bid": "5", "text": "Test Issue"}

Step 6: Agent A Executes
├─ Try: page.fill('[data-bid="5"]', text)
├─ Success! ✅
└─ Log: method=data-bid

... continues until TASK_COMPLETE
```

## Comparison: Hybrid vs Vision Mode

| Aspect | Hybrid Mode | Vision Mode |
|--------|------------|-------------|
| **Perception** | DOM + Text + Screenshot | Screenshot only |
| **Primary Method** | DOM selectors | Coordinates |
| **Fallback** | Coordinates | None |
| **Stability** | High | Medium |
| **Speed** | Fast (selector lookup) | Slower (vision analysis) |
| **Canvas/Icons** | Falls back to coords | Native support |
| **Debugging** | Easy (see methods) | Harder |
| **Cost per step** | ~$0.02 | ~$0.03 |

## Error Handling

### Selector Injection Failures

```python
# If selector fails to find element
try:
    elem = page.querySelector(selector)
    if elem:
        elem.setAttribute('data-bid', bid)
except:
    # Skip silently - will use alternative selectors
    pass
```

Result: System tries multiple selectors, falls back to coordinates

### Action Execution Failures

```python
# Timeout on data-bid
✅ Try aria-label selector
✅ Try name attribute
✅ Try text matching
🟡 Fallback to coordinates
```

All failures are logged with error details

## Performance Characteristics

- **DOM Extraction**: ~100ms for 100 elements
- **Bid Injection**: ~50ms for 64 elements
- **Selector Click**: ~200ms
- **Coordinate Click**: ~300ms
- **Total per step**: ~2-3 seconds (hybrid) vs ~4-5 seconds (vision)

## Future Enhancements

1. **Visibility Detection**: Filter out hidden elements before extraction
2. **Bounding Boxes**: Extract element coordinates from browser
3. **Selector Caching**: Remember successful selectors per element type
4. **Multi-element Selection**: Handle lists and grids
5. **Shadow DOM Support**: Penetrate web component boundaries

## References

- **browser-use**: Inspiration for hybrid DOM + vision approach
- **Playwright**: Browser automation framework
- **OpenAI GPT-4o**: Vision + reasoning capabilities

---

**Architecture Summary**

Softlight combines the best of both worlds:
- 🎯 Stable DOM selectors for reliability
- 🔄 Coordinate fallback for flexibility
- 📊 Observable execution for debugging
- 🚀 Fast and cost-effective automation

