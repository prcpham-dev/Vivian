from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from handlers import graph, scan, git, ws

app = FastAPI(title="Vivian Sidecar", version="0.1.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(graph.router)
app.include_router(scan.router)
app.include_router(git.router)
app.include_router(ws.router)


@app.get("/health")
def health():
    return {"status": "ok"}
