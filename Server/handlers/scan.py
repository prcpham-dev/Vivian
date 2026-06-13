import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

from core.agents.vuln_agent import vuln_graph
from core.agents.state import ScanState, FileContent
from core.settings_manager import get_model, get_max_scan_files

router = APIRouter(prefix="/scan", tags=["scan"])


class NodeScanRequest(BaseModel):
    workspace_root: str
    nodes: List[str]

class DiffScanRequest(BaseModel):
    diff: str


async def _run_scan(files: List[FileContent], target: str, workspace_root: str, diff: str = ""):
    print(f"[VulnAgent] Initiating scan for target: {target} with {len(files)} files.")
    state = ScanState(
        workspace_root=workspace_root,
        files=[{"path": f["path"], "content": f["content"]} for f in files],
        diff=diff or None,
        scan_target=target,
        findings=[],
    )
    result = await vuln_graph.ainvoke(state)
    findings = result.get("findings", [])
    if len(files) == 1:
        for f in findings:
            if not f.get("file"):
                f["file"] = files[0]["path"]
    return {"findings": findings}


def _read_files(workspace_root: str, paths: List[str]) -> List[FileContent]:
    files = []
    for path in paths:
        full_path = os.path.join(workspace_root, path) if not os.path.isabs(path) else path
        if os.path.isfile(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                files.append({"path": path, "content": content})
            except Exception as e:
                print(f"Failed to read {full_path}: {e}")
        else:
            print(f"File not found: {full_path}")
    print(f"Read {len(files)} files.")
    return files


@router.post("/directory")
async def scan_directory(req: NodeScanRequest):
    if len(req.nodes) > get_max_scan_files():
        return {"error": f"Too many files. Max: {get_max_scan_files()}", "findings": []}
    files = _read_files(req.workspace_root, req.nodes)
    return await _run_scan(files, "directory", req.workspace_root)


@router.post("/diff", include_in_schema=False)
async def scan_diff(req: DiffScanRequest):
    pseudo = [{"path": "git-diff", "content": req.diff}]
    return await _run_scan(pseudo, "diff", "", diff=req.diff)
