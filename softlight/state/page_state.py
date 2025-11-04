# page_state.py - Page state representation for hybrid system
"""
PageState encapsulates all perception data for a single step:
- DOM structure (extracted elements)
- Page text (visible content)
- Screenshot (for vision)
- Metadata (URL, title)

This is the input to the hybrid instructor agent for decision making.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from playwright.sync_api import Page
from softlight.domProcessor.element_info import ElementInfo
from softlight.domProcessor.dom_extractor import extract_dom_state
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class PageState:
    """
    Complete page state for hybrid perception.
    
    Combines:
    - DOM structure (actionable elements with semantic attributes)
    - Page text (visible content for semantic context)
    - Screenshot path (for vision grounding)
    - Metadata (URL, title)
    """
    
    # DOM data
    html: str                                  # Full HTML content
    elements: List[ElementInfo]                # Extracted actionable elements
    page_text: str                             # Visible text content
    
    # Vision data
    screenshot_path: str                       # Path to screenshot file
    
    # Metadata
    url: str                                   # Current page URL
    title: str                                 # Page title
    
    # Optional raw data
    raw_html: Optional[str] = None            # Original HTML (if needed)
    
    def get_elements_summary(self, max_elements: int = 50) -> str:
        """
        Get compact summary of elements for LLM prompt.
        
        Args:
            max_elements: Maximum elements to include
            
        Returns:
            Formatted string with element list
        """
        if not self.elements:
            return "No actionable elements found."
        
        lines = ["Available elements:"]
        for elem in self.elements[:max_elements]:
            lines.append(elem.to_compact_string())
        
        if len(self.elements) > max_elements:
            lines.append(f"... and {len(self.elements) - max_elements} more elements")
        
        return "\n".join(lines)
    
    def get_element_by_bid(self, bid: str) -> Optional[ElementInfo]:
        """
        Find element by bid.
        
        Args:
            bid: Element bid
            
        Returns:
            ElementInfo or None if not found
        """
        for elem in self.elements:
            if elem.bid == bid:
                return elem
        return None
    
    def get_page_text_summary(self, max_chars: int = 1000) -> str:
        """
        Get truncated page text for LLM prompt.
        
        Args:
            max_chars: Maximum characters to include
            
        Returns:
            Truncated page text
        """
        if not self.page_text:
            return "No visible text on page."
        
        if len(self.page_text) <= max_chars:
            return self.page_text
        
        return self.page_text[:max_chars] + "..."
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "url": self.url,
            "title": self.title,
            "screenshot_path": self.screenshot_path,
            "elements_count": len(self.elements),
            "elements": [elem.to_dict() for elem in self.elements[:20]],  # Limit for size
            "page_text_preview": self.page_text[:500] if self.page_text else "",
        }


def build_page_state(page: Page, screenshot_path: str, max_elements: int = 100) -> PageState:
    """
    Build PageState from Playwright page.
    
    This is the main entry point for perception in the hybrid system.
    
    Args:
        page: Playwright Page object
        screenshot_path: Path where screenshot should be saved
        max_elements: Maximum elements to extract
        
    Returns:
        PageState object with all perception data
    """
    logger.debug("Building page state")
    
    try:
        # Capture screenshot
        page.screenshot(path=screenshot_path)
        logger.debug(f"Screenshot saved to {screenshot_path}")
        
        # Get HTML content
        html = page.content()
        
        # Extract DOM elements and page text
        elements, page_text = extract_dom_state(html, max_elements=max_elements)
        
        # CRITICAL: Inject data-bid attributes into the actual DOM
        # This allows us to use stable selectors like [data-bid="13"]
        _inject_bids_into_dom(page, elements)
        
        # Get metadata
        url = page.url
        title = page.title()
        
        # Build state object
        state = PageState(
            html=html,
            elements=elements,
            page_text=page_text,
            screenshot_path=screenshot_path,
            url=url,
            title=title,
        )
        
        logger.info(
            f"Page state built",
            url=url,
            title=title,
            elements_count=len(elements),
            text_length=len(page_text),
        )
        
        return state
        
    except Exception as e:
        logger.error(f"Failed to build page state: {e}")
        # Return minimal state
        return PageState(
            html="",
            elements=[],
            page_text="",
            screenshot_path=screenshot_path,
            url=page.url if page else "",
            title="",
        )


def _inject_bids_into_dom(page: Page, elements: List[ElementInfo]):
    """
    Inject data-bid attributes into the actual page DOM.
    
    This is critical for the hybrid system to work. We extract elements,
    assign them bid values, then inject those bids back into the page
    so we can use selectors like [data-bid="13"].
    
    Strategy:
    1. Build a list of candidate selectors for each element
    2. Try each selector in order of specificity
    3. Set data-bid on the first matching element
    
    Args:
        page: Playwright Page object
        elements: List of ElementInfo with assigned bids
    """
    try:
        import json
        
        # Build selector strategies for each element
        element_strategies = [_build_selector_strategies(elem) for elem in elements]
        
        # Convert to JSON for safe injection into JavaScript
        elements_json = json.dumps(element_strategies)
        
        # Build JavaScript to inject all bids at once
        js_script = f"""
        (function() {{
            const elements = {elements_json};
            
            let successCount = 0;
            for (const item of elements) {{
                const {{ bid, selectors }} = item;
                
                // Try each selector until one works
                for (const selector of selectors) {{
                    try {{
                        const elem = document.querySelector(selector);
                        if (elem && !elem.hasAttribute('data-bid')) {{
                            elem.setAttribute('data-bid', bid);
                            successCount++;
                            break;  // Success, move to next element
                        }}
                    }} catch(e) {{
                        // Selector failed, try next one
                        continue;
                    }}
                }}
            }}
            
            return successCount;
        }})();
        """
        
        # Execute injection
        success_count = page.evaluate(js_script)
        
        logger.debug(f"Injected {success_count}/{len(elements)} data-bid attributes into DOM")
        
    except Exception as e:
        logger.warning(f"Failed to inject bids into DOM: {e}")
        # Non-critical failure - system will fall back to coordinate-based clicking


def _build_selector_strategies(elem: ElementInfo) -> dict:
    """
    Build a list of selector strategies for an element, in priority order.
    
    Returns a dict with bid and list of selectors to try.
    
    Args:
        elem: ElementInfo object
        
    Returns:
        {"bid": str, "selectors": [str]}
    """
    selectors = []
    
    # Strategy 1: ID (most stable)
    if elem.id:
        selectors.append(f"#{elem.id}")
    
    # Strategy 2: data-testid
    if elem.data_testid:
        selectors.append(f"[data-testid='{elem.data_testid}']")
    
    # Strategy 3: name attribute
    if elem.name:
        selectors.append(f"{elem.tag}[name='{elem.name}']")
    
    # Strategy 4: aria-label (for buttons/links)
    if elem.aria_label and elem.tag in ['button', 'a']:
        # Escape quotes in aria-label
        safe_label = elem.aria_label.replace("'", "\\'")
        selectors.append(f"{elem.tag}[aria-label='{safe_label}']")
    
    # Strategy 5: Tag + type (for inputs)
    if elem.tag == 'input' and elem.type:
        selectors.append(f"input[type='{elem.type}']")
        # If it has a placeholder, add that too
        if elem.placeholder:
            safe_placeholder = elem.placeholder.replace("'", "\\'")
            selectors.append(f"input[type='{elem.type}'][placeholder='{safe_placeholder}']")
    
    # Strategy 6: href (for links)
    if elem.tag == 'a' and elem.href:
        safe_href = elem.href.replace("'", "\\'")
        selectors.append(f"a[href='{safe_href}']")
    
    # Always include the basic selector from element_info as fallback
    if elem.selector and elem.selector not in selectors:
        selectors.append(elem.selector)
    
    return {
        "bid": elem.bid,
        "selectors": selectors
    }

