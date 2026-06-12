from typing import List, Optional
from core.agents.state import CompactGraphNode

VULN_SYSTEM_TEMPLATE = """\
You are a security code reviewer specializing in {vuln_type} vulnerabilities.

Analyze ONLY the provided source files for {vuln_type} issues.
For each finding output a JSON object on a single line:
{{"file": "<path>", "line": <int>, "type": "<vuln_type>", "severity": "<critical|high|medium|low|info>", "snippet": "<offending code, max 120 chars>", "fix": "<one-line fix suggestion>", "agent": "{agent_name}"}}

Rules:
- Output ONLY finding JSON lines. No prose, no markdown.
- If no findings, output nothing.
- Focus exclusively on {vuln_type} patterns — do not report other vuln classes.
- Be precise: cite the exact line number.
"""

GIT_SYSTEM = """\
You are an expert software engineer reviewing a git diff.

Your tasks:
1. Write a concise commit message following the Conventional Commits spec.
   Format: <type>(<scope>): <short description>
   Types: feat | fix | refactor | perf | docs | test | chore | ci

2. Write a short impact summary covering:
   - Which files and functions changed
   - Whether any public APIs changed (breaking change risk)
   - Which other files in the codebase might be affected (use the graph summary)

Format your response as JSON (single object):
{
  "commit_message": "...",
  "impact_summary": "..."
}
Output ONLY the JSON object. No prose or markdown fences.
"""

CHAT_SYSTEM_BASE = """\
You are Vivian, an AI coding assistant with full knowledge of this codebase's architecture.
Use the codebase summary below to answer questions accurately.

## Codebase Summary
{graph_block}
{selected_block}
Answer concisely with code examples when relevant. \
Reference file paths from the summary when citing code locations.
"""


def build_chat_system_prompt(
    graph_summary: List[CompactGraphNode],
    selected_node: Optional[CompactGraphNode] = None,
) -> str:
    """Build the chat system prompt from the graph summary."""
    node_lines = []
    for node in graph_summary:
        funcs   = ", ".join(node.get("functions", [])[:20]) or "none"
        imports = ", ".join(node.get("imports_from", [])) or "none"
        used_by = ", ".join(node.get("imported_by", [])) or "none"
        node_lines.append(
            f"\n[{node.get('file', 'unknown')}]\n"
            f"  functions : {funcs}\n"
            f"  imports   : {imports}\n"
            f"  used by   : {used_by}"
        )

    selected_block = ""
    if selected_node:
        selected_block = (
            f"\n\n## Currently Selected File\n"
            f"The user has selected: {selected_node.get('file', 'unknown')}\n"
            f"Prioritize context from this file and its direct neighbours when answering."
        )

    return CHAT_SYSTEM_BASE.format(
        graph_block="\n".join(node_lines) or "No graph data provided.",
        selected_block=selected_block,
    )
