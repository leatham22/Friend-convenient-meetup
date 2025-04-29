"""
This script was used to consolidate the stations from different modes into a single file. 

It was used to create the `unique_stations.json` file, which is the master data source for all potential stations a user can start/travel to. 
"""

import json
import os

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_stations(file_name):
    """Load stations from a JSON file"""
    filepath = os.path.join(PROJECT_ROOT, file_name)
    with open(filepath, 'r') as file:
        stations = json.load(file)
    return stations

def save_stations(stations, filename):
    """Save stations to a JSON file"""
    filepath = os.path.join(PROJECT_ROOT, filename)
    with open(filepath, 'w') as f:
        json.dump(stations, f, indent=2)

def consolidate_stations():
    """Consolidate stations from different modes into a single file"""
    # Load stations from each mode
    modes = ['tube', 'dlr', 'overground', 'elizabethline']
    all_stations = []
    
    for mode in modes:
        try:
            stations = load_stations(f'raw_stations/unique_stations_{mode}.json')
            all_stations.extend(stations)
            print(f"Loaded {len(stations)} {mode} stations")
        except FileNotFoundError:
            print(f"Warning: No file found for {mode}")
    
    # Create dictionary to deduplicate stations
    stations_dict = {}
    for station in all_stations:
        name = station['name']
        if name not in stations_dict:
            stations_dict[name] = station
        else:
            # Merge modes and lines if station already exists
            existing = stations_dict[name]
            existing['modes'] = list(set(existing['modes'] + station['modes']))
            existing['lines'] = list(set(existing['lines'] + station['lines']))
    
    # Convert back to list and sort by name
    final_stations = sorted(stations_dict.values(), key=lambda x: x['name'])
    
    # Save consolidated stations
    save_stations(final_stations, 'raw_stations/unique_stations.json')
    print(f"\nSaved {len(final_stations)} consolidated stations")

if __name__ == "__main__":
    consolidate_stations() 