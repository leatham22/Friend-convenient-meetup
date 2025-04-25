#!/usr/bin/env python3
"""
Extract Line Edges

This script extracts adjacent station pairs from the network graph file,
organizing them by line. It creates a JSON file containing sets of adjacent 
stations grouped by line, including station IDs needed for TfL API calls.

Usage:
    python extract_line_edges.py

Output:
    Creates line_edges.json in the network_data directory
"""

import json
import os
from collections import defaultdict

def load_graph_data(file_path):
    """
    Load the network graph data from a JSON file.
    
    Args:
        file_path (str): Path to the graph JSON file
        
    Returns:
        dict: The loaded graph data
    """
    # Load the JSON file
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def extract_line_edges(graph_data):
    """
    Extract edges grouped by line from the network graph.
    
    Args:
        graph_data (dict): The network graph data
        
    Returns:
        dict: Edges grouped by line
    """
    # Get nodes and edges from the graph data
    nodes = graph_data.get('nodes', {})
    edges = graph_data.get('edges', [])
    
    # Dictionary to store edges by line
    line_edges = defaultdict(list)
    
    # Process all edges
    for edge in edges:
        # Skip transfer edges (zero weight)
        if edge.get('transfer', False) or edge.get('weight', 0) == 0:
            continue
        
        # Get edge information
        source = edge.get('source')
        target = edge.get('target')
        line = edge.get('line')
        line_name = edge.get('line_name', '')
        mode = edge.get('mode', '')
        
        # Skip if missing essential information
        if not all([source, target, line, mode]):
            continue
        
        # Get station IDs from nodes
        source_id = nodes.get(source, {}).get('id', '')
        target_id = nodes.get(target, {}).get('id', '')
        
        # Skip if IDs are missing
        if not source_id or not target_id:
            continue
        
        # Create edge data structure
        edge_data = {
            'source_name': source,
            'target_name': target,
            'source_id': source_id,
            'target_id': target_id,
            'line': line,
            'line_name': line_name,
            'mode': mode
        }
        
        # Add to line edges
        line_edges[line].append(edge_data)
    
    # Convert defaultdict to regular dict for JSON serialization
    return dict(line_edges)

def create_unique_station_pairs(line_edges):
    """
    Create unique station pairs for each line (to avoid duplicates in both directions).
    
    Args:
        line_edges (dict): Edges grouped by line
        
    Returns:
        dict: Unique station pairs by line
    """
    unique_pairs = {}
    
    for line, edges in line_edges.items():
        # Set to track unique pairs
        seen_pairs = set()
        unique_line_edges = []
        
        for edge in edges:
            # Create a frozenset of station IDs (order doesn't matter for uniqueness)
            station_pair = frozenset([edge['source_id'], edge['target_id']])
            
            # Skip if we've already seen this pair
            if station_pair in seen_pairs:
                continue
            
            # Add to unique edges and mark as seen
            unique_line_edges.append(edge)
            seen_pairs.add(station_pair)
        
        unique_pairs[line] = unique_line_edges
    
    return unique_pairs

def main():
    """Main function to extract and save line edges"""
    # File paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    graph_file = os.path.join(script_dir, 'networkx_graph_new.json')
    output_file = os.path.join(script_dir, 'line_edges.json')
    
    print(f"Loading graph data from {graph_file}...")
    graph_data = load_graph_data(graph_file)
    
    print("Extracting edges by line...")
    line_edges = extract_line_edges(graph_data)
    
    print("Creating unique station pairs...")
    unique_pairs = create_unique_station_pairs(line_edges)
    
    # Determine line counts
    line_counts = {line: len(edges) for line, edges in unique_pairs.items()}
    total_pairs = sum(line_counts.values())
    
    print(f"\nFound {total_pairs} unique station pairs across {len(unique_pairs)} lines:")
    for line, count in sorted(line_counts.items(), key=lambda x: x[1], reverse=True):
        line_name = next((edge['line_name'] for edge in unique_pairs[line] if edge['line_name']), line)
        print(f"  {line_name}: {count} station pairs")
    
    print(f"\nSaving data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(unique_pairs, file, indent=2)
    
    print("Done!")

if __name__ == "__main__":
    main() 