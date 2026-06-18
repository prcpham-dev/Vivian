import json, re
from pathlib import Path
from typing import List, Optional

from .types import ParsedFile, FunctionDef, ClassDef, InterfaceDef
from . import parsers

def parse_file(file_path: str, content: str, workspace_root: str, path_aliases: dict) -> ParsedFile:
    ext = Path(file_path).suffix.lower()
    
    functions: List[FunctionDef] = []
    classes: List[ClassDef] = []
    interfaces: List[InterfaceDef] = []
    imports: List[str] = []
    
    if ext == ".py":
        functions, classes, imports = parsers.parse_python(content, file_path, workspace_root)
    elif ext in {".ts", ".tsx", ".js", ".jsx"}:
        functions, classes, interfaces, raw_imports = parsers.parse_ts_js(content)
        imports = [parsers.resolve_js(file_path, imp, workspace_root, path_aliases) for imp in raw_imports]
    elif ext == ".go":
        functions, classes, interfaces, raw_imports = parsers.parse_go(content)
        imports = parsers.resolve_go_imports(file_path, raw_imports, workspace_root)
    elif ext == ".rs":
        functions, classes, interfaces, imports = parsers.parse_rust(content, file_path)
    elif ext == ".java":
        functions, classes, interfaces, raw_imports = parsers.parse_java(content)
        imports = parsers.resolve_java_imports(file_path, raw_imports, workspace_root)
    elif ext in {".c", ".cpp", ".h", ".hpp"}:
        functions, classes, interfaces, raw_imports = parsers.parse_cpp(content)
        imports = parsers.resolve_cpp_imports(file_path, raw_imports, workspace_root)
    elif ext == ".cs":
        functions, classes, interfaces, raw_imports = parsers.parse_cs(content)
        imports = parsers.resolve_cs_imports(file_path, raw_imports, workspace_root)
        
    # Filter out unresolvable imports
    resolved_imports = [imp for imp in imports if imp is not None]
    
    return ParsedFile(
        functions=functions,
        classes=classes,
        interfaces=interfaces,
        imports=resolved_imports
    )

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
