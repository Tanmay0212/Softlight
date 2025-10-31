# state_manager.py
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any


class StateManager:
    """Manages the state and history of agent actions during task execution."""
    
    def __init__(self, task: str, url: str):
        self.task = task
        self.url = url
        self.history: List[Dict[str, Any]] = []
        self.attempted_actions = set()
        self.start_time = time.time()
        self.task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def add_step(self, step: int, screenshot: str, dom: str, action: str, success: bool = True):
        """Add a step to the history."""
        step_data = {
            'step': step,
            'action': action,
            'success': success,
            'timestamp': time.time(),
            'elapsed_time': time.time() - self.start_time
        }
        self.history.append(step_data)
        
        # Track attempted actions to avoid loops
        command_line = action.strip().split('\n')[-1].strip()
        self.attempted_actions.add(command_line)
    
    def get_recent_context(self, last_n: int = 3) -> str:
        """
        Get the last N steps as context for the agent.
        This helps the agent understand what it has already tried.
        """
        if not self.history:
            return "No previous actions."
        
        recent = self.history[-last_n:]
        context_lines = ["Previous actions:"]
        for s in recent:
            status = "✓" if s['success'] else "✗"
            context_lines.append(f"{status} Step {s['step']}: {s['action']}")
        
        return "\n".join(context_lines)
    
    def has_attempted(self, action: str) -> bool:
        """Check if an action has already been attempted."""
        return action in self.attempted_actions
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the task execution."""
        return {
            'task': self.task,
            'url': self.url,
            'task_id': self.task_id,
            'total_steps': len(self.history),
            'successful_steps': sum(1 for s in self.history if s['success']),
            'failed_steps': sum(1 for s in self.history if not s['success']),
            'total_time': time.time() - self.start_time,
            'start_time': self.start_time,
        }
    
    def save_results(self, results_dir: str = "results", completed: bool = False):
        """Save the task execution results to a JSON file."""
        os.makedirs(results_dir, exist_ok=True)
        
        result = {
            **self.get_summary(),
            'completed': completed,
            'history': self.history,
        }
        
        filename = f"task_{self.task_id}.json"
        filepath = os.path.join(results_dir, filename)
        
        with open(filepath, "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"📁 Results saved to: {filepath}")
        return filepath

