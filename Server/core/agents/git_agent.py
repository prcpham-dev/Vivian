from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .state import GitState, CompactGraphNode
from .prompts import GIT_SYSTEM
from config import settings

async def run_git_assistant(state: GitState) -> dict:
    """
    LangGraph node: analyze a git diff and return commit message + impact summary.

    TODO (Person 3): Enhance the prompt to:
      - highlight breaking changes more explicitly
      - suggest test files that should be updated
      - detect if changelog or README needs updating
    """
    diff: str  = state.get("diff", "")
    graph_summary = state.get("graph_summary", [])
    api_key: str = state["api_key"]
    model: str   = state["model"]

    if not diff.strip():
        return {
            "commit_message": "chore: (no staged changes detected)",
            "impact_summary": "No diff provided.",
        }

    # Build a compact graph block for context
    graph_lines = []
    for node in graph_summary[:30]:  # limit to 30 files for token budget
        graph_lines.append(
            f"[{node.get('file')}] imports: {', '.join(node.get('imports_from', []))}"
        )
    graph_block = "\n".join(graph_lines) or "No graph context provided."

    user_content = f"## Codebase Graph (for impact context)\n{graph_block}\n\n## Git Diff\n```\n{diff[:6000]}\n```"

    llm = ChatOpenAI(
        api_key=api_key,
        base_url=settings.OPENROUTER_BASE_URL,
        model=model,
        max_tokens=1024,
        streaming=False,
    )

    response = await llm.ainvoke([
        SystemMessage(content=GIT_SYSTEM),
        HumanMessage(content=user_content),
    ])

    import json
    try:
        result = json.loads(response.content.strip())
        return {
            "commit_message": result.get("commit_message", ""),
            "impact_summary": result.get("impact_summary", ""),
        }
    except json.JSONDecodeError:
        # Fallback: return raw content if JSON parse fails
        return {
            "commit_message": "",
            "impact_summary": response.content,
        }
