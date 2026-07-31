import re
from typing import List, Optional
from pathlib import Path

from ..types import FunctionDef, ClassDef, InterfaceDef

_SWIFT_IMPORT_RE = re.compile(r'^import\s+(\w+)', re.MULTILINE)
_SWIFT_CLASS_RE = re.compile(r'(?:class|actor)\s+(\w+)(?:\s*:\s*([\w,\s<>]+))?')
_SWIFT_STRUCT_RE = re.compile(r'struct\s+(\w+)')
_SWIFT_PROTOCOL_RE = re.compile(r'protocol\s+(\w+)(?:\s*:\s*([\w,\s]+))?')
_SWIFT_FUNC_RE = re.compile(r'func\s+(\w+)\s*(?:<[^>]+>)?\s*\(')

# ── HTTP client call detection ──────────────────────────────────────────────
# URLSession: URL(string: "/path"), URLRequest(url: URL(string: "/path")!)
_SWIFT_URL_RE = re.compile(
    r'URL\s*\(\s*string\s*:\s*"([^"]+)"',
    re.IGNORECASE
)
# Alamofire: AF.request("/path", method: .get), AF.upload, AF.download
_SWIFT_AF_RE = re.compile(
    r'AF\.(request|upload|download)\s*\(\s*"([^"]+)"(?:\s*,\s*method\s*:\s*\.(\w+))?',
    re.IGNORECASE
)
# URLSession.shared.dataTask(with: url) -- covered by URL capture above

def parse_swift(content: str):
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    interfaces: List[InterfaceDef] = []
    structs: List[dict] = []
    raw_imports: List[str] = []

    for m in _SWIFT_IMPORT_RE.finditer(content):
        raw_imports.append(m.group(1))

    for m in _SWIFT_CLASS_RE.finditer(content):
        name, parents = m.groups()
        extends = [x.strip() for x in parents.split(",")] if parents else []
        line = content.count('\n', 0, m.start()) + 1
        classes.append(ClassDef(name=name, extends=extends, line=line))

    for m in _SWIFT_STRUCT_RE.finditer(content):
        line = content.count('\n', 0, m.start()) + 1
        structs.append({"name": m.group(1), "line": line})

    for m in _SWIFT_PROTOCOL_RE.finditer(content):
        name, ext = m.groups()
        extends = [x.strip() for x in ext.split(",")] if ext else []
        line = content.count('\n', 0, m.start()) + 1
        interfaces.append(InterfaceDef(name=name, extends=extends, line=line))

    for m in _SWIFT_FUNC_RE.finditer(content):
        name = m.group(1)
        if name not in {"if", "guard", "while", "for", "switch", "catch"}:
            line = content.count('\n', 0, m.start()) + 1
            functions.append(FunctionDef(name=name, params="", returnType="", line=line, calledBy=[], calls=[]))

    api_calls = _extract_swift_api_calls(content)
    return functions, classes, interfaces, structs, raw_imports, api_calls

def _extract_swift_api_calls(content: str) -> list:
    api_calls = []
    seen = set()
    def _add(method: str, raw: str):
        frag = raw.strip()
        if not frag or len(frag) < 2: return
        key = (method.upper(), frag)
        if key not in seen:
            seen.add(key)
            api_calls.append({"method": method.upper(), "path_fragment": frag})
    for m in _SWIFT_URL_RE.finditer(content):
        _add("ANY", m.group(1))
    for m in _SWIFT_AF_RE.finditer(content):
        verb = m.group(3).upper() if m.group(3) else "GET"
        _add(verb, m.group(2))
    return api_calls
