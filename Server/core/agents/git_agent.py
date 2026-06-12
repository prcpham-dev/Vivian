import json
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings
from .state import GitState
from .prompts import GIT_ASSISTANT_PROMPT
from .context_loader import get_graph_context
from .vuln_agent import vuln_graph

async def run_git_assistant(state: GitState) -> dict:
    diff = state.get("diff", "")
    
    if not diff.strip():
        return {
            "commit_message": "chore: (no staged changes detected)",
            "impact_summary": "No diff provided.",
        }

    # 1. Run Security Scan on Diff
    vuln_state = await vuln_graph.ainvoke({
        "diff": diff,
        "scan_target": "diff"
    })
    findings = vuln_state.get("findings", [])
    
    vuln_text = ""
    if findings:
        vuln_text = "\n\n## Findings:\n"
        for f in findings:
            vuln_text += f"- {f.get('title')}: {f.get('remediation')}\n"

    # 2. Get Graph Context
    graph_context = get_graph_context()

    # 3. Build Prompt
    user_content = f"{graph_context}\n\n## Git Diff\n```diff\n{diff[:6000]}\n```\n{vuln_text}"

    # 4. Invoke LLM
    response = await settings.LLM.ainvoke([
        SystemMessage(content=GIT_ASSISTANT_PROMPT),
        HumanMessage(content=user_content),
    ])

    # 5. Parse Response
    try:
        raw = response.content.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
            
        result = json.loads(raw)
        return {
            "commit_message": result.get("commit_message", "chore: updated files"),
            "impact_summary": result.get("impact_summary", ""),
        }
    except json.JSONDecodeError:
        return {
            "commit_message": "chore: updated files",
            "impact_summary": response.content,
        }
