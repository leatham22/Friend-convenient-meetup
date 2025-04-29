#!/usr/bin/env python3
"""
Script to check the connectivity of the London transport network graph.

This script analyzes the graph structure to identify connectivity issues
that might prevent finding paths between certain stations.
"""

import os
import json
import networkx as nx
from collections import defaultdict

# Import our graph utility functions
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from network_data.graph_utils import load_graph_from_json

def get_connected_components(G):
    """
    Find all connected components in the graph.
    
    Args:
        G: NetworkX graph object
        
    Returns:
        List of sets of nodes, where each set represents a connected component
    """
    # For directed graphs, we need to use weakly_connected_components
    # This ignores edge directions when finding components
    if isinstance(G, nx.DiGraph):
        return list(nx.weakly_connected_components(G))
    else:
        return list(nx.connected_components(G))

def analyze_connectivity(G):
    """
    Analyze the connectivity of the graph.
    
    Args:
        G: NetworkX graph object
        
    Returns:
        Dictionary with connectivity analysis
    """
    # Get connected components
    components = get_connected_components(G)
    
    # Count stations by component
    component_sizes = [len(c) for c in components]
    
    # Sort components by size (largest first)
    sorted_components = sorted(zip(component_sizes, components), reverse=True)
    
    return {
        'total_components': len(components),
        'largest_component_size': sorted_components[0][0] if sorted_components else 0,
        'components': sorted_components
    }

def check_path_existence(G, source, target):
    """
    Check if a path exists between two stations and analyze why not if it doesn't.
    
    Args:
        G: NetworkX graph object
        source: Source station name
        target: Target station name
        
    Returns:
        Dictionary with path analysis results
    """
    results = {
        'source_exists': source in G.nodes,
        'target_exists': target in G.nodes,
        'path_exists': False,
        'reason': None,
        'same_component': False,
        'source_component_size': 0,
        'target_component_size': 0
    }
    
    # Check if both stations exist
    if not results['source_exists'] or not results['target_exists']:
        results['reason'] = "One or both stations don't exist in the graph"
        return results
    
    # Check if there's a path between them
    try:
        path = nx.shortest_path(G, source, target)
        results['path_exists'] = True
        results['path_length'] = len(path)
        return results
    except nx.NetworkXNoPath:
        results['reason'] = "No path exists between stations"
        
        # Find which components the stations are in
        components = get_connected_components(G)
        source_component = None
        target_component = None
        
        for i, component in enumerate(components):
            if source in component:
                source_component = (i, component)
            if target in component:
                target_component = (i, component)
                
            # If we've found both, we can stop searching
            if source_component and target_component:
                break
        
        # Check if they're in the same component
        if source_component and target_component:
            results['source_component_size'] = len(source_component[1])
            results['target_component_size'] = len(target_component[1])
            
            if source_component[0] == target_component[0]:
                results['same_component'] = True
                results['reason'] = "Stations are in the same component but no directed path exists"
            else:
                results['reason'] = f"Stations are in different components: {source_component[0]} and {target_component[0]}"
        
        return results

def find_stations_by_substring(G, substring):
    """
    Find stations that match a substring.
    
    Args:
        G: NetworkX graph object
        substring: Substring to search for (case-insensitive)
        
    Returns:
        List of matching station names
    """
    substring = substring.lower()
    return sorted([station for station in G.nodes if substring.lower() in station.lower()])

def analyze_example_paths(G):
    """
    Analyze a few example paths to check connectivity.
    
    Args:
        G: NetworkX graph object
    """
    # List of important station pairs to check
    station_pairs = [
        ("King's Cross St. Pancras Underground Station", "Waterloo Underground Station"),
        ("Paddington Underground Station", "Liverpool Street Underground Station"),
        ("Euston Underground Station", "Victoria Underground Station"),
        ("Bank Underground Station", "Oxford Circus Underground Station")
    ]
    
    print("\nAnalyzing paths between major stations:")
    for source, target in station_pairs:
        # Clean up station names (try to find them in the graph)
        source_matches = find_stations_by_substring(G, source.split()[0])
        target_matches = find_stations_by_substring(G, target.split()[0])
        
        if source_matches and target_matches:
            exact_source = next((s for s in source_matches if source.lower() in s.lower()), source_matches[0])
            exact_target = next((s for s in target_matches if target.lower() in s.lower()), target_matches[0])
            
            print(f"\nChecking path: {exact_source} -> {exact_target}")
            results = check_path_existence(G, exact_source, exact_target)
            
            if results['path_exists']:
                print(f"✅ Path exists with {results['path_length']} stations")
            else:
                print(f"❌ No path exists: {results['reason']}")
                if results['same_component']:
                    print(f"   Both stations are in the same component with {results['source_component_size']} stations")
                else:
                    print(f"   Source component has {results['source_component_size']} stations")
                    print(f"   Target component has {results['target_component_size']} stations")

def check_tube_line_connectivity(G, line_name):
    """
    Check if all stations on a tube line are connected.
    
    Args:
        G: NetworkX graph object
        line_name: Name of the tube line
        
    Returns:
        Dictionary with analysis results
    """
    # Find all stations on this line
    line_stations = []
    for node, attrs in G.nodes(data=True):
        lines = attrs.get('lines', [])
        if line_name in lines:
            line_stations.append(node)
    
    if not line_stations:
        return {
            'line': line_name,
            'station_count': 0,
            'is_connected': False,
            'component_count': 0,
            'largest_component_size': 0,
            'reason': "No stations found for this line"
        }
    
    # Create a subgraph with just these stations
    subgraph = G.subgraph(line_stations).copy()
    
    # Check if it's connected
    components = get_connected_components(subgraph)
    
    return {
        'line': line_name,
        'station_count': len(line_stations),
        'is_connected': len(components) == 1,
        'component_count': len(components),
        'largest_component_size': max(len(c) for c in components) if components else 0
    }

def main():
    """Main function to analyze graph connectivity."""
    print("Loading London transport network graph...")
    G = load_graph_from_json()
    
    # Analyze overall connectivity
    print(f"\nGraph has {G.number_of_nodes()} stations and {G.number_of_edges()} connections")
    
    connectivity = analyze_connectivity(G)
    print(f"\nConnectivity analysis:")
    print(f"- Graph has {connectivity['total_components']} connected components")
    print(f"- Largest component has {connectivity['largest_component_size']} stations " +
          f"({connectivity['largest_component_size']/G.number_of_nodes():.1%} of total)")
    
    # Print information about all components
    if connectivity['total_components'] > 1:
        print("\nConnected components:")
        for i, (size, component) in enumerate(connectivity['components'][:5]):  # Show top 5
            # Sample a few stations from this component
            sample_stations = sorted(list(component))[:3]
            print(f"  Component {i+1}: {size} stations")
            print(f"    Sample stations: {', '.join(sample_stations)}")
    
    # Check example paths
    analyze_example_paths(G)
    
    # Check connectivity of main tube lines
    main_lines = ['bakerloo', 'central', 'circle', 'district', 'hammersmith-city', 
                  'jubilee', 'metropolitan', 'northern', 'piccadilly', 'victoria', 'waterloo-city']
    
    print("\nAnalyzing tube line connectivity:")
    for line in main_lines:
        results = check_tube_line_connectivity(G, line)
        if results['is_connected']:
            print(f"✅ {line}: All {results['station_count']} stations are connected")
        else:
            print(f"❌ {line}: {results['station_count']} stations in {results['component_count']} components")
            print(f"   Largest component: {results['largest_component_size']} stations")
    
    print("\nDone!")

if __name__ == "__main__":
    main() 