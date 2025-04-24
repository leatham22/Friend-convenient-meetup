#!/usr/bin/env python3
"""
Script to check if the current networkx_graph.json file is in a format that can be
directly loaded as a NetworkX graph, or if it needs conversion.

This script will:
1. Attempt to load the JSON file directly as a NetworkX graph
2. If that fails, analyze the structure to determine what conversion is needed
3. Provide a sample of how to load the graph properly
"""

import json
import os
import networkx as nx

# File path
GRAPH_FILE = os.path.join("network_data", "networkx_graph.json")

def load_json_file(file_path):
    """
    Load a JSON file and return its contents.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        The parsed JSON data or None if there was an error
    """
    try:
        # Open the file in read mode and parse it as JSON
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # Print an error message if there's a problem
        print(f"Error loading {file_path}: {e}")
        return None

def try_direct_load():
    """
    Try to load the JSON file directly as a NetworkX graph.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # NetworkX has a function to load graphs directly from JSON
        G = nx.node_link_graph(load_json_file(GRAPH_FILE))
        
        # If we get here, it worked - print some basic info
        print(f"Successfully loaded the graph directly with NetworkX!")
        print(f"Graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
        return True
    except Exception as e:
        # If there's an error, print it and return False
        print(f"Could not load directly as a NetworkX graph: {e}")
        return False

def analyze_graph_structure():
    """
    Analyze the structure of the graph file to determine if and how it
    can be converted to a NetworkX graph.
    """
    # Load the raw JSON data
    data = load_json_file(GRAPH_FILE)
    if not data:
        return
    
    print("\nAnalyzing graph structure...")
    
    # Check the top-level structure
    top_keys = list(data.keys())
    print(f"Top-level keys: {', '.join(top_keys)}")
    
    # Check if it has the expected structure for our custom format
    if "nodes" in top_keys and "edges" in top_keys:
        print("\nThe graph is in a custom format with 'nodes' and 'edges' sections.")
        
        # Get some stats
        node_count = len(data.get("nodes", {}))
        edge_count = len(data.get("edges", []))
        print(f"Contains {node_count} nodes and {edge_count} edges")
        
        # Sample a node
        if node_count > 0:
            sample_node_key = list(data["nodes"].keys())[0]
            sample_node = data["nodes"][sample_node_key]
            print(f"\nSample node '{sample_node_key}':")
            for key, value in sample_node.items():
                # Truncate long values for display
                if isinstance(value, list) and len(value) > 3:
                    print(f"  {key}: [{', '.join(str(v) for v in value[:3])}...]")
                else:
                    print(f"  {key}: {value}")
        
        # Sample an edge
        if edge_count > 0:
            sample_edge = data["edges"][0]
            print(f"\nSample edge:")
            for key, value in sample_edge.items():
                print(f"  {key}: {value}")
        
        # Provide conversion code
        print("\nTo convert this format to a NetworkX graph, use the following code:")
        print("""
import json
import networkx as nx

def load_graph_from_json(file_path):
    '''Load the custom JSON format into a NetworkX graph.'''
    # Load the JSON data
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Create a new directed graph
    G = nx.DiGraph()
    
    # Add nodes with their attributes
    for node_name, attributes in data['nodes'].items():
        G.add_node(node_name, **attributes)
    
    # Add edges with their attributes
    for edge in data['edges']:
        source = edge.pop('source')
        target = edge.pop('target')
        G.add_edge(source, target, **edge)
    
    return G

# Usage
G = load_graph_from_json('network_data/networkx_graph.json')
""")
    else:
        print("\nThe graph is not in the expected custom format with 'nodes' and 'edges'.")
        print("Please check the structure manually to determine how to convert it.")

def main():
    """Main function to check the graph format."""
    print(f"Checking if {GRAPH_FILE} can be loaded directly as a NetworkX graph...")
    
    # First try loading directly
    direct_load_successful = try_direct_load()
    
    if not direct_load_successful:
        # If direct loading failed, analyze the structure
        analyze_graph_structure()

if __name__ == "__main__":
    main() 