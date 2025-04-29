"""
This script compares the stations in the unique_stations.json file with the stations in the station_graph.json file.
It finds the stations that are in the unique_stations.json file but not in the station_graph.json file.
It also finds the stations that have very similar names but don't match.
"""




#!/usr/bin/env python3
import json
import re
from typing import Dict, List, Set

def normalize_station_name(name: str) -> str:
    """
    Normalize a station name for better matching between different data sources.
    
    Args:
        name: The original station name
        
    Returns:
        A normalized version of the name for matching
    """
    # Convert to lowercase
    name = name.lower()
    
    # Replace special characters and standardize names
    name = name.replace("'s", "s")
    name = name.replace("st.", "st")
    name = name.replace("&", "and")
    name = name.replace("-", " ")
    
    # Remove common suffixes like "station", "underground station", etc.
    name = re.sub(r'\s+(dlr|rail|underground|tube|overground|elizabeth[- ]line)?\s*station$', '', name)
    
    # Remove common words that might differ between datasets
    words_to_remove = ['rail', 'underground', 'tube', 'overground', 'dlr', 'elizabeth line']
    for word in words_to_remove:
        name = re.sub(r'\b' + word + r'\b', '', name)
    
    # Special case handling for terminals and numbered stations
    name = re.sub(r'\bterminals?\s*[0-9]+', '', name)  # Remove "terminal(s) X"
    name = re.sub(r'\bterminal\s*[a-z]+', '', name)    # Remove "terminal X"
    
    # Numbers handling
    name = name.replace("123", "")  # For Heathrow 123
    name = name.replace("terminal 5", "")  # For Heathrow Terminal 5
    
    # Remove non-alphanumeric characters (except spaces)
    name = re.sub(r'[^\w\s]', '', name)
    
    # Normalize whitespace (replace multiple spaces with a single space)
    name = re.sub(r'\s+', ' ', name)
    
    # Strip leading/trailing whitespace
    name = name.strip()
    
    return name

def analyze_missing_stations():
    """
    Analyze which stations from unique_stations.json are missing from our graph.
    Compare using normalized names to account for naming variations.
    """
    # Load the stations JSON file
    try:
        with open('slim_stations/unique_stations.json', 'r') as f:
            stations_data = json.load(f)
    except FileNotFoundError:
        try:
            with open('raw_stations/unique_stations2.json', 'r') as f:
                stations_data = json.load(f)
        except FileNotFoundError:
            print("Error: Could not find station data file.")
            return
    
    # Load the generated graph
    try:
        with open('station_graph.normalized.json', 'r') as f:
            graph = json.load(f)
    except FileNotFoundError:
        print("Error: Could not find station_graph.json. Please run create_station_graph.py first.")
        return
    
    # Normalize and collect station names from both sources
    station_names = set()
    station_name_to_original = {}
    for station in stations_data:
        original_name = station['name']
        normalized_name = normalize_station_name(original_name)
        station_names.add(normalized_name)
        station_name_to_original[normalized_name] = original_name
    
    graph_names = set()
    for station in graph:
        normalized_name = normalize_station_name(station)
        graph_names.add(normalized_name)
    
    # Find missing stations
    missing_stations = station_names - graph_names
    
    # Print statistics
    print(f"Total stations in station JSON: {len(station_names)}")
    print(f"Total stations in graph: {len(graph_names)}")
    print(f"Missing stations: {len(missing_stations)}")
    
    # Print list of missing stations with original names
    if missing_stations:
        print("\nMissing stations:")
        for i, normalized_name in enumerate(sorted(missing_stations), 1):
            original_name = station_name_to_original.get(normalized_name, normalized_name)
            print(f"  {i}. '{original_name}' (normalized: '{normalized_name}')")
    
    # Find stations that have very similar names but don't match
    close_matches = []
    for station_name in sorted(missing_stations):
        for graph_name in graph_names:
            # If one is a substring of the other, it might be a close match
            if station_name in graph_name or graph_name in station_name:
                original_name = station_name_to_original.get(station_name, station_name)
                close_matches.append((original_name, station_name, graph_name))
    
    # Print close matches
    if close_matches:
        print("\nPotential close matches (missing station → graph station):")
        for i, (original, missing, graph_name) in enumerate(close_matches[:20], 1):
            print(f"  {i}. '{original}' ('{missing}') → '{graph_name}'")
        
        if len(close_matches) > 20:
            print(f"  ... and {len(close_matches) - 20} more")

if __name__ == "__main__":
    analyze_missing_stations() 