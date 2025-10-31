# executor_agent.py - Agent A (Executor)
import base64
from typing import Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from softlight.core.config.env import Settings
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


class ExecutorAgent:
    """
    Agent A - The Executor Agent
    
    Responsibilities:
    - Observes web pages and reports what it sees
    - Executes instructions from Agent B (Instructor)
    - Reports results of actions clearly
    - Captures UI state information
    """
    
    def __init__(self, browser_controller):
        self.browser = browser_controller
        self.llm = ChatOpenAI(
            model=Settings.AGENT_A_MODEL,
            api_key=Settings.OPENAI_API_KEY,
            max_tokens=Settings.AGENT_A_MAX_TOKENS
        )
        self.system_prompt = """
You are Agent A, an executor agent that observes web pages and executes instructions.

Your responsibilities:
1. OBSERVE: Look at the page and describe what you see in detail
2. REPORT: Tell Agent B about all interactive elements with their bid numbers
3. EXECUTE: Follow Agent B's instructions precisely
4. CONFIRM: Report what happened after each action

When observing, describe:
- All interactive elements (buttons, links, inputs) with their bid numbers
- Current page state and layout
- Any visible text, forms, or modals
- What actions seem possible

When reporting execution results:
- Exactly what action you performed
- What happened immediately after
- New elements that appeared or disappeared
- Any errors or unexpected behavior

Be thorough, precise, and always reference bid numbers from the DOM.
"""
    
    def observe_and_report(self, screenshot_b64: str, serialized_dom: str, step_num: int) -> str:
        """
        Observe the current page state and report observations to Agent B.
        
        Args:
            screenshot_b64: Base64 encoded screenshot
            serialized_dom: Simplified DOM with bid numbers
            step_num: Current step number
            
        Returns:
            Detailed observation report as string
        """
        prompt = f"""
Current page state (Step {step_num}):

Simplified DOM with interactive elements:
{serialized_dom}

Please observe the screenshot and the DOM, then provide a detailed report of:
1. What page/screen you're on
2. All visible interactive elements with their bid numbers
3. The current state of the page
4. What actions appear to be available

Be specific and mention bid numbers for elements you see.
"""
        
        message = HumanMessage(
            content=[
                {"type": "text", "text": self.system_prompt + "\n\n" + prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}},
            ]
        )
        
        logger.debug("Agent A observing page", step=step_num)
        response = self.llm.invoke([message])
        observation = response.content.strip()
        
        logger.info("Agent A observation", step=step_num, observation=observation[:200])
        return observation
    
    def execute_instruction(self, instruction: str, serialized_dom: str) -> Dict[str, any]:
        """
        Execute Agent B's instruction and report the result.
        
        Args:
            instruction: Instruction from Agent B
            serialized_dom: Current DOM for action execution
            
        Returns:
            Dict with success, action taken, and result description
        """
        logger.info("Agent A executing instruction", instruction=instruction)
        
        # Parse the instruction to extract the action
        action = self._extract_action_from_instruction(instruction, serialized_dom)
        
        if not action:
            return {
                "success": False,
                "action": "NONE",
                "result": f"Could not understand instruction: {instruction}"
            }
        
        # Execute the action using browser controller
        try:
            success = self.browser.execute_action(action)
            
            if success:
                result_desc = self._describe_action_result(action)
                return {
                    "success": True,
                    "action": action,
                    "result": result_desc
                }
            else:
                return {
                    "success": False,
                    "action": action,
                    "result": "Action failed to execute"
                }
                
        except Exception as e:
            logger.error("Agent A execution error", error=str(e), instruction=instruction)
            return {
                "success": False,
                "action": action,
                "result": f"Error: {str(e)}"
            }
    
    def _extract_action_from_instruction(self, instruction: str, serialized_dom: str) -> str:
        """
        Parse Agent B's natural language instruction into an executable action.
        
        Args:
            instruction: Natural language instruction from Agent B
            serialized_dom: Current DOM to understand context
            
        Returns:
            Action string like "CLICK 5" or "TYPE 3 'search term'"
        """
        # Use LLM to convert natural language instruction to action
        prompt = f"""
Agent B gave this instruction: "{instruction}"

Available elements:
{serialized_dom}

Convert this instruction into ONE executable action command. Use ONLY these formats:
- CLICK <bid>
- TYPE <bid> "<text>"
- SCROLL UP or SCROLL DOWN
- WAIT

Respond with ONLY the action command, nothing else.
"""
        
        message = HumanMessage(content=[{"type": "text", "text": prompt}])
        response = self.llm.invoke([message])
        action = response.content.strip()
        
        logger.debug("Extracted action", instruction=instruction, action=action)
        return action
    
    def _describe_action_result(self, action: str) -> str:
        """
        Generate a description of what happened after performing an action.
        
        Args:
            action: The action that was performed
            
        Returns:
            Human-readable description of the result
        """
        parts = action.split(" ", 2)
        action_type = parts[0].upper()
        
        if action_type == "CLICK":
            return f"Clicked element with bid={parts[1]}. Waiting for page response..."
        elif action_type == "TYPE":
            text = parts[2].strip('"\'') if len(parts) > 2 else ""
            return f"Typed '{text}' into element with bid={parts[1]}. Pressed Enter."
        elif action_type == "SCROLL":
            direction = parts[1] if len(parts) > 1 else "DOWN"
            return f"Scrolled {direction}."
        elif action_type == "WAIT":
            return "Waited 2 seconds for page to load."
        else:
            return f"Executed action: {action}"

