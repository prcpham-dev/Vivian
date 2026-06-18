import re
from pathlib import Path
from typing import List

from ..types import FunctionDef, ClassDef, InterfaceDef

_GO_IMPORT_BLOCK_RE = re.compile(r'import\s*\(([^)]+)\)', re.DOTALL)
_GO_SINGLE_IMPORT_RE = re.compile(r'"([^"]+)"')
_GO_STRUCT_RE = re.compile(r'type\s+(\w+)\s+struct')
_GO_INTF_RE = re.compile(r'type\s+(\w+)\s+interface')
_GO_FUNC_RE = re.compile(r'func\s+(?:\([^)]+\)\s+)?(\w+)')

def parse_go(content: str):
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    interfaces: List[InterfaceDef] = []
    raw_imports: List[str] = []
    
    for block_m in _GO_IMPORT_BLOCK_RE.finditer(content):
        for imp_m in _GO_SINGLE_IMPORT_RE.finditer(block_m.group(1)):
            raw_imports.append(imp_m.group(1))
            
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        for m in _GO_STRUCT_RE.finditer(line):
            classes.append(ClassDef(name=m.group(1), extends=[], line=i))
        for m in _GO_INTF_RE.finditer(line):
            interfaces.append(InterfaceDef(name=m.group(1), extends=[], line=i))
        for m in _GO_FUNC_RE.finditer(line):
            functions.append(FunctionDef(name=m.group(1), params="", returnType="", line=i, calledBy=[], calls=[]))
            
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
