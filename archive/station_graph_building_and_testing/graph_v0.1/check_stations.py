"""
This script checks for stations matching the given search terms in the graph.
"""

#!/usr/bin/env python3
import json

def check_for_stations(graph_path, search_terms):
    """
    Check for stations matching the given search terms in the graph.
    
    Args:
        graph_path: Path to the station graph JSON
        search_terms: List of terms to search for in station names
    """
    # Load the graph
    with open(graph_path, 'r') as f:
        graph = json.load(f)
    
    print(f"Loaded graph with {len(graph)} stations")
    
    # For each search term, find all matching stations
    for term in search_terms:
        matching_stations = []
        for station in graph:
            if term.lower() in station.lower():
                matching_stations.append(station)
        
        # Print the results
        if matching_stations:
            print(f"\nStations matching '{term}':")
            for station in sorted(matching_stations):
                print(f"  - '{station}'")
        else:
            print(f"\nNo stations found matching '{term}'")

if __name__ == "__main__":
    # Path to the graph
    graph_path = "station_graph.json"
    
    # Terms to search for
    search_terms = [
        "heathrow",
        "walthamstow",
        "king",
        "pancras",
        "terminal"
    ]
    
    # Check for stations
    check_for_stations(graph_path, search_terms) 