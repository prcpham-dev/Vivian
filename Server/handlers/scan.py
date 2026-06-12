import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

from core.agents.vuln_agent import vuln_graph
from core.agents.state import ScanState, FileContent
from core.settings_manager import get_model, get_max_scan_files

router = APIRouter(prefix="/scan", tags=["scan"])


class NodeScanRequest(BaseModel):
    nodes: List[str]

class DiffScanRequest(BaseModel):
    diff: str


async def _run_scan(files: List[FileContent], target: str, diff: str = ""):
    state = ScanState(
        files=[{"path": f["path"], "content": f["content"]} for f in files],
        diff=diff or None,
        scan_target=target,
        findings=[],
    )
    result = await vuln_graph.ainvoke(state)
    return {"findings": result.get("findings", [])}


def _read_files(paths: List[str]) -> List[FileContent]:
    files = []
    for path in paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                files.append({"path": path, "content": content})
            except Exception:
                pass
    return files


@router.post("/directory")
async def scan_directory(req: NodeScanRequest):
    if len(req.nodes) > get_max_scan_files():
        return {"error": f"Too many files. Max: {get_max_scan_files()}", "findings": []}
    files = _read_files(req.nodes)
    return await _run_scan(files, "directory")


@router.post("/file")
async def scan_file(req: NodeScanRequest):
    files = _read_files(req.nodes[:1])
    if not files:
        return {"error": "File not found or unreadable.", "findings": []}
    return await _run_scan(files, "file")


@router.post("/diff")
async def scan_diff(req: DiffScanRequest):
    pseudo = [{"path": "git-diff", "content": req.diff}]
    return await _run_scan(pseudo, "diff", diff=req.diff)
