import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.agents.graph_chat import stream_chat
from core.agents.vuln_agent import vuln_graph
from core.agents.state import ScanState
from core.agents.chat_history import chat_db

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    try:
        while True:
            raw = await ws.receive_text()

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"event": "error", "message": "Invalid JSON"})
                continue

            event = msg.get("event", "")

            # Init — just acknowledge connection
            if event == "init":
                await ws.send_json({"event": "ready"})

            # Chat — stream tokens
            elif event == "chat":
                try:
                    workspace_root = msg.get("workspace_root")
                    
                    if not workspace_root:
                        await ws.send_json({"event": "error", "message": "workspace_root is required for chat"})
                        continue
                        
                    user_text = msg.get("text", "")
                    
                    # 1. Load history from memory
                    history = chat_db.get_history(workspace_root)
                    
                    # 2. Save user message immediately
                    chat_db.add_message(workspace_root, "user", user_text)

                    # 3. Stream AI response and collect full text
                    full_response = ""
                    async for token in stream_chat(
                        workspace_root=workspace_root,
                        user_message=user_text,
                        history=history,
                        selected_node=msg.get("selected_node"),
                    ):
                        # Some tokens might be tool notifications (e.g. "> *Vivian is running...*")
                        # But typically we just append all emitted text to the history
                        full_response += token
                        await ws.send_json({"event": "chatResponse", "text": token, "done": False})
                        
                    # 4. Save AI response to history
                    chat_db.add_message(workspace_root, "assistant", full_response)
                    
                    await ws.send_json({"event": "chatResponse", "text": "", "done": True})
                except Exception as e:
                    await ws.send_json({"event": "error", "message": str(e)})

            # Scan — run vuln agents
            elif event == "scan":
                try:
                    target = msg.get("target", "directory")
                    files = msg.get("files", [])
                    diff = msg.get("diff", "")

                    scan_files = [{"path": "git-diff", "content": diff}] if target == "diff" else files

                    state = ScanState(
                        files=scan_files,
                        diff=diff or None,
                        scan_target=target,
                        findings=[],
                    )
                    result = await vuln_graph.ainvoke(state)
                    await ws.send_json({
                        "event": "scanResult",
                        "findings": result.get("findings", []),
                        "done": True,
                    })
                except Exception as e:
                    await ws.send_json({"event": "error", "message": str(e)})

            else:
                await ws.send_json({"event": "error", "message": f"Unknown event: {event!r}"})

    except WebSocketDisconnect:
        pass
