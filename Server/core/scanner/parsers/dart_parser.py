import re
from typing import List, Optional
from pathlib import Path

from ..types import FunctionDef, ClassDef, InterfaceDef

_DART_IMPORT_RE = re.compile(r"^import\s+['\"]([^'\"]+)['\"]", re.MULTILINE)
_DART_CLASS_RE = re.compile(r'class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?')
_DART_FUNC_RE = re.compile(
    r'(?:Future|void|String|int|bool|double|dynamic|List|Map|\w+)\s+(\w+)\s*\([^)]*\)\s*(?:async\s*)?\{'
)
_DART_MIXIN_RE = re.compile(r'mixin\s+(\w+)')

# ── HTTP client call detection ──────────────────────────────────────────────
# http package: http.get(Uri.parse('/path')), http.post(Uri.parse('/path'))
_DART_HTTP_RE = re.compile(
    r'(?:http|_http|client)\.(get|post|put|delete|patch)\s*\(\s*Uri\.parse\s*\(\s*[\'"]([^\'"]+)[\'"]',
    re.IGNORECASE
)
# http.get('/path') — direct string form (older API)
_DART_HTTP_STR_RE = re.compile(
    r'(?:http|_http|client)\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]',
    re.IGNORECASE
)
# Dio: dio.get('/path'), _dio.post('/path'), Dio().get('/path')
_DART_DIO_RE = re.compile(
    r'(?:dio|_dio|Dio\s*\(\s*\))\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]',
    re.IGNORECASE
)

def parse_dart(content: str):
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    raw_imports: List[str] = []

    for m in _DART_IMPORT_RE.finditer(content):
        raw_imports.append(m.group(1))

    for m in _DART_CLASS_RE.finditer(content):
        name, ext, impl = m.groups()
        extends = []
        if ext: extends.append(ext)
        if impl: extends.extend([x.strip() for x in impl.split(",") if x.strip()])
        line = content.count('\n', 0, m.start()) + 1
        classes.append(ClassDef(name=name, extends=extends, line=line))

    for m in _DART_FUNC_RE.finditer(content):
        name = m.group(1)
        if name not in {"if", "for", "while", "switch", "catch", "else"}:
            line = content.count('\n', 0, m.start()) + 1
            functions.append(FunctionDef(name=name, params="", returnType="", line=line, calledBy=[], calls=[]))

    api_calls = _extract_dart_api_calls(content)
    return functions, classes, raw_imports, api_calls

def _extract_dart_api_calls(content: str) -> list:
    api_calls = []
    seen = set()
    def _add(method: str, raw: str):
        frag = raw.strip()
        if not frag or len(frag) < 2: return
        key = (method.upper(), frag)
        if key not in seen:
            seen.add(key)
            api_calls.append({"method": method.upper(), "path_fragment": frag})
    for m in _DART_HTTP_RE.finditer(content):
        _add(m.group(1), m.group(2))
    for m in _DART_HTTP_STR_RE.finditer(content):
        _add(m.group(1), m.group(2))
    for m in _DART_DIO_RE.finditer(content):
        _add(m.group(1), m.group(2))
    return api_calls

def resolve_dart_imports(file_path: str, raw_imports: List[str], workspace_root: str) -> List[str]:
    results = []
    root = Path(workspace_root).resolve()
    from_dir = Path(file_path).parent
    for imp in raw_imports:
        if imp.startswith("dart:") or imp.startswith("package:flutter") or imp.startswith("package:dart"):
            continue
        if imp.startswith("package:"):
            # package:myapp/src/foo.dart → try lib/src/foo.dart
            rel = imp.split("/", 1)[-1] if "/" in imp else imp
            candidate = root / "lib" / rel
        else:
            candidate = (from_dir / imp).resolve()
        if candidate.exists() and candidate.is_file():
            results.append(str(candidate))
    return results
