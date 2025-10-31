# orchestrator.py - Two-Agent Orchestrator
import time
from datetime import datetime
from softlight.browserController.browser_controller import BrowserController
from softlight.agent.executor_agent import ExecutorAgent
from softlight.agent.instructor_agent import InstructorAgent
from softlight.capture.screenshot_manager import ScreenshotManager
from softlight.dataset.dataset_manager import DatasetManager
from softlight.domProcessor.dom_serializer import serialize_dom
from softlight.core.config.env import Settings
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


class TwoAgentOrchestrator:
    """
    Orchestrates the communication loop between Agent A (Executor) and Agent B (Instructor).
    
    Flow:
    1. Agent B initializes with task
    2. Agent A observes page → reports to Agent B
    3. Agent B provides instruction → Agent A executes
    4. Repeat until task complete
    5. Save dataset
    """
    
    def __init__(self, use_existing_profile: bool = False):
        self.browser = BrowserController(use_existing_profile=use_existing_profile)
        self.screenshot_mgr = None  # Initialized after browser setup
        self.agent_a = None  # Initialized after browser setup
        self.agent_b = InstructorAgent()
        self.conversation_log = []
        self.start_time = None
    
    def run_task(self, question: str, url: str, app_name: str = "Unknown") -> str:
        """
        Main loop coordinating Agent A and Agent B.
        
        Args:
            question: User's task/question
            url: Starting URL
            app_name: Name of the application
            
        Returns:
            Path to saved dataset
        """
        self.start_time = time.time()
        task_id = DatasetManager.generate_task_id(question)
        
        logger.info("Starting two-agent task", question=question, url=url, task_id=task_id)
        print(f"\n{'='*70}")
        print(f"🚀 Starting Two-Agent System")
        print(f"{'='*70}")
        print(f"Task: {question}")
        print(f"URL: {url}")
        print(f"App: {app_name}")
        print(f"Task ID: {task_id}")
        print(f"{'='*70}\n")
        
        try:
            # Initialize browser and agents
            self.browser.navigate(url)
            self.screenshot_mgr = ScreenshotManager(self.browser.page)
            self.agent_a = ExecutorAgent(self.browser)
            self.agent_b.initialize_task(question, url)
            
            # Step 0: Initial observation
            print(f"\n📸 Step 0: Initial Observation")
            print(f"{'-'*70}")
            
            screenshot, html = self.browser.get_observation()
            serialized_dom, updated_html = serialize_dom(html)
            self.browser.inject_serializer_ids(updated_html)
            
            # Capture initial state
            self.screenshot_mgr.capture_state(0, "initial", task_id)
            
            # Agent A observes and reports to Agent B
            agent_a_observation = self.agent_a.observe_and_report(screenshot, serialized_dom, 0)
            print(f"🤖 Agent A: {agent_a_observation[:200]}...")
            
            # Main loop
            for step in range(1, Settings.MAX_STEPS + 1):
                print(f"\n📸 Step {step}")
                print(f"{'-'*70}")
                
                # Agent B provides instruction based on Agent A's observation
                instruction = self.agent_b.provide_instruction(agent_a_observation, screenshot)
                print(f"🧠 Agent B: {instruction}")
                
                # Log conversation
                conversation_entry = {
                    "step_num": step - 1,
                    "agent_a_observation": agent_a_observation,
                    "screenshot": f"step_{step-1}.png",
                    "agent_b_instruction": instruction
                }
                
                # Check if complete
                if "TASK_COMPLETE" in instruction.upper() or self.agent_b.is_task_complete(agent_a_observation):
                    print(f"\n✅ Task Complete!")
                    print(f"{'-'*70}")
                    conversation_entry["agent_a_action"] = "TASK_COMPLETE"
                    conversation_entry["agent_a_result"] = "Task completed successfully"
                    self.conversation_log.append(conversation_entry)
                    break
                
                # Agent A executes instruction
                print(f"⚙️  Agent A executing...")
                result = self.agent_a.execute_instruction(instruction, serialized_dom)
                
                # Update conversation log with execution results
                conversation_entry["agent_a_action"] = result["action"]
                conversation_entry["agent_a_result"] = result["result"]
                
                # Capture state after execution
                screenshot, html = self.browser.get_observation()
                serialized_dom, updated_html = serialize_dom(html)
                self.browser.inject_serializer_ids(updated_html)
                
                action_desc = result["action"].replace(" ", "_")[:50]
                self.screenshot_mgr.capture_state(step, action_desc, task_id)
                
                # Agent A observes and reports result to Agent B
                agent_a_observation = self.agent_a.observe_and_report(screenshot, serialized_dom, step)
                observation_with_context = f"Previous action: {result['action']}. Result: {result['result']}. Current observation: {agent_a_observation}"
                
                conversation_entry["agent_a_next_observation"] = agent_a_observation
                self.conversation_log.append(conversation_entry)
                
                print(f"✅ Action completed: {result['action']}")
                print(f"📋 Result: {result['result']}")
                
                # Update observation for next iteration
                agent_a_observation = observation_with_context
                
            else:
                # Max steps reached
                print(f"\n⚠️  Max steps ({Settings.MAX_STEPS}) reached without completion")
                logger.warning("Max steps reached", task_id=task_id, steps=Settings.MAX_STEPS)
            
            # Save dataset
            duration = time.time() - self.start_time
            dataset_path = self._save_dataset(question, task_id, app_name, url, duration)
            
            print(f"\n{'='*70}")
            print(f"📊 Task Summary")
            print(f"{'='*70}")
            print(f"Total Steps: {len(self.conversation_log)}")
            print(f"Duration: {duration:.2f}s")
            print(f"Dataset: {dataset_path}")
            print(f"{'='*70}\n")
            
            return dataset_path
            
        except Exception as e:
            logger.error("Orchestrator error", error=str(e), task_id=task_id)
            print(f"\n❌ Error: {e}")
            raise
        
        finally:
            self.browser.close()
    
    def _save_dataset(
        self,
        question: str,
        task_id: str,
        app_name: str,
        url: str,
        duration: float
    ) -> str:
        """
        Save the complete workflow dataset.
        
        Args:
            question: User's question
            task_id: Task identifier
            app_name: Application name
            url: Starting URL
            duration: Task duration in seconds
            
        Returns:
            Path to saved dataset
        """
        metadata = {
            "app": app_name,
            "url": url,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "completed": any("TASK_COMPLETE" in entry.get("agent_b_instruction", "").upper() 
                           for entry in self.conversation_log)
        }
        
        dataset_path = DatasetManager.save_workflow(
            task_id=task_id,
            question=question,
            conversation_log=self.conversation_log,
            metadata=metadata
        )
        
        logger.info("Dataset saved", task_id=task_id, path=dataset_path)
        return dataset_path

