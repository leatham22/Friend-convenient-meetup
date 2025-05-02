#!/usr/bin/env python3
"""
Test script to demonstrate how the normalized station names work with user input.
This shows the process of:
1. Normalizing user input to find a station in the metadata
2. Using the exact same name to find the station in the graph
"""

import json
from archive.normalize_stations import normalize_name


def test_normalization():
    """
    Test the normalization process with sample user inputs.
    Shows how normalized station names match across both datasets.
    """
    # ---------- REAL APPLICATION WORKFLOW ----------
    print("\nSIMULATED APPLICATION WORKFLOW:")
    print("==============================")
    
    # Load the original station metadata (not normalized file)
    with open("slim_stations/unique_stations.json", "r") as f:
        metadata = json.load(f)
    
    # Create a dictionary for quick lookups with normalized names as keys
    station_dict = {}
    for station in metadata:
        # Normalize the station name
        norm_name = normalize_name(station["name"])
        station_dict[norm_name] = station
        
        # Also index child stations
        for child in station.get("child_stations", []):
            norm_child = normalize_name(child)
            if norm_child != norm_name:  # Avoid duplicates
                station_dict[norm_child] = station
    
    # Load the graph data
    with open("station_graph.json", "r") as f:
        graph_data = json.load(f)
    
    # Test some user inputs
    test_inputs = [
        "King's Cross",
        "Paddington",
        "Baker Street",
        "baker st",
        "Victoria",
        "Walthamstow Central"
    ]
    
    for user_input in test_inputs:
        print(f"\nUser input: '{user_input}'")
        
        # Normalize user input
        normalized = normalize_name(user_input)
        print(f"Normalized: '{normalized}'")
        
        # Look up in metadata
        if normalized in station_dict:
            station = station_dict[normalized]
            print(f"✅ Found in metadata as: '{station['name']}'")
            print(f"   Coordinates: {station['lat']}, {station['lon']}")
            
            # Look up in graph with the SAME normalized name
            if normalized in graph_data:
                connections = len(graph_data[normalized])
                print(f"✅ Found in graph with {connections} connections")
                print(f"   First connection: {list(graph_data[normalized].items())[0]}")
                print("✅ Match across datasets: Yes")
            else:
                print("❌ Not found in graph")
                print("❌ Match across datasets: No")
        else:
            print("❌ Not found in metadata")
            if normalized in graph_data:
                print("✅ Found in graph")
                print("❌ Match across datasets: No")
            else:
                print("❌ Not found in graph")
                print("❌ Match across datasets: No")
    
    print("\n" + "="*40)
    print("CONCLUSION")
    print("="*40)
    print("The normalization process needs these steps:")
    print("1. When processing station data:")
    print("   - Normalize all station names consistently")
    print("   - Update both metadata and graph files to use the same normalized names")
    print("   - Special cases like Walthamstow need manual handling to ensure consistency")
    print("2. In the application:")
    print("   - Normalize user input the same way")
    print("   - Use normalized name to look up in both datasets")
    print("   - This ensures consistent handling across all data sources")


if __name__ == "__main__":
    test_normalization() 