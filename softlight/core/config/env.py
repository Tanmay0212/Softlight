import os

from softlight.core.config.secrets_functions import load_softlight_env


class Settings:

    load_softlight_env()
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    OPENAI_MODEL_NAME = "gpt-4o"  # GPT-4o is ideal for its multimodal capabilities

    # Browser Configuration
    HEADLESS_MODE = False

    # Output Configuration
    DATASET_DIR = "datasets"
