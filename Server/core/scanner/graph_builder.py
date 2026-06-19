import json, time, os, re
from pathlib import Path
from core.settings_manager import BASE_DIR
from typing import List, Optional, Dict
from .constants import (
    DEFAULT_IGNORE_PATTERNS,
    SUPPORTED_EXTENSIONS,
    DEFAULT_MAX_DEPTH,
    CACHE_FILE_NAME,
    GRAPH_FILE_NAME,
)

from core.settings_manager import get_project_dir
from .discovery import walk_repository_paths, read_file_contents
from .file_parser import parse_file, load_path_aliases
from .types import KnowledgeGraph, GraphNode, GraphRelationship, FunctionDef

def add_relationship(
    relationships: List[GraphRelationship], 
    rel_type: str, 
    source_id: str, 
    target_id: str, 
    confidence: float = 1.0, 
    reason: str = ""
):
    rel_id = f"{rel_type}_{source_id}->{target_id}"
    for r in relationships:
        if r["id"] == rel_id:
            return
    relationships.append({
        "id": rel_id,
        "type": rel_type,
        "sourceId": source_id,
        "targetId": target_id,
        "confidence": confidence,
        "reason": reason
    })

def build_graph(
    workspace_root: str,
    ignore_patterns: Optional[List[str]] = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> KnowledgeGraph:
    patterns = list(DEFAULT_IGNORE_PATTERNS) + list(ignore_patterns or [])
    root = str(Path(workspace_root).resolve())

    print(f"[GraphBuilder] Starting hierarchical graph build for: {root}")
    
    # Step 1: Walk
    relative_files = walk_repository_paths(root, patterns, max_depth, SUPPORTED_EXTENSIONS)
    print(f"[GraphBuilder] Discovered {len(relative_files)} files")

    # Step 2: Read
    file_contents = read_file_contents(root, relative_files)
    
    path_aliases = load_path_aliases(root)

    nodes_dict: dict[str, GraphNode] = {}
    relationships: List[GraphRelationship] = []
    
    class_locations: dict[str, str] = {}

    # Phase 3: Parse & Store
    for rel_path, content in file_contents.items():
        abs_path = str(Path(root) / rel_path)
        parsed = parse_file(abs_path, content, root, path_aliases)
        
        resolved_imports_rel = []
        for imp_abs in parsed.get("imports", []):
            try:
                imp_rel = os.path.relpath(imp_abs, root).replace(os.sep, "/")
                resolved_imports_rel.append(imp_rel)
            except ValueError:
                pass
        
        nodes_dict[rel_path] = {
            "id": rel_path,
            "label": "File",
            "properties": {
                "name": Path(rel_path).name,
                "functions": parsed.get("functions", []),
                "classes": parsed.get("classes", []),
                "interfaces": parsed.get("interfaces", []),
                "structs": parsed.get("structs", []),
                "enums": parsed.get("enums", []),
                "records": parsed.get("records", []),
                "filePath": rel_path
            }
        }
        
        for func in parsed.get("functions", []):
            func_id = f"{rel_path}::{func['name']}"
            
            parent_id = rel_path
            func_line = func.get("line", 0)
            label = "Function"
            
            if func_line > 0:
                best_parent_name = None
                best_parent_line = 0
                for c_type in ["classes", "interfaces", "structs", "enums", "records"]:
                    for c in parsed.get(c_type, []):
                        c_line = c.get("line", 0)
                        if c_line > 0 and c_line <= func_line:
                            if c_line > best_parent_line:
                                best_parent_line = c_line
                                best_parent_name = c["name"]
                
                if best_parent_name:
                    parent_id = f"{rel_path}::{best_parent_name}"
                    label = "Method"

            nodes_dict[func_id] = {
                "id": func_id,
                "label": label,
                "properties": {
                    "name": func['name'],
                    "line": func.get('line', 0)
                }
            }
            add_relationship(relationships, "CONTAINS", parent_id, func_id)
            
        for cls in parsed.get("classes", []):
            cls_id = f"{rel_path}::{cls['name']}"
            nodes_dict[cls_id] = {
                "id": cls_id,
                "label": "Class",
                "properties": {
                    "name": cls['name'],
                    "line": cls.get('line', 0)
                }
            }
            add_relationship(relationships, "CONTAINS", rel_path, cls_id)
            class_locations[cls['name']] = rel_path
            
        for intf in parsed.get("interfaces", []):
            intf_id = f"{rel_path}::{intf['name']}"
            nodes_dict[intf_id] = {
                "id": intf_id,
                "label": "Interface",
                "properties": {
                    "name": intf['name'],
                    "line": intf.get('line', 0)
                }
            }
            add_relationship(relationships, "CONTAINS", rel_path, intf_id)
            class_locations[intf['name']] = rel_path

        for struct in parsed.get("structs", []):
            struct_id = f"{rel_path}::{struct['name']}"
            nodes_dict[struct_id] = {
                "id": struct_id,
                "label": "Struct",
                "properties": {
                    "name": struct['name'],
                    "line": struct.get('line', 0)
                }
            }
            add_relationship(relationships, "CONTAINS", rel_path, struct_id)

        for enum_def in parsed.get("enums", []):
            enum_id = f"{rel_path}::{enum_def['name']}"
            nodes_dict[enum_id] = {
                "id": enum_id,
                "label": "Enum",
                "properties": {
                    "name": enum_def['name'],
                    "line": enum_def.get('line', 0)
                }
            }
            add_relationship(relationships, "CONTAINS", rel_path, enum_id)

        for record in parsed.get("records", []):
            record_id = f"{rel_path}::{record['name']}"
            nodes_dict[record_id] = {
                "id": record_id,
                "label": "Record",
                "properties": {
                    "name": record['name'],
                    "line": record.get('line', 0)
                }
            }
            add_relationship(relationships, "CONTAINS", rel_path, record_id)

        for target_imp in resolved_imports_rel:
            if target_imp in file_contents:
                add_relationship(relationships, "IMPORTS", rel_path, target_imp)

        _build_directory_hierarchy(rel_path, nodes_dict, relationships)

    _track_function_calls_and_inheritance(
        nodes_dict, 
        relationships, 
        file_contents, 
        class_locations
    )

    node_list = list(nodes_dict.values())

    graph = KnowledgeGraph(
        nodes=node_list,
        relationships=relationships,
        timestamp=int(time.time() * 1000),
    )

    print("Done!")
    return graph

def _build_directory_hierarchy(rel_path: str, nodes_dict: dict, relationships: List[GraphRelationship]):
    parts = rel_path.split("/")
    
    current_id = rel_path
    for i in range(len(parts) - 1, 0, -1):
        parent_id = "/".join(parts[:i])
        
        if parent_id not in nodes_dict:
            nodes_dict[parent_id] = {
                "id": parent_id,
                "label": "Folder",
                "properties": {
                    "name": parts[i-1],
                    "filePath": parent_id
                }
            }
            
        add_relationship(relationships, "CONTAINS", parent_id, current_id)
        current_id = parent_id

def _track_function_calls_and_inheritance(
    nodes: dict,
    relationships: List[GraphRelationship],
    contents: dict,
    class_locations: dict
):
    imports_map = {}
    for r in relationships:
        if r["type"] == "IMPORTS":
            imports_map.setdefault(r["sourceId"], []).append(r["targetId"])

    # 1. Inheritance
    for node_id, node in nodes.items():
        if node["label"] != "File": continue
        
        # For classes
        for c in node["properties"].get("classes", []):
            c_id = f"{node_id}::{c['name']}"
            for base in c.get("extends", []):
                base_loc = class_locations.get(base)
                if base_loc:
                    base_id = f"{base_loc}::{base}"
                    add_relationship(relationships, "INHERITS", c_id, base_id)
                    
        # For interfaces
        for i in node["properties"].get("interfaces", []):
            i_id = f"{node_id}::{i['name']}"
            for base in i.get("extends", []):
                base_loc = class_locations.get(base)
                if base_loc:
                    base_id = f"{base_loc}::{base}"
                    add_relationship(relationships, "INHERITS", i_id, base_id)

    # 2. Function Calls
    for src, targets in imports_map.items():
        src_content = contents.get(src, "")
        if not src_content: continue
            
        src_node = nodes.get(src)
        src_functions = []
        if src_node and src_node["label"] == "File":
            src_functions = src_node["properties"].get("functions", [])
            src_functions = sorted(src_functions, key=lambda f: f.get("line", 0))

        for tgt in targets:
            tgt_node = nodes.get(tgt)
            if not tgt_node or tgt_node["label"] != "File": continue
                
            for func in tgt_node["properties"].get("functions", []):
                func_name = func.get("name")
                if not func_name: continue
                    
                pattern = r'\b' + re.escape(func_name) + r'\b'
                for match in re.finditer(pattern, src_content):
                    line_no = src_content.count('\n', 0, match.start()) + 1
                    
                    caller_func = None
                    for i in range(len(src_functions)):
                        if src_functions[i].get("line", 0) <= line_no:
                            if i + 1 < len(src_functions) and src_functions[i+1].get("line", 0) <= line_no:
                                continue
                            caller_func = src_functions[i]
                            break
                            
                    func_id = f"{tgt}::{func_name}"
                    if caller_func:
                        caller_id = f"{src}::{caller_func['name']}"
                        func.setdefault("calledBy", []).append(caller_id)
                        add_relationship(relationships, "CALLS", caller_id, func_id)

def save_graph_file(workspace_root: str, graph: KnowledgeGraph) -> None:
    graph_path = Path(workspace_root) / GRAPH_FILE_NAME
    try:
        graph_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    except OSError:
        pass

def save_cache(workspace_root: str, graph: KnowledgeGraph) -> None:
    project_dir = get_project_dir(workspace_root)
    cache_path = project_dir / CACHE_FILE_NAME
    try:
        cache_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    except OSError:
        pass

def load_cache(workspace_root: str) -> Optional[KnowledgeGraph]:
    project_dir = get_project_dir(workspace_root)
    cache_path = project_dir / CACHE_FILE_NAME
    if not cache_path.exists(): return None
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        return KnowledgeGraph(**data)
    except Exception:
        return None
