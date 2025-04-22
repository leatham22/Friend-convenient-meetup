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

# --- Configuration ---
# Base URL for the TfL API (only for journey planning)
TFL_API_BASE_URL = "https://api.tfl.gov.uk/Journey/JourneyResults/"

# --- Path to Local Station Data ---
STATION_DATA_PATH = "slim_stations/unique_stations.json"

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
        print("  Start and end stations are the same - no journey needed")
        return 0
        
    start_loc = f"{start_coords[0]},{start_coords[1]}"
    end_loc = f"{end_coords[0]},{end_coords[1]}"
    url = f"{TFL_API_BASE_URL}{start_loc}/to/{end_loc}"
    
    params = {
        'app_key': api_key,
        'timeIs': 'Departing',
    }

    try:
        print(f"  Querying TfL API for journey...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        journey_data = response.json()
        
        if not journey_data.get('journeys'):
            print("  Warning: No journey found between these stations.")
            return None
            
        duration = journey_data['journeys'][0].get('duration')
        if duration is not None:
            print(f"  Found journey duration: {duration} minutes")
        return duration

    except Exception as e:
        print(f"  Error getting travel time: {e}", file=sys.stderr)
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

def main():
    """
    Main function to find the optimal meeting location using optimized station filtering.
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

    # Filter stations using optimized method
    filtered_stations = filter_stations_optimized(all_stations, people_data)
    
    # Calculate travel times and find optimal meeting point
    print(f"\nCalculating travel times to the {len(filtered_stations)} filtered stations...")
    
    min_total_time = float('inf')
    min_avg_time = float('inf')
    best_meeting_station = None
    results = []

    for i, meeting_station in enumerate(filtered_stations, 1):
        meeting_station_name = meeting_station['name']
        meeting_station_lat = meeting_station['lat']
        meeting_station_lon = meeting_station['lon']
        
        print(f"\nProcessing potential meeting station {i}/{len(filtered_stations)}: {meeting_station_name}")
        print("-" * 80)

        current_meeting_total_time = 0
        possible_meeting = True
        person_times = []  # Store individual travel times

        # Calculate travel time for each person
        for person in people_data:
            start_station_lat = person['start_station_lat']
            start_station_lon = person['start_station_lon']
            time_to_station = person['time_to_station']

            # Get travel time from start station to meeting station
            tfl_travel_time = get_travel_time(
                (start_station_lat, start_station_lon), 
                (meeting_station_lat, meeting_station_lon), 
                args.api_key
            )

            if tfl_travel_time is None:
                print(f"Cannot calculate journey from {person['start_station_name']} to {meeting_station_name}")
                possible_meeting = False
                break

            # Total time for this person = walk to their station + TfL journey time
            person_total_time = time_to_station + tfl_travel_time
            person_times.append(person_total_time)
            current_meeting_total_time += person_total_time
            
            print(f"Person {person['id']} from {person['start_station_name']}:")
            print(f"  → Walk to station: {time_to_station} mins")
            print(f"  → TfL journey:     {tfl_travel_time} mins")
            print(f"  → Total journey:   {person_total_time} mins")

        if possible_meeting:
            avg_time = current_meeting_total_time / len(people_data)
            print(f"\nSummary for {meeting_station_name}:")
            print(f"  Total combined travel time: {current_meeting_total_time} mins")
            print(f"  Average travel time: {avg_time:.1f} mins per person")
            results.append((current_meeting_total_time, avg_time, meeting_station_name, meeting_station))

            if current_meeting_total_time < min_total_time:
                min_total_time = current_meeting_total_time
                min_avg_time = avg_time
                best_meeting_station = meeting_station

    # Print final results
    if best_meeting_station:
        print("\n" + "="*80)
        print("                                    RESULT")
        print("="*80)
        print(f"The most convenient station found is: {best_meeting_station['name']}")
        print(f"Coordinates: {best_meeting_station['lat']}, {best_meeting_station['lon']}")
        print(f"\nTotal combined travel time: {min_total_time} minutes")
        print(f"Average travel time per person: {min_avg_time:.1f} minutes")
        print("\nBreakdown by person:")
        
        # Recalculate individual times for the best station for final display
        for person in people_data:
            tfl_time = get_travel_time(
                (person['start_station_lat'], person['start_station_lon']),
                (best_meeting_station['lat'], best_meeting_station['lon']),
                args.api_key
            )
            if tfl_time is not None:
                total_time = person['time_to_station'] + tfl_time
                print(f"Person {person['id']} from {person['start_station_name']}:")
                print(f"  → Walk to station: {person['time_to_station']} mins")
                print(f"  → TfL journey: {tfl_time} mins")
                print(f"  → Total time: {total_time} mins")
        
        print("="*80)
        
        # Print top 5 alternatives
        results.sort()  # Sort by total time
        if len(results) > 1:  # Only show alternatives if we have more than one result
            print("\nTop 5 Alternative Meeting Locations:")
            print("-" * 50)
            for i, (total_time, avg_time, name, _) in enumerate(results[:5], 1):
                print(f"{i}. {name}")
                print(f"   Total travel time: {total_time} mins")
                print(f"   Average per person: {avg_time:.1f} mins")
                print()
    else:
        print("\n" + "="*80)
        print("Could not find a suitable meeting station where all journeys were possible.")
        print("Please check the starting stations entered or try again later.")
        print("="*80)

if __name__ == "__main__":
    main()