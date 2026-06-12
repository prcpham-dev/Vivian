from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

from core.agents.vuln_agent import vuln_graph
from core.agents.state import ScanState, FileContent
from config import settings

router = APIRouter(prefix="/scan", tags=["scan"])


class ScanRequest(BaseModel):
    files: List[FileContent]
    api_key: str
    model: str = settings.DEFAULT_MODEL


class DiffScanRequest(BaseModel):
    diff: str
    api_key: str
    model: str = settings.DEFAULT_MODEL


async def _run_scan(files: List[FileContent], api_key: str, model: str, target: str, diff: str = ""):
    state = ScanState(
        files=[{"path": f["path"], "content": f["content"]} for f in files],
        diff=diff or None,
        api_key=api_key,
        model=model,
        scan_target=target,
        findings=[],
    )
    result = await vuln_graph.ainvoke(state)
    return {"findings": result.get("findings", [])}


@router.post("/directory")
async def scan_directory(req: ScanRequest):
    if len(req.files) > settings.MAX_SCAN_FILES:
        return {"error": f"Too many files. Max: {settings.MAX_SCAN_FILES}", "findings": []}
    return await _run_scan(req.files, req.api_key, req.model, "directory")


@router.post("/file")
async def scan_file(req: ScanRequest):
    return await _run_scan(req.files[:1], req.api_key, req.model, "file")


@router.post("/diff")
async def scan_diff(req: DiffScanRequest):
    pseudo = [{"path": "git-diff", "content": req.diff}]
    return await _run_scan(pseudo, req.api_key, req.model, "diff", diff=req.diff)
