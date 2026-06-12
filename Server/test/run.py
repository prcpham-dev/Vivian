import sys
import os
import networkx as nx
import matplotlib.pyplot as plt

# Add the Server dir to path so we can import core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.scanner.graph_builder import build_graph

def main():
    workspace = "/Users/prc.__/Documents/codeMics/Vivian/Server/test/template"
    if not os.path.exists(workspace):
        print(f"Error: {workspace} does not exist.")
        sys.exit(1)
        
    print(f"Building graph for {workspace}...")
    graph = build_graph(workspace)
    
    G = nx.DiGraph()
    
    dir_nodes = []
    file_nodes = []
    func_nodes = []
    class_nodes = []
    intf_nodes = []
    
    # 1. Add nodes
    for node in graph["nodes"]:
        node_id = node["id"]
        label = node.get("label", "")
        # Fallback to id if properties missing name
        display_name = node.get("properties", {}).get("name", node_id)
        
        G.add_node(node_id, label=display_name)
        
        if label == "Folder": dir_nodes.append(node_id)
        elif label == "File": file_nodes.append(node_id)
        elif label == "Function": func_nodes.append(node_id)
        elif label == "Class": class_nodes.append(node_id)
        elif label == "Interface": intf_nodes.append(node_id)
            
    # 2. Add edges
    contains_edges = []
    dependency_edges = []
    call_edges = []
    inherits_edges = []
    
    for rel in graph["relationships"]:
        src = rel["sourceId"]
        tgt = rel["targetId"]
        rel_type = rel["type"]
        
        if rel_type == "CONTAINS": contains_edges.append((src, tgt))
        elif rel_type == "IMPORTS": dependency_edges.append((src, tgt))
        elif rel_type == "CALLS": call_edges.append((src, tgt))
        elif rel_type == "INHERITS": inherits_edges.append((src, tgt))
            
    # 3. Draw graph
    plt.figure(figsize=(24, 16))
    
    # Spring layout
    pos = nx.spring_layout(G, k=0.3, iterations=100)
    
    # Draw Nodes
    nx.draw_networkx_nodes(G, pos, nodelist=dir_nodes, node_color='orange', node_size=3000, alpha=0.8, edgecolors='black')
    nx.draw_networkx_nodes(G, pos, nodelist=file_nodes, node_color='lightgreen', node_size=2000, alpha=0.8, edgecolors='black')
    nx.draw_networkx_nodes(G, pos, nodelist=func_nodes, node_color='pink', node_size=800, alpha=0.9, edgecolors='black')
    nx.draw_networkx_nodes(G, pos, nodelist=class_nodes, node_color='purple', node_size=1200, alpha=0.9, edgecolors='white')
    nx.draw_networkx_nodes(G, pos, nodelist=intf_nodes, node_color='violet', node_size=1200, alpha=0.9, edgecolors='black')
    
    # Draw labels
    labels = {n: d["label"] for n, d in G.nodes(data=True)}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=7, font_family='sans-serif', font_weight='bold')
    
    # Draw Edges
    if contains_edges:
        nx.draw_networkx_edges(G, pos, edgelist=contains_edges, edge_color='black', width=1.0, arrows=True, arrowsize=15, alpha=0.4)
    if dependency_edges:
        nx.draw_networkx_edges(G, pos, edgelist=dependency_edges, edge_color='gray', width=1.0, arrows=True, arrowsize=15, alpha=0.3)
    if call_edges:
        nx.draw_networkx_edges(G, pos, edgelist=call_edges, edge_color='blue', width=1.5, arrows=True, arrowsize=15, alpha=0.8, connectionstyle='arc3,rad=0.1', style='dashed')
    if inherits_edges:
        nx.draw_networkx_edges(G, pos, edgelist=inherits_edges, edge_color='red', width=2.0, arrows=True, arrowsize=20, alpha=0.9, connectionstyle='arc3,rad=-0.1', style='dotted')
    
    # Draw Edge Labels
    edge_labels = {}
    for (u, v) in contains_edges:
        edge_labels[(u, v)] = "CONTAINS"
    for (u, v) in dependency_edges:
        edge_labels[(u, v)] = "IMPORTS"
    for (u, v) in call_edges:
        edge_labels[(u, v)] = "CALLS"
    for (u, v) in inherits_edges:
        edge_labels[(u, v)] = "INHERITS"
        
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=5, font_color='black', alpha=0.7)
    
    plt.title(f"Deep Graph: {os.path.basename(workspace)}\n"
              f"Orange: Folder | Green: File | Pink: Func | Purple: Class | Violet: Interface\n"
              f"Black: Contains | Gray: Imports | Blue: Calls | Red: Inherits")
    plt.axis('off')
    plt.tight_layout()
    
    print("Graph built successfully. Opening matplotlib window...")
    plt.show()

if __name__ == "__main__":
    main()
