# instructor_agent.py - Agent B (Instructor)
from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from softlight.core.config.env import Settings
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


class InstructorAgent:
    """
    Agent B - The Instructor Agent
    
    Responsibilities:
    - Understand user's task/question
    - Analyze Agent A's observations
    - Provide step-by-step instructions to Agent A
    - Determine when the task is complete
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=Settings.AGENT_B_MODEL,
            api_key=Settings.OPENAI_API_KEY,
            max_tokens=Settings.AGENT_B_MAX_TOKENS
        )
        self.task_context = None
        self.conversation_history = []
        self.system_prompt = """
You are Agent B, an instructor agent that guides Agent A through completing tasks on web applications.

Your responsibilities:
1. UNDERSTAND: Analyze the user's task/question to know what needs to be accomplished
2. GUIDE: Provide clear, step-by-step instructions to Agent A
3. ANALYZE: Interpret Agent A's observations to understand the current state
4. DECIDE: Determine the next action needed to progress toward the goal
5. COMPLETE: Recognize when the task has been successfully accomplished

When providing instructions:
- Be specific and reference bid numbers from Agent A's observations
- Give ONE clear instruction at a time
- Use natural language that Agent A can convert to actions
- Examples: "Click the search button (bid=5)" or "Type 'example' in the search box (bid=3)"
- IMPORTANT: If a modal/dialog is open, ONLY interact with elements INSIDE the modal, ignore background elements
- For modals: Look for input fields, text areas, and buttons within the modal first
- Common modal elements: "Issue title", "Description", "Submit", "Create", "Save", "Cancel" buttons

When the task is complete, say:
TASK_COMPLETE: [brief summary of what was accomplished]

Remember: Agent A executes, you instruct. Guide them step-by-step to complete the user's task.
"""
    
    def initialize_task(self, question: str, url: str):
        """
        Initialize with the user's task and starting context.
        
        Args:
            question: User's question/task
            url: Starting URL
        """
        self.task_context = {
            "question": question,
            "starting_url": url,
            "goal": self._extract_goal(question)
        }
        self.conversation_history = []
        
        logger.info("Agent B initialized", question=question, url=url)
    
    def provide_instruction(self, agent_a_report: str, screenshot_b64: str = None) -> str:
        """
        Analyze Agent A's report and provide the next instruction.
        
        Args:
            agent_a_report: Agent A's observation or execution result
            screenshot_b64: Optional screenshot for visual analysis
            
        Returns:
            Instruction for Agent A or TASK_COMPLETE
        """
        # Add Agent A's report to conversation history
        self.conversation_history.append({
            "role": "agent_a",
            "content": agent_a_report
        })
        
        # Build the prompt for Agent B
        prompt = self._build_instruction_prompt(agent_a_report)
        
        # Create messages for the LLM
        messages = [
            SystemMessage(content=self.system_prompt),
        ]
        
        # Add conversation history
        for entry in self.conversation_history[-5:]:  # Last 5 exchanges
            if entry["role"] == "agent_a":
                messages.append(HumanMessage(content=f"Agent A reports: {entry['content']}"))
            elif entry["role"] == "agent_b":
                messages.append(AIMessage(content=entry["content"]))
        
        # Add current prompt
        if screenshot_b64:
            messages.append(HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}},
                ]
            ))
        else:
            messages.append(HumanMessage(content=prompt))
        
        # Get instruction from LLM
        logger.debug("Agent B providing instruction")
        response = self.llm.invoke(messages)
        instruction = response.content.strip()
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "agent_b",
            "content": instruction
        })
        
        logger.info("Agent B instruction", instruction=instruction[:200])
        return instruction
    
    def is_task_complete(self, agent_a_report: str) -> bool:
        """
        Determine if the task has been completed based on Agent A's report.
        
        Args:
            agent_a_report: Agent A's latest report
            
        Returns:
            True if task is complete, False otherwise
        """
        # Check if the last instruction contained TASK_COMPLETE
        if self.conversation_history:
            last_instruction = self.conversation_history[-1].get("content", "")
            if "TASK_COMPLETE" in last_instruction.upper():
                return True
        
        # Use LLM to assess completion
        prompt = f"""
Task: {self.task_context['question']}
Goal: {self.task_context['goal']}

Agent A's latest report:
{agent_a_report}

Has the task been completed successfully? Answer ONLY with YES or NO.
"""
        
        message = HumanMessage(content=[{"type": "text", "text": prompt}])
        response = self.llm.invoke([message])
        answer = response.content.strip().upper()
        
        return "YES" in answer
    
    def _extract_goal(self, question: str) -> str:
        """
        Extract the core goal from the user's question.
        
        Args:
            question: User's question/task
            
        Returns:
            Simplified goal statement
        """
        prompt = f"""
User's question: "{question}"

Extract the core goal/action that needs to be accomplished.
Respond in one concise sentence.

Examples:
- Question: "Search for Softlight on Google" → Goal: "Perform a search for 'Softlight' on Google"
- Question: "How do I create a project in Linear?" → Goal: "Create a new project in Linear"
"""
        
        message = HumanMessage(content=[{"type": "text", "text": prompt}])
        response = self.llm.invoke([message])
        goal = response.content.strip()
        
        logger.debug("Extracted goal", question=question, goal=goal)
        return goal
    
    def _build_instruction_prompt(self, agent_a_report: str) -> str:
        """
        Build a prompt for Agent B to generate the next instruction.
        
        Args:
            agent_a_report: Agent A's observation or result
            
        Returns:
            Prompt string
        """
        prompt = f"""
User's Task: {self.task_context['question']}
Goal: {self.task_context['goal']}

Agent A's Report:
{agent_a_report}

Based on Agent A's report, what should Agent A do next to accomplish the task?

Provide ONE clear instruction referencing specific elements by their bid numbers.
If the task is complete, respond with: TASK_COMPLETE: [summary]

Your instruction:
"""
        return prompt

