import json
import os

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def merge_edgware_road_stations():
    """
    Merge the two Edgware Road stations into a single entry with one as a child of the other.
    """
    # Load the existing stations file
    file_path = os.path.join(PROJECT_ROOT, 'raw_stations', 'unique_stations2.json')
    with open(file_path, 'r') as f:
        stations = json.load(f)
    
    # Find the two Edgware Road stations
    edgware_circle = None
    edgware_bakerloo = None
    
    for station in stations:
        if station['name'] == 'Edgware Road (Circle Line) Underground Station':
            edgware_circle = station
        elif station['name'] == 'Edgware Road (Bakerloo) Underground Station':
            edgware_bakerloo = station
    
    # Make sure we found both stations
    if not edgware_circle or not edgware_bakerloo:
        print("Could not find both Edgware Road stations!")
        return
    
    # Make the Circle Line station the parent and Bakerloo the child
    # Add Bakerloo lines to the Circle station
    for line in edgware_bakerloo['lines']:
        if line not in edgware_circle['lines']:
            edgware_circle['lines'].append(line)
    
    # Add Bakerloo station name to child_stations
    edgware_circle['child_stations'].append(edgware_bakerloo['name'])
    
    # Remove the Bakerloo station from the list
    stations = [s for s in stations if s['name'] != 'Edgware Road (Bakerloo) Underground Station']
    
    # Save the updated stations file
    with open(file_path, 'w') as f:
        json.dump(stations, f, indent=2)
    
    print(f"Merged Edgware Road stations. Now there are {len(stations)} total stations.")
    print(f"Edgware Road (Circle Line) has {len(edgware_circle['child_stations'])} child stations: {edgware_circle['child_stations']}")
    print(f"Edgware Road (Circle Line) has lines: {edgware_circle['lines']}")

if __name__ == "__main__":
    merge_edgware_road_stations() 