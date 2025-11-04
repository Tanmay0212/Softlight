# browser_actions.py - Pure Playwright action primitives
"""
Browser action executors - no intelligence, just execution.
All methods return {"success": bool, "error": str or None}
"""
from playwright.sync_api import Page
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


class BrowserActions:
    """All available browser actions using Playwright primitives"""
    
    def __init__(self, page: Page):
        """
        Initialize with Playwright page object.
        
        Args:
            page: Playwright Page instance
        """
        self.page = page
    
    def click_coordinate(self, x: int, y: int) -> dict:
        """
        Click at exact pixel coordinates.
        
        Args:
            x: X coordinate (pixels from left)
            y: Y coordinate (pixels from top)
            
        Returns:
            {"success": bool, "error": str or None}
        """
        try:
            # DEBUG: Draw a red circle where we're clicking for 1 second
            self.page.evaluate(f"""
                () => {{
                    const circle = document.createElement('div');
                    circle.style.position = 'fixed';
                    circle.style.left = '{x - 10}px';
                    circle.style.top = '{y - 10}px';
                    circle.style.width = '20px';
                    circle.style.height = '20px';
                    circle.style.borderRadius = '50%';
                    circle.style.border = '3px solid red';
                    circle.style.backgroundColor = 'rgba(255, 0, 0, 0.3)';
                    circle.style.zIndex = '999999';
                    circle.style.pointerEvents = 'none';
                    document.body.appendChild(circle);
                    setTimeout(() => circle.remove(), 1000);
                }}
            """)
            
            # Move mouse to position first, then click
            self.page.mouse.move(x, y)
            self.page.wait_for_timeout(100)
            self.page.mouse.click(x, y)
            
            logger.info("Clicked coordinate", x=x, y=y)
            return {"success": True, "error": None}
        except Exception as e:
            logger.error("Click failed", x=x, y=y, error=str(e))
            return {"success": False, "error": str(e)}
    
    def type_text(self, text: str, x: int = None, y: int = None) -> dict:
        """
        Type text at current focus or at coordinates.
        If coordinates provided, clicks first then types.
        
        Args:
            text: Text to type
            x: Optional X coordinate to click first
            y: Optional Y coordinate to click first
            
        Returns:
            {"success": bool, "error": str or None}
        """
        try:
            # Click at position if coordinates provided
            if x is not None and y is not None:
                self.page.mouse.click(x, y)
                self.page.wait_for_timeout(300)  # Wait for focus
            
            # Type the text with delay between keystrokes
            self.page.keyboard.type(text, delay=50)  # 50ms between keys
            logger.info("Typed text", text=text, x=x, y=y, length=len(text))
            return {"success": True, "error": None}
        except Exception as e:
            logger.error("Type failed", text=text, x=x, y=y, error=str(e))
            return {"success": False, "error": str(e)}
    
    def press_key(self, key: str) -> dict:
        """
        Press a keyboard key (Enter, Escape, Tab, etc.).
        
        Args:
            key: Key name (e.g., "Enter", "Escape", "ArrowDown", "Tab")
            
        Returns:
            {"success": bool, "error": str or None}
        """
        try:
            self.page.keyboard.press(key)
            logger.info("Pressed key", key=key)
            return {"success": True, "error": None}
        except Exception as e:
            logger.error("Key press failed", key=key, error=str(e))
            return {"success": False, "error": str(e)}
    
    def scroll(self, direction: str, amount: int = 300) -> dict:
        """
        Scroll the page up or down.
        
        Args:
            direction: "up" or "down"
            amount: Pixels to scroll (default: 300)
            
        Returns:
            {"success": bool, "error": str or None}
        """
        try:
            delta_y = -amount if direction.lower() == "up" else amount
            self.page.mouse.wheel(0, delta_y)
            logger.info("Scrolled", direction=direction, amount=amount)
            return {"success": True, "error": None}
        except Exception as e:
            logger.error("Scroll failed", direction=direction, amount=amount, error=str(e))
            return {"success": False, "error": str(e)}
    
    def hover(self, x: int, y: int) -> dict:
        """
        Hover over coordinates (useful for revealing tooltips/menus).
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            {"success": bool, "error": str or None}
        """
        try:
            self.page.mouse.move(x, y)
            logger.info("Hovered", x=x, y=y)
            return {"success": True, "error": None}
        except Exception as e:
            logger.error("Hover failed", x=x, y=y, error=str(e))
            return {"success": False, "error": str(e)}
    
    def wait(self, milliseconds: int) -> dict:
        """
        Wait for specified time.
        
        Args:
            milliseconds: Time to wait in milliseconds
            
        Returns:
            {"success": bool, "error": str or None}
        """
        try:
            self.page.wait_for_timeout(milliseconds)
            logger.info("Waited", milliseconds=milliseconds)
            return {"success": True, "error": None}
        except Exception as e:
            logger.error("Wait failed", milliseconds=milliseconds, error=str(e))
            return {"success": False, "error": str(e)}
    
    def click_element_hybrid(self, bid: str = None, element_info: dict = None, x: int = None, y: int = None) -> dict:
        """
        Click element using hybrid strategy: DOM selectors first, coordinates fallback.
        
        Strategy (selector-first):
        1. Try data-bid selector
        2. Try semantic selectors (role, aria-label, name, id)
        3. Fallback to coordinates
        
        Args:
            bid: Element bid for data-bid selector
            element_info: Element attributes for semantic selectors
            x: Fallback X coordinate
            y: Fallback Y coordinate
            
        Returns:
            {"success": bool, "error": str or None, "method": str}
        """
        errors = []
        
        # Strategy 1: Try data-bid
        if bid:
            try:
                self.page.click(f'[data-bid="{bid}"]', timeout=3000)
                logger.info("Clicked by data-bid", bid=bid, method="data-bid")
                return {"success": True, "error": None, "method": "data-bid"}
            except Exception as e:
                errors.append(f"data-bid: {str(e)[:50]}")
        
        # Strategy 2: Try semantic selectors
        if element_info:
            # Try role + aria-label
            if element_info.get('role') and element_info.get('aria_label'):
                try:
                    self.page.get_by_role(
                        element_info['role'],
                        name=element_info['aria_label']
                    ).first.click(timeout=3000)
                    logger.info("Clicked by role+aria-label", method="role+aria-label")
                    return {"success": True, "error": None, "method": "role+aria-label"}
                except Exception as e:
                    errors.append(f"role+aria-label: {str(e)[:50]}")
            
            # Try aria-label alone
            if element_info.get('aria_label'):
                try:
                    self.page.get_by_label(element_info['aria_label']).first.click(timeout=3000)
                    logger.info("Clicked by aria-label", method="aria-label")
                    return {"success": True, "error": None, "method": "aria-label"}
                except Exception as e:
                    errors.append(f"aria-label: {str(e)[:50]}")
            
            # Try name attribute
            if element_info.get('name'):
                try:
                    self.page.click(f'[name="{element_info["name"]}"]', timeout=3000)
                    logger.info("Clicked by name", method="name")
                    return {"success": True, "error": None, "method": "name"}
                except Exception as e:
                    errors.append(f"name: {str(e)[:50]}")
            
            # Try ID
            if element_info.get('id'):
                try:
                    self.page.click(f'#{element_info["id"]}', timeout=3000)
                    logger.info("Clicked by id", method="id")
                    return {"success": True, "error": None, "method": "id"}
                except Exception as e:
                    errors.append(f"id: {str(e)[:50]}")
            
            # Try text content
            if element_info.get('text') and element_info.get('tag'):
                try:
                    self.page.locator(element_info['tag']).filter(
                        has_text=element_info['text']
                    ).first.click(timeout=3000)
                    logger.info("Clicked by text", method="text")
                    return {"success": True, "error": None, "method": "text"}
                except Exception as e:
                    errors.append(f"text: {str(e)[:50]}")
        
        # Strategy 3: Fallback to coordinates
        if x is not None and y is not None:
            result = self.click_coordinate(x, y)
            if result["success"]:
                result["method"] = "coordinates"
                logger.info("Clicked by coordinates (fallback)", x=x, y=y, method="coordinates")
                return result
            else:
                errors.append(f"coordinates: {result['error']}")
        
        # All strategies failed
        error_msg = "; ".join(errors)
        logger.error("All click strategies failed", errors=error_msg)
        return {"success": False, "error": error_msg, "method": "none"}
    
    def type_element_hybrid(self, text: str, bid: str = None, element_info: dict = None, x: int = None, y: int = None) -> dict:
        """
        Type into element using hybrid strategy: DOM selectors first, coordinates fallback.
        
        Args:
            text: Text to type
            bid: Element bid
            element_info: Element attributes
            x: Fallback X coordinate
            y: Fallback Y coordinate
            
        Returns:
            {"success": bool, "error": str or None, "method": str}
        """
        errors = []
        
        # Strategy 1: Try data-bid
        if bid:
            try:
                self.page.fill(f'[data-bid="{bid}"]', text, timeout=3000)
                logger.info("Typed by data-bid", bid=bid, method="data-bid")
                return {"success": True, "error": None, "method": "data-bid"}
            except Exception as e:
                errors.append(f"data-bid: {str(e)[:50]}")
        
        # Strategy 2: Try semantic selectors
        if element_info:
            # Try role
            if element_info.get('role') in ['textbox', 'searchbox', 'combobox']:
                try:
                    locator = self.page.get_by_role(element_info['role'])
                    if element_info.get('aria_label'):
                        locator = locator.filter(has_text=element_info['aria_label'])
                    locator.first.fill(text, timeout=3000)
                    logger.info("Typed by role", method="role")
                    return {"success": True, "error": None, "method": "role"}
                except Exception as e:
                    errors.append(f"role: {str(e)[:50]}")
            
            # Try placeholder
            if element_info.get('placeholder'):
                try:
                    self.page.get_by_placeholder(element_info['placeholder']).first.fill(text, timeout=3000)
                    logger.info("Typed by placeholder", method="placeholder")
                    return {"success": True, "error": None, "method": "placeholder"}
                except Exception as e:
                    errors.append(f"placeholder: {str(e)[:50]}")
            
            # Try name
            if element_info.get('name'):
                try:
                    self.page.fill(f'[name="{element_info["name"]}"]', text, timeout=3000)
                    logger.info("Typed by name", method="name")
                    return {"success": True, "error": None, "method": "name"}
                except Exception as e:
                    errors.append(f"name: {str(e)[:50]}")
        
        # Strategy 3: Fallback to coordinates (click then type)
        if x is not None and y is not None:
            result = self.type_text(text, x, y)
            if result["success"]:
                result["method"] = "coordinates"
                logger.info("Typed by coordinates (fallback)", method="coordinates")
                return result
            else:
                errors.append(f"coordinates: {result['error']}")
        
        # All strategies failed
        error_msg = "; ".join(errors)
        logger.error("All type strategies failed", errors=error_msg)
        return {"success": False, "error": error_msg, "method": "none"}

