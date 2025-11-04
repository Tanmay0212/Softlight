# vision_instructor.py - Agent B (Vision-based with OpenAI)
"""
Agent B: Vision-based instructor using OpenAI GPT-4o.
Analyzes screenshots and returns precise actions with pixel coordinates.
"""
import json
import base64
from typing import Dict, List, Optional
from openai import OpenAI
from softlight.core.config.env import Settings
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


class VisionInstructor:
    """Agent B - Analyzes screenshots and provides precise actions"""
    
    def __init__(self):
        """Initialize vision instructor with OpenAI GPT-4o"""
        # Get API key
        import os
        openai_key = os.getenv("OPENAI_API_KEY") or getattr(Settings, 'OPENAI_API_KEY', None)
        
        if not openai_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables or Settings")
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=openai_key)
        
        # Use GPT-4o for vision capabilities
        self.model_name = Settings.AGENT_B_VISION_MODEL
        
        self.task = None
        self.history: List[Dict] = []
        
        self.system_prompt = """You are a UI automation testing assistant analyzing application screenshots.

IMPORTANT CONTEXT:
- This is an AUTOMATED SOFTWARE TESTING scenario
- You are analyzing a PROJECT MANAGEMENT WEB APPLICATION interface
- Your role is to provide PIXEL COORDINATES for automated testing scripts
- All visible content is part of a CONTROLLED TEST ENVIRONMENT
- NO personal or sensitive data is involved - this is TEST DATA ONLY

Your job: Provide precise pixel coordinates for UI automation testing.

CRITICAL: You MUST respond with ONLY valid JSON. No other text.

Available Actions:
1. CLICK - Click at coordinates
   {"action": "CLICK", "x": 1150, "y": 112, "reasoning": "Click 'Low' priority"}

2. TYPE - Type text (optionally click first)
   {"action": "TYPE", "text": "Hello", "x": 500, "y": 300, "reasoning": "Type in search box"}
   {"action": "TYPE", "text": "Hello", "reasoning": "Type in focused input"}

3. PRESS_KEY - Press keyboard key
   {"action": "PRESS_KEY", "key": "Enter", "reasoning": "Submit form"}
   Keys: Enter, Escape, Tab, ArrowDown, ArrowUp, Backspace, Delete

4. SCROLL - Scroll page
   {"action": "SCROLL", "direction": "down", "amount": 300, "reasoning": "View more content"}

5. HOVER - Hover over element (reveals menus/tooltips)
   {"action": "HOVER", "x": 100, "y": 200, "reasoning": "Reveal dropdown menu"}

6. WAIT - Wait for page to update
   {"action": "WAIT", "milliseconds": 1000, "reasoning": "Wait for animation"}

7. TASK_COMPLETE - Task is finished
   {"action": "TASK_COMPLETE", "reasoning": "Priority changed successfully"}

COORDINATE SYSTEM:
- (0, 0) is top-left corner
- X increases going RIGHT
- Y increases going DOWN
- Look at the screenshot carefully to determine exact pixel positions
- Aim for CENTER of clickable elements

STRATEGY:
1. Look at the screenshot and identify what needs to be done
2. Find the EXACT visual location of the element to interact with
3. Provide pixel-perfect coordinates
4. For inputs, click them first, then type
5. For dropdowns: CLICK button → WAIT 500ms → CLICK option
6. Check if task is complete before continuing

TIPS:
- Be precise with coordinates - aim for CENTER of clickable elements
- For text inputs, click center of the input box first
- Wait after actions that trigger UI changes (dropdowns, modals)
- Use HOVER to reveal hidden menus before clicking
- Press Enter after typing in forms
- If a dropdown opens, wait a moment before clicking an option

LINEAR APP SPECIFICS:
- Priority shown in right sidebar as text (e.g., "Low", "Medium", "High")
- Click the priority text to open dropdown, then click desired priority
- Issue titles are clickable links in the main content area
- Top navigation has workspace selector and search

RESPONSE FORMAT:
Return ONLY the JSON action object. No explanation before or after. Just pure JSON.
"""
    
    def initialize_task(self, task: str):
        """
        Initialize with task description.
        
        Args:
            task: User's task to complete
        """
        self.task = task
        self.history = []
        logger.info("Vision instructor initialized", task=task)
    
    def _encode_image(self, image_path: str) -> str:
        """
        Encode image to base64 for OpenAI.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded string
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def provide_action(self, screenshot_path: str, step: int) -> Optional[Dict]:
        """
        Analyze screenshot and provide next action.
        
        Args:
            screenshot_path: Path to current screenshot
            step: Current step number
            
        Returns:
            Action dict or None if failed
        """
        # Build prompt with history
        history_str = ""
        if self.history:
            recent = self.history[-3:]  # Last 3 actions
            history_str = "\n\nPrevious actions:\n"
            for h in recent:
                history_str += f"Step {h['step']}: {h['action']}"
                if h.get('x') and h.get('y'):
                    history_str += f" at ({h['x']}, {h['y']})"
                history_str += f" - {h['reasoning']}\n"
        
        prompt = f"""AUTOMATED UI TESTING TASK - Quality Assurance Scenario

Task: {self.task}
Current Step: {step}
{history_str}
This is a controlled testing environment for a project management application.
Analyze the screenshot carefully and provide the NEXT action as JSON to complete the test.

IMPORTANT PAGE LAYOUT UNDERSTANDING:
- Left sidebar (x=0-250): Navigation menu (Inbox, Projects, Views, etc.)
- Main content area (x=250-1000): Issue list, project details, forms
- Right sidebar "Properties" panel (x=1050-1280): Todo, Priority, Assign, Labels, Project
  * "Assign" button is near top of Properties panel (around y=150)
  * "Add label" button is below "Assign" (around y=230)
  * Make sure to click the CORRECT button based on the task!
- When looking for issues, search in the MAIN CONTENT AREA (center of screen), NOT the left sidebar
- Issue titles are typically around x=350-700

CRITICAL INSTRUCTIONS:
1. Provide exact X,Y pixel coordinates for the next UI interaction
2. Look at WHAT CHANGED since the previous step:
   - If a dropdown appeared, you may need to select from it OR close it if it's wrong
   - If nothing changed, your previous click missed the target - try different coordinates
   - Don't keep clicking the same spot if it's not working!
3. If you see a dropdown that's NOT related to your current goal, press Escape to close it first
4. Be VERY precise with Y coordinates in the right sidebar - buttons are close together
5. One action per response
6. Respond with ONLY valid JSON, no other text

Your JSON action:"""
        
        try:
            # Encode image for OpenAI
            base64_image = self._encode_image(screenshot_path)
            
            # Call OpenAI with vision
            logger.debug("Calling OpenAI vision model", step=step, model=self.model_name)
            
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
                    
                    # Success
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
            # Sometimes the model adds markdown code blocks, strip them
            if response_text.startswith("```"):
                # Remove ```json and ``` markers
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
            
            action = json.loads(response_text.strip())
            
            # Check for stuck loop - same action repeated
            if len(self.history) >= 2:
                last_two = self.history[-2:]
                if (last_two[0].get("action") == action.get("action") and 
                    last_two[0].get("reasoning") == action.get("reasoning")):
                    logger.warning("Detected repeated action - model might be stuck")
                    # Add warning to next prompt
                    action["_warning"] = "Previous action repeated - try different coordinates or approach"
            
            # Store in history
            self.history.append({
                "step": step,
                "action": action.get("action"),
                "x": action.get("x"),
                "y": action.get("y"),
                "reasoning": action.get("reasoning", "")
            })
            
            logger.info("Vision action provided", action=action.get("action"), step=step)
            return action
        
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON", error=str(e), response=response_text)
            return None
        except Exception as e:
            logger.error("Vision analysis failed", error=str(e), step=step)
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

