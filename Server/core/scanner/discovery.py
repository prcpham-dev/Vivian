import os
from typing import List, Optional, Dict

from .constants import (
    DEFAULT_IGNORE_PATTERNS,
    SUPPORTED_EXTENSIONS,
    DEFAULT_MAX_DEPTH,
    MAX_FILES,
)

def walk_repository_paths(
    workspace_root: str,
    ignore_patterns: Optional[List[str]] = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
    supported_extensions: Optional[set[str]] = None,
) -> List[str]:
    """
    Walk the repository and return a list of relative paths.
    """
    ignore = set(ignore_patterns or DEFAULT_IGNORE_PATTERNS)
    exts = supported_extensions or SUPPORTED_EXTENSIONS
    root = os.path.abspath(workspace_root)

    results: List[str] = []
    _fast_walk(root, root, ignore, exts, max_depth, 0, results)

    if len(results) >= MAX_FILES:
        print(f"[discovery] WARNING: hit file limit ({MAX_FILES}). "
              f"Consider narrowing the selected directory.")

    return results

def read_file_contents(
    workspace_root: str,
    relative_paths: List[str]
) -> Dict[str, str]:
    """
    Read file contents for a specific set of relative paths.
    Returns a dict mapping relative path to content.
    """
    contents = {}
    root = os.path.abspath(workspace_root)
    for rel_path in relative_paths:
        full_path = os.path.join(root, rel_path)
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                contents[rel_path] = f.read()
        except OSError:
            pass
    return contents


def _fast_walk(
    current_dir: str,
    root_dir: str,
    ignore: set[str],
    exts: set[str],
    max_depth: int,
    depth: int,
    results: List[str],
) -> None:
    if depth > max_depth or len(results) >= MAX_FILES:
        return

    try:
        with os.scandir(current_dir) as it:
            for entry in it:
                if len(results) >= MAX_FILES:
                    return
                
                if _should_ignore(entry.name, ignore):
                    continue

                if entry.is_dir(follow_symlinks=False):
                    _fast_walk(entry.path, root_dir, ignore, exts, max_depth, depth + 1, results)
                elif entry.is_file(follow_symlinks=False):
                    _, ext = os.path.splitext(entry.name)
                    if ext.lower() in exts:
                        # Convert to relative path and use forward slashes
                        rel_path = os.path.relpath(entry.path, root_dir)
                        rel_path = rel_path.replace(os.sep, "/")
                        results.append(rel_path)
    except PermissionError:
        pass


def _should_ignore(name: str, ignore_patterns: set[str]) -> bool:
    name_lower = name.lower()
    for pattern in ignore_patterns:
        if pattern.lower() in name_lower:
            return True
    return False
