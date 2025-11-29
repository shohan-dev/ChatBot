import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "ISP AI Assistant"
    VERSION: str = "1.0.0"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-pro")
    HISTORY_FILE: str = os.path.join("data", "chat_history.json")

settings = Settings()
