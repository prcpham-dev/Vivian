import json
import uuid
import glob
from typing import List, Dict, Any
from core.settings_manager import get_project_dir

class ChatHistoryManager:
    def _get_sessions_dir(self, workspace_root: str):
        project_dir = get_project_dir(workspace_root)
        sessions_dir = project_dir / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        return sessions_dir

    def _get_session_path(self, workspace_root: str, session_id: str):
        return self._get_sessions_dir(workspace_root) / f"{session_id}.json"

    def get_all_sessions(self, workspace_root: str) -> List[str]:
        sessions_dir = self._get_sessions_dir(workspace_root)
        files = glob.glob(str(sessions_dir / "*.json"))
        return [f.split("/")[-1].replace(".json", "") for f in files]

    def create_session(self, workspace_root: str) -> str:
        session_id = str(uuid.uuid4())
        db_path = self._get_session_path(workspace_root, session_id)
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return session_id

    def get_session(self, workspace_root: str, session_id: str) -> List[Dict[str, str]]:
        db_path = self._get_session_path(workspace_root, session_id)
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def delete_session(self, workspace_root: str, session_id: str):
        db_path = self._get_session_path(workspace_root, session_id)
        if db_path.exists():
            db_path.unlink()

    def add_message(self, workspace_root: str, session_id: str, role: str, content: str):
        history = self.get_session(workspace_root, session_id)
        history.append({"role": role, "content": content})
        db_path = self._get_session_path(workspace_root, session_id)
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

chat_db = ChatHistoryManager()
