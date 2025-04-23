"""
This script adds missing stations to the station graph by analyzing the CSV file.
It normalizes the station names and adds them to the graph if they are not already present.
It also adds connections to the graph if they are not already present.
"""

#!/usr/bin/env python3
import json
import csv
import re
from collections import defaultdict
from typing import Dict, Set, Tuple, List

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
        if "square" in name:
            name = "euston square"
        else:
            name = "euston"  # Normalize Euston variants
    
    # Additional special cases for missing stations
    if "highbury" in name or "highbury and islington" in name:
        name = "highbury and islington"  # Normalize Highbury variants
        
    if "new cross" in name:
        if "gate" in name:
            name = "new cross gate"
        else:
            name = "new cross"  # Distinguish between New Cross and New Cross Gate
        
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

def add_missing_stations() -> None:
    """
    Add missing stations to the station graph by analyzing the CSV file.
    """
    csv_path = "Inter_station_times.csv"
    graph_path = "station_graph.json"
    
    # Load the existing graph
    try:
        with open(graph_path, 'r') as f:
            graph = json.load(f)
            graph_stations = set(graph.keys())
    except FileNotFoundError:
        print("Error: Could not find station_graph.json. Please run create_station_graph.py first.")
        return
    
    # Track missing stations and connections
    missing_stations = set()
    connections_to_add = []
    
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
        running_time_col = 'Un-impeded Running Time (Mins)'
        inter_peak_col = 'Inter peak (1000 - 1600) Running time (mins)'
        
        # Create a CSV reader with these headers
        reader = csv.DictReader(f, fieldnames=headers, skipinitialspace=True)
        
        # Process each row in the CSV file to collect missing stations and connections
        for row in reader:
            if not row.get(from_station_col) or not row.get(to_station_col):
                continue
            
            start_original = row[from_station_col].strip()
            end_original = row[to_station_col].strip()
            
            # Get the running time, prefer unimpeded but fallback to inter-peak
            running_time = row.get(running_time_col)
            if not running_time or running_time.strip() == '':
                running_time = row.get(inter_peak_col)
            
            if not running_time or running_time.strip() == '':
                continue  # Skip if no running time available
                
            try:
                running_time = float(running_time)
            except ValueError:
                continue  # Skip if running time is not a valid number
            
            # Normalize the station names
            start_normalized = normalize_station_name(start_original)
            end_normalized = normalize_station_name(end_original)
            
            # Check if either station is missing from the graph
            if start_normalized not in graph_stations:
                missing_stations.add(start_normalized)
            
            if end_normalized not in graph_stations:
                missing_stations.add(end_normalized)
            
            # If either station is missing, add this connection to our list to add
            if start_normalized not in graph_stations or end_normalized not in graph_stations:
                connections_to_add.append((start_normalized, end_normalized, running_time))
    
    # Add missing stations to the graph
    for station in missing_stations:
        if station not in graph:
            graph[station] = {}
    
    # Add missing connections to the graph
    for start, end, time in connections_to_add:
        if start in graph and end in graph:
            # Check if there's already a connection and take the minimum time
            if end in graph[start]:
                graph[start][end] = min(graph[start][end], time)
            else:
                graph[start][end] = time
    
    # Save the updated graph
    with open(graph_path, 'w') as f:
        json.dump(graph, f, indent=2)
    
    print(f"Added {len(missing_stations)} missing stations to the graph:")
    for station in sorted(missing_stations):
        print(f"  - {station}")
    
    print(f"Added {len(connections_to_add)} new connections to the graph.")

if __name__ == "__main__":
    add_missing_stations() 