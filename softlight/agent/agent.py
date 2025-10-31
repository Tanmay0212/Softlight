# agent.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from softlight.core.config.env import Settings

class Agent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=Settings.OPENAI_MODEL_NAME, 
            api_key=Settings.OPENAI_API_KEY, 
            max_tokens=500  # Increased to allow for reasoning
        )
        self.system_prompt = """
You are an expert AI agent controlling a web browser to complete user tasks.

You will receive:
1. A screenshot of the current page
2. A simplified DOM showing interactive elements with unique `bid` identifiers

**Available Commands:**
- CLICK <bid> - Click on an element
- TYPE <bid> "<text>" - Type text into an input field
- SCROLL <direction> - Scroll up or down (direction: UP or DOWN)
- WAIT - Wait 2 seconds for page to load
- FINISH - Task is complete

**Rules:**
1. Analyze the screenshot AND DOM together
2. Take ONE action at a time
3. If you see the information/result the user asked for, use FINISH
4. Always verify elements exist in the DOM before acting on them
5. For search tasks: type query, press enter (or click search button), then return results

**Response Format:**
Provide brief reasoning (1-2 sentences), then on the LAST LINE provide ONLY the command.

Example:
I can see a search input field at bid=3. I'll type the search query there.
TYPE 3 "example search"

Example 2:
The search results are now visible. Task is complete.
FINISH
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
    
    def parse_action(self, action_str: str) -> dict:
        """
        Parse and validate action string.
        Returns a dict with action details.
        """
        lines = action_str.strip().split('\n')
        command_line = lines[-1].strip()  # Last line should be the command
        
        parts = command_line.split(' ', 2)
        action_type = parts[0].upper()
        
        if action_type == "FINISH":
            return {"type": "FINISH"}
        elif action_type == "CLICK":
            if len(parts) < 2:
                raise ValueError("CLICK command requires a bid parameter")
            return {"type": "CLICK", "bid": parts[1]}
        elif action_type == "TYPE":
            if len(parts) < 3:
                raise ValueError("TYPE command requires bid and text parameters")
            bid = parts[1]
            text = parts[2].strip('"\'')
            return {"type": "TYPE", "bid": bid, "text": text}
        elif action_type == "SCROLL":
            direction = parts[1].upper() if len(parts) > 1 else "DOWN"
            return {"type": "SCROLL", "direction": direction}
        elif action_type == "WAIT":
            return {"type": "WAIT"}
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    