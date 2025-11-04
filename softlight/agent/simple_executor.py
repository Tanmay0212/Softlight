# simple_executor.py - Agent A (No LLM, just execution)
"""
Agent A: Simple executor with no intelligence.
Just executes actions given by Agent B.
"""
from softlight.actions.browser_actions import BrowserActions
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


class SimpleExecutor:
    """Agent A - Executes actions with no intelligence"""
    
    def __init__(self, browser_controller):
        """
        Initialize executor with browser controller.
        
        Args:
            browser_controller: BrowserController instance
        """
        self.browser = browser_controller
        self.actions = BrowserActions(browser_controller.page)
    
    def execute_action(self, action_command: dict, page_state=None) -> dict:
        """
        Execute a single action command from Agent B.
        
        Supports both vision-only mode (coordinates) and hybrid mode (bid + coordinates).
        
        Args:
            action_command: {
                "action": "CLICK" | "TYPE" | "PRESS_KEY" | "SCROLL" | "HOVER" | "WAIT" | "TASK_COMPLETE",
                "bid": str (for hybrid mode - DOM element ID),
                "x": int (coordinates - fallback or vision mode),
                "y": int (coordinates - fallback or vision mode),
                "text": str (for type),
                "key": str (for press_key),
                "direction": str (for scroll),
                "amount": int (for scroll),
                "milliseconds": int (for wait),
                "reasoning": str
            }
            page_state: Optional PageState for element lookup in hybrid mode
            
        Returns:
            {
                "success": bool,
                "action": str,
                "error": str or None,
                "method": str (selector type used - for observability)
            }
        """
        action = action_command.get("action")
        
        logger.debug("Executing action", action=action, command=action_command)
        
        # Route to appropriate action handler
        if action == "CLICK":
            # Check if hybrid mode (has bid or page_state)
            if action_command.get("bid") or page_state:
                # Get element info from page_state if available
                element_info = None
                if page_state and action_command.get("bid"):
                    elem = page_state.get_element_by_bid(action_command["bid"])
                    if elem:
                        element_info = elem.to_dict()
                
                # Use hybrid click (selector-first strategy)
                result = self.actions.click_element_hybrid(
                    bid=action_command.get("bid"),
                    element_info=element_info,
                    x=action_command.get("x"),
                    y=action_command.get("y")
                )
            else:
                # Vision-only mode: use coordinates
                result = self.actions.click_coordinate(
                    x=action_command["x"],
                    y=action_command["y"]
                )
                result["method"] = "coordinates"
        
        elif action == "TYPE":
            # Check if hybrid mode
            if action_command.get("bid") or page_state:
                # Get element info from page_state if available
                element_info = None
                if page_state and action_command.get("bid"):
                    elem = page_state.get_element_by_bid(action_command["bid"])
                    if elem:
                        element_info = elem.to_dict()
                
                # Use hybrid type (selector-first strategy)
                result = self.actions.type_element_hybrid(
                    text=action_command["text"],
                    bid=action_command.get("bid"),
                    element_info=element_info,
                    x=action_command.get("x"),
                    y=action_command.get("y")
                )
            else:
                # Vision-only mode: use coordinates
                result = self.actions.type_text(
                    text=action_command["text"],
                    x=action_command.get("x"),
                    y=action_command.get("y")
                )
                result["method"] = "coordinates"
        
        elif action == "PRESS_KEY":
            result = self.actions.press_key(
                key=action_command["key"]
            )
            result["method"] = "keyboard"
        
        elif action == "SCROLL":
            result = self.actions.scroll(
                direction=action_command["direction"],
                amount=action_command.get("amount", 300)
            )
            result["method"] = "scroll"
        
        elif action == "HOVER":
            result = self.actions.hover(
                x=action_command["x"],
                y=action_command["y"]
            )
            result["method"] = "coordinates"
        
        elif action == "WAIT":
            result = self.actions.wait(
                milliseconds=action_command.get("milliseconds", 1000)
            )
            result["method"] = "wait"
        
        elif action == "TASK_COMPLETE":
            result = {"success": True, "error": None, "method": "complete"}
            logger.info("Task marked as complete")
        
        else:
            result = {"success": False, "error": f"Unknown action: {action}", "method": "none"}
            logger.error("Unknown action", action=action)
        
        # Log method used for observability
        if result.get("success") and result.get("method"):
            logger.info(
                "Action executed successfully",
                action=action,
                method=result["method"],
                bid=action_command.get("bid")
            )
        
        return {
            "success": result["success"],
            "action": action,
            "error": result.get("error"),
            "method": result.get("method", "unknown")
        }

