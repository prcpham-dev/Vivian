import re
from typing import List, Optional
from pathlib import Path

from ..types import FunctionDef, ClassDef, InterfaceDef

_KT_IMPORT_RE = re.compile(r'^import\s+([\w.]+)', re.MULTILINE)
_KT_CLASS_RE = re.compile(r'(?:data\s+)?class\s+(\w+)(?:\s*(?::|extends)\s*([\w<>,\s]+))?')
_KT_INTF_RE = re.compile(r'interface\s+(\w+)(?:\s*:\s*([\w<>,\s]+))?')
_KT_FUNC_RE = re.compile(r'(?:suspend\s+)?fun\s+(\w+)\s*(?:<[^>]+>)?\s*\(')
_KT_OBJECT_RE = re.compile(r'object\s+(\w+)')

# ── HTTP client call detection ──────────────────────────────────────────────
# Retrofit: @GET("/path"), @POST("/path") on interface methods (same pattern as Java)
_KT_RETROFIT_RE = re.compile(
    r'@(GET|POST|PUT|DELETE|PATCH)\s*\(\s*"([^"]+)"',
    re.IGNORECASE
)
# Ktor client: client.get("/path"), client.post("/path") { ... }
_KT_KTOR_RE = re.compile(
    r'(?:client|httpClient)\.(get|post|put|delete|patch)\s*\(\s*"([^"]+)"',
    re.IGNORECASE
)
# OkHttp: Request.Builder().url("/path")
_KT_OKHTTP_RE = re.compile(r'\.url\s*\(\s*"([^"]+)"', re.IGNORECASE)

def parse_kotlin(content: str):
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    interfaces: List[InterfaceDef] = []
    raw_imports: List[str] = []

    for m in _KT_IMPORT_RE.finditer(content):
        raw_imports.append(m.group(1))

    for m in _KT_CLASS_RE.finditer(content):
        name, ext = m.groups()
        extends = [x.strip() for x in ext.split(",")] if ext else []
        line = content.count('\n', 0, m.start()) + 1
        classes.append(ClassDef(name=name, extends=extends, line=line))

    for m in _KT_INTF_RE.finditer(content):
        name, ext = m.groups()
        extends = [x.strip() for x in ext.split(",")] if ext else []
        line = content.count('\n', 0, m.start()) + 1
        interfaces.append(InterfaceDef(name=name, extends=extends, line=line))

    for m in _KT_FUNC_RE.finditer(content):
        name = m.group(1)
        if name not in {"if", "for", "while", "when", "try", "catch"}:
            line = content.count('\n', 0, m.start()) + 1
            functions.append(FunctionDef(name=name, params="", returnType="", line=line, calledBy=[], calls=[]))

    api_calls = _extract_kotlin_api_calls(content)
    return functions, classes, interfaces, raw_imports, api_calls

def _extract_kotlin_api_calls(content: str) -> list:
    api_calls = []
    seen = set()
    def _add(method: str, raw: str):
        frag = raw.strip()
        if not frag or len(frag) < 2: return
        key = (method.upper(), frag)
        if key not in seen:
            seen.add(key)
            api_calls.append({"method": method.upper(), "path_fragment": frag})
    for m in _KT_RETROFIT_RE.finditer(content):
        _add(m.group(1), m.group(2))
    for m in _KT_KTOR_RE.finditer(content):
        _add(m.group(1), m.group(2))
    for m in _KT_OKHTTP_RE.finditer(content):
        _add("ANY", m.group(1))
    return api_calls

def resolve_kotlin_imports(file_path: str, raw_imports: List[str], workspace_root: str) -> List[str]:
    results = []
    root = Path(workspace_root).resolve()
    for imp in raw_imports:
        if imp.startswith("kotlin.") or imp.startswith("java.") or imp.startswith("android."):
            continue
        rel_path = imp.replace(".", "/") + ".kt"
        candidates = [
            root / rel_path,
            root / "src" / "main" / "kotlin" / rel_path,
            root / "src" / "main" / "java" / rel_path,
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                results.append(str(c.resolve()))
                break
    return results
