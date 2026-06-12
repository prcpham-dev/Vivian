"""
agents/vuln_agent.py
--------------------
LangGraph vulnerability scanning agents.

Graph layout:
  START
    └─► triage_files          (filters to only security-relevant files)
           └─► [PARALLEL]
                 ├─ xss_checker
                 ├─ sqli_checker
                 ├─ auth_checker
                 └─ crypto_checker
                        └─► END

Each checker writes to state["findings"] using LangGraph's Annotated[list, add]
so parallel branches concatenate their results safely.

Person 3 owns this file — implement each checker node below.
"""


import asyncio
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from .state import ScanState, VulnFinding, FileContent
from config import settings


# ---------------------------------------------------------------------------
# LLM factory — uses OpenRouter base URL + caller-supplied API key
# ---------------------------------------------------------------------------

def make_llm(api_key: str, model: str) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=api_key,
        base_url=settings.OPENROUTER_BASE_URL,
        model=model,
        max_tokens=settings.MAX_TOKENS,
        streaming=True,
    )


# ---------------------------------------------------------------------------
# Helper — shared prompt builder for vuln checkers
# ---------------------------------------------------------------------------

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

def _build_file_block(files: List[FileContent], max_files: int = 20) -> str:
    """Format file list for the prompt. Truncates large files at 200 lines."""
    parts = []
    for f in files[:max_files]:
        lines = f["content"].splitlines()[:200]
        parts.append(f"### {f['path']}\n" + "\n".join(lines))
    return "\n\n".join(parts)


def _parse_findings(raw: str, agent_name: str) -> List[VulnFinding]:
    """Parse JSON-per-line output from the LLM into VulnFinding dicts."""
    import json
    findings: List[VulnFinding] = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            obj["agent"] = agent_name  # ensure agent tag is set
            findings.append(obj)
        except json.JSONDecodeError:
            pass  # skip malformed lines
    return findings


# ---------------------------------------------------------------------------
# Triage node — filters to files likely to contain security issues
# ---------------------------------------------------------------------------

# File extensions worth scanning
_SCAN_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx",   # web / Node
    ".py",                          # Python
    ".go",                          # Go
    ".java",                        # Java
    ".php",                         # PHP (common vuln surface)
    ".rb",                          # Ruby
    ".c", ".cpp", ".h", ".hpp",    # C/C++
}

# Skip these path patterns even when included
_SKIP_PATTERNS = [
    "node_modules", "dist", "build", ".git",
    "__pycache__", "vendor", ".venv", "venv",
    ".next", "coverage", "__mocks__",
]


def triage_files(state: ScanState) -> dict:
    """
    Filter incoming files to only those likely to contain vulnerabilities.
    Skips test files, build artifacts, and files above the size limit.
    """
    raw_files: List[FileContent] = state.get("files") or []
    limit = settings.MAX_SCAN_FILES

    def should_scan(f: FileContent) -> bool:
        p = f["path"].lower().replace("\\", "/")
        for skip in _SKIP_PATTERNS:
            if f"/{skip}/" in f"/{p}/":
                return False
        # must have a scannable extension
        from pathlib import PurePosixPath
        ext = PurePosixPath(p).suffix
        return ext in _SCAN_EXTENSIONS

    filtered = [f for f in raw_files if should_scan(f)][:limit]
    return {"files": filtered}


# ---------------------------------------------------------------------------
# XSS checker
# ---------------------------------------------------------------------------

async def xss_checker(state: ScanState) -> dict:
    """
    TODO (Person 3): Implement XSS vulnerability scanner node.

    Patterns to look for:
      - innerHTML / document.write with unsanitized user input
      - dangerouslySetInnerHTML in React
      - Jinja2 {{ var | safe }} without escaping
      - Template injection in Python f-strings rendered to HTML
    """
    files: List[FileContent] = state.get("files") or []
    api_key: str = state["api_key"]
    model: str   = state["model"]

    if not files:
        return {"findings": []}

    system = VULN_SYSTEM_TEMPLATE.format(
        vuln_type="Cross-Site Scripting (XSS)",
        agent_name="xss_checker",
    )
    user_block = _build_file_block(files)

    llm = make_llm(api_key, model)
    response = await llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=user_block),
    ])

    findings = _parse_findings(response.content, "xss_checker")
    return {"findings": findings}


# ---------------------------------------------------------------------------
# SQL injection checker
# ---------------------------------------------------------------------------

async def sqli_checker(state: ScanState) -> dict:
    """
    TODO (Person 3): Implement SQL Injection scanner node.

    Patterns to look for:
      - f-string / % / .format() in SQL query strings
      - raw cursor.execute() with concatenated user input
      - ORM raw() / extra() calls with user input
      - Parameterized query misuse
    """
    files: List[FileContent] = state.get("files") or []
    api_key: str = state["api_key"]
    model: str   = state["model"]

    if not files:
        return {"findings": []}

    system = VULN_SYSTEM_TEMPLATE.format(
        vuln_type="SQL Injection (SQLi)",
        agent_name="sqli_checker",
    )
    user_block = _build_file_block(files)

    llm = make_llm(api_key, model)
    response = await llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=user_block),
    ])

    findings = _parse_findings(response.content, "sqli_checker")
    return {"findings": findings}


# ---------------------------------------------------------------------------
# Auth / Authorization checker
# ---------------------------------------------------------------------------

async def auth_checker(state: ScanState) -> dict:
    """
    TODO (Person 3): Implement Auth/Authorization vulnerability scanner.

    Patterns to look for:
      - Missing authentication middleware on sensitive routes
      - Hardcoded credentials / tokens in source
      - JWT without expiry or weak secret
      - Insecure session configuration
      - IDOR (object access without ownership check)
    """
    files: List[FileContent] = state.get("files") or []
    api_key: str = state["api_key"]
    model: str   = state["model"]

    if not files:
        return {"findings": []}

    system = VULN_SYSTEM_TEMPLATE.format(
        vuln_type="Authentication & Authorization Failures",
        agent_name="auth_checker",
    )
    user_block = _build_file_block(files)

    llm = make_llm(api_key, model)
    response = await llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=user_block),
    ])

    findings = _parse_findings(response.content, "auth_checker")
    return {"findings": findings}


# ---------------------------------------------------------------------------
# Cryptographic failure checker
# ---------------------------------------------------------------------------

async def crypto_checker(state: ScanState) -> dict:
    """
    TODO (Person 3): Implement Cryptographic Failure scanner.

    Patterns to look for:
      - Use of MD5 / SHA1 for password hashing
      - Weak random number generation (random.random() for secrets)
      - Hardcoded encryption keys / IVs
      - HTTP instead of HTTPS for sensitive data transfer
      - Disabled TLS verification (verify=False)
    """
    files: List[FileContent] = state.get("files") or []
    api_key: str = state["api_key"]
    model: str   = state["model"]

    if not files:
        return {"findings": []}

    system = VULN_SYSTEM_TEMPLATE.format(
        vuln_type="Cryptographic Failures",
        agent_name="crypto_checker",
    )
    user_block = _build_file_block(files)

    llm = make_llm(api_key, model)
    response = await llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=user_block),
    ])

    findings = _parse_findings(response.content, "crypto_checker")
    return {"findings": findings}


# ---------------------------------------------------------------------------
# LangGraph — Vulnerability Scan Graph
# ---------------------------------------------------------------------------

def build_vuln_graph() -> StateGraph:
    """
    Builds and compiles the vulnerability scanning graph.

    Flow:
      START → triage_files → [xss, sqli, auth, crypto in parallel] → END
    """
    builder = StateGraph(ScanState)

    builder.add_node("triage_files",  triage_files)
    builder.add_node("xss_checker",   xss_checker)
    builder.add_node("sqli_checker",  sqli_checker)
    builder.add_node("auth_checker",  auth_checker)
    builder.add_node("crypto_checker", crypto_checker)

    builder.add_edge(START, "triage_files")

    # Fan out to all checkers in parallel after triage
    for checker in ["xss_checker", "sqli_checker", "auth_checker", "crypto_checker"]:
        builder.add_edge("triage_files", checker)
        builder.add_edge(checker, END)

    return builder.compile()


# Singleton compiled graph — imported by main.py routers
vuln_graph = build_vuln_graph()
