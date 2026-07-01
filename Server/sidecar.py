from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import sys
import uvicorn
import json

from handlers import graph, scan, git, ws, settings as settings_handler, chat

app = FastAPI(title="Vivian Sidecar", version="0.1.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(graph.router)
app.include_router(scan.router)
app.include_router(git.router)
app.include_router(ws.router)
app.include_router(settings_handler.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "vivian-sidecar"}

@app.get("/test-chat")
def serve_chat_test():
    return FileResponse("chat_test.html")

if __name__ == "__main__":
    uvicorn.run("sidecar:app", host="127.0.0.1", port=8765)
