import json
import os

def create_slim_version(input_file, output_file):
    """
    Create a slim version of a station file containing only necessary fields:
    - name (for identification)
    - lat/lon (for journey time calculations)
    - child_stations (for syncing)
    """
    # Read input file
    with open(input_file, 'r') as f:
        stations = json.load(f)
    
    # Create slim versions
    slim_stations = []
    for station in stations:
        slim_station = {
            'name': station['name'],
            'lat': station['lat'],
            'lon': station['lon'],
            'child_stations': station['child_stations']
        }
        slim_stations.append(slim_station)
    
    # Save to output file
    with open(output_file, 'w') as f:
        json.dump(sorted(slim_stations, key=lambda x: x['name']), f, indent=2)
    
    return len(slim_stations)

def main():
    """
    Create slim versions of all station files.
    """
    # Create output directory if it doesn't exist
    os.makedirs('slim_stations', exist_ok=True)
    
    # Process consolidated file
    print("\nProcessing consolidated stations file...")
    count = create_slim_version(
        'raw_stations/unique_stations2.json',
        'slim_stations/unique_stations.json'
    )
    print(f"Created slim version with {count} stations")
    
    # Process mode-specific files
    modes = ['tube', 'dlr', 'overground', 'elizabethline']
    for mode in modes:
        print(f"\nProcessing {mode} stations file...")
        try:
            count = create_slim_version(
                f'raw_stations/unique_stations2_{mode}.json',
                f'slim_stations/unique_stations_{mode}.json'
            )
            print(f"Created slim version with {count} stations")
        except FileNotFoundError:
            print(f"Warning: Could not find raw_stations/unique_stations2_{mode}.json")

if __name__ == "__main__":
    main() 