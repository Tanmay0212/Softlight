# browser_controller.py
import base64
import os
import time
from playwright.sync_api import sync_playwright, Page
from softlight.core.config.env import Settings
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


class BrowserController:
    def __init__(self, use_existing_profile: bool = False):
        self.playwright = sync_playwright().start()
        self.context = None  # May not be used in persistent context
        
        if use_existing_profile:
            # Use a SEPARATE profile directory for automation
            # This allows your main Chrome to stay open while automation runs
            user_data_dir = os.path.expanduser("~/.chrome-automation-profile")
            
            # Create directory if it doesn't exist
            os.makedirs(user_data_dir, exist_ok=True)
            
            try:
                logger.info(f"Using separate Chrome profile for automation: {user_data_dir}")
                
                # Check if this is first time (profile is empty)
                is_first_time = not os.path.exists(os.path.join(user_data_dir, "Default"))
                
                self.browser = self.playwright.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=False,  # Must be non-headless when using profiles
                    viewport={'width': 1280, 'height': 720},  # Fixed viewport for coordinate matching
                    channel="chrome"  # Use actual Chrome, not Chromium
                )
                self.page: Page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()
                
                # Enforce window size to match viewport (critical for coordinate accuracy)
                self._enforce_window_size()
                
                if is_first_time:
                    logger.info("🔐 First time setup: Please log into Linear manually in the browser that opened")
                    logger.info("💾 Your login will be saved for future runs")
                else:
                    logger.info("✅ Using saved login session from previous runs")
                    
            except Exception as e:
                logger.warning(f"Could not use automation profile: {e}, falling back to default browser")
                use_existing_profile = False
        
        if not use_existing_profile:
            # Original behavior - fresh browser instance
            self.browser = self.playwright.chromium.launch(
                headless=Settings.HEADLESS_MODE
            )
            self.context = self.browser.new_context(viewport={'width': 1280, 'height': 720})
            self.page: Page = self.context.new_page()
            
            # Enforce window size to match viewport (critical for coordinate accuracy)
            self._enforce_window_size()
    
    def _enforce_window_size(self):
        """
        Enforce that the browser window stays at exactly 1280x720.
        This is CRITICAL for coordinate accuracy - the screenshot dimensions
        must match the actual window dimensions where clicks happen.
        """
        try:
            # Set viewport size explicitly
            self.page.set_viewport_size({"width": 1280, "height": 720})
            
            # Set the actual window size and prevent resizing
            self.page.evaluate("""
                () => {
                    // Set window to exact size
                    window.resizeTo(1280, 720);
                    
                    // Lock window size - prevent manual resizing
                    let resizeAttempts = 0;
                    const enforceSize = () => {
                        if (window.innerWidth !== 1280 || window.innerHeight !== 720) {
                            resizeAttempts++;
                            if (resizeAttempts < 10) {  // Prevent infinite loops
                                window.resizeTo(1280, 720);
                            }
                        }
                    };
                    
                    // Check size every 500ms
                    setInterval(enforceSize, 500);
                    
                    // Also enforce on resize events
                    window.addEventListener('resize', enforceSize);
                }
            """)
            
            logger.info("Window size enforced: 1280x720 (locked)")
            
        except Exception as e:
            logger.warning(f"Could not enforce window size: {e}")

    def navigate(self, url: str):
        print(f"Navigating to {url}...")
        self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            # Try to wait for network idle, but don't fail if it takes too long
            # Some apps (like Notion) have constant background activity
            self.page.wait_for_load_state('networkidle', timeout=10000)
        except Exception as e:
            logger.warning(f"Network did not become idle within timeout, continuing anyway: {e}")
            # Wait a bit for the page to stabilize
            import time
            time.sleep(2)

    def get_observation(self) -> (str, str):
        """Returns the base64 screenshot and the page's HTML content."""
        #screenshot_b64 = self.page.screenshot().decode('base64')
        screenshot_b64 = base64.b64encode(self.page.screenshot()).decode('utf-8')
        html_content = self.page.content()
        return screenshot_b64, html_content
    
    def inject_serializer_ids(self, updated_html: str):
        """
        Uses Javascript to inject the `data-bid` attributes into the live DOM.
        This approach preserves JavaScript and event listeners better than replacing innerHTML.
        
        NOTE: This step is optional and will be skipped if the site has strict CSP policies.
        """
        try:
            # Try to inject data-bid attributes for better element targeting
            self.page.evaluate("""
                (html) => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const elementsWithBid = doc.querySelectorAll('[data-bid]');
                    
                    elementsWithBid.forEach(elem => {
                        const bid = elem.getAttribute('data-bid');
                        const tag = elem.tagName.toLowerCase();
                        
                        // Find matching element in live DOM using multiple strategies
                        let liveElem = null;
                        
                        // Strategy 1: By name attribute
                        if (elem.name) {
                            liveElem = document.querySelector(`${tag}[name="${elem.name}"]`);
                        }
                        
                        // Strategy 2: By id
                        if (!liveElem && elem.id) {
                            liveElem = document.getElementById(elem.id);
                        }
                        
                        // Strategy 3: By class combination
                        if (!liveElem && elem.className) {
                            const classes = elem.className.split(' ').filter(c => c).join('.');
                            if (classes) {
                                liveElem = document.querySelector(`${tag}.${classes}`);
                            }
                        }
                        
                        // Strategy 4: By text content for buttons/links
                        if (!liveElem && (tag === 'button' || tag === 'a')) {
                            const text = elem.textContent.trim();
                            if (text) {
                                const allOfType = Array.from(document.querySelectorAll(tag));
                                liveElem = allOfType.find(el => el.textContent.trim() === text);
                            }
                        }
                        
                        // Apply the data-bid attribute if we found a match
                        if (liveElem && !liveElem.hasAttribute('data-bid')) {
                            liveElem.setAttribute('data-bid', bid);
                        }
                    });
                }
            """, updated_html)
            logger.debug("Serializer IDs injected into live DOM")
        except Exception as e:
            # Skip injection if site has strict CSP (Content Security Policy)
            logger.warning(f"Could not inject serializer IDs (site has strict CSP): {str(e)[:100]}")
            logger.info("Continuing without data-bid attributes (agents will use other element selectors)")


    def execute_action(self, command: str, element_map: dict = None, max_retries: int = Settings.MAX_ACTION_RETRIES) -> bool:
        """
        Parses and executes an action command from the agent.
        Uses hybrid selector strategy with multiple fallbacks for reliability.
        
        Args:
            command: Action command string (e.g., "CLICK 5")
            element_map: Dict mapping bid -> element info for fallback selection
            max_retries: Number of retry attempts
            
        Returns:
            True if successful, False otherwise.
        """
        print(f"Executing action: {command}")
        
        # Extract the actual command from multi-line response (last line)
        lines = command.strip().split('\n')
        command_line = lines[-1].strip()
        parts = command_line.split(" ", 2)
        action_type = parts[0].upper()
        
        element_map = element_map or {}
        
        for attempt in range(max_retries):
            try:
                if action_type == "CLICK":
                    bid = parts[1]
                    if self._click_element(bid, element_map):
                        print(f"✓ Clicked element with bid={bid}")
                        # Wait for the UI to settle after click
                        self.page.wait_for_load_state('networkidle', timeout=10000)
                        return True
                    else:
                        raise Exception(f"Could not click element bid={bid}")
                
                elif action_type == "TYPE":
                    bid = parts[1]
                    text_to_type = parts[2].strip('"\'')
                    if self._type_into_element(bid, text_to_type, element_map):
                        print(f"✓ Typed '{text_to_type}' into element with bid={bid}")
                        return True
                    else:
                        raise Exception(f"Could not type into element bid={bid}")
                
                elif action_type == "SCROLL":
                    direction = parts[1].upper() if len(parts) > 1 else "DOWN"
                    self.scroll(direction)
                    print(f"✓ Scrolled {direction}")
                    return True
                
                elif action_type == "WAIT":
                    self.wait()
                    print("✓ Waited 2 seconds")
                    return True
                
                else:
                    print(f"⚠ Unknown action type: {action_type}")
                    return False
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠ Attempt {attempt + 1} failed: {str(e)[:100]}. Retrying...")
                    time.sleep(1)
                else:
                    print(f"✗ Action failed after {max_retries} attempts: {str(e)[:100]}")
                    return False
        
        return False
    
    def _click_element(self, bid: str, element_map: dict) -> bool:
        """
        Hybrid selector strategy to click an element.
        Tries multiple methods in order of reliability.
        """
        elem_info = element_map.get(bid, {})
        
        # Strategy 1: Try data-bid (fast if injection worked)
        try:
            self.page.click(f'[data-bid="{bid}"]', timeout=3000)
            logger.debug(f"Clicked by data-bid: {bid}")
            return True
        except Exception as e:
            logger.debug(f"data-bid failed: {str(e)[:50]}")
        
        # Strategy 2: Playwright's getByRole (most reliable!)
        if elem_info.get('role') and elem_info.get('text'):
            try:
                self.page.get_by_role(
                    elem_info['role'], 
                    name=elem_info['text']
                ).first.click(timeout=5000)
                logger.debug(f"Clicked by role+name: {elem_info['role']}")
                return True
            except Exception as e:
                logger.debug(f"role+name failed: {str(e)[:50]}")
        
        # Strategy 3: By aria-label (accessible elements)
        if elem_info.get('aria_label'):
            try:
                self.page.get_by_label(elem_info['aria_label']).first.click(timeout=5000)
                logger.debug(f"Clicked by aria-label")
                return True
            except Exception as e:
                logger.debug(f"aria-label failed: {str(e)[:50]}")
        
        # Strategy 4: By placeholder (form inputs)
        if elem_info.get('placeholder'):
            try:
                self.page.get_by_placeholder(elem_info['placeholder']).first.click(timeout=5000)
                logger.debug(f"Clicked by placeholder")
                return True
            except Exception as e:
                logger.debug(f"placeholder failed: {str(e)[:50]}")
        
        # Strategy 5: By name attribute (form elements)
        if elem_info.get('name'):
            try:
                selector = f'[name="{elem_info["name"]}"]'
                self.page.click(selector, timeout=5000)
                logger.debug(f"Clicked by name attribute")
                return True
            except Exception as e:
                logger.debug(f"name attribute failed: {str(e)[:50]}")
        
        # Strategy 6: By ID (if present)
        if elem_info.get('id'):
            try:
                self.page.click(f'#{elem_info["id"]}', timeout=5000)
                logger.debug(f"Clicked by ID")
                return True
            except Exception as e:
                logger.debug(f"ID failed: {str(e)[:50]}")
        
        # Strategy 7: By text content (last resort)
        if elem_info.get('text'):
            try:
                tag = elem_info.get('tag', 'button')
                self.page.locator(tag).filter(
                    has_text=elem_info['text']
                ).first.click(timeout=5000)
                logger.debug(f"Clicked by text content")
                return True
            except Exception as e:
                logger.debug(f"text content failed: {str(e)[:50]}")
        
        logger.warning(f"All click strategies failed for bid={bid}")
        return False
    
    def _type_into_element(self, bid: str, text: str, element_map: dict) -> bool:
        """
        Hybrid selector strategy to type into an element.
        Tries multiple methods in order of reliability.
        """
        elem_info = element_map.get(bid, {})
        
        # Strategy 1: Try data-bid (fast if injection worked)
        try:
            selector = f'[data-bid="{bid}"]'
            self.page.fill(selector, text, timeout=3000)
            logger.debug(f"Typed by data-bid: {bid}")
            return True
        except Exception as e:
            logger.debug(f"data-bid fill failed: {str(e)[:50]}")
        
        # Strategy 2: Playwright's getByRole for textbox
        if elem_info.get('role') in ['textbox', 'searchbox', 'combobox']:
            try:
                locator = self.page.get_by_role(elem_info['role'])
                if elem_info.get('aria_label'):
                    locator = locator.filter(has_text=elem_info['aria_label'])
                locator.first.fill(text, timeout=5000)
                logger.debug(f"Typed by role: {elem_info['role']}")
                return True
            except Exception as e:
                logger.debug(f"role fill failed: {str(e)[:50]}")
        
        # Strategy 3: By placeholder
        if elem_info.get('placeholder'):
            try:
                self.page.get_by_placeholder(elem_info['placeholder']).first.fill(text, timeout=5000)
                logger.debug(f"Typed by placeholder")
                return True
            except Exception as e:
                logger.debug(f"placeholder fill failed: {str(e)[:50]}")
        
        # Strategy 4: By aria-label
        if elem_info.get('aria_label'):
            try:
                self.page.get_by_label(elem_info['aria_label']).first.fill(text, timeout=5000)
                logger.debug(f"Typed by aria-label")
                return True
            except Exception as e:
                logger.debug(f"aria-label fill failed: {str(e)[:50]}")
        
        # Strategy 5: By name attribute
        if elem_info.get('name'):
            try:
                selector = f'[name="{elem_info["name"]}"]'
                self.page.fill(selector, text, timeout=5000)
                logger.debug(f"Typed by name attribute")
                return True
            except Exception as e:
                logger.debug(f"name attribute fill failed: {str(e)[:50]}")
        
        # Strategy 6: For contenteditable, use click + type
        if elem_info.get('contenteditable'):
            try:
                # First click to focus
                if self._click_element(bid, element_map):
                    # Then type
                    self.page.keyboard.type(text, delay=50)
                    logger.debug(f"Typed into contenteditable by keyboard")
                    return True
            except Exception as e:
                logger.debug(f"contenteditable type failed: {str(e)[:50]}")
        
        logger.warning(f"All type strategies failed for bid={bid}")
        return False
    
    def scroll(self, direction: str = "DOWN"):
        """Scroll the page up or down."""
        if direction.upper() == "DOWN":
            self.page.evaluate("window.scrollBy(0, window.innerHeight)")
        else:
            self.page.evaluate("window.scrollBy(0, -window.innerHeight)")
    
    def wait(self, seconds: int = 2):
        """Wait for specified seconds."""
        time.sleep(seconds)
    
    def go_back(self):
        """Navigate back in browser history."""
        self.page.go_back()
    
    def screenshot_element(self, bid: str) -> bytes:
        """Take screenshot of a specific element."""
        selector = f'[data-bid="{bid}"]'
        return self.page.locator(selector).screenshot()

    def close(self):
        print("Closing browser.")
        try:
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
        finally:
            if hasattr(self, 'playwright'):
                self.playwright.stop()