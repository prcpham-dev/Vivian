import re
from pathlib import Path
from typing import List

from ..types import FunctionDef, ClassDef, InterfaceDef

_CS_IMPORT_RE = re.compile(r'^\s*using\s+([\w\.]+);', re.MULTILINE)
_CS_CLASS_RE = re.compile(r'class\s+(\w+)(?:\s*:\s*([\w\.,\s<>]+))?')
_CS_INTF_RE = re.compile(r'interface\s+(\w+)(?:\s*:\s*([\w\.,\s<>]+))?')
_CS_FUNC_RE = re.compile(r'(?:public|private|protected|internal|static|virtual|override|async|\s)*\s+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*\{')

# ASP.NET Core: [HttpGet("/path")], [HttpPost], [Route("/path")]
_CS_ATTR_ROUTE_RE = re.compile(
    r'\[(Http(Get|Post|Put|Delete|Patch)|Route)\s*(?:\(\s*"?([^")]*?)"?\s*\))?\]',
    re.IGNORECASE
)
# Minimal API: app.MapGet("/path", ...), endpoints.MapPost("/path", ...)
_CS_MINIMAL_RE = re.compile(
    r'\.Map(Get|Post|Put|Delete|Patch)\s*\(\s*"([^"]+)"',
    re.IGNORECASE
)

def parse_cs(content: str):
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    interfaces: List[InterfaceDef] = []
    raw_imports: List[str] = []
    
    for m in _CS_IMPORT_RE.finditer(content):
        raw_imports.append(m.group(1))
        
    for m in _CS_CLASS_RE.finditer(content):
        name, ext = m.groups()
        extends_list = []
        if ext:
            extends_list.extend([x.strip() for x in ext.split(",") if x.strip()])
        line = content.count('\n', 0, m.start()) + 1
        classes.append(ClassDef(name=name, extends=extends_list, line=line))
        
    for m in _CS_INTF_RE.finditer(content):
        name, ext = m.groups()
        extends_list = []
        if ext:
            extends_list.extend([x.strip() for x in ext.split(",") if x.strip()])
        line = content.count('\n', 0, m.start()) + 1
        interfaces.append(InterfaceDef(name=name, extends=extends_list, line=line))
        
    lines = content.splitlines()
    for m in _CS_FUNC_RE.finditer(content):
        name = m.group(1)
        if name not in {"if", "for", "while", "switch", "catch", "get", "set"}:
            line = content.count('\n', 0, m.start()) + 1
            # Look back up to 5 lines for [HttpGet/Post/...] or [Route] attributes
            api_routes = []
            start_line = max(0, line - 6)
            preceding = "\n".join(lines[start_line:line - 1])
            for rm in _CS_ATTR_ROUTE_RE.finditer(preceding):
                attr = rm.group(1).upper()  # HTTPGET, HTTPPOST, ROUTE
                path = rm.group(3) or "/"
                if attr == "ROUTE":
                    verb = "ANY"
                else:
                    verb = attr.replace("HTTP", "")
                api_routes.append({"method": verb, "path": path})
            entry = FunctionDef(name=name, params="", returnType="", line=line, calledBy=[], calls=[])
            if api_routes:
                entry["api_routes"] = api_routes
            functions.append(entry)

    # Minimal API: app.MapGet("/path", handler) — attach to a synthetic function node
    for m in _CS_MINIMAL_RE.finditer(content):
        verb = m.group(1).upper()
        path = m.group(2)
        line = content.count('\n', 0, m.start()) + 1
        fn_name = f"MapRoute_{verb}_{path.strip('/').replace('/', '_') or 'root'}"
        entry = FunctionDef(name=fn_name, params="", returnType="", line=line, calledBy=[], calls=[])
        entry["api_routes"] = [{"method": verb, "path": path}]
        functions.append(entry)
            
    return functions, classes, interfaces, raw_imports

def resolve_cs_imports(file_path: str, raw_imports: List[str], workspace_root: str):
    results = []
    root = Path(workspace_root).resolve()
    for imp in raw_imports:
        if imp.startswith("System"):
            continue
        rel_path = imp.replace(".", "/") + ".cs"
        candidate = root / rel_path
        if candidate.exists() and candidate.is_file():
            results.append(str(candidate))
    return results
