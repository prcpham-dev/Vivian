import os
from pathlib import Path
from typing import List
from core.scanner.graph_builder import load_cache
from config import settings

def get_graph_context() -> str:
    """
    Loads the knowledge graph from disk and formats it into a highly compressed 
    string to provide a 'Table of Contents' map to the LLM in memory.
    """
    graph = load_cache("")
    if not graph:
        return "No codebase graph available. Rely on general knowledge."

    nodes = graph.get("nodes", [])
    rels = graph.get("relationships", [])

    imports_map = {}
    for rel in rels:
        if rel["type"] == "IMPORTS":
            src = rel["sourceId"]
            tgt = rel["targetId"]
            if src not in imports_map:
                imports_map[src] = []
            imports_map[src].append(tgt)
            
    used_by_map = {}
    for rel in rels:
        if rel["type"] == "IMPORTS":
            src = rel["sourceId"]
            tgt = rel["targetId"]
            if tgt not in used_by_map:
                used_by_map[tgt] = []
            used_by_map[tgt].append(src)

    lines = ["## Codebase Architecture Summary\n"]
    
    for node in nodes:
        if node.get("label") == "File":
            file_path = node["id"]
            props = node.get("properties", {})
            
            funcs_list = []
            for f in props.get("functions", []):
                if "name" in f:
                    name = f["name"]
                    line = f.get("line")
                    funcs_list.append(f"{name} (L{line})" if line else name)
            func_str = ", ".join(funcs_list[:15]) if funcs_list else "none"

            classes_list = []
            for c in props.get("classes", []):
                if "name" in c:
                    name = c["name"]
                    line = c.get("line")
                    classes_list.append(f"{name} (L{line})" if line else name)
            cls_str = ", ".join(classes_list[:15]) if classes_list else "none"
            
            imports = imports_map.get(file_path, [])
            imp_str = ", ".join(imports[:15]) if imports else "none"
            
            used_by = used_by_map.get(file_path, [])
            used_str = ", ".join(used_by[:15]) if used_by else "none"
            
            lines.append(f"[{file_path}]")
            if cls_str != "none":
                lines.append(f"  classes  : {cls_str}")
            if func_str != "none":
                lines.append(f"  functions: {func_str}")
            lines.append(f"  imports  : {imp_str}")
            lines.append(f"  used by  : {used_str}\n")
            
    return "\n".join(lines)