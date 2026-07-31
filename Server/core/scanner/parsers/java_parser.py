import re
from pathlib import Path
from typing import List

from ..types import FunctionDef, ClassDef, InterfaceDef

# ── HTTP client call detection ──────────────────────────────────────────
# Retrofit: @GET("/path"), @POST("/path") on interface methods
_JAVA_RETROFIT_RE = re.compile(
    r'@(GET|POST|PUT|DELETE|PATCH)\s*\(\s*"([^"]+)"',
    re.IGNORECASE
)
# RestTemplate: restTemplate.getForObject("/path", ...) / postForObject
_JAVA_REST_TEMPLATE_RE = re.compile(
    r'(?:restTemplate|template)\.(getForObject|getForEntity|postForObject|postForEntity|exchange|delete|put)'
    r'\s*\(\s*"([^"]+)"',
    re.IGNORECASE
)
# OkHttp: new Request.Builder().url("/path")
_JAVA_OKHTTP_RE = re.compile(r'\.url\s*\(\s*"([^"]+)"', re.IGNORECASE)
# WebClient: webClient.get().uri("/path")
_JAVA_WEBCLIENT_RE = re.compile(
    r'\.(get|post|put|delete|patch)\s*\(\s*\)\.uri\s*\(\s*"([^"]+)"',
    re.IGNORECASE
)

_JAVA_REST_VERB_MAP = {
    "getforobject": "GET", "getforentity": "GET",
    "postforobject": "POST", "postforentity": "POST",
    "delete": "DELETE", "put": "PUT", "exchange": "ANY",
}

def _extract_java_api_calls(content: str) -> list:
    api_calls = []
    seen = set()
    def _add(method: str, raw: str):
        frag = raw.strip()
        if not frag or len(frag) < 2: return
        key = (method.upper(), frag)
        if key not in seen:
            seen.add(key)
            api_calls.append({"method": method.upper(), "path_fragment": frag})
    for m in _JAVA_RETROFIT_RE.finditer(content):
        _add(m.group(1), m.group(2))
    for m in _JAVA_REST_TEMPLATE_RE.finditer(content):
        verb = _JAVA_REST_VERB_MAP.get(m.group(1).lower(), "ANY")
        _add(verb, m.group(2))
    for m in _JAVA_OKHTTP_RE.finditer(content):
        _add("ANY", m.group(1))
    for m in _JAVA_WEBCLIENT_RE.finditer(content):
        _add(m.group(1), m.group(2))
    return api_calls

_JAVA_IMPORT_RE = re.compile(r'^\s*import\s+(?:static\s+)?([\w\.]+);', re.MULTILINE)
_JAVA_CLASS_RE = re.compile(r'class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w\.,\s]+))?')
_JAVA_INTF_RE = re.compile(r'interface\s+(\w+)(?:\s+extends\s+([\w\.,\s]+))?')
_JAVA_FUNC_RE = re.compile(r'(?:public|private|protected|static|final|\s)*\s+[\w\<\>\[\]]+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w\.,\s]+)?\s*\{')

# Spring Boot route annotation detection
# Matches: @GetMapping("/path"), @PostMapping, @RequestMapping(value="/path", method=...)
_JAVA_ROUTE_RE = re.compile(
    r'@(Get|Post|Put|Delete|Patch|Request)Mapping'
    r'(?:\s*\(\s*(?:value\s*=\s*)?"([^"]+)")?',
    re.IGNORECASE
)

def parse_java(content: str):
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    interfaces: List[InterfaceDef] = []
    raw_imports: List[str] = []
    
    for m in _JAVA_IMPORT_RE.finditer(content):
        raw_imports.append(m.group(1))
        
    for m in _JAVA_CLASS_RE.finditer(content):
        name, ext, impl = m.groups()
        extends_list = [ext] if ext else []
        if impl:
            extends_list.extend([x.strip() for x in impl.split(",") if x.strip()])
        line = content.count('\n', 0, m.start()) + 1
        classes.append(ClassDef(name=name, extends=extends_list, line=line))
        
    for m in _JAVA_INTF_RE.finditer(content):
        name, ext = m.groups()
        extends_list = [x.strip() for x in ext.split(",")] if ext else []
        line = content.count('\n', 0, m.start()) + 1
        interfaces.append(InterfaceDef(name=name, extends=extends_list, line=line))
        
    lines = content.splitlines()
    for m in _JAVA_FUNC_RE.finditer(content):
        name = m.group(1)
        if name not in {"if", "for", "while", "switch", "catch"}:
            line = content.count('\n', 0, m.start()) + 1
            # Look back up to 5 lines for route annotations
            api_routes = []
            start_line = max(0, line - 6)
            preceding = "\n".join(lines[start_line:line - 1])
            for rm in _JAVA_ROUTE_RE.finditer(preceding):
                verb = rm.group(1).upper()
                path = rm.group(2) or "/"
                if verb == "REQUEST":
                    verb = "ANY"
                api_routes.append({"method": verb, "path": path})
            entry = FunctionDef(name=name, params="", returnType="", line=line, calledBy=[], calls=[])
            if api_routes:
                entry["api_routes"] = api_routes
            functions.append(entry)
            
    return functions, classes, interfaces, raw_imports

def resolve_java_imports(file_path: str, raw_imports: List[str], workspace_root: str):
    results = []
    root = Path(workspace_root).resolve()
    for imp in raw_imports:
        if imp.endswith(".*"):
            continue
            
        rel_path = imp.replace(".", "/") + ".java"
        candidates = [
            root / rel_path,
            root / "src" / "main" / "java" / rel_path,
            root / "src" / "test" / "java" / rel_path,
            root / "src" / rel_path
        ]
        
        for c in candidates:
            if c.exists() and c.is_file():
                results.append(str(c.resolve()))
                break
                
    return results
