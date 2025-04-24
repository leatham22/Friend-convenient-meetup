#!/usr/bin/env python3
"""
Test script to verify that all stations in slim_stations/unique_stations.json
are also present in our NetworkX graph.

This script compares both datasets to ensure complete station coverage
and identifies any stations that might be missing from the graph.
"""

import json
import os
import sys
from collections import defaultdict

# Output file paths
GRAPH_FILE = os.path.join("network_data", "networkx_graph_fixed.json")
OLD_STATIONS_FILE = os.path.join("slim_stations", "unique_stations.json")

def load_json_file(file_path):
    """Load a JSON file and return its contents."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading {file_path}: {e}")
        return None

def get_graph_stations():
    """Get a set of station names from the NetworkX graph."""
    graph_data = load_json_file(GRAPH_FILE)
    if not graph_data:
        return set()
    
    # Extract all station names from the graph
    return set(graph_data.get("nodes", {}).keys())

def get_old_stations():
    """Get a set of station names from the old slim_stations file."""
    old_stations_data = load_json_file(OLD_STATIONS_FILE)
    if not old_stations_data:
        return set()
    
    # Extract all station names, including parent and child stations
    stations = set()
    child_stations = set()
    
    for station in old_stations_data:
        # Add parent station
        stations.add(station.get("name", ""))
        
        # Add child stations
        for child in station.get("child_stations", []):
            stations.add(child)
            child_stations.add(child)
    
    return stations, child_stations

def check_missing_stations():
    """Check for missing stations in the graph compared to the old data."""
    graph_stations = get_graph_stations()
    old_stations, child_stations = get_old_stations()
    
    # Find stations missing from the graph
    missing_stations = old_stations - graph_stations
    
    # Group missing stations by type (parent or child)
    missing_parent_stations = missing_stations - child_stations
    missing_child_stations = missing_stations & child_stations
    
    return missing_parent_stations, missing_child_stations

def find_parent_for_children(missing_child_stations):
    """Find the parent stations for missing child stations."""
    old_stations_data = load_json_file(OLD_STATIONS_FILE)
    if not old_stations_data:
        return {}
    
    # Create a mapping of child to parent
    child_to_parent = {}
    for station in old_stations_data:
        parent_name = station.get("name", "")
        for child in station.get("child_stations", []):
            if child in missing_child_stations:
                child_to_parent[child] = parent_name
    
    return child_to_parent

def check_edge_connections():
    """Check if all parent-child station pairs have zero-weight edges."""
    graph_data = load_json_file(GRAPH_FILE)
    old_stations_data = load_json_file(OLD_STATIONS_FILE)
    
    if not graph_data or not old_stations_data:
        return []
    
    # Create a set of all expected parent-child connections
    expected_connections = set()
    for station in old_stations_data:
        parent_name = station.get("name", "")
        for child in station.get("child_stations", []):
            # Add both directions
            expected_connections.add((parent_name, child))
            expected_connections.add((child, parent_name))
    
    # Create a set of all actual connections in the graph
    actual_connections = set()
    for edge in graph_data.get("edges", []):
        source = edge.get("source", "")
        target = edge.get("target", "")
        weight = edge.get("weight", 1)
        transfer = edge.get("transfer", False)
        
        # Only include zero-weight transfer edges
        if weight == 0 and transfer and source and target:
            actual_connections.add((source, target))
    
    # Find missing connections
    missing_connections = expected_connections - actual_connections
    
    return missing_connections

def main():
    """Main function to run all station coverage tests."""
    print("Testing station coverage in NetworkX graph...")
    
    # Check for missing stations
    missing_parent_stations, missing_child_stations = check_missing_stations()
    
    print(f"\nStation coverage results:")
    print(f"-------------------------")
    
    if not missing_parent_stations and not missing_child_stations:
        print("✅ All stations from slim_stations/unique_stations.json are present in the graph")
    else:
        print(f"❌ Found {len(missing_parent_stations) + len(missing_child_stations)} missing stations:")
        
        if missing_parent_stations:
            print(f"\n  Missing parent stations ({len(missing_parent_stations)}):")
            for station in sorted(missing_parent_stations):
                print(f"  - {station}")
        
        if missing_child_stations:
            child_to_parent = find_parent_for_children(missing_child_stations)
            print(f"\n  Missing child stations ({len(missing_child_stations)}):")
            for child in sorted(missing_child_stations):
                parent = child_to_parent.get(child, "Unknown parent")
                print(f"  - {child} (Parent: {parent})")
    
    # Check for missing connections
    missing_connections = check_edge_connections()
    
    if not missing_connections:
        print("\n✅ All parent-child station pairs have zero-weight transfer edges")
    else:
        print(f"\n❌ Found {len(missing_connections)} missing zero-weight transfer edges:")
        
        # Group by parent station for better readability
        connections_by_parent = defaultdict(list)
        for parent, child in missing_connections:
            # Only show one direction to avoid duplication
            if (child, parent) in missing_connections and parent < child:
                connections_by_parent[parent].append(child)
        
        for parent, children in sorted(connections_by_parent.items()):
            if children:
                print(f"  - {parent} <-> {', '.join(sorted(children))}")
    
    return 0 if not (missing_parent_stations or missing_child_stations or missing_connections) else 1

if __name__ == "__main__":
    sys.exit(main()) 