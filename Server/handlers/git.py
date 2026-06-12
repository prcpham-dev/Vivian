from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

from core.agents.git_agent import run_git_assistant
from core.agents.state import GitState, CompactGraphNode
from config import settings

router = APIRouter(prefix="/git", tags=["git"])


class GitSummarizeRequest(BaseModel):
    diff: str
    graph_summary: List[CompactGraphNode] = []
    api_key: str
    model: str = settings.DEFAULT_MODEL


@router.post("/summarize")
async def git_summarize(req: GitSummarizeRequest):
    state = GitState(
        diff=req.diff,
        graph_summary=req.graph_summary,
        api_key=req.api_key,
        model=req.model,
    )
    result = await run_git_assistant(state)
    return {
        "commit_message": result.get("commit_message", ""),
        "impact_summary": result.get("impact_summary", ""),
    }
