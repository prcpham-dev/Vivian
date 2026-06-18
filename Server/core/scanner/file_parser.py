import ast, re, json
from pathlib import Path
from typing import List, Optional

from .types import ParsedFile, FunctionDef, ClassDef, InterfaceDef

def parse_file(file_path: str, content: str, workspace_root: str, path_aliases: dict) -> ParsedFile:
    ext = Path(file_path).suffix.lower()
    
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    interfaces: List[InterfaceDef] = []
    imports: List[str] = []
    
    if ext == ".py":
        functions, classes, imports = _parse_python(content, file_path, workspace_root)
    elif ext in {".ts", ".tsx", ".js", ".jsx"}:
        functions, classes, interfaces, raw_imports = _parse_ts_js(content)
        imports = [_resolve_js(file_path, imp, workspace_root, path_aliases) for imp in raw_imports]
    elif ext == ".go":
        functions, classes, interfaces, raw_imports = _parse_go(content)
        imports = _resolve_go_imports(file_path, raw_imports, workspace_root)
    elif ext == ".rs":
        functions, classes, interfaces, imports = _parse_rust(content, file_path)
    elif ext == ".java":
        functions, classes, interfaces, raw_imports = _parse_java(content)
        imports = _resolve_java_imports(file_path, raw_imports, workspace_root)
    elif ext in {".c", ".cpp", ".h", ".hpp"}:
        functions, classes, interfaces, raw_imports = _parse_cpp(content)
        imports = _resolve_cpp_imports(file_path, raw_imports, workspace_root)
        
    # Filter out unresolvable imports
    resolved_imports = [imp for imp in imports if imp is not None]
    
    return ParsedFile(
        functions=functions,
        classes=classes,
        interfaces=interfaces,
        imports=resolved_imports
    )

# ---------------------------------------------------------------------------
# Python
_PY_FROM_RE = re.compile(r"^from\s+(\.*)(\w[\w.]*|)\s+import\s+", re.MULTILINE)
_PY_IMPORT_RE = re.compile(r"^import\s+([\w.]+)", re.MULTILINE)

def _parse_python(content: str, file_path: str, workspace_root: str):
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    imports: List[str] = []
    
    root = Path(workspace_root).resolve()
    from_dir = Path(file_path).parent
    
    ast_success = False
    
    # 1. Parse AST for functions, classes, and imports
    try:
        tree = ast.parse(content)
        ast_success = True
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in node.args.args]
                functions.append(FunctionDef(
                    name=node.name,
                    params=", ".join(args),
                    returnType="",
                    line=node.lineno,
                    calledBy=[], calls=[]
                ))
            elif isinstance(node, ast.ClassDef):
                bases = []
                for b in node.bases:
                    if isinstance(b, ast.Name): bases.append(b.id)
                    elif isinstance(b, ast.Attribute): bases.append(b.attr)
                classes.append(ClassDef(name=node.name, extends=bases, line=node.lineno))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    candidate = root.joinpath(*parts)
                    imports.append(_try_py(candidate))
            elif isinstance(node, ast.ImportFrom):
                level = node.level or 0
                module = node.module or ""
                
                if level > 0:
                    target_dir = from_dir
                    for _ in range(level - 1): target_dir = target_dir.parent
                    base_path = target_dir.joinpath(*module.split(".")) if module else target_dir
                else:
                    base_path = root.joinpath(*module.split(".")) if module else root
                    
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
                    candidate = root.joinpath(*parts)
                    imports.append(_try_py(candidate))
                    
        for m in _PY_IMPORT_RE.finditer(content):
            module = m.group(1)
            if module:
                parts = module.split(".")
                candidate = root.joinpath(*parts)
                imports.append(_try_py(candidate))
                
    return functions, classes, imports

def _try_py(base: Path) -> Optional[str]:
    p = base.with_suffix(".py")
    if p.exists(): return str(p)
    init = base / "__init__.py"
    if init.exists(): return str(init)
    return None

# ---------------------------------------------------------------------------
# JS / TS
_JS_IMPORT_RE = re.compile(
    r"(?:import\s+(?:[\w{},*\s]+\s+from\s+)?['\"](\.{1,2}[^'\"]+|@\/[^'\"]+)['\"]|"
    r"require\s*\(\s*['\"](\.{1,2}[^'\"]+)['\"]|"
    r"import\s*\(\s*['\"](\.{1,2}[^'\"]+)['\"])"
)
_TS_CLASS_RE = re.compile(r"class\s+(\w+)(?:\s+(?:extends|implements)\s+([\w<>,\s]+))?")
_TS_INTF_RE = re.compile(r"interface\s+(\w+)(?:\s+extends\s+([\w<>,\s]+))?")
_JS_FUNC_RE = re.compile(r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)")

def _parse_ts_js(content: str):
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

def _resolve_js(from_file: str, import_path: str, workspace_root: str, aliases: dict[str, str]) -> Optional[str]:
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

# ---------------------------------------------------------------------------
# Go
_GO_IMPORT_BLOCK_RE = re.compile(r'import\s*\(([^)]+)\)', re.DOTALL)
_GO_SINGLE_IMPORT_RE = re.compile(r'"([^"]+)"')
_GO_STRUCT_RE = re.compile(r'type\s+(\w+)\s+struct')
_GO_INTF_RE = re.compile(r'type\s+(\w+)\s+interface')
_GO_FUNC_RE = re.compile(r'func\s+(?:\([^)]+\)\s+)?(\w+)')

def _parse_go(content: str):
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

def _resolve_go_imports(file_path: str, raw_imports: List[str], workspace_root: str):
    results = []
    root = Path(workspace_root).resolve()
    for imp in raw_imports:
        candidate = root / imp
        if candidate.exists() and candidate.is_dir():
            go_files = list(candidate.glob("*.go"))
            if go_files: results.append(str(go_files[0]))
    return results

# ---------------------------------------------------------------------------
# Rust
_RS_MOD_RE = re.compile(r"^\s*(?:pub\s+)?mod\s+(\w+)\s*;", re.MULTILINE)
_RS_STRUCT_RE = re.compile(r"struct\s+(\w+)")
_RS_FUNC_RE = re.compile(r"fn\s+(\w+)")

def _parse_rust(content: str, file_path: str):
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

# ---------------------------------------------------------------------------
# C++
_CPP_INCLUDE_RE = re.compile(r'^\s*#\s*include\s*["<]([^">]+)[">]', re.MULTILINE)
_CPP_CLASS_RE = re.compile(r'class\s+(\w+)(?:\s*:\s*(?:public|private|protected)\s+(\w+))?')

def _parse_cpp(content: str):
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

def _resolve_cpp_imports(file_path: str, raw_imports: List[str], workspace_root: str):
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

# ---------------------------------------------------------------------------
# Java
_JAVA_IMPORT_RE = re.compile(r'^\s*import\s+(?:static\s+)?([\w\.]+);', re.MULTILINE)
_JAVA_CLASS_RE = re.compile(r'class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w\.,\s]+))?')
_JAVA_INTF_RE = re.compile(r'interface\s+(\w+)(?:\s+extends\s+([\w\.,\s]+))?')
_JAVA_FUNC_RE = re.compile(r'(?:public|private|protected|static|final|\s)*\s+[\w<>[\]]+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w\.,\s]+)?\s*\{')

def _parse_java(content: str):
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

def _resolve_java_imports(file_path: str, raw_imports: List[str], workspace_root: str):
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

_ALIAS_CONFIGS = ["tsconfig.json", "tsconfig.base.json", "jsconfig.json", "tsconfig.paths.json"]
_COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")

def load_path_aliases(workspace_root: str) -> dict[str, str]:
    root = Path(workspace_root)
    for config_name in _ALIAS_CONFIGS:
        config_path = root / config_name
        if not config_path.exists(): continue
        try:
            raw = config_path.read_text(encoding="utf-8")
            clean = _COMMENT_RE.sub("", raw)
            clean = _TRAILING_COMMA_RE.sub(r"\1", clean)
            data = json.loads(clean)
            paths_map = (data.get("compilerOptions") or {}).get("paths") or {}
            aliases: dict[str, str] = {}
            config_dir = config_path.parent
            for alias, targets in paths_map.items():
                if not targets: continue
                clean_alias = alias.rstrip("/*")
                clean_target = targets[0].rstrip("/*")
                resolved = Path(clean_target) if Path(clean_target).is_absolute() else config_dir / clean_target
                aliases[clean_alias] = str(resolved.resolve())
            return aliases
        except Exception:
            continue
    return {}
