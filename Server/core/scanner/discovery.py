import os
from typing import Dict, List, Optional, Tuple

from .constants import (
    DEFAULT_IGNORE_PATTERNS,
    SUPPORTED_EXTENSIONS,
    DEFAULT_MAX_DEPTH,
)

def walk_repository_paths(
    workspace_root: str,
    ignore_patterns: Optional[List[str]] = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
    supported_extensions: Optional[set[str]] = None,
) -> Dict[str, float]:
    """
    Walk the repository and return a dict of {relative_path: mtime}.
    The mtime is read for free from the OS DirEntry cache during the scan,
    eliminating the need for a second stat() pass.
    """
    ignore = set(ignore_patterns or DEFAULT_IGNORE_PATTERNS)
    exts = supported_extensions or SUPPORTED_EXTENSIONS
    root = os.path.abspath(workspace_root)

    results: Dict[str, float] = {}
    _fast_walk(root, root, ignore, exts, max_depth, 0, results)

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
    results: Dict[str, float],
) -> None:
    if depth > max_depth:
        return

    try:
        with os.scandir(current_dir) as it:
            for entry in it:
                if _should_ignore(entry.name, ignore):
                    continue

                if entry.is_dir(follow_symlinks=False):
                    _fast_walk(entry.path, root_dir, ignore, exts, max_depth, depth + 1, results)
                elif entry.is_file(follow_symlinks=False):
                    _, ext = os.path.splitext(entry.name)
                    if ext.lower() in exts:
                        rel_path = os.path.relpath(entry.path, root_dir)
                        rel_path = rel_path.replace(os.sep, "/")
                        # Grab mtime from the cached DirEntry stat — zero extra I/O
                        try:
                            results[rel_path] = entry.stat(follow_symlinks=False).st_mtime
                        except OSError:
                            results[rel_path] = 0.0
    except PermissionError:
        pass


def _should_ignore(name: str, ignore_patterns: set[str]) -> bool:
    # Exact match on the full directory/file name (case-insensitive).
    # Substring matching caused false positives, e.g. "bin" ignoring "binary_tree".
    name_lower = name.lower()
    return name_lower in {p.lower() for p in ignore_patterns}

def devTime():
    return "&nbsp;"