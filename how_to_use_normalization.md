# How to Use Station Name Normalization

This guide explains how to use the station name normalization system in your application to ensure consistent station matching between user input, metadata, and the graph.

## Basic Workflow

The recommended workflow is:

1. Import the normalization function:
   ```python
   from normalize_stations import normalize_name
   ```

2. When handling user input:
   ```python
   # Get user input
   user_station = input("Enter a station: ")
   
   # Normalize the user input
   normalized_station = normalize_name(user_station)
   ```

3. Use the normalized name to look up in both datasets:
   ```python
   # Look up in metadata
   if normalized_station in metadata_dict:
       station_info = metadata_dict[normalized_station]
       
       # Use the same normalized name to look up in the graph
       if normalized_station in graph:
           connections = graph[normalized_station]
   ```

## Setting Up the Lookup Dictionaries

For efficient lookups, create dictionaries indexed by normalized station names:

```python
# For station metadata
def load_station_metadata(filename):
    with open(filename, 'r') as f:
        stations = json.load(f)
    
    # Create a dictionary with normalized names as keys
    metadata_dict = {}
    for station in stations:
        # Normalize the station name
        norm_name = normalize_name(station["name"])
        metadata_dict[norm_name] = station
        
        # Also index child stations
        for child in station.get("child_stations", []):
            norm_child = normalize_name(child)
            if norm_child != norm_name:  # Avoid duplicates
                metadata_dict[norm_child] = station
    
    return metadata_dict

# For the graph
def load_station_graph(filename):
    with open(filename, 'r') as f:
        graph = json.load(f)
    
    # For the graph, no additional processing is needed
    # as it should already be indexed by normalized names
    return graph
```

## Example Usage

Complete example for looking up a station and finding connections:

```python
import json
from normalize_stations import normalize_name

# Load data
def load_data():
    # Load station metadata
    with open("slim_stations/unique_stations.json", 'r') as f:
        stations = json.load(f)
    
    # Create metadata lookup dictionary
    metadata_dict = {}
    for station in stations:
        norm_name = normalize_name(station["name"])
        metadata_dict[norm_name] = station
        
        # Also index child stations
        for child in station.get("child_stations", []):
            norm_child = normalize_name(child)
            if norm_child != norm_name:
                metadata_dict[norm_child] = station
    
    # Load graph
    with open("station_graph.json", 'r') as f:
        graph = json.load(f)
    
    return metadata_dict, graph

# Main function
def find_station():
    metadata_dict, graph = load_data()
    
    # Get user input
    user_station = input("Enter a station: ")
    normalized_station = normalize_name(user_station)
    
    # Look up in metadata
    if normalized_station in metadata_dict:
        station = metadata_dict[normalized_station]
        print(f"Found station: {station['name']}")
        print(f"Coordinates: {station['lat']}, {station['lon']}")
        
        # Look up in graph
        if normalized_station in graph:
            connections = graph[normalized_station]
            print(f"Found {len(connections)} connections:")
            for dest, time in list(connections.items())[:5]:
                print(f"  To {dest}: {time} minutes")
        else:
            print("Station found in metadata but not in graph.")
    else:
        print(f"Station '{user_station}' not found.")

if __name__ == "__main__":
    find_station()
```

## Important Notes

1. Always use the `normalize_name()` function from `normalize_stations.py` for consistency.

2. The normalization handles:
   - Case insensitivity
   - Common suffixes (Station, Underground, etc.)
   - Special characters
   - Common abbreviations
   - Line indicators (e.g., (Metropolitan), (Circle Line))

3. Special cases like "Walthamstow Central" → "walthamstow" are handled automatically.

4. If you find stations that aren't matching correctly:
   - Check if they're in both datasets
   - Check if their normalized names match
   - Add them to the exceptions_map in normalize_stations.py if needed 