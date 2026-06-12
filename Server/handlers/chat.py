from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from core.agents.chat_history import chat_db

router = APIRouter(prefix="/chat", tags=["chat"])

class AddMessageRequest(BaseModel):
    role: str = "user"
    content: str


@router.post("/sessions")
def create_session(workspace_root: str):
    session_id = chat_db.create_session(workspace_root)
    return {"session_id": session_id}

@router.get("/sessions")
def get_sessions(workspace_root: str):
    return chat_db.get_all_sessions(workspace_root)

@router.get("/sessions/{session_id}")
def get_session_history(workspace_root: str, session_id: str):
    return chat_db.get_session(workspace_root, session_id)

@router.delete("/sessions/{session_id}")
def delete_session(workspace_root: str, session_id: str):
    chat_db.delete_session(workspace_root, session_id)
    return {"status": "success"}

@router.post("/sessions/{session_id}/messages")
def add_message(workspace_root: str, session_id: str, req: AddMessageRequest):
    chat_db.add_message(workspace_root, session_id, req.role, req.content)
    return {
        "status": "success", 
        "history": chat_db.get_session(workspace_root, session_id)
    }


