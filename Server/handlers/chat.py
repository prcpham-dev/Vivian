from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from core.agents.chat_history import chat_db

router = APIRouter(prefix="/chat", tags=["chat"])

class AddMessageRequest(BaseModel):
    role: str = "user"
    content: str

@router.post("/start")
def start_chat(workspace_root: str):
    """Starts a new chat by clearing the history for the workspace."""
    chat_db.clear_history(workspace_root)
    return {"status": "success", "message": "Chat history cleared."}

@router.get("/history")
def get_history(workspace_root: str):
    return chat_db.get_history(workspace_root)

@router.post("/clear")
def clear_history(workspace_root: str):
    chat_db.clear_history(workspace_root)
    return {"status": "success"}
