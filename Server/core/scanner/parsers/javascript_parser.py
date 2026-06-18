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

def parse_ts_js(content: str):
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    interfaces: List[InterfaceDef] = []
    raw_imports: List[str] = []
    
    for m in _JS_IMPORT_RE.finditer(content):
        imp = m.group(1) or m.group(2) or m.group(3)
        if imp: raw_imports.append(imp)
        
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        for m in _TS_CLASS_RE.finditer(line):
            name, ext = m.groups()
            classes.append(ClassDef(name=name, extends=[ext.strip()] if ext else [], line=i))
        for m in _TS_INTF_RE.finditer(line):
            name, ext = m.groups()
            interfaces.append(InterfaceDef(name=name, extends=[ext.strip()] if ext else [], line=i))
        for m in _JS_FUNC_RE.finditer(line):
            name = m.group(1) or m.group(2)
            if name:
                functions.append(FunctionDef(name=name, params="", returnType="", line=i, calledBy=[], calls=[]))
                
    return functions, classes, interfaces, raw_imports

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
