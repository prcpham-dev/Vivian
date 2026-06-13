from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from core.scanner.graph_builder import load_cache

def get_graph_tools(workspace_root: str):
    def _get_graph():
        graph = load_cache(workspace_root)
        if not graph:
            raise ValueError("No codebase graph available. Run scanner first.")
        return graph

    @tool
    def get_project_stats() -> str:
        """Returns a high-level statistical overview of the codebase (total files, functions, classes)."""
        try:
            graph = _get_graph()
            nodes = graph.get("nodes", [])
            
            files = sum(1 for n in nodes if n.get("label") == "File")
            funcs = sum(1 for n in nodes if n.get("label") == "Function")
            classes = sum(1 for n in nodes if n.get("label") == "Class")
            
            return f"Project Stats:\n- Files: {files}\n- Functions: {funcs}\n- Classes: {classes}"
        except Exception as e:
            return f"Error: {str(e)}"

    @tool
    def get_file_details(filepath: str) -> str:
        """Returns the details of a specific file, including its classes, functions, and imports."""
        try:
            graph = _get_graph()
            nodes = graph.get("nodes", [])
            rels = graph.get("relationships", [])
            
            target = next((n for n in nodes if n.get("label") == "File" and n.get("id", "").endswith(filepath)), None)
            if not target:
                return f"Error: File '{filepath}' not found in graph."
                
            filepath = target.get("id") # Use the actual matched path
                
            props = target.get("properties", {})
            funcs = [f.get("name") for f in props.get("functions", []) if f.get("name")]
            classes = [c.get("name") for c in props.get("classes", []) if c.get("name")]
            
            imports = [r["targetId"] for r in rels if r["type"] == "IMPORTS" and r["sourceId"] == filepath]
            imported_by = [r["sourceId"] for r in rels if r["type"] == "IMPORTS" and r["targetId"] == filepath]
            
            res = [f"File: {filepath}"]
            if classes: res.append(f"Classes: {', '.join(classes)}")
            if funcs: res.append(f"Functions: {', '.join(funcs)}")
            if imports: res.append(f"Imports: {', '.join(imports)}")
            if imported_by: res.append(f"Imported by: {', '.join(imported_by)}")
            
            return "\n".join(res)
        except Exception as e:
            return f"Error: {str(e)}"

    @tool
    def find_symbol(symbol_name: str) -> str:
        """Searches the graph for a specific class or function and returns where it is defined."""
        try:
            graph = _get_graph()
            nodes = graph.get("nodes", [])
            
            matches = []
            for n in nodes:
                label = n.get("label")
                if label in ("Function", "Class", "Interface"):
                    name = n.get("properties", {}).get("name")
                    if name == symbol_name:
                        matches.append(n.get("id"))
                        
            if not matches:
                return f"Symbol '{symbol_name}' not found."
                
            return f"Symbol '{symbol_name}' found at:\n" + "\n".join(f"- {m}" for m in matches)
        except Exception as e:
            return f"Error: {str(e)}"

    @tool
    def get_callers(function_id: str) -> str:
        """Finds all files/functions that call a specific function. Provide the full function ID (e.g. 'src/main.ts::myFunc')."""
        try:
            graph = _get_graph()
            rels = graph.get("relationships", [])
            
            callers = [r["sourceId"] for r in rels if r["type"] == "CALLS" and r["targetId"] == function_id]
            
            if not callers:
                return f"No callers found for '{function_id}'."
                
            return f"Callers of '{function_id}':\n" + "\n".join(f"- {c}" for c in callers)
        except Exception as e:
            return f"Error: {str(e)}"

    return [get_project_stats, get_file_details, find_symbol, get_callers]
