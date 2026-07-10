import sys
import json
import threading
import time
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from core.scanner.graph_builder import load_cache, save_cache
from core.scanner.incremental_graph_builder import build_incremental_graph
from core.scanner.discovery import read_file_contents
from core.scanner.constants import SUPPORTED_EXTENSIONS

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    _WATCHDOG_AVAILABLE = True
except ImportError:
    _WATCHDOG_AVAILABLE = False

mcp = FastMCP(
    "Vivian",
    instructions="""
CRITICAL INSTRUCTION: You are connected to the Vivian structural graph MCP server.
When exploring this codebase, finding functions, or trying to understand how files relate to each other, you MUST prioritize using these Vivian MCP tools (e.g., get_workspace_graph, get_callers, find_symbol) FIRST.
Do NOT default to blindly using grep or reading raw files to map out relationships. Use these graph tools to get exact dependencies immediately.

AUTO-UPDATE: Call watch_workspace(workspace_root) once at the start of a session to keep the graph always up to date.
The watcher will automatically rebuild the graph in the background whenever source files change (with a 2-second debounce).
If the watcher is not active, you can still call get_workspace_graph — but results may be stale if files have changed since the last scan.
"""
)

_NO_GRAPH_MSG = (
    "ERROR: No Vivian graph found for this workspace. "
    "Please call watch_workspace(workspace_root) first, or open the Vivian panel in VS Code and run a scan."
)

_watcher_registry: dict[str, Observer] = {}
_rebuild_timers: dict[str, threading.Timer] = {}
_rebuild_lock = threading.Lock()

DEBOUNCE_SECONDS = 2.0

class _SourceFileEventHandler(FileSystemEventHandler):
    """Watches a workspace and triggers a debounced graph rebuild on any source file change."""

    def __init__(self, workspace_root: str):
        super().__init__()
        self.workspace_root = workspace_root

    def on_any_event(self, event):
        if event.is_directory:
            return
        src_path = getattr(event, "src_path", "") or ""
        ext = Path(src_path).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return
        _schedule_rebuild(self.workspace_root)


def _schedule_rebuild(workspace_root: str):
    """Cancels any pending rebuild timer and schedules a new one (debounce)."""
    with _rebuild_lock:
        existing = _rebuild_timers.get(workspace_root)
        if existing:
            existing.cancel()
        timer = threading.Timer(DEBOUNCE_SECONDS, _do_rebuild, args=[workspace_root])
        timer.daemon = True
        timer.start()
        _rebuild_timers[workspace_root] = timer


def _do_rebuild(workspace_root: str):
    """Runs an incremental graph rebuild and saves cache. Called in background thread."""
    try:
        print(f"[Vivian Watcher] Incremental rebuild for: {workspace_root}")
        graph = build_incremental_graph(workspace_root)
        print(f"[Vivian Watcher] Graph updated for: {workspace_root}")
    except Exception as e:
        print(f"[Vivian Watcher] Rebuild error for {workspace_root}: {e}")
    finally:
        with _rebuild_lock:
            _rebuild_timers.pop(workspace_root, None)


# ──────────────────────────────────────────────
# MCP Tools
# ──────────────────────────────────────────────

@mcp.tool()
def watch_workspace(workspace_root: str) -> str:
    """
    Starts auto-watching the given workspace_root for file changes.
    Whenever a source file is saved, the Vivian knowledge graph is automatically
    rebuilt in the background (with a 2-second debounce after the last change).

    Also builds the initial graph immediately if no cache exists yet.

    Call this ONCE at the beginning of a session to keep all graph tools up to date.
    Returns a status string indicating success or failure.
    """
    if not _WATCHDOG_AVAILABLE:
        return (
            "ERROR: 'watchdog' package is not installed. "
            "Run `pip install watchdog` in the Vivian Server environment and restart."
        )

    workspace_root = str(Path(workspace_root).resolve())

    # Build initial graph if missing (incremental builder handles the full-build fallback)
    if not load_cache(workspace_root):
        try:
            print(f"[Vivian Watcher] No cache found — building initial graph for: {workspace_root}")
            build_incremental_graph(workspace_root)
        except Exception as e:
            return f"ERROR: Failed to build initial graph: {e}"

    # Stop existing watcher if any
    if workspace_root in _watcher_registry:
        try:
            _watcher_registry[workspace_root].stop()
            _watcher_registry[workspace_root].join(timeout=2)
        except Exception:
            pass

    # Start new observer
    handler = _SourceFileEventHandler(workspace_root)
    observer = Observer()
    observer.schedule(handler, path=workspace_root, recursive=True)
    observer.daemon = True
    observer.start()
    _watcher_registry[workspace_root] = observer

    return (
        f"Watching '{workspace_root}' for changes. "
        f"Graph will auto-rebuild {DEBOUNCE_SECONDS}s after any source file is saved."
    )


@mcp.tool()
def stop_watch_workspace(workspace_root: str) -> str:
    """
    Stops the auto-watcher for the given workspace_root.
    The graph will no longer auto-rebuild when files change.
    """
    workspace_root = str(Path(workspace_root).resolve())
    observer = _watcher_registry.pop(workspace_root, None)
    if not observer:
        return f"No active watcher found for '{workspace_root}'."
    try:
        observer.stop()
        observer.join(timeout=2)
    except Exception as e:
        return f"Watcher stopped with warning: {e}"
    return f"Watcher stopped for '{workspace_root}'."


@mcp.tool()
def get_watch_status(workspace_root: str) -> str:
    """
    Returns whether the auto-watcher is currently active for the given workspace_root,
    and whether a rebuild is pending.
    """
    workspace_root = str(Path(workspace_root).resolve())
    is_watching = workspace_root in _watcher_registry and _watcher_registry[workspace_root].is_alive()
    is_rebuilding = workspace_root in _rebuild_timers

    if is_watching:
        status = f"ACTIVE — watching '{workspace_root}'"
        if is_rebuilding:
            status += " (rebuild pending...)"
        return status
    return f"INACTIVE — no watcher running for '{workspace_root}'."


@mcp.tool()
def rebuild_graph_now(workspace_root: str) -> str:
    """
    Manually triggers an immediate graph rebuild for the given workspace_root.
    Useful if you want to force a refresh without waiting for a file change event.
    """
    workspace_root = str(Path(workspace_root).resolve())
    try:
        print(f"[Vivian] Manual incremental rebuild for: {workspace_root}")
        graph = build_incremental_graph(workspace_root)
        nodes = len(graph.get("nodes", []))
        rels = len(graph.get("relationships", []))
        return f"Graph rebuilt successfully. {nodes} nodes, {rels} relationships."
    except Exception as e:
        return f"ERROR: Rebuild failed: {e}"


@mcp.tool()
def get_workspace_graph(workspace_root: str) -> str:
    """
    Retrieves the cached Vivian structural knowledge graph for the given workspace_root.
    Returns the graph as a JSON string containing nodes and relationships.

    TIP: Call watch_workspace(workspace_root) once at the start of a session so this
    cache is always kept fresh automatically.
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
