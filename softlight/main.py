# main.py
import argparse
from softlight.browserController.browser_controller import BrowserController
from softlight.agent.agent import Agent
from softlight.domProcessor.dom_serializer import serialize_dom
# from state_capture import save_state # Assuming this is implemented

def main(task: str, url: str):
    browser = BrowserController()
    agent = Agent()
    
    try:
        browser.navigate(url)
        
        for step in range(15): # Max steps to prevent infinite loops
            print(f"\n--- Step {step} ---")
            
            # 1. OBSERVE
            screenshot, html = browser.get_observation()
            serialized_dom, updated_html = serialize_dom(html)
            
            # This step is crucial: update the live page with our tracking IDs
            browser.inject_serializer_ids(updated_html)
            
            # 2. DECIDE
            action = agent.decide_next_action(task, screenshot, serialized_dom)
            print(f"Agent Action: {action}")
            
            # TODO: save_state(task, step, screenshot, serialized_dom, action)
            
            if action.upper() == "FINISH":
                print("Task complete.")
                break
            
            # 3. ACT
            browser.execute_action(action)
            
    finally:
        browser.close()

if __name__ == "__main__":
    task = "what all button do you see on the page?"
    url = "https://www.google.com/"
    
    main(task=task, url=url)