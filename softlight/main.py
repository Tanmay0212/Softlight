# main.py - Multi-Mode UI Automation System Entry Point
from softlight.orchestrator_vision import VisionOrchestrator
from softlight.orchestrator_hybrid import HybridOrchestrator
from softlight.core.config.env import Settings
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


def main(question: str, url: str, app_name: str = "Unknown", use_profile: bool = False, mode: str = None):
    """
    Main entry point for the UI automation system.
    
    Supports two modes:
    - Vision: Pure vision-based (screenshot + coordinates)
    - Hybrid: DOM + Vision (semantic selectors + coordinate fallback)
    
    This system uses two agents:
    - Agent A (Simple Executor): Executes actions using Playwright primitives
    - Agent B (Instructor): Analyzes state and provides actions
      * Vision mode: Analyzes screenshots only
      * Hybrid mode: Analyzes DOM + text + screenshots
    
    Args:
        question: User's task/question (e.g., "open bot issue 2 and change its priority to 'High'")
        url: Starting URL for the task
        app_name: Name of the application for dataset organization
        use_profile: If True, uses existing Chrome profile with logged-in sessions
        mode: "vision" or "hybrid" (default: from Settings.AGENT_MODE)
        
    Returns:
        Path to the saved dataset
    """
    # Determine mode
    mode = mode or Settings.AGENT_MODE
    mode = mode.lower()
    
    if mode not in ["vision", "hybrid"]:
        logger.warning(f"Invalid mode '{mode}', defaulting to 'vision'")
        mode = "vision"
    
    # Select orchestrator based on mode
    if mode == "hybrid":
        orchestrator = HybridOrchestrator(use_existing_profile=use_profile)
    else:
        orchestrator = VisionOrchestrator(use_existing_profile=use_profile)
    
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
    # =============================================================================
    # CONFIGURATION
    # =============================================================================
    
    # Set mode: "vision" (screenshot only) or "hybrid" (DOM + vision)
    mode = "hybrid"  # Change to "vision" to test vision-only mode
    
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

    question = "create a new project with name 'Bot project 7'"
    url = "https://linear.app/softlight-assesment/team/SOF/active"  # Update with your workspace
    app_name = "Linear"
    use_profile = True

    # question = "add a description to bot issue 6 saying 'this is a test description'"
    # url = "https://linear.app/softlight-assesment/issue/SOF-11/bot-issue-6"  # Update with your workspace
    # app_name = "Linear"
    # use_profile = True

    # question = "open bot issue 2 and change its priority to 'High'"
    # url = "https://linear.app/softlight-assesment/team/SOF/active"  # Update with your workspace
    # app_name = "Linear"
    # use_profile = True
    
    # Example 3: Filter Issues in Linear
    # question = "How do I filter issues by status in Linear?"
    # url = "https://linear.app/test916/team/TES/active"
    # app_name = "Linear"
    # use_profile = True
    
    # =============================================================================
    # EXECUTION
    # =============================================================================
    
    print("\n" + "="*70)
    print(f"SOFTLIGHT - UI Automation System ({mode.upper()} mode)")
    print("="*70)
    print(f"\nRunning task: {question}")
    print(f"Starting at: {url}")
    print(f"App: {app_name}")
    print(f"Mode: {mode.upper()}")
    print(f"Using separate profile: {use_profile}\n")
    
    if mode == "hybrid":
        print("🔬 HYBRID MODE:")
        print("   - DOM extraction for semantic understanding")
        print("   - Stable selectors (role, aria-label, name, id)")
        print("   - Coordinate fallback for icons/custom controls")
        print("   - More resilient to layout changes\n")
    else:
        print("👁️  VISION MODE:")
        print("   - Pure screenshot analysis")
        print("   - Pixel-perfect coordinate clicks")
        print("   - Works with any UI (including canvas/icons)\n")
    
    if use_profile:
        print("ℹ️  Using separate Chrome profile for automation")
        print("   Your main Chrome browser can stay open!")
        print("   First run: You'll need to log into Linear manually")
        print("   Future runs: Login will be remembered\n")
    
    dataset_path = main(question=question, url=url, app_name=app_name, use_profile=use_profile, mode=mode)
    
    if dataset_path:
        print(f"\n✅ Success! Dataset saved to: {dataset_path}")
        print("\nYou can find:")
        print(f"  - Screenshots: {dataset_path}/step_*.png")
        print(f"  - Metadata: {dataset_path}/metadata.json")
    else:
        print("\n⚠️  Task did not complete successfully.")
