#!/usr/bin/env python3
"""
Build a NetworkX graph of London transport network using TFL API.

This script fetches line sequence data from the TFL API and builds a comprehensive
graph of the London transport network, focusing on the stopPointSequences data
which provides more accurate station sequences and connection information.

Requirements:
- NetworkX
- Requests
- Python-dotenv
"""

# Standard library imports
import os
import json
import time
from collections import defaultdict

# Third-party imports
import requests
import networkx as nx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# TFL API Configuration
TFL_API_KEY = os.getenv("TFL_API_KEY")  # Get API key from .env file
TFL_APP_ID = os.getenv("TFL_APP_ID", "")  # Get app ID, with empty string as default if not found
BASE_URL = "https://api.tfl.gov.uk"  # Base URL for all TFL API requests

# List of transport modes we want to include in our graph
TRANSPORT_MODES = [
    "tube",          # London Underground
    "dlr",           # Docklands Light Railway
    "overground",    # London Overground
    "elizabeth-line" # Elizabeth Line (formerly Crossrail)
]

# Output file paths
OUTPUT_DIR = "network_data"  # Directory to store our data
GRAPH_FILE = os.path.join(OUTPUT_DIR, "networkx_graph_new.json")  # Path for the final graph file
RAW_DATA_FILE = os.path.join(OUTPUT_DIR, "tfl_line_data.json")  # Path for raw API data

def ensure_output_dir():
    """Ensure the output directory exists; create it if it doesn't."""
    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def get_lines_by_mode(mode):
    """
    Get all lines for a specific transport mode from the TFL API.
    
    Args:
        mode: Transport mode (tube, dlr, etc.)
        
    Returns:
        List of line objects containing information about each line
    """
    print(f"Fetching lines for mode: {mode}")
    
    # Create a dictionary of parameters to send with the API request
    params = {
        "app_key": TFL_API_KEY,  # API key for authentication
        "app_id": TFL_APP_ID     # App ID for authentication
    }
    
    # Make a GET request to the TFL API to get all lines for the specified mode
    response = requests.get(f"{BASE_URL}/Line/Mode/{mode}", params=params)
    
    # Check if the request was successful
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching lines for mode {mode}: {response.status_code}")
        print(response.text)
        return []

def get_line_sequence(line_id):
    """
    Get route sequence data for a specific line from the TFL API.
    
    Args:
        line_id: TFL line ID (e.g., 'bakerloo', 'central')
        
    Returns:
        Dictionary containing route sequence data or None if the request fails
    """
    print(f"Fetching sequence data for line: {line_id}")
    
    # Parameters for the API request
    params = {
        "app_key": TFL_API_KEY,
        "app_id": TFL_APP_ID,
        "excludeCrowding": "true"  # We don't need crowding data
    }
    
    # The TFL endpoint for route sequences
    response = requests.get(
        f"{BASE_URL}/Line/{line_id}/Route/Sequence/all", 
        params=params
    )
    
    # Check if request was successful
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching sequence for line {line_id}: {response.status_code}")
        print(response.text)
        return None

def fetch_all_line_data():
    """
    Fetch route sequence data for all lines across all transport modes.
    
    Returns:
        Dictionary with line_id as key and sequence data as value
    """
    # Dictionary to store all the line data
    all_line_data = {}
    
    # Loop through each transport mode
    for mode in TRANSPORT_MODES:
        # Get all lines for this mode
        lines = get_lines_by_mode(mode)
        
        # Loop through each line
        for line in lines:
            # Get the line ID from the line object
            line_id = line.get("id")
            
            # Only proceed if we have a valid line ID
            if line_id:
                # Add a small delay to avoid overwhelming the API with requests
                time.sleep(0.5)
                
                # Get detailed sequence data for this line
                sequence_data = get_line_sequence(line_id)
                
                # If we got valid data, add it to our dictionary
                if sequence_data:
                    all_line_data[line_id] = sequence_data
    
    return all_line_data

def save_raw_data(data):
    """
    Save raw TFL API data to a JSON file.
    
    Args:
        data: The data to save
    """
    # Make sure the output directory exists
    ensure_output_dir()
    
    # Save data as JSON
    with open(RAW_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Raw data saved to {RAW_DATA_FILE}")

def load_raw_data():
    """
    Load raw TFL API data from file if available.
    
    Returns:
        The loaded data or None if the file doesn't exist
    """
    # Check if the file exists
    if os.path.exists(RAW_DATA_FILE):
        with open(RAW_DATA_FILE, 'r') as f:
            return json.load(f)
    return None

def get_station_data(station_dict):
    """
    Extract relevant station data from the station dictionary.
    
    Args:
        station_dict: Station dictionary from TFL API
        
    Returns:
        Dictionary with cleaned station data
    """
    # Extract the most useful data for each station
    return {
        "station_id": station_dict.get("stationId", ""),    # Unique station ID
        "parent_id": station_dict.get("topMostParentId", ""), # Parent station ID
        "name": station_dict.get("name", ""),               # Station name
        "lat": station_dict.get("lat", 0),                  # Latitude coordinate
        "lon": station_dict.get("lon", 0),                  # Longitude coordinate
        "modes": station_dict.get("modes", []),             # Transport modes
        "lines": [line.get("id") for line in station_dict.get("lines", [])],  # Lines serving this station
        "zone": station_dict.get("zone", "")                # London transport zone
    }

def build_graph_from_stop_point_sequences(line_data):
    """
    Build a NetworkX graph from the stopPointSequences data in the TFL API response.
    
    Args:
        line_data: Dictionary with line_id as key and sequence data as value
        
    Returns:
        NetworkX graph object with stations as nodes and connections as edges
    """
    # Create a new multi-directed graph to support multiple edges between the same nodes
    G = nx.MultiDiGraph()
    
    # Dictionary to track all stations by their ID
    all_stations = {}
    
    # Dictionary to track station connections (edges)
    connections = defaultdict(list)
    
    # Process each line
    for line_id, sequence_data in line_data.items():
        line_name = sequence_data.get("lineName", line_id)
        mode = sequence_data.get("mode", "")
        
        print(f"Processing line: {line_name} ({line_id})")
        
        # First check if there's a stopPointSequences section
        stop_point_sequences = sequence_data.get("stopPointSequences", [])
        
        if stop_point_sequences:
            print(f"  Found {len(stop_point_sequences)} stop point sequences")
            
            # Process each stop point sequence (each represents a branch/direction)
            for i, sequence in enumerate(stop_point_sequences):
                direction = sequence.get("direction", "unknown")
                branch_name = sequence.get("name", "unknown")
                print(f"  Processing sequence {i+1}: {direction} - {branch_name}")
                
                # Get the stop points (stations) in this sequence
                stop_points = sequence.get("stopPoint", [])
                print(f"  Sequence has {len(stop_points)} stations")
                
                # First pass: add all stations to the graph
                for stop in stop_points:
                    # Get station ID
                    station_id = stop.get("stationId", "")
                    if not station_id:
                        print(f"  Warning: Station {stop.get('name', 'Unknown')} has no ID, skipping")
                        continue
                    
                    # Create station data dictionary
                    station_data = {
                        "station_id": station_id,
                        "parent_id": stop.get("topMostParentId", stop.get("parentId", "")),
                        "name": stop.get("name", ""),
                        "lat": stop.get("lat", 0),
                        "lon": stop.get("lon", 0),
                        "modes": stop.get("modes", []),
                        "lines": [line.get("id") for line in stop.get("lines", [])],
                        "zone": stop.get("zone", "")
                    }
                    
                    # Add to all_stations dictionary
                    if station_id not in all_stations:
                        all_stations[station_id] = station_data
                    else:
                        # Update lines list if station already exists
                        all_stations[station_id]["lines"] = list(set(
                            all_stations[station_id]["lines"] + station_data["lines"]
                        ))
                    
                    # Add the station to the graph
                    if not G.has_node(station_id):
                        G.add_node(station_id, **station_data)
                    else:
                        # Update node data to ensure all line information is captured
                        lines = G.nodes[station_id].get('lines', [])
                        for line in station_data.get('lines', []):
                            if line not in lines:
                                lines.append(line)
                        G.nodes[station_id]['lines'] = lines
                
                # Second pass: create connections between consecutive stations
                for j in range(len(stop_points) - 1):
                    from_station = stop_points[j].get("stationId", "")
                    to_station = stop_points[j + 1].get("stationId", "")
                    
                    if from_station and to_station:
                        # Create a connection tuple (from, to, attributes)
                        connection = (from_station, to_station, {
                            "line": line_id,
                            "line_name": line_name,
                            "mode": mode,
                            "direction": direction,
                            "branch": branch_name,
                            "weight": 1  # Default weight - can be updated with actual times
                        })
                        
                        # Add to connections dictionary
                        connections[line_id].append(connection)
        else:
            # If no stopPointSequences, fall back to the orderedLineRoutes
            print(f"  Warning: No stopPointSequences found for {line_id}, trying orderedLineRoutes")
            
            # Process the ordered line routes if available
            ordered_routes = sequence_data.get("orderedLineRoutes", [])
            if ordered_routes:
                print(f"  Found {len(ordered_routes)} ordered routes")
                
                for i, route in enumerate(ordered_routes):
                    # Get the naptan IDs (station IDs) in this route
                    naptan_ids = route.get("naptanIds", [])
                    branch_name = route.get("name", f"route-{i+1}")
                    direction = route.get("direction", "unknown")
                    
                    if not naptan_ids:
                        print(f"  Warning: No stations in route {i+1} for {line_id}")
                        continue
                        
                    print(f"  Route {i+1} has {len(naptan_ids)} stations")
                    
                    # First, add all stations in this route to the graph
                    for station_id in naptan_ids:
                        # Try to find the station in the stations list for this line
                        station_data = None
                        for station in sequence_data.get("stations", []):
                            if station.get("stationId") == station_id:
                                station_data = get_station_data(station)
                                break
                        
                        # If not found, create minimal data
                        if not station_data:
                            station_data = {
                                "station_id": station_id,
                                "name": station_id,  # Use ID as name if no better info
                                "lines": [line_id]
                            }
                        
                        # Add to all_stations dictionary
                        if station_id not in all_stations:
                            all_stations[station_id] = station_data
                        else:
                            # Update lines list if station already exists
                            all_stations[station_id]["lines"] = list(set(
                                all_stations[station_id]["lines"] + station_data["lines"]
                            ))
                        
                        # Add the station to the graph
                        if not G.has_node(station_id):
                            G.add_node(station_id, **station_data)
                        else:
                            # Update node data to ensure all line information is captured
                            lines = G.nodes[station_id].get('lines', [])
                            for line in station_data.get('lines', []):
                                if line not in lines:
                                    lines.append(line)
                            G.nodes[station_id]['lines'] = lines
                    
                    # Create connections between consecutive stations
                    for j in range(len(naptan_ids) - 1):
                        from_station = naptan_ids[j]
                        to_station = naptan_ids[j + 1]
                        
                        # Create a connection tuple (from, to, attributes)
                        connection = (from_station, to_station, {
                            "line": line_id,
                            "line_name": line_name,
                            "mode": mode,
                            "direction": direction,
                            "branch": branch_name,
                            "weight": 1
                        })
                        
                        # Add to connections dictionary
                        connections[line_id].append(connection)
            else:
                # If neither stopPointSequences nor orderedLineRoutes, try stations and service patterns
                print(f"  Warning: No ordered routes found for {line_id}, trying service patterns")
                
                # Process all stations on this line
                all_line_stations = []
                for station in sequence_data.get("stations", []):
                    station_data = get_station_data(station)
                    station_id = station_data["station_id"]
                    
                    # Skip stations with no ID
                    if not station_id:
                        continue
                    
                    all_line_stations.append(station_id)
                    
                    # Add to all_stations dictionary
                    if station_id not in all_stations:
                        all_stations[station_id] = station_data
                    else:
                        # Update lines list if station already exists
                        all_stations[station_id]["lines"] = list(set(
                            all_stations[station_id]["lines"] + station_data["lines"]
                        ))
                    
                    # Add the station to the graph
                    if not G.has_node(station_id):
                        G.add_node(station_id, **station_data)
                    else:
                        # Update node data to ensure all line information is captured
                        lines = G.nodes[station_id].get('lines', [])
                        for line in station_data.get('lines', []):
                            if line not in lines:
                                lines.append(line)
                        G.nodes[station_id]['lines'] = lines
                
                # Check service patterns if available
                service_patterns = sequence_data.get("servicePatterns", [])
                if service_patterns:
                    print(f"  Found {len(service_patterns)} service patterns")
                    
                    for i, pattern in enumerate(service_patterns):
                        stops = pattern.get("stopPoint", [])
                        if not stops:
                            continue
                        
                        print(f"  Pattern {i+1} has {len(stops)} stops")
                        
                        # Create connections between consecutive stations
                        for j in range(len(stops) - 1):
                            from_id = stops[j].get("stationId")
                            to_id = stops[j + 1].get("stationId")
                            
                            if from_id and to_id:
                                # Create a connection tuple (from, to, attributes)
                                connection = (from_id, to_id, {
                                    "line": line_id,
                                    "line_name": line_name,
                                    "mode": mode,
                                    "direction": f"pattern-{i+1}",
                                    "branch": f"service-pattern-{i+1}",
                                    "weight": 1
                                })
                                
                                # Add to connections dictionary
                                connections[line_id].append(connection)
    
    # Add all connections to the graph
    edge_count = 0
    
    # With MultiDiGraph, we can add multiple edges between the same nodes with different attributes
    for line_id, line_connections in connections.items():
        for from_station, to_station, attrs in line_connections:
            # Add edge if both stations exist in graph
            if G.has_node(from_station) and G.has_node(to_station):
                # Also add the line to both stations' lines attributes if not already there
                for station_id in [from_station, to_station]:
                    lines = G.nodes[station_id].get('lines', [])
                    if line_id not in lines:
                        lines.append(line_id)
                        G.nodes[station_id]['lines'] = lines
                
                # Add bidirectional edges for each connection
                # Forward direction
                G.add_edge(from_station, to_station, **attrs)
                
                # Reverse direction (for bidirectional travel)
                reverse_attrs = attrs.copy()
                if reverse_attrs.get('direction') == 'inbound':
                    reverse_attrs['direction'] = 'outbound'
                elif reverse_attrs.get('direction') == 'outbound':
                    reverse_attrs['direction'] = 'inbound'
                
                G.add_edge(to_station, from_station, **reverse_attrs)
                
                edge_count += 2  # Count both directions
    
    print(f"Added {edge_count} edges between stations")
    
    # Add parent-child edges (zero-weight transfer edges)
    add_parent_child_edges(G, all_stations)
    
    return G

def add_parent_child_edges(G, all_stations):
    """
    Add zero-weight edges between parent and child stations for transfers.
    
    Args:
        G: NetworkX graph
        all_stations: Dictionary of all stations
    """
    # Group stations by parent ID
    parent_to_children = defaultdict(list)
    
    # Find parent-child relationships
    for station_id, station_data in all_stations.items():
        parent_id = station_data["parent_id"]
        
        # If parent_id is different from station_id and both are in the graph
        if parent_id and parent_id != station_id and G.has_node(parent_id) and G.has_node(station_id):
            parent_to_children[parent_id].append(station_id)
    
    # Load existing parent-child relationships if available
    # Get the absolute path to the project root (parent of network_data)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    slim_stations_file = os.path.join(project_root, "slim_stations/unique_stations.json")
    
    try:
        with open(slim_stations_file, 'r') as f:
            existing_data = json.load(f)
            print(f"Loaded existing station data for parent-child relationships from {slim_stations_file}")
            
            # Create a mapping from station name to ID
            name_to_id = {}
            for station_id, data in G.nodes(data=True):
                name = data.get("name", "")
                if name:
                    name_to_id[name] = station_id
            
            # Add parent-child relationships from existing data
            for station in existing_data:
                parent_name = station.get("name", "")
                children = station.get("child_stations", [])
                
                if not parent_name or not children:
                    continue
                
                # Get parent ID
                parent_id = name_to_id.get(parent_name)
                if not parent_id:
                    continue
                
                # Process each child
                for child_name in children:
                    child_id = name_to_id.get(child_name)
                    if child_id and G.has_node(child_id):
                        # Add this relationship
                        if child_id not in parent_to_children[parent_id]:
                            parent_to_children[parent_id].append(child_id)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load existing station data from {slim_stations_file}: {e}")
    
    # Add zero-weight edges between parent and children (both directions)
    added_edges = 0
    for parent_id, children in parent_to_children.items():
        for child_id in children:
            # Add bidirectional edges with transfer=True attribute
            G.add_edge(parent_id, child_id, weight=0, transfer=True)
            G.add_edge(child_id, parent_id, weight=0, transfer=True)
            added_edges += 2
    
    print(f"Added {added_edges} zero-weight transfer edges between parent and child stations")

def save_graph_to_json(G):
    """
    Save NetworkX graph as JSON.
    
    Args:
        G: NetworkX graph object
    """
    ensure_output_dir()
    
    # Convert NetworkX graph to a dictionary format
    graph_data = {
        "nodes": {},  # Dictionary of node name -> node data
        "edges": []   # List of edge objects
    }
    
    # Add nodes to the dictionary
    for node, data in G.nodes(data=True):
        station_name = data.get("name", "")
        if not station_name:
            print(f"Warning: Station {node} has no name")
            continue
            
        # Store data with station name as the key
        graph_data["nodes"][station_name] = {
            "id": node,
            "name": station_name,
            "lat": data.get("lat", 0),
            "lon": data.get("lon", 0),
            "zone": data.get("zone", ""),
            "modes": data.get("modes", []),
            "lines": data.get("lines", []),
            "child_stations": []  # Will be populated later from slim_stations data
        }
    
    # Try to load existing child station data
    # Get the absolute path to the project root (parent of network_data)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    slim_stations_file = os.path.join(project_root, "slim_stations/unique_stations.json")
    
    try:
        with open(slim_stations_file, 'r') as f:
            existing_data = json.load(f)
            print(f"Loaded existing station data for child stations from {slim_stations_file}")
            
            # Create a mapping from original name to standardized name
            name_to_standardized = {}
            for station in existing_data:
                original_name = station.get("name", "")
                if original_name:
                    name_to_standardized[original_name.lower()] = original_name
            
            # Update child_stations for each node
            for station in existing_data:
                parent_name = station.get("name", "")
                child_stations = station.get("child_stations", [])
                
                if parent_name in graph_data["nodes"] and child_stations:
                    graph_data["nodes"][parent_name]["child_stations"] = child_stations
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load existing station data for child stations from {slim_stations_file}: {e}")
    
    # Now we can add all edges from the MultiDiGraph, preserving multiple edges between the same stations
    edge_count = 0
    
    # Add edges to the list, with each edge having its unique attributes
    for u, v, key, data in G.edges(data=True, keys=True):
        # Get the station names for source and target
        u_data = G.nodes[u]
        v_data = G.nodes[v]
        
        source_name = u_data.get("name", "")
        target_name = v_data.get("name", "")
        
        if not source_name or not target_name:
            # Skip edges with missing station names
            continue
            
        # Create the edge with all attributes
        edge = {
            "source": source_name,      # Source station name
            "target": target_name,      # Target station name
            "line": data.get("line", ""),
            "line_name": data.get("line_name", ""),
            "mode": data.get("mode", ""),
            "weight": data.get("weight", 1),
            "transfer": data.get("transfer", False),  # Transfer flag
            "direction": data.get("direction", ""),   # Direction info
            "branch": data.get("branch", ""),         # Branch info
            "key": key                               # Include the MultiDiGraph edge key
        }
        
        # Add edge to the edges list
        graph_data["edges"].append(edge)
        edge_count += 1
    
    print(f"Added {edge_count} edges to graph data")
    
    # Save to file
    with open(GRAPH_FILE, 'w') as f:
        json.dump(graph_data, f, indent=2)
    
    print(f"Graph saved to {GRAPH_FILE}")

def main():
    """Main function to build and save the network graph."""
    print("Building London transport network graph using stopPointSequences data...")
    
    # Try to load raw data from file if available
    line_data = load_raw_data()
    
    # If not available, fetch from API
    if not line_data:
        print("No cached data found. Fetching from TFL API...")
        line_data = fetch_all_line_data()
        save_raw_data(line_data)
    else:
        print("Using cached TFL data.")
    
    # Build graph from line data using stopPointSequences
    print("Building graph from stopPointSequences data...")
    G = build_graph_from_stop_point_sequences(line_data)
    
    # Print some graph statistics
    print(f"Graph built with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    
    # Analyze connectivity
    connected_components = list(nx.weakly_connected_components(G))
    print(f"Graph has {len(connected_components)} connected components")
    print(f"Largest component has {max(len(c) for c in connected_components)} stations")
    
    # Save graph to JSON
    print("Saving graph to JSON...")
    save_graph_to_json(G)
    
    print("Done!")

if __name__ == "__main__":
    main() 