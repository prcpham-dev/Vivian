import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from core.settings_manager import get_project_dir
from .constants import (
    CACHE_FILE_NAME,
    DEFAULT_IGNORE_PATTERNS,
    DEFAULT_MAX_DEPTH,
    SUPPORTED_EXTENSIONS,
)
from .discovery import read_file_contents, walk_repository_paths
from .file_parser import load_path_aliases, parse_file
from .graph_builder import (
    _build_directory_hierarchy,
    _track_function_calls_and_inheritance,
    add_relationship,
    build_graph,
    load_cache,
    save_cache,
)
from .types import GraphNode, GraphRelationship, KnowledgeGraph


_MTIMES_FILE = ".vivian-mtimes.json"

def _load_mtimes(workspace_root: str) -> Dict[str, float]:
    path = get_project_dir(workspace_root) / _MTIMES_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_mtimes(workspace_root: str, mtimes: Dict[str, float]) -> None:
    path = get_project_dir(workspace_root) / _MTIMES_FILE
    try:
        path.write_text(json.dumps(mtimes, indent=2), encoding="utf-8")
    except OSError:
        pass

def _collect_mtimes(workspace_root: str, rel_files: List[str]) -> Dict[str, float]:
    """Returns {rel_path: mtime} for every file that can be stat'd."""
    root = Path(workspace_root)
    result: Dict[str, float] = {}
    for rel in rel_files:
        try:
            result[rel] = (root / rel).stat().st_mtime
        except OSError:
            pass
    return result


def _is_owned_by(node_id: str, rel_path: str) -> bool:
    """True if node_id belongs to the file at rel_path (the file node itself or a child like ::ClassName)."""
    return node_id == rel_path or node_id.startswith(rel_path + "::")


def _remove_file_from_graph(
    rel_path: str,
    nodes_dict: Dict[str, GraphNode],
    relationships: List[GraphRelationship],
) -> Set[str]:
    """
    Removes all nodes and relationships that belong to rel_path.
    Returns a set of *other* file paths that had edges pointing INTO this file
    (callers / importers) — these neighbors must be re-analyzed too.
    """
    neighbor_files: Set[str] = set()
    for r in relationships:
        target_owned = _is_owned_by(r.get("targetId", ""), rel_path)
        source_owned = _is_owned_by(r.get("sourceId", ""), rel_path)
        if target_owned and not source_owned:
            file_part = r["sourceId"].split("::")[0]
            neighbor_files.add(file_part)

    for nid in [k for k in list(nodes_dict) if _is_owned_by(k, rel_path)]:
        del nodes_dict[nid]

    relationships[:] = [
        r for r in relationships
        if not _is_owned_by(r.get("sourceId", ""), rel_path)
        and not _is_owned_by(r.get("targetId", ""), rel_path)
    ]

    return neighbor_files

def _parse_and_insert_file(
    rel_path: str,
    content: str,
    workspace_root: str,
    path_aliases: dict,
    nodes_dict: Dict[str, GraphNode],
    relationships: List[GraphRelationship],
    class_locations: Dict[str, List[str]],
    known_files: Set[str],
) -> None:
    """
    Parses a single file and inserts its nodes + immediate edges
    (CONTAINS, IMPORTS) into the graph data structures.
    Does NOT run cross-file analysis — that's done separately.
    """
    root = Path(workspace_root)
    abs_path = str(root / rel_path)
    parsed = parse_file(abs_path, content, workspace_root, path_aliases)

    # Resolve import paths to relative
    resolved_imports: List[str] = []
    for imp_abs in parsed.get("imports", []):
        try:
            imp_rel = os.path.relpath(imp_abs, workspace_root).replace(os.sep, "/")
            resolved_imports.append(imp_rel)
        except ValueError:
            pass

    nodes_dict[rel_path] = {
        "id": rel_path,
        "label": "File",
        "properties": {
            "name": Path(rel_path).name,
            "functions":  parsed.get("functions", []),
            "classes":    parsed.get("classes", []),
            "interfaces": parsed.get("interfaces", []),
            "structs":    parsed.get("structs", []),
            "enums":      parsed.get("enums", []),
            "records":    parsed.get("records", []),
            "filePath":   rel_path,
        },
    }

    for func in parsed.get("functions", []):
        func_id = f"{rel_path}::{func['name']}"
        parent_id = rel_path
        func_line = func.get("line", 0)
        label = "Function"

        if func_line > 0:
            best_name, best_line = None, 0
            for c_type in ["classes", "interfaces", "structs", "enums", "records"]:
                for c in parsed.get(c_type, []):
                    c_line = c.get("line", 0)
                    if 0 < c_line <= func_line and c_line > best_line:
                        best_line = c_line
                        best_name = c["name"]
            if best_name:
                parent_id = f"{rel_path}::{best_name}"
                label = "Method"

        nodes_dict[func_id] = {
            "id": func_id,
            "label": label,
            "properties": {"name": func["name"], "line": func.get("line", 0)},
        }
        add_relationship(relationships, "CONTAINS", parent_id, func_id)

    # Class nodes
    for cls in parsed.get("classes", []):
        cls_id = f"{rel_path}::{cls['name']}"
        nodes_dict[cls_id] = {
            "id": cls_id,
            "label": "Class",
            "properties": {"name": cls["name"], "line": cls.get("line", 0)},
        }
        add_relationship(relationships, "CONTAINS", rel_path, cls_id)
        class_locations.setdefault(cls["name"], []).append(rel_path)

    # Interface nodes
    for intf in parsed.get("interfaces", []):
        intf_id = f"{rel_path}::{intf['name']}"
        nodes_dict[intf_id] = {
            "id": intf_id,
            "label": "Interface",
            "properties": {"name": intf["name"], "line": intf.get("line", 0)},
        }
        add_relationship(relationships, "CONTAINS", rel_path, intf_id)
        class_locations.setdefault(intf["name"], []).append(rel_path)

    # Struct nodes
    for struct in parsed.get("structs", []):
        struct_id = f"{rel_path}::{struct['name']}"
        nodes_dict[struct_id] = {
            "id": struct_id,
            "label": "Struct",
            "properties": {"name": struct["name"], "line": struct.get("line", 0)},
        }
        add_relationship(relationships, "CONTAINS", rel_path, struct_id)

    # Enum nodes
    for enum_def in parsed.get("enums", []):
        enum_id = f"{rel_path}::{enum_def['name']}"
        nodes_dict[enum_id] = {
            "id": enum_id,
            "label": "Enum",
            "properties": {"name": enum_def["name"], "line": enum_def.get("line", 0)},
        }
        add_relationship(relationships, "CONTAINS", rel_path, enum_id)

    # Record nodes
    for record in parsed.get("records", []):
        record_id = f"{rel_path}::{record['name']}"
        nodes_dict[record_id] = {
            "id": record_id,
            "label": "Record",
            "properties": {"name": record["name"], "line": record.get("line", 0)},
        }
        add_relationship(relationships, "CONTAINS", rel_path, record_id)

    # IMPORTS edges (only to files we know about)
    for target_rel in resolved_imports:
        if target_rel in known_files:
            add_relationship(relationships, "IMPORTS", rel_path, target_rel)

    # Directory hierarchy
    _build_directory_hierarchy(rel_path, nodes_dict, relationships)


def build_incremental_graph(
    workspace_root: str,
    ignore_patterns: Optional[List[str]] = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> KnowledgeGraph:
    """
    Incrementally rebuilds the knowledge graph for workspace_root.

    Strategy:
      1. Load the existing cache + stored file mtimes.
      2. Walk all source files and compare current mtimes against stored ones.
      3. Compute: added / modified / deleted file sets.
      4. If nothing changed → return cache as-is (instant).
      5. Otherwise:
         a. Remove dirty files' nodes + relationships from the graph.
         b. Collect "neighbor" files that had cross-file edges into dirty files.
         c. Re-parse dirty (non-deleted) + neighbor files.
         d. Re-run cross-file analysis (CALLS, INHERITS) for those files only.
      6. Persist updated graph + mtimes.

    Falls back to a full build if no cache or no mtime history is found.
    """
    patterns = list(DEFAULT_IGNORE_PATTERNS) + list(ignore_patterns or [])
    root = str(Path(workspace_root).resolve())

    existing_graph = load_cache(root)
    old_mtimes = _load_mtimes(root)

    if not existing_graph or not old_mtimes:
        print("[IncrementalGraph] No cache — running full build.")
        graph = build_graph(root, ignore_patterns, max_depth)
        all_files = walk_repository_paths(root, patterns, max_depth, SUPPORTED_EXTENSIONS)
        _save_mtimes(root, _collect_mtimes(root, all_files))
        save_cache(root, graph)
        return graph

    current_files = walk_repository_paths(root, patterns, max_depth, SUPPORTED_EXTENSIONS)
    current_mtimes = _collect_mtimes(root, current_files)

    old_set = set(old_mtimes)
    new_set = set(current_mtimes)

    added    = new_set - old_set
    deleted  = old_set - new_set
    modified = {
        f for f in (old_set & new_set)
        if current_mtimes[f] != old_mtimes[f]
    }
    dirty = added | modified | deleted

    if not dirty:
        print("[IncrementalGraph] No changes detected — returning cached graph.")
        return existing_graph

    print(
        f"[IncrementalGraph] Changes: +{len(added)} added  "
        f"~{len(modified)} modified  -{len(deleted)} deleted"
    )

    # ── Mutate in-memory graph ───────────────────────────────
    nodes_dict: Dict[str, GraphNode] = {
        n["id"]: n for n in existing_graph.get("nodes", [])
    }
    relationships: List[GraphRelationship] = list(existing_graph.get("relationships", []))

    # Remove dirty files and collect neighbors that need re-analysis
    neighbor_files: Set[str] = set()
    for rel_path in dirty:
        neighbors = _remove_file_from_graph(rel_path, nodes_dict, relationships)
        neighbor_files.update(neighbors)

    # Files to re-parse = (added + modified + affected neighbors) minus deleted
    re_parse: Set[str] = (
        (added | modified | neighbor_files) - deleted
    ) & new_set   # guard: only files that actually exist now

    if not re_parse:
        # Only deletions — just save the cleaned graph
        graph: KnowledgeGraph = {
            "nodes": list(nodes_dict.values()),
            "relationships": relationships,
            "timestamp": int(time.time() * 1000),
        }
        save_cache(root, graph)
        _save_mtimes(root, current_mtimes)
        print("[IncrementalGraph] Deletions only — graph cleaned.")
        return graph

    print(f"[IncrementalGraph] Re-parsing {len(re_parse)} / {len(new_set)} files.")

    # ── Re-parse dirty + neighbor files ─────────────────────
    file_contents = read_file_contents(root, list(re_parse))
    path_aliases = load_path_aliases(root)
    known_files: Set[str] = new_set  # full set for import resolution

    # Seed class_locations from UNCHANGED nodes still in graph
    class_locations: Dict[str, List[str]] = {}
    for node in nodes_dict.values():
        if node["label"] in ("Class", "Interface"):
            name = node["properties"].get("name", "")
            file_part = node["id"].split("::")[0]
            if name:
                class_locations.setdefault(name, []).append(file_part)

    for rel_path, content in file_contents.items():
        _parse_and_insert_file(
            rel_path, content, root, path_aliases,
            nodes_dict, relationships, class_locations, known_files,
        )

    # ── Cross-file analysis (scoped to re-parsed files only) ─
    # Unchanged files retain their existing CALLS/INHERITS edges.
    # We only need to re-derive edges that touch re-parsed file nodes.
    _track_function_calls_and_inheritance(
        nodes_dict,
        relationships,
        file_contents,          # only re-parsed content — avoids full rescan
        class_locations,
    )

    graph = {
        "nodes": list(nodes_dict.values()),
        "relationships": relationships,
        "timestamp": int(time.time() * 1000),
    }

    save_cache(root, graph)
    _save_mtimes(root, current_mtimes)

    total_nodes = len(graph["nodes"])
    total_rels  = len(graph["relationships"])
    print(
        f"[IncrementalGraph] Done. "
        f"{total_nodes} nodes, {total_rels} relationships in final graph."
    )
    return graph
