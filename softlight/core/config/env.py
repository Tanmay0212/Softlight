import os

from softlight.core.config.secrets_functions import load_softlight_env


class Settings:

    load_softlight_env()
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")  # GPT-4o for multimodal capabilities

    # Agent A (Executor) Configuration
    AGENT_A_MODEL = os.getenv("AGENT_A_MODEL", "gpt-4o")
    AGENT_A_MAX_TOKENS = int(os.getenv("AGENT_A_MAX_TOKENS", "500"))
    
    # Agent B (Instructor) Configuration
    AGENT_B_MODEL = os.getenv("AGENT_B_MODEL", "gpt-4o")
    AGENT_B_MAX_TOKENS = int(os.getenv("AGENT_B_MAX_TOKENS", "800"))
    
    # Vision Mode Configuration
    VISION_MODE = os.getenv("VISION_MODE", "True").lower() == "true"
    AGENT_B_VISION_MODEL = os.getenv("AGENT_B_VISION_MODEL", "gpt-4o")  # GPT-4 Vision model

    # Hybrid DOM + Vision Configuration
    AGENT_MODE = os.getenv("AGENT_MODE", "vision")  # "vision" or "hybrid"
    DOM_EXTRACTION_ENABLED = os.getenv("DOM_EXTRACTION_ENABLED", "True").lower() == "true"
    VISION_FALLBACK_ENABLED = os.getenv("VISION_FALLBACK_ENABLED", "True").lower() == "true"
    MAX_ELEMENTS = int(os.getenv("MAX_ELEMENTS", "100"))  # Max elements to extract from DOM

    # Agent Configuration (Legacy - for backward compatibility)
    MAX_STEPS = int(os.getenv("MAX_STEPS", "20"))  # Maximum steps before stopping
    AGENT_MAX_TOKENS = int(os.getenv("AGENT_MAX_TOKENS", "500"))
    
    # Browser Configuration
    HEADLESS_MODE = os.getenv("HEADLESS_MODE", "False").lower() == "true"
    BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "60000"))  # milliseconds
    VIEWPORT_WIDTH = int(os.getenv("VIEWPORT_WIDTH", "1920"))
    VIEWPORT_HEIGHT = int(os.getenv("VIEWPORT_HEIGHT", "1080"))
    
    # Action Configuration
    MAX_ACTION_RETRIES = int(os.getenv("MAX_ACTION_RETRIES", "3"))
    # Recovery loop when an action fails (re-observe + re-plan per step)
    RECOVERY_MAX_ATTEMPTS = int(os.getenv("RECOVERY_MAX_ATTEMPTS", "2"))
    
    # Output Configuration
    DATASET_DIR = os.getenv("DATASET_DIR", "datasets")
    DATASET_ROOT = os.getenv("DATASET_ROOT", "datasets")  # For two-agent system
    RESULTS_DIR = os.getenv("RESULTS_DIR", "results")
    SAVE_SCREENSHOTS = os.getenv("SAVE_SCREENSHOTS", "True").lower() == "true"
    SAVE_RESULTS = os.getenv("SAVE_RESULTS", "True").lower() == "true"
