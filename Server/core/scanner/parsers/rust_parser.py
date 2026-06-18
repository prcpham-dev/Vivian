import re
from pathlib import Path
from typing import List

from ..types import FunctionDef, ClassDef

_RS_MOD_RE = re.compile(r"^\s*(?:pub\s+)?mod\s+(\w+)\s*;", re.MULTILINE)
_RS_STRUCT_RE = re.compile(r"struct\s+(\w+)")
_RS_FUNC_RE = re.compile(r"fn\s+(\w+)")

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
        
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        for m in _RS_STRUCT_RE.finditer(line):
            classes.append(ClassDef(name=m.group(1), extends=[], line=i))
        for m in _RS_FUNC_RE.finditer(line):
            functions.append(FunctionDef(name=m.group(1), params="", returnType="", line=i, calledBy=[], calls=[]))
            
    return functions, classes, [], imports
