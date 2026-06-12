from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

class Settings:
    BASE_DIR: Path = Path(__file__).resolve().parent
    PORT: int = int(os.getenv("VIVIAN_PORT", "8765"))
    MAX_SCAN_FILES: int = int(os.getenv("VIVIAN_MAX_SCAN_FILES", "500"))
    LLM = ChatGoogleGenerativeAI(
        model=os.getenv("VIVIAN_DEFAULT_MODEL", "gemini-2.5-flash"),
        api_key=os.getenv("CHAT_API_KEY"),
        max_tokens=1024,
        streaming=True,
    )

settings = Settings()