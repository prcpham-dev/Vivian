import re
from pathlib import Path
from typing import List

from ..types import FunctionDef, ClassDef, InterfaceDef

_CS_IMPORT_RE = re.compile(r'^\s*using\s+([\w\.]+);', re.MULTILINE)
_CS_CLASS_RE = re.compile(r'class\s+(\w+)(?:\s*:\s*([\w\.,\s<>]+))?')
_CS_INTF_RE = re.compile(r'interface\s+(\w+)(?:\s*:\s*([\w\.,\s<>]+))?')
_CS_FUNC_RE = re.compile(r'(?:public|private|protected|internal|static|virtual|override|async|\s)*\s+[\w<>[\]]+\s+(\w+)\s*\([^)]*\)\s*\{')

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
        
    for m in _CS_FUNC_RE.finditer(content):
        name = m.group(1)
        if name not in {"if", "for", "while", "switch", "catch", "get", "set"}:
            line = content.count('\n', 0, m.start()) + 1
            functions.append(FunctionDef(name=name, params="", returnType="", line=line, calledBy=[], calls=[]))
            
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
