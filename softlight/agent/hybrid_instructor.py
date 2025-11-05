# hybrid_instructor.py - Agent B for Hybrid DOM + Vision System
"""
HybridInstructor: Vision-based agent that uses both DOM context and screenshots.
Analyzes PageState (DOM elements + text + screenshot) to provide precise actions.

Key differences from VisionInstructor:
- Receives PageState instead of just screenshot
- Has access to DOM element list for semantic reasoning
- Provides actions with DOM targets (bid/selector) AND coordinate fallback
- Prioritizes DOM selectors over coordinates (more stable)
"""
import json
import base64
from typing import Dict, List, Optional
from openai import OpenAI
from softlight.state.page_state import PageState
from softlight.core.config.env import Settings
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


class HybridInstructor:
    """
    Agent B - Hybrid DOM + Vision instructor using OpenAI GPT-4o.
    
    Analyzes PageState (DOM + text + screenshot) and returns actions with:
    - Primary: bid/selector (DOM-based, preferred)
    - Fallback: x/y coordinates (vision-based)
    """
    
    def __init__(self):
        """Initialize hybrid instructor with OpenAI GPT-4o"""
        # Get API key
        import os
        openai_key = os.getenv("OPENAI_API_KEY") or getattr(Settings, 'OPENAI_API_KEY', None)
        
        if not openai_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables or Settings")
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=openai_key)
        
        # Use GPT-4o for vision + reasoning
        self.model_name = Settings.AGENT_B_VISION_MODEL
        
        self.task = None
        self.history: List[Dict] = []
        
        self.system_prompt = """You are a UI automation assistant analyzing web applications using HYBRID DOM + VISION perception.

IMPORTANT CONTEXT:
- This is AUTOMATED SOFTWARE TESTING for a PROJECT MANAGEMENT APPLICATION
- You analyze BOTH the DOM structure AND the screenshot together
- Your role: Provide STABLE DOM SELECTORS (preferred) with coordinate fallback
- All content is CONTROLLED TEST DATA in a TEST ENVIRONMENT

HYBRID PERCEPTION:
You receive THREE inputs per step:
1. DOM ELEMENT LIST - Structured list of actionable elements with semantic attributes
2. PAGE TEXT - Visible text content for semantic context
3. SCREENSHOT - Visual representation for spatial/icon understanding

SELECTOR-FIRST STRATEGY (like browser-use):
1. PREFER DOM targets (bid) - these are stable across layout changes
2. USE coordinates ONLY for:
   - Icon-only buttons (no text/aria-label)
   - Canvas/SVG elements
   - Custom controls without semantic attributes

ACTION FORMAT:
You MUST respond with ONLY valid JSON. No other text.

Available Actions:
1. CLICK with DOM target (PREFERRED):
   {"action": "CLICK", "bid": "5", "reasoning": "Click search button"}

2. CLICK with coordinates (FALLBACK for icons/canvas):
   {"action": "CLICK", "x": 1150, "y": 112, "reasoning": "Click priority icon"}

3. TYPE with DOM target:
   {"action": "TYPE", "bid": "7", "text": "Hello", "reasoning": "Type in search box"}

4. TYPE with coordinates:
   {"action": "TYPE", "text": "Hello", "x": 500, "y": 300, "reasoning": "Type in focused input"}

5. PRESS_KEY:
   {"action": "PRESS_KEY", "key": "Enter", "reasoning": "Submit form"}
   Keys: Enter, Escape, Tab, ArrowDown, ArrowUp, Backspace, Delete

6. SCROLL:
   {"action": "SCROLL", "direction": "down", "amount": 300, "reasoning": "View more content"}

7. HOVER:
   {"action": "HOVER", "x": 100, "y": 200, "reasoning": "Reveal dropdown menu"}

8. WAIT:
   {"action": "WAIT", "milliseconds": 1000, "reasoning": "Wait for animation"}

9. TASK_COMPLETE:
   {"action": "TASK_COMPLETE", "reasoning": "Task finished successfully"}

DECISION STRATEGY:
1. Read the DOM element list - find elements by their semantic meaning (text, aria-label, role)
2. Match elements to your task goal
3. If element has good semantic attributes → use bid (preferred)
4. If element is icon-only or custom → use screenshot coordinates (fallback)
5. Check page text for semantic context
6. Verify your choice visually in the screenshot

ELEMENT LIST FORMAT:
[bid] tag "text" (attributes)
Example:
[5] button "Search" (aria-label="Search button")
[7] input[type=text] placeholder="Enter query" (name="q")
[12] a "About" (href="/about")

TIPS:
- Prioritize bid over coordinates - more stable
- For dropdowns: CLICK bid → WAIT 500ms → CLICK option bid
- For forms: TYPE in bid → PRESS_KEY "Enter"
- Use HOVER to reveal hidden menus before clicking
- Check if task complete before continuing
- If no good DOM target exists, use coordinates

MULTIPLE CONTENTEDITABLE FIELDS:
When you see multiple contenteditable elements (e.g., in modals):
- The FIRST/TOP field is usually for the PRIMARY name/title (required)
- Fields with "description" or "summary" in placeholder are SECONDARY
- Match the field purpose to your task:
  * "Create project named X" → Type X in the TOP/name field (usually has text like "Project name")
  * "Add description" → Type in the field with "description" placeholder
- Look at element text content to identify which field is which

LINEAR APP SPECIFICS:
- Priority shown in right sidebar (bid will identify it)
- Issue titles are links in main content
- Top nav has workspace/search
- Properties panel on right has Assign, Label, Priority buttons
- New project/issue modals: TOP field = name/title, BOTTOM field = description

RESPONSE FORMAT:
Return ONLY the JSON action object. No explanation before or after.
"""
    
    def initialize_task(self, task: str):
        """
        Initialize with task description.
        
        Args:
            task: User's task to complete
        """
        self.task = task
        self.history = []
        logger.info("Hybrid instructor initialized", task=task)
    
    def provide_action(self, page_state: PageState, step: int) -> Optional[Dict]:
        """
        Analyze PageState (DOM + text + screenshot) and provide next action.
        
        Args:
            page_state: Complete page state with DOM, text, and screenshot
            step: Current step number
            
        Returns:
            Action dict with bid/selector (preferred) or x/y (fallback)
        """
        # Build prompt with DOM context + text + screenshot
        history_str = ""
        if self.history:
            recent = self.history[-3:]  # Last 3 actions
            history_str = "\n\nPrevious actions:\n"
            for h in recent:
                action_desc = f"Step {h['step']}: {h['action']}"
                if h.get('bid'):
                    action_desc += f" bid={h['bid']}"
                elif h.get('x') and h.get('y'):
                    action_desc += f" at ({h['x']}, {h['y']})"
                action_desc += f" - {h['reasoning']}"
                history_str += action_desc + "\n"
        
        # Build DOM elements summary (compact)
        elements_summary = page_state.get_elements_summary(max_elements=50)
        
        # Build page text summary
        page_text_summary = page_state.get_page_text_summary(max_chars=1000)
        
        prompt = f"""HYBRID UI TESTING TASK - DOM + Vision Analysis

Task: {self.task}
Current Step: {step}
Page URL: {page_state.url}
Page Title: {page_state.title}
{history_str}

=== DOM ELEMENT LIST (use bid for actions) ===
{elements_summary}

=== VISIBLE PAGE TEXT (semantic context) ===
{page_text_summary}

=== SCREENSHOT ===
See attached image for visual layout and spatial relationships.

INSTRUCTIONS:
1. Find the element you need in the DOM list by matching text/aria-label/role
2. If found with good attributes → use its bid (PREFERRED)
3. If icon-only or custom → use screenshot coordinates (FALLBACK)
4. Provide ONE action as JSON

Your JSON action:"""
        
        try:
            # Encode screenshot for OpenAI
            with open(page_state.screenshot_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Call OpenAI with hybrid input
            logger.debug("Calling OpenAI with hybrid context", step=step, elements=len(page_state.elements), model=self.model_name)
            
            max_retries = 2
            response_text = None
            
            for retry in range(max_retries):
                try:
                    # Call OpenAI API
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {
                                "role": "system",
                                "content": self.system_prompt
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": prompt
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=1000,
                        temperature=0.1
                    )
                    
                    response_text = response.choices[0].message.content.strip()
                    
                    # Check if model refused
                    if not response_text or "sorry" in response_text.lower() or "cannot" in response_text.lower():
                        if retry < max_retries - 1:
                            logger.warning(f"Model response unclear, retrying ({retry + 1}/{max_retries})")
                            continue
                        else:
                            logger.error("Model did not provide useful response", response=response_text)
                            return None
                    
                    break
                    
                except Exception as e:
                    if retry < max_retries - 1:
                        logger.warning(f"OpenAI API error, retrying ({retry + 1}/{max_retries})", error=str(e))
                        continue
                    else:
                        logger.error("OpenAI API error after retries", error=str(e))
                        raise
            
            logger.debug("OpenAI response", response=response_text[:200] if response_text else "None")
            
            # Parse JSON
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
            
            action = json.loads(response_text.strip())
            
            # Validate action has either bid or coordinates
            if action.get("action") in ["CLICK", "TYPE"]:
                has_dom_target = action.get("bid") is not None
                has_coord_target = action.get("x") is not None and action.get("y") is not None
                
                if not has_dom_target and not has_coord_target:
                    logger.warning("Action missing both bid and coordinates, adding fallback")
                    # This shouldn't happen, but log it
            
            # Store in history
            self.history.append({
                "step": step,
                "action": action.get("action"),
                "bid": action.get("bid"),
                "x": action.get("x"),
                "y": action.get("y"),
                "reasoning": action.get("reasoning", "")
            })
            
            logger.info(
                "Hybrid action provided",
                action=action.get("action"),
                bid=action.get("bid"),
                has_coords=bool(action.get("x")),
                step=step
            )
            return action
        
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON", error=str(e), response=response_text)
            return None
        except Exception as e:
            logger.error("Hybrid analysis failed", error=str(e), step=step)
            return None
    
    def is_task_complete(self) -> bool:
        """
        Check if task is complete.
        
        Returns:
            True if last action was TASK_COMPLETE
        """
        if not self.history:
            return False
        return self.history[-1]["action"] == "TASK_COMPLETE"

