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
        
        # Find sequence starting points (stations with only one connection)
        endpoints = [station for station in stations if station in adjacency and len(adjacency[station]) == 1]
        
        # If no endpoints found, use any station as starting point
        starting_points = endpoints if endpoints else (list(adjacency.keys()) if adjacency else [])
        
        sequences = []
        visited = set()
        
        # Start from each endpoint and build sequences
        for start in starting_points:
            if start in visited:
                continue
                
            sequence = [start]
            visited.add(start)
            
            # Follow connections to build sequence
            current = start
            while True:
                next_stations = [s for s in adjacency[current] if s not in visited]
                if not next_stations:
                    break
                    
                next_station = next_stations[0]
                sequence.append(next_station)
                visited.add(next_station)
                current = next_station
            
            if len(sequence) > 1:
                sequences.append(sequence)
        
        # Handle any remaining stations (for complex networks with loops)
        remaining = [s for s in stations if s in adjacency and s not in visited]
        if remaining:
            start = remaining[0]
            sequence = [start]
            visited.add(start)
            
            # Follow connections to build sequence
            current = start
            while True:
                next_stations = [s for s in adjacency[current] if s not in visited]
                if not next_stations:
                    break
                    
                next_station = next_stations[0]
                sequence.append(next_station)
                visited.add(next_station)
                current = next_station
            
            if len(sequence) > 1:
                sequences.append(sequence)
        
        line_sequences[line] = sequences
    
    return line_sequences

def check_line_continuity(graph_data, target_line=None):
    """
    Check for missing connections within each line sequence.
    
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
    
    # Extract line branch information from edge data if available
    line_branches = defaultdict(lambda: defaultdict(set))
    
    for edge in graph_data.get('edges', []):
        # Skip transfer edges
        if edge.get('transfer', False) or edge.get('weight', 0) == 0:
            continue
        
        source = edge.get('source')
        target = edge.get('target')
        line = edge.get('line', '')
        branch = edge.get('branch', '')
        
        # Store branch information if available
        if source and target and line and branch:
            line_branches[line][branch].add(source)
            line_branches[line][branch].add(target)
    
    # Track missing connections
    missing_connections = defaultdict(list)
    
    # Define known branched lines to prevent false positives
    branched_lines = {
        "northern": [
            # Bank branch
            ["Bank Underground Station", "London Bridge Underground Station", "Borough Underground Station", 
             "Elephant & Castle Underground Station"],
            # Charing Cross branch
            ["Charing Cross Underground Station", "Embankment Underground Station", "Waterloo Underground Station", 
             "Kennington Underground Station"]
        ],
        "district": [
            # Richmond branch
            ["Turnham Green Underground Station", "Gunnersbury Underground Station", "Kew Gardens Underground Station", 
             "Richmond Underground Station"],
            # Ealing branch  
            ["Acton Town Underground Station", "Ealing Common Underground Station", "Ealing Broadway Underground Station"],
            # Wimbledon branch
            ["Earl's Court Underground Station", "West Brompton Underground Station", "Fulham Broadway Underground Station", 
             "Parsons Green Underground Station", "Putney Bridge Underground Station", "East Putney Underground Station", 
             "Southfields Underground Station", "Wimbledon Park Underground Station", "Wimbledon Underground Station"],
            # Main line East
            ["Earl's Court Underground Station", "High Street Kensington Underground Station", "Notting Hill Gate Underground Station",
             "Bayswater Underground Station", "Paddington Underground Station"],
            # Main line West
            ["Earl's Court Underground Station", "Gloucester Road Underground Station", "South Kensington Underground Station", 
             "Sloane Square Underground Station", "Victoria Underground Station", "St. James's Park Underground Station", 
             "Westminster Underground Station", "Embankment Underground Station", "Temple Underground Station", 
             "Blackfriars Underground Station", "Mansion House Underground Station", "Cannon Street Underground Station", 
             "Monument Underground Station", "Tower Hill Underground Station", "Aldgate East Underground Station", 
             "Whitechapel Underground Station", "Stepney Green Underground Station", "Mile End Underground Station", 
             "Bow Road Underground Station", "Bromley-by-Bow Underground Station", "West Ham Underground Station", 
             "Plaistow Underground Station", "Upton Park Underground Station", "East Ham Underground Station", 
             "Barking Underground Station", "Upney Underground Station", "Becontree Underground Station", 
             "Dagenham Heathway Underground Station", "Dagenham East Underground Station", "Elm Park Underground Station", 
             "Hornchurch Underground Station", "Upminster Bridge Underground Station", "Upminster Underground Station"],
            # Hammersmith & City connection
            ["Hammersmith (Dist&Picc Line) Underground Station", "Barons Court Underground Station", 
             "West Kensington Underground Station", "Earl's Court Underground Station"],
            # Piccadilly connection
            ["Acton Town Underground Station", "Turnham Green Underground Station", 
             "Hammersmith (Dist&Picc Line) Underground Station", "Barons Court Underground Station"]
        ],
        "jubilee": [
            # North West section
            ["Stanmore Underground Station", "Canons Park Underground Station", "Queensbury Underground Station", 
             "Kingsbury Underground Station", "Wembley Park Underground Station"],
            # Middle section  
            ["Wembley Park Underground Station", "Neasden Underground Station", "Dollis Hill Underground Station", 
             "Willesden Green Underground Station", "Kilburn Underground Station", "West Hampstead Underground Station", 
             "Finchley Road Underground Station"],
            # South section
            ["Finchley Road Underground Station", "Swiss Cottage Underground Station", "St. John's Wood Underground Station", 
             "Baker Street Underground Station", "Bond Street Underground Station", "Green Park Underground Station", 
             "Westminster Underground Station", "Waterloo Underground Station", "Southwark Underground Station", 
             "London Bridge Underground Station", "Bermondsey Underground Station", "Canada Water Underground Station", 
             "Canary Wharf Underground Station", "North Greenwich Underground Station", "Canning Town Underground Station", 
             "West Ham Underground Station", "Stratford Underground Station"]
        ]
    }
    
    # Supplement known branch information with API branch data if available
    for line_id, branches in line_branches.items():
        if line_id not in branched_lines:
            branched_lines[line_id] = []
            # For each branch found in the API, add it as a branch in our known data
            for branch_id, stations in branches.items():
                if len(stations) > 1:  # Only add branches with multiple stations
                    branched_lines[line_id].append(list(stations))
    
    # Create a lookup dictionary to check if two stations are on the same branch
    station_to_branch = {}
    for line, branches in branched_lines.items():
        for branch_idx, branch in enumerate(branches):
            for station in branch:
                if station not in station_to_branch:
                    station_to_branch[station] = {}
                if line not in station_to_branch[station]:
                    station_to_branch[station][line] = []
                station_to_branch[station][line].append(branch_idx)
    
    # Process only the target line if specified
    lines_to_check = [target_line] if target_line else line_sequences.keys()
    
    # Check each line
    for line in lines_to_check:
        if line not in line_sequences:
            print(f"Line '{line}' not found in the graph")
            continue
        
        # Only check lines for relevant transport modes
        if not is_relevant_line(graph_data, line):
            continue
            
        connections = line_connections.get(line, set())
        
        # Check each sequence in the line
        for sequence in line_sequences[line]:
            # Check each pair of consecutive stations
            for i in range(len(sequence) - 1):
                station1 = sequence[i]
                station2 = sequence[i+1]
                
                # Check if connection exists
                if (station1, station2) not in connections and (station2, station1) not in connections:
                    # Skip known branch connections for branched lines
                    if line in branched_lines:
                        # Skip if either station isn't in our branch data
                        if (station1 not in station_to_branch or
                            station2 not in station_to_branch or
                            line not in station_to_branch.get(station1, {}) or
                            line not in station_to_branch.get(station2, {})):
                            # Still report if this is part of a sequence
                            pass
                        else:
                            # Check if they should be on the same branch
                            station1_branches = station_to_branch[station1][line]
                            station2_branches = station_to_branch[station2][line]
                            
                            # If no common branches and not consecutive in any branch, skip
                            common_branches = [b for b in station1_branches if b in station2_branches]
                            
                            if not common_branches:
                                is_branch_consecutive = False
                                for branch_idx in set(station1_branches + station2_branches):
                                    branch = branched_lines[line][branch_idx]
                                    if station1 in branch and station2 in branch:
                                        s1_idx = branch.index(station1)
                                        s2_idx = branch.index(station2)
                                        if abs(s1_idx - s2_idx) == 1:
                                            is_branch_consecutive = True
                                            break
                                
                                if not is_branch_consecutive:
                                    continue
                                
                    # Check if there's a direct connection on any other line
                    # If they're connected on another line, it's more likely this connection is valid
                    direct_connection_exists = False
                    for other_line, other_connections in line_connections.items():
                        if other_line != line:
                            if (station1, station2) in other_connections or (station2, station1) in other_connections:
                                direct_connection_exists = True
                                break
                    
                    if direct_connection_exists or (line in branched_lines):
                        missing_connections[line].append((station1, station2))
    
    return missing_connections

def is_relevant_line(graph_data, line_id):
    """
    Check if a line belongs to one of the relevant transport modes we care about.
    
    Args:
        graph_data (dict): The network graph data
        line_id (str): The line ID to check
        
    Returns:
        bool: True if the line is relevant, False otherwise
    """
    # Find an edge with this line to get its mode
    for edge in graph_data.get('edges', []):
        if edge.get('line') == line_id:
            mode = edge.get('mode', '')
            return mode in RELEVANT_MODES
    
    return False

def get_official_line_name(graph_data, line_id):
    """
    Get the official name of a line from its ID.
    
    Args:
        graph_data (dict): The network graph data
        line_id (str): Line ID to look up
        
    Returns:
        str: Official line name or line ID if not found
    """
    # Find an edge with this line to get its official name
    for edge in graph_data.get('edges', []):
        if edge.get('line') == line_id and edge.get('line_name'):
            return edge.get('line_name')
    
    return line_id

def check_station_on_line(graph_data, station_name, line_id):
    """
    Check if a station should be on a specific line.
    
    Args:
        graph_data (dict): The network graph data
        station_name (str): Station name to check
        line_id (str): Line ID to check
        
    Returns:
        bool: True if station should be on the line, False otherwise
    """
    station_data = graph_data.get('nodes', {}).get(station_name, {})
    return line_id in station_data.get('lines', [])

def check_missing_edges_for_all_lines(graph_data):
    """
    Check for missing edges on all lines by analyzing the node data.
    
    This approach examines which stations should be connected based on line information
    in the node data, rather than relying on pre-defined sequences.
    
    Args:
        graph_data (dict): The network graph data
        
    Returns:
        dict: Dictionary with line IDs as keys and lists of potential missing connections
    """
    missing_connections = defaultdict(list)
    line_connections = get_line_connections(graph_data)
    
    # Load the TFL line data if available
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tfl_data_path = os.path.join(script_dir, 'tfl_line_data.json')
    
    # Get stations by line
    lines_with_stations = defaultdict(dict)
    
    # Extract stations on each line from node data
    for station_name, station_data in graph_data.get('nodes', {}).items():
        for line in station_data.get('lines', []):
            station_id = station_data.get('id', '')
            if station_id:
                lines_with_stations[line][station_name] = station_id
    
    # Go through each pair of stations on the same line
    for line, stations in lines_with_stations.items():
        # Only check lines for relevant transport modes
        if not is_relevant_line(graph_data, line):
            continue
            
        # Skip lines with less than 2 stations
        if len(stations) < 2:
            continue
            
        # Get existing connections for this line
        existing_connections = line_connections.get(line, set())
        
        # Check station pairs
        station_names = list(stations.keys())
        
        # For each station, check adjacency with other stations on the line
        for i, station1 in enumerate(station_names):
            for j, station2 in enumerate(station_names):
                if i == j:  # Skip same station
                    continue
                    
                # Check if stations are connected by an edge for this line
                if ((station1, station2) not in existing_connections and 
                    (station2, station1) not in existing_connections):
                    
                    # Check if this pair is directly connected by any edge
                    direct_connection = False
                    for edge_line, connections in line_connections.items():
                        if (station1, station2) in connections or (station2, station1) in connections:
                            direct_connection = True
                            break
                    
                    # If stations are directly connected by another line's edge,
                    # this indicates they should be connected for this line too
                    if direct_connection:
                        # Add as potential missing connection
                        missing_connections[line].append((station1, station2))
    
    # Remove duplicates
    for line in missing_connections:
        unique_pairs = set()
        filtered_connections = []
        
        for station1, station2 in missing_connections[line]:
            # Create a frozenset to handle bidirectional uniqueness
            pair = frozenset([station1, station2])
            if pair not in unique_pairs:
                unique_pairs.add(pair)
                filtered_connections.append((station1, station2))
        
        missing_connections[line] = filtered_connections
    
    return missing_connections

def check_real_world_connections(graph_data):
    """
    Check for existing connections in TfL data against the graph.
    
    Instead of using hardcoded connections, this function analyzes the TfL data
    to identify connections that should exist based on the API data itself.
    
    Args:
        graph_data (dict): The network graph data
        
    Returns:
        list: List of missing connections found in TfL data
    """
    missing_real_world = []
    
    # Get all connections
    line_connections = get_line_connections(graph_data)
    
    # Load the TFL line data if available
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tfl_data_path = os.path.join(script_dir, 'tfl_line_data.json')
    
    try:
        with open(tfl_data_path, 'r') as f:
            tfl_data = json.load(f)
            
            # Process each line's data
            for line_id, line_data in tfl_data.items():
                # Extract station sequences from stopPointSequences
                stop_point_sequences = line_data.get('stopPointSequences', [])
                
                if stop_point_sequences:
                    for sequence in stop_point_sequences:
                        stop_points = sequence.get('stopPoint', [])
                        
                        # Check consecutive stations in each sequence
                        for i in range(len(stop_points) - 1):
                            station1 = stop_points[i].get('name', '')
                            station2 = stop_points[i + 1].get('name', '')
                            
                            # Skip if either station name is missing
                            if not station1 or not station2:
                                continue
                            
                            # Check if both stations exist and are on this line
                            if (not check_station_on_line(graph_data, station1, line_id) or 
                                not check_station_on_line(graph_data, station2, line_id)):
                                continue
                            
                            # Check if connection exists in our graph
                            if (station1, station2) not in line_connections.get(line_id, set()) and \
                               (station2, station1) not in line_connections.get(line_id, set()):
                                missing_real_world.append((line_id, station1, station2))
                
                # If no stopPointSequences, try orderedLineRoutes
                if not stop_point_sequences:
                    ordered_routes = line_data.get('orderedLineRoutes', [])
                    
                    if ordered_routes:
                        for route in ordered_routes:
                            naptan_ids = route.get('naptanIds', [])
                            
                            # We need to map NaptanIds to station names
                            station_names = []
                            for naptan_id in naptan_ids:
                                # Find the station name for this ID
                                for name, data in graph_data.get('nodes', {}).items():
                                    if data.get('id') == naptan_id:
                                        station_names.append(name)
                                        break
                            
                            # Check consecutive stations in the route
                            for i in range(len(station_names) - 1):
                                station1 = station_names[i]
                                station2 = station_names[i + 1]
                                
                                # Skip if we couldn't map an ID to a name
                                if not station1 or not station2:
                                    continue
                                
                                # Check if connection exists in our graph
                                if (station1, station2) not in line_connections.get(line_id, set()) and \
                                   (station2, station1) not in line_connections.get(line_id, set()):
                                    missing_real_world.append((line_id, station1, station2))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not analyze TfL data from {tfl_data_path}: {e}")
    
    return missing_real_world

def find_cross_line_connections(graph_data):
    """
    Find where edges exist between stations but are missing on some overlapping lines.
    
    This function identifies cases where two stations are connected by an edge on one line,
    but lack an edge on another line they both serve, accounting for branched lines.
    
    Args:
        graph_data (dict): The network graph data
        
    Returns:
        dict: Dictionary with line IDs as keys and missing connections as values
    """
    # Get all connections (regardless of line)
    all_connections = set()
    line_connections = defaultdict(set)
    
    # Extract line branch information from edge data if available
    line_branches = defaultdict(lambda: defaultdict(set))
    
    for edge in graph_data.get('edges', []):
        # Skip transfer edges
        if edge.get('transfer', False) or edge.get('weight', 0) == 0:
            continue
        
        source = edge.get('source')
        target = edge.get('target')
        line = edge.get('line', '')
        mode = edge.get('mode', '')
        branch = edge.get('branch', '')
        
        # Only consider connections for relevant modes
        if source and target and mode in RELEVANT_MODES:
            # Add to all connections
            all_connections.add(frozenset([source, target]))
            
            # Add to line connections
            if line:
                line_connections[line].add(frozenset([source, target]))
                
                # If we have branch information, store it
                if branch:
                    line_branches[line][branch].add(source)
                    line_branches[line][branch].add(target)
    
    # Get stations by line
    line_stations = defaultdict(set)
    
    for station_name, station_data in graph_data.get('nodes', {}).items():
        for line in station_data.get('lines', []):
            line_stations[line].add(station_name)
    
    # Define known branched lines to prevent false positives
    branched_lines = {
        "northern": [
            # Bank branch
            ["Bank Underground Station", "London Bridge Underground Station", "Borough Underground Station", 
             "Elephant & Castle Underground Station"],
            # Charing Cross branch
            ["Charing Cross Underground Station", "Embankment Underground Station", "Waterloo Underground Station", 
             "Kennington Underground Station"]
        ],
        "district": [
            # Richmond branch
            ["Turnham Green Underground Station", "Gunnersbury Underground Station", "Kew Gardens Underground Station", 
             "Richmond Underground Station"],
            # Ealing branch  
            ["Acton Town Underground Station", "Ealing Common Underground Station", "Ealing Broadway Underground Station"],
            # Wimbledon branch
            ["Earl's Court Underground Station", "West Brompton Underground Station", "Fulham Broadway Underground Station", 
             "Parsons Green Underground Station", "Putney Bridge Underground Station", "East Putney Underground Station", 
             "Southfields Underground Station", "Wimbledon Park Underground Station", "Wimbledon Underground Station"],
            # Main line East
            ["Earl's Court Underground Station", "High Street Kensington Underground Station", "Notting Hill Gate Underground Station",
             "Bayswater Underground Station", "Paddington Underground Station"],
            # Main line West
            ["Earl's Court Underground Station", "Gloucester Road Underground Station", "South Kensington Underground Station", 
             "Sloane Square Underground Station", "Victoria Underground Station", "St. James's Park Underground Station", 
             "Westminster Underground Station", "Embankment Underground Station", "Temple Underground Station", 
             "Blackfriars Underground Station", "Mansion House Underground Station", "Cannon Street Underground Station", 
             "Monument Underground Station", "Tower Hill Underground Station", "Aldgate East Underground Station", 
             "Whitechapel Underground Station", "Stepney Green Underground Station", "Mile End Underground Station", 
             "Bow Road Underground Station", "Bromley-by-Bow Underground Station", "West Ham Underground Station", 
             "Plaistow Underground Station", "Upton Park Underground Station", "East Ham Underground Station", 
             "Barking Underground Station", "Upney Underground Station", "Becontree Underground Station", 
             "Dagenham Heathway Underground Station", "Dagenham East Underground Station", "Elm Park Underground Station", 
             "Hornchurch Underground Station", "Upminster Bridge Underground Station", "Upminster Underground Station"],
            # Hammersmith & City connection
            ["Hammersmith (Dist&Picc Line) Underground Station", "Barons Court Underground Station", 
             "West Kensington Underground Station", "Earl's Court Underground Station"],
            # Piccadilly connection
            ["Acton Town Underground Station", "Turnham Green Underground Station", 
             "Hammersmith (Dist&Picc Line) Underground Station", "Barons Court Underground Station"]
        ],
        "jubilee": [
            # North West section
            ["Stanmore Underground Station", "Canons Park Underground Station", "Queensbury Underground Station", 
             "Kingsbury Underground Station", "Wembley Park Underground Station"],
            # Middle section  
            ["Wembley Park Underground Station", "Neasden Underground Station", "Dollis Hill Underground Station", 
             "Willesden Green Underground Station", "Kilburn Underground Station", "West Hampstead Underground Station", 
             "Finchley Road Underground Station"],
            # South section
            ["Finchley Road Underground Station", "Swiss Cottage Underground Station", "St. John's Wood Underground Station", 
             "Baker Street Underground Station", "Bond Street Underground Station", "Green Park Underground Station", 
             "Westminster Underground Station", "Waterloo Underground Station", "Southwark Underground Station", 
             "London Bridge Underground Station", "Bermondsey Underground Station", "Canada Water Underground Station", 
             "Canary Wharf Underground Station", "North Greenwich Underground Station", "Canning Town Underground Station", 
             "West Ham Underground Station", "Stratford Underground Station"]
        ]
    }
    
    # Supplement known branch information with API branch data if available
    for line_id, branches in line_branches.items():
        if line_id not in branched_lines:
            branched_lines[line_id] = []
            # For each branch found in the API, add it as a branch in our known data
            for branch_id, stations in branches.items():
                if len(stations) > 1:  # Only add branches with multiple stations
                    branched_lines[line_id].append(list(stations))
    
    # Create a lookup dictionary to check if two stations are on the same branch
    station_to_branch = {}
    for line, branches in branched_lines.items():
        for branch_idx, branch in enumerate(branches):
            for station in branch:
                if station not in station_to_branch:
                    station_to_branch[station] = {}
                if line not in station_to_branch[station]:
                    station_to_branch[station][line] = []
                station_to_branch[station][line].append(branch_idx)
    
    # Find missing connections on each line
    missing_connections = defaultdict(list)
    
    for line, stations in line_stations.items():
        # Only check lines for relevant transport modes
        if not is_relevant_line(graph_data, line):
            continue
            
        line_conns = line_connections.get(line, set())
        
        # Check all connections to see if they involve two stations on this line
        for connection in all_connections:
            station_pair = list(connection)
            station1, station2 = station_pair[0], station_pair[1]
            
            # Check if both stations are on this line
            if station1 in stations and station2 in stations:
                # Check if the connection exists for this line
                if frozenset([station1, station2]) not in line_conns:
                    # For known branched lines, only report if stations are on the same branch
                    if line in branched_lines:
                        # Skip if either station isn't in our branch data
                        if (station1 not in station_to_branch or 
                            station2 not in station_to_branch or
                            line not in station_to_branch.get(station1, {}) or
                            line not in station_to_branch.get(station2, {})):
                            continue
                            
                        # Check if stations share at least one branch
                        station1_branches = station_to_branch[station1][line]
                        station2_branches = station_to_branch[station2][line]
                        
                        # If no common branches, skip this pair
                        common_branches = [b for b in station1_branches if b in station2_branches]
                        if not common_branches:
                            # Even if they don't share a branch ID, check if they're consecutive in any branch
                            is_branch_consecutive = False
                            for branch_idx in set(station1_branches + station2_branches):
                                branch = branched_lines[line][branch_idx]
                                if station1 in branch and station2 in branch:
                                    s1_idx = branch.index(station1)
                                    s2_idx = branch.index(station2)
                                    if abs(s1_idx - s2_idx) == 1:  # Only consider consecutive stations
                                        is_branch_consecutive = True
                                        break
                            
                            if not is_branch_consecutive:
                                continue
                    
                    # Add as missing connection if they should be connected
                    # Check if other lines connect them to confirm they should be connected
                    for test_line, test_conns in line_connections.items():
                        if test_line != line and frozenset([station1, station2]) in test_conns:
                            missing_connections[line].append((station1, station2))
                            break
    
    return missing_connections

def main():
    """Main function to check line continuity"""
    parser = argparse.ArgumentParser(description="Check for missing connections along transport lines")
    parser.add_argument("--line", help="Check a specific line only (e.g., bakerloo, district)")
    args = parser.parse_args()
    
    # File paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    graph_file = os.path.join(script_dir, 'networkx_graph_new.json')  # Use the new graph file
    
    print(f"Loading graph data from {graph_file}...")
    graph_data = load_graph_data(graph_file)
    
    # Check for missing edges on overlapping lines
    cross_line_missing = find_cross_line_connections(graph_data)
    
    # Check known real-world connections
    missing_real_world = check_real_world_connections(graph_data)
    
    # Check continuity for all lines
    missing_continuity = check_line_continuity(graph_data, args.line)
    
    if not cross_line_missing and not missing_real_world and not missing_continuity:
        print("\nNo missing connections found! All lines appear continuous.")
        return
    
    # Report missing cross-line connections
    if cross_line_missing:
        print("\nMissing edges on overlapping lines:")
        for line, connections in cross_line_missing.items():
            if args.line and args.line != line:
                continue
                
            if connections:
                line_name = get_official_line_name(graph_data, line)
                print(f"\n{line_name} Line ({line}): {len(connections)} missing connections")
                for station1, station2 in connections[:10]:  # Limit output to avoid overwhelming
                    print(f"  {station1} → {station2}")
                
                if len(connections) > 10:
                    print(f"  ... and {len(connections) - 10} more")
    
    # Report missing connections from the continuity check
    if missing_continuity:
        print("\nMissing connections from continuity check:")
        for line, connections in missing_continuity.items():
            if args.line and args.line != line:
                continue
                
            if connections:
                line_name = get_official_line_name(graph_data, line)
                print(f"\n{line_name} Line ({line}):")
                for station1, station2 in connections:
                    print(f"  {station1} → {station2}")
    
    # Report missing real-world connections
    if missing_real_world:
        print("\nMissing known real-world connections:")
        current_line = None
        for line, station1, station2 in missing_real_world:
            if args.line and args.line != line:
                continue
                
            if line != current_line:
                line_name = get_official_line_name(graph_data, line)
                print(f"\n{line_name} Line ({line}):")
                current_line = line
            print(f"  {station1} → {station2}")
    
    # Count total missing connections
    total_missing = sum(len(connections) for connections in cross_line_missing.values())
    print(f"\nTotal missing cross-line connections: {total_missing}")

if __name__ == "__main__":
    main() 