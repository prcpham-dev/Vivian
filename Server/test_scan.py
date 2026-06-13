import asyncio
from core.agents.vuln_agent import run_vuln_scan

async def main():
    state = {
        "workspace_root": "/Users/prc.__/Documents/codeMics/Vivian",
        "files": [{"path": "test/template/vuln.py", "content": open("test/template/vuln.py").read()}],
        "scan_target": "directory"
    }
    res = await run_vuln_scan(state)
    print(res)

asyncio.run(main())
