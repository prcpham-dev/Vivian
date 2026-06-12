"""
agents/state.py
---------------
Shared LangGraph state schemas for all Vivian agents.

Every agent node receives the full State dict and returns a partial update.
Keys are designed to be additive — agents only write the keys they own.

This file mirrors the TypeScript type definitions in Client/src/types.ts:
  CompactGraphNode  ↔  CompactGraphNode
  VulnFinding       ↔  VulnFinding
  ChatMessage       ↔  ChatMessage
"""


from typing import Any, Dict, List, Optional, Annotated, TypedDict
import operator


# ---------------------------------------------------------------------------
# Primitive schemas (mirror of Client/src/types.ts)
# ---------------------------------------------------------------------------

class FunctionInfo(TypedDict, total=False):
    name: str
    params: str
    return_type: str
    line: int


class CompactGraphNode(TypedDict, total=False):
    """
    Compact per-file summary sent from the extension for AI context.
    ~200 tokens per file keeps the whole codebase in one prompt window.
    """
    file: str               # relative path from workspace root
    functions: List[str]    # function names only
    imports_from: List[str] # files this file imports (relative paths)
    imported_by: List[str]  # files that import this file (relative paths)


class FileContent(TypedDict):
    """A source file with its content — sent for scan requests."""
    path: str       # absolute path
    content: str


class VulnFinding(TypedDict, total=False):
    file: str
    line: int
    type: str           # e.g. "XSS", "SQLi", "Auth", "CryptoFailure"
    severity: str       # "critical" | "high" | "medium" | "low" | "info"
    snippet: str        # offending code fragment (trimmed)
    fix: str            # brief suggested fix
    agent: str          # which LangGraph agent found this


class ChatMessage(TypedDict):
    role: str       # "user" | "assistant" | "system"
    content: str
    timestamp: Optional[int]


# ---------------------------------------------------------------------------
# LangGraph States
# ---------------------------------------------------------------------------

class ScanState(TypedDict, total=False):
    """
    State for the vulnerability scanning graph.

    Agents write to their own findings list; the parallel runner collects all.
    Using Annotated[list, operator.add] means LangGraph merges list updates
    from parallel branches by concatenation rather than overwriting.
    """
    # Input
    files: List[FileContent]            # files to scan
    diff: Optional[str]                 # raw git diff (diff scan only)
    api_key: str
    model: str

    # Outputs — each agent appends its findings
    findings: Annotated[List[VulnFinding], operator.add]

    # Internal routing
    scan_target: str                    # "directory" | "file" | "diff"


class ChatState(TypedDict, total=False):
    """
    State for the graph-context chat agent.
    """
    # Input
    user_message: str
    history: List[ChatMessage]
    graph_summary: List[CompactGraphNode]
    selected_node: Optional[CompactGraphNode]
    api_key: str
    model: str

    # Output — streaming tokens accumulate here
    response_chunks: Annotated[List[str], operator.add]
    done: bool


class ImpactState(TypedDict, total=False):
    """
    State for the impact analysis agent.
    """
    target_file: str                    # relative path of the file being edited
    graph_summary: List[CompactGraphNode]
    api_key: str
    model: str

    # Output
    depended_on_by: List[str]           # files that import target_file
    risk_level: str                     # "low" | "medium" | "high"
    risk_summary: str


class RefactorState(TypedDict, total=False):
    """
    State for the refactor advisor agent.
    """
    node_file: str
    source_code: str
    neighbours: List[CompactGraphNode]
    api_key: str
    model: str

    # Output — streamed back to chat panel
    suggestions: Annotated[List[str], operator.add]
    done: bool


class GitState(TypedDict, total=False):
    """
    State for the git assistant agent.
    """
    diff: str                           # raw git diff
    graph_summary: List[CompactGraphNode]
    api_key: str
    model: str

    # Output
    commit_message: str
    impact_summary: str
