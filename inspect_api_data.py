import requests
import json
from dotenv import load_dotenv
import os
from collections import defaultdict
import time

# Load environment variables (for API key)
load_dotenv()

# Define our target modes and lines
VALID_MODES = {'tube', 'overground', 'dlr', 'elizabeth-line'}

def get_station_identifier(station):
    """
    Get the best identifier for a station, prioritizing hubNaptanCode and parent station IDs (940G).
    Returns tuple of (identifier, source) where source indicates what was used.
    """
    hub_code = station.get('hubNaptanCode')
    name = station.get('commonName', '').strip()
    naptan_id = station.get('naptanId', '')
    
    # First priority: hubNaptanCode
    if hub_code:
        return (hub_code, 'hub')
    
    # Second priority: Parent station IDs (940G)
    if naptan_id and naptan_id.startswith('940G'):
        return (naptan_id, 'parent_naptan')
    
    # Skip child stations (9400) as they should be grouped with their parent
    if naptan_id and naptan_id.startswith('9400'):
        return (None, 'child_station')
    
    # If no hub code or valid naptan_id pattern, try to use station name and coordinates
    lat = station.get('lat')
    lon = station.get('lon')
    
    if name and lat and lon:
        # Normalize station name by removing common suffixes and converting to lowercase
        normalized_name = name.lower()
        for suffix in [' dlr station', ' underground station', ' station', ' dlr']:
            normalized_name = normalized_name.replace(suffix, '')
        normalized_name = normalized_name.strip()
        
        # Create a composite key using normalized name and rounded coordinates
        return (f"{normalized_name}_{round(lat,4)}_{round(lon,4)}", 'composite')
    
    # Last resort: use original naptanId if it's not a child station
    return (naptan_id or 'UNKNOWN', 'naptan')

def is_valid_station(station):
    """
    Determine if a station should be included based on its modes and lines.
    """
    # Get the station's modes
    station_modes = set(station.get('modes', []))
    
    # Check if the station has at least one of our valid modes
    has_valid_mode = bool(station_modes & VALID_MODES)
    
    # Get the station's lines
    station_lines = station.get('lines', [])
    line_names = {line.get('name', '').lower() for line in station_lines}
    
    # Filter out stations that only have bus lines
    has_only_bus_lines = all(
        'bus' in line.lower() or line.isdigit() or line.startswith('N') 
        for line in line_names if line
    )
    
    return has_valid_mode and not has_only_bus_lines

def make_api_request(url, params, max_retries=3, timeout=30):
    """
    Make an API request with retry logic
    """
    for attempt in range(max_retries):
        try:
            print(f"API request attempt {attempt + 1}/{max_retries}...")
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            print(f"Attempt {attempt + 1} timed out after {timeout} seconds")
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
        
        if attempt < max_retries - 1:  # Don't sleep after the last attempt
            sleep_time = (attempt + 1) * 5  # Progressive backoff: 5s, 10s, 15s
            print(f"Waiting {sleep_time} seconds before retrying...")
            time.sleep(sleep_time)
    
    return None

def inspect_station_data():
    """
    Fetches and analyzes station data from TfL API, printing detailed information
    about the types of stations and their properties.
    """
    # Get API key from environment
    api_key = os.getenv('TFL_API_KEY')
    if not api_key:
        print("Error: TFL_API_KEY not found in environment variables")
        return

    # Base URL for StopPoint service (same as in main.py)
    TFL_STOPPOINT_BASE_URL = "https://api.tfl.gov.uk/StopPoint/Mode/tube,overground,dlr,elizabeth-line"
    
    # Make the API request with retry logic
    print("Fetching data from TfL API...")
    response = make_api_request(
        TFL_STOPPOINT_BASE_URL,
        params={'app_key': api_key},
        timeout=60  # Increased timeout to 60 seconds
    )

    if not response:
        print("Failed to fetch data after all retry attempts")
        return

    # Parse the JSON response
    data = response.json()

    if 'stopPoints' in data:
        stations = data['stopPoints']
        print(f"\nTotal number of stop points before filtering: {len(stations)}")

        # Filter stations using our new validation function
        filtered_stations = [station for station in stations if is_valid_station(station)]
        print(f"Stations after mode filtering: {len(filtered_stations)}")

        # Count modes in filtered stations
        mode_counts = defaultdict(int)
        for station in filtered_stations:
            for mode in station.get('modes', []):
                if mode in VALID_MODES:  # Only count modes we care about
                    mode_counts[mode] += 1
        
        print("\nMode distribution in filtered stations:")
        for mode, count in sorted(mode_counts.items()):
            print(f"- {mode}: {count} stations")

        # Track how stations are being identified
        id_method_counts = defaultdict(int)

        # Analyze stations by identifier
        stations_by_id = defaultdict(list)
        for station in filtered_stations:
            station_id, id_method = get_station_identifier(station)
            id_method_counts[id_method] += 1
            # Only add stations with valid identifiers (skip child stations)
            if station_id is not None:
                stations_by_id[station_id].append(station)

        # Print identification method statistics
        print("\nStation Identification Methods:")
        for method, count in id_method_counts.items():
            print(f"- Using {method}: {count} stations")

        # Print analysis
        print("\nStation Duplication Analysis:")
        print("-" * 50)
        
        # Count unique physical stations
        unique_stations = len(stations_by_id)
        print(f"\nUnique Physical Stations: {unique_stations}")
        print(f"Total Station Entries: {len(filtered_stations)}")
        print(f"Average entries per station: {len(filtered_stations)/unique_stations:.2f}")

        # Count modes for unique stations (note: stations can appear in multiple modes)
        unique_mode_counts = defaultdict(int)
        for entries in stations_by_id.values():
            # Combine modes from all entries for this unique station
            station_modes = set()
            for entry in entries:
                station_modes.update(mode for mode in entry.get('modes', []) if mode in VALID_MODES)
            # Count each mode for this station
            for mode in station_modes:
                unique_mode_counts[mode] += 1
        
        print("\nMode distribution across unique stations (stations can appear in multiple modes):")
        for mode, count in sorted(unique_mode_counts.items()):
            print(f"- {mode}: {count} stations")

        # Show distribution of entry counts
        entry_counts = defaultdict(int)
        for entries in stations_by_id.values():
            entry_counts[len(entries)] += 1
        
        print("\nDistribution of entries per station:")
        for count in sorted(entry_counts.keys()):
            print(f"{count} entries: {entry_counts[count]} stations")

        # Show some examples of heavily duplicated stations
        print("\nExample of heavily duplicated stations:")
        heavily_duplicated = [(id, entries) for id, entries in stations_by_id.items() if len(entries) > 3]
        heavily_duplicated.sort(key=lambda x: len(x[1]), reverse=True)
        
        for station_id, entries in heavily_duplicated[:3]:  # Show top 3
            first_station = entries[0]
            print(f"\nStation: {first_station['commonName']}")
            print(f"Identifier: {station_id}")
            print(f"Number of entries: {len(entries)}")
            print("Modes:", set().union(*[set(entry.get('modes', [])) for entry in entries]) & VALID_MODES)
            all_lines = set().union(*[{line.get('name', '') for line in entry.get('lines', [])} for entry in entries])
            # Filter out bus routes from display
            filtered_lines = {line for line in all_lines 
                            if not (line.isdigit() or line.startswith('N') or 'bus' in line.lower())}
            print("Lines:", filtered_lines)
            # Print NaptanIDs to help debug
            print("NaptanIDs:", [entry.get('naptanId') for entry in entries])

        # Save unique station data for potential local database
        unique_stations_data = []
        for station_id, entries in stations_by_id.items():
            # Take the first entry as representative for name and location
            main_entry = entries[0]
            # Combine all modes and lines from all entries
            all_modes = set()
            all_lines = set()
            for entry in entries:
                all_modes.update(entry.get('modes', []))
                all_lines.update(line.get('name', '') for line in entry.get('lines', []))
            
            # Filter out bus routes and other unwanted lines
            filtered_lines = {line for line in all_lines 
                            if not (line.isdigit() or line.startswith('N') or 'bus' in line.lower())}
            
            station_data = {
                'name': main_entry['commonName'],
                'stationId': station_id,
                'naptanIds': [entry.get('naptanId') for entry in entries],  # Keep all NaptanIDs for reference
                'modes': list(all_modes & VALID_MODES),  # Only keep valid modes
                'lines': list(filtered_lines),
                'lat': main_entry['lat'],
                'lon': main_entry['lon']
            }
            unique_stations_data.append(station_data)

        # Save unique stations to a file
        print("\nSaving unique stations to 'unique_stations.json'...")
        with open('unique_stations.json', 'w') as f:
            json.dump(unique_stations_data, f, indent=2)

if __name__ == "__main__":
    inspect_station_data() 