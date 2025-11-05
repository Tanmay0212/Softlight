# orchestrator_hybrid.py - Hybrid DOM + Vision Orchestrator
"""
HybridOrchestrator: Coordinates hybrid DOM + Vision workflow.

Flow (based on browser-use model):
1. Perception: Build PageState (DOM + text + screenshot)
2. Decision: HybridInstructor analyzes PageState → returns action with bid/selector + coords
3. Execution: SimpleExecutor tries selectors first, falls back to coordinates
4. Wait: Page settle
5. Repeat: Until TASK_COMPLETE or max_steps

Key difference from VisionOrchestrator:
- Passes full PageState to instructor (not just screenshot)
- Logs which selection method succeeded (selector vs coordinates)
- More stable due to DOM-first strategy
"""
import time
import os
from datetime import datetime
from softlight.browserController.browser_controller import BrowserController
from softlight.agent.simple_executor import SimpleExecutor
from softlight.agent.hybrid_instructor import HybridInstructor
from softlight.state.page_state import build_page_state
from softlight.dataset.dataset_manager import DatasetManager
from softlight.core.config.env import Settings
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


class HybridOrchestrator:
    """
    Orchestrates hybrid DOM + Vision workflow.
    
    Main loop:
    1. Build PageState (DOM extraction + text + screenshot)
    2. HybridInstructor provides action (bid/selector preferred, coords fallback)
    3. SimpleExecutor executes (selector-first strategy)
    4. Wait for page to settle
    5. Repeat until complete
    """
    
    def __init__(self, use_existing_profile: bool = False):
        """
        Initialize orchestrator.
        
        Args:
            use_existing_profile: Use existing Chrome profile with saved sessions
        """
        self.browser = BrowserController(use_existing_profile=use_existing_profile)
        self.agent_a = None
        self.agent_b = HybridInstructor()
        self.start_time = None
        self.task_id = None
        self.dataset_dir = None
        self.max_elements = Settings.MAX_ELEMENTS
    
    def run_task(self, question: str, url: str, app_name: str = "Unknown") -> str:
        """
        Main loop with hybrid DOM + Vision workflow.
        
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
        
        logger.info("Starting hybrid task", question=question, url=url, task_id=self.task_id)
        print(f"\n{'='*70}")
        print(f"🚀 Starting Hybrid DOM + Vision System")
        print(f"{'='*70}")
        print(f"Task: {question}")
        print(f"URL: {url}")
        print(f"App: {app_name}")
        print(f"Task ID: {self.task_id}")
        print(f"Mode: HYBRID (DOM + Vision)")
        print(f"{'='*70}\n")
        
        try:
            # Initialize browser and agents
            print(f"Navigating to {url}...")
            self.browser.navigate(url)
            self.agent_a = SimpleExecutor(self.browser)
            self.agent_b.initialize_task(question)
            
            # Step 0: Initial perception
            print(f"\n📸 Step 0: Initial Perception")
            print(f"{'-'*70}")
            
            screenshot_path = os.path.join(self.dataset_dir, "step_0_initial.png")
            page_state = build_page_state(
                self.browser.page,
                screenshot_path,
                max_elements=self.max_elements
            )
            
            print(f"🔍 DOM: Extracted {len(page_state.elements)} actionable elements")
            print(f"📄 Text: {len(page_state.page_text)} chars visible text")
            print(f"📸 Screenshot: {page_state.title}")
            
            # Main loop
            max_steps = 20
            for step in range(1, max_steps + 1):
                print(f"\n📸 Step {step}")
                print(f"{'-'*70}")
                
                # Agent B: Analyze PageState (DOM + text + screenshot)
                action = self.agent_b.provide_action(page_state, step)
                
                if not action:
                    print("❌ Agent B failed to provide action")
                    logger.error("Agent B failed", step=step)
                    
                    # Retry once
                    print("   Retrying...")
                    time.sleep(2)
                    
                    screenshot_path = os.path.join(self.dataset_dir, f"step_{step}_retry.png")
                    page_state = build_page_state(
                        self.browser.page,
                        screenshot_path,
                        max_elements=self.max_elements
                    )
                    
                    action = self.agent_b.provide_action(page_state, step)
                    if not action:
                        print("   Retry failed. Stopping.")
                        break
                    print("   ✅ Retry succeeded!")
                
                action_type = action.get("action")
                reasoning = action.get("reasoning", "")[:80]
                
                # Format action description
                action_desc = f"🧠 Agent B: {action_type}"
                if action.get("bid"):
                    action_desc += f" [bid={action['bid']}]"
                    # Show element details
                    elem = page_state.get_element_by_bid(action['bid'])
                    if elem:
                        action_desc += f" ({elem.tag}"
                        if elem.text:
                            action_desc += f" '{elem.text[:30]}'"
                        action_desc += ")"
                if action.get("x") and action.get("y"):
                    action_desc += f" coords=({action['x']}, {action['y']})"
                
                print(action_desc)
                print(f"   Reasoning: {reasoning}")
                
                # Check if task complete
                if action_type == "TASK_COMPLETE":
                    print(f"\n✅ Task completed!")
                    logger.info("Task completed", step=step, total_time=time.time() - self.start_time)
                    break
                
                # Agent A: Execute action (selector-first strategy)
                print(f"⚙️  Agent A executing...")
                result = self.agent_a.execute_action(action, page_state=page_state)
                
                if result["success"]:
                    method = result.get("method", "unknown")
                    print(f"✅ {action_type} successful (method: {method})")
                    
                    # FIX 3: Enhanced logging with method tracking
                    logger.info(
                        "Action executed",
                        action=action_type,
                        method=method,
                        step=step,
                        bid=action.get("bid"),
                        fallback_used="data-bid" not in method
                    )
                    
                    # FIX 1: Check for DOM changes after CLICK actions (modals, dropdowns)
                    if action_type == "CLICK":
                        from softlight.state.page_state import detect_dom_changes_and_reinject
                        
                        print(f"   Checking for dynamic content...")
                        dom_changed = detect_dom_changes_and_reinject(
                            self.browser.page,
                            max_elements=self.max_elements
                        )
                        
                        if dom_changed:
                            print(f"   ✅ New elements detected and bids injected")
                            logger.info("Dynamic content handled", step=step)
                            # Wait for re-injection to settle
                            time.sleep(0.5)
                else:
                    print(f"❌ {action_type} failed: {result['error']}")
                    logger.warning("Action failed", action=action_type, error=result['error'], step=step)
                
                # Wait for page to settle
                time.sleep(1.5)
                
                # Capture new PageState for next iteration
                action_desc_file = action_type.lower()
                if action.get("bid"):
                    action_desc_file += f"_bid{action['bid']}"
                elif action.get('x'):
                    action_desc_file += f"_{action['x']}_{action['y']}"
                
                screenshot_path = os.path.join(self.dataset_dir, f"step_{step}_{action_desc_file}.png")
                page_state = build_page_state(
                    self.browser.page,
                    screenshot_path,
                    max_elements=self.max_elements
                )
                
                print(f"🔍 New state: {len(page_state.elements)} elements, {len(page_state.page_text)} chars text")
            
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
            "mode": "hybrid",
            "max_elements": self.max_elements,
            "action_history": self.agent_b.history
        }
        
        metadata_path = os.path.join(self.dataset_dir, "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info("Metadata saved", path=metadata_path)

