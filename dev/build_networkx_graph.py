#!/usr/bin/env python3
"""
Build a NetworkX graph of London transport network using TFL API.

This script fetches line sequence data from the TFL API and builds a comprehensive
graph of the London transport network, including tube, DLR, overground, and
other rail services. The graph is stored in a JSON file for later use.

Requirements:
- NetworkX
- Requests
- Python-dotenv
"""

# Standard library imports for handling files, directories, etc.
import os
import json
import time

# Third-party imports
import requests  # For making HTTP requests to the TFL API
import networkx as nx  # For creating and manipulating graph data structures
from dotenv import load_dotenv  # For loading API keys from .env file
from collections import defaultdict  # Special dictionary that provides default values for missing keys

# Load environment variables from .env file
# This keeps sensitive info like API keys out of the code
load_dotenv()

# TFL API Configuration
# We get the API key from environment variables for security
TFL_API_KEY = os.getenv("TFL_API_KEY")  # Get API key from .env file
TFL_APP_ID = os.getenv("TFL_APP_ID", "")  # Get app ID, with empty string as default if not found
BASE_URL = "https://api.tfl.gov.uk"  # Base URL for all TFL API requests

# List of transport modes we want to include in our graph
TRANSPORT_MODES = [
    "tube",  # London Underground
    "dlr",   # Docklands Light Railway
    "overground",  # London Overground
    "elizabeth-line"  # Elizabeth Line (formerly Crossrail)
]

# Output file paths
OUTPUT_DIR = "network_data"  # Directory to store our data
GRAPH_FILE = os.path.join(OUTPUT_DIR, "networkx_graph.json")  # Path for the final graph file
RAW_DATA_FILE = os.path.join(OUTPUT_DIR, "tfl_line_data.json")  # Path for raw API data

# Special handling for lines with problematic station data
SPECIAL_STATION_MAPPINGS = {
    "waterloo-city": {
        "Bank": "940GZZLUBNK",  # Bank Underground Station ID
        "Waterloo": "940GZZLUWLO"  # Waterloo Underground Station ID
    }
}

def ensure_output_dir():
    """Ensure the output directory exists; create it if it doesn't."""
    # os.path.exists checks if a directory or file exists
    if not os.path.exists(OUTPUT_DIR):
        # os.makedirs creates the directory if it doesn't exist
        os.makedirs(OUTPUT_DIR)
        # This is similar to running 'mkdir -p network_data' in the terminal

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
    # f-strings allow embedding variables directly in strings with {variable}
    response = requests.get(f"{BASE_URL}/Line/Mode/{mode}", params=params)
    
    # Check if the request was successful (HTTP status code 200 means success)
    if response.status_code == 200:
        # Parse the JSON response and return it
        return response.json()
    else:
        # If request failed, print error details and return empty list
        print(f"Error fetching lines for mode {mode}: {response.status_code}")
        print(response.text)
        return []

def get_line_sequence(line_id):
    """
    Get route sequence data for a specific line from the TFL API.
    
    This is the main endpoint we use to get station-by-station sequence data.
    
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
    # We use 'all' to get all directions of the line
    response = requests.get(
        f"{BASE_URL}/Line/{line_id}/Route/Sequence/all", 
        params=params
    )
    
    # Check if request was successful
    if response.status_code == 200:
        return response.json()  # Return parsed JSON data
    else:
        # Print error details and return None if request failed
        print(f"Error fetching sequence for line {line_id}: {response.status_code}")
        print(response.text)
        return None

def fetch_all_line_data():
    """
    Fetch route sequence data for all lines across all transport modes.
    
    This function:
    1. Gets all lines for each transport mode
    2. For each line, gets its detailed sequence data
    3. Combines everything into a single dictionary
    
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
                # This is a common practice to avoid rate limiting
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
    
    This allows us to cache the data so we don't need to call the API every time.
    
    Args:
        data: The data to save
    """
    # Make sure the output directory exists
    ensure_output_dir()
    
    # Open the file for writing ('w' mode)
    # The 'with' statement ensures the file is properly closed after writing
    with open(RAW_DATA_FILE, 'w') as f:
        # Write the data as formatted JSON with indentation for readability
        json.dump(data, f, indent=2)
    
    print(f"Raw data saved to {RAW_DATA_FILE}")

def load_raw_data():
    """
    Load raw TFL API data from file if available.
    
    This lets us use cached data instead of calling the API every time.
    
    Returns:
        The loaded data or None if the file doesn't exist
    """
    # Check if the file exists
    if os.path.exists(RAW_DATA_FILE):
        # Open the file for reading ('r' mode)
        with open(RAW_DATA_FILE, 'r') as f:
            # Parse JSON from the file and return it
            return json.load(f)
    return None  # Return None if file doesn't exist

def get_station_data(station_dict):
    """
    Extract relevant station data from the station dictionary.
    
    This creates a clean, consistent format for station data 
    by extracting just the fields we need.
    
    Args:
        station_dict: Station dictionary from TFL API
        
    Returns:
        Dictionary with cleaned station data
    """
    # Extract the most useful data for each station
    # The get() method provides a default value if the key doesn't exist
    return {
        "station_id": station_dict.get("stationId", ""),  # Unique station ID
        "parent_id": station_dict.get("topMostParentId", ""),  # Parent station ID
        "name": station_dict.get("name", ""),  # Station name
        "lat": station_dict.get("lat", 0),  # Latitude coordinate
        "lon": station_dict.get("lon", 0),  # Longitude coordinate
        "modes": station_dict.get("modes", []),  # Transport modes (tube, bus, etc.)
        "lines": [line.get("id") for line in station_dict.get("lines", [])],  # Lines serving this station
        "zone": station_dict.get("zone", "")  # London transport zone
    }

def parse_geo_json_string(geo_json_str):
    """
    Parse a GeoJSON string into a list of coordinate pairs.
    
    Args:
        geo_json_str: GeoJSON string representing a line
        
    Returns:
        List of coordinate pairs [[lon, lat], [lon, lat], ...]
    """
    try:
        # Try to parse as a complete GeoJSON object
        data = json.loads(geo_json_str)
        
        # Extract coordinates based on GeoJSON structure
        if isinstance(data, dict):
            # Full GeoJSON object
            if 'type' in data:
                if data['type'] == 'LineString' and 'coordinates' in data:
                    return data['coordinates']
                elif data['type'] == 'Feature' and 'geometry' in data:
                    geometry = data['geometry']
                    if 'type' in geometry and geometry['type'] == 'LineString' and 'coordinates' in geometry:
                        return geometry['coordinates']
                    elif 'type' in geometry and geometry['type'] == 'MultiLineString' and 'coordinates' in geometry:
                        # Flatten multi-line string
                        all_coords = []
                        for line in geometry['coordinates']:
                            all_coords.extend(line)
                        return all_coords
            
            # GeoJSON FeatureCollection
            if 'features' in data and isinstance(data['features'], list):
                coordinates = []
                for feature in data['features']:
                    if 'geometry' in feature and 'coordinates' in feature['geometry']:
                        if feature['geometry'].get('type') == 'LineString':
                            coordinates.extend(feature['geometry']['coordinates'])
                        elif feature['geometry'].get('type') == 'MultiLineString':
                            for line in feature['geometry']['coordinates']:
                                coordinates.extend(line)
                return coordinates
        elif isinstance(data, list):
            # Direct array of coordinates or array of line segments
            if data and isinstance(data[0], list):
                if len(data[0]) == 2 and all(isinstance(x, (int, float)) for x in data[0]):
                    # Direct array of [lon, lat] pairs
                    return data
                elif isinstance(data[0][0], list):
                    # Array of line segments, flatten it
                    flat_coords = []
                    for segment in data:
                        flat_coords.extend(segment)
                    return flat_coords
        
        # None of the recognized formats matched
        print(f"  Warning: Unrecognized GeoJSON format: {str(data)[:100]}...")
        
        # Last resort: try to extract any array that looks like coordinates
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list) and value and isinstance(value[0], list) and len(value[0]) == 2:
                    print(f"  Found potential coordinates in key '{key}'")
                    return value
        
        return []
    except json.JSONDecodeError as e:
        # Debug: print small sample of the string for diagnosis
        sample = geo_json_str[:100] + '...' if len(geo_json_str) > 100 else geo_json_str
        print(f"  Error parsing GeoJSON: {e}")
        print(f"  Sample: {sample}")
        
        # Try to sanitize the string and parse again
        try:
            # Some strings might be malformed JSON with unescaped characters
            # Try to clean up common issues
            sanitized = geo_json_str.replace('\\', '\\\\').replace('\n', '\\n')
            data = json.loads(sanitized)
            print(f"  Succeeded after sanitizing the string")
            
            # Now try parsing the sanitized data
            if isinstance(data, dict) and 'coordinates' in data:
                return data['coordinates']
            elif isinstance(data, list):
                return data
            
        except json.JSONDecodeError:
            pass
            
        return []

def build_graph_from_data(line_data):
    """
    Build a NetworkX graph from the TFL line sequence data.
    
    This is the core function that transforms the API data into a graph structure.
    
    Args:
        line_data: Dictionary with line_id as key and sequence data as value
        
    Returns:
        NetworkX graph object with stations as nodes and connections as edges
    """
    # Create a new directed graph (DiGraph)
    # We use a directed graph because travel times might be different in each direction
    G = nx.DiGraph()
    
    # Dictionary to track all stations by their ID
    all_stations = {}
    
    # Dictionary to track station connections (edges)
    # defaultdict creates a dictionary with default values (empty list in this case)
    connections = defaultdict(list)
    
    # First pass: add all stations to the graph
    for line_id, sequence_data in line_data.items():
        # Get the line name and mode from the sequence data
        line_name = sequence_data.get("lineName", line_id)  # Use line_id as fallback
        mode = sequence_data.get("mode", "")
        
        print(f"Processing line: {line_name} ({line_id})")
        
        # Process all stations on this line
        for station in sequence_data.get("stations", []):
            # Get clean station data
            station_data = get_station_data(station)
            station_id = station_data["station_id"]
            
            # Special handling for lines with missing station IDs
            if not station_id and line_id in SPECIAL_STATION_MAPPINGS:
                station_name = station_data["name"]
                if station_name in SPECIAL_STATION_MAPPINGS[line_id]:
                    station_id = SPECIAL_STATION_MAPPINGS[line_id][station_name]
                    station_data["station_id"] = station_id
                    print(f"  Applied special mapping for {station_name} on {line_id} line: {station_id}")
            
            # Skip stations with no ID after special handling attempt
            if not station_id:
                print(f"  Warning: Station {station_data['name']} has no ID, skipping")
                continue
                
            # Add to all_stations dictionary if not already present
            if station_id not in all_stations:
                all_stations[station_id] = station_data
            else:
                # If station exists, update its lines list with any new lines
                # We convert to a set to remove duplicates, then back to a list
                all_stations[station_id]["lines"] = list(set(
                    all_stations[station_id]["lines"] + station_data["lines"]
                ))
            
            # Add the station to the graph if not already present
            # NetworkX allows storing data with each node
            if not G.has_node(station_id):
                G.add_node(station_id, **station_data)  # ** unpacks the dictionary as keyword arguments
        
        # For waterloo-city line, manually add connection if not in lineStrings
        if line_id == "waterloo-city" and len(sequence_data.get("lineStrings", [])) == 0:
            # Get the station IDs for Bank and Waterloo
            bank_id = SPECIAL_STATION_MAPPINGS["waterloo-city"]["Bank"]
            waterloo_id = SPECIAL_STATION_MAPPINGS["waterloo-city"]["Waterloo"]
            
            # Check if both stations were added to the graph
            if G.has_node(bank_id) and G.has_node(waterloo_id):
                print(f"  Manually adding Waterloo & City line connection between Bank and Waterloo")
                
                # Create connections in both directions
                connections[line_id].append((bank_id, waterloo_id, {
                    "line": line_id,
                    "line_name": line_name,
                    "mode": mode,
                    "weight": 1
                }))
                connections[line_id].append((waterloo_id, bank_id, {
                    "line": line_id,
                    "line_name": line_name,
                    "mode": mode,
                    "weight": 1
                }))
                
        # Second pass: process the lineStrings to extract connections between stations
        # Each array in lineStrings represents a branch/direction of the line
        line_strings = sequence_data.get("lineStrings", [])
        print(f"  Line {line_id} has {len(line_strings)} branches/directions")
        
        stations_list = sequence_data.get("stations", [])
        
        for i, line_string in enumerate(line_strings):
            # Check if this is actually a list of coordinates or a GeoJSON string
            if isinstance(line_string, str):
                print(f"  Branch {i+1}: Parsing GeoJSON string...")
                # Parse the GeoJSON string into a list of coordinates
                coordinates = parse_geo_json_string(line_string)
                print(f"  Extracted {len(coordinates)} coordinates from GeoJSON")
                
                # Map coordinates to station IDs
                if coordinates:
                    # Convert to station sequence
                    station_sequence = match_coordinates_to_stations(
                        coordinates, 
                        stations_list
                    )
                    
                    print(f"  Found {len(station_sequence)} stations in sequence")
                    
                    # Create edges between consecutive stations in the sequence
                    for j in range(len(station_sequence) - 1):
                        from_station = station_sequence[j]
                        to_station = station_sequence[j + 1]
                        
                        if from_station and to_station:
                            # Create a connection tuple (from, to, attributes)
                            connection = (from_station, to_station, {
                                "line": line_id,          # Line ID
                                "line_name": line_name,   # Human-readable line name
                                "mode": mode,             # Transport mode
                                # Default weight of 1, can be updated later with actual travel times
                                "weight": 1
                            })
                            # Add to connections dictionary (grouped by line)
                            connections[line_id].append(connection)
            elif isinstance(line_string, list) and len(line_string) > 1:
                # It's already a list of coordinates
                print(f"  Branch {i+1}: Processing {len(line_string)} coordinates")
                
                # Map coordinates to station IDs
                station_sequence = match_coordinates_to_stations(
                    line_string, 
                    stations_list
                )
                
                print(f"  Found {len(station_sequence)} stations in sequence")
                
                # Create edges between consecutive stations in the sequence
                for j in range(len(station_sequence) - 1):
                    from_station = station_sequence[j]
                    to_station = station_sequence[j + 1]
                    
                    if from_station and to_station:
                        # Create a connection tuple (from, to, attributes)
                        connection = (from_station, to_station, {
                            "line": line_id,          # Line ID
                            "line_name": line_name,   # Human-readable line name
                            "mode": mode,             # Transport mode
                            # Default weight of 1, can be updated later with actual travel times
                            "weight": 1
                        })
                        # Add to connections dictionary (grouped by line)
                        connections[line_id].append(connection)
            else:
                print(f"  Warning: Skipping branch {i+1} - invalid format or too short")
    
    # Add all connections to the graph
    edge_count = 0
    for line_id, line_connections in connections.items():
        for from_station, to_station, attrs in line_connections:
            # Add edge if both stations exist in graph
            if G.has_node(from_station) and G.has_node(to_station):
                G.add_edge(from_station, to_station, **attrs)
                edge_count += 1
    
    print(f"Added {edge_count} edges between stations")
    
    # Add zero-weight edges between parent-child stations for transfers
    add_parent_child_edges(G, all_stations)
    
    return G

def match_coordinates_to_stations(line_string, stations):
    """
    Match coordinates in a line_string to station IDs.
    
    This is a challenging part of the script because the coordinates in 
    lineStrings don't always exactly match station coordinates.
    
    Args:
        line_string: List of coordinate pairs or GeoJSON string
        stations: List of station dictionaries
        
    Returns:
        List of station IDs in sequence along the line
    """
    # Handle GeoJSON strings if that's what we received
    if len(line_string) > 0 and isinstance(line_string[0], str):
        # Try to parse GeoJSON strings
        try:
            # If it's a JSON string, parse it
            if line_string[0].startswith('[') or line_string[0].startswith('{'):
                print("  Attempting to parse GeoJSON string")
                parsed_coords = []
                for coord_str in line_string:
                    try:
                        # Parse the JSON string into a Python object
                        coords = json.loads(coord_str)
                        if isinstance(coords, list):
                            parsed_coords.extend(coords)
                        else:
                            print(f"  Warning: Unexpected format after parsing: {type(coords)}")
                    except json.JSONDecodeError:
                        print(f"  Warning: Failed to parse coordinate string: {coord_str[:30]}...")
                
                # Replace line_string with parsed coordinates
                line_string = parsed_coords
                print(f"  Parsed {len(parsed_coords)} coordinates from GeoJSON")
        except Exception as e:
            print(f"  Error parsing GeoJSON: {e}")
    
    # Create a lookup dictionary for stations by coordinates
    # This makes it faster to find stations by their coordinates
    station_by_coord = {}
    for station in stations:
        # Use a tuple of rounded coordinates as key for better matching
        # Rounding helps handle small differences in precision
        lat = round(station.get("lat", 0), 5)
        lon = round(station.get("lon", 0), 5)
        station_by_coord[(lat, lon)] = station.get("stationId")
        # Also add a reversed coordinate pair as some APIs swap lat/lon
        station_by_coord[(lon, lat)] = station.get("stationId")
    
    # Match each coordinate in the line_string to a station
    station_sequence = []
    for coord in line_string:
        try:
            # Check if coord is a proper coordinate pair
            if not isinstance(coord, (list, tuple)) or len(coord) < 2:
                # Skip invalid coordinates
                print(f"  Warning: Invalid coordinate format: {coord}")
                continue
                
            # Try both coordinate orientations (TFL sometimes uses [lon, lat] and sometimes [lat, lon])
            # First assume [lon, lat] which is more common in GeoJSON
            lon, lat = coord[0], coord[1]
            
            # Round coordinates for more reliable matching
            rounded_lat = round(lat, 5)
            rounded_lon = round(lon, 5)
            
            # Try to find a station with these coordinates
            station_id = station_by_coord.get((rounded_lat, rounded_lon))
            
            # If not found, try reversed coordinates [lat, lon]
            if not station_id:
                station_id = station_by_coord.get((rounded_lon, rounded_lat))
            
            # If still not found, find closest station within a threshold
            if not station_id:
                station_id = find_closest_station(rounded_lat, rounded_lon, stations)
                
                # If still not found, try with coordinates reversed
                if not station_id:
                    station_id = find_closest_station(rounded_lon, rounded_lat, stations)
            
            # Only add station if we haven't just added it (avoid duplicates)
            # This checks if station_id exists and if it's different from the last added station
            if station_id and (not station_sequence or station_sequence[-1] != station_id):
                station_sequence.append(station_id)
        except (ValueError, TypeError, IndexError) as e:
            # Handle any errors in unpacking or processing coordinates
            print(f"  Warning: Error processing coordinate {coord}: {e}")
            continue
    
    return station_sequence

def find_closest_station(lat, lon, stations, max_distance=0.001):
    """
    Find the closest station to given coordinates.
    
    This handles cases where coordinates don't exactly match any station.
    
    Args:
        lat: Latitude
        lon: Longitude
        stations: List of station dictionaries
        max_distance: Maximum allowed distance for matching (approx. 100m)
        
    Returns:
        Closest station ID or None if no station is within max_distance
    """
    closest_station = None
    min_distance = float('inf')  # Start with infinity as the minimum distance
    
    for station in stations:
        station_lat = station.get("lat", 0)
        station_lon = station.get("lon", 0)
        
        # Calculate simple Euclidean distance
        # For small areas like London, this approximation is good enough
        # For larger areas, we would need to use the Haversine formula
        distance = ((lat - station_lat) ** 2 + (lon - station_lon) ** 2) ** 0.5
        
        # Update closest_station if this station is closer than current minimum
        # and within the maximum allowed distance
        if distance < min_distance and distance < max_distance:
            min_distance = distance
            closest_station = station.get("stationId")
    
    return closest_station

def add_parent_child_edges(G, all_stations):
    """
    Add zero-weight edges between parent and child stations.
    
    This represents free transfers between connected stations like
    "Bank Underground Station" and "Bank DLR Station".
    
    Args:
        G: NetworkX graph
        all_stations: Dictionary of all stations
    """
    # Group stations by parent ID
    # This makes it easy to find all children of a parent station
    parent_to_children = defaultdict(list)
    
    # Find all parent-child relationships based on TFL data
    for station_id, station_data in all_stations.items():
        parent_id = station_data["parent_id"]
        
        # If parent_id is different from station_id and both are in the graph
        # This identifies child stations that have a different parent
        if parent_id and parent_id != station_id and G.has_node(parent_id) and G.has_node(station_id):
            parent_to_children[parent_id].append(station_id)
    
    # Load existing parent-child relationships from slim_stations/unique_stations.json
    try:
        with open("slim_stations/unique_stations.json", 'r') as f:
            existing_data = json.load(f)
            print(f"Loaded existing station data for parent-child relationships")
            
            # Create a mapping from station name to ID in our graph
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
                        # Add this relationship to our tracking dictionary
                        if child_id not in parent_to_children[parent_id]:
                            parent_to_children[parent_id].append(child_id)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load existing station data for parent-child relationships: {e}")
    
    # Add zero-weight edges between parent and child stations (both directions)
    # Zero weight means there's no time cost to transfer between them
    added_edges = 0
    for parent_id, children in parent_to_children.items():
        for child_id in children:
            # Parent to child edge
            G.add_edge(parent_id, child_id, weight=0, transfer=True)
            # Child to parent edge (for the return journey)
            G.add_edge(child_id, parent_id, weight=0, transfer=True)
            added_edges += 2  # Count both directions
    
    print(f"Added {added_edges} zero-weight transfer edges between parent and child stations")

def save_stations_to_slim_format(G, existing_data=None):
    """
    Save stations in a format compatible with slim_stations/unique_stations.json.
    
    Args:
        G: NetworkX graph object
        existing_data: Existing station data from slim_stations/unique_stations.json
    """
    # Create a list of stations in the format used by slim_stations
    stations_list = []
    
    # Create a lookup dictionary for existing parent-child relationships by name
    parent_to_children = {}
    if existing_data:
        for station in existing_data:
            name = station.get("name", "")
            children = station.get("child_stations", [])
            if name and children:
                parent_to_children[name] = children
    
    # Create lookup for all stations in the graph by name
    name_to_station = {}
    for node, data in G.nodes(data=True):
        station_name = data.get("name", "")
        if station_name:
            name_to_station[station_name] = data
    
    # Create stations list from all known stations
    for station_name, data in name_to_station.items():
        # Get child stations from existing data
        child_stations = parent_to_children.get(station_name, [])
        
        # Create station entry
        station_entry = {
            "name": station_name,
            "lat": data.get("lat", 0),
            "lon": data.get("lon", 0),
            "child_stations": child_stations
        }
        
        stations_list.append(station_entry)
    
    # Add any missing stations from the existing data
    # This ensures we don't lose any stations that might not be in the TFL API
    existing_names = set(name_to_station.keys())
    for station in existing_data:
        name = station.get("name", "")
        if name and name not in existing_names:
            # Copy the station data as is
            stations_list.append({
                "name": name,
                "lat": station.get("lat", 0),
                "lon": station.get("lon", 0),
                "child_stations": station.get("child_stations", [])
            })
    
    # Sort stations by name for consistency
    stations_list.sort(key=lambda x: x["name"])
    
    # Save to file
    slim_file = os.path.join(OUTPUT_DIR, "stations_slim_format.json")
    with open(slim_file, 'w') as f:
        json.dump(stations_list, f, indent=2)
    
    print(f"Slim format stations saved to {slim_file}")

def save_graph_to_json(G, existing_data=None):
    """
    Save NetworkX graph as JSON.
    
    NetworkX graphs can't be directly serialized to JSON, so we convert
    to a custom format first.
    
    Args:
        G: NetworkX graph object
        existing_data: Existing station data from slim_stations/unique_stations.json
    """
    ensure_output_dir()
    
    # Create a lookup dictionary for existing parent-child relationships
    parent_to_children = {}
    name_to_station = {}
    if existing_data:
        for station in existing_data:
            name = station.get("name", "")
            children = station.get("child_stations", [])
            if name:
                parent_to_children[name] = children
                name_to_station[name] = station
    
    # Convert NetworkX graph to a dictionary format
    # We use separate sections for nodes and edges
    graph_data = {
        "nodes": {},  # Dictionary of node ID -> node data
        "edges": []   # List of edge objects
    }
    
    # Add nodes to the dictionary
    # G.nodes(data=True) returns all nodes with their data
    for node, data in G.nodes(data=True):
        # Make sure we have station names as used in the existing project
        station_name = data.get("name", "")
        if not station_name:
            print(f"Warning: Station {node} has no name")
            continue
            
        # Get child stations from existing data
        child_stations = parent_to_children.get(station_name, [])
            
        # Store data with station name as the key (this is how the existing system expects it)
        # This ensures compatibility with the slim_stations/unique_stations.json format
        graph_data["nodes"][station_name] = {
            "id": node,
            "name": station_name,
            "lat": data.get("lat", 0),
            "lon": data.get("lon", 0),
            "zone": data.get("zone", ""),
            "modes": data.get("modes", []),
            "lines": data.get("lines", []),
            "child_stations": child_stations
        }
    
    # Add edges to the list
    # G.edges(data=True) returns all edges with their data
    for u, v, data in G.edges(data=True):
        # Get the station names for source and target
        u_data = G.nodes[u]
        v_data = G.nodes[v]
        
        source_name = u_data.get("name", "")
        target_name = v_data.get("name", "")
        
        if not source_name or not target_name:
            # Skip edges with missing station names
            continue
            
        edge = {
            "source": source_name,  # Source station name
            "target": target_name,  # Target station name
            "line": data.get("line", ""),
            "line_name": data.get("line_name", ""),
            "mode": data.get("mode", ""),
            "weight": data.get("weight", 1),
            "transfer": data.get("transfer", False)
        }
        graph_data["edges"].append(edge)
    
    # Make sure Waterloo & City line stations have the line in their lines attribute
    if "Bank Underground Station" in graph_data["nodes"] and "Waterloo Underground Station" in graph_data["nodes"]:
        # Add waterloo-city to the lines attribute if not already present
        if "waterloo-city" not in graph_data["nodes"]["Bank Underground Station"]["lines"]:
            graph_data["nodes"]["Bank Underground Station"]["lines"].append("waterloo-city")
            print("Added waterloo-city line to Bank Underground Station")
            
        if "waterloo-city" not in graph_data["nodes"]["Waterloo Underground Station"]["lines"]:
            graph_data["nodes"]["Waterloo Underground Station"]["lines"].append("waterloo-city")
            print("Added waterloo-city line to Waterloo Underground Station")
            
        # Make sure there's an edge between them for the Waterloo & City line
        waterloo_city_edge_exists = False
        for edge in graph_data["edges"]:
            if (edge["source"] == "Bank Underground Station" and edge["target"] == "Waterloo Underground Station" and
                edge["line"] == "waterloo-city"):
                waterloo_city_edge_exists = True
                break
        
        if not waterloo_city_edge_exists:
            # Add the Waterloo & City line edge in both directions
            graph_data["edges"].append({
                "source": "Bank Underground Station",
                "target": "Waterloo Underground Station",
                "line": "waterloo-city",
                "line_name": "Waterloo & City",
                "mode": "tube",
                "weight": 1,
                "transfer": False
            })
            graph_data["edges"].append({
                "source": "Waterloo Underground Station",
                "target": "Bank Underground Station",
                "line": "waterloo-city",
                "line_name": "Waterloo & City",
                "mode": "tube",
                "weight": 1,
                "transfer": False
            })
            print("Added Waterloo & City line edge between Bank and Waterloo")
            
    # Add any stations from existing_data that are not in the graph
    if existing_data:
        # Track how many stations were added
        added_stations = 0
        added_edges = 0
        
        # Create a set of station names already in the graph
        existing_names = set(graph_data["nodes"].keys())
        
        # Add missing parent stations
        for station in existing_data:
            name = station.get("name", "")
            if name and name not in existing_names:
                # Add the station to the graph
                graph_data["nodes"][name] = {
                    "id": f"from_slim_{name.replace(' ', '_')}",  # Create a synthetic ID
                    "name": name,
                    "lat": station.get("lat", 0),
                    "lon": station.get("lon", 0),
                    "zone": "",  # We don't have this data
                    "modes": [],  # We don't have this data
                    "lines": [],  # We don't have this data
                    "child_stations": station.get("child_stations", [])
                }
                added_stations += 1
                
                # Connect to a nearby station if possible
                # This helps ensure the graph is connected
                if len(graph_data["nodes"]) > 1:
                    # Find a station with a similar name if possible
                    connected = False
                    for other_name in existing_names:
                        # Simple name similarity - check if one contains the other
                        if name in other_name or other_name in name:
                            # Add edges in both directions with high weight (10) to indicate it's a less reliable connection
                            graph_data["edges"].append({
                                "source": name,
                                "target": other_name,
                                "line": "",
                                "line_name": "Unknown",
                                "mode": "",
                                "weight": 10,
                                "transfer": True
                            })
                            graph_data["edges"].append({
                                "target": name,
                                "source": other_name,
                                "line": "",
                                "line_name": "Unknown",
                                "mode": "",
                                "weight": 10,
                                "transfer": True
                            })
                            added_edges += 2
                            connected = True
                            break
                
        print(f"Added {added_stations} stations and {added_edges} edges from existing data")
    
    # Save to file
    with open(GRAPH_FILE, 'w') as f:
        json.dump(graph_data, f, indent=2)
    
    print(f"Graph saved to {GRAPH_FILE}")

    # Also save in the slim format
    save_stations_to_slim_format(G, existing_data)

def analyze_tfl_response_structure(line_data):
    """
    Analyze the structure of TFL API response data to understand its format.
    
    This is a debugging function to help understand the API response structure.
    
    Args:
        line_data: Dictionary with line_id as key and sequence data as value
    """
    print("\n=== TFL API Response Structure Analysis ===")
    
    for line_id, data in line_data.items():
        print(f"\nLine: {data.get('lineName', line_id)} ({line_id})")
        
        # Check if lineStrings exists
        line_strings = data.get("lineStrings", [])
        print(f"  lineStrings: {type(line_strings)} with {len(line_strings)} items")
        
        # Analyze the structure of each lineString
        for i, line_string in enumerate(line_strings):
            if i >= 2:  # Limit to first 2 for brevity
                print(f"  ... {len(line_strings) - 2} more branches ...")
                break
                
            print(f"  Branch {i+1}: {type(line_string)} with {len(line_string) if isinstance(line_string, (list, tuple)) else 'N/A'} items")
            
            # Check the first few coordinates
            if isinstance(line_string, (list, tuple)) and len(line_string) > 0:
                print(f"    First coordinate: {line_string[0]} (type: {type(line_string[0])})")
                if isinstance(line_string[0], (list, tuple)):
                    print(f"    Coordinate format: {len(line_string[0])} values {type(line_string[0][0]) if len(line_string[0]) > 0 else 'empty'}")
                elif isinstance(line_string[0], str):
                    # If it's a string, it might be a GeoJSON format
                    print(f"    Appears to be GeoJSON or other string format")
                    # Check if we need to parse the string
                    if line_string[0].startswith('[') or line_string[0].startswith('{'):
                        print(f"    Appears to be JSON string that needs parsing")
        
        # Check stations
        stations = data.get("stations", [])
        print(f"  Stations: {len(stations)} items")
        if stations:
            # Sample the first station
            first_station = stations[0]
            print(f"  Sample station keys: {', '.join(sorted(first_station.keys()))}")
            print(f"  Sample station ID: {first_station.get('stationId', 'N/A')}")
            print(f"  Sample station name: {first_station.get('name', 'N/A')}")
            print(f"  Sample station coordinates: lat={first_station.get('lat', 'N/A')}, lon={first_station.get('lon', 'N/A')}")
    
    print("\n=== End of Analysis ===\n")

def main():
    """Main function to build and save the network graph."""
    print("Building London transport network graph...")
    
    # Try to load raw data from file if available
    line_data = load_raw_data()
    
    # If not available, fetch from API
    if not line_data:
        print("No cached data found. Fetching from TFL API...")
        line_data = fetch_all_line_data()
        save_raw_data(line_data)  # Cache the data for future runs
    else:
        print("Using cached TFL data.")
    
    # Make sure waterloo-city line is included
    if "waterloo-city" not in line_data:
        print("Warning: waterloo-city line not found in data. Will add manually later.")
    else:
        print("waterloo-city line found in data.")
        # Check if it has stations
        waterloo_city_stations = line_data["waterloo-city"].get("stations", [])
        print(f"  waterloo-city has {len(waterloo_city_stations)} stations")
        # Print the station names
        for station in waterloo_city_stations:
            station_name = station.get("name", "Unknown")
            station_id = station.get("stationId", "Unknown")
            print(f"  - {station_name} (ID: {station_id})")
    
    # Load existing station data to preserve parent-child relationships
    existing_data = None
    try:
        with open("slim_stations/unique_stations.json", 'r') as f:
            existing_data = json.load(f)
            print(f"Loaded existing station data with {len(existing_data)} stations")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load existing station data: {e}")
    
    # Print a sample of parent-child relationships from existing data
    if existing_data:
        parent_child_count = 0
        print("\nParent-child relationships from existing data:")
        for station in existing_data:
            if station.get("child_stations", []):
                parent_child_count += 1
                if parent_child_count <= 5:  # Print just a few examples
                    print(f"  {station['name']} -> {', '.join(station['child_stations'])}")
        print(f"  Found {parent_child_count} parent stations with children\n")
    
    # Analyze the TFL response structure to understand the data format
    analyze_tfl_response_structure(line_data)
    
    # Build graph from line data
    print("Building graph from line data...")
    G = build_graph_from_data(line_data)
    
    # Print some graph statistics
    print(f"Graph built with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    
    # Save graph to JSON
    print("Saving graph to JSON...")
    save_graph_to_json(G, existing_data)
    
    # Verify that the parent-child relationships are preserved
    verify_parent_child_edges("network_data/networkx_graph.json")
    
    print("Done!")

def verify_parent_child_edges(graph_file):
    """
    Verify that parent-child relationships from existing data are preserved in the graph.
    
    Args:
        graph_file: Path to the graph JSON file
    """
    # Load the graph from file
    with open(graph_file, 'r') as f:
        graph_data = json.load(f)
    
    # Count transfer edges
    transfer_edges = [(e["source"], e["target"]) for e in graph_data["edges"] if e.get("transfer", False)]
    
    print(f"\nVerifying parent-child edges in graph:")
    print(f"  Found {len(transfer_edges)} transfer edges in graph")
    
    # Print some examples of transfer edges
    if transfer_edges:
        print("  Examples of transfer edges:")
        for source, target in transfer_edges[:5]:
            print(f"    {source} -> {target}")
    
    # Load existing data to verify against
    try:
        with open("slim_stations/unique_stations.json", 'r') as f:
            existing_data = json.load(f)
        
        # Count expected parent-child edges
        expected_edges = []
        for station in existing_data:
            if station.get("child_stations"):
                parent = station["name"]
                for child in station["child_stations"]:
                    expected_edges.append((parent, child))
                    expected_edges.append((child, parent))  # Both directions
        
        print(f"  Expected {len(expected_edges)} transfer edges from existing data")
        
        # Check if all expected edges are in the graph
        missing_edges = [e for e in expected_edges if e not in transfer_edges]
        if missing_edges:
            print(f"  Warning: Missing {len(missing_edges)} transfer edges in graph:")
            for source, target in missing_edges[:5]:
                print(f"    {source} -> {target}")
                
            # Add a fix for this issue
            print("\nFixing missing transfer edges:")
            
            # Get a list of all nodes in the graph
            # Use the keys from the "nodes" dictionary in graph_data
            nodes_in_graph = set(graph_data["nodes"].keys())
            # Print stats about nodes
            print(f"  Total nodes in graph: {len(nodes_in_graph)}")
            
            added_edges = 0
            missing_nodes = set()
            
            for source, target in missing_edges:
                if source in nodes_in_graph and target in nodes_in_graph:
                    # Add the missing edge to the graph
                    edge = {
                        "source": source,
                        "target": target,
                        "line": "",
                        "line_name": "",
                        "mode": "",
                        "weight": 0,
                        "transfer": True
                    }
                    graph_data["edges"].append(edge)
                    added_edges += 1
                else:
                    # Track missing nodes
                    if source not in nodes_in_graph:
                        missing_nodes.add(source)
                    if target not in nodes_in_graph:
                        missing_nodes.add(target)
            
            # Print stats about missing nodes
            print(f"  Missing nodes that prevented edge creation: {len(missing_nodes)}")
            if missing_nodes:
                print("  Examples of missing nodes:")
                for node in list(missing_nodes)[:5]:
                    print(f"    {node}")
                    
                # Find similar node names that might be causing the mismatch
                for node in list(missing_nodes)[:5]:
                    similar_nodes = [n for n in nodes_in_graph if node in n or n in node]
                    if similar_nodes:
                        print(f"    Similar to '{node}': {', '.join(similar_nodes[:3])}")
            
            # Add missing nodes from existing data
            added_nodes = 0
            for station in existing_data:
                name = station["name"]
                if name in missing_nodes and name not in graph_data["nodes"]:
                    # Add the missing node to the graph
                    graph_data["nodes"][name] = {
                        "id": f"missing_{len(graph_data['nodes'])}",
                        "name": name,
                        "lat": station["lat"],
                        "lon": station["lon"],
                        "zone": "",
                        "modes": [],
                        "lines": [],
                        "child_stations": station.get("child_stations", [])
                    }
                    added_nodes += 1
                    nodes_in_graph.add(name)
            
            print(f"  Added {added_nodes} missing nodes to graph")
            
            # Try adding edges again with the new nodes
            additional_edges = 0
            if added_nodes > 0:
                for source, target in missing_edges:
                    if source in nodes_in_graph and target in nodes_in_graph:
                        # Check if this edge already exists
                        edge_exists = False
                        for e in graph_data["edges"]:
                            if e["source"] == source and e["target"] == target:
                                edge_exists = True
                                break
                                
                        if not edge_exists:
                            # Add the missing edge to the graph
                            edge = {
                                "source": source,
                                "target": target,
                                "line": "",
                                "line_name": "",
                                "mode": "",
                                "weight": 0,
                                "transfer": True
                            }
                            graph_data["edges"].append(edge)
                            additional_edges += 1
            
            print(f"  Added {additional_edges} more transfer edges after node additions")
            
            # Now add all the parent-child edges from the existing data
            extra_edges = 0
            for station in existing_data:
                parent = station["name"]
                children = station.get("child_stations", [])
                
                if not children:
                    continue
                    
                if parent in nodes_in_graph:
                    for child in children:
                        if child in nodes_in_graph:
                            # Check if this edge already exists
                            parent_child_exists = False
                            child_parent_exists = False
                            for e in graph_data["edges"]:
                                if e["source"] == parent and e["target"] == child:
                                    parent_child_exists = True
                                if e["source"] == child and e["target"] == parent:
                                    child_parent_exists = True
                                if parent_child_exists and child_parent_exists:
                                    break
                                    
                            # Add parent->child edge if needed
                            if not parent_child_exists:
                                edge = {
                                    "source": parent,
                                    "target": child,
                                    "line": "",
                                    "line_name": "",
                                    "mode": "",
                                    "weight": 0,
                                    "transfer": True
                                }
                                graph_data["edges"].append(edge)
                                extra_edges += 1
                                
                            # Add child->parent edge if needed
                            if not child_parent_exists:
                                edge = {
                                    "source": child,
                                    "target": parent,
                                    "line": "",
                                    "line_name": "",
                                    "mode": "",
                                    "weight": 0,
                                    "transfer": True
                                }
                                graph_data["edges"].append(edge)
                                extra_edges += 1
            
            print(f"  Added {extra_edges} edges from direct parent-child relationships")
            total_added = added_edges + additional_edges + extra_edges
            print(f"  Total edges added: {total_added}")
            
            # Save the updated graph
            with open(graph_file, 'w') as f:
                json.dump(graph_data, f, indent=2)
            
            print(f"  Saved updated graph to {graph_file}")
        else:
            print("  All expected transfer edges are in the graph")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"  Warning: Could not verify against existing data: {e}")

# This is the entry point of the script
# It only runs if this script is executed directly (not imported)
if __name__ == "__main__":
    main() 