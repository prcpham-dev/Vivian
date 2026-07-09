import threading
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Literal

from core.scanner.graph_builder import build_graph, save_cache, load_cache

router = APIRouter(prefix="/graph", tags=["graph"])

_build_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


class BuildGraphRequest(BaseModel):
    workspace_root: str
    ignore_patterns: Optional[List[str]] = None
    max_depth: int = 15
    cache: bool = True


class LoadCacheRequest(BaseModel):
    workspace_root: str


def _run_build(req: BuildGraphRequest):
    """Worker that runs in a background thread."""
    try:
        graph = build_graph(
            workspace_root=req.workspace_root,
            ignore_patterns=req.ignore_patterns,
            max_depth=req.max_depth,
        )
        if req.cache:
            save_cache(req.workspace_root, graph)
        with _jobs_lock:
            _build_jobs[req.workspace_root] = {"status": "done", "error": None}
    except Exception as e:
        with _jobs_lock:
            _build_jobs[req.workspace_root] = {"status": "error", "error": str(e)}


@router.post("/build")
def graph_build(req: BuildGraphRequest):
    """Kicks off a background graph build and returns immediately."""
    with _jobs_lock:
        existing = _build_jobs.get(req.workspace_root)
        if existing and existing["status"] == "running":
            return {"status": "running", "message": "A build is already in progress."}
        _build_jobs[req.workspace_root] = {"status": "running", "error": None}

    thread = threading.Thread(target=_run_build, args=(req,), daemon=True)
    thread.start()
    return {"status": "running", "message": "Graph build started in the background."}


@router.get("/build/status")
def graph_build_status(workspace_root: str):
    """Poll this endpoint to check whether the background build has finished."""
    with _jobs_lock:
        job = _build_jobs.get(workspace_root)
    if not job:
        return {"status": "idle", "error": None}
    return {"status": job["status"], "error": job.get("error")}


@router.post("/cache/load")
def graph_cache_load(req: LoadCacheRequest):
    cached = load_cache(req.workspace_root)
    return cached if cached else {"cached": False}
