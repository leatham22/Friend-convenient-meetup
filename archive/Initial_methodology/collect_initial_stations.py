import json
import requests
from datetime import datetime
import os
from dotenv import load_dotenv
import time
from collections import defaultdict

# Load environment variables
load_dotenv()

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def make_api_request(url, params=None, max_retries=3, initial_timeout=60):
    """
    Make API request with retries and exponential backoff.
    This function is more reliable for the Line endpoint than the StopPoint endpoint.
    """
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

def get_station_key(station):
    """
    Get a unique key for a station, prioritizing:
    1. HubNaptanCode (for grouping related stations)
    2. Location-based key (for stations without HubNaptanCode)
    """
    hub_code = station.get('hubNaptanCode')
    if hub_code:
        return (hub_code, 'hub')
    
    # Fallback to location-based key
    lat = station.get('lat')
    lon = station.get('lon')
    if lat and lon:
        # Round to 4 decimal places (~11m accuracy)
        return (f"{round(lat,4)}_{round(lon,4)}", 'location')
    
    return (None, None)

def handle_special_station_cases(stations):
    """
    Handle special cases for stations that need custom processing.
    
    Currently handles:
    1. Edgware Road stations - combines the two separate stations (Circle Line and Bakerloo)
       into a single parent station with child relationship
    
    Args:
        stations (list): List of station dictionaries
        
    Returns:
        list: Updated list of stations with special cases handled
    """
    # Find special case stations that need to be combined
    edgware_circle = None
    edgware_bakerloo = None
    
    for station in stations:
        if station['name'] == 'Edgware Road (Circle Line) Underground Station':
            edgware_circle = station
        elif station['name'] == 'Edgware Road (Bakerloo) Underground Station':
            edgware_bakerloo = station
    
    # Handle Edgware Road special case if both stations are found
    if edgware_circle and edgware_bakerloo:
        print("Handling special case: Combining Edgware Road stations")
        
        # Add Bakerloo line to the Circle station's lines
        for line in edgware_bakerloo['lines']:
            if line not in edgware_circle['lines']:
                edgware_circle['lines'].append(line)
        
        # Add Bakerloo station name to child_stations if not already there
        if edgware_bakerloo['name'] not in edgware_circle['child_stations']:
            edgware_circle['child_stations'].append(edgware_bakerloo['name'])
        
        # Remove the Bakerloo station from the list
        stations = [s for s in stations if s['name'] != 'Edgware Road (Bakerloo) Underground Station']
        
        print(f"  Edgware Road (Circle Line) now has {len(edgware_circle['child_stations'])} child station(s)")
        print(f"  Edgware Road (Circle Line) now has lines: {edgware_circle['lines']}")
    
    return stations

def collect_stations():
    """
    Collect station data using the Line endpoint method.
    This is more reliable than the StopPoint endpoint.
    """
    # Define our target modes and lines
    lines = {
        'tube': ['bakerloo', 'central', 'circle', 'district', 'hammersmith-city', 
                'jubilee', 'metropolitan', 'northern', 'piccadilly', 'victoria', 
                'waterloo-city'],
        'dlr': ['dlr'],
        'overground': ['mildmay', 'windrush', 'lioness', 'weaver', 'suffragette', 'liberty'],
        'elizabeth-line': ['elizabeth']
    }
    
    # Dictionary to store stations by their key (hub code or location)
    stations_by_key = defaultdict(lambda: {'entries': [], 'modes': set(), 'lines': set(), 'names': set()})
    
    # Process each mode and line
    for mode, mode_lines in lines.items():
        print(f"\nProcessing {mode} lines...")
        mode_stations = []  # For mode-specific file
        
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
                
                station_key, key_type = get_station_key(station)
                if not station_key:
                    continue
                
                # Store the station data
                station_data = {
                    'name': station.get('commonName', ''),
                    'lat': station.get('lat'),
                    'lon': station.get('lon'),
                    'modes': station.get('modes', []),
                    'lines': [line.get('name', '') for line in station.get('lines', [])]
                }
                
                # Update the station group
                stations_by_key[station_key]['entries'].append(station_data)
                stations_by_key[station_key]['modes'].add(mode)
                stations_by_key[station_key]['names'].add(station.get('commonName', ''))
                stations_by_key[station_key]['lines'].update(
                    line.get('name', '') for line in station.get('lines', [])
                    if not (line.get('name', '').isdigit() or 
                           line.get('name', '').startswith('N') or 
                           'bus' in line.get('name', '').lower())
                )
                
                # Also add any alternate names
                for prop in station.get('additionalProperties', []):
                    if prop.get('key') == 'AlternateName' and prop.get('value'):
                        stations_by_key[station_key]['names'].add(prop['value'])
        
        # Create mode-specific station list
        for key, data in stations_by_key.items():
            if mode in data['modes']:
                # Take the first entry as representative
                main_entry = data['entries'][0]
                station_data = {
                    'name': main_entry['name'],
                    'lat': main_entry['lat'],
                    'lon': main_entry['lon'],
                    'modes': [m for m in data['modes'] if m in {'tube', 'overground', 'dlr', 'elizabeth-line'}],
                    'lines': list(data['lines']),
                    'child_stations': list(name for name in data['names'] if name != main_entry['name'])
                }
                mode_stations.append(station_data)
        
        # Handle special station cases for mode-specific stations
        mode_stations = handle_special_station_cases(mode_stations)
        
        # Save mode-specific file
        save_mode_stations(mode_stations, mode)
    
    # Create consolidated station list
    consolidated_stations = []
    for key, data in stations_by_key.items():
        # Take the first entry as representative
        main_entry = data['entries'][0]
        station_data = {
            'name': main_entry['name'],
            'lat': main_entry['lat'],
            'lon': main_entry['lon'],
            'modes': [m for m in data['modes'] if m in {'tube', 'overground', 'dlr', 'elizabeth-line'}],
            'lines': list(data['lines']),
            'child_stations': list(name for name in data['names'] if name != main_entry['name'])
        }
        consolidated_stations.append(station_data)
    
    # Handle special station cases for consolidated stations
    consolidated_stations = handle_special_station_cases(consolidated_stations)
    
    # Save consolidated file
    save_all_stations(consolidated_stations)
    
    # Print statistics
    print(f"\nSaved {len(consolidated_stations)} total unique stations")
    stations_with_children = sum(1 for s in consolidated_stations if s['child_stations'])
    total_children = sum(len(s['child_stations']) for s in consolidated_stations)
    print(f"\nStation statistics:")
    print(f"- Total stations: {len(consolidated_stations)}")
    print(f"- Stations with child stations: {stations_with_children}")
    print(f"- Total child stations: {total_children}")
    print(f"- Average children per station: {total_children/len(consolidated_stations):.2f}")

def save_mode_stations(stations_by_mode, mode):
    """Save stations for a specific mode to a file"""
    mode_filename = os.path.join(PROJECT_ROOT, 'raw_stations', f'unique_stations2_{mode.replace("-", "")}.json')
    os.makedirs(os.path.dirname(mode_filename), exist_ok=True)
    with open(mode_filename, 'w') as f:
        json.dump(stations_by_mode, f, indent=2)
    print(f"Saved {len(stations_by_mode)} {mode} stations")

def save_all_stations(all_stations):
    """Save consolidated stations to a file"""
    filename = os.path.join(PROJECT_ROOT, 'raw_stations', 'unique_stations2.json')
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        json.dump(all_stations, f, indent=2)
    print(f"Saved {len(all_stations)} total stations")

if __name__ == "__main__":
    collect_stations() 