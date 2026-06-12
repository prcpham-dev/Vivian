from typing import AsyncGenerator, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from config import settings
from .state import ChatMessage
from .prompts import CHAT_SYSTEM_PROMPT
from .tools import GRAPH_TOOLS
from .context_loader import get_graph_context

def _to_lc_messages(history: List[ChatMessage]) -> list:
    result = []
    for msg in history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            result.append(HumanMessage(content=content))
        elif role == "assistant":
            result.append(AIMessage(content=content))
    return result

# Create the interactive agent once
chat_agent = create_react_agent(settings.LLM, tools=GRAPH_TOOLS)

async def stream_chat(
    user_message: str,
    history: List[ChatMessage],
    selected_node: Optional[dict],
    api_key: str,
    model: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    
    # 1. Load the optimized structural map
    graph_context = get_graph_context()
    
    # 2. Base system prompt: Give it the map so it doesn't hallucinate, PLUS tools to dig deeper!
    sys_content = f"{CHAT_SYSTEM_PROMPT}\n\n### Codebase Architecture Map\n{graph_context}\n\nYou have access to interactive tools to query the codebase graph on-demand. Use this map to know what files and functions exist. If you need to trace execution (e.g., who calls what), use the tools!"
    
    if selected_node:
        sys_content += f"\n\n## Currently Selected File\nThe user has selected: {selected_node.get('file', 'unknown')}\nPrioritize looking up this file if context is needed."

    lc_history = _to_lc_messages(history)
    messages = [
        SystemMessage(content=sys_content),
        *lc_history,
        HumanMessage(content=user_message),
    ]

    # Stream using astream_events to capture the final LLM response cleanly
    async for event in chat_agent.astream_events({"messages": messages}, version="v2"):
        
        # When the AI decides to use a tool, notify the user so they aren't waiting in silence!
        if event["event"] == "on_tool_start":
            tool_name = event["name"]
            yield f"\n> *Vivian is running `{tool_name}` to investigate your codebase...*\n\n"
            
        elif event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            # Only yield text content, ignore tool_calls chunks
            if chunk.content and isinstance(chunk.content, str):
                yield chunk.content
