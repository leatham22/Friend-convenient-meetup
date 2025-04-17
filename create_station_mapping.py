import json
import requests
from datetime import datetime
import os
from dotenv import load_dotenv
import time
from collections import defaultdict

# Load environment variables
load_dotenv()

def get_station_identifier(station):
    """
    Get the best identifier for a station using a priority system:
    1. hubNaptanCode (most reliable unique identifier)
    2. Parent station IDs (940G for Underground/DLR, 910G for Overground/Elizabeth)
    3. Skip child stations (9400/9100 prefixes)
    4. Fallback to composite key of name and location
    """
    hub_code = station.get('hubNaptanCode')
    name = station.get('commonName', '').strip()
    naptan_id = station.get('naptanId', '')
    
    # First priority: hubNaptanCode (most reliable)
    if hub_code:
        return (hub_code, 'hub')
    
    # Second priority: Parent station IDs
    if naptan_id:
        if naptan_id.startswith('940G') or naptan_id.startswith('910G'):
            return (naptan_id, 'parent_naptan')
        
        # Skip child stations to avoid duplicates
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
    """
    # Valid transport modes
    VALID_MODES = {'tube', 'overground', 'dlr', 'elizabeth-line'}
    
    # Get the station's modes as a set for O(1) lookup
    station_modes = set(station.get('modes', []))
    
    # Check if the station has at least one valid mode using set intersection
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

def make_api_request(url, params=None, max_retries=3, initial_timeout=60):
    """Make API request with retries and exponential backoff"""
    if params is None:
        params = {}
    api_key = os.getenv('TFL_API_KEY')
    if api_key:
        params['app_key'] = api_key
        
    for attempt in range(max_retries):
        try:
            print(f"API request attempt {attempt + 1}/{max_retries}...")
            response = requests.get(url, params=params, timeout=initial_timeout * (attempt + 1))
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            print(f"Attempt {attempt + 1} timed out after {initial_timeout * (attempt + 1)} seconds")
        except requests.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
        
        if attempt < max_retries - 1:
            wait_time = 5 * (attempt + 1)  # Exponential backoff
            print(f"Waiting {wait_time} seconds before retrying...")
            time.sleep(wait_time)
            
    print("Failed to fetch data after all retry attempts")
    return None

def create_station_mapping():
    """Create station mapping with child stations"""
    # Define our target modes and lines
    lines = {
        'tube': ['bakerloo', 'central', 'circle', 'district', 'hammersmith-city', 
                'jubilee', 'metropolitan', 'northern', 'piccadilly', 'victoria', 
                'waterloo-city'],
        'dlr': ['dlr'],
        'overground': ['mildmay', 'windrush', 'lioness', 'weaver', 'suffragette', 'liberty'],
        'elizabeth-line': ['elizabeth']
    }
    
    # Dictionary to store stations by their identifier
    stations_by_id = defaultdict(list)
    # Dictionary to store child stations
    child_stations = defaultdict(set)
    
    # Process each mode and line
    for mode, mode_lines in lines.items():
        print(f"\nProcessing {mode} lines...")
        for line in mode_lines:
            print(f"Fetching stations for {line}...")
            url = f"https://api.tfl.gov.uk/Line/{line}/StopPoints"
            stations = make_api_request(url)
            
            if not stations:
                continue
                
            # Process each station
            for station in stations:
                if not is_valid_station(station):
                    continue
                    
                station_id, id_method = get_station_identifier(station)
                
                # Skip child stations but record their names
                if id_method == 'child_station':
                    # Create a composite key for the parent station
                    lat = station.get('lat')
                    lon = station.get('lon')
                    if lat and lon:
                        parent_key = f"{round(lat,4)}_{round(lon,4)}"
                        child_stations[parent_key].add(station.get('commonName', ''))
                    continue
                
                # Only add stations with valid identifiers
                if station_id is not None:
                    # Create a composite key for matching child stations
                    lat = station.get('lat')
                    lon = station.get('lon')
                    if lat and lon:
                        parent_key = f"{round(lat,4)}_{round(lon,4)}"
                        # Add the station's own name to child stations
                        child_stations[parent_key].add(station.get('commonName', ''))
                    
                    # Store the station data
                    stations_by_id[station_id].append({
                        'name': station.get('commonName', ''),
                        'lat': station.get('lat'),
                        'lon': station.get('lon'),
                        'modes': station.get('modes', []),
                        'lines': [line.get('name', '') for line in station.get('lines', [])]
                    })
    
    # Create the final station list with child stations
    final_stations = []
    for station_id, entries in stations_by_id.items():
        # Take the first entry as representative
        main_entry = entries[0]
        
        # Combine modes and lines from all entries
        all_modes = set()
        all_lines = set()
        for entry in entries:
            all_modes.update(entry.get('modes', []))
            all_lines.update(entry.get('lines', []))
        
        # Filter out bus routes and unwanted lines
        filtered_lines = {line for line in all_lines 
                        if not (line.isdigit() or line.startswith('N') or 'bus' in line.lower())}
        
        # Get child stations for this location
        parent_key = f"{round(main_entry['lat'],4)}_{round(main_entry['lon'],4)}"
        station_children = list(child_stations[parent_key])
        
        # Create station data object
        station_data = {
            'name': main_entry['name'],
            'lat': main_entry['lat'],
            'lon': main_entry['lon'],
            'modes': list(mode for mode in all_modes if mode in {'tube', 'overground', 'dlr', 'elizabeth-line'}),
            'lines': list(filtered_lines),
            'child_stations': station_children
        }
        
        final_stations.append(station_data)
    
    # Generate timestamp for the filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'station_mapping_{timestamp}.json'
    
    # Save to file
    with open(filename, 'w') as f:
        json.dump(final_stations, f, indent=2)
    
    # Print statistics
    print(f"\nSaved {len(final_stations)} stations to {filename}")
    stations_with_children = sum(1 for s in final_stations if s['child_stations'])
    total_children = sum(len(s['child_stations']) for s in final_stations)
    print(f"\nStation statistics:")
    print(f"- Total stations: {len(final_stations)}")
    print(f"- Stations with child stations: {stations_with_children}")
    print(f"- Total child stations: {total_children}")
    print(f"- Average children per station: {total_children/len(final_stations):.2f}")

if __name__ == "__main__":
    create_station_mapping() 