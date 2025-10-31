# screenshot_manager.py
import os
import re
from typing import List, Dict
from softlight.core.config.env import Settings
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


class ScreenshotManager:
    """
    Manages screenshot capture and storage for UI state capture.
    """
    
    def __init__(self, browser_page):
        self.page = browser_page
        self.captured_states = []
    
    def capture_state(self, step_num: int, action_description: str, task_id: str) -> str:
        """
        Capture and save screenshot for the current state.
        
        Args:
            step_num: Current step number
            action_description: Brief description of the action/state
            task_id: Unique task identifier
            
        Returns:
            Path to saved screenshot
        """
        # Sanitize description for filename
        sanitized_desc = self._sanitize_filename(action_description)
        filename = f"step_{step_num}_{sanitized_desc}.png"
        
        # Create dataset directory
        dataset_dir = os.path.join(Settings.DATASET_ROOT, task_id)
        os.makedirs(dataset_dir, exist_ok=True)
        
        filepath = os.path.join(dataset_dir, filename)
        
        try:
            # Capture screenshot
            screenshot_bytes = self.page.screenshot()
            
            # Save to file
            with open(filepath, "wb") as f:
                f.write(screenshot_bytes)
            
            # Track captured state
            self.captured_states.append({
                "step": step_num,
                "filename": filename,
                "description": action_description,
                "filepath": filepath
            })
            
            logger.debug("Screenshot captured", step=step_num, filepath=filepath)
            return filepath
            
        except Exception as e:
            logger.error("Failed to capture screenshot", step=step_num, error=str(e))
            return None
    
    def get_captured_states(self) -> List[Dict]:
        """
        Get list of all captured states.
        
        Returns:
            List of captured state dictionaries
        """
        return self.captured_states
    
    def _sanitize_filename(self, text: str, max_length: int = 50) -> str:
        """
        Sanitize text for use in filename.
        
        Args:
            text: Text to sanitize
            max_length: Maximum length of result
            
        Returns:
            Sanitized filename-safe string
        """
        # Remove or replace invalid characters
        text = re.sub(r'[^\w\s-]', '', text)
        # Replace spaces with underscores
        text = re.sub(r'[\s]+', '_', text)
        # Remove multiple underscores
        text = re.sub(r'_+', '_', text)
        # Lowercase and trim
        text = text.lower().strip('_')
        # Limit length
        if len(text) > max_length:
            text = text[:max_length]
        
        return text or "state"

