import requests
import argparse
import os
import sys
import math # Added for distance calculation

# --- Configuration ---
# Base URL for the TfL API
TFL_API_BASE_URL = "https://api.tfl.gov.uk/Journey/JourneyResults/"

# Base URL for StopPoint service
TFL_STOPPOINT_BASE_URL = "https://api.tfl.gov.uk/StopPoint/Mode/tube,overground,dlr,elizabeth-line"

# --- Helper Functions ---

def calculate_centroid(locations):
    """
    Calculates the geographic centroid (average lat/lon) of a list of locations.

    Args:
        locations (list): A list of location strings in "latitude,longitude" format.

    Returns:
        tuple: A tuple containing (average_latitude, average_longitude),
               or (None, None) if the input is empty or invalid.
    """
    total_lat = 0
    total_lon = 0
    count = 0
    if not locations:
        return None, None

    for loc_str in locations:
        try:
            lat, lon = map(float, loc_str.split(','))
            total_lat += lat
            total_lon += lon
            count += 1
        except (ValueError, AttributeError):
            print(f"  Warning: Skipping invalid location '{loc_str}' for centroid calculation.")
            continue # Skip invalid entries

    if count == 0:
        return None, None

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

def validate_location_format(location):
    """
    Basic validation for latitude,longitude format.
    """
    try:
        lat, lon = map(float, location.split(','))
        # Basic range check (adjust ranges if needed for specific use cases)
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Latitude or longitude out of range.")
        return True
    except ValueError:
        return False

# --- Argument Parsing ---

def parse_arguments():
    """
    Parses command-line arguments for API key, start locations, and meeting locations.
    """
    parser = argparse.ArgumentParser(
        description="Find the most convenient meeting location in London based on TfL travel times."
    )

    # Argument for TfL API Key (optional if environment variable is set)
    parser.add_argument(
        "--api-key",
        help="Your TfL API key. Alternatively, set the TFL_API_KEY environment variable."
    )

    # Argument for starting locations (at least one required) - REMOVED
    # parser.add_argument(
    #     "-s", "--start",
    #     required=True,
    #     nargs='+',  # Allows one or more starting locations
    #     help="One or more starting locations (latitude,longitude format). Example: 51.5074,-0.1278"
    # )

    args = parser.parse_args()

    # Validate location formats for start locations only - REMOVED VALIDATION HERE
    # for loc in args.start:
    #     if not validate_location_format(loc):
    #         parser.error(f"Invalid location format: '{loc}'. Use latitude,longitude (e.g., 51.5074,-0.1278).")

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

# --- TfL API Interaction ---

def get_london_stations(api_key, centroid_lat=None, centroid_lon=None, radius_km=None):
    """
    Fetches London Tube and Overground/Rail stations, optionally filtering by radius.

    Args:
        api_key (str): The TfL API key.
        centroid_lat (float, optional): Latitude of the center for filtering.
        centroid_lon (float, optional): Longitude of the center for filtering.
        radius_km (float, optional): Radius in km for filtering.

    Returns:
        list: A list of dictionaries (name, coords) for stations,
              filtered if center and radius are provided.
    """
    params = {
        'app_key': api_key
    }
    stations = []
    filtered_stations = [] # New list for filtered results

    try:
        print(f"Fetching London stations... This might take a moment.")
        response = requests.get(TFL_STOPPOINT_BASE_URL, params=params, timeout=60) # Increased timeout for potentially larger response
        response.raise_for_status()
        stop_point_data = response.json()

        # Check common response structures
        if 'stopPoints' in stop_point_data:
            potential_stations = stop_point_data['stopPoints']
        elif isinstance(stop_point_data, list): # Sometimes it returns a list directly
            potential_stations = stop_point_data
        else:
             print(" Unexpected API response structure when fetching stations.", file=sys.stderr)
             return []

        print(f"Processing {len(potential_stations)} fetched stop points...")

        filtering_active = centroid_lat is not None and centroid_lon is not None and radius_km is not None
        if filtering_active:
            print(f"Filtering stations within {radius_km:.2f} km of ({centroid_lat:.4f}, {centroid_lon:.4f}).")

        # Iterate through the fetched stop points
        for station in potential_stations:
            if 'commonName' in station and 'lat' in station and 'lon' in station:
                name = station['commonName']
                lat = station['lat']
                lon = station['lon']

                # Basic name filter (heuristic)
                if ' Underground Station' in name or ' DLR Station' in name or ' Rail Station' in name or ' Station' in name:
                    # Now apply geographic filter if active
                    if filtering_active:
                        if is_within_radius(centroid_lat, centroid_lon, radius_km, lat, lon):
                            coords = f"{lat},{lon}"
                            filtered_stations.append({'name': name, 'coords': coords})
                        # else: station is outside the radius, skip it
                    else:
                        # Filtering is not active, add all matching stations
                        coords = f"{lat},{lon}"
                        filtered_stations.append({'name': name, 'coords': coords})
            # else: station missing essential data, skip it

        result_list = filtered_stations # Return the filtered list
        if filtering_active:
            print(f"Filtered down to {len(result_list)} stations within the radius.")
        else:
             print(f"Fetched {len(result_list)} potential stations (no geographic filter applied).")
        return result_list

    except requests.exceptions.RequestException as e:
        print(f" Error calling TfL API for stations: {e}", file=sys.stderr)
        return []
    except KeyError as e:
        print(f" Error parsing TfL API station response: Missing key {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f" An unexpected error occurred fetching stations: {e}", file=sys.stderr)
        return []

def get_travel_time(start_loc, end_loc, api_key):
    """
    Calls the TfL Journey Planner API to get the travel time between two locations.

    Args:
        start_loc (str): Starting location in "latitude,longitude" format.
        end_loc (str): Ending location in "latitude,longitude" format.
        api_key (str): The TfL API key.

    Returns:
        int: Travel time in minutes, or None if the journey cannot be found or an error occurs.
    """
    # Construct the API request URL
    # Note: TfL API uses {from}/to/{to} structure with coordinates directly
    url = f"{TFL_API_BASE_URL}{start_loc}/to/{end_loc}"

    # Parameters for the API request, including the API key
    params = {
        'app_key': api_key,
        'timeIs': 'Departing', # Assume departure time is 'now'
        # Add other parameters as needed, e.g., mode preferences
        # 'mode': 'tube,dlr,overground' # Example: limit modes
    }

    try:
        print(f"  Querying TfL API: {start_loc} -> {end_loc}...")
        response = requests.get(url, params=params, timeout=30) # Add a timeout
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        # Parse the JSON response
        journey_data = response.json()

        # Check if journeys were found
        if not journey_data.get('journeys'):
            print(f"  Warning: No direct journey found between {start_loc} and {end_loc}.")
            return None

        # Extract the duration of the first recommended journey
        # TfL API provides duration in minutes
        first_journey = journey_data['journeys'][0]
        duration = first_journey.get('duration')

        if duration is not None:
            print(f"  Found journey duration: {duration} minutes.")
            return duration
        else:
            print(f"  Warning: Could not extract duration for journey {start_loc} -> {end_loc}.")
            return None

    except requests.exceptions.RequestException as e:
        # Handle network errors, timeout errors, bad status codes, etc.
        print(f"  Error calling TfL API for {start_loc} -> {end_loc}: {e}", file=sys.stderr)
        return None
    except KeyError as e:
        # Handle unexpected structure in the JSON response
        print(f"  Error parsing TfL API response for {start_loc} -> {end_loc}: Missing key {e}", file=sys.stderr)
        return None
    except Exception as e:
        # Catch any other unexpected errors during the process
        print(f"  An unexpected error occurred for {start_loc} -> {end_loc}: {e}", file=sys.stderr)
        return None

# --- Main Logic ---

def main():
    """
    Main function to orchestrate the process.
    """
    args = parse_arguments()

    print(f"\nUsing API Key: {'*' * (len(args.api_key) - 4) + args.api_key[-4:]}") # Mask key for printing

    # --- Fetch All Stations Once for Lookup ---
    print("\nFetching all stations for lookup...")
    all_stations_list = get_london_stations(args.api_key)
    if not all_stations_list:
        print("Could not fetch the station list. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Create a dictionary for faster lookup: lowercase name -> {name, coords}
    stations_lookup = {s['name'].lower(): s for s in all_stations_list}
    print(f"Found {len(stations_lookup)} unique station names for lookup.")

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

        # Find the station in our lookup (case-insensitive)
        found_station = stations_lookup.get(station_name_input.lower())

        if not found_station:
            print(f" Error: Station '{station_name_input}' not found in the list of Tube/Overground/DLR/Rail stations.")
            print(" Please check the spelling and ensure it's a relevant station.")
            # Optional: Suggest similar names if possible (more complex)
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
            'start_station_coords': found_station['coords'],
            'time_to_station': walk_time_minutes
        }
        people_data.append(person_info)
        print(f"Added: Person {person_count} starting from {found_station['name']} ({walk_time_minutes} mins walk).")
        person_count += 1

    # --- Calculate Centroid and Radius based on *inputted stations* ---
    print("\nCalculating geographic center and radius from starting stations...")
    start_station_coords_list = [p['start_station_coords'] for p in people_data]
    centroid_lat, centroid_lon = calculate_centroid(start_station_coords_list)

    if centroid_lat is None:
        print("Could not calculate centroid from the provided stations. Exiting.", file=sys.stderr)
        sys.exit(1)

    max_distance = 0
    for station_coords in start_station_coords_list:
        try:
            lat, lon = map(float, station_coords.split(','))
            distance = haversine_distance(centroid_lat, centroid_lon, lat, lon)
            if distance > max_distance:
                max_distance = distance
        except (ValueError, AttributeError):
            continue # Should not happen if lookup worked, but good practice

    # Add a buffer to the radius just in case the optimal meeting point is slightly outside
    # the circle encompassing the start stations. Adjust buffer as needed.
    SEARCH_RADIUS_BUFFER_KM = 1.0
    search_radius_km = max_distance + SEARCH_RADIUS_BUFFER_KM
    print(f"  Centroid of start stations: ({centroid_lat:.4f}, {centroid_lon:.4f})")
    print(f"  Max distance from centroid: {max_distance:.2f} km")
    print(f"  Search Radius (with buffer): {search_radius_km:.2f} km")

    # --- Get Potential Meeting Stations (Filtered based on start station centroid/radius) ---
    potential_meeting_stations = get_london_stations(args.api_key, centroid_lat, centroid_lon, search_radius_km)
    if not potential_meeting_stations:
        print("Could not fetch or filter potential meeting stations within the calculated area. Exiting.", file=sys.stderr)
        sys.exit(1)

    print(f"\nCalculating travel times to the {len(potential_meeting_stations)} filtered potential meeting stations...")

    # --- Calculate Total Travel Times (Adapting the calculation) ---
    results = []
    min_total_time = float('inf')
    best_meeting_station_info = None # Store the whole station dict

    for i, meeting_station in enumerate(potential_meeting_stations):
        meeting_station_name = meeting_station['name']
        meeting_station_coords = meeting_station['coords']
        print(f"\nProcessing potential meeting station {i+1}/{len(potential_meeting_stations)}: {meeting_station_name} ({meeting_station_coords})")

        current_meeting_total_time = 0
        possible_meeting = True

        # Loop through each *person* entered by the user
        for person in people_data:
            start_station_coords = person['start_station_coords']
            time_to_station = person['time_to_station']

            # Get travel time from the person's start station to the potential meeting station
            tfl_travel_time = get_travel_time(start_station_coords, meeting_station_coords, args.api_key)

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
            results.append((current_meeting_total_time, meeting_station_name, meeting_station_coords))

            if current_meeting_total_time < min_total_time:
                min_total_time = current_meeting_total_time
                best_meeting_station_info = meeting_station # Store the station info

    # --- Report Results ---
    if best_meeting_station_info:
        print("\n" + "="*40)
        print("              RESULT")
        print("="*40)
        print(f"The most convenient station found is: {best_meeting_station_info['name']}")
        print(f"Coordinates: {best_meeting_station_info['coords']}")
        print(f"Minimum total combined travel time: {min_total_time} minutes")
        print(" (Includes walk time to start station + TfL journey time for each person)")
        print("="*40)
    else:
        print("\n" + "="*40)
        print("Could not find a suitable meeting station where all journeys were possible.")
        print("Please check the starting stations entered or try again later.")
        print("="*40)

    # Optional: Print all calculated results
    # print("\nFull Results (Total Time, Station Name, Coords):")
    # results.sort() # Sort by total time
    # for time, name, coords in results:
    #     print(f"- {time} mins: {name} ({coords})")


if __name__ == "__main__":
    main()
