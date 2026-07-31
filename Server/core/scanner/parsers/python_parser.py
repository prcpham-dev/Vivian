import ast, re
from pathlib import Path
from typing import List, Optional, Any

from ..types import FunctionDef, ClassDef

_PY_FROM_RE = re.compile(r"^from\s+(\.*)(\w[\w.]*|)\s+import\s+", re.MULTILINE)
_PY_IMPORT_RE = re.compile(r"^import\s+([\w.]+)", re.MULTILINE)

# ── HTTP client call detection ──────────────────────────────────────────
# requests.get('/path'), httpx.post('/path'), session.get('/path')
_PY_HTTP_RE = re.compile(
    r'(?:requests|httpx|session|client|self\.client|self\.session|aiohttp)'
    r'\.(get|post|put|delete|patch|request)\s*\(\s*[f\'"]((?:[^\'"\\]|\\.)+)[\'"]',
    re.IGNORECASE
)
# aiohttp.ClientSession().get('url'), async with session.get('url')
_PY_AIOHTTP_RE = re.compile(
    r'session\.(get|post|put|delete|patch)\s*\(\s*[f\'"]((?:[^\'"\\]|\\.)+)[\'"]',
    re.IGNORECASE
)
# urllib.request.urlopen('/path')
_PY_URLLIB_RE = re.compile(
    r'urlopen\s*\(\s*[f\'"]((?:[^\'"\\]|\\.)+)[\'"]',
    re.IGNORECASE
)

def _py_strip_fstring(path: str) -> str:
    """Remove f-string {expr} to get static path fragment."""
    return re.sub(r'\{[^}]+\}', '', path).rstrip('/')

def parse_python(content: str, file_path: str, workspace_root: str):
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    structs: List[Any] = []
    enums: List[Any] = []
    records: List[Any] = []
    imports: List[str] = []
    
    root = Path(workspace_root).resolve()
    from_dir = Path(file_path).parent
    
    def _find_py_base(parts: List[str]) -> Path:
        curr = from_dir
        while True:
            cand = curr.joinpath(*parts)
            if cand.exists() or cand.with_suffix(".py").exists() or (cand / "__init__.py").exists():
                return cand
            if curr == root or curr.parent == curr:
                break
            curr = curr.parent
        return root.joinpath(*parts)

    ast_success = False
    
    # 1. Parse AST for functions, classes, and imports
    try:
        tree = ast.parse(content)
        ast_success = True
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in node.args.args]
                # Detect FastAPI / Flask route decorators
                # e.g. @app.get("/path"), @router.post("/items"), @app.route("/")
                api_routes = []
                _HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "route"}
                for dec in node.decorator_list:
                    # @app.get("/path") or @router.post("/path")
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                        method = dec.func.attr.lower()
                        if method in _HTTP_METHODS and dec.args:
                            first = dec.args[0]
                            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                                api_routes.append({"method": method.upper() if method != "route" else "ANY", "path": first.value})
                functions.append({
                    "name": node.name,
                    "params": ", ".join(args),
                    "returnType": "",
                    "line": node.lineno,
                    "calledBy": [], "calls": [],
                    **(({"api_routes": api_routes}) if api_routes else {})
                })
            elif isinstance(node, ast.ClassDef):
                bases = []
                is_enum = False
                is_struct = False
                for b in node.bases:
                    if isinstance(b, ast.Name):
                        bases.append(b.id)
                        if b.id == "Enum": is_enum = True
                        if b.id in ("NamedTuple", "TypedDict"): is_struct = True
                    elif isinstance(b, ast.Attribute):
                        bases.append(b.attr)
                        if b.attr == "Enum": is_enum = True
                
                # Check decorators for dataclass
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Name) and dec.id == "dataclass":
                        is_struct = True
                    elif isinstance(dec, ast.Call) and getattr(dec.func, 'id', '') == "dataclass":
                        is_struct = True

                if is_enum:
                    enums.append({"name": node.name, "line": node.lineno})
                elif is_struct:
                    structs.append({"name": node.name, "line": node.lineno})
                elif node.name.endswith("Record"):
                    records.append({"name": node.name, "line": node.lineno})
                else:
                    classes.append({"name": node.name, "extends": bases, "line": node.lineno})
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    candidate = _find_py_base(parts)
                    imports.append(_try_py(candidate))
            elif isinstance(node, ast.ImportFrom):
                level = node.level or 0
                module = node.module or ""
                
                if level > 0:
                    target_dir = from_dir
                    for _ in range(level - 1): target_dir = target_dir.parent
                    base_path = target_dir.joinpath(*module.split(".")) if module else target_dir
                else:
                    base_path = _find_py_base(module.split(".")) if module else root
                    
                imports.append(_try_py(base_path))
                
                for alias in node.names:
                    if alias.name != "*":
                        imports.append(_try_py(base_path / alias.name))
    except SyntaxError:
        pass
        
    # 2. Parse Imports (Fallback Regex if AST fails)
    if not ast_success:
        for m in _PY_FROM_RE.finditer(content):
            dots = m.group(1)
            module = m.group(2)
            if dots:
                target_dir = from_dir
                for _ in range(len(dots) - 1): target_dir = target_dir.parent
                parts = module.split(".") if module else []
                candidate = target_dir.joinpath(*parts)
                imports.append(_try_py(candidate))
            else:
                if module:
                    parts = module.split(".")
                    candidate = _find_py_base(parts)
                    imports.append(_try_py(candidate))
                    
        for m in _PY_IMPORT_RE.finditer(content):
            module = m.group(1)
            if module:
                parts = module.split(".")
                candidate = _find_py_base(parts)
                imports.append(_try_py(candidate))
                
    return functions, classes, structs, enums, records, imports

def _extract_py_api_calls(content: str) -> list:
    """Scan Python file content for outgoing HTTP client calls."""
    api_calls = []
    seen = set()

    def _add(method: str, raw: str):
        fragment = _py_strip_fstring(raw).strip()
        if not fragment or len(fragment) < 2:
            return
        key = (method.upper(), fragment)
        if key not in seen:
            seen.add(key)
            api_calls.append({"method": method.upper(), "path_fragment": fragment})

    for m in _PY_HTTP_RE.finditer(content):
        _add(m.group(1), m.group(2))
    for m in _PY_AIOHTTP_RE.finditer(content):
        _add(m.group(1), m.group(2))
    for m in _PY_URLLIB_RE.finditer(content):
        _add("GET", m.group(1))
    return api_calls

def _try_py(base: Path) -> Optional[str]:
    p = base.with_suffix(".py")
    if p.exists(): return str(p)
    init = base / "__init__.py"
    if init.exists(): return str(init)
    return None
