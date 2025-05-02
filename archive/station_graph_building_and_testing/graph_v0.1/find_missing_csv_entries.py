"""
This script compares the stations in the Inter_station_times.csv file with the stations in the station_graph.json file.
It finds the stations that are in the Inter_station_times.csv file but not in the station_graph.json file.
"""

#!/usr/bin/env python3
import json
import csv
import re
from collections import Counter
from typing import Dict, List, Set, Tuple

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
    
    # Handle special line suffixes in parentheses
    name = re.sub(r'\s*\([^)]*\)\s*', ' ', name)  # Remove any text in parentheses
    
    # Remove common suffixes like "station", "underground station", etc.
    name = re.sub(r'\s+(dlr|rail|underground|tube|overground|elizabeth[- ]line)?\s*station$', '', name)
    
    # Remove common words that might differ between datasets
    words_to_remove = ['rail', 'underground', 'tube', 'overground', 'dlr', 'elizabeth line', 'dlr', 'ell']
    for word in words_to_remove:
        name = re.sub(r'\b' + word + r'\b', '', name)
    
    # Special case handling for terminals and numbered stations
    name = re.sub(r'\bterminals?\s*[0-9]+', '', name)  # Remove "terminal(s) X"
    name = re.sub(r'\bterminal\s*[a-z]+', '', name)    # Remove "terminal X"
    
    # Numbers handling
    name = name.replace("123", "")  # For Heathrow 123
    name = name.replace("terminal 5", "")  # For Heathrow Terminal 5
    
    # Special cases for specific stations with known variations
    if "heathrow" in name:
        name = "heathrow"  # Normalize all Heathrow variants
    
    if "walthamstow" in name:
        name = "walthamstow"  # Normalize all Walthamstow variants
        
    if "kings cross" in name or "king cross" in name or "kings cross st pancras" in name:
        name = "kings cross"  # Normalize King's Cross variants
        
    if "hammersmith" in name:
        name = "hammersmith"  # Normalize all Hammersmith variants
    
    if "edgware road" in name:
        name = "edgware road"  # Normalize Edgware Road variants
        
    if "paddington" in name:
        name = "paddington"  # Normalize Paddington variants
        
    if "kennington" in name:
        name = "kennington"  # Normalize Kennington variants
        
    if "baker street" in name:
        name = "baker street"  # Normalize Baker Street variants
        
    if "euston" in name or "euston square" in name:
        name = "euston"  # Normalize Euston variants
        
    if "highbury" in name or "highbury and islington" in name:
        name = "highbury and islington"  # Normalize Highbury variants
        
    if "kensington olympia" in name:
        name = "kensington olympia"  # Normalize Kensington Olympia variants

    if "shepherds bush" in name:
        # Check if it's Shepherd's Bush Market
        if "market" in name:
            name = "shepherds bush market"
        else:
            name = "shepherds bush"  # For Shepherd's Bush (Central line)
    
    # Remove non-alphanumeric characters (except spaces)
    name = re.sub(r'[^\w\s]', '', name)
    
    # Normalize whitespace (replace multiple spaces with a single space)
    name = re.sub(r'\s+', ' ', name)
    
    # Strip leading/trailing whitespace
    name = name.strip()
    
    return name

def analyze_csv_entries():
    """
    Analyze which entries in the CSV file are not being matched to stations in our graph.
    """
    csv_path = "Inter_station_times.csv"
    graph_path = "station_graph.json"
    
    # Load the graph to see which stations made it in
    try:
        with open(graph_path, 'r') as f:
            graph = json.load(f)
            graph_stations = set(graph.keys())
    except FileNotFoundError:
        print("Error: Could not find station_graph.json. Please run create_station_graph.py first.")
        return
    
    # Load the raw stations data to see all possible stations
    try:
        with open('raw_stations/unique_stations2.json', 'r') as f:
            stations_data = json.load(f)
            
        # Create a normalized map of station names
        stations_map = {}
        for station in stations_data:
            normalized = normalize_station_name(station['name'])
            stations_map[normalized] = station['name']
    except FileNotFoundError:
        print("Error: Could not find stations data.")
        return
    
    # Track stations from CSV that aren't making it into the graph
    csv_stations = set()
    missing_connections = []
    normalized_to_original = {}
    
    # Open the CSV file and analyze it
    with open(csv_path, 'r') as f:
        # Skip the first line (which is empty commas)
        next(f)
        
        # Read the second line which contains the headers
        headers_line = next(f).strip()
        headers = [h.strip() for h in headers_line.split(',')]
        
        # Find the column indices for station names
        from_station_col = 'Station from (A)'
        to_station_col = 'Station to (B)'
        
        # Create a CSV reader with these headers
        reader = csv.DictReader(f, fieldnames=headers, skipinitialspace=True)
        
        # Process each row in the CSV file to collect station names and connections
        row_count = 0
        for row in reader:
            if not row.get(from_station_col) or not row.get(to_station_col):
                continue
            
            row_count += 1
            
            start_original = row[from_station_col].strip()
            end_original = row[to_station_col].strip()
            
            # Normalize the station names
            start_normalized = normalize_station_name(start_original)
            end_normalized = normalize_station_name(end_original)
            
            # Add to our sets and mappings
            csv_stations.add(start_original)
            csv_stations.add(end_original)
            normalized_to_original[start_normalized] = start_original
            normalized_to_original[end_normalized] = end_original
            
            # Check if this connection is missing from our graph
            if start_normalized not in graph_stations or end_normalized not in graph_stations:
                missing_connections.append((start_original, end_original, start_normalized, end_normalized))
    
    # Find stations that appear in CSV but aren't in our graph
    missing_stations = []
    for normalized, original in normalized_to_original.items():
        if normalized not in graph_stations:
            missing_stations.append((original, normalized))
    
    # Print results
    print(f"Total unique stations in CSV: {len(csv_stations)}")
    print(f"Total stations in graph: {len(graph_stations)}")
    print(f"Total rows in CSV: {row_count}")
    
    print("\nTop 30 missing stations from CSV:")
    for i, (original, normalized) in enumerate(sorted(missing_stations, key=lambda x: x[0])[:30], 1):
        print(f"  {i}. '{original}' (normalized: '{normalized}')")
    
    print("\nSample of missing connections:")
    for i, (start, end, start_norm, end_norm) in enumerate(missing_connections[:20], 1):
        missing_part = "start" if start_norm not in graph_stations else "end"
        print(f"  {i}. '{start}' → '{end}' (missing {missing_part} station)")
    
    if len(missing_connections) > 20:
        print(f"  ... and {len(missing_connections) - 20} more")
    
    # Analyze potential normalization issues
    print("\nSuggested normalizations to add:")
    suggestions = {}
    for original, normalized in normalized_to_original.items():
        if normalized not in graph_stations:
            # Try to find close matches in the graph
            for graph_station in graph_stations:
                if normalized in graph_station or graph_station in normalized:
                    if normalized not in suggestions:
                        suggestions[normalized] = []
                    suggestions[normalized].append((original, graph_station))
    
    for normalized, matches in list(suggestions.items())[:20]:
        original = matches[0][0]
        suggested_match = matches[0][1]
        print(f"  '{original}' → '{suggested_match}'")

if __name__ == "__main__":
    analyze_csv_entries() 