import re
from pathlib import Path
from typing import List

from ..types import FunctionDef, ClassDef, InterfaceDef

_JAVA_IMPORT_RE = re.compile(r'^\s*import\s+(?:static\s+)?([\w\.]+);', re.MULTILINE)
_JAVA_CLASS_RE = re.compile(r'class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w\.,\s]+))?')
_JAVA_INTF_RE = re.compile(r'interface\s+(\w+)(?:\s+extends\s+([\w\.,\s]+))?')
_JAVA_FUNC_RE = re.compile(r'(?:public|private|protected|static|final|\s)*\s+[\w<>[\]]+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w\.,\s]+)?\s*\{')

def parse_java(content: str):
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    interfaces: List[InterfaceDef] = []
    raw_imports: List[str] = []
    
    for m in _JAVA_IMPORT_RE.finditer(content):
        raw_imports.append(m.group(1))
        
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        for m in _JAVA_CLASS_RE.finditer(line):
            name, ext, impl = m.groups()
            extends_list = [ext] if ext else []
            if impl:
                extends_list.extend([x.strip() for x in impl.split(",") if x.strip()])
            classes.append(ClassDef(name=name, extends=extends_list, line=i))
            
        for m in _JAVA_INTF_RE.finditer(line):
            name, ext = m.groups()
            extends_list = [x.strip() for x in ext.split(",")] if ext else []
            interfaces.append(InterfaceDef(name=name, extends=extends_list, line=i))
            
        for m in _JAVA_FUNC_RE.finditer(line):
            name = m.group(1)
            if name not in {"if", "for", "while", "switch", "catch"}:
                functions.append(FunctionDef(name=name, params="", returnType="", line=i, calledBy=[], calls=[]))
                
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
