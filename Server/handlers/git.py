from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

from core.agents.git_agent import run_git_assistant
from core.agents.state import GitState
from core.settings_manager import get_model

router = APIRouter(prefix="/git", tags=["git"])

class GitSummarizeRequest(BaseModel):
    diff: str

@router.post("/summarize")
async def git_summarize(req: GitSummarizeRequest):
    state = GitState(
        diff=req.diff,
    )
    result = await run_git_assistant(state)
    return {
        "commit_message": result.get("commit_message", ""),
        "impact_summary": result.get("impact_summary", ""),
    }
