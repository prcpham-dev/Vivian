from typing import Any, Dict, List, Optional, TypedDict

class FunctionInfo(TypedDict, total=False):
    name: str
    params: str
    return_type: str
    line: int

class FileContent(TypedDict, total=False):
    path: str
    content: str

class VulnFinding(TypedDict, total=False):
    title: str
    description: str
    remediation: str
    severity: str
    file: str
    line: Optional[int]

class ScanState(TypedDict, total=False):
    files: List[FileContent]
    diff: Optional[str]
    scan_target: str
    target_node: Optional[str]
    findings: List[VulnFinding]

class GitState(TypedDict, total=False):
    diff: str
    commit_message: str
    impact_summary: str

class ChatMessage(TypedDict, total=False):
    role: str
    content: str

class ChatState(TypedDict, total=False):
    messages: List[ChatMessage]
    selected_node: Optional[Dict[str, Any]]
