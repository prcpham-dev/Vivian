from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

class Settings:
    PORT: int = int(os.getenv("VIVIAN_PORT", "8765"))
    DEFAULT_MODEL: str = os.getenv("VIVIAN_DEFAULT_MODEL", "google/gemini-2.5-flash-preview")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    MAX_SCAN_FILES: int = int(os.getenv("VIVIAN_MAX_SCAN_FILES", "500"))
    # Directory where the server lives; used for locating the data/ cache folder
    BASE_DIR: Path = Path(__file__).parent

settings = Settings()