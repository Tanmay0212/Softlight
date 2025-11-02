# main.py - Two-Agent System Main Entry Point
from softlight.orchestrator import TwoAgentOrchestrator
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


def main(question: str, url: str, app_name: str = "Unknown", use_profile: bool = False):
    """
    Main entry point for the two-agent UI capture system.
    
    This system uses two agents:
    - Agent A (Executor): Observes pages, executes actions, reports results
    - Agent B (Instructor): Analyzes observations, provides step-by-step instructions
    
    Args:
        question: User's task/question (e.g., "Search for Softlight on Google")
        url: Starting URL for the task
        app_name: Name of the application for dataset organization
        use_profile: If True, uses existing Chrome profile with logged-in sessions
        
    Returns:
        Path to the saved dataset
    """
    orchestrator = TwoAgentOrchestrator(use_existing_profile=use_profile)
    
    try:
        dataset_path = orchestrator.run_task(question, url, app_name)
        return dataset_path
        
    except KeyboardInterrupt:
        logger.info("Task interrupted by user")
        print("\n\n⏸️  Task interrupted by user.")
        return None
        
    except Exception as e:
        logger.error("Task failed", error=str(e), error_type=type(e).__name__)
        print(f"\n❌ Task failed: {e}")
        raise


if __name__ == "__main__":
    # Example 1: Google Search (no login needed)
    # question = "Search for Softlight on Google"
    # url = "https://www.google.com/"
    # app_name = "Google"
    # use_profile = False
    
    # Example 2: Linear Tasks (requires login - use existing Chrome profile)
    # question = "give me list of projects that I have"
    # url = "https://linear.app/softlight-assesment/team/SOF/active"  # Update with your workspace
    # app_name = "Linear"
    # use_profile = True  # Use existing Chrome profile with logged-in sessions

    # question = "select 'Import your data (4)' issue and then assign it to Tanmay Bhardwaj"
    # url = "https://linear.app/softlight-assesment/team/SOF/active"  # Update with your workspace
    # app_name = "Linear"
    # use_profile = True

    question = "select issue with name 'Bot issue 1' and then set its priority to 'High'"
    url = "https://linear.app/softlight-assesment/team/SOF/active"  # Update with your workspace
    app_name = "Linear"
    use_profile = True
    
    # Example 3: Filter Issues in Linear
    # question = "How do I filter issues by status in Linear?"
    # url = "https://linear.app/test916/team/TES/active"
    # app_name = "Linear"
    # use_profile = True
    
    print("\n" + "="*70)
    print("SOFTLIGHT - Two-Agent UI Capture System")
    print("="*70)
    print(f"\nRunning task: {question}")
    print(f"Starting at: {url}")
    print(f"App: {app_name}")
    print(f"Using separate profile: {use_profile}\n")
    
    if use_profile:
        print("ℹ️  Using separate Chrome profile for automation")
        print("   Your main Chrome browser can stay open!")
        print("   First run: You'll need to log into Linear manually")
        print("   Future runs: Login will be remembered\n")
    
    dataset_path = main(question=question, url=url, app_name=app_name, use_profile=use_profile)
    
    if dataset_path:
        print(f"\n✅ Success! Dataset saved to: {dataset_path}")
        print("\nYou can find:")
        print(f"  - Screenshots: {dataset_path}/step_*.png")
        print(f"  - Metadata: {dataset_path}/metadata.json")
    else:
        print("\n⚠️  Task did not complete successfully.")
