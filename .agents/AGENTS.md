# Vivian Agent Rules

This file defines workspace-scoped behavior rules for agentic AI assistants (like Antigravity) pair-programming on this repository.

## Vivian MCP Server Permissions

The workspace is analyzed using Vivian's custom structural code graph MCP server, configured as `vivian-graph`.

1. **Checking Permissions**: At the start of a session, check if you have permissions to call tools under `mcp(vivian-graph/*)`.
2. **Proactive Request**: If permission to run these MCP tools is not already granted or is missing from your tool declarations, you MUST immediately call the `ask_permission` tool:
   - **Action**: `mcp`
   - **Target**: `vivian-graph/*`
   - **Reason**: Requesting access to Vivian's structural code graph tools to run auto-scan, trace functions, find symbols, and retrieve workspace statistics.
3. **Usage Priority**: Once authorized, prioritize using the Vivian graph tools (e.g., `watch_workspace`, `get_workspace_graph`, `find_symbol`, `get_callers`) over blind file reading or generic `grep_search` to understand codebase relationships.
