"""
This script checks for stations in the Inter_station_times.csv file that are not in the station_graph.json file.
It also checks for stations that might need special normalization.
"""

#!/usr/bin/env python3
import csv
import json
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
    
    # Special cases for specific stations
    if "heathrow" in name:
        name = "heathrow"  # Normalize all Heathrow variants
    
    if "walthamstow" in name:
        name = "walthamstow"  # Normalize all Walthamstow variants
        
    if "kings cross" in name or "king cross" in name or "kings cross st pancras" in name:
        name = "kings cross"  # Normalize King's Cross variants
    
    # Remove non-alphanumeric characters (except spaces)
    name = re.sub(r'[^\w\s]', '', name)
    
    # Normalize whitespace (replace multiple spaces with a single space)
    name = re.sub(r'\s+', ' ', name)
    
    # Strip leading/trailing whitespace
    name = name.strip()
    
    return name

def analyze_csv_stations():
    """
    Analyze stations in the CSV file to identify which ones occur frequently
    but aren't making it into our graph.
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
    
    # Track stations from CSV and their occurrence count
    station_counter = Counter()
    station_to_normalized = {}
    normalized_to_original = {}
    
    # Open and read the CSV file to extract all station names
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
        
        # Process each row in the CSV file to collect station names
        for row in reader:
            if not row.get(from_station_col) or not row.get(to_station_col):
                continue
                
            start_station = row[from_station_col].strip()
            end_station = row[to_station_col].strip()
            
            # Count occurrences 
            station_counter[start_station] += 1
            station_counter[end_station] += 1
            
            # Store normalized versions
            start_normalized = normalize_station_name(start_station)
            end_normalized = normalize_station_name(end_station)
            
            station_to_normalized[start_station] = start_normalized
            station_to_normalized[end_station] = end_normalized
            
            normalized_to_original[start_normalized] = start_station
            normalized_to_original[end_normalized] = end_station
    
    # Find stations that appear frequently in CSV but aren't in our graph
    missing_stations = []
    for station, count in station_counter.most_common():
        normalized = station_to_normalized[station]
        if normalized not in graph_stations:
            missing_stations.append((station, normalized, count))
    
    # Print results
    print(f"Total unique stations in CSV: {len(station_counter)}")
    print(f"Total stations in graph: {len(graph_stations)}")
    
    print("\nTop 30 missing stations (by occurrence count):")
    for i, (station, normalized, count) in enumerate(missing_stations[:30], 1):
        print(f"  {i}. '{station}' (normalized: '{normalized}') - {count} occurrences")
    
    # Find stations that might need special normalization
    special_cases = []
    for station, normalized in station_to_normalized.items():
        for graph_station in graph_stations:
            # If normalized name is similar but not equal, it might need special handling
            if normalized != graph_station and (normalized in graph_station or graph_station in normalized):
                special_cases.append((station, normalized, graph_station))
    
    print("\nPotential special cases for normalization:")
    for i, (station, normalized, graph_station) in enumerate(special_cases[:20], 1):
        print(f"  {i}. '{station}' ('{normalized}') → '{graph_station}'")
    
    if len(special_cases) > 20:
        print(f"  ... and {len(special_cases) - 20} more")

if __name__ == "__main__":
    analyze_csv_stations() 