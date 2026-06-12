"""
agents/graph_chat.py
--------------------
Context-aware AI chat agent.

Receives:
  - user message
  - conversation history
  - compact graph summary (list of CompactGraphNode)
  - optionally, the currently-selected node

Builds a system prompt that compresses the full codebase into ~200 tokens/file
so the LLM understands the architecture when answering questions.

Streams response tokens back via the async generator stream_chat().

Person 3 owns this file — refine the system prompt and add RAG-style
node selection if needed.
"""


from typing import AsyncGenerator, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from .state import ChatState, ChatMessage, CompactGraphNode
from config import settings


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

def _build_system_prompt(
    graph_summary: List[CompactGraphNode],
    selected_node: Optional[CompactGraphNode],
) -> str:
    """
    Build a compact, token-efficient system prompt from the graph summary.

    Format per file:
      [path/to/file.ts]
      functions: foo, bar, baz
      imports:   utils.ts, api.ts
      used by:   main.ts

    Roughly 200 tokens per file.
    """
    lines: List[str] = [
        "You are Vivian, an AI coding assistant with full knowledge of this codebase's architecture.",
        "Use the codebase summary below to answer questions accurately.",
        "",
        "## Codebase Summary",
    ]

    for node in graph_summary:
        lines.append(f"\n[{node.get('file', 'unknown')}]")
        funcs = ", ".join(node.get("functions", [])[:20]) or "none"
        lines.append(f"  functions : {funcs}")
        imports = ", ".join(node.get("imports_from", [])) or "none"
        lines.append(f"  imports   : {imports}")
        used_by = ", ".join(node.get("imported_by", [])) or "none"
        lines.append(f"  used by   : {used_by}")

    if selected_node:
        lines.append("")
        lines.append("## Currently Selected File")
        lines.append(f"The user has selected: {selected_node.get('file', 'unknown')}")
        lines.append(
            "Prioritize context from this file and its direct neighbours when answering."
        )

    lines.append("")
    lines.append(
        "Answer concisely with code examples when relevant. "
        "Reference file paths from the summary when citing code locations."
    )

    return "\n".join(lines)


def _to_lc_messages(history: List[ChatMessage]) -> list:
    """Convert our ChatMessage history to LangChain message objects."""
    result = []
    for msg in history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            result.append(HumanMessage(content=content))
        elif role == "assistant":
            result.append(AIMessage(content=content))
        # system messages in history are skipped — we build our own
    return result


# ---------------------------------------------------------------------------
# Public streaming function
# ---------------------------------------------------------------------------

async def stream_chat(
    user_message: str,
    history: List[ChatMessage],
    graph_summary: List[CompactGraphNode],
    selected_node: Optional[CompactGraphNode],
    api_key: str,
    model: str,
) -> AsyncGenerator[str, None]:
    """
    Streams response tokens for a chat message.

    Usage (in main.py WebSocket handler):
        async for token in stream_chat(...):
            await ws.send_json({"event": "chatResponse", "text": token, "done": False})
        await ws.send_json({"event": "chatResponse", "text": "", "done": True})
    """
    llm = ChatOpenAI(
        api_key=api_key,
        base_url=settings.OPENROUTER_BASE_URL,
        model=model,
        max_tokens=settings.MAX_TOKENS,
        streaming=True,
    )

    system_prompt = _build_system_prompt(graph_summary, selected_node)
    lc_history    = _to_lc_messages(history)

    messages = [
        SystemMessage(content=system_prompt),
        *lc_history,
        HumanMessage(content=user_message),
    ]

    async for chunk in llm.astream(messages):
        token = chunk.content
        if token:
            yield token
