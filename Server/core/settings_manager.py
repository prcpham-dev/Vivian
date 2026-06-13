import os, json
from pathlib import Path
from dotenv import load_dotenv, set_key
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

BASE_DIR: Path = Path(__file__).resolve().parent.parent

def get_project_dir(workspace_root: str) -> Path:
    """Returns a global storage directory for a specific workspace: ~/.vivian/projects/<safe_name>"""
    home = Path.home()
    safe_name = workspace_root.replace("/", "_").replace("\\", "_").strip("_")
    if not safe_name:
        safe_name = "default_project"
    
    project_dir = home / ".vivian" / "projects" / safe_name
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir

_ENV_PATH = BASE_DIR / ".env"
_SETTINGS_JSON = BASE_DIR / "settings.json"

def _read() -> dict:
    return json.loads(_SETTINGS_JSON.read_text(encoding="utf-8"))

def _write(data: dict):
    _SETTINGS_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")

# Model
def get_model() -> str:
    return _read()["VIVIAN_DEFAULT_MODEL"]

def update_model(model: str):
    d = _read(); d["VIVIAN_DEFAULT_MODEL"] = model; _write(d)

# Max_scan_file
def get_max_scan_files() -> int:
    return int(_read()["VIVIAN_MAX_SCAN_FILES"])

def update_max_scan_files(n: int):
    d = _read(); d["VIVIAN_MAX_SCAN_FILES"] = str(n); _write(d)

# APi key
def has_api_key() -> bool:
    return bool(os.environ.get("CHAT_API_KEY", ""))

def update_api_key(api_key: str):
    if not _ENV_PATH.exists():
        _ENV_PATH.touch()
    set_key(str(_ENV_PATH), "CHAT_API_KEY", api_key)
    os.environ["CHAT_API_KEY"] = api_key

def get_llm() -> ChatGoogleGenerativeAI:
    if not has_api_key():
        raise ValueError("API key is not set.")
        
    key = os.environ.get("CHAT_API_KEY", "")
    return ChatGoogleGenerativeAI(
        model=get_model(),
        api_key=key,
        max_tokens=8192,
        streaming=True,
    )

