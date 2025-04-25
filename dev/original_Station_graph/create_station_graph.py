"""
This script creates a station graph from a station JSON file and a travel times CSV file.
It normalizes the station names and creates a graph of travel times between stations.
"""

#!/usr/bin/env python3
import json  # For reading/writing JSON files
import csv   # For processing CSV data
import sys   # For writing to stderr
import re    # For regular expressions to help with name normalization
from typing import Dict, List, Set, Tuple, Any  # Type hints for better code documentation

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
        
    # Handle Euston and Euston Square as separate stations
    if "euston square" in name:
        name = "euston square"  # Keep Euston Square distinct
    elif "euston" in name:
        name = "euston"  # Normalize other Euston variants
    
    # Handle Highbury & Islington
    if "highbury" in name or "highbury and islington" in name:
        name = "highbury and islington"  # Normalize Highbury variants
    
    # Handle Kensington Olympia
    if "kensington olympia" in name:
        name = "kensington olympia"  # Normalize Kensington Olympia variants

    # Handle different Shepherd's Bush stations
    if "shepherds bush market" in name:
        name = "shepherds bush market"  # For Shepherd's Bush Market
    elif "shepherds bush" in name:
        name = "shepherds bush"  # For Shepherd's Bush (Central line)
    
    # Remove non-alphanumeric characters (except spaces)
    name = re.sub(r'[^\w\s]', '', name)
    
    # Normalize whitespace (replace multiple spaces with a single space)
    name = re.sub(r'\s+', ' ', name)
    
    # Strip leading/trailing whitespace
    name = name.strip()
    
    return name

def load_stations(json_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Load station data from JSON file and create a mapping of normalized names to parent stations.
    Also creates a mapping of child stations to their parent stations.
    
    Args:
        json_path: Path to the station JSON file
        
    Returns:
        Dictionary with two mappings:
        - 'parent_map': Maps normalized child station names to their parent station names
        - 'stations': Maps normalized station names to their original station data
    """
    # Read the JSON file containing station data
    with open(json_path, 'r') as f:
        stations_data = json.load(f)
    
    # Create two mapping dictionaries to organize the station data
    parent_map = {}  # Will map any station name to its parent station name
    stations = {}    # Will store the full station data keyed by normalized station name
    original_to_normalized = {}  # Maps original names to normalized names for debugging
    
    # Track the full number of original stations
    total_stations = len(stations_data)
    
    # Process each station in the JSON data
    for station in stations_data:
        # Get the original name
        original_name = station['name']
        
        # Normalize the parent station name by converting to lowercase and removing whitespace
        parent_name = normalize_station_name(original_name)
        
        # Store the mapping from original to normalized for debugging
        original_to_normalized[original_name] = parent_name
        
        # Add the parent station data to our stations dictionary
        stations[parent_name] = station
        
        # Add parent to itself in parent_map (a parent is its own parent)
        parent_map[parent_name] = parent_name
        
        # For each child station, map it to its parent station
        for child in station.get('child_stations', []):
            # Normalize the child station name
            child_name = normalize_station_name(child)
            # Map this child to its parent
            parent_map[child_name] = parent_name
            # Store original to normalized mapping
            original_to_normalized[child] = child_name
    
    # Add special manual mappings for known station variants that occur in the CSV
    special_mappings = {
        "edgware road": "edgware road",
        "paddington handc": "paddington",
        "paddington circle": "paddington",
        "paddington dis": "paddington",
        "baker street met": "baker street",
        "baker street metropolitan": "baker street",
        "baker street circle": "baker street",
        "hammersmith handc": "hammersmith",
        "hammersmith district": "hammersmith",
        "euston cx": "euston",
        "euston city": "euston",
        "kennington city": "kennington",
        "kennington cx": "kennington",
        "finchley central hb": "finchley central",
        "st james park": "st jamess park",
        "new cross": "new cross gate",  # Map to closest match
        "shepherds bush": "shepherds bush central"  # Map to Central line station
    }
    
    # Add these special mappings to our parent_map
    for variant, parent in special_mappings.items():
        if parent in parent_map:
            parent_map[variant] = parent_map[parent]
    
    # Print some debug information
    print(f"Loaded {total_stations} original stations")
    print(f"Normalized to {len(stations)} unique station names")
    print(f"Mapped {len(parent_map)} station names to parent stations")
    
    # Return all the mappings as a dictionary
    return {
        'parent_map': parent_map, 
        'stations': stations,
        'original_to_normalized': original_to_normalized
    }

def create_csv_station_to_normalized_map(csv_path: str) -> Dict[str, str]:
    """
    Create a mapping from CSV station names to normalized station names.
    This helps identify stations that might be in the CSV but not match our normalization pattern.
    
    Args:
        csv_path: Path to the CSV file with travel times
        
    Returns:
        Dictionary mapping original CSV station names to their normalized versions
    """
    csv_stations = set()
    mapping = {}
    
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
            
            csv_stations.add(start_station)
            csv_stations.add(end_station)
    
    # Create the mapping of original names to normalized names
    for station in csv_stations:
        mapping[station] = normalize_station_name(station)
    
    return mapping

def load_travel_times(csv_path: str, parent_map: Dict[str, str], original_to_normalized: Dict[str, str]) -> Dict[str, Dict[str, float]]:
    """
    Build a directed graph of travel times between parent stations.
    
    Args:
        csv_path: Path to the CSV file with travel times
        parent_map: Mapping of normalized station names to parent stations
        original_to_normalized: Mapping of original to normalized station names for debugging
        
    Returns:
        Dictionary where keys are parent station names and values are dictionaries 
        mapping destination stations to travel times in minutes
    """
    # Initialize an empty graph as a dictionary of dictionaries
    # Each key is a station and its value is another dictionary mapping destination stations to travel times
    graph = {}
    
    # Create a mapping from CSV station names to normalized names
    csv_station_mapping = create_csv_station_to_normalized_map(csv_path)
    
    # Keep track of station names we couldn't find
    unknown_stations = set()
    
    # Keep track of how many rows we processed and how many we skipped
    rows_processed = 0
    rows_skipped = 0
    edges_created = 0
    
    # Column names we expect in the CSV
    from_station_col = 'Station from (A)'
    to_station_col = 'Station to (B)'
    unimpeded_time_col = 'Un-impeded Running Time (Mins)'
    interpeak_time_col = 'Inter peak (1000 - 1600) Running time (mins)'
    
    # Open and read the CSV file containing travel times
    with open(csv_path, 'r') as f:
        # Skip the first line (which is empty commas)
        next(f)
        
        # Read the second line which contains the headers
        headers_line = next(f).strip()
        headers = [h.strip() for h in headers_line.split(',')]
        
        # Create a CSV reader with these headers
        reader = csv.DictReader(f, fieldnames=headers, skipinitialspace=True)
        
        # Process each row in the CSV file
        for row_num, row in enumerate(reader, start=3):  # Start at 3 since we've read 2 lines already
            # Skip empty rows or rows without station names
            if not row.get(from_station_col) or not row.get(to_station_col):
                continue
            
            rows_processed += 1
            
            # Get original station names
            start_original = row[from_station_col].strip()
            dest_original = row[to_station_col].strip()
            
            # Normalize station names using our mapping
            start_name = csv_station_mapping.get(start_original)
            dest_name = csv_station_mapping.get(dest_original)
            
            # Check if we can find these stations in our parent_map
            # If not, we can't map them to parent stations, so we'll skip this row
            if start_name not in parent_map:
                unknown_stations.add(start_original)
                rows_skipped += 1
                continue
                
            if dest_name not in parent_map:
                unknown_stations.add(dest_original)
                rows_skipped += 1
                continue
                
            # Look up the parent stations for both the start and destination
            parent_start = parent_map.get(start_name)
            parent_dest = parent_map.get(dest_name)
            
            # Skip if start and end are the same parent station
            # This happens with transfers at the same station, which are zero-cost in our model
            if parent_start == parent_dest:
                rows_skipped += 1
                continue
            
            # Extract the travel time from the row
            # We'll try to use UnimpededTravelTime first, then fall back to InterPeakTravelTime
            travel_time = None
            unimpeded_time = row.get(unimpeded_time_col, '')
            interpeak_time = row.get(interpeak_time_col, '')
            
            # Try to convert the unimpeded time to a float if it exists and is a number
            if unimpeded_time and unimpeded_time.strip() and unimpeded_time.replace('.', '', 1).isdigit():
                # Keep time in minutes (NOT converting to seconds)
                travel_time = float(unimpeded_time)
            # If unimpeded time isn't available, try interpeak time
            elif interpeak_time and interpeak_time.strip() and interpeak_time.replace('.', '', 1).isdigit():
                # Keep time in minutes (NOT converting to seconds)
                travel_time = float(interpeak_time)
            else:
                # Skip this row if we can't find a valid travel time
                rows_skipped += 1
                continue
            
            # Initialize a graph entry for this parent station if it doesn't exist yet
            if parent_start not in graph:
                graph[parent_start] = {}
            
            # Add or update the edge with the minimum travel time
            # If we've already seen this edge, only keep the faster time
            if parent_dest not in graph[parent_start] or travel_time < graph[parent_start][parent_dest]:
                graph[parent_start][parent_dest] = travel_time
                edges_created += 1
            
    # Print information about stations we couldn't find
    if unknown_stations:
        print(f"WARNING: {len(unknown_stations)} stations from CSV were not found in station JSON:")
        for station in sorted(list(unknown_stations)[:10]):  # Show first 10 for brevity
            normalized = csv_station_mapping.get(station, "unknown")
            print(f"  - '{station}' (normalized: '{normalized}')")
        if len(unknown_stations) > 10:
            print(f"  - ... and {len(unknown_stations) - 10} more")
    
    # Print statistics about rows processed
    print(f"Processed {rows_processed} rows from CSV")
    print(f"Skipped {rows_skipped} rows")
    print(f"Created {edges_created} edges in the graph")
    
    # Return the completed graph
    return graph

def create_station_graph(stations_json_path: str, travel_times_csv_path: str, output_path: str) -> None:
    """
    Main function to create station graph and save it to JSON.
    
    Args:
        stations_json_path: Path to the station JSON file
        travel_times_csv_path: Path to the travel times CSV file
        output_path: Path to save the output graph JSON
    """
    # Step 1: Load station data from JSON file
    print(f"Loading stations from {stations_json_path}...")
    station_data = load_stations(stations_json_path)
    # Extract the parent_map which maps any station to its parent station
    parent_map = station_data['parent_map']
    original_to_normalized = station_data['original_to_normalized']
    
    # Step 2: Load travel times from CSV and build the graph
    print(f"Loading travel times from {travel_times_csv_path}...")
    graph = load_travel_times(travel_times_csv_path, parent_map, original_to_normalized)
    
    # Step 3: Save the graph to a JSON file
    print(f"Saving graph to {output_path}...")
    with open(output_path, 'w') as f:
        # indent=2 makes the JSON file more readable with proper indentation
        json.dump(graph, f, indent=2)
    
    # Step 4: Print some statistics about the generated graph
    total_nodes = len(graph)  # Number of stations (nodes)
    # Sum up all the destinations for each station to get total edges
    total_edges = sum(len(destinations) for destinations in graph.values())
    print(f"Created graph with {total_nodes} nodes and {total_edges} edges.")
    
    # Show some example edges from the first node in the graph
    if graph:
        print(f"Example edges from first node:")
        # Get the first node in the graph
        first_node = next(iter(graph))
        # Show up to 5 edges from this node
        for dest, time in list(graph[first_node].items())[:5]:
            print(f"  {first_node} -> {dest}: {time} minutes")

if __name__ == "__main__":
    # Define the paths to input and output files
    stations_json_path = "slim_stations/unique_stations.json"  # Path to station data
    travel_times_csv_path = "Inter_station_times.csv"         # Path to travel times data
    output_path = "station_graph.json"                        # Where to save the resulting graph
    
    # Call the main function to create the graph
    create_station_graph(stations_json_path, travel_times_csv_path, output_path)
    print("Done!") 