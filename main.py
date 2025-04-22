import requests
import argparse
import os
import sys
import math
import json
from difflib import get_close_matches
from fuzzywuzzy import fuzz

# --- Configuration ---
# Base URL for the TfL API (only for journey planning)
TFL_API_BASE_URL = "https://api.tfl.gov.uk/Journey/JourneyResults/"

# --- Path to Local Station Data ---
STATION_DATA_PATH = "slim_stations/unique_stations.json"

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
    # Main lookup dictionary (lowercase name -> station data)
    lookup = {}
    
    # Process all stations including child stations
    for station in stations:
        # Add main station
        lookup[station['name'].lower()] = station
        
        # Add child stations that refer to their parent
        for child_name in station.get('child_stations', []):
            lookup[child_name.lower()] = station
    
    print(f"Created lookup dictionary with {len(lookup)} station names (including aliases).")
    return lookup

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

def calculate_centroid(locations):
    """
    Calculates the geographic centroid (average lat/lon) of a list of locations.

    Args:
        locations (list): A list of [lat, lon] coordinates.

    Returns:
        tuple: A tuple containing (average_latitude, average_longitude),
               or (None, None) if the input is empty or invalid.
    """
    if not locations:
        return None, None
    
    total_lat = sum(loc[0] for loc in locations)
    total_lon = sum(loc[1] for loc in locations)
    count = len(locations)
    
    return total_lat / count, total_lon / count

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
    # Radius of Earth in kilometers
    R = 6371.0

    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Differences
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance

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
        return False # Cannot calculate if coordinates are missing
    distance = haversine_distance(centroid_lat, centroid_lon, station_lat, station_lon)
    return distance <= radius_km

def get_api_key():
    """
    Retrieves the TfL API key.
    Prioritizes environment variable 'TFL_API_KEY', then command-line argument.
    Exits if no key is found.
    """
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get('TFL_API_KEY')
    if api_key:
        print("Using TfL API key from environment variable.")
        return api_key

    # Check command-line arguments (handled by argparse below)
    # Argparse will handle the case where it's not provided via command line
    return None

def filter_stations_by_radius(stations, centroid_lat, centroid_lon, radius_km):
    """
    Filters stations that are within the specified radius from the centroid.
    
    Args:
        stations (list): List of station dictionaries.
        centroid_lat (float): Latitude of the center point.
        centroid_lon (float): Longitude of the center point.
        radius_km (float): Radius in kilometers.
        
    Returns:
        list: Filtered list of stations within the radius.
    """
    filtered_stations = []
    
    for station in stations:
        if is_within_radius(centroid_lat, centroid_lon, radius_km, 
                           station['lat'], station['lon']):
            filtered_stations.append(station)
    
    print(f"Filtered {len(filtered_stations)} stations within {radius_km:.2f} km radius.")
    return filtered_stations

def get_travel_time(start_coords, end_coords, api_key):
    """
    Calls the TfL Journey Planner API to get the travel time between two locations.

    Args:
        start_coords (tuple): Starting location (latitude, longitude).
        end_coords (tuple): Ending location (latitude, longitude).
        api_key (str): The TfL API key.

    Returns:
        int: Travel time in minutes, or None if the journey cannot be found or an error occurs.
    """
    # Check if start and end coordinates are the same
    if start_coords == end_coords:
        print(f"  Start and end stations are the same - no journey needed")
        return 0  # Return 0 minutes for travel time
        
    # Format coordinates for API request
    start_loc = f"{start_coords[0]},{start_coords[1]}"
    end_loc = f"{end_coords[0]},{end_coords[1]}"
    
    # Construct the API request URL
    url = f"{TFL_API_BASE_URL}{start_loc}/to/{end_loc}"

    # Parameters for the API request, including the API key
    params = {
        'app_key': api_key,
        'timeIs': 'Departing', # Assume departure time is 'now'
    }

    try:
        print(f"  Querying TfL API for journey: {start_loc} -> {end_loc}...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        # Parse the JSON response
        journey_data = response.json()

        # Check if journeys were found
        if not journey_data.get('journeys'):
            print(f"  Warning: No direct journey found between {start_loc} and {end_loc}.")
            return None

        # Extract the duration of the first recommended journey
        first_journey = journey_data['journeys'][0]
        duration = first_journey.get('duration')

        if duration is not None:
            print(f"  Found journey duration: {duration} minutes.")
            return duration
        else:
            print(f"  Warning: Could not extract duration for journey {start_loc} -> {end_loc}.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"  Error calling TfL API for {start_loc} -> {end_loc}: {e}", file=sys.stderr)
        return None
    except KeyError as e:
        print(f"  Error parsing TfL API response for {start_loc} -> {end_loc}: Missing key {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  An unexpected error occurred for {start_loc} -> {end_loc}: {e}", file=sys.stderr)
        return None

# --- Argument Parsing ---

def parse_arguments():
    """
    Parses command-line arguments for API key.
    """
    parser = argparse.ArgumentParser(
        description="Find the most convenient meeting location in London based on TfL travel times."
    )

    # Argument for TfL API Key (optional if environment variable is set)
    parser.add_argument(
        "--api-key",
        help="Your TfL API key. Alternatively, set the TFL_API_KEY environment variable."
    )

    args = parser.parse_args()

    # Get API key, prioritizing environment variable
    final_api_key = get_api_key()
    if not final_api_key:
        # If env var not set, use the command-line arg (or fail if that's also missing)
        if args.api_key:
            final_api_key = args.api_key
        else:
            parser.error("TfL API key is required. Provide it via --api-key or the TFL_API_KEY environment variable.")

    # Add the validated API key back into the args object for easy access
    args.api_key = final_api_key

    return args

# --- Main Logic ---

def main():
    """
    Main function to orchestrate the process.
    """
    args = parse_arguments()

    print(f"\nUsing API Key: {'*' * (len(args.api_key) - 4) + args.api_key[-4:]}") # Mask key for printing

    # --- Load local station data ---
    all_stations = load_station_data()
    if not all_stations:
        print("Could not load the station data. Exiting.", file=sys.stderr)
        sys.exit(1)
        
    # Create station lookup dictionary for quick access and name matching
    station_lookup = create_station_lookup(all_stations)

    # --- Interactive Input for People's Start Stations and Walk Times ---
    people_data = []
    print("\nPlease enter the details for each person.")
    print("Enter the name of their NEAREST Tube/Overground/DLR/Rail station.")
    print("Type 'done' or leave the station name blank when finished.")

    person_count = 1
    while True:
        print(f"\n--- Person {person_count} ---")
        station_name_input = input(f"Nearest Station Name (or type 'done'): ").strip()

        if not station_name_input or station_name_input.lower() == 'done':
            if len(people_data) >= 2: # Need at least two people
                break
            else:
                print("Please enter details for at least two people.")
                continue

        # Find the station using our local data (with fuzzy matching if needed)
        found_station = find_closest_station_match(station_name_input, station_lookup)

        if not found_station:
            print(f" Error: Station '{station_name_input}' not found in the list of Tube/Overground/DLR/Rail stations.")
            print(" Please check the spelling and ensure it's a relevant station.")
            continue # Ask for input for the same person again

        # Get walk time
        while True:
            try:
                walk_time_input = input(f"Time (minutes) to walk TO '{found_station['name']}': ").strip()
                walk_time_minutes = int(walk_time_input)
                if walk_time_minutes < 0:
                    print(" Walk time cannot be negative.")
                    continue
                break # Valid input received
            except ValueError:
                print(" Invalid input. Please enter a whole number for minutes.")

        # Store the data for this person
        person_info = {
            'id': person_count,
            'start_station_name': found_station['name'],
            'start_station_lat': found_station['lat'],
            'start_station_lon': found_station['lon'],
            'time_to_station': walk_time_minutes
        }
        people_data.append(person_info)
        print(f"Added: Person {person_count} starting from {found_station['name']} ({walk_time_minutes} mins walk).")
        person_count += 1

    # --- Calculate Centroid and Radius based on *inputted stations* ---
    print("\nCalculating geographic center and radius from starting stations...")
    start_station_coords = [(p['start_station_lat'], p['start_station_lon']) for p in people_data]
    centroid_lat, centroid_lon = calculate_centroid(start_station_coords)

    if centroid_lat is None:
        print("Could not calculate centroid from the provided stations. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Calculate maximum distance from centroid to define our search radius
    max_distance = 0
    for lat, lon in start_station_coords:
        distance = haversine_distance(centroid_lat, centroid_lon, lat, lon)
        if distance > max_distance:
            max_distance = distance

    # Add a buffer to the radius to ensure we find the optimal meeting point
    SEARCH_RADIUS_BUFFER_KM = 1.0
    search_radius_km = max_distance + SEARCH_RADIUS_BUFFER_KM
    print(f"  Centroid of start stations: ({centroid_lat:.4f}, {centroid_lon:.4f})")
    print(f"  Max distance from centroid: {max_distance:.2f} km")
    print(f"  Search Radius (with buffer): {search_radius_km:.2f} km")

    # --- Get Potential Meeting Stations (Filtered based on centroid/radius) ---
    # Filter stations locally using the radius
    potential_meeting_stations = filter_stations_by_radius(all_stations, centroid_lat, centroid_lon, search_radius_km)
    
    if not potential_meeting_stations:
        print("Could not find potential meeting stations within the calculated area. Exiting.", file=sys.stderr)
        sys.exit(1)

    print(f"\nCalculating travel times to the {len(potential_meeting_stations)} filtered potential meeting stations...")

    # --- Calculate Total Travel Times ---
    results = []
    min_total_time = float('inf')
    best_meeting_station = None

    for i, meeting_station in enumerate(potential_meeting_stations):
        meeting_station_name = meeting_station['name']
        meeting_station_lat = meeting_station['lat']
        meeting_station_lon = meeting_station['lon']
        
        print(f"\nProcessing potential meeting station {i+1}/{len(potential_meeting_stations)}: {meeting_station_name}")

        current_meeting_total_time = 0
        possible_meeting = True

        # Loop through each person
        for person in people_data:
            start_station_lat = person['start_station_lat']
            start_station_lon = person['start_station_lon']
            time_to_station = person['time_to_station']

            # Get travel time from the person's start station to the potential meeting station
            tfl_travel_time = get_travel_time(
                (start_station_lat, start_station_lon), 
                (meeting_station_lat, meeting_station_lon), 
                args.api_key
            )

            if tfl_travel_time is None:
                print(f"  Cannot calculate TfL journey from {person['start_station_name']} to {meeting_station_name}. Skipping this meeting station.")
                possible_meeting = False
                break # Stop checking other people for this meeting station
            else:
                # Total time for this person = walk to their station + TfL journey time
                person_total_time = time_to_station + tfl_travel_time
                current_meeting_total_time += person_total_time
                print(f"    Time for Person {person['id']} ({person['start_station_name']} -> {meeting_station_name}): {time_to_station} min walk + {tfl_travel_time} min TfL = {person_total_time} min")

        if possible_meeting:
            print(f"-> Total combined travel time to {meeting_station_name}: {current_meeting_total_time} minutes")
            results.append((current_meeting_total_time, meeting_station_name, (meeting_station_lat, meeting_station_lon)))

            if current_meeting_total_time < min_total_time:
                min_total_time = current_meeting_total_time
                best_meeting_station = meeting_station

    # --- Report Results ---
    if best_meeting_station:
        print("\n" + "="*40)
        print("              RESULT")
        print("="*40)
        print(f"The most convenient station found is: {best_meeting_station['name']}")
        print(f"Coordinates: {best_meeting_station['lat']}, {best_meeting_station['lon']}")
        print(f"Minimum total combined travel time: {min_total_time} minutes")
        print(" (Includes walk time to start station + TfL journey time for each person)")
        print("="*40)
    else:
        print("\n" + "="*40)
        print("Could not find a suitable meeting station where all journeys were possible.")
        print("Please check the starting stations entered or try again later.")
        print("="*40)

    # Optional: Print top 5 results sorted by total time
    results.sort() # Sort by total time
    if len(results) > 0:
        print("\nTop 5 Meeting Locations:")
        for i, (time, name, coords) in enumerate(results[:5]):
            print(f"{i+1}. {name} - {time} mins total travel time - Coords: {coords[0]:.4f}, {coords[1]:.4f}")


if __name__ == "__main__":
    main()
