"""
This script verifies the station graph by checking some example paths.
"""

#!/usr/bin/env python3
import json
import re
from collections import deque
from typing import Dict, List, Tuple, Set, Optional

def normalize_station_name(name: str) -> str:
    """
    Normalize a station name for better matching.
    
    Args:
        name: The station name to normalize
        
    Returns:
        A normalized version of the name
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

    if "shepherds bush" in name:
        if "market" in name:
            name = "shepherds bush market"
        else:
            name = "shepherds bush"  # Normalize Shepherd's Bush variants
    
    if "highbury" in name or "highbury and islington" in name:
        name = "highbury and islington"  # Normalize Highbury variants
        
    if "new cross" in name:
        if "gate" in name:
            name = "new cross gate"
        else:
            name = "new cross"  # Distinguish between New Cross and New Cross Gate
    
    # Remove non-alphanumeric characters (except spaces)
    name = re.sub(r'[^\w\s]', '', name)
    
    # Normalize whitespace (replace multiple spaces with a single space)
    name = re.sub(r'\s+', ' ', name)
    
    # Strip leading/trailing whitespace
    name = name.strip()
    
    return name

def find_station(graph: Dict, name: str) -> Optional[str]:
    """
    Find a station in the graph, including partial matches.
    
    Args:
        graph: The station graph
        name: The station name to find
        
    Returns:
        The matched station name, or None if no match was found
    """
    # Normalize the input name
    normalized_name = normalize_station_name(name)
    
    # Try exact match first
    if normalized_name in graph:
        return normalized_name
    
    # Try prefix match
    for station in graph:
        if station.startswith(normalized_name):
            return station
    
    # Try contains match
    for station in graph:
        if normalized_name in station:
            return station
            
    # Special case for terminals
    if "terminal" in name.lower() or "heathrow" in name.lower():
        for station in graph:
            if "heathrow" in station:
                return station
    
    return None

def find_shortest_path(graph: Dict, start: str, end: str) -> Optional[Tuple[List[str], float]]:
    """
    Find the shortest path between two stations using BFS.
    
    Args:
        graph: The station graph dictionary
        start: The starting station name
        end: The destination station name
        
    Returns:
        A tuple containing (path as list of stations, total travel time in minutes)
        or None if no path is found
    """
    # Try to find the stations in the graph
    start_station = find_station(graph, start)
    end_station = find_station(graph, end)
    
    if not start_station:
        print(f"Error: Start station '{start}' not found in graph")
        return None
    
    if not end_station:
        print(f"Error: End station '{end}' not found in graph")
        return None
    
    # Show which stations we're actually using (for debugging)
    if start_station != start:
        print(f"Using '{start_station}' for '{start}'")
    if end_station != end:
        print(f"Using '{end_station}' for '{end}'")
        
    # If start and end are the same, return immediately
    if start_station == end_station:
        return ([start_station], 0)
    
    # Initialize BFS queue with (station, path, total_time)
    queue = deque([(start_station, [start_station], 0)])
    visited = set([start_station])
    
    # Perform BFS
    while queue:
        station, path, total_time = queue.popleft()
        
        # Check all neighbors of the current station
        for neighbor, time in graph.get(station, {}).items():
            if neighbor not in visited:
                new_path = path + [neighbor]
                new_time = total_time + time
                
                # If we found the destination, return the path and time
                if neighbor == end_station:
                    return (new_path, new_time)
                
                # Otherwise, add to the queue and mark as visited
                queue.append((neighbor, new_path, new_time))
                visited.add(neighbor)
    
    # If we get here, no path was found
    print(f"No path found from '{start_station}' to '{end_station}'")
    return None

def format_time(minutes: float) -> str:
    """
    Format time in minutes to a readable string.
    
    Args:
        minutes: Time in minutes
        
    Returns:
        Formatted time string (e.g., "3.5 minutes")
    """
    return f"{minutes:.1f} minutes"

def main():
    """
    Main function to verify the graph by checking some example paths.
    """
    # Load the graph
    with open('station_graph.json', 'r') as f:
        graph = json.load(f)
    
    # Print some basic statistics
    print(f"Loaded graph with {len(graph)} stations and {sum(len(dests) for dests in graph.values())} edges")
    
    # Show some stations in the graph (for debugging)
    print("\nSample stations in the graph:")
    for station in list(graph.keys())[:10]:
        print(f"  - {station}")
    
    # Define some example paths to check
    test_paths = [
        ("oxford circus", "bank"),           # Central line
        ("baker street", "kings cross"),     # Metropolitan/Circle/H&C lines
        ("victoria", "oxford circus"),       # Victoria line
        ("waterloo", "london bridge"),       # Jubilee line
        ("paddington", "heathrow terminal 5"), # Picadilly line
        ("liverpool street", "stratford"),   # Central/Elizabeth line
        ("brixton", "walthamstow central"),  # Victoria line end-to-end
        ("ealing broadway", "upminster"),    # District line end-to-end
        ("hammersmith", "edgware road"),     # Additional test for newly handled stations
        ("shepherds bush", "white city"),    # Additional test for newly handled stations
        
        # Test the newly added stations
        ("finsbury park", "highbury and islington"),  # Test the Highbury & Islington station
        ("highbury and islington", "kings cross"),    # Test connection to Kings Cross
        ("wood lane", "shepherds bush market"),       # Test Shepherd's Bush Market station
        ("shepherds bush market", "goldhawk road"),   # Test another connection
        ("euston", "euston square"),                  # Test Euston Square station
        ("victoria", "st james park")                 # Test St James's Park station
    ]
    
    # Check each test path
    for start, end in test_paths:
        print(f"\nFinding path from '{start}' to '{end}':")
        result = find_shortest_path(graph, start, end)
        
        if result:
            path, time = result
            print(f"Found path with {len(path)} stations and travel time of {format_time(time)}:")
            for i in range(len(path) - 1):
                travel_time = graph[path[i]][path[i+1]]
                print(f"  {path[i]} → {path[i+1]}: {format_time(travel_time)}")
        else:
            print(f"No path found between '{start}' and '{end}'")

if __name__ == "__main__":
    main() 