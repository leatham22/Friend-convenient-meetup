#!/usr/bin/env python3
"""
Utility functions for loading and working with the London transport network graph.

This module provides easy-to-use functions for loading the NetworkX graph from 
the JSON file and performing common operations like finding paths and analyzing
the network structure.
"""

import json
import os
import networkx as nx

# Try to import matplotlib, but continue if not available
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Note: matplotlib not installed. Visualization functions will be unavailable.")

# File paths
# Define the path to the graph file relative to the script's location
# Changed from os.path.join("network_data", "networkx_graph_fixed.json")
GRAPH_FILE = os.path.join("..", "graph_data", "networkx_graph_new.json")

def load_graph_from_json(file_path=GRAPH_FILE):
    """
    Load the custom JSON format into a NetworkX graph.
    
    Args:
        file_path: Path to the graph JSON file (default: graph_data/networkx_graph_new.json)
        
    Returns:
        NetworkX DiGraph object representing the transport network
    """
    # Load the JSON data from file
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Create a new directed graph
    # We use DiGraph because travel times might differ in each direction
    G = nx.DiGraph()
    
    # Add nodes with their attributes
    for node_name, attributes in data['nodes'].items():
        # The ** operator unpacks the dictionary as keyword arguments
        G.add_node(node_name, **attributes)
    
    # Add edges with their attributes
    for edge in data['edges']:
        # Extract source and target from the edge data
        source = edge.pop('source')
        target = edge.pop('target')
        # Add the edge with remaining attributes as keyword arguments
        G.add_edge(source, target, **edge)
    
    return G

# Add new function for loading standard node-link JSON format
def load_node_link_graph(filepath):
    """
    Loads a NetworkX graph from a JSON file (node-link format).

    Args:
        filepath: Path to the graph JSON file (node-link format).

    Returns:
        NetworkX graph object (DiGraph, MultiDiGraph, etc., based on file).
        Returns None if loading fails.
    """
    try:
        with open(filepath, 'r') as f:
            graph_data = json.load(f)
        # Determine if it's a multigraph based on the 'multigraph' key
        is_multigraph = graph_data.get('multigraph', False)
        # Determine if it's directed based on the 'directed' key
        is_directed = graph_data.get('directed', False)
        # Load the graph using networkx.node_link_graph
        # Specify directed and multigraph flags based on the loaded data
        # Explicitly set edges="edges" to match how the data was saved and address FutureWarning
        G = nx.node_link_graph(graph_data, directed=is_directed, multigraph=is_multigraph, edges="edges")
        print(f"Successfully loaded node-link graph from {filepath}")
        return G
    except FileNotFoundError:
        print(f"Error: Input graph file not found at {filepath}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filepath}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading the node-link graph: {e}")
        return None

def find_shortest_path(G, source, target, weight='weight'):
    """
    Find the shortest path between two stations.
    
    Args:
        G: NetworkX graph object
        source: Name of the source station
        target: Name of the target station
        weight: Edge attribute to use as weight (default: 'weight')
        
    Returns:
        List of stations in the path, or None if no path exists
    """
    # Verify that both stations exist in the graph
    if source not in G.nodes:
        print(f"Error: Source station '{source}' not found in graph")
        return None
    
    if target not in G.nodes:
        print(f"Error: Target station '{target}' not found in graph")
        return None
    
    try:
        # Use NetworkX's built-in shortest path algorithm
        path = nx.shortest_path(G, source, target, weight=weight)
        return path
    except nx.NetworkXNoPath:
        # If no path exists
        print(f"Error: No path exists between '{source}' and '{target}'")
        return None
    except Exception as e:
        # Handle any other errors
        print(f"Error finding path: {e}")
        return None

def find_station_by_substring(G, substring):
    """
    Find all stations that contain a given substring in their name.
    
    Args:
        G: NetworkX graph object
        substring: Case-insensitive substring to search for
        
    Returns:
        List of matching station names
    """
    substring = substring.lower()
    matches = [station for station in G.nodes() if substring in station.lower()]
    return sorted(matches)  # Sort for consistent results

def get_station_info(G, station_name):
    """
    Get detailed information about a station.
    
    Args:
        G: NetworkX graph object
        station_name: Name of the station
        
    Returns:
        Dictionary with station attributes, or None if station not found
    """
    if station_name in G.nodes:
        # Get all node attributes
        return dict(G.nodes[station_name])
    else:
        return None

def get_connected_stations(G, station_name):
    """
    Get all stations directly connected to the given station.
    
    Args:
        G: NetworkX graph object
        station_name: Name of the station
        
    Returns:
        Dictionary mapping connected station names to edge attributes
    """
    if station_name not in G.nodes:
        return {}
    
    # Get all neighbors (outgoing edges)
    connections = {}
    for neighbor in G.neighbors(station_name):
        # Get edge attributes
        edge_data = G.get_edge_data(station_name, neighbor)
        connections[neighbor] = edge_data
    
    return connections

def get_parent_child_stations(G):
    """
    Get all parent-child station pairs in the network.
    
    Args:
        G: NetworkX graph object
        
    Returns:
        List of (parent, child) pairs representing station connections
    """
    # Find all zero-weight transfer edges
    pairs = []
    for source, target, attrs in G.edges(data=True):
        # Check if this is a transfer edge
        if attrs.get('transfer', False) and attrs.get('weight', 1) == 0:
            pairs.append((source, target))
    
    return pairs

def get_graph_stats(G):
    """
    Get basic statistics about the graph.
    
    Args:
        G: NetworkX graph object
        
    Returns:
        Dictionary with graph statistics
    """
    # Count different types of stations by mode
    modes = {}
    for node, attrs in G.nodes(data=True):
        node_modes = attrs.get('modes', [])
        for mode in node_modes:
            modes[mode] = modes.get(mode, 0) + 1
    
    # Count different types of edges by line
    lines = {}
    for _, _, attrs in G.edges(data=True):
        line = attrs.get('line', '')
        if line:
            lines[line] = lines.get(line, 0) + 1
    
    # Count transfer edges
    transfer_edges = sum(1 for _, _, attrs in G.edges(data=True) if attrs.get('transfer', False))
    
    return {
        'nodes': G.number_of_nodes(),
        'edges': G.number_of_edges(),
        'modes': modes,
        'lines': lines,
        'transfer_edges': transfer_edges
    }

def visualize_graph(G, output_file=None, figsize=(12, 10)):
    """
    Create a simple visualization of the graph.
    
    Warning: This can be very slow and messy for large graphs.
    Best used for small subgraphs.
    
    Args:
        G: NetworkX graph object
        output_file: Path to save the image, or None to display (default: None)
        figsize: Figure size (width, height) in inches (default: (12, 10))
    """
    if not MATPLOTLIB_AVAILABLE:
        print("Cannot visualize: matplotlib is not installed")
        print("Install with: pip install matplotlib")
        return
        
    # Create a new figure
    plt.figure(figsize=figsize)
    
    # Get node positions based on latitude and longitude
    pos = {}
    for node in G.nodes():
        data = G.nodes[node]
        # Use longitude for x and latitude for y
        pos[node] = (data.get('lon', 0), data.get('lat', 0))
    
    # Draw the graph
    nx.draw_networkx(
        G, 
        pos=pos,
        node_size=50,  # Small nodes to reduce clutter
        font_size=8,   # Small font for readability
        with_labels=True,
        arrows=False   # No arrows to reduce clutter
    )
    
    # Set axis limits based on London's geographic boundaries
    plt.xlim(-0.5, 0.3)
    plt.ylim(51.4, 51.7)
    
    # Save or show the plot
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
    else:
        plt.show()

def example():
    """Example usage of the graph utilities."""
    print("Loading London transport network graph...")
    G = load_graph_from_json()
    
    # Get graph statistics
    stats = get_graph_stats(G)
    print(f"Graph loaded with {stats['nodes']} stations and {stats['edges']} connections")
    print(f"  {stats['transfer_edges']} are zero-weight transfer edges")
    
    # List a few modes
    print("\nStation counts by mode:")
    for mode, count in sorted(stats['modes'].items()):
        print(f"  {mode}: {count} stations")
    
    # Find a few important stations
    print("\nFinding stations by name substring:")
    kings_cross_matches = find_station_by_substring(G, "King's Cross")
    print(f"  'King's Cross' matches ({len(kings_cross_matches)}): {', '.join(kings_cross_matches)}")
    waterloo_matches = find_station_by_substring(G, "Waterloo")
    print(f"  'Waterloo' matches ({len(waterloo_matches)}): {', '.join(waterloo_matches)}")
    
    # Use exact station names from the data
    source = kings_cross_matches[0] if kings_cross_matches else None
    target = waterloo_matches[0] if waterloo_matches else None
    
    # Example: Find shortest path between two stations
    if source and target:
        print(f"\nFinding shortest path from '{source}' to '{target}'...")
        path = find_shortest_path(G, source, target)
        
        if path:
            print(f"Path found with {len(path)} stations:")
            for i, station in enumerate(path):
                print(f"  {i+1}. {station}")
    
    # Example: Get station info
    example_station = "Oxford Circus Underground Station"
    info = get_station_info(G, example_station)
    
    if info:
        print(f"\nInformation about {example_station}:")
        for key, value in info.items():
            # Format lists nicely for display
            if isinstance(value, list):
                if len(value) > 3:
                    print(f"  {key}: [{', '.join(str(v) for v in value[:3])}...]")
                else:
                    print(f"  {key}: {value}")
            else:
                print(f"  {key}: {value}")
    
    # Example: Get connected stations
    connections = get_connected_stations(G, example_station)
    
    if connections:
        print(f"\nStations connected to {example_station}:")
        for station, edge_data in connections.items():
            line = edge_data.get('line_name', 'Unknown line')
            print(f"  → {station} (via {line})")
    
    # Only try visualization if matplotlib is available
    if MATPLOTLIB_AVAILABLE:
        print("\nVisualization is available. Uncomment the line below to create a visualization.")
        # visualize_graph(G)  # Uncommented for now as it can be slow
    else:
        print("\nVisualization is not available (matplotlib not installed).")
    
    print("\nDone!")

if __name__ == "__main__":
    example() 