import json
import os

def consolidate_stations():
    # List of our current station files
    station_files = [
        'unique_stations_tube.json',
        'unique_stations_dlr.json',
        'unique_stations_overground.json',
        'unique_stations_elizabeth-line.json'
    ]
    
    # Dictionary to store unique stations by name
    # Using a dictionary ensures we don't have duplicates
    consolidated_stations = {}
    counter = 0
    # Process each station file
    for file_name in station_files:
        try:
            with open(file_name, 'r') as file:
                stations = json.load(file)
                
                # Process each station in the file
                for station in stations:
                    # Only store essential information: name, lat, lon
                    station_name = station['name'].lower()  # Convert to lowercase for consistency
                    counter += 1
                    # If station already exists, skip it (we already have its coordinates)
                    if station_name not in consolidated_stations:
                        # Store only essential data
                        consolidated_stations[station_name] = {
                            'name': station['name'],  # Keep original name for display
                            'lat': station['lat'],
                            'lon': station['lon']
                        }
        except FileNotFoundError:
            print(f"Warning: Could not find {file_name}")
        except json.JSONDecodeError:
            print(f"Warning: Error reading {file_name}")
    
    # Convert dictionary to list for final storage
    final_stations = list(consolidated_stations.values())
    
    # Save consolidated stations to new file
    with open('unique_stations.json', 'w') as f:  # Using correct filename
        json.dump(final_stations, f, indent=2)
    print(counter)
    print(f"Successfully consolidated {len(final_stations)} unique stations with minimal data (name, lat, lon)")

if __name__ == "__main__":
    consolidate_stations() 