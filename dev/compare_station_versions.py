import json
import os
from collections import defaultdict

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_stations(filename):
    """Load stations from a JSON file"""
    filepath = os.path.join(PROJECT_ROOT, filename)
    with open(filepath, 'r') as f:
        stations = json.load(f)
    return stations

def compare_stations(old_file, new_file, mode=None):
    """
    Compare two station files and report differences.
    Returns a tuple of (match_count, only_in_old, only_in_new, location_mismatches)
    """
    # Load stations
    old_stations = load_stations(old_file)
    new_stations = load_stations(new_file)
    
    # Find stations in each set
    old_names = set(old_stations.keys())
    new_names = set(new_stations.keys())
    
    # Calculate differences
    only_in_old = old_names - new_names
    only_in_new = new_names - old_names
    common_names = old_names & new_names
    
    # Check for location mismatches in common stations
    location_mismatches = []
    for name in common_names:
        old_station = old_stations[name]
        new_station = new_stations[name]
        if (old_station['lat'] != new_station['lat'] or 
            old_station['lon'] != new_station['lon']):
            location_mismatches.append({
                'name': name,
                'old_location': (old_station['lat'], old_station['lon']),
                'new_location': (new_station['lat'], new_station['lon'])
            })
    
    return len(common_names), only_in_old, only_in_new, location_mismatches

def main():
    """Compare different versions of station files"""
    comparisons = [
        ('slim_stations/unique_stations.json', 'raw_stations/unique_stations2.json', 'consolidated'),
        ('slim_stations/unique_stations_tube.json', 'raw_stations/unique_stations2_tube.json', 'tube'),
        ('slim_stations/unique_stations_dlr.json', 'raw_stations/unique_stations2_dlr.json', 'DLR'),
        ('slim_stations/unique_stations_overground.json', 'raw_stations/unique_stations2_overground.json', 'Overground'),
        ('slim_stations/unique_stations_elizabethline.json', 'raw_stations/unique_stations2_elizabethline.json', 'Elizabeth Line')
    ]
    
    for old_file, new_file, mode in comparisons:
        print(f"\nComparing {mode} stations...")
        try:
            matches, only_old, only_new, loc_mismatches = compare_stations(old_file, new_file, mode)
            
            print(f"Results for {mode} stations:")
            print(f"- Matching stations: {matches}")
            print(f"- Only in old file: {len(only_old)}")
            if only_old:
                print("  Stations:")
                for name in sorted(only_old):
                    print(f"  - {name}")
            
            print(f"- Only in new file: {len(only_new)}")
            if only_new:
                print("  Stations:")
                for name in sorted(only_new):
                    print(f"  - {name}")
            
            print(f"- Location mismatches: {len(loc_mismatches)}")
            if loc_mismatches:
                print("  Stations:")
                for mismatch in loc_mismatches:
                    print(f"  - {mismatch['name']}")
                    print(f"    Old: {mismatch['old_location']}")
                    print(f"    New: {mismatch['new_location']}")
            
        except FileNotFoundError as e:
            print(f"Warning: Could not compare {mode} stations - file not found")
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 