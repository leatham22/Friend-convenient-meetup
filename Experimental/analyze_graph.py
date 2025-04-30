#!/usr/bin/env python3
"""
Analyze Graph

This script analyzes the network graph to identify stations connected by multiple lines.
It checks for duplicate edges and verifies our graph structure is correct.
"""

import json
import os
from collections import defaultdict

def load_graph_data(file_path):
    """
    Load the network graph data from a JSON file.
    
    Args:
        file_path (str): Path to the graph JSON file
        
    Returns:
        dict: The loaded graph data
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def analyze_connections(graph_data):
    """
    Analyze connections to find station pairs served by multiple lines.
    
    Args:
        graph_data (dict): The network graph data
        
    Returns:
        dict: Dictionary with station pairs as keys and lists of serving lines as values
    """
    # Dictionary to track connections
    connections = defaultdict(list)
    
    # Count transfer and non-transfer edges
    transfer_count = 0
    normal_count = 0
    
    # Process each edge
    for edge in graph_data.get('edges', []):
        source = edge.get('source')
        target = edge.get('target')
        line = edge.get('line', '')
        is_transfer = edge.get('transfer', False) or edge.get('weight', 1) == 0
        
        # Skip edges without source or target
        if not source or not target:
            continue
        
        # Track if this is a transfer edge
        if is_transfer:
            transfer_count += 1
        else:
            normal_count += 1
            
            # Add this line to the connection
            connection_key = (source, target)
            if line and line not in connections[connection_key]:
                connections[connection_key].append(line)
    
    # Find connections with multiple lines
    multi_line_connections = {k: v for k, v in connections.items() if len(v) > 1}
    
    return connections, multi_line_connections, transfer_count, normal_count

def identify_missing_line_edges(graph_data, connections):
    """
    Identify station pairs that should have multiple lines but only have one.
    
    Args:
        graph_data (dict): The network graph data
        connections (dict): Dictionary of station pairs and their lines
        
    Returns:
        dict: Dictionary of potentially missing line connections
    """
    # Build a map of stations to their lines
    station_lines = defaultdict(set)
    
    # Extract lines for each station from node data
    for station_name, station_data in graph_data.get('nodes', {}).items():
        for line in station_data.get('lines', []):
            station_lines[station_name].add(line)
    
    # Check each connection to see if it should have more lines
    potential_missing = defaultdict(list)
    
    for (station1, station2), lines in connections.items():
        # Find common lines between these stations
        common_lines = station_lines[station1].intersection(station_lines[station2])
        
        # Check if there are lines that should connect these stations but don't
        missing_lines = common_lines - set(lines)
        if missing_lines:
            potential_missing[(station1, station2)] = list(missing_lines)
    
    return potential_missing

def main():
    """Main function to analyze the graph"""
    # File path relative to the script's location
    graph_file = os.path.join("..", "graph_data", "networkx_graph_new.json")
    
    print(f"Loading graph data from {graph_file}...")
    graph_data = load_graph_data(graph_file)
    
    # Analyze connections
    connections, multi_line_connections, transfer_count, normal_count = analyze_connections(graph_data)
    
    # Print summary
    print(f"\nGraph analysis:")
    print(f"Total nodes: {len(graph_data.get('nodes', {}))}")
    print(f"Total edges: {len(graph_data.get('edges', []))}")
    print(f"  - Transfer edges: {transfer_count}")
    print(f"  - Normal edges: {normal_count}")
    print(f"  - Unique station pairs: {len(connections)}")
    
    # Print multi-line connections
    print(f"\nConnections with multiple lines: {len(multi_line_connections)}")
    if multi_line_connections:
        print("\nSample of multi-line connections:")
        for i, (stations, lines) in enumerate(list(multi_line_connections.items())[:10]):
            source, target = stations
            print(f"{i+1}. {source} → {target}: {', '.join(lines)}")
    
    # Identify potentially missing line edges
    potential_missing = identify_missing_line_edges(graph_data, connections)
    
    # Print potentially missing line edges
    print(f"\nStation pairs that should have additional line connections: {len(potential_missing)}")
    if potential_missing:
        print("\nSample of potentially missing line edges:")
        for i, ((station1, station2), missing_lines) in enumerate(list(potential_missing.items())[:20]):
            existing_lines = connections[(station1, station2)]
            print(f"{i+1}. {station1} → {station2}")
            print(f"   Current lines: {', '.join(existing_lines)}")
            print(f"   Missing lines: {', '.join(missing_lines)}")
    
    # Check for stations with the most shared lines
    stations_with_shared_lines = []
    for station1 in graph_data.get('nodes', {}):
        for station2 in graph_data.get('nodes', {}):
            if station1 != station2:
                common_lines = set(graph_data['nodes'][station1].get('lines', [])) & set(graph_data['nodes'][station2].get('lines', []))
                if len(common_lines) > 1:
                    stations_with_shared_lines.append((station1, station2, list(common_lines)))
    
    # Sort by number of shared lines
    stations_with_shared_lines.sort(key=lambda x: len(x[2]), reverse=True)
    
    # Print top stations with shared lines
    print("\nTop station pairs with multiple common lines:")
    for i, (station1, station2, common_lines) in enumerate(stations_with_shared_lines[:10]):
        print(f"{i+1}. {station1} and {station2}: {len(common_lines)} shared lines")
        print(f"   Lines: {', '.join(common_lines)}")
            
if __name__ == "__main__":
    main() 