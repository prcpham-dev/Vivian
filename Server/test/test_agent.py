import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agents.graph_chat import stream_chat
from core.scanner.graph_builder import build_graph, save_cache

import networkx as nx
import matplotlib.pyplot as plt

async def main():
    workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Clear out old data
    data_dir = os.path.join(workspace, "data")
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            file_path = os.path.join(data_dir, f)
            if os.path.isfile(file_path):
                os.remove(file_path)
    else:
        os.makedirs(data_dir)
        
    print("Building cache...")
    graph = build_graph(workspace)
    save_cache(workspace, graph)
    print("Cache built.")
    
    # 2. Draw graph with matplotlib
    G = nx.DiGraph()
    
    dir_nodes, file_nodes, func_nodes, class_nodes, intf_nodes = [], [], [], [], []
    
    for node in graph["nodes"]:
        node_id = node["id"]
        label = node.get("label", "")
        display_name = node.get("properties", {}).get("name", node_id)
        G.add_node(node_id, label=display_name)
        
        if label == "Folder": dir_nodes.append(node_id)
        elif label == "File": file_nodes.append(node_id)
        elif label == "Function": func_nodes.append(node_id)
        elif label == "Class": class_nodes.append(node_id)
        elif label == "Interface": intf_nodes.append(node_id)
            
    contains_edges, dependency_edges, call_edges, inherits_edges = [], [], [], []
    
    for rel in graph["relationships"]:
        src, tgt, rel_type = rel["sourceId"], rel["targetId"], rel["type"]
        if rel_type == "CONTAINS": contains_edges.append((src, tgt))
        elif rel_type == "IMPORTS": dependency_edges.append((src, tgt))
        elif rel_type == "CALLS": call_edges.append((src, tgt))
        elif rel_type == "INHERITS": inherits_edges.append((src, tgt))
            
    plt.figure(figsize=(24, 16))
    pos = nx.spring_layout(G, k=0.3, iterations=100)
    
    nx.draw_networkx_nodes(G, pos, nodelist=dir_nodes, node_color='orange', node_size=3000, alpha=0.8, edgecolors='black')
    nx.draw_networkx_nodes(G, pos, nodelist=file_nodes, node_color='lightgreen', node_size=2000, alpha=0.8, edgecolors='black')
    nx.draw_networkx_nodes(G, pos, nodelist=func_nodes, node_color='pink', node_size=800, alpha=0.9, edgecolors='black')
    nx.draw_networkx_nodes(G, pos, nodelist=class_nodes, node_color='purple', node_size=1200, alpha=0.9, edgecolors='white')
    nx.draw_networkx_nodes(G, pos, nodelist=intf_nodes, node_color='violet', node_size=1200, alpha=0.9, edgecolors='black')
    
    labels = {n: d["label"] for n, d in G.nodes(data=True)}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=7, font_family='sans-serif', font_weight='bold')
    
    if contains_edges: nx.draw_networkx_edges(G, pos, edgelist=contains_edges, edge_color='black', width=1.0, arrows=True, arrowsize=15, alpha=0.4)
    if dependency_edges: nx.draw_networkx_edges(G, pos, edgelist=dependency_edges, edge_color='gray', width=1.0, arrows=True, arrowsize=15, alpha=0.3)
    if call_edges: nx.draw_networkx_edges(G, pos, edgelist=call_edges, edge_color='blue', width=1.5, arrows=True, arrowsize=15, alpha=0.8, connectionstyle='arc3,rad=0.1', style='dashed')
    if inherits_edges: nx.draw_networkx_edges(G, pos, edgelist=inherits_edges, edge_color='red', width=2.0, arrows=True, arrowsize=20, alpha=0.9, connectionstyle='arc3,rad=-0.1', style='dotted')
    
    plt.title(f"Deep Graph: Vivian Server\nOrange: Folder | Green: File | Pink: Func | Purple: Class | Violet: Interface\nBlack: Contains | Gray: Imports | Blue: Calls | Red: Inherits")
    plt.axis('off')
    plt.tight_layout()
    
    output_path = os.path.join(data_dir, "graph.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Graph image saved successfully to {output_path}")
    
    print("Opening matplotlib window...")
    plt.show(block=False)
    plt.pause(1)

    print("\n--- Starting Chat ---")
    query = "What classes are defined in models.py and who calls them?"
    
    async for token in stream_chat(
        user_message=query,
        history=[],
        selected_node=None,
        api_key="",
        model=""
    ):
        print(token, end="", flush=True)
        
    print("\n--- Chat Done ---")

if __name__ == "__main__":
    asyncio.run(main())
