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
    1. Clear stale bids (selective - only disconnected/hidden elements)
    2. Build a list of candidate selectors for each element
    3. Try each selector in order of specificity
    4. Set data-bid on the first matching element
    
    Args:
        page: Playwright Page object
        elements: List of ElementInfo with assigned bids
    """
    try:
        import json
        
        # FIX 2: Selective bid clearing - remove only stale/removed elements
        clear_stale_bids_script = """
        (function() {
            const existingBids = document.querySelectorAll('[data-bid]');
            let removedCount = 0;
            existingBids.forEach(elem => {
                // Remove bid if element is disconnected or hidden (likely removed/replaced)
                if (!elem.isConnected || elem.offsetParent === null) {
                    elem.removeAttribute('data-bid');
                    removedCount++;
                }
            });
            return removedCount;
        })();
        """
        
        try:
            removed_count = page.evaluate(clear_stale_bids_script)
            if removed_count > 0:
                logger.debug(f"Cleared {removed_count} stale data-bid attributes")
        except Exception as e:
            logger.debug(f"Could not clear stale bids: {e}")
        
        # Build selector strategies for each element
        element_strategies = [_build_selector_strategies(elem) for elem in elements]
        
        # Convert to JSON for safe injection into JavaScript
        elements_json = json.dumps(element_strategies)
        
        # FIX 3: Enhanced injection with detailed logging
        js_script = f"""
        (function() {{
            const elements = {elements_json};
            
            let successCount = 0;
            const failed = [];
            
            for (const item of elements) {{
                const {{ bid, selectors, elementInfo }} = item;
                let matched = false;
                
                // Try each selector until one works
                for (const selector of selectors) {{
                    try {{
                        const elem = document.querySelector(selector);
                        if (elem && !elem.hasAttribute('data-bid')) {{
                            elem.setAttribute('data-bid', bid);
                            successCount++;
                            matched = true;
                            break;  // Success, move to next element
                        }}
                    }} catch(e) {{
                        // Selector failed, try next one
                        continue;
                    }}
                }}
                
                if (!matched) {{
                    failed.push({{
                        bid: bid,
                        tag: elementInfo?.tag,
                        text: elementInfo?.text?.substring(0, 30),
                        selectors: selectors
                    }});
                }}
            }}
            
            return {{ successCount, failed }};
        }})();
        """
        
        # Execute injection
        result = page.evaluate(js_script)
        success_count = result.get('successCount', 0)
        failed_items = result.get('failed', [])
        
        # FIX 3: Detailed logging
        logger.info(
            f"Bid injection: {success_count}/{len(elements)} successful",
            success_rate=f"{success_count/len(elements)*100:.1f}%" if elements else "N/A"
        )
        
        if failed_items:
            failed_bids = [item['bid'] for item in failed_items[:5]]  # Log first 5
            logger.warning(
                f"Failed to inject {len(failed_items)} bids",
                failed_bids=failed_bids,
                examples=[{
                    'bid': item['bid'],
                    'tag': item['tag'],
                    'text': item['text']
                } for item in failed_items[:3]]
            )
        
    except Exception as e:
        logger.warning(f"Failed to inject bids into DOM: {e}")
        # Non-critical failure - system will fall back to coordinate-based clicking


def detect_dom_changes_and_reinject(page: Page, max_elements: int = 100) -> bool:
    """
    FIX 1: Detect DOM changes after CLICK actions and re-inject bids for new elements.
    
    This handles dynamic content (modals, dropdowns) that appear after initial bid injection.
    
    Strategy:
    1. Wait up to 2 seconds for DOM mutations
    2. Re-extract DOM to find new elements
    3. Inject bids for newly appeared elements
    
    Args:
        page: Playwright Page object
        max_elements: Maximum elements to extract
        
    Returns:
        True if DOM changed and bids were re-injected, False otherwise
    """
    try:
        # Wait for potential DOM mutations (modals, dropdowns appearing)
        # This uses Playwright's wait_for_function with a mutation observer
        dom_changed = page.evaluate("""
            () => {
                return new Promise((resolve) => {
                    const initialCount = document.querySelectorAll('*').length;
                    let mutationOccurred = false;
                    
                    const observer = new MutationObserver((mutations) => {
                        // Check if significant DOM changes occurred
                        const currentCount = document.querySelectorAll('*').length;
                        const changePercent = Math.abs(currentCount - initialCount) / initialCount;
                        
                        // If >5% of DOM changed, consider it significant
                        if (changePercent > 0.05) {
                            mutationOccurred = true;
                            observer.disconnect();
                            resolve(true);
                        }
                    });
                    
                    observer.observe(document.body, {
                        childList: true,
                        subtree: true
                    });
                    
                    // Timeout after 2 seconds
                    setTimeout(() => {
                        observer.disconnect();
                        resolve(mutationOccurred);
                    }, 2000);
                });
            }
        """)
        
        if dom_changed:
            logger.info("DOM mutation detected - re-extracting and re-injecting bids")
            
            # Get updated HTML
            html = page.content()
            
            # Re-extract elements
            from softlight.domProcessor.dom_extractor import extract_dom_state
            elements, _ = extract_dom_state(html, max_elements=max_elements)
            
            # Re-inject bids (will use selective clearing)
            _inject_bids_into_dom(page, elements)
            
            return True
        else:
            logger.debug("No significant DOM mutations detected")
            return False
            
    except Exception as e:
        logger.warning(f"DOM change detection failed: {e}")
        return False


def _build_selector_strategies(elem: ElementInfo) -> dict:
    """
    Build a list of selector strategies for an element, in priority order.
    
    FIX 4: Enhanced with position-based selectors for improved uniqueness.
    
    Returns a dict with bid and list of selectors to try.
    
    Args:
        elem: ElementInfo object
        
    Returns:
        {"bid": str, "selectors": [str], "elementInfo": dict}
    """
    selectors = []
    
    # Strategy 1: ID (most stable - unique by definition)
    if elem.id:
        selectors.append(f"#{elem.id}")
    
    # Strategy 2: data-testid
    if elem.data_testid:
        selectors.append(f"[data-testid='{elem.data_testid}']")
    
    # FIX 4: Strategy 3: Compound selector with parent + name + position
    if elem.name and elem.parent_tag and elem.position_in_parent:
        selectors.append(f"{elem.parent_tag} > {elem.tag}[name='{elem.name}']:nth-child({elem.position_in_parent})")
    
    # Strategy 4: name attribute (basic)
    if elem.name:
        selectors.append(f"{elem.tag}[name='{elem.name}']")
    
    # FIX 4: Strategy 5: aria-label with position (for buttons/links)
    if elem.aria_label and elem.tag in ['button', 'a']:
        safe_label = elem.aria_label.replace("'", "\\'")
        
        # Try with position first (more unique)
        if elem.parent_tag and elem.position_in_parent:
            selectors.append(f"{elem.parent_tag} > {elem.tag}[aria-label='{safe_label}']:nth-child({elem.position_in_parent})")
        
        # Then try without position
        selectors.append(f"{elem.tag}[aria-label='{safe_label}']")
    
    # FIX 4: Strategy 6: Placeholder with position (for inputs)
    if elem.placeholder:
        safe_placeholder = elem.placeholder.replace("'", "\\'")
        
        # Compound: type + placeholder + position
        if elem.type and elem.parent_tag and elem.position_in_parent:
            selectors.append(f"{elem.parent_tag} > input[type='{elem.type}'][placeholder='{safe_placeholder}']:nth-child({elem.position_in_parent})")
        
        # Just type + placeholder
        if elem.type:
            selectors.append(f"input[type='{elem.type}'][placeholder='{safe_placeholder}']")
    
    # Strategy 7: Tag + type (for inputs - basic)
    if elem.tag == 'input' and elem.type:
        # With position
        if elem.parent_tag and elem.position_in_parent:
            selectors.append(f"{elem.parent_tag} > input[type='{elem.type}']:nth-child({elem.position_in_parent})")
        
        # Without position
        selectors.append(f"input[type='{elem.type}']")
    
    # Strategy 8: href (for links)
    if elem.tag == 'a' and elem.href:
        safe_href = elem.href.replace("'", "\\'")
        selectors.append(f"a[href='{safe_href}']")
    
    # Always include the basic selector from element_info as fallback
    if elem.selector and elem.selector not in selectors:
        selectors.append(elem.selector)
    
    # FIX 3: Include element info for detailed logging
    return {
        "bid": elem.bid,
        "selectors": selectors,
        "elementInfo": {
            "tag": elem.tag,
            "text": elem.text[:50] if elem.text else None,
            "aria_label": elem.aria_label,
            "placeholder": elem.placeholder
        }
    }

