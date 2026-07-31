import re
from pathlib import Path
from typing import List

from ..types import FunctionDef, ClassDef

_RS_MOD_RE = re.compile(r"^\s*(?:pub\s+)?mod\s+(\w+)\s*;", re.MULTILINE)
_RS_STRUCT_RE = re.compile(r"struct\s+(\w+)")
_RS_FUNC_RE = re.compile(r"fn\s+(\w+)")

# Actix-web / Axum route macros:
# #[get("/path")], #[post("/path")], #[route("/path", method="GET")]
_RS_ROUTE_RE = re.compile(
    r'#\[(get|post|put|delete|patch|head|options|route)\s*\(\s*"([^"]+)"',
    re.IGNORECASE
)

def parse_rust(content: str, file_path: str):
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    imports: List[str] = []
    
    from_dir = Path(file_path).parent
    for m in _RS_MOD_RE.finditer(content):
        mod_name = m.group(1)
        candidate1 = from_dir / f"{mod_name}.rs"
        candidate2 = from_dir / mod_name / "mod.rs"
        if candidate1.exists(): imports.append(str(candidate1))
        elif candidate2.exists(): imports.append(str(candidate2))
        
    for m in _RS_STRUCT_RE.finditer(content):
        line = content.count('\n', 0, m.start()) + 1
        classes.append(ClassDef(name=m.group(1), extends=[], line=line))
        
    lines = content.splitlines()
    for m in _RS_FUNC_RE.finditer(content):
        line = content.count('\n', 0, m.start()) + 1
        # Look back up to 3 lines for route proc-macro attributes
        api_routes = []
        start_line = max(0, line - 4)
        preceding = "\n".join(lines[start_line:line - 1])
        for rm in _RS_ROUTE_RE.finditer(preceding):
            verb = rm.group(1).upper()
            path = rm.group(2)
            if verb == "ROUTE":
                verb = "ANY"
            api_routes.append({"method": verb, "path": path})
        entry = FunctionDef(name=m.group(1), params="", returnType="", line=line, calledBy=[], calls=[])
        if api_routes:
            entry["api_routes"] = api_routes
        functions.append(entry)
            
    return functions, classes, [], imports
