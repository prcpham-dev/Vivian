import re, json
from pathlib import Path
from typing import List, Optional, Dict

from ..types import FunctionDef, ClassDef, InterfaceDef

_JS_IMPORT_RE = re.compile(
    r"(?:import\s+(?:[\w{},*\s]+\s+from\s+)?['\"](\.{1,2}[^'\"]+|@\/[^'\"]+)['\"]|"
    r"require\s*\(\s*['\"](\.{1,2}[^'\"]+)['\"]|"
    r"import\s*\(\s*['\"](\.{1,2}[^'\"]+)['\"])"
)
_TS_CLASS_RE = re.compile(r"class\s+(\w+)(?:\s+(?:extends|implements)\s+([\w<>,\s]+))?")
_TS_INTF_RE = re.compile(r"interface\s+(\w+)(?:\s+extends\s+([\w<>,\s]+))?")
_JS_FUNC_RE = re.compile(r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)")

_TS_ENUM_RE = re.compile(r"enum\s+(\w+)")
_TS_TYPE_RE = re.compile(r"type\s+(\w+)\s*=\s*(.*)")

# Express: app.get('/path', handler), router.post('/path')
_EXPRESS_ROUTE_RE = re.compile(
    r'(?:app|router|server|route)\.(get|post|put|delete|patch|all)\s*\(\s*[\'"]([^\'"]+)[\'"]',
    re.IGNORECASE
)
# NestJS: @Get('/path'), @Post('/path'), @Put, @Delete, @Patch decorators
_NESTJS_ROUTE_RE = re.compile(
    r'@(Get|Post|Put|Delete|Patch|All)\s*\(?\s*[\'"]?([^\'"\)]+)?[\'"]?\s*\)?',
    re.IGNORECASE
)

# ── Frontend API call detection ──────────────────────────────────────────────
# fetch('/api/users') or fetch('/api/users', { method: 'POST' })
_FETCH_RE = re.compile(
    r'fetch\s*\(\s*[`\'"]((?:[^\'"` $]|\$\{[^}]+\})+)[`\'"]'
    r'(?:\s*,\s*\{[^}]*?method\s*:\s*[\'"]([A-Za-z]+)[\'"])?',
    re.IGNORECASE | re.DOTALL
)
# axios.get('/path'), axios.post('/path'), etc.
_AXIOS_METHOD_RE = re.compile(
    r'axios\.(get|post|put|delete|patch)\s*\(\s*[`\'"]((?:[^\'"` $]|\$\{[^}]+\})+)[`\'"]',
    re.IGNORECASE
)
# axios({ url: '/path', method: 'post' }) or axios({ method: 'post', url: '/path' })
_AXIOS_OBJ_RE = re.compile(
    r'axios\s*\(\s*\{[^}]*?url\s*:\s*[`\'"]((?:[^\'"` $]|\$\{[^}]+\})+)[`\'"][^}]*?'
    r'method\s*:\s*[\'"]([A-Za-z]+)[\'"]|'
    r'axios\s*\(\s*\{[^}]*?method\s*:\s*[\'"]([A-Za-z]+)[\'"][^}]*?'
    r'url\s*:\s*[`\'"]((?:[^\'"` $]|\$\{[^}]+\})+)[`\'"]',
    re.IGNORECASE | re.DOTALL
)
# useQuery / useMutation / useSWR / $http — cover common patterns
_GENERIC_HTTP_RE = re.compile(
    r'(?:useQuery|useMutation|useSWR|\$http\.(?:get|post|put|delete|patch)|'
    r'http\.(?:get|post|put|delete|patch))\s*\(?\s*[`\'"]((?:[^\'"` $]|\$\{[^}]+\})+)[`\'"]',
    re.IGNORECASE
)

def _strip_template_vars(path: str) -> str:
    """Remove ${...} from template literals to get the static path fragment."""
    return re.sub(r'\$\{[^}]+\}', '', path).rstrip('/')

def parse_ts_js(content: str):
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    interfaces: List[InterfaceDef] = []
    structs: List[Dict] = []
    enums: List[Dict] = []
    records: List[Dict] = []
    raw_imports: List[str] = []
    
    for m in _JS_IMPORT_RE.finditer(content):
        imp = m.group(1) or m.group(2) or m.group(3)
        if imp: raw_imports.append(imp)
        
    for m in _TS_CLASS_RE.finditer(content):
        name, ext = m.groups()
        line = content.count('\n', 0, m.start()) + 1
        classes.append(ClassDef(name=name, extends=[ext.strip()] if ext else [], line=line))
    for m in _TS_INTF_RE.finditer(content):
        name, ext = m.groups()
        line = content.count('\n', 0, m.start()) + 1
        interfaces.append(InterfaceDef(name=name, extends=[ext.strip()] if ext else [], line=line))
    lines = content.splitlines()
    for m in _JS_FUNC_RE.finditer(content):
        name = m.group(1) or m.group(2)
        if name:
            line = content.count('\n', 0, m.start()) + 1
            # NestJS: check up to 3 lines back for @Get/@Post decorators
            api_routes = []
            start_line = max(0, line - 4)
            preceding = "\n".join(lines[start_line:line - 1])
            for rm in _NESTJS_ROUTE_RE.finditer(preceding):
                verb = rm.group(1).upper()
                path = (rm.group(2) or "/").strip()
                if verb == "ALL":
                    verb = "ANY"
                api_routes.append({"method": verb, "path": path})
            entry = FunctionDef(name=name, params="", returnType="", line=line, calledBy=[], calls=[])
            if api_routes:
                entry["api_routes"] = api_routes
            functions.append(entry)

    # Express: app.get('/path', handler) — synthetic route nodes
    for m in _EXPRESS_ROUTE_RE.finditer(content):
        verb = m.group(1).upper()
        path = m.group(2)
        line = content.count('\n', 0, m.start()) + 1
        fn_name = f"Route_{verb}_{path.strip('/').replace('/', '_') or 'root'}"
        entry = FunctionDef(name=fn_name, params="", returnType="", line=line, calledBy=[], calls=[])
        entry["api_routes"] = [{"method": verb if verb != "ALL" else "ANY", "path": path}]
        functions.append(entry)

    for m in _TS_ENUM_RE.finditer(content):
        line = content.count('\n', 0, m.start()) + 1
        enums.append({"name": m.group(1), "line": line})
    for m in _TS_TYPE_RE.finditer(content):
        name, def_body = m.groups()
        line = content.count('\n', 0, m.start()) + 1
        if "Record<" in def_body:
            records.append({"name": name, "line": line})
        else:
            structs.append({"name": name, "line": line})
                
    # ── Frontend API call extraction ──────────────────────────────────────────
    api_calls: List[Dict] = []
    seen_calls: set = set()

    def _add_call(method: str, raw_path: str):
        fragment = _strip_template_vars(raw_path).strip()
        if not fragment or fragment in ('//', ''):
            return
        key = (method.upper(), fragment)
        if key not in seen_calls:
            seen_calls.add(key)
            api_calls.append({"method": method.upper(), "path_fragment": fragment})

    for m in _FETCH_RE.finditer(content):
        method = m.group(2) or "GET"
        _add_call(method, m.group(1))
    for m in _AXIOS_METHOD_RE.finditer(content):
        _add_call(m.group(1), m.group(2))
    for m in _AXIOS_OBJ_RE.finditer(content):
        # Two capture layouts from the alternation
        if m.group(1) and m.group(2):
            _add_call(m.group(2), m.group(1))
        elif m.group(3) and m.group(4):
            _add_call(m.group(3), m.group(4))
    for m in _GENERIC_HTTP_RE.finditer(content):
        _add_call("GET", m.group(1))  # default GET; method is baked into the fn name

    return functions, classes, interfaces, structs, enums, records, raw_imports, api_calls

_JS_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".vue", ".mts", ".cts"]

def resolve_js(from_file: str, import_path: str, workspace_root: str, aliases: dict[str, str]) -> Optional[str]:
    from_dir = Path(from_file).parent
    for alias, alias_target in aliases.items():
        if import_path.startswith(alias):
            rel = import_path[len(alias):]
            base = Path(alias_target) / rel
            return _try_extensions(base, _JS_EXTENSIONS)
    if import_path.startswith("."):
        base = (from_dir / import_path).resolve()
        return _try_extensions(base, _JS_EXTENSIONS)
    return None

def _try_extensions(base: Path, exts: list[str]) -> Optional[str]:
    if base.exists() and base.is_file(): return str(base)
    for ext in exts:
        p = base.with_suffix(ext) if not base.suffix else Path(str(base) + ext)
        if p.exists(): return str(p)
        idx = base / f"index{ext}"
        if idx.exists(): return str(idx)
    return None
