import requests
import json
from dotenv import load_dotenv
import os
from collections import defaultdict
import time

# Load environment variables (for API key)
load_dotenv()

# Define our target modes and lines
# Using a set for O(1) lookup time when checking if a mode is valid
VALID_MODES = {'tube', 'overground', 'dlr', 'elizabeth-line'}

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_station_identifier(station):
    """
    Get the best identifier for a station using a priority system:
    1. hubNaptanCode (most reliable unique identifier)
    2. Parent station IDs (940G for Underground/DLR, 910G for Overground/Elizabeth)
    3. Skip child stations (9400/9100 prefixes)
    4. Fallback to composite key of name and location
    
    The NaptanID patterns explained:
    - 940G/910G: Parent station IDs (main station entry)
    - 9400/9100: Child station IDs (usually platforms or entrances)
    
    Parameters:
    - station: Dictionary containing station data from TfL API
    
    Returns:
    - Tuple of (identifier, source) where source indicates what was used
    """
    hub_code = station.get('hubNaptanCode')
    name = station.get('commonName', '').strip()
    naptan_id = station.get('naptanId', '')
    
    # First priority: hubNaptanCode (most reliable)
    if hub_code:
        return (hub_code, 'hub')
    
    # Second priority: Parent station IDs
    # We check for parent IDs first to ensure we use the main station entry
    if naptan_id:
        if naptan_id.startswith('940G') or naptan_id.startswith('910G'):
            return (naptan_id, 'parent_naptan')
        
        # Skip child stations to avoid duplicates
        # Child stations are usually platforms or different entrances
        if naptan_id.startswith('9400') or naptan_id.startswith('9100'):
            return (None, 'child_station')
    
    # Fallback: Create a composite key from name and location
    lat = station.get('lat')
    lon = station.get('lon')
    
    if name and lat and lon:
        # Normalize station name for consistent comparison
        normalized_name = name.lower()
        # Remove common suffixes that don't affect station identity
        for suffix in [' dlr station', ' underground station', ' station', ' dlr']:
            normalized_name = normalized_name.replace(suffix, '')
        normalized_name = normalized_name.strip()
        
        # Create composite key with 4 decimal place precision (~11m accuracy)
        return (f"{normalized_name}_{round(lat,4)}_{round(lon,4)}", 'composite')
    
    # Last resort: use original naptanId if it's not a child station
    return (naptan_id or 'UNKNOWN', 'naptan')

def is_valid_station(station):
    """
    Determine if a station should be included based on its modes and lines.
    
    We filter stations based on two criteria:
    1. Must have at least one valid transport mode
    2. Must not be exclusively a bus station
    
    Using set operations for efficient mode checking:
    - & (intersection) to check if any modes match
    - all() with generator expression for bus line checking
    
    Parameters:
    - station: Dictionary containing station data from TfL API
    
    Returns:
    - Boolean indicating if station should be included
    """
    # Get the station's modes as a set for O(1) lookup
    station_modes = set(station.get('modes', []))
    
    # Check if the station has at least one valid mode using set intersection
    has_valid_mode = bool(station_modes & VALID_MODES)
    
    # Get the station's lines
    station_lines = station.get('lines', [])
    line_names = {line.get('name', '').lower() for line in station_lines}
    
    # Filter out stations that only have bus lines
    # A station is a bus-only station if ALL its lines are either:
    # - Contain 'bus' in the name
    # - Are purely numeric (bus route numbers)
    # - Start with 'N' (night bus routes)
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

        # After mode distribution but before entry counts
        print("\nAnalyzing NaptanID patterns by mode:")
        mode_patterns = defaultdict(set)
        for station in filtered_stations:
            naptan_id = station.get('naptanId', '')
            if naptan_id:
                prefix = naptan_id[:4] if len(naptan_id) >= 4 else naptan_id
                for mode in station.get('modes', []):
                    if mode in VALID_MODES:
                        mode_patterns[mode].add(prefix)
        
        for mode in sorted(mode_patterns.keys()):
            print(f"\n{mode} ID patterns:")
            for pattern in sorted(mode_patterns[mode]):
                print(f"- {pattern}")
            
            # Print example stations for this mode
            print(f"\nExample {mode} stations:")
            examples = [s for s in filtered_stations if mode in s.get('modes', []) and s.get('naptanId')][:3]
            for station in examples:
                print(f"- {station['commonName']}: {station.get('naptanId')}")

        print("\n" + "-" * 50 + "\n")

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

        # Save stations by mode
        stations_by_mode = defaultdict(list)
        
        for station_id, entries in stations_by_id.items():
            # Take the first entry as representative for name and location
            main_entry = entries[0]
            
            # Get all modes and lines from all entries
            all_modes = set()
            all_lines = set()
            for entry in entries:
                all_modes.update(entry.get('modes', []))
                all_lines.update(line.get('name', '') for line in entry.get('lines', []))
            
            # Filter out bus routes and other unwanted lines
            filtered_lines = {line for line in all_lines 
                            if not (line.isdigit() or line.startswith('N') or 'bus' in line.lower())}
            
            # Create station data object
            station_data = {
                'name': main_entry['commonName'],
                'stationId': station_id,
                'naptanIds': [entry.get('naptanId') for entry in entries],  # Keep all NaptanIDs for reference
                'modes': list(all_modes & VALID_MODES),  # Only keep valid modes
                'lines': list(filtered_lines),
                'lat': main_entry['lat'],
                'lon': main_entry['lon']
            }
            
            # Add station to each mode's list
            for mode in (all_modes & VALID_MODES):
                stations_by_mode[mode].append(station_data)

        # Save mode-specific files and print summaries
        print("\nSaving mode-specific station files:")
        mode_file_mapping = {
            'tube': 'unique_stations_tube.json',
            'dlr': 'unique_stations_dlr.json',
            'overground': 'unique_stations_overground.json',
            'elizabeth-line': 'unique_stations_elizabeth.json'
        }
        
        for mode, filename in mode_file_mapping.items():
            stations = sorted(stations_by_mode[mode], key=lambda x: x['name'])
            print(f"- {mode}: {len(stations)} stations saved to {filename}")
            save_stations(stations, filename)

        # Also save the complete unique stations file as before
        print("\nSaving complete unique stations list to 'unique_stations.json'")
        save_stations_by_mode(stations_by_mode)
            
        print("\nAll files saved successfully!")

def save_stations(stations, filename):
    """Save stations to a JSON file"""
    filepath = os.path.join(PROJECT_ROOT, filename)
    with open(filepath, 'w') as f:
        json.dump(stations, f, indent=2)

def save_stations_by_mode(stations_by_mode):
    """Save stations grouped by mode"""
    filepath = os.path.join(PROJECT_ROOT, 'raw_stations', 'unique_stations.json')
    with open(filepath, 'w') as f:
        json.dump(list(stations_by_mode.values()), f, indent=2)

if __name__ == "__main__":
    inspect_station_data() 