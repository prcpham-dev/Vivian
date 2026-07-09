import sys
import json
from mcp.server.fastmcp import FastMCP
from core.scanner.graph_builder import load_cache
from core.scanner.discovery import read_file_contents

mcp = FastMCP(
    "Vivian",
    instructions="""
CRITICAL INSTRUCTION: You are connected to the Vivian structural graph MCP server.
When exploring this codebase, finding functions, or trying to understand how files relate to each other, you MUST prioritize using these Vivian MCP tools (e.g., get_workspace_graph, get_callers, find_symbol) FIRST.
Do NOT default to blindly using grep or reading raw files to map out relationships. Use these graph tools to get exact dependencies immediately.

IMPORTANT: The Vivian graph must be generated manually by opening the Vivian panel in VS Code and running a scan. If any tool returns an error about a missing graph, inform the user and ask them to open Vivian and scan their workspace first.
"""
)

_NO_GRAPH_MSG = (
    "ERROR: No Vivian graph found for this workspace. "
    "Please open the Vivian panel in VS Code and run a scan first, then retry."
)

@mcp.tool()
def get_workspace_graph(workspace_root: str) -> str:
    """
    Retrieves the cached Vivian structural knowledge graph for the given workspace_root.
    Returns the graph as a JSON string containing nodes and relationships.

    NOTE: The graph must be generated first by opening the Vivian panel in VS Code
    and clicking 'Scan'. This tool only reads the cached result — it does not build
    the graph automatically.
    """
    graph = load_cache(workspace_root)
    if not graph:
        return _NO_GRAPH_MSG
    return json.dumps(graph, indent=2)

@mcp.tool()
def get_node_connections(workspace_root: str, node_id: str) -> str:
    """
    Finds all incoming and outgoing edges for a specific node in the Vivian knowledge graph.
    Returns a JSON list of relationships connecting to this node.

    NOTE: The graph must be generated first by opening the Vivian panel in VS Code
    and clicking 'Scan'. This tool only reads the cached result.
    """
    graph_data = load_cache(workspace_root)
    if not graph_data:
        return _NO_GRAPH_MSG

    rels = graph_data.get("relationships", [])
    node_id_lower = node_id.lower()
    
    connections = []
    for r in rels:
        if str(r.get("sourceId", "")).lower() == node_id_lower or str(r.get("targetId", "")).lower() == node_id_lower:
            connections.append(r)
            
    return json.dumps(connections, indent=2)

@mcp.tool()
def read_workspace_file(workspace_root: str, relative_path: str) -> str:
    """
    Reads the content of a specific file within the workspace using Vivian's safe reading logic.
    """
    contents = read_file_contents(workspace_root, [relative_path])
    if relative_path in contents:
        return contents[relative_path]
    return f"Error: File {relative_path} not found or could not be read."

@mcp.tool()
def search_graph_nodes(workspace_root: str, query: str) -> str:
    """
    Searches the Vivian knowledge graph nodes for the given query string.
    Matches node properties like name, label, or filePath.

    NOTE: The graph must be generated first by opening the Vivian panel in VS Code
    and clicking 'Scan'. This tool only reads the cached result.
    """
    graph_data = load_cache(workspace_root)
    if not graph_data:
        return _NO_GRAPH_MSG

    nodes = graph_data.get("nodes", [])
    
    results = []
    query_lower = query.lower()
    for node in nodes:
        props = node.get("properties", {})
        
        name = str(props.get("name", "")).lower()
        filepath = str(props.get("filePath", "")).lower()
        node_id = str(node.get("id", "")).lower()
        label = str(node.get("label", "")).lower()
        
        if query_lower in name or query_lower in filepath or query_lower in node_id or query_lower in label:
            results.append(node)
            
    return json.dumps(results, indent=2)

@mcp.tool()
def get_project_stats(workspace_root: str) -> str:
    """
    Returns a high-level statistical overview of the codebase (total files, functions, classes).

    NOTE: The graph must be generated first by opening the Vivian panel in VS Code
    and clicking 'Scan'. This tool only reads the cached result.
    """
    try:
        graph = load_cache(workspace_root)
        if not graph:
            return _NO_GRAPH_MSG
            
        nodes = graph.get("nodes", [])
        files = sum(1 for n in nodes if n.get("label") == "File")
        funcs = sum(1 for n in nodes if n.get("label") == "Function")
        classes = sum(1 for n in nodes if n.get("label") == "Class")
        
        return f"Project Stats:\n- Files: {files}\n- Functions: {funcs}\n- Classes: {classes}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def get_file_details(workspace_root: str, filepath: str) -> str:
    """
    Returns the details of a specific file, including its classes, functions, and imports.

    NOTE: The graph must be generated first by opening the Vivian panel in VS Code
    and clicking 'Scan'. This tool only reads the cached result.
    """
    try:
        graph = load_cache(workspace_root)
        if not graph:
            return _NO_GRAPH_MSG
            
        nodes = graph.get("nodes", [])
        rels = graph.get("relationships", [])
        
        target = next((n for n in nodes if n.get("label") == "File" and str(n.get("id", "")).endswith(filepath)), None)
        if not target:
            return f"Error: File '{filepath}' not found in graph."
            
        actual_filepath = target.get("id")
        props = target.get("properties", {})
        funcs = [f.get("name") for f in props.get("functions", []) if f.get("name")]
        classes = [c.get("name") for c in props.get("classes", []) if c.get("name")]
        
        imports = [r["targetId"] for r in rels if r["type"] == "IMPORTS" and r["sourceId"] == actual_filepath]
        imported_by = [r["sourceId"] for r in rels if r["type"] == "IMPORTS" and r["targetId"] == actual_filepath]
        
        res = [f"File: {actual_filepath}"]
        if classes: res.append(f"Classes: {', '.join(classes)}")
        if funcs: res.append(f"Functions: {', '.join(funcs)}")
        if imports: res.append(f"Imports: {', '.join(imports)}")
        if imported_by: res.append(f"Imported by: {', '.join(imported_by)}")
        
        return "\n".join(res)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def find_symbol(workspace_root: str, symbol_name: str) -> str:
    """
    Searches the graph for a specific class or function and returns exactly where it is defined.

    NOTE: The graph must be generated first by opening the Vivian panel in VS Code
    and clicking 'Scan'. This tool only reads the cached result.
    """
    try:
        graph = load_cache(workspace_root)
        if not graph:
            return _NO_GRAPH_MSG
            
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

@mcp.tool()
def get_callers(workspace_root: str, function_id: str) -> str:
    """
    Finds all files/functions that call a specific function. Provide the full function ID (e.g. 'src/main.ts::myFunc').

    NOTE: The graph must be generated first by opening the Vivian panel in VS Code
    and clicking 'Scan'. This tool only reads the cursor/cached result.
    """
    try:
        graph = load_cache(workspace_root)
        if not graph:
            return _NO_GRAPH_MSG
            
        rels = graph.get("relationships", [])
        callers = [r["sourceId"] for r in rels if r["type"] == "CALLS" and r["targetId"] == function_id]
        
        if not callers:
            return f"No callers found for '{function_id}'."
            
        return f"Callers of '{function_id}':\n" + "\n".join(f"- {c}" for c in callers)
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio')
