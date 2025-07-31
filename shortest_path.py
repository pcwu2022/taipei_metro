import networkx as nx
import json

def json_to_graph(graph_data):
    """
    Convert a JSON graph representation back to a NetworkX graph.
    
    Args:
        graph_data (dict): Dictionary containing nodes and edges data
        
    Returns:
        nx.Graph: A NetworkX graph reconstructed from the JSON data
    """
    G = nx.Graph()
    
    # Add nodes with attributes
    for node_data in graph_data["nodes"]:
        G.add_node(
            node_data["id"],
            label=node_data.get("label", ""),
            time=node_data.get("time", 0)
        )
    
    # Add edges with attributes
    for edge_data in graph_data["edges"]:
        G.add_edge(
            edge_data["source"],
            edge_data["target"],
            type=edge_data.get("type", 0),
            time=edge_data.get("time", 0)
        )
    
    return G

with open("working/metro_graph.json", "r") as f:
    graph_data = json.load(f)

G = json_to_graph(graph_data)