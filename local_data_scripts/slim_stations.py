import json
import os

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def slim_stations(input_file, output_file):
    """Create a slim version of the stations file with only essential data"""
    try:
        # Update paths to use PROJECT_ROOT
        input_path = os.path.join(PROJECT_ROOT, input_file)
        output_path = os.path.join(PROJECT_ROOT, output_file)
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(input_path, 'r') as f:
            stations = json.load(f)
            
        slim_stations = []
        for station in stations:
            slim_station = {
                'name': station['name'],
                'lat': station['lat'],
                'lon': station['lon']
            }
            if 'child_stations' in station:
                slim_station['child_stations'] = station['child_stations']
            slim_stations.append(slim_station)
            
        with open(output_path, 'w') as f:
            json.dump(slim_stations, f, indent=2)
            
        print(f"Created slim version with {len(slim_stations)} stations")
        
    except FileNotFoundError:
        print(f"Warning: Could not find {input_file}")
    except Exception as e:
        print(f"Error processing {input_file}: {str(e)}")

def main():
    # Process main stations file
    slim_stations(
        'raw_stations/unique_stations2.json',
        'slim_stations/unique_stations.json'
    )
    
    # Process mode-specific files
    for mode in ['tube', 'dlr', 'overground', 'elizabethline']:
        slim_stations(
            f'raw_stations/unique_stations2_{mode}.json',
            f'slim_stations/unique_stations_{mode}.json'
        )

if __name__ == "__main__":
    main() 