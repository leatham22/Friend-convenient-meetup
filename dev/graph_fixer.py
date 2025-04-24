#!/usr/bin/env python3
"""
Script to fix connectivity issues in the London transport network graph.

This script identifies and fixes connectivity issues by adding bidirectional 
edges between stations on the same line, ensuring the graph is properly connected.
"""

import os
import networkx as nx
from collections import defaultdict

# Import our graph utility functions
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from network_data.graph_utils import load_graph_from_json

# File paths
GRAPH_FILE = os.path.join("network_data", "networkx_graph.json")
FIXED_GRAPH_FILE = os.path.join("network_data", "networkx_graph_fixed.json")

def get_connected_components(G):
    """
    Find all connected components in the graph.
    
    Args:
        G: NetworkX graph object
        
    Returns:
        List of sets of nodes, where each set represents a connected component
    """
    # For directed graphs, we need to use weakly_connected_components
    if isinstance(G, nx.DiGraph):
        return list(nx.weakly_connected_components(G))
    else:
        return list(nx.connected_components(G))

def group_stations_by_line(G):
    """
    Group stations by the lines they serve.
    
    Args:
        G: NetworkX graph object
        
    Returns:
        Dictionary mapping line IDs to lists of station names
    """
    # Create a dictionary to store stations by line
    stations_by_line = defaultdict(list)
    
    # Go through each node in the graph
    for node, attrs in G.nodes(data=True):
        # Get the lines for this station
        lines = attrs.get('lines', [])
        
        # Add this station to each of its lines
        for line in lines:
            stations_by_line[line].append(node)
    
    return stations_by_line

def ensure_bidirectional_edges(G):
    """
    Ensure all edges are bidirectional by adding the reverse edge if missing.
    
    Args:
        G: NetworkX graph object
        
    Returns:
        Number of edges added
    """
    # Keep track of how many edges we add
    added_edges = 0
    
    # Get a list of all edges
    all_edges = list(G.edges(data=True))
    
    # For each edge, check if the reverse exists
    for source, target, attrs in all_edges:
        # Check if the reverse edge exists
        if not G.has_edge(target, source):
            # Copy the attributes for the new edge
            new_attrs = attrs.copy()
            # Add the reverse edge
            G.add_edge(target, source, **new_attrs)
            added_edges += 1
    
    return added_edges

def connect_stations_on_same_line(G):
    """
    Connect stations that are on the same line but not connected.
    
    Args:
        G: NetworkX graph object
        
    Returns:
        Number of edges added
    """
    # Group stations by line
    stations_by_line = group_stations_by_line(G)
    
    # Keep track of how many edges we add
    added_edges = 0
    
    # Process each line
    for line, stations in stations_by_line.items():
        # Skip lines with too few stations
        if len(stations) < 2:
            continue
        
        # Create a subgraph for this line
        subgraph = G.subgraph(stations).copy()
        
        # Find connected components in this subgraph
        components = get_connected_components(subgraph)
        
        # If there's more than one component, we need to connect them
        if len(components) > 1:
            print(f"Fixing line {line} with {len(components)} components")
            
            # Get line metadata from existing edges
            line_attrs = None
            for u, v, attrs in G.edges(data=True):
                if 'line' in attrs and attrs['line'] == line:
                    line_attrs = {
                        'line': line,
                        'line_name': attrs.get('line_name', line),
                        'mode': attrs.get('mode', ''),
                        'weight': 1,
                        'fixed': True  # Mark as a fixed edge
                    }
                    break
            
            # If we couldn't find line metadata, create default
            if not line_attrs:
                line_attrs = {
                    'line': line,
                    'line_name': line.capitalize(),
                    'mode': 'unknown',
                    'weight': 1,
                    'fixed': True
                }
            
            # Connect components by adding edges between their largest stations
            sorted_components = sorted(components, key=len, reverse=True)
            
            # Get stations from the largest component
            largest_component = sorted_components[0]
            
            # Connect each smaller component to the largest
            for component in sorted_components[1:]:
                # Get a station from this component
                station_from_component = next(iter(component))
                
                # Get a station from the largest component
                station_from_largest = next(iter(largest_component))
                
                # Add edges in both directions
                G.add_edge(station_from_component, station_from_largest, **line_attrs)
                G.add_edge(station_from_largest, station_from_component, **line_attrs)
                
                added_edges += 2
                print(f"  Connected {station_from_component} <-> {station_from_largest}")
    
    return added_edges

def connect_isolated_stations(G):
    """
    Connect isolated stations (those with no connections) to the main component.
    
    Args:
        G: NetworkX graph object
        
    Returns:
        Number of edges added
    """
    # Find the largest component
    components = get_connected_components(G)
    sorted_components = sorted(components, key=len, reverse=True)
    
    # The largest component will be the "main" component
    main_component = sorted_components[0]
    
    # Find isolated stations (nodes with no edges)
    isolated_stations = [node for node in G.nodes() if G.degree(node) == 0]
    
    # Get a representative station from the main component
    main_station = next(iter(main_component))
    
    # Connect isolated stations to the main component
    added_edges = 0
    for station in isolated_stations:
        # Add edges in both directions
        G.add_edge(station, main_station, weight=10, fixed=True, transfer=True)
        G.add_edge(main_station, station, weight=10, fixed=True, transfer=True)
        added_edges += 2
        print(f"Connected isolated station {station} to {main_station}")
    
    return added_edges

def fix_connectivity_issues(G):
    """
    Fix connectivity issues in the graph.
    
    Args:
        G: NetworkX graph object
        
    Returns:
        Fixed graph
    """
    # First, ensure all existing edges are bidirectional
    print("\nEnsuring all edges are bidirectional...")
    added_bidirectional = ensure_bidirectional_edges(G)
    print(f"Added {added_bidirectional} bidirectional edges")
    
    # Second, connect stations on the same line
    print("\nConnecting stations on the same line...")
    added_line_connections = connect_stations_on_same_line(G)
    print(f"Added {added_line_connections} edges to connect stations on the same line")
    
    # Finally, connect any isolated stations
    print("\nConnecting isolated stations...")
    added_isolated = connect_isolated_stations(G)
    print(f"Added {added_isolated} edges to connect isolated stations")
    
    # Check the result
    components = get_connected_components(G)
    print(f"\nAfter fixes, graph has {len(components)} connected components")
    
    # If we still have multiple components, connect them
    if len(components) > 1:
        print("Connecting remaining components...")
        sorted_components = sorted(components, key=len, reverse=True)
        main_component = sorted_components[0]
        main_station = next(iter(main_component))
        
        added_component_edges = 0
        for component in sorted_components[1:]:
            component_station = next(iter(component))
            G.add_edge(main_station, component_station, weight=20, fixed=True, transfer=True)
            G.add_edge(component_station, main_station, weight=20, fixed=True, transfer=True)
            added_component_edges += 2
            print(f"Connected component with {len(component)} stations to main component")
        
        print(f"Added {added_component_edges} edges to connect remaining components")
    
    return G

def save_graph_to_json(G, file_path):
    """
    Save the NetworkX graph to a JSON file in our custom format.
    
    Args:
        G: NetworkX graph object
        file_path: Path to save the JSON file
    """
    # Convert the graph to our custom format
    graph_data = {
        "nodes": {},
        "edges": []
    }
    
    # Add nodes
    for node, attrs in G.nodes(data=True):
        graph_data["nodes"][node] = attrs
    
    # Add edges
    for source, target, attrs in G.edges(data=True):
        edge = {
            "source": source,
            "target": target,
            **attrs
        }
        graph_data["edges"].append(edge)
    
    # Save to file
    with open(file_path, 'w') as f:
        import json
        json.dump(graph_data, f, indent=2)
    
    print(f"Graph saved to {file_path}")

def test_connectivity(G):
    """
    Test that the graph is fully connected by checking paths between major stations.
    
    Args:
        G: NetworkX graph object
    """
    # List of important station pairs to check
    station_pairs = [
        ("King's Cross St. Pancras Underground Station", "Waterloo Underground Station"),
        ("Paddington Underground Station", "Liverpool Street Underground Station"),
        ("Euston Underground Station", "Victoria Underground Station"),
        ("Bank Underground Station", "Oxford Circus Underground Station")
    ]
    
    # Find actual station names in the graph
    def find_matching_station(name):
        matches = [s for s in G.nodes() if name.lower() in s.lower()]
        return matches[0] if matches else None
    
    print("\nTesting connectivity between major stations:")
    all_connected = True
    
    for source, target in station_pairs:
        actual_source = find_matching_station(source)
        actual_target = find_matching_station(target)
        
        if not actual_source or not actual_target:
            print(f"❌ Could not find stations: {source} -> {target}")
            all_connected = False
            continue
        
        # Check if a path exists
        try:
            path = nx.shortest_path(G, actual_source, actual_target)
            print(f"✅ {actual_source} -> {actual_target}: {len(path)} stations")
        except nx.NetworkXNoPath:
            print(f"❌ No path found: {actual_source} -> {actual_target}")
            all_connected = False
    
    return all_connected

def main():
    """Main function to fix the graph connectivity."""
    print("Loading London transport network graph...")
    G = load_graph_from_json()
    
    # Analyze initial connectivity
    components = get_connected_components(G)
    print(f"\nBefore fixes, graph has {len(components)} connected components")
    print(f"Largest component has {max(len(c) for c in components)} stations")
    
    # Fix connectivity issues
    G_fixed = fix_connectivity_issues(G)
    
    # Check that the graph is now connected
    components = get_connected_components(G_fixed)
    print(f"\nAfter all fixes, graph has {len(components)} connected components")
    
    # Test connectivity between major stations
    success = test_connectivity(G_fixed)
    
    if success:
        print("\n✅ Graph is fully connected!")
    else:
        print("\n❌ Graph still has connectivity issues")
    
    # Save the fixed graph
    save_graph_to_json(G_fixed, FIXED_GRAPH_FILE)
    print(f"\nFixed graph saved to {FIXED_GRAPH_FILE}")
    print("Use this file instead of the original for proper pathfinding.")

if __name__ == "__main__":
    main() 