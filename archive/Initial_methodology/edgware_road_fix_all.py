import json
import os
import glob

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def merge_edgware_road_stations_in_all_files():
    """
    Merge the two Edgware Road stations into a single entry with one as a child of the other
    in all relevant JSON files.
    """
    # Find all relevant JSON files
    json_pattern = os.path.join(PROJECT_ROOT, 'raw_stations', 'unique_stations2*.json')
    json_files = glob.glob(json_pattern)
    
    print(f"Found {len(json_files)} JSON files to process:")
    for json_file in json_files:
        print(f"- {os.path.basename(json_file)}")
    
    # Process each file
    for json_file in json_files:
        print(f"\nProcessing {os.path.basename(json_file)}...")
        
        # Load the existing stations file
        with open(json_file, 'r') as f:
            stations = json.load(f)
        
        # Find the two Edgware Road stations
        edgware_circle = None
        edgware_bakerloo = None
        
        for station in stations:
            if station['name'] == 'Edgware Road (Circle Line) Underground Station':
                edgware_circle = station
            elif station['name'] == 'Edgware Road (Bakerloo) Underground Station':
                edgware_bakerloo = station
        
        # Skip if we don't have both stations
        if not edgware_circle or not edgware_bakerloo:
            print(f"  Could not find both Edgware Road stations in {os.path.basename(json_file)}")
            continue
        
        # Make the Circle Line station the parent and Bakerloo the child
        # Add Bakerloo lines to the Circle station
        for line in edgware_bakerloo['lines']:
            if line not in edgware_circle['lines']:
                edgware_circle['lines'].append(line)
        
        # Add Bakerloo station name to child_stations
        if 'child_stations' not in edgware_circle:
            edgware_circle['child_stations'] = []
            
        if edgware_bakerloo['name'] not in edgware_circle['child_stations']:
            edgware_circle['child_stations'].append(edgware_bakerloo['name'])
        
        # Remove the Bakerloo station from the list
        stations = [s for s in stations if s['name'] != 'Edgware Road (Bakerloo) Underground Station']
        
        # Save the updated stations file
        with open(json_file, 'w') as f:
            json.dump(stations, f, indent=2)
        
        print(f"  Merged Edgware Road stations in {os.path.basename(json_file)}")
        print(f"  Now there are {len(stations)} total stations.")
        print(f"  Edgware Road (Circle Line) has {len(edgware_circle['child_stations'])} child station(s): {edgware_circle['child_stations']}")
        print(f"  Edgware Road (Circle Line) has lines: {edgware_circle['lines']}")

if __name__ == "__main__":
    merge_edgware_road_stations_in_all_files() 