import json
import networkx as nx
import sys

def load_networkx_graph_and_station_data(graph_path):
    """
    Loads the NetworkX graph from the JSON file and extracts station data from nodes.

    Args:
        graph_path (str): Path to the NetworkX graph JSON file.

    Returns:
        tuple: (nx.MultiDiGraph, dict) containing the loaded graph and a
               station_data_lookup dictionary (name -> attributes), or (None, None) on failure.
    """
    try:
        with open(graph_path, 'r') as f:
            graph_data = json.load(f)

        # Ensure G is created as MultiDiGraph as specified in the JSON
        G = nx.MultiDiGraph()
        station_data_lookup = {}

        # Process nodes (list of dicts in the final graph format)
        if 'nodes' in graph_data and isinstance(graph_data['nodes'], list):
            for node_dict in graph_data['nodes']:
                if isinstance(node_dict, dict) and 'id' in node_dict:
                    node_id = node_dict['id'] # Node ID is the hub name
                    try:
                        # Add node directly with its attributes from the JSON dict
                        G.add_node(node_id, **node_dict) 
                        # *** Crucially, populate the lookup AFTER adding to graph, using graph's data view ***
                        station_data_lookup[node_id] = G.nodes[node_id] 
                    except Exception as e:
                        print(f"Error adding node or populating lookup for '{node_id}': {e}")
                else:
                    print(f"Warning: Skipping node due to missing 'id' or unexpected format: {node_dict}")
        else:
            print("Warning: 'nodes' key not found or not a list in graph data.")

        # Process edges (now a list of dicts with 'key')
        # Use 'links' key first, fallback to 'edges'
        edge_list_key = 'links' if 'links' in graph_data else 'edges'
        if edge_list_key in graph_data and isinstance(graph_data[edge_list_key], list):
            for edge_dict in graph_data[edge_list_key]:
                # Check for 'weight' instead of 'duration'
                if isinstance(edge_dict, dict) and all(k in edge_dict for k in ['source', 'target', 'key', 'weight']):
                    source = edge_dict['source']
                    target = edge_dict['target']
                    key = edge_dict['key'] # This is the line/mode/transfer identifier
                    # Use 'weight' key
                    weight = edge_dict['weight'] 
                    # Ensure nodes exist before adding edge
                    if G.has_node(source) and G.has_node(target):
                        # Add edge with key and weight as an attribute
                        G.add_edge(source, target, key=key, weight=weight) # Use weight=weight
                    else:
                        print(f"Warning: Skipping edge due to missing node(s): {source} -> {target} (Key: {key})")
                else:
                    # Update error message
                    print(f"Warning: Skipping invalid edge format or missing required keys (source, target, key, weight) in '{edge_list_key}' list: {edge_dict}")
        # Removed the elif 'edges' fallback as it's covered by the logic above
        else:
            print(f"Warning: Neither 'links' nor 'edges' key found or not a list in graph data.")

        print(f"Loaded NetworkX graph from '{graph_path}' with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
        print(f"Created station lookup for {len(station_data_lookup)} stations from graph nodes.")
        return G, station_data_lookup
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading or parsing NetworkX graph JSON from {graph_path}: {e}", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred during graph construction: {e}", file=sys.stderr)
        return None, None 