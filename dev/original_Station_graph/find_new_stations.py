#!/usr/bin/env python3
"""
Script to identify stations that exist in the NetworkX graph but not in the
old slim_stations dataset. This helps verify that new stations from the TFL API
are being properly included in the graph.
"""

import json
import os
from collections import defaultdict

# File paths
GRAPH_FILE = os.path.join("network_data", "networkx_graph_new.json")
OLD_STATIONS_FILE = os.path.join("slim_stations", "unique_stations.json")

def load_json_file(file_path):
    """
    Load a JSON file and return its contents.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        The parsed JSON data or None if there was an error
    """
    try:
        with open(file_path, 'r') as f:
            # Parse the JSON file into a Python object
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # Print an error message if the file doesn't exist or isn't valid JSON
        print(f"Error loading {file_path}: {e}")
        return None

def get_graph_stations():
    """
    Get all station names from the NetworkX graph.
    
    Returns:
        A set of station names from the graph
    """
    # Load the graph data from the JSON file
    graph_data = load_json_file(GRAPH_FILE)
    if not graph_data:
        return set()
    
    # Extract all station names from the nodes dictionary
    return set(graph_data.get("nodes", {}).keys())

def get_old_stations():
    """
    Get all station names from the old slim_stations file,
    including both parent and child stations.
    
    Returns:
        A set of all station names from the old dataset
    """
    # Load the old stations data from the JSON file
    old_stations_data = load_json_file(OLD_STATIONS_FILE)
    if not old_stations_data:
        return set()
    
    # Create a set to store all station names
    all_stations = set()
    
    # Process each station in the old dataset
    for station in old_stations_data:
        # Add the parent station name
        all_stations.add(station.get("name", ""))
        
        # Add all child station names
        for child in station.get("child_stations", []):
            all_stations.add(child)
    
    return all_stations

def find_new_stations():
    """
    Find stations that exist in the graph but not in the old dataset.
    
    Returns:
        A set of station names that are new in the graph
    """
    # Get all stations from both datasets
    graph_stations = get_graph_stations()
    old_stations = get_old_stations()
    
    # Find stations that are in the graph but not in the old dataset
    new_stations = graph_stations - old_stations
    
    return new_stations

def categorize_new_stations(new_stations):
    """
    Categorize new stations by their transport mode.
    
    Args:
        new_stations: Set of new station names
        
    Returns:
        Dictionary mapping mode to list of station names
    """
    # Load the graph data
    graph_data = load_json_file(GRAPH_FILE)
    if not graph_data:
        return {}
    
    # Create a dictionary to store stations by mode
    stations_by_mode = defaultdict(list)
    
    # Go through each new station
    for station_name in new_stations:
        # Get the station data from the graph
        station_data = graph_data.get("nodes", {}).get(station_name, {})
        
        # Get the modes for this station
        modes = station_data.get("modes", [])
        
        if not modes:
            # If no modes, categorize as "unknown"
            stations_by_mode["unknown"].append(station_name)
        else:
            # Add the station to each of its modes
            for mode in modes:
                stations_by_mode[mode].append(station_name)
    
    return stations_by_mode

def main():
    """Main function to find and display new stations."""
    print("Finding stations that exist in the NetworkX graph but not in the old dataset...")
    
    # Find new stations
    new_stations = find_new_stations()
    
    if not new_stations:
        print("\n✅ No new stations found. The graph only contains stations from the old dataset.")
        return
    
    # Get the total counts
    total_graph_stations = len(get_graph_stations())
    total_old_stations = len(get_old_stations())
    
    print(f"\nStation comparison results:")
    print(f"-------------------------")
    print(f"Total stations in graph: {total_graph_stations}")
    print(f"Total stations in old dataset: {total_old_stations}")
    print(f"New stations found: {len(new_stations)} ({len(new_stations)/total_graph_stations:.1%} of graph)")
    
    # Categorize new stations by mode
    stations_by_mode = categorize_new_stations(new_stations)
    
    # Display new stations by mode
    print("\nNew stations by transport mode:")
    for mode, stations in sorted(stations_by_mode.items()):
        print(f"\n  {mode.upper()} ({len(stations)}):")
        for station in sorted(stations):
            print(f"  - {station}")

if __name__ == "__main__":
    main() 