import re
from pathlib import Path
from typing import List

from ..types import FunctionDef, ClassDef, InterfaceDef

_GO_IMPORT_BLOCK_RE = re.compile(r'import\s*\(([^)]+)\)', re.DOTALL)
_GO_SINGLE_IMPORT_RE = re.compile(r'"([^"]+)"')
_GO_STRUCT_RE = re.compile(r'type\s+(\w+)\s+struct')
_GO_INTF_RE = re.compile(r'type\s+(\w+)\s+interface')
_GO_FUNC_RE = re.compile(r'func\s+(?:\([^)]+\)\s+)?(\w+)')

# Go HTTP route registration patterns:
# stdlib: http.HandleFunc("/path", handler)
# Gin: r.GET("/path", handler) / router.POST("/path", handler)
# Chi/Echo: r.Get("/path", handler)
# Gorilla Mux: router.HandleFunc("/path", handler).Methods("GET")
_GO_ROUTE_RE = re.compile(
    r'(?:\w+)\.(?:HandleFunc|(GET|POST|PUT|DELETE|PATCH|Head|Options|get|post|put|delete|patch))'
    r'\s*\(\s*"([^"]+)"',
)

def parse_go(content: str):
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    interfaces: List[InterfaceDef] = []
    raw_imports: List[str] = []
    
    for block_m in _GO_IMPORT_BLOCK_RE.finditer(content):
        for imp_m in _GO_SINGLE_IMPORT_RE.finditer(block_m.group(1)):
            raw_imports.append(imp_m.group(1))
            
    for m in _GO_STRUCT_RE.finditer(content):
        line = content.count('\n', 0, m.start()) + 1
        classes.append(ClassDef(name=m.group(1), extends=[], line=line))
    for m in _GO_INTF_RE.finditer(content):
        line = content.count('\n', 0, m.start()) + 1
        interfaces.append(InterfaceDef(name=m.group(1), extends=[], line=line))
    for m in _GO_FUNC_RE.finditer(content):
        line = content.count('\n', 0, m.start()) + 1
        functions.append(FunctionDef(name=m.group(1), params="", returnType="", line=line, calledBy=[], calls=[]))

    # Detect route registrations as synthetic function nodes
    for m in _GO_ROUTE_RE.finditer(content):
        verb = (m.group(1) or "ANY").upper()
        path = m.group(2)
        line = content.count('\n', 0, m.start()) + 1
        fn_name = f"Route_{verb}_{path.strip('/').replace('/', '_') or 'root'}"
        entry = FunctionDef(name=fn_name, params="", returnType="", line=line, calledBy=[], calls=[])
        entry["api_routes"] = [{"method": verb, "path": path}]
        functions.append(entry)
            
    return functions, classes, interfaces, raw_imports

def resolve_go_imports(file_path: str, raw_imports: List[str], workspace_root: str):
    results = []
    root = Path(workspace_root).resolve()
    for imp in raw_imports:
        candidate = root / imp
        if candidate.exists() and candidate.is_dir():
            go_files = list(candidate.glob("*.go"))
            if go_files: results.append(str(go_files[0]))
    return results
