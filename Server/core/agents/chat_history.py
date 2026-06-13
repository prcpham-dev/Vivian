import json
import os
from typing import List, Dict, Any
from core.settings_manager import get_project_dir

class ChatHistoryManager:
    def _get_chat_file_path(self, workspace_root: str):
        project_dir = get_project_dir(workspace_root)
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir / "chat.json"

    def clear_history(self, workspace_root: str):
        db_path = self._get_chat_file_path(workspace_root)
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

    def get_history(self, workspace_root: str) -> List[Dict[str, str]]:
        db_path = self._get_chat_file_path(workspace_root)
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def add_message(self, workspace_root: str, role: str, content: str):
        history = self.get_history(workspace_root)
        history.append({"role": role, "content": content})
        db_path = self._get_chat_file_path(workspace_root)
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

chat_db = ChatHistoryManager()
