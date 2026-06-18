import ast, re
from pathlib import Path
from typing import List, Optional

from ..types import FunctionDef, ClassDef

_PY_FROM_RE = re.compile(r"^from\s+(\.*)(\w[\w.]*|)\s+import\s+", re.MULTILINE)
_PY_IMPORT_RE = re.compile(r"^import\s+([\w.]+)", re.MULTILINE)

def parse_python(content: str, file_path: str, workspace_root: str):
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    structs: List[Any] = []
    enums: List[Any] = []
    records: List[Any] = []
    imports: List[str] = []
    
    root = Path(workspace_root).resolve()
    from_dir = Path(file_path).parent
    
    def _find_py_base(parts: List[str]) -> Path:
        curr = from_dir
        while True:
            cand = curr.joinpath(*parts)
            if cand.exists() or cand.with_suffix(".py").exists() or (cand / "__init__.py").exists():
                return cand
            if curr == root or curr.parent == curr:
                break
            curr = curr.parent
        return root.joinpath(*parts)

    ast_success = False
    
    # 1. Parse AST for functions, classes, and imports
    try:
        tree = ast.parse(content)
        ast_success = True
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in node.args.args]
                functions.append({
                    "name": node.name,
                    "params": ", ".join(args),
                    "returnType": "",
                    "line": node.lineno,
                    "calledBy": [], "calls": []
                })
            elif isinstance(node, ast.ClassDef):
                bases = []
                is_enum = False
                is_struct = False
                for b in node.bases:
                    if isinstance(b, ast.Name):
                        bases.append(b.id)
                        if b.id == "Enum": is_enum = True
                        if b.id in ("NamedTuple", "TypedDict"): is_struct = True
                    elif isinstance(b, ast.Attribute):
                        bases.append(b.attr)
                        if b.attr == "Enum": is_enum = True
                
                # Check decorators for dataclass
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Name) and dec.id == "dataclass":
                        is_struct = True
                    elif isinstance(dec, ast.Call) and getattr(dec.func, 'id', '') == "dataclass":
                        is_struct = True

                if is_enum:
                    enums.append({"name": node.name, "line": node.lineno})
                elif is_struct:
                    structs.append({"name": node.name, "line": node.lineno})
                elif node.name.endswith("Record"):
                    records.append({"name": node.name, "line": node.lineno})
                else:
                    classes.append({"name": node.name, "extends": bases, "line": node.lineno})
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    candidate = _find_py_base(parts)
                    imports.append(_try_py(candidate))
            elif isinstance(node, ast.ImportFrom):
                level = node.level or 0
                module = node.module or ""
                
                if level > 0:
                    target_dir = from_dir
                    for _ in range(level - 1): target_dir = target_dir.parent
                    base_path = target_dir.joinpath(*module.split(".")) if module else target_dir
                else:
                    base_path = _find_py_base(module.split(".")) if module else root
                    
                imports.append(_try_py(base_path))
                
                for alias in node.names:
                    if alias.name != "*":
                        imports.append(_try_py(base_path / alias.name))
    except SyntaxError:
        pass
        
    # 2. Parse Imports (Fallback Regex if AST fails)
    if not ast_success:
        for m in _PY_FROM_RE.finditer(content):
            dots = m.group(1)
            module = m.group(2)
            if dots:
                target_dir = from_dir
                for _ in range(len(dots) - 1): target_dir = target_dir.parent
                parts = module.split(".") if module else []
                candidate = target_dir.joinpath(*parts)
                imports.append(_try_py(candidate))
            else:
                if module:
                    parts = module.split(".")
                    candidate = _find_py_base(parts)
                    imports.append(_try_py(candidate))
                    
        for m in _PY_IMPORT_RE.finditer(content):
            module = m.group(1)
            if module:
                parts = module.split(".")
                candidate = _find_py_base(parts)
                imports.append(_try_py(candidate))
                
    return functions, classes, structs, enums, records, imports

def _try_py(base: Path) -> Optional[str]:
    p = base.with_suffix(".py")
    if p.exists(): return str(p)
    init = base / "__init__.py"
    if init.exists(): return str(init)
    return None
