"""
This script is the optimized version of the program.
It uses a convex hull to filter evenly distributed users. And using a centroid containing 70% of users filter outliers.
It then calculates the travel time to each potential meeting station and selects the one with the lowest total travel time.
"""

import requests
import argparse
import os
import sys
import math
import json
from difflib import get_close_matches
from fuzzywuzzy import fuzz
from scipy.spatial import ConvexHull
import numpy as np
import networkx as nx
import heapq

# --- Configuration ---
# Base URL for the TfL API (only for journey planning)
TFL_API_BASE_URL = "https://api.tfl.gov.uk/Journey/JourneyResults/"



# --- Path to NetworkX Graph Data ---
GRAPH_PATH = "networkx_graph/create_graph/output/final_networkx_graph.json"

# --- Station Filtering Functions ---

def create_convex_hull(points):
    """
    Creates a convex hull from a set of points and returns the hull points.
    
    Args:
        points (list): List of [lat, lon] coordinates
        
    Returns:
        hull_points (np.array): Array of coordinates forming the convex hull
        hull (ConvexHull): The hull object for additional calculations
    """
    # Convert points to numpy array for ConvexHull calculation
    points_array = np.array(points)
    
    # Create the convex hull
    hull = ConvexHull(points_array)
    
    # Get the points that form the hull
    hull_points = points_array[hull.vertices]
    
    return hull_points, hull

def point_in_hull(point, hull_points, hull):
    """
    Checks if a point lies within the convex hull.
    
    Args:
        point (list): [lat, lon] coordinates to check
        hull_points (np.array): Array of coordinates forming the convex hull
        hull (ConvexHull): The hull object for calculations
        
    Returns:
        bool: True if point is inside hull, False otherwise
    """
    # Add a small buffer to the hull (0.5% expansion)
    centroid = np.mean(hull_points, axis=0)
    hull_points_buffered = np.array([
        p + (p - centroid) * 0.005 for p in hull_points
    ])
    
    # Create new hull with buffered points
    hull_buffered = ConvexHull(hull_points_buffered)
    
    # Test if point is in buffered hull
    new_points = np.vstack((hull_points_buffered, point))
    new_hull = ConvexHull(new_points)
    
    # If the number of vertices is the same, the point was inside
    return len(new_hull.vertices) == len(hull_buffered.vertices)

def filter_stations_by_convex_hull(stations, start_locations):
    """
    Filters stations that lie within the convex hull created by start locations.
    
    Args:
        stations (list): List of station dictionaries
        start_locations (list): List of [lat, lon] coordinates for start points
        
    Returns:
        list: Filtered list of stations within the hull
    """
    # Create convex hull from start locations
    hull_points, hull = create_convex_hull(start_locations)
    
    # Filter stations
    filtered_stations = []
    for station in stations:
        station_point = np.array([station['lat'], station['lon']])
        if point_in_hull(station_point, hull_points, hull):
            filtered_stations.append(station)
            
    print(f"Found {len(filtered_stations)} stations within convex hull.")
    return filtered_stations

def calculate_centroid_with_coverage(locations, coverage_percent=0.7):
    """
    Calculates the centroid and minimum radius needed to cover the specified percentage of locations.
    
    Args:
        locations (list): List of [lat, lon] coordinates
        coverage_percent (float): Percentage of points to cover (0.0 to 1.0)
        
    Returns:
        tuple: (centroid_lat, centroid_lon, radius_km)
    """
    if not locations:
        return None, None, None
    
    # Calculate centroid
    centroid_lat = sum(loc[0] for loc in locations) / len(locations)
    centroid_lon = sum(loc[1] for loc in locations) / len(locations)
    
    # Calculate distances from centroid to all points
    distances = []
    for lat, lon in locations:
        dist = haversine_distance(centroid_lat, centroid_lon, lat, lon)
        distances.append(dist)
    
    # Sort distances and find the radius needed for coverage
    distances.sort()
    coverage_index = int(len(distances) * coverage_percent)
    radius_km = distances[coverage_index - 1]  # -1 because index is 0-based
    
    return centroid_lat, centroid_lon, radius_km

def point_in_ellipse(point_lat, point_lon, focus1_lat, focus1_lon, focus2_lat, focus2_lon, major_axis):
    """
    Determines if a point lies within an ellipse defined by two foci.
    Uses the standard ellipse definition: sum of distances to foci <= major axis
    
    Important geometric note:
    - If major_axis equals the distance between foci (2c), the ellipse collapses to a line
    - We use major_axis = 1.2 * distance to create a reasonable search area
    - This works better with the centroid filtering stage by allowing more initial candidates
    
    Args:
        point_lat, point_lon: Coordinates of the point to check
        focus1_lat, focus1_lon: Coordinates of the first focus (starting point)
        focus2_lat, focus2_lon: Coordinates of the second focus (starting point)
        major_axis: The major axis length of the ellipse (in km)
        
    Returns:
        bool: True if the point is inside or on the ellipse, False otherwise
    """
    # Calculate distances from point to each focus
    dist1 = haversine_distance(point_lat, point_lon, focus1_lat, focus1_lon)
    dist2 = haversine_distance(point_lat, point_lon, focus2_lat, focus2_lon)
    
    # Allow for small numerical error (0.5% tolerance)
    # Increased from 0.1% to 0.5% to account for Earth's curvature effects
    tolerance = major_axis * 0.005
    
    # Check if sum of distances is less than or equal to major axis (with tolerance)
    # This is the definition of an ellipse: sum of distances to foci is constant
    if (dist1 + dist2) > (major_axis + tolerance):
        return False
        
    return True

def filter_stations_optimized(all_stations, people_data):
    """
    Two-step filtering process:
    1. If more than 2 people: Filter stations within convex hull of start locations
       If 2 people: Filter stations within an elliptical area focused around the midpoint
    2. Further filter based on centroid circle covering 70% of start locations
    
    Args:
        all_stations (list): List of all station dictionaries
        people_data (list): List of dictionaries containing people's start locations
        
    Returns:
        list: Filtered list of stations
    """
    # Extract start locations
    start_locations = [(p['start_station_lat'], p['start_station_lon']) 
                      for p in people_data]
    
    # Step 1: Initial Filtering
    print("\nStep 1: Filtering stations...")
    if len(start_locations) > 2:
        print("Using convex hull method for filtering (3+ people)")
        hull_filtered = filter_stations_by_convex_hull(all_stations, start_locations)
    else:
        print("Using elliptical boundary method for filtering (2 people)")
        # Get the two points
        point1_lat, point1_lon = start_locations[0]
        point2_lat, point2_lon = start_locations[1]
        
        # Calculate direct distance between points
        direct_distance = haversine_distance(
            point1_lat, point1_lon,
            point2_lat, point2_lon
        )
        
        # Use 1.2 * distance between stations as the major axis
        # This creates a wider ellipse than using just the direct distance,
        # giving a more reasonable search area that works better with the centroid filtering
        major_axis = direct_distance * 1.2
        
        # Filter stations within the ellipse
        hull_filtered = []
        for station in all_stations:
            if point_in_ellipse(
                station['lat'], station['lon'],
                point1_lat, point1_lon,
                point2_lat, point2_lon,
                major_axis
            ):
                hull_filtered.append(station)
                
        print(f"Found {len(hull_filtered)} stations within elliptical boundary")
        print(f"Direct distance between points: {direct_distance:.2f}km")
        print(f"Ellipse major axis: {major_axis:.2f}km (1.2 * direct distance)")
    
    # Step 2: Centroid Circle Filtering
    print("\nStep 2: Further filtering using centroid circle...")
    
    # For 2 people, calculate the centroid as the midpoint between stations
    if len(start_locations) == 2:
        centroid_lat = (start_locations[0][0] + start_locations[1][0]) / 2
        centroid_lon = (start_locations[0][1] + start_locations[1][1]) / 2
        # Use 70% of the distance to center as the radius
        radius_km = (direct_distance / 2) * 0.7
        print(f"Using midpoint as centroid and {radius_km:.2f}km as radius (70% of distance to center)")
    else:
        # For 3+ people, use the original coverage-based calculation
        centroid_lat, centroid_lon, radius_km = calculate_centroid_with_coverage(
            start_locations, coverage_percent=0.7
        )
    
    final_filtered = []
    for station in hull_filtered:
        if is_within_radius(centroid_lat, centroid_lon, radius_km,
                          station['lat'], station['lon']):
            final_filtered.append(station)
            
    print(f"Final filtered count: {len(final_filtered)} stations")
    return final_filtered

# --- Helper Functions ---

def load_networkx_graph_and_station_data():
    """
    Loads the NetworkX graph from the JSON file and extracts station data from nodes.

    Returns:
        tuple: (nx.MultiDiGraph, dict) containing the loaded graph and a
               station_data_lookup dictionary (name -> attributes), or (None, None) on failure.
    """
    try:
        # Use the globally defined GRAPH_PATH
        with open(GRAPH_PATH, 'r') as f:
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

        print(f"Loaded NetworkX graph from '{GRAPH_PATH}' with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
        print(f"Created station lookup for {len(station_data_lookup)} stations from graph nodes.")
        return G, station_data_lookup
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading or parsing NetworkX graph JSON from {GRAPH_PATH}: {e}", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred during graph construction: {e}", file=sys.stderr)
        return None, None

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points
    on the Earth (specified in decimal degrees) using Haversine formula.

    Args:
        lat1, lon1: Latitude and longitude of point 1 (in degrees).
        lat2, lon2: Latitude and longitude of point 2 (in degrees).

    Returns:
        float: Distance in kilometers.
    """
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def is_within_radius(centroid_lat, centroid_lon, radius_km, station_lat, station_lon):
    """
    Checks if a station is within a given radius from the centroid.

    Args:
        centroid_lat, centroid_lon: Coordinates of the center point.
        radius_km: The maximum distance allowed (in kilometers).
        station_lat, station_lon: Coordinates of the station to check.

    Returns:
        bool: True if the station is within the radius, False otherwise.
    """
    if None in [centroid_lat, centroid_lon, station_lat, station_lon]:
        return False
    distance = haversine_distance(centroid_lat, centroid_lon, station_lat, station_lon)
    return distance <= radius_km

def find_closest_station_match(station_name, station_data_lookup):
    """
    Finds the closest matching station name present as a node in the graph data.
    Uses exact matching first, then normalized names, and finally fuzzy matching.
    Presents user with options when multiple close matches are found.

    Args:
        station_name (str): The user-provided station name.
        station_data_lookup (dict): Dictionary mapping station names (from graph nodes)
                                   to their attribute dictionaries.

    Returns:
        dict: The station attribute data if found, None otherwise.
    """
    # Normalize the user input
    normalized_input_raw = station_name.lower().strip()

    # Try exact case-insensitive match first against graph node names (keys of the lookup)
    for node_name, node_attributes in station_data_lookup.items():
        if node_name.lower() == normalized_input_raw:
            print(f"Exact match found: '{node_name}'")
            # Return the attributes dictionary for the matched node
            # Check if 'hub_name' is present, otherwise use the matched node_name
            if 'hub_name' in node_attributes:
                return node_attributes
            else:
                # If hub_name is missing but we matched, add the key as the name
                node_attributes['hub_name'] = node_name 
            return node_attributes

    # If no exact match, normalize the input name using the same logic as before
    def normalize_name(name):
        """Helper function to normalize station names"""
        if not name:
            return ""

        name = name.lower().strip()

        # Handle common abbreviations before other normalizations
        common_abbrevs = {
            'st ': 'street ',
            'st.': 'street',
            'rd ': 'road ',
            'rd.': 'road',
            'ave ': 'avenue ',
            'ave.': 'avenue',
            'ln ': 'lane ',
            'ln.': 'lane',
            'pk ': 'park ',
            'pk.': 'park',
            'gdns ': 'gardens ',
            'gdns.': 'gardens',
            'xing ': 'crossing ',
            'xing.': 'crossing',
            'stn ': 'station ',
            'stn.': 'station'
        }

        # Add a space at the end to help match abbreviations at the end of the name
        name = name + ' '
        for abbrev, full in common_abbrevs.items():
            name = name.replace(abbrev, full)
        name = name.strip()  # Remove the extra space we added

        # First handle special patterns that include parentheses
        patterns_with_parens = [
            ' (h and c line)',
            ' (handc line)',
            ' (h&c line)',
            ' (central)',
            ' (dist and picc line)',
            ' (distandpicc line)',
            ' (dist&picc line)',
            ' (for excel)',
            ' (london)',
            ' (berks)',
            ' (for maritime greenwich)',
            ' (for excel)'
        ]
        for pattern in patterns_with_parens:
            name = name.replace(pattern, '')

        # Then standardize remaining special characters
        name = name.replace(" & ", " and ")
        name = name.replace("&", "and")
        name = name.replace("-", " ")
        name = name.replace("'", "")
        name = name.replace('"', '')

        # Now handle any remaining parentheses
        name = name.replace("(", " ")
        name = name.replace(")", " ")

        # Clean spaces
        name = ' '.join(name.split())

        # Remove common prefixes
        prefixes = ['london ']
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]

        # Remove common suffixes
        suffixes = [
            ' underground station',
            ' overground station',
            ' dlr station',
            ' rail station',
            ' station',
            ' underground',
            ' overground',
            ' dlr'
        ]
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]

        # Remove any remaining common patterns
        patterns = [
            ' ell ',
            ' rail ',
            ' tube '
        ]
        for pattern in patterns:
            name = name.replace(pattern, "")

        return ' '.join(name.split())

    normalized_input_processed = normalize_name(normalized_input_raw)

    # Try fuzzy matching against normalized graph node names
    matches = []
    # Iterate through the graph node names and their attributes
    for node_name, node_attributes in station_data_lookup.items():
        # Normalize the graph node name for comparison
        station_normalized = normalize_name(node_name)
        # Calculate fuzzy ratio between normalized input and normalized node name
        ratio = fuzz.ratio(normalized_input_processed, station_normalized)

        # Collect matches above a threshold (e.g., 75)
        if ratio > 75:
            # Store the attributes, ratio, and the original node name
            matches.append((node_attributes, ratio, node_name))

    if not matches:
        # Single consolidated error message
        print(f"\n Error: Station '{station_name}' not found or doesn't closely match any station in the graph data.")
        print(" Please check the spelling and ensure it's a relevant station name as listed in the network graph.")
        print(" Tip: You can use common abbreviations like 'st' for 'street', 'rd' for 'road', etc.")
        return None

    # Sort matches by ratio in descending order
    matches.sort(key=lambda x: x[1], reverse=True)

    # If we have a perfect match (ratio 100), use it
    if matches[0][1] == 100:
        print(f"Close match found: '{matches[0][2]}'")
        # Return the attributes of the best match
        return matches[0][0]

    # If we have multiple close matches, show top 5 options
    print(f"\nMultiple potential matches found for '{station_name}'. Please select the correct station:")
    # Display the original node name found in the graph
    for i, (attributes, ratio, matched_name) in enumerate(matches[:5], 1):
        print(f"{i}. {matched_name} (similarity: {ratio}%)")

    while True:
        try:
            choice = input("\nEnter the number of your station (or 0 to try a different name): ")
            if choice == '0':
                return None
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(matches[:5]):
                # Return the attributes dictionary for the chosen station
                return matches[choice_idx][0]
            print("Invalid selection. Please enter a number between 0 and", min(5, len(matches)))
        except ValueError:
            print("Invalid input. Please enter a number.")

def get_api_key():
    """
    Retrieves the TfL API key from environment variable or command line.
    """
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get('TFL_API_KEY')
    if api_key:
        print("Using TfL API key from environment variable.")
        return api_key
    return None

def get_travel_time(start_naptan_id, end_naptan_id, api_key):
    """
    Calls the TfL Journey Planner API to get the travel time between two stations using Naptan IDs.

    Args:
        start_naptan_id (str): Naptan ID of the starting station.
        end_naptan_id (str): Naptan ID of the ending station.
        api_key (str): The TfL API key.

    Returns:
        int: Travel time in minutes, or None if the journey cannot be found.
    """
    # Check if start and end IDs are the same
    if start_naptan_id == end_naptan_id:
        print("  Start and end stations are the same (by Naptan ID) - no journey needed")
        return 0

    # Validate Naptan IDs are present
    if not start_naptan_id or not end_naptan_id:
        print(f"  Error: Missing Naptan ID for TfL API call (Start: {start_naptan_id}, End: {end_naptan_id})")
        return None

    # Construct the URL using Naptan IDs
    url = f"{TFL_API_BASE_URL}{start_naptan_id}/to/{end_naptan_id}"

    params = {
        'app_key': api_key,
        'timeIs': 'Departing',
        'journeyPreference': 'leasttime'
    }

    try:
        print(f"  Querying TfL API for journey ({start_naptan_id} -> {end_naptan_id})...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
        journey_data = response.json()

        # Check if the 'journeys' key exists and is not empty
        if not journey_data.get('journeys'):
            # Provide more context in the warning
            print(f"  Warning: No journey found between {start_naptan_id} and {end_naptan_id}.")
            return None

        # Safely access the duration from the first journey
        duration = journey_data['journeys'][0].get('duration')
        if duration is not None:
            print(f"  Found journey duration: {duration} minutes")
        else:
            # Handle case where journey exists but duration is missing
            print(f"  Warning: Journey found between {start_naptan_id} and {end_naptan_id}, but duration is missing.")
        return duration

    except requests.exceptions.RequestException as e:
        # Handle potential network errors, timeouts, etc.
        error_message = f"Error during TfL API request: {e}"
        # Attempt to include TfL error message if response was received
        try:
            if response:
                error_details = response.json()
                if 'message' in error_details:
                    error_message += f" - TfL Message: {error_details['message']}"
        except Exception:
             pass # Ignore if response isn't available or not JSON
        print(f"  {error_message}", file=sys.stderr)
        return None
    except Exception as e:
        # Catch any other unexpected errors (e.g., JSON decoding issues if raise_for_status didn't catch)
        print(f"  An unexpected error occurred processing TfL response: {e}", file=sys.stderr)
        return None

def parse_arguments():
    """
    Parses command-line arguments for API key.
    """
    parser = argparse.ArgumentParser(
        description="Find the most convenient meeting location in London using optimized station filtering."
    )
    parser.add_argument(
        "--api-key",
        help="Your TfL API key. Alternatively, set the TFL_API_KEY environment variable."
    )
    args = parser.parse_args()
    
    final_api_key = get_api_key()
    if not final_api_key and args.api_key:
        final_api_key = args.api_key
    if not final_api_key:
        parser.error("TfL API key is required. Provide it via --api-key or the TFL_API_KEY environment variable.")
    
    args.api_key = final_api_key
    return args

def dijkstra_with_transfer_penalty(graph, start_station_name, end_station_name):
    """
    Calculates the shortest path travel time using a custom Dijkstra algorithm
    that incorporates walk time and applies a 5-minute penalty for line/mode changes
    during the search. WALK TIME IS ADDED EXTERNALLY.

    Args:
        graph (nx.MultiDiGraph): The loaded NetworkX graph.
        start_station_name (str): Name of the starting station.
        end_station_name (str): Name of the ending (meeting) station.
        # walk_time (int): REMOVED - Time to walk TO the start station is added externally.

    Returns:
        float: Minimum calculated travel time in minutes (excluding initial walk time),
               or float('inf') if no path found.
    """
    # Ensure start/end stations exist in the graph before starting
    if start_station_name not in graph:
        print(f"    Error: Start station '{start_station_name}' not found in the graph.")
        return float('inf')
    if end_station_name not in graph:
        print(f"    Error: End station '{end_station_name}' not found in the graph.")
        return float('inf')

    # If start and end are the same, return 0 time immediately
    if start_station_name == end_station_name:
        print(f"    Start and end stations are the same ('{start_station_name}'), path time is 0.")
        return 0.0

    # Priority queue stores tuples: (current_path_time, current_station_name, line_key_taken_to_reach_station)
    # Initialize time to 0.0 as walk time is handled externally.
    pq = [(0.0, start_station_name, None)]

    # Distances dictionary stores the minimum time found so far to reach a station VIA a specific line key
    # Key: (station_name, line_key), Value: time
    # Initialize start distance to 0.0
    distances = {(start_station_name, None): 0.0}

    # Keep track of the minimum time found to reach the end_station_name, regardless of the line taken
    min_time_to_destination = float('inf')

    while pq:
        # Get the element with the smallest time
        current_time, current_station, previous_line_key = heapq.heappop(pq)

        # If we found a shorter path already to this state (station via previous_line_key), skip
        if current_time > distances.get((current_station, previous_line_key), float('inf')):
            continue

        # If we have reached the destination station, update the overall minimum time found so far
        if current_station == end_station_name:
            min_time_to_destination = min(min_time_to_destination, current_time)
            # Optimization: If the current_time is already greater than the best found time
            # for the destination, we can potentially prune this path (though standard Dijkstra
            # usually explores fully). Let's keep it simple and explore fully for now.
            # continue # Optional optimization

        # If the current path time exceeds the best known time to the destination, we can prune it
        # (A* - like optimization, assuming non-negative edge weights)
        if current_time > min_time_to_destination:
             continue

        # Explore neighbors
        if current_station not in graph:
            print(f"    Warning: Station '{current_station}' not in graph nodes during Dijkstra search.")
            continue

        for neighbor_station in graph.neighbors(current_station):
            # Get all edges between current_station and neighbor_station
            edge_datas = graph.get_edge_data(current_station, neighbor_station)
            if not edge_datas:
                continue # Should not happen with graph.neighbors, but safeguard

            for edge_key, edge_data in edge_datas.items():
                # Use 'weight' instead of 'duration'
                edge_travel_time = edge_data.get('weight', float('inf')) 
                current_edge_line_key = edge_key # <-- Correct: The edge_index *is* the line key (e.g., 'circle')

                # Check using edge_travel_time
                if edge_travel_time == float('inf') or current_edge_line_key is None:
                    continue # Skip edges without weight or a valid line key (edge_index)

                # Calculate penalty
                penalty = 0.0
                # Apply penalty ONLY if it's not the first step (previous_line_key exists)
                # AND the line key is different from the previous one
                # AND neither the previous line nor the current line is a 'transfer' edge.
                if (previous_line_key is not None and 
                    current_edge_line_key != previous_line_key and
                    previous_line_key != 'transfer' and 
                    current_edge_line_key != 'transfer'):
                    penalty = 5.0 
                    # Optional: print penalty application for debugging
                    # print(f"        +5 min penalty: Changed from '{previous_line_key}' to '{current_edge_line_key}' arriving at {neighbor_station}")

                # Calculate the time to reach the neighbor via THIS specific edge using edge_travel_time
                new_time = current_time + edge_travel_time + penalty 

                # Relaxation step: If this path is shorter than any known path to reach
                # the neighbor_station VIA the current_edge_line_key, update it.
                if new_time < distances.get((neighbor_station, current_edge_line_key), float('inf')):
                    distances[(neighbor_station, current_edge_line_key)] = new_time
                    heapq.heappush(pq, (new_time, neighbor_station, current_edge_line_key))

    # After the loop, min_time_to_destination holds the minimum time to reach the end station
    if min_time_to_destination == float('inf'):
        print(f"    No path found from {start_station_name} to {end_station_name} using custom Dijkstra.")
    else:
        print(f"    Calculated Dijkstra path cost: {min_time_to_destination:.2f} mins (incl. penalties)")

    return min_time_to_destination

# --- Functions Extracted from main() ---

def get_user_inputs(station_data_lookup):
    """
    Gathers station names and walk times from the user.

    Args:
        station_data_lookup (dict): Dictionary mapping station names to attributes.

    Returns:
        list: List of dictionaries, each representing a person's data,
              or an empty list if insufficient input is provided.
    """
    people_data = []
    print("\nPlease enter the details for each person.")
    print("Enter the name of their NEAREST Tube/Overground/DLR/Rail station.")
    print("Type 'done' or leave blank when finished.")

    person_count = 1
    while True:
        print(f"\n--- Person {person_count} ---")
        station_name = input(f"Nearest Station Name (or 'done'): ").strip()

        if not station_name or station_name.lower() == 'done':
            if len(people_data) >= 2:
                break
            else:
                print("Please enter details for at least two people.")
                continue

        found_station_attributes = find_closest_station_match(station_name, station_data_lookup)
        if not found_station_attributes:
            continue

        hub_name = found_station_attributes.get('hub_name', found_station_attributes.get('id'))
        station_lat = found_station_attributes.get('lat')
        station_lon = found_station_attributes.get('lon')
        primary_naptan_id = found_station_attributes.get('primary_naptan_id')
        constituent_stations = found_station_attributes.get('constituent_stations', [])

        if not all([hub_name, station_lat, station_lon]):
            print(f"Error: Missing essential attributes for matched station '{station_name}'. Attributes: {found_station_attributes}")
            continue

        chosen_naptan_id = None
        chosen_station_name_for_display = hub_name

        if primary_naptan_id and primary_naptan_id.startswith("HUB") and len(constituent_stations) > 1:
            print(f"\n'{hub_name}' is a hub. Please specify your exact starting station:")
            for idx, constituent in enumerate(constituent_stations):
                print(f"  {idx + 1}. {constituent.get('name', 'Unknown Name')}")
            
            while True:
                try:
                    choice = input(f"Enter the number (1-{len(constituent_stations)}): ").strip()
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(constituent_stations):
                        chosen_constituent = constituent_stations[choice_idx]
                        chosen_naptan_id = chosen_constituent.get('naptan_id')
                        chosen_station_name_for_display = chosen_constituent.get('name', hub_name)
                        if not chosen_naptan_id:
                            print("Error: Selected constituent station is missing Naptan ID.")
                            chosen_naptan_id = None 
                        break 
                    else:
                        print(f"Invalid choice. Please enter a number between 1 and {len(constituent_stations)}.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
        
        if not chosen_naptan_id:
            if primary_naptan_id and not primary_naptan_id.startswith("HUB"):
                chosen_naptan_id = primary_naptan_id
            elif constituent_stations and isinstance(constituent_stations, list) and len(constituent_stations) > 0:
                 if isinstance(constituent_stations[0], dict) and 'naptan_id' in constituent_stations[0]:
                      chosen_naptan_id = constituent_stations[0]['naptan_id']
                 else:
                     print(f"Error: Invalid structure for constituent_stations[0] for hub '{hub_name}'. Skipping.")
                     continue 
            elif hub_name and not hub_name.startswith("HUB"):
                 print(f"Warning: Falling back to using hub name '{hub_name}' as Naptan ID.")
                 chosen_naptan_id = hub_name 
            else:
                 print(f"Error: Could not determine any valid Naptan ID for '{hub_name}'. Skipping.")
                 continue 

        if not chosen_naptan_id:
            print(f"Critical Error: Failed to assign a Naptan ID for station '{hub_name}'. Skipping this person.")
            continue

        while True:
            try:
                walk_time = int(input(f"Time (minutes) to walk TO '{chosen_station_name_for_display}': ").strip())
                if walk_time < 0:
                    print("Walk time cannot be negative.")
                    continue
                break
            except ValueError:
                print("Please enter a valid number of minutes.")

        people_data.append({
            'id': person_count,
            'start_station_name': hub_name, 
            'start_station_lat': station_lat,         
            'start_station_lon': station_lon,         
            'start_naptan_id': chosen_naptan_id,   
            'time_to_station': walk_time
        })

        print(f"Added: Person {person_count} starting from {chosen_station_name_for_display} (Hub: {hub_name}, Naptan: {chosen_naptan_id})")
        person_count += 1
        
    return people_data

def calculate_networkx_estimates(filtered_stations_attributes, people_data, G):
    """
    Performs the initial travel time estimation using the NetworkX graph.

    Args:
        filtered_stations_attributes (list): List of station attribute dictionaries.
        people_data (list): List of dictionaries containing person data.
        G (nx.MultiDiGraph): The NetworkX graph.

    Returns:
        list: Sorted list of tuples: (total_time, avg_time, name, attributes) 
              for stations reachable by all people according to NetworkX estimates.
    """
    print(f"\n\n--- Stage 1: Calculating initial travel time estimates for {len(filtered_stations_attributes)} stations using NetworkX ---\n")
    networkx_results = []

    for i, meeting_station_attributes in enumerate(filtered_stations_attributes, 1):
        meeting_station_name = meeting_station_attributes.get('hub_name', meeting_station_attributes.get('id'))
        
        if not meeting_station_name:
            print(f"Warning: Skipping filtered station at index {i} due to missing name attribute.")
            continue

        print(f"\nProcessing potential meeting station {i}/{len(filtered_stations_attributes)}: {meeting_station_name} (NetworkX)")
        print("-" * 80)

        current_meeting_total_time_nx = 0
        possible_meeting_nx = True
        person_times_nx = []

        for person in people_data:
            start_station_name = person['start_station_name']
            time_to_station = person['time_to_station']

            nx_path_cost = dijkstra_with_transfer_penalty(
                G,
                start_station_name,
                meeting_station_name
            )

            if nx_path_cost == float('inf'):
                print(f"    Cannot estimate journey for Person {person['id']} from {start_station_name} to {meeting_station_name} using NetworkX (No path found)")
                possible_meeting_nx = False
                break 

            person_total_time_nx = time_to_station + nx_path_cost
            print(f"    Person {person['id']} ({start_station_name}): Walk={time_to_station} + PathCost={nx_path_cost:.2f} -> Total={person_total_time_nx:.2f}")
            
            person_times_nx.append(person_total_time_nx)
            current_meeting_total_time_nx += person_total_time_nx

        if possible_meeting_nx:
            avg_time_nx = current_meeting_total_time_nx / len(people_data)
            print(f"\n    NetworkX Summary for {meeting_station_name}:")
            print(f"      Total estimated time: {current_meeting_total_time_nx:.2f} mins")
            print(f"      Avg. estimated time:  {avg_time_nx:.2f} mins per person")
            networkx_results.append((current_meeting_total_time_nx, avg_time_nx, meeting_station_name, meeting_station_attributes))
        else:
            print(f"    Skipping {meeting_station_name} due to impossible journey estimation.")

    networkx_results.sort(key=lambda x: x[1]) # Sort by average time
    return networkx_results

def determine_api_naptan_id(station_attributes):
    """
    Determines the appropriate Naptan ID for TfL API calls based on station attributes.

    Args:
        station_attributes (dict): Dictionary of station attributes.

    Returns:
        str or None: The Naptan ID to use, or None if not determinable.
    """
    target_api_id = None
    target_primary_id = station_attributes.get('primary_naptan_id')
    target_constituents = station_attributes.get('constituent_stations', [])

    if target_primary_id and not target_primary_id.startswith("HUB"):
        target_api_id = target_primary_id
    elif target_constituents and isinstance(target_constituents[0], dict) and 'naptan_id' in target_constituents[0]:
        target_api_id = target_constituents[0].get('naptan_id')
    
    # Fallback if no specific ID is found (should be rare)
    if not target_api_id:
        hub_name = station_attributes.get('hub_name', station_attributes.get('id'))
        if hub_name and not hub_name.startswith("HUB"):
             print(f"Warning: Falling back to using hub name '{hub_name}' as Naptan ID for API call.")
             target_api_id = hub_name
        
    return target_api_id

def calculate_tfl_times(top_stations_attributes, people_data, api_key):
    """
    Calculates accurate travel times for top candidate stations using TfL API.

    Args:
        top_stations_attributes (list): List of attribute dictionaries for top stations.
        people_data (list): List of dictionaries containing person data.
        api_key (str): TfL API key.

    Returns:
        tuple: (list, dict or None) 
               - List of TFL results: [(total_time, avg_time, name, attributes), ...]
               - Attributes dictionary of the best meeting station found via TFL, or None.
    """
    print(f"\n\n--- Stage 2: Calculating accurate travel times for Top {len(top_stations_attributes)} stations using TfL API ---\n")
    
    top_station_names = [s.get('hub_name', s.get('id', 'Unknown')) for s in top_stations_attributes]
    print(f"Top stations based on NetworkX estimate: {top_station_names}")

    min_total_time = float('inf')
    best_meeting_station_attributes = None 
    tfl_results = [] 

    for i, meeting_station_attributes in enumerate(top_stations_attributes, 1):
        meeting_station_name = meeting_station_attributes.get('hub_name', meeting_station_attributes.get('id'))
        target_api_id = determine_api_naptan_id(meeting_station_attributes)

        if not meeting_station_name:
            print(f"Warning: Skipping top station {i} due to missing name attribute. Attributes: {meeting_station_attributes}")
            continue
        if not target_api_id:
             print(f"Warning: Skipping top station {i} ('{meeting_station_name}') due to inability to determine valid Naptan ID.")
             continue

        print(f"\nProcessing Top station {i}/{len(top_stations_attributes)}: {meeting_station_name} (Using Naptan ID: {target_api_id}) (TfL API)")
        print("-" * 80)

        current_meeting_total_time = 0
        possible_meeting = True
        person_times = []

        for person in people_data:
            start_naptan_id = person['start_naptan_id']
            time_to_station = person['time_to_station']

            tfl_travel_time = get_travel_time(
                start_naptan_id,
                target_api_id,
                api_key
            )

            if tfl_travel_time is None:
                print(f"    Cannot calculate TFL journey from {person['start_station_name']} to {meeting_station_name}")
                possible_meeting = False
                break

            person_total_time = time_to_station + tfl_travel_time
            person_times.append(person_total_time)
            current_meeting_total_time += person_total_time
            
            print(f"  Person {person['id']} from {person['start_station_name']}:")
            print(f"    -> Walk to station: {time_to_station} mins")
            print(f"    -> TfL journey:     {tfl_travel_time} mins")
            print(f"    -> Total TFL time:  {person_total_time} mins")

        if possible_meeting:
            avg_time = current_meeting_total_time / len(people_data)
            print(f"\n  TFL Summary for {meeting_station_name}:")
            print(f"    Total combined TFL travel time: {current_meeting_total_time} mins")
            print(f"    Average TFL travel time: {avg_time:.1f} mins per person")
            tfl_results.append((current_meeting_total_time, avg_time, meeting_station_name, meeting_station_attributes)) 

            if current_meeting_total_time < min_total_time:
                min_total_time = current_meeting_total_time
                best_meeting_station_attributes = meeting_station_attributes
        else:
            print(f"    Skipping {meeting_station_name} for TFL ranking due to impossible journey.")
            
    return tfl_results, best_meeting_station_attributes

def display_results(best_meeting_station_attributes, people_data, tfl_results, api_key):
    """
    Presents the final results, including the best station and alternatives.

    Args:
        best_meeting_station_attributes (dict or None): Attributes of the best station.
        people_data (list): List of dictionaries containing person data.
        tfl_results (list): List of TFL results: [(total_time, avg_time, name, attributes), ...]
        api_key (str): TfL API key.
    """
    if best_meeting_station_attributes:
        best_name = best_meeting_station_attributes.get('hub_name', best_meeting_station_attributes.get('id', 'Unknown Station'))
        best_lat = best_meeting_station_attributes.get('lat', 'N/A')
        best_lon = best_meeting_station_attributes.get('lon', 'N/A')
        best_id_for_api = determine_api_naptan_id(best_meeting_station_attributes)
        
        # Recalculate min_total_time and min_avg_time for the best station from tfl_results
        min_total_time = float('inf')
        min_avg_time = float('inf')
        for total, avg, name, attrs in tfl_results:
            # Compare based on the actual ID or hub name used during TFL calc
            current_name = attrs.get('hub_name', attrs.get('id'))
            if current_name == best_name:
                min_total_time = total
                min_avg_time = avg
                break


        print("\n" + "="*80)
        print("                                    FINAL RESULT (based on TFL API for top NetworkX estimates)")
        print("="*80)
        print(f"The most convenient station found is: {best_name}")
        print(f"Coordinates: {best_lat}, {best_lon}")
        print(f"Using Naptan ID for final checks: {best_id_for_api if best_id_for_api else 'Error: Could not determine ID'}") 
        print(f"\nTotal combined TFL travel time: {min_total_time} minutes")
        print(f"Average TFL travel time per person: {min_avg_time:.1f} minutes")
        print("\nBreakdown by person (TFL API times for best station):")

        if not best_id_for_api:
             print(" Error: Could not determine a valid Naptan ID for the best station to show final breakdown.")
        else:
            for person in people_data:
                start_naptan_id = person.get('start_naptan_id') 
                if not start_naptan_id:
                    print(f"  Person {person['id']} from {person['start_station_name']}: Error retrieving start Naptan ID.")
                    continue
                tfl_time = get_travel_time(
                    start_naptan_id,
                    best_id_for_api,
                    api_key
                )
                if tfl_time is not None:
                    total_time = person['time_to_station'] + tfl_time
                    print(f"  Person {person['id']} from {person['start_station_name']}:")
                    print(f"    -> Walk to station: {person['time_to_station']} mins")
                    print(f"    -> TfL journey: {tfl_time} mins")
                    print(f"    -> Total time: {total_time} mins")
                else:
                     print(f"  Person {person['id']} from {person['start_station_name']}: Could not retrieve final TFL time.")
        
        print("="*80)
        
        tfl_results.sort() 
        if len(tfl_results) > 1: 
            print("\nTop 5 Alternative Meeting Locations (based on TFL API):")
            print("-" * 50)
            alternatives_shown = 0
            for total_time, avg_time, name, station_attributes in tfl_results:
                 current_name = station_attributes.get('hub_name', station_attributes.get('id'))
                 if current_name != best_name and alternatives_shown < 5:
                    print(f"{alternatives_shown + 1}. {name}")
                    print(f"   Total TFL travel time: {total_time} mins")
                    print(f"   Average per person: {avg_time:.1f} mins")
                    print()
                    alternatives_shown += 1
            if alternatives_shown == 0:
                 print("No other viable alternatives found among the top stations processed by TfL API.")

    else:
        print("\n" + "="*80)
        print("Could not find a suitable meeting station where all TFL journeys were possible among the top candidates.")
        print("Please check the starting stations entered or try again later.")
        print("="*80)

# --- Main Execution ---

def main():
    """
    Main function to find the optimal meeting location using optimized station filtering.
    """
    args = parse_arguments()
    print(f"\nUsing API Key: {'*' * (len(args.api_key) - 4) + args.api_key[-4:]}")

    # Load NetworkX graph AND station data lookup from the graph file
    G, station_data_lookup = load_networkx_graph_and_station_data()
    if G is None or station_data_lookup is None:
        print("Could not load the NetworkX graph or station data. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Get user input
    people_data = get_user_inputs(station_data_lookup)
    if not people_data: # Exit if user input failed or was insufficient
        print("Exiting due to insufficient user input.")
        sys.exit(1)


    # Filter stations using optimized method
    all_stations_list_for_filtering = [
        attributes for attributes in station_data_lookup.values()
        if 'lat' in attributes and 'lon' in attributes 
    ]
    if not all_stations_list_for_filtering:
        print("Error: No stations with coordinates found in the graph data for filtering.", file=sys.stderr)
        sys.exit(1)
        
    filtered_stations_attributes = filter_stations_optimized(all_stations_list_for_filtering, people_data)
    if not filtered_stations_attributes:
        print("\nNo stations found within the initial filtering criteria (convex hull/ellipse and centroid).")
        sys.exit(1)

    # --- Stage 1: Calculate initial estimates using NetworkX Graph --- 
    networkx_results = calculate_networkx_estimates(filtered_stations_attributes, people_data, G)
    
    if not networkx_results:
        print("\nNo suitable stations found after NetworkX estimation (no paths found for all participants).")
        sys.exit(1)
        
    # Select top 10 stations based on NetworkX results
    top_10_stations_attributes = [res[3] for res in networkx_results[:10]]

    # --- Stage 2: Calculate accurate travel times for Top 10 using TfL API ---
    tfl_results, best_meeting_station_attributes = calculate_tfl_times(
        top_10_stations_attributes, 
        people_data, 
        args.api_key
    )

    # --- Final Result Display ---
    display_results(best_meeting_station_attributes, people_data, tfl_results, args.api_key)


if __name__ == "__main__":
    main()