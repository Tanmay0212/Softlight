# orchestrator_vision.py - Vision-Based Orchestrator
"""
Orchestrates vision-based workflow between Agent A and Agent B.
Simpler than DOM-based approach: Screenshot → Agent B → Agent A → Repeat
"""
import time
import os
from datetime import datetime
from softlight.browserController.browser_controller import BrowserController
from softlight.agent.simple_executor import SimpleExecutor
from softlight.agent.vision_instructor import VisionInstructor
from softlight.dataset.dataset_manager import DatasetManager
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


class VisionOrchestrator:
    """
    Orchestrates vision-based workflow.
    
    Flow:
    1. Agent B initializes with task
    2. Capture screenshot
    3. Agent B analyzes screenshot → returns JSON action with coordinates
    4. Agent A executes action using Playwright primitives
    5. Wait for page to settle
    6. Repeat until task complete
    7. Save dataset
    """
    
    def __init__(self, use_existing_profile: bool = False):
        """
        Initialize orchestrator.
        
        Args:
            use_existing_profile: Use existing Chrome profile with saved sessions
        """
        self.browser = BrowserController(use_existing_profile=use_existing_profile)
        self.agent_a = None
        self.agent_b = VisionInstructor()
        self.start_time = None
        self.task_id = None
        self.dataset_dir = None
    
    def run_task(self, question: str, url: str, app_name: str = "Unknown") -> str:
        """
        Main loop with vision-based workflow.
        
        Args:
            question: User's task/question
            url: Starting URL
            app_name: Name of the application
            
        Returns:
            Path to saved dataset
        """
        self.start_time = time.time()
        self.task_id = DatasetManager.generate_task_id(question)
        
        # Create dataset directory
        self.dataset_dir = f"datasets/{self.task_id}"
        os.makedirs(self.dataset_dir, exist_ok=True)
        
        logger.info("Starting vision-based task", question=question, url=url, task_id=self.task_id)
        print(f"\n{'='*70}")
        print(f"🚀 Starting Vision-Based System")
        print(f"{'='*70}")
        print(f"Task: {question}")
        print(f"URL: {url}")
        print(f"App: {app_name}")
        print(f"Task ID: {self.task_id}")
        print(f"{'='*70}\n")
        
        try:
            # Initialize browser and agents
            print(f"Navigating to {url}...")
            self.browser.navigate(url)
            self.agent_a = SimpleExecutor(self.browser)
            self.agent_b.initialize_task(question)
            
            # Step 0: Initial screenshot
            print(f"\n📸 Step 0: Initial Observation")
            print(f"{'-'*70}")
            
            screenshot_path = os.path.join(self.dataset_dir, "step_0_initial.png")
            self.browser.page.screenshot(path=screenshot_path)
            page_title = self.browser.page.title()
            print(f"🤖 Screenshot captured: {page_title}")
            
            # Main loop
            max_steps = 20
            for step in range(1, max_steps + 1):
                print(f"\n📸 Step {step}")
                print(f"{'-'*70}")
                
                # Agent B: Analyze screenshot and provide action
                action = self.agent_b.provide_action(screenshot_path, step)
                
                if not action:
                    print("❌ Agent B failed to provide action (content policy or API issue)")
                    print("   Trying to continue with fallback...")
                    logger.error("Agent B failed", step=step)
                    
                    # Try one more time with a WAIT action to let the page settle
                    print("   Waiting 2 seconds for page to settle...")
                    time.sleep(2)
                    
                    # Capture new screenshot and try again
                    screenshot_path = os.path.join(self.dataset_dir, f"step_{step}_retry.png")
                    self.browser.page.screenshot(path=screenshot_path)
                    
                    action = self.agent_b.provide_action(screenshot_path, step)
                    if not action:
                        print("   Retry also failed. Stopping.")
                        break
                    print("   ✅ Retry succeeded!")
                
                action_type = action.get("action")
                reasoning = action.get("reasoning", "")[:80]
                coords = f"({action.get('x')}, {action.get('y')})" if action.get('x') else ""
                
                print(f"🧠 Agent B: {action_type} {coords}")
                print(f"   Reasoning: {reasoning}")
                
                # Check if task complete
                if action_type == "TASK_COMPLETE":
                    print(f"\n✅ Task completed!")
                    logger.info("Task completed", step=step, total_time=time.time() - self.start_time)
                    break
                
                # Agent A: Execute action
                print(f"⚙️  Agent A executing...")
                result = self.agent_a.execute_action(action)
                
                if result["success"]:
                    print(f"✅ {action_type} successful")
                    logger.info("Action executed", action=action_type, step=step)
                else:
                    print(f"❌ {action_type} failed: {result['error']}")
                    logger.warning("Action failed", action=action_type, error=result['error'], step=step)
                
                # Wait for page to settle and animations
                time.sleep(1.5)  # Increased wait time for UI changes
                
                # Capture new screenshot for next iteration
                action_desc = action_type.lower()
                if action.get('x'):
                    action_desc += f"_{action['x']}_{action['y']}"
                screenshot_path = os.path.join(self.dataset_dir, f"step_{step}_{action_desc}.png")
                self.browser.page.screenshot(path=screenshot_path)
                
            else:
                print(f"\n⚠️  Reached maximum steps ({max_steps})")
                logger.warning("Max steps reached", max_steps=max_steps)
            
            # Save metadata
            self._save_metadata(question, url, app_name)
            
            return self.dataset_dir
        
        except Exception as e:
            logger.error("Task failed", error=str(e), error_type=type(e).__name__)
            print(f"\n❌ Task failed: {e}")
            raise
        
        finally:
            # Close browser
            self.browser.close()
            logger.info("Browser closed")
    
    def _save_metadata(self, question: str, url: str, app_name: str):
        """
        Save task metadata to JSON file.
        
        Args:
            question: Task question
            url: Starting URL
            app_name: Application name
        """
        import json
        
        metadata = {
            "task_id": self.task_id,
            "question": question,
            "url": url,
            "app_name": app_name,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(time.time() - self.start_time, 2),
            "mode": "vision",
            "action_history": self.agent_b.history
        }
        
        metadata_path = os.path.join(self.dataset_dir, "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info("Metadata saved", path=metadata_path)

