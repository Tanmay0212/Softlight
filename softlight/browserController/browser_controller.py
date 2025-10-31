# browser_controller.py
import base64
from playwright.sync_api import sync_playwright, Page
from softlight.core.config.env import Settings

class BrowserController:
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=Settings.HEADLESS_MODE, args=["--start-maximized"])
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
        This is more robust than reloading the entire page content.
        """
        #self.page.evaluate("() => { document.body.innerHTML = arguments[0]; }", updated_html)
        self.page.evaluate("(html) => { document.body.innerHTML = html; }", updated_html)


    def execute_action(self, command: str):
        """Parses and executes an action command from the agent."""
        print(f"Executing action: {command}")
        parts = command.split(" ", 2)
        action_type = parts[0].upper()
        
        try:
            if action_type == "CLICK":
                bid = parts[1]
                selector = f'[data-bid="{bid}"]'
                self.page.click(selector, timeout=30000)
            
            elif action_type == "TYPE":
                bid = parts[1]
                text_to_type = parts[2].strip('"')
                selector = f'[data-bid="{bid}"]'
                self.page.fill(selector, text_to_type, timeout=30000)
                
            # Wait for the UI to settle after an action
            self.page.wait_for_load_state('networkidle', timeout=30000)
        except Exception as e:
            print(f"Error executing action '{command}': {e}")

    def close(self):
        print("Closing browser.")
        self.browser.close()
        self.playwright.stop()