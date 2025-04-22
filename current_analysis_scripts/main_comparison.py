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

# --- Configuration ---
# Base URL for the TfL API (only for journey planning)
TFL_API_BASE_URL = "https://api.tfl.gov.uk/Journey/JourneyResults/"

# --- Path to Local Station Data ---
STATION_DATA_PATH = "slim_stations/unique_stations.json"

# --- New Station Filtering Functions ---

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
            
    print(f"Filtered {len(filtered_stations)} stations within convex hull.")
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

def filter_stations_optimized(all_stations, people_data):
    """
    Two-step filtering process:
    1. Filter stations within convex hull of start locations
    2. Further filter based on centroid circle covering 70% of start locations
    
    Args:
        all_stations (list): List of all station dictionaries
        people_data (list): List of dictionaries containing people's start locations
        
    Returns:
        tuple: (filtered_stations, stats_dict)
    """
    # Extract start locations
    start_locations = [(p['start_station_lat'], p['start_station_lon']) 
                      for p in people_data]
    
    # Step 1: Convex Hull Filtering
    print("\nStep 1: Filtering stations using convex hull...")
    hull_filtered = filter_stations_by_convex_hull(all_stations, start_locations)
    
    # Step 2: Centroid Circle Filtering
    print("\nStep 2: Further filtering using centroid circle (70% coverage)...")
    centroid_lat, centroid_lon, radius_km = calculate_centroid_with_coverage(
        start_locations, coverage_percent=0.7
    )
    
    final_filtered = []
    for station in hull_filtered:
        if is_within_radius(centroid_lat, centroid_lon, radius_km,
                          station['lat'], station['lon']):
            final_filtered.append(station)
            
    print(f"Final filtered count: {len(final_filtered)} stations")
    
    # Prepare statistics for comparison
    stats = {
        'total_stations': len(all_stations),
        'hull_filtered_count': len(hull_filtered),
        'final_filtered_count': len(final_filtered),
        'centroid_lat': centroid_lat,
        'centroid_lon': centroid_lon,
        'coverage_radius_km': radius_km
    }
    
    return final_filtered, stats

# --- Helper Functions from Original Script ---

def load_station_data():
    """
    Loads station data from the local JSON file.
    
    Returns:
        list: A list of station dictionaries with name, coordinates, and child stations.
        None: If loading fails.
    """
    try:
        with open(STATION_DATA_PATH, 'r') as file:
            stations = json.load(file)
            print(f"Loaded {len(stations)} stations from local database.")
            return stations
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading station data: {e}", file=sys.stderr)
        return None

def create_station_lookup(stations):
    """
    Creates a lookup dictionary for faster station searches.
    
    Args:
        stations (list): List of station dictionaries.
        
    Returns:
        dict: Dictionary mapping lowercase station names to station data.
    """
    lookup = {}
    for station in stations:
        lookup[station['name'].lower()] = station
        for child_name in station.get('child_stations', []):
            lookup[child_name.lower()] = station
    
    print(f"Created lookup dictionary with {len(lookup)} station names (including aliases).")
    return lookup

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

def find_closest_station_match(station_name, station_lookup):
    """
    Finds the closest matching station using exact matching first, then normalized names, and finally fuzzy matching.
    Presents user with options when multiple close matches are found.
    
    Args:
        station_name (str): The user-provided station name.
        station_lookup (dict): The station lookup dictionary.
        
    Returns:
        dict: The station data if found, None otherwise.
    """
    # First try direct lookup (case-insensitive)
    normalized_input = station_name.lower().strip()
    
    # Try exact match first
    for station_key, station_data in station_lookup.items():
        if station_key.lower() == normalized_input:
            return station_data
            
        # Also check child stations for exact matches
        for child in station_data.get('child_stations', []):
            if child.lower() == normalized_input:
                return station_data
    
    # If no exact match, normalize the input name using same logic as sync_stations.py
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
        
        # First standardize special characters
        name = name.replace(" & ", " and ")
        name = name.replace("&", "and")
        name = name.replace("-", " ")
        name = name.replace("'", "")
        name = name.replace('"', '')
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
                
        # Remove common patterns
        patterns = [
            ' (h&c line)',
            ' (central)',
            ' (dist&picc line)',
            ' (for excel)',
            ' (london)',
            ' ell '
        ]
        for pattern in patterns:
            name = name.replace(pattern, "")
            
        return ' '.join(name.split())
    
    normalized_input = normalize_name(normalized_input)
    
    # Try matching against normalized names
    matches = []
    seen_names = set()  # Track unique station names we've already added
    
    for station_key, station_data in station_lookup.items():
        # Check main station name
        station_normalized = normalize_name(station_key)
        ratio = fuzz.ratio(normalized_input, station_normalized)
        
        # Only add if we haven't seen this exact name before
        if ratio > 75 and station_data['name'] not in seen_names:  # Collect all matches above threshold
            matches.append((station_data, ratio, station_data['name']))
            seen_names.add(station_data['name'])
            
            # If this station has child stations that are different types (e.g., DLR vs Underground),
            # add them as separate options
            for child in station_data.get('child_stations', []):
                child_normalized = normalize_name(child)
                child_ratio = fuzz.ratio(normalized_input, child_normalized)
                
                # Only add child if it's a good match and we haven't seen this name
                if child_ratio > 75 and child not in seen_names:
                    # For child stations, we still return the parent data but show the child name
                    matches.append((station_data, child_ratio, child))
                    seen_names.add(child)
    
    if not matches:
        # Single consolidated error message
        print(f"\n Error: Station '{station_name}' not found in the list of Tube/Overground/DLR/Rail stations.")
        print(" Please check the spelling and ensure it's a relevant station.")
        print(" Tip: You can use common abbreviations like 'st' for 'street', 'rd' for 'road', etc.")
        return None
        
    # Sort matches by ratio in descending order
    matches.sort(key=lambda x: x[1], reverse=True)
    
    # If we have a perfect match, use it
    if matches[0][1] == 100:
        print(f"Exact match found: '{matches[0][2]}'")
        return matches[0][0]
        
    # If we have multiple matches, show top 5 options
    print(f"\nMultiple matches found for '{station_name}'. Please select the correct station:")
    for i, (station, ratio, matched_name) in enumerate(matches[:5], 1):
        print(f"{i}. {matched_name} (similarity: {ratio}%)")
    
    while True:
        try:
            choice = input("\nEnter the number of your station (or 0 to try a different name): ")
            if choice == '0':
                return None
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(matches[:5]):
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

def get_travel_time(start_coords, end_coords, api_key):
    """
    Calls the TfL Journey Planner API to get the travel time between two locations.

    Args:
        start_coords (tuple): Starting location (latitude, longitude).
        end_coords (tuple): Ending location (latitude, longitude).
        api_key (str): The TfL API key.

    Returns:
        int: Travel time in minutes, or None if the journey cannot be found.
    """
    if start_coords == end_coords:
        return 0
        
    start_loc = f"{start_coords[0]},{start_coords[1]}"
    end_loc = f"{end_coords[0]},{end_coords[1]}"
    url = f"{TFL_API_BASE_URL}{start_loc}/to/{end_loc}"
    
    params = {
        'app_key': api_key,
        'timeIs': 'Departing',
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        journey_data = response.json()
        
        if not journey_data.get('journeys'):
            return None
            
        duration = journey_data['journeys'][0].get('duration')
        return duration

    except Exception as e:
        print(f"Error getting travel time: {e}", file=sys.stderr)
        return None

def calculate_original_filtering_stats(all_stations, people_data):
    """
    Calculates how many stations would be filtered using the original method.
    
    Args:
        all_stations (list): List of all station dictionaries
        people_data (list): List of dictionaries containing people's start locations
        
    Returns:
        dict: Statistics about the original filtering method
    """
    # Extract start locations
    start_locations = [(p['start_station_lat'], p['start_station_lon']) 
                      for p in people_data]
    
    # Calculate centroid
    centroid_lat = sum(lat for lat, _ in start_locations) / len(start_locations)
    centroid_lon = sum(lon for _, lon in start_locations) / len(start_locations)
    
    # Calculate maximum distance for original method
    max_distance = 0
    for lat, lon in start_locations:
        distance = haversine_distance(centroid_lat, centroid_lon, lat, lon)
        if distance > max_distance:
            max_distance = distance
            
    # Add buffer as in original code
    search_radius_km = max_distance + 1.0  # Original 1.0 km buffer
    
    # Count stations that would be included
    filtered_count = sum(1 for station in all_stations 
                        if is_within_radius(centroid_lat, centroid_lon, 
                                         search_radius_km,
                                         station['lat'], station['lon']))
    
    return {
        'total_stations': len(all_stations),
        'filtered_count': filtered_count,
        'centroid_lat': centroid_lat,
        'centroid_lon': centroid_lon,
        'search_radius_km': search_radius_km
    }

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

def main():
    """
    Main function to orchestrate the process with comparison to original method.
    """
    args = parse_arguments()
    print(f"\nUsing API Key: {'*' * (len(args.api_key) - 4) + args.api_key[-4:]}")

    # Load station data
    all_stations = load_station_data()
    if not all_stations:
        print("Could not load the station data. Exiting.", file=sys.stderr)
        sys.exit(1)
        
    station_lookup = create_station_lookup(all_stations)

    # Get user input
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

        found_station = find_closest_station_match(station_name, station_lookup)
        if not found_station:
            print(f"Station '{station_name}' not found. Please try again.")
            continue

        while True:
            try:
                walk_time = int(input(f"Time (minutes) to walk TO '{found_station['name']}': ").strip())
                if walk_time < 0:
                    print("Walk time cannot be negative.")
                    continue
                break
            except ValueError:
                print("Please enter a valid number of minutes.")

        people_data.append({
            'id': person_count,
            'start_station_name': found_station['name'],
            'start_station_lat': found_station['lat'],
            'start_station_lon': found_station['lon'],
            'time_to_station': walk_time
        })
        
        print(f"Added: Person {person_count} starting from {found_station['name']}")
        person_count += 1

    # Calculate statistics for both methods
    print("\nCalculating filtering statistics...")
    
    # Original method stats
    original_stats = calculate_original_filtering_stats(all_stations, people_data)
    
    # New optimized method
    filtered_stations, new_stats = filter_stations_optimized(all_stations, people_data)
    
    # Print comparison
    print("\n=== Filtering Method Comparison ===")
    print("\nOriginal Method:")
    print(f"Total stations: {original_stats['total_stations']}")
    print(f"Stations after filtering: {original_stats['filtered_count']}")
    print(f"Search radius: {original_stats['search_radius_km']:.2f} km")
    
    print("\nNew Optimized Method:")
    print(f"Total stations: {new_stats['total_stations']}")
    print(f"Stations after convex hull: {new_stats['hull_filtered_count']}")
    print(f"Stations after final filtering: {new_stats['final_filtered_count']}")
    print(f"Coverage radius: {new_stats['coverage_radius_km']:.2f} km")
    
    reduction_percent = ((original_stats['filtered_count'] - new_stats['final_filtered_count']) 
                        / original_stats['filtered_count'] * 100)
    print(f"\nStation reduction: {reduction_percent:.1f}%")
    
    # Continue with journey calculations using filtered_stations
    print("\nCalculating travel times to filtered stations...")
    
    # [Rest of the journey calculation logic would go here]
    # For now, we'll just print the number of API calls we saved
    api_calls_saved = original_stats['filtered_count'] - new_stats['final_filtered_count']
    print(f"\nReduced TfL API calls by: {api_calls_saved}")
    print(f"(This will significantly improve runtime!)")

if __name__ == "__main__":
    main() 