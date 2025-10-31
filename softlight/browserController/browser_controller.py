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
                    args=["--start-maximized"],
                    channel="chrome"  # Use actual Chrome, not Chromium
                )
                self.page: Page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()
                
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
                headless=Settings.HEADLESS_MODE, 
                args=["--start-maximized"]
            )
            self.context = self.browser.new_context(no_viewport=True)
            self.page: Page = self.context.new_page()

    def navigate(self, url: str):
        print(f"Navigating to {url}...")
        self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_load_state('networkidle')

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


    def execute_action(self, command: str, max_retries: int = 3) -> bool:
        """
        Parses and executes an action command from the agent.
        Returns True if successful, False otherwise.
        """
        print(f"Executing action: {command}")
        
        # Extract the actual command from multi-line response (last line)
        lines = command.strip().split('\n')
        command_line = lines[-1].strip()
        parts = command_line.split(" ", 2)
        action_type = parts[0].upper()
        
        for attempt in range(max_retries):
            try:
                if action_type == "CLICK":
                    bid = parts[1]
                    selector = f'[data-bid="{bid}"]'
                    self.page.click(selector, timeout=30000)
                    print(f"✓ Clicked element with bid={bid}")
                
                elif action_type == "TYPE":
                    bid = parts[1]
                    text_to_type = parts[2].strip('"\'')
                    selector = f'[data-bid="{bid}"]'
                    self.page.fill(selector, text_to_type, timeout=30000)
                    print(f"✓ Typed '{text_to_type}' into element with bid={bid}")
                    
                    # Also press Enter for search boxes
                    self.page.press(selector, "Enter")
                
                elif action_type == "SCROLL":
                    direction = parts[1].upper() if len(parts) > 1 else "DOWN"
                    self.scroll(direction)
                    print(f"✓ Scrolled {direction}")
                
                elif action_type == "WAIT":
                    self.wait()
                    print("✓ Waited 2 seconds")
                
                else:
                    print(f"⚠ Unknown action type: {action_type}")
                    return False
                
                # Wait for the UI to settle after an action
                self.page.wait_for_load_state('networkidle', timeout=30000)
                return True  # Success
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠ Attempt {attempt + 1} failed: {e}. Retrying...")
                    time.sleep(1)
                else:
                    print(f"✗ Action failed after {max_retries} attempts: {e}")
                    return False
        
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