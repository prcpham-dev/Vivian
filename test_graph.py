import sys
from Server.core.scanner.graph_builder import build_graph
try:
    build_graph("/Users/prc.__/Documents/codeMics/Vivian")
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
