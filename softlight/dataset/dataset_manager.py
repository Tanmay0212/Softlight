# dataset_manager.py
import json
import os
from datetime import datetime
from typing import List, Dict
from softlight.core.config.env import Settings
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


class DatasetManager:
    """
    Manages organization and storage of workflow datasets.
    """
    
    @staticmethod
    def save_workflow(
        task_id: str,
        question: str,
        conversation_log: List[Dict],
        metadata: Dict
    ) -> str:
        """
        Save complete workflow dataset with conversation and metadata.
        
        Args:
            task_id: Unique task identifier
            question: Original user question/task
            conversation_log: List of conversation steps between agents
            metadata: Additional metadata (app, url, timing, etc.)
            
        Returns:
            Path to saved dataset directory
        """
        dataset_dir = os.path.join(Settings.DATASET_ROOT, task_id)
        os.makedirs(dataset_dir, exist_ok=True)
        
        # Prepare metadata content
        metadata_content = {
            "task_id": task_id,
            "user_question": question,
            "app": metadata.get("app", "Unknown"),
            "url": metadata.get("url", ""),
            "completed": metadata.get("completed", True),
            "total_steps": len(conversation_log),
            "duration": metadata.get("duration", 0),
            "timestamp": metadata.get("timestamp", datetime.now().isoformat()),
            "conversation": conversation_log
        }
        
        # Save metadata.json
        metadata_path = os.path.join(dataset_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata_content, f, indent=2)
        
        logger.info("Workflow saved", task_id=task_id, path=dataset_dir, steps=len(conversation_log))
        return dataset_dir
    
    @staticmethod
    def generate_task_id(question: str) -> str:
        """
        Generate a unique task ID from question and timestamp.
        
        Args:
            question: User's question/task
            
        Returns:
            Unique task ID string
        """
        import re
        
        # Extract key words from question
        words = re.findall(r'\w+', question.lower())
        # Take first 3-4 meaningful words
        key_words = [w for w in words if len(w) > 2][:4]
        slug = "_".join(key_words)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_id = f"{slug}_{timestamp}"
        
        return task_id
    
    @staticmethod
    def create_dataset_summary(dataset_root: str = None) -> Dict:
        """
        Create a summary of all workflows in the dataset.
        
        Args:
            dataset_root: Root directory of datasets (defaults to Settings.DATASET_ROOT)
            
        Returns:
            Summary dictionary
        """
        dataset_root = dataset_root or Settings.DATASET_ROOT
        
        if not os.path.exists(dataset_root):
            return {"total_workflows": 0, "workflows": []}
        
        workflows = []
        total_steps = 0
        total_duration = 0
        
        # Iterate through dataset directories
        for task_dir in os.listdir(dataset_root):
            task_path = os.path.join(dataset_root, task_dir)
            if not os.path.isdir(task_path):
                continue
            
            metadata_path = os.path.join(task_path, "metadata.json")
            if not os.path.exists(metadata_path):
                continue
            
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                
                workflows.append({
                    "task_id": metadata.get("task_id"),
                    "question": metadata.get("user_question"),
                    "app": metadata.get("app"),
                    "steps": metadata.get("total_steps", 0),
                    "duration": metadata.get("duration", 0),
                    "completed": metadata.get("completed", False)
                })
                
                total_steps += metadata.get("total_steps", 0)
                total_duration += metadata.get("duration", 0)
                
            except Exception as e:
                logger.warning("Failed to read metadata", path=metadata_path, error=str(e))
                continue
        
        summary = {
            "total_workflows": len(workflows),
            "total_steps": total_steps,
            "total_duration": total_duration,
            "workflows": workflows,
            "generated_at": datetime.now().isoformat()
        }
        
        # Save summary
        summary_path = os.path.join(dataset_root, "dataset_summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        
        logger.info("Dataset summary created", workflows=len(workflows), path=summary_path)
        return summary

