import json
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from .state import ScanState, VulnFinding
from .prompts import VULN_SYSTEM_PROMPT
from .context_loader import get_graph_context
from core.settings_manager import get_llm

async def run_vuln_scan(state: ScanState) -> dict:
    files = state.get("files", [])
    diff = state.get("diff")
    scan_target = state.get("scan_target")
    workspace_root = state.get("workspace_root", "")
    
    # 1. Load Graph Context
    graph_context = get_graph_context(workspace_root) if workspace_root else "No workspace root provided."
    
    # 2. Build User Content
    user_content = f"{graph_context}\n\n"
    
    if scan_target == "diff" and diff:
        user_content += f"## Code to Scan (Git Diff)\n```diff\n{diff[:8000]}\n```"
    elif scan_target == "file" and files:
        target_file = files[0]
        user_content += f"## Code to Scan ({target_file.get('path')})\n```\n{target_file.get('content', '')[:8000]}\n```"
    else:
        # Scan all provided files (fallback)
        user_content += "## Code to Scan\n"
        for f in files[:10]: # limit to 10 files
            user_content += f"### {f.get('path')}\n```\n{f.get('content', '')[:2000]}\n```\n\n"

    # 3. Invoke LLM
    print(f"[VulnAgent] Scanning target={scan_target}, num_files={len(files)}")
    response = await get_llm().ainvoke([
        SystemMessage(content=VULN_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ])
    print(f"[VulnAgent] LLM returned {len(response.content)} chars.")
    
    # 4. Parse Findings
    findings = []
    try:
        # Strip markdown json blocks if they exist
        raw = response.content.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
            
        data = json.loads(raw)
        findings = data.get("vulnerabilities", [])
    except json.JSONDecodeError:
        print(f"[VulnAgent] Failed to parse JSON: {response.content}")
        
    return {"findings": findings}

def build_vuln_graph() -> StateGraph:
    builder = StateGraph(ScanState)
    builder.add_node("scanner", run_vuln_scan)
    builder.add_edge(START, "scanner")
    builder.add_edge("scanner", END)
    return builder.compile()

vuln_graph = build_vuln_graph()
