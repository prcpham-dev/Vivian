import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.agents.graph_chat import stream_chat
from core.agents.vuln_agent import vuln_graph
from core.agents.state import ScanState
from config import settings

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    api_key = ""
    model = settings.DEFAULT_MODEL

    try:
        while True:
            raw = await ws.receive_text()

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"event": "error", "message": "Invalid JSON"})
                continue

            event = msg.get("event", "")

            # Init — store api key + model for this connection
            if event == "init":
                api_key = msg.get("apiKey", "")
                model = msg.get("model", settings.DEFAULT_MODEL)
                await ws.send_json({"event": "ready"})

            # Chat — stream tokens
            elif event == "chat":
                if not api_key:
                    await ws.send_json({"event": "error", "message": "Send init first"})
                    continue
                try:
                    async for token in stream_chat(
                        user_message=msg.get("text", ""),
                        history=msg.get("history", []),
                        graph_summary=msg.get("graph_summary", []),
                        selected_node=msg.get("selected_node"),
                        api_key=api_key,
                        model=model,
                    ):
                        await ws.send_json({"event": "chatResponse", "text": token, "done": False})
                    await ws.send_json({"event": "chatResponse", "text": "", "done": True})
                except Exception as e:
                    await ws.send_json({"event": "error", "message": str(e)})

            # Scan — run vuln agents
            elif event == "scan":
                if not api_key:
                    await ws.send_json({"event": "error", "message": "Send init first"})
                    continue
                try:
                    target = msg.get("target", "directory")
                    files = msg.get("files", [])
                    diff = msg.get("diff", "")

                    scan_files = [{"path": "git-diff", "content": diff}] if target == "diff" else files

                    state = ScanState(
                        files=scan_files,
                        diff=diff or None,
                        api_key=api_key,
                        model=model,
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
