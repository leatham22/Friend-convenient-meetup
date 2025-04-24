#!/usr/bin/env python3
"""
Check Line Continuity

This script analyzes the network graph to identify any missing connections
along transport lines. It checks whether stations that should be sequentially
connected on the same line actually have edges between them.

Usage:
    python check_line_continuity.py [--line LINE_NAME]

Options:
    --line: Check a specific line only (e.g., bakerloo, district)
            If omitted, all lines will be checked

Output:
    Prints a report of missing connections within each line
"""

import json
import os
import argparse
from collections import defaultdict

# Define the relevant transport modes we care about
RELEVANT_MODES = ["tube", "dlr", "overground", "elizabeth-line"]

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

def get_line_stations(graph_data):
    """
    Get all stations on each line from node data.
    
    Args:
        graph_data (dict): The network graph data
        
    Returns:
        dict: Dictionary with line IDs as keys and lists of station names as values
    """
    line_stations = defaultdict(set)
    
    # Extract line information from node data
    for station_name, station_data in graph_data.get('nodes', {}).items():
        for line in station_data.get('lines', []):
            line_stations[line].add(station_name)
    
    return {line: list(stations) for line, stations in line_stations.items()}

def get_line_connections(graph_data):
    """
    Get all connections (edges) for each line.
    
    Args:
        graph_data (dict): The network graph data
        
    Returns:
        dict: Dictionary with line IDs as keys and sets of (source, target) pairs as values
    """
    line_connections = defaultdict(set)
    
    # Extract connection information from edge data
    for edge in graph_data.get('edges', []):
        # Skip transfer edges
        if edge.get('transfer', False) or edge.get('weight', 0) == 0:
            continue
        
        source = edge.get('source')
        target = edge.get('target')
        line = edge.get('line')
        mode = edge.get('mode', '')
        
        # Only consider connections for relevant modes
        if source and target and line and mode in RELEVANT_MODES:
            line_connections[line].add((source, target))
    
    return line_connections

def build_line_sequences(graph_data):
    """
    Build sequences of stations for each line by following connections.
    Takes into account branch lines by identifying branch points.
    
    Args:
        graph_data (dict): The network graph data
        
    Returns:
        dict: Dictionary with line IDs as keys and lists of ordered station sequences as values
    """
    # Get stations on each line
    line_stations = get_line_stations(graph_data)
    
    # Get connections on each line
    line_connections = get_line_connections(graph_data)
    
    line_sequences = {}
    
    # For each line, build sequences
    for line, stations in line_stations.items():
        if line not in line_connections:
            continue
        
        connections = line_connections[line]
        
        # Build adjacency list
        adjacency = defaultdict(set)
        for source, target in connections:
            adjacency[source].add(target)
            adjacency[target].add(source)  # Graph is bidirectional
        
        # Identify branch points (stations with more than 2 connections)
        branch_points = {station for station in adjacency if len(adjacency[station]) > 2}
        
        # Find endpoints (stations with only one connection)
        endpoints = [station for station in stations if station in adjacency and len(adjacency[station]) == 1]
        
        # If no endpoints found, use branch points as starting points
        starting_points = endpoints if endpoints else (list(branch_points) if branch_points else list(adjacency.keys())[:1])
        
        sequences = []
        visited = set()
        
        # Process each branch from each starting point
        for start in starting_points:
            if start in visited and not branch_points:
                continue
                
            # For branch points, we need to explore all possible branches
            if start in branch_points:
                # Get all neighbors that haven't been fully explored
                neighbors = [n for n in adjacency[start] if (start, n) not in visited and (n, start) not in visited]
                
                # If all neighbors have been visited, skip
                if not neighbors:
                    continue
                
                # Create a sequence for each branch
                for neighbor in neighbors:
                    # Mark this connection as visited
                    visited.add((start, neighbor))
                    visited.add((neighbor, start))
                    
                    # Start a new sequence from this branch
                    sequence = [start, neighbor]
                    current = neighbor
                    
                    # Follow the branch until we hit a branch point or endpoint
                    while current not in branch_points and len(adjacency[current]) == 2:
                        # Get the next station (not the one we came from)
                        next_stations = [s for s in adjacency[current] if s != sequence[-2]]
                        
                        if not next_stations:
                            break
                            
                        next_station = next_stations[0]
                        
                        # Mark this connection as visited
                        visited.add((current, next_station))
                        visited.add((next_station, current))
                        
                        sequence.append(next_station)
                        current = next_station
                    
                    if len(sequence) > 2:
                        sequences.append(sequence)
            else:
                # For regular starting points, just follow the path
                sequence = [start]
                visited.add(start)
                
                # Follow connections to build sequence
                current = start
                while True:
                    # Get all unvisited neighbors
                    next_stations = [s for s in adjacency[current] if s not in sequence]
                    
                    if not next_stations:
                        break
                        
                    next_station = next_stations[0]
                    sequence.append(next_station)
                    
                    # If we hit a branch point, stop
                    if next_station in branch_points:
                        break
                        
                    current = next_station
                
                if len(sequence) > 1:
                    sequences.append(sequence)
        
        # Check if we missed any significant portion of the line
        all_visited = set()
        for seq in sequences:
            all_visited.update(seq)
            
        missed_stations = [s for s in stations if s in adjacency and s not in all_visited]
        
        # If we missed stations, try to find additional sequences
        if missed_stations and missed_stations[0] in adjacency:
            start = missed_stations[0]
            sequence = [start]
            
            current = start
            while True:
                next_stations = [s for s in adjacency[current] if s not in sequence]
                if not next_stations:
                    break
                    
                next_station = next_stations[0]
                sequence.append(next_station)
                
                # If we hit a branch point, stop
                if next_station in branch_points:
                    break
                    
                current = next_station
            
            if len(sequence) > 1:
                sequences.append(sequence)
        
        line_sequences[line] = sequences
    
    return line_sequences

def check_line_continuity(graph_data, target_line=None):
    """
    Check for missing connections within each line sequence, accounting for branches.
    
    Args:
        graph_data (dict): The network graph data
        target_line (str, optional): Specific line to check
        
    Returns:
        dict: Dictionary with line IDs as keys and lists of missing connections as values
    """
    # Build line sequences
    line_sequences = build_line_sequences(graph_data)
    
    # Get all connections
    line_connections = get_line_connections(graph_data)
    
    # Track missing connections
    missing_connections = defaultdict(list)
    
    # Process each line
    for line, sequences in line_sequences.items():
        # Skip if we're looking for a specific line and this isn't it
        if target_line and line != target_line:
            continue
            
        # Skip if there are no sequences
        if not sequences:
            continue
            
        # Get the connections for this line
        connections = line_connections.get(line, set())
        
        # Keep track of existing connections for this line
        existing_connections = set()
        for source, target in connections:
            existing_connections.add((source, target))
            existing_connections.add((target, source))  # Add both directions
        
        # Track missing connections for this line
        line_missing = []
        
        # Check each sequence
        for sequence in sequences:
            # Check pairs of adjacent stations in the sequence
            for i in range(len(sequence) - 1):
                source = sequence[i]
                target = sequence[i + 1]
                
                # Check if this connection exists
                if (source, target) not in existing_connections and (target, source) not in existing_connections:
                    # If both stations are on the same line, this should be a direct connection
                    # But first verify they're not part of a branch point
                    line_missing.append((source, target))
        
        # Add missing connections to the result
        if line_missing:
            # Remove potential false positives at branch points
            # Get line adjacency list to identify branch points
            adjacency = defaultdict(set)
            for source, target in connections:
                adjacency[source].add(target)
                adjacency[target].add(source)
            
            # Identify branch points (stations with more than 2 connections)
            branch_points = {station for station in adjacency if len(adjacency[station]) > 2}
            
            # Filter out potential false positives at branch points
            filtered_missing = []
            for source, target in line_missing:
                # Keep the connection as missing if neither station is a branch point
                if source not in branch_points and target not in branch_points:
                    filtered_missing.append((source, target))
            
            missing_connections[line] = filtered_missing
    
    return missing_connections

def is_relevant_line(graph_data, line_id):
    """
    Check if a line is relevant for our analysis.
    
    Args:
        graph_data (dict): The network graph data
        line_id (str): Line ID to check
        
    Returns:
        bool: True if the line is relevant, False otherwise
    """
    # Extract mode information from a single edge using this line
    for edge in graph_data.get('edges', []):
        if edge.get('line') == line_id:
            return edge.get('mode', '') in RELEVANT_MODES
    return False

def get_official_line_name(graph_data, line_id):
    """
    Get the official name of a line from the graph data.
    
    Args:
        graph_data (dict): The network graph data
        line_id (str): Line ID
        
    Returns:
        str: Official line name or the ID if not found
    """
    # Look for line name in edge data
    for edge in graph_data.get('edges', []):
        if edge.get('line') == line_id and 'line_name' in edge:
            return edge.get('line_name')
    return line_id

def check_station_on_line(graph_data, station_name, line_id):
    """
    Check if a station is on a specific line.
    
    Args:
        graph_data (dict): The network graph data
        station_name (str): Station to check
        line_id (str): Line to check
        
    Returns:
        bool: True if the station is on the line, False otherwise
    """
    station_data = graph_data.get('nodes', {}).get(station_name, {})
    return line_id in station_data.get('lines', [])

def check_missing_edges_for_all_lines(graph_data):
    """
    Check for missing connections on all lines with auto branch detection.
    
    Args:
        graph_data (dict): The network graph data
        
    Returns:
        dict: Missing connections by line ID
    """
    # Get missing connections for all lines
    missing_connections = check_line_continuity(graph_data)
    
    line_missing_counts = {}
    total_missing = 0
    
    print("\nMissing edges on overlapping lines:\n")
    
    # Process each line
    for line_id, connections in missing_connections.items():
        # Skip if no missing connections or not a relevant line
        if not connections or not is_relevant_line(graph_data, line_id):
            continue
            
        # Get official line name
        line_name = get_official_line_name(graph_data, line_id)
        
        # Count missing connections
        count = len(connections)
        line_missing_counts[line_id] = count
        total_missing += count
        
        print(f"{line_name} ({line_id}): {count} missing connections")
        
        # Print each missing connection
        for source, target in connections:
            print(f"  {source} → {target}")
        
        print()
    
    print(f"Total missing cross-line connections: {total_missing}")
    
    return missing_connections

def find_cross_line_connections(graph_data):
    """
    Find stations where lines overlap and check if there are connections
    between sequential stations on the same line.
    
    Args:
        graph_data (dict): The network graph data
        
    Returns:
        dict: Dictionary of missing connections by line
    """
    return check_missing_edges_for_all_lines(graph_data)

def main():
    """Main function to run the script"""
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Check line continuity in the transport network")
    parser.add_argument('--line', type=str, help="Check a specific line only (e.g., bakerloo, district)")
    
    # Parse arguments
    args = parser.parse_args()
    
    # File path for the graph data
    script_dir = os.path.dirname(os.path.abspath(__file__))
    graph_file = os.path.join(script_dir, 'networkx_graph_new.json')
    
    print(f"Loading graph data from {graph_file}...")
    
    # Load graph data
    graph_data = load_graph_data(graph_file)
    
    if args.line:
        # Check a specific line
        missing = check_line_continuity(graph_data, args.line)
        
        if args.line in missing and missing[args.line]:
            line_name = get_official_line_name(graph_data, args.line)
            print(f"\nMissing connections on {line_name} ({args.line}):")
            
            for source, target in missing[args.line]:
                print(f"  {source} → {target}")
                
            print(f"\nTotal: {len(missing[args.line])} missing connections")
        else:
            print(f"\nNo missing connections found on the specified line")
    else:
        # Check all lines
        find_cross_line_connections(graph_data)

if __name__ == "__main__":
    main() 