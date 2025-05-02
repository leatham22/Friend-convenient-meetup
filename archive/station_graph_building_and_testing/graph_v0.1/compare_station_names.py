#!/usr/bin/env python3
"""
This script compares the station names in station_graph.backup.updated.json
with those in slim_stations/unique_stations.json to verify that the names
match exactly without requiring normalization.

It will report any stations that appear in one file but not the other,
helping to ensure that our update script worked correctly.
"""

import json

def load_station_metadata(file_path):
    """
    Load station metadata from JSON file and extract station names.
    
    Args:
        file_path: Path to the metadata JSON file
        
    Returns:
        Set of station names
    """
    # Load the metadata file
    with open(file_path, 'r') as f:
        metadata = json.load(f)
    
    # Extract station names 
    station_names = set()
    child_to_parent = {}
    
    # Process each station
    for station in metadata:
        # Get the station name and add it to the set
        station_name = station['name']
        station_names.add(station_name)
        
        # Also add child stations to the mapping (for reference in results)
        for child_name in station.get('child_stations', []):
            child_to_parent[child_name] = station_name
            station_names.add(child_name)
    
    print(f"Loaded {len(station_names)} station names from metadata")
    return station_names, child_to_parent

def load_graph_stations(file_path):
    """
    Load station graph from JSON file and extract station names.
    
    Args:
        file_path: Path to the graph JSON file
        
    Returns:
        Set of station names in the graph
    """
    # Load the graph file
    with open(file_path, 'r') as f:
        graph = json.load(f)
    
    # Extract station names (keys in the graph)
    station_names = set(graph.keys())
    
    # Also check for station names in the connections
    all_connections = set()
    for connections in graph.values():
        all_connections.update(connections.keys())
    
    # Report if there are connections to stations not in the graph keys
    undefined_stations = all_connections - station_names
    if undefined_stations:
        print(f"Warning: Found {len(undefined_stations)} stations in connections that are not defined in the graph:")
        for station in sorted(undefined_stations):
            print(f"  - '{station}'")
    
    print(f"Loaded {len(station_names)} station names from graph")
    return station_names

def compare_stations(metadata_stations, graph_stations):
    """
    Compare station names between metadata and graph.
    
    Args:
        metadata_stations: Set of station names from metadata
        graph_stations: Set of station names from graph
        
    Returns:
        Dictionary with sets of mismatched stations
    """
    # Find stations in metadata but not in graph
    metadata_only = metadata_stations - graph_stations
    
    # Find stations in graph but not in metadata
    graph_only = graph_stations - metadata_stations
    
    return {
        'metadata_only': metadata_only,
        'graph_only': graph_only
    }

def main():
    """
    Main function to compare station names between files.
    """
    # File paths
    metadata_file = "slim_stations/unique_stations.json"
    graph_file = "station_graph.normalized.json"
    
    print(f"Comparing station names between:")
    print(f"  - {metadata_file}")
    print(f"  - {graph_file}")
    print()
    
    # Load station names from metadata
    try:
        metadata_stations, child_to_parent = load_station_metadata(metadata_file)
    except Exception as e:
        print(f"Error loading metadata: {str(e)}")
        return
    
    # Load station names from graph
    try:
        graph_stations = load_graph_stations(graph_file)
    except Exception as e:
        print(f"Error loading graph: {str(e)}")
        return
    
    # Compare stations
    mismatches = compare_stations(metadata_stations, graph_stations)
    
    # Print results
    print("\nCOMPARISON RESULTS:")
    print("===================")
    
    # Check if there are any mismatches
    if not mismatches['metadata_only'] and not mismatches['graph_only']:
        print("\n✅ SUCCESS: All station names match exactly between files!")
        print(f"Both files contain the same {len(metadata_stations.intersection(graph_stations))} station names.")
    else:
        # Report stations in metadata but not in graph
        if mismatches['metadata_only']:
            # Separate parent and child stations in results
            parent_stations = set()
            child_stations = set()
            for station in mismatches['metadata_only']:
                if station in child_to_parent.values() or station not in child_to_parent:
                    parent_stations.add(station)
                else:
                    child_stations.add(station)
            
            print(f"\n❌ Found {len(mismatches['metadata_only'])} stations in metadata but not in graph:")
            
            if parent_stations:
                print(f"\nParent stations missing from graph ({len(parent_stations)}):")
                for station in sorted(parent_stations):
                    print(f"  - '{station}'")
            
            if child_stations:
                print(f"\nChild stations missing from graph ({len(child_stations)}):")
                for station in sorted(child_stations):
                    parent = child_to_parent.get(station, "Unknown")
                    print(f"  - '{station}' (parent: '{parent}')")
        else:
            print("\n✅ All metadata stations are present in the graph.")
        
        # Report stations in graph but not in metadata
        if mismatches['graph_only']:
            print(f"\n❌ Found {len(mismatches['graph_only'])} stations in graph but not in metadata:")
            for station in sorted(mismatches['graph_only']):
                print(f"  - '{station}'")
        else:
            print("\n✅ All graph stations are present in the metadata.")
    
    # Print conclusion
    print("\nCONCLUSION:")
    print("===========")
    if not mismatches['metadata_only'] and not mismatches['graph_only']:
        print("The update script has successfully aligned all station names.")
        print("The graph now uses the exact same station names as the metadata file.")
        print("This eliminates the need for normalization at runtime.")
    else:
        print("Some station names still don't match exactly between files.")
        if mismatches['metadata_only'] and mismatches['graph_only']:
            print("Consider updating the manual mappings in the update script.")
        elif mismatches['metadata_only']:
            print("There are stations in the metadata that are not in the graph.")
            print("This is expected for DLR, Overground, and Elizabeth Line stations, which will be added later.")
        else:
            print("There are stations in the graph that don't exist in the metadata.")
            print("This needs to be fixed by updating the mappings in the script.")

if __name__ == "__main__":
    main() 