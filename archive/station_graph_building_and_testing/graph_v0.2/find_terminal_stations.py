#!/usr/bin/env python3
"""
Find Terminal Stations

This script analyzes the network graph data to identify terminal stations 
for each Tube and DLR line. A station is considered a terminal for a specific 
line if it has only one non-transfer connection on that line.

Usage:
    python3 find_terminal_stations.py

Output:
    Creates terminal_stations.json in the network_data directory, mapping 
    line IDs to a list of their terminal station IDs (Naptan IDs).
"""

import json
import os
from collections import defaultdict

# Define the modes we are interested in (Tube and DLR)
TARGET_MODES = {"tube", "dlr"}

def load_graph_data(file_path):
    """
    Load the network graph data from a JSON file.
    
    Args:
        file_path (str): Path to the graph JSON file
        
    Returns:
        dict: The loaded graph data, or None if loading fails.
    """
    # Check if the file exists
    if not os.path.exists(file_path):
        print(f"Error: Graph file not found at {file_path}")
        return None
        
    # Load the JSON file
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {file_path}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading {file_path}: {e}")
        return None

def find_terminals(graph_data):
    """
    Identifies terminal stations for each relevant line.
    
    Args:
        graph_data (dict): The network graph data.
        
    Returns:
        dict: A dictionary mapping line IDs to a list of terminal station IDs.
              Returns None if input data is invalid.
    """
    # Validate input data structure
    if not graph_data or 'nodes' not in graph_data or 'edges' not in graph_data:
        print("Error: Invalid graph data structure.")
        return None
        
    nodes = graph_data['nodes']
    edges = graph_data['edges']
    
    # Dictionary to store unique neighbors for each station on each of its lines
    # Format: station_neighbors[station_name][line_id] = {neighbor1_name, neighbor2_name, ...}
    station_neighbors = defaultdict(lambda: defaultdict(set))
    
    # Dictionary to map station names to their Naptan IDs
    station_name_to_id = {name: data.get('id') for name, data in nodes.items() if data.get('id')} # Ensure node has an ID
    
    # Iterate through edges to identify unique neighbors per station per line
    for edge in edges:
        source_name = edge.get('source')
        target_name = edge.get('target')
        line_id = edge.get('line')
        mode = edge.get('mode')
        is_transfer = edge.get('transfer', False) or edge.get('weight', 0) == 0

        # Skip if essential data is missing, it's a transfer, or not a target mode
        if not source_name or not target_name or not line_id or not mode or is_transfer or mode not in TARGET_MODES:
            continue
            
        # Add the neighbor to the set for this station and line
        # Sets automatically handle uniqueness
        station_neighbors[source_name][line_id].add(target_name)
        station_neighbors[target_name][line_id].add(source_name)
        
    # Dictionary to store terminal stations per line
    # Format: terminals_by_line[line_id] = [station_id1, station_id2, ...]
    terminals_by_line = defaultdict(list)
    
    # Identify terminals by checking neighbor counts
    for station_name, lines_data in station_neighbors.items():
        station_node = nodes.get(station_name)
        station_id = station_name_to_id.get(station_name)
        
        # Ensure the station and its ID exist and it belongs to a target mode
        if not station_node or not station_id or not any(mode in TARGET_MODES for mode in station_node.get('modes', [])):
            continue
            
        # Check each line the station is part of
        for line_id, neighbors in lines_data.items():
            # Check if the line itself is a target mode line (e.g. exclude bus lines appearing on tube station nodes)
            # This check ensures we only consider lines that actually have Tube/DLR segments involving this station
            is_target_line = any(edge.get('mode') in TARGET_MODES for edge in edges if edge.get('line') == line_id and (edge.get('source') == station_name or edge.get('target') == station_name))

            # A terminal station will have exactly one unique neighbor on that specific line
            if is_target_line and len(neighbors) == 1:
                # Ensure we don't add the same station ID multiple times if it's a terminal on different conceptual "lines" that merge (though unlikely with current data)
                if station_id not in terminals_by_line[line_id]:
                     terminals_by_line[line_id].append(station_id)
                     
    # Sort the station IDs within each line for consistency
    for line_id in terminals_by_line:
        terminals_by_line[line_id].sort()

    return dict(terminals_by_line)

def main():
    """Main function to find and save terminal stations."""
    # Determine file paths relative to the script location
    OUTPUT_DIR = "../graph_data" 
    graph_file = os.path.join(OUTPUT_DIR, 'networkx_graph_new.json')
    output_file = os.path.join(OUTPUT_DIR, 'terminal_stations.json')
    
    print(f"Loading graph data from {graph_file}...")
    graph_data = load_graph_data(graph_file)
    
    if graph_data is None:
        print("Failed to load graph data. Exiting.")
        return # Exit if graph data loading failed

    print("Finding terminal stations for Tube and DLR lines...")
    terminals = find_terminals(graph_data)
    
    if terminals is None:
        print("Failed to find terminals due to invalid graph data. Exiting.")
        return # Exit if terminal finding failed
        
    # Print summary
    print(f"Identified terminals for {len(terminals)} lines:")
    for line_id, stations in sorted(terminals.items()):
        print(f"  Line: {line_id}, Terminals: {len(stations)}") # Print count and list of terminals
        # Optionally print the station IDs themselves if needed for debugging
        # print(f"    {stations}") 

    print(f"Saving terminal stations to {output_file}...")
    # Save the results to the output JSON file
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(terminals, file, indent=2, sort_keys=True) # Sort keys for consistency
        print("Successfully saved terminal stations.")
    except IOError as e:
        print(f"Error saving file {output_file}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while saving the file: {e}")

if __name__ == "__main__":
    # This ensures the main function runs when the script is executed
    main() 