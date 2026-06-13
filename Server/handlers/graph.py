from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from core.scanner.graph_builder import build_graph, save_graph_file, save_cache, load_cache

router = APIRouter(prefix="/graph", tags=["graph"])


class BuildGraphRequest(BaseModel):
    workspace_root: str
    ignore_patterns: Optional[List[str]] = None
    max_depth: int = 15
    cache: bool = True


class LoadCacheRequest(BaseModel):
    workspace_root: str


@router.post("/build")
def graph_build(req: BuildGraphRequest):
    graph = build_graph(
        workspace_root=req.workspace_root,
        ignore_patterns=req.ignore_patterns,
        max_depth=req.max_depth,
    )
    save_graph_file(req.workspace_root, graph)
    if req.cache:
        save_cache(req.workspace_root, graph)
    return graph


@router.post("/cache/load")
def graph_cache_load(req: LoadCacheRequest):
    cached = load_cache(req.workspace_root)
    return cached if cached else {"cached": False}
