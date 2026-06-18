import re
from pathlib import Path
from typing import List

from ..types import FunctionDef, ClassDef

_CPP_INCLUDE_RE = re.compile(r'^\s*#\s*include\s*["<]([^">]+)[">]', re.MULTILINE)
_CPP_CLASS_RE = re.compile(r'class\s+(\w+)(?:\s*:\s*(?:public|private|protected)\s+(\w+))?')

def parse_cpp(content: str):
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    raw_imports: List[str] = []
    
    for m in _CPP_INCLUDE_RE.finditer(content):
        raw_imports.append(m.group(1))
        
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        for m in _CPP_CLASS_RE.finditer(line):
            name, ext = m.groups()
            classes.append(ClassDef(name=name, extends=[ext] if ext else [], line=i))
            
    return functions, classes, [], raw_imports

def resolve_cpp_imports(file_path: str, raw_imports: List[str], workspace_root: str):
    results = []
    from_dir = Path(file_path).parent
    root = Path(workspace_root).resolve()
    for include in raw_imports:
        candidates = [from_dir / include, root / include, root / "include" / include, root / "src" / include]
        for c in candidates:
            if c.exists() and c.is_file():
                results.append(str(c.resolve()))
                break
    return results
