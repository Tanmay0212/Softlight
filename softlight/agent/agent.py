# agent.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from softlight.core.config.env import Settings

class Agent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=Settings.OPENAI_MODEL_NAME, 
            api_key=Settings.OPENAI_API_KEY, 
            max_tokens=100
        )
        self.system_prompt = """
You are an expert AI agent controlling a web browser. Your goal is to complete a task given by the user.
You will be given a screenshot of the current page, and a simplified DOM showing only the elements you can interact with, each with a unique `bid`.

Analyze the screenshot and the DOM to determine the single next action to take.
Your response must be a single command in one of these formats:
- CLICK <bid>
- TYPE <bid> "<text_to_type>"
- FINISH

Think step-by-step. What is the most logical action to get closer to the goal?
"""

    def decide_next_action(self, task: str, screenshot_b64: str, serialized_dom: str) -> str:
        prompt = f"""
Current Task: "{task}"

Simplified DOM:
{serialized_dom}

Based on the screenshot and the DOM, what is the next command to execute?
"""
        
        message = HumanMessage(
            content=[
                {"type": "text", "text": self.system_prompt + prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}},
            ]
        )
        
        response = self.llm.invoke([message])
        action = response.content.strip()
        return action