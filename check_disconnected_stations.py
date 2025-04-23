#!/usr/bin/env python3
"""
This script analyzes the station_graph.json file to find disconnected stations.
It uses breadth-first search (BFS) to check which stations can reach other stations.
Stations that can't reach or be reached by others are considered disconnected.
"""

import json
from collections import deque, defaultdict
from typing import Dict, List, Set, Tuple

def load_graph(graph_file: str) -> Dict[str, Dict[str, float]]:
    """
    Load the station graph from the JSON file.
    
    Args:
        graph_file: Path to the graph JSON file
        
    Returns:
        The graph data structure
    """
    try:
        with open(graph_file, 'r') as f:
            graph = json.load(f)
        print(f"Loaded graph with {len(graph)} stations")
        return graph
    except Exception as e:
        print(f"Error loading graph: {str(e)}")
        exit(1)

def find_disconnected_stations(graph: Dict[str, Dict[str, float]]) -> Tuple[List[str], List[str], List[Set[str]]]:
    """
    Find stations that are disconnected from the main network.
    
    Args:
        graph: The station graph
        
    Returns:
        Tuple containing:
        1. List of completely isolated stations (no connections)
        2. List of stations that can't be reached from most other stations
        3. List of connected components in the graph
    """
    # Create a dictionary of all stations and their connections
    stations = set(graph.keys())
    
    # Check for completely isolated stations (no connections)
    isolated_stations = []
    for station, connections in graph.items():
        if not connections:
            isolated_stations.append(station)
    
    # Build an undirected graph for connected component analysis
    # This combines both directions (A→B and B→A) to find physical connectivity
    undirected_graph = defaultdict(set)
    for station, connections in graph.items():
        for connected_station in connections:
            undirected_graph[station].add(connected_station)
            undirected_graph[connected_station].add(station)
    
    # Find the connected components using BFS
    components = []
    unvisited = set(stations)
    
    while unvisited:
        # Start a new component
        start = next(iter(unvisited))
        component = set()
        
        # BFS to find all connected stations
        queue = deque([start])
        component.add(start)
        
        while queue:
            station = queue.popleft()
            for neighbor in undirected_graph.get(station, set()):
                if neighbor in unvisited and neighbor not in component:
                    queue.append(neighbor)
                    component.add(neighbor)
        
        # Remove the component's stations from unvisited
        unvisited -= component
        
        # Add the component to our list
        components.append(component)
    
    # Sort components by size (largest first)
    components.sort(key=len, reverse=True)
    
    # Find stations not in the largest component (disconnected islands)
    main_component = components[0] if components else set()
    disconnected_stations = []
    
    for station in stations:
        if station not in main_component and station not in isolated_stations:
            disconnected_stations.append(station)
    
    return isolated_stations, disconnected_stations, components

def check_reachability(graph: Dict[str, Dict[str, float]], start_station: str) -> Tuple[Set[str], Set[str]]:
    """
    Check which stations can be reached from the start station,
    and which stations can reach the start station.
    
    Args:
        graph: The station graph
        start_station: The starting station
        
    Returns:
        Tuple containing:
        1. Set of stations reachable from the start station
        2. Set of stations that can reach the start station
    """
    # Find stations reachable from the start station
    reachable_from_start = set()
    queue = deque([start_station])
    visited = {start_station}
    
    while queue:
        station = queue.popleft()
        reachable_from_start.add(station)
        
        for neighbor in graph.get(station, {}):
            if neighbor not in visited:
                queue.append(neighbor)
                visited.add(neighbor)
    
    # Create a reversed graph
    reversed_graph = defaultdict(dict)
    for station, connections in graph.items():
        for connected_station, time in connections.items():
            reversed_graph[connected_station][station] = time
    
    # Find stations that can reach the start station
    can_reach_start = set()
    queue = deque([start_station])
    visited = {start_station}
    
    while queue:
        station = queue.popleft()
        can_reach_start.add(station)
        
        for neighbor in reversed_graph.get(station, {}):
            if neighbor not in visited:
                queue.append(neighbor)
                visited.add(neighbor)
    
    return reachable_from_start, can_reach_start

def main():
    """
    Main function to analyze the graph for disconnected stations.
    """
    # File paths - use both original and normalized graph for comparison
    graph_file = "station_graph.json"
    normalized_graph_file = "station_graph.normalized.json"
    
    # Load the original graph
    print("Analyzing original graph...")
    graph = load_graph(graph_file)
    
    # Find disconnected stations
    isolated_stations, disconnected_stations, components = find_disconnected_stations(graph)
    
    # Print results
    print("\nRESULTS - ORIGINAL GRAPH")
    print("=======================")
    print(f"Total stations: {len(graph)}")
    print(f"Connected components: {len(components)}")
    
    if len(components) > 1:
        print("\nComponent sizes:")
        for i, component in enumerate(components, 1):
            print(f"  Component {i}: {len(component)} stations")
    
    if isolated_stations:
        print(f"\nCompletely isolated stations ({len(isolated_stations)}):")
        for station in sorted(isolated_stations):
            print(f"  - {station}")
    else:
        print("\nNo completely isolated stations found.")
    
    if disconnected_stations:
        print(f"\nStations in smaller components ({len(disconnected_stations)}):")
        for station in sorted(disconnected_stations):
            print(f"  - {station}")
    else:
        print("\nAll stations are in the main connected component.")
    
    # Load the normalized graph
    print("\nAnalyzing normalized graph...")
    try:
        normalized_graph = load_graph(normalized_graph_file)
        
        # Find disconnected stations
        norm_isolated, norm_disconnected, norm_components = find_disconnected_stations(normalized_graph)
        
        # Print results
        print("\nRESULTS - NORMALIZED GRAPH")
        print("=========================")
        print(f"Total stations: {len(normalized_graph)}")
        print(f"Connected components: {len(norm_components)}")
        
        if len(norm_components) > 1:
            print("\nComponent sizes:")
            for i, component in enumerate(norm_components, 1):
                print(f"  Component {i}: {len(component)} stations")
        
        if norm_isolated:
            print(f"\nCompletely isolated stations ({len(norm_isolated)}):")
            for station in sorted(norm_isolated):
                print(f"  - {station}")
        else:
            print("\nNo completely isolated stations found.")
        
        if norm_disconnected:
            print(f"\nStations in smaller components ({len(norm_disconnected)}):")
            for station in sorted(norm_disconnected):
                print(f"  - {station}")
        else:
            print("\nAll stations are in the main connected component.")
    except Exception as e:
        print(f"Error analyzing normalized graph: {str(e)}")
    
    # Check reachability for a sample station from the main component
    if components:
        sample_station = next(iter(components[0]))
        print(f"\nReachability Analysis for '{sample_station}':")
        
        reachable, can_reach = check_reachability(graph, sample_station)
        
        if len(reachable) < len(graph):
            print(f"  - Can reach {len(reachable)} out of {len(graph)} stations")
            unreachable = set(graph.keys()) - reachable
            print(f"  - Cannot reach {len(unreachable)} stations:")
            for station in sorted(list(unreachable)[:10]):
                print(f"    * {station}")
            if len(unreachable) > 10:
                print(f"    * ... and {len(unreachable) - 10} more")
        else:
            print(f"  - Can reach all {len(graph)} stations")
        
        if len(can_reach) < len(graph):
            print(f"  - Can be reached from {len(can_reach)} out of {len(graph)} stations")
            cant_reach = set(graph.keys()) - can_reach
            print(f"  - Cannot be reached from {len(cant_reach)} stations:")
            for station in sorted(list(cant_reach)[:10]):
                print(f"    * {station}")
            if len(cant_reach) > 10:
                print(f"    * ... and {len(cant_reach) - 10} more")
        else:
            print(f"  - Can be reached from all {len(graph)} stations")
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main() 