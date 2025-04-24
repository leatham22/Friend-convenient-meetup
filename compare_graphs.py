#!/usr/bin/env python3
"""
Compare the structure of the old and new network graphs to analyze improvements.
"""

import json
import os
from collections import defaultdict, Counter

# File paths
OLD_GRAPH_FILE = os.path.join("network_data", "networkx_graph.json")
NEW_GRAPH_FILE = os.path.join("network_data", "networkx_graph_new.json")

def load_graph(file_path):
    """Load graph data from a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def analyze_graph(graph_data):
    """Analyze graph structure and return statistics."""
    stats = {}
    
    # Basic stats
    stats["node_count"] = len(graph_data["nodes"])
    stats["edge_count"] = len(graph_data["edges"])
    
    # Count edges by line
    line_edge_counts = defaultdict(int)
    for edge in graph_data["edges"]:
        line = edge.get("line", "unknown")
        line_edge_counts[line] += 1
    stats["edges_by_line"] = dict(line_edge_counts)
    
    # Count bidirectional edges
    edge_pairs = set()
    for edge in graph_data["edges"]:
        source = edge.get("source", "")
        target = edge.get("target", "")
        if source and target:
            edge_pairs.add((source, target))
    
    bidirectional_count = 0
    for source, target in edge_pairs:
        if (target, source) in edge_pairs:
            bidirectional_count += 1
    
    stats["bidirectional_edge_count"] = bidirectional_count // 2  # Divide by 2 to count pairs once
    
    # Count transfer edges
    transfer_edges = [edge for edge in graph_data["edges"] if edge.get("transfer", False)]
    stats["transfer_edge_count"] = len(transfer_edges)
    
    # Check if all nodes have edges
    nodes_with_edges = set()
    for edge in graph_data["edges"]:
        nodes_with_edges.add(edge.get("source", ""))
        nodes_with_edges.add(edge.get("target", ""))
    
    stats["nodes_without_edges"] = len(graph_data["nodes"]) - len(nodes_with_edges)
    
    # Count edges by mode
    mode_edge_counts = defaultdict(int)
    for edge in graph_data["edges"]:
        mode = edge.get("mode", "unknown")
        mode_edge_counts[mode] += 1
    stats["edges_by_mode"] = dict(mode_edge_counts)
    
    return stats

def compare_stations(old_graph, new_graph):
    """Compare stations between old and new graphs."""
    old_stations = set(old_graph["nodes"].keys())
    new_stations = set(new_graph["nodes"].keys())
    
    only_in_old = old_stations - new_stations
    only_in_new = new_stations - old_stations
    
    print("\nStation comparison:")
    print(f"Stations only in old graph: {len(only_in_old)}")
    if only_in_old:
        print("Examples:", list(only_in_old)[:5])
    
    print(f"Stations only in new graph: {len(only_in_new)}")
    if only_in_new:
        print("Examples:", list(only_in_new)[:5])
    
    print(f"Stations in both graphs: {len(old_stations & new_stations)}")

def compare_connections(old_graph, new_graph):
    """Compare connections between old and new graphs."""
    # Create sets of connections
    old_connections = set()
    for edge in old_graph["edges"]:
        source = edge.get("source", "")
        target = edge.get("target", "")
        line = edge.get("line", "")
        if source and target:
            old_connections.add((source, target, line))
    
    new_connections = set()
    for edge in new_graph["edges"]:
        source = edge.get("source", "")
        target = edge.get("target", "")
        line = edge.get("line", "")
        if source and target:
            new_connections.add((source, target, line))
    
    only_in_old = old_connections - new_connections
    only_in_new = new_connections - old_connections
    
    print("\nConnection comparison:")
    print(f"Connections only in old graph: {len(only_in_old)}")
    if only_in_old:
        print("Examples:", list(only_in_old)[:5])
    
    print(f"Connections only in new graph: {len(only_in_new)}")
    if only_in_new:
        print("Examples:", list(only_in_new)[:5])
    
    print(f"Connections in both graphs: {len(old_connections & new_connections)}")

def main():
    """Main function to compare graph structures."""
    print("Comparing old and new network graphs...")
    
    # Load graphs
    old_graph = load_graph(OLD_GRAPH_FILE)
    new_graph = load_graph(NEW_GRAPH_FILE)
    
    # Analyze graphs
    old_stats = analyze_graph(old_graph)
    new_stats = analyze_graph(new_graph)
    
    # Print basic statistics
    print("\nBasic statistics:")
    print(f"Old graph: {old_stats['node_count']} nodes, {old_stats['edge_count']} edges")
    print(f"New graph: {new_stats['node_count']} nodes, {new_stats['edge_count']} edges")
    
    print("\nBidirectional edges:")
    print(f"Old graph: {old_stats['bidirectional_edge_count']} bidirectional pairs")
    print(f"New graph: {new_stats['bidirectional_edge_count']} bidirectional pairs")
    
    print("\nTransfer edges:")
    print(f"Old graph: {old_stats['transfer_edge_count']} transfer edges")
    print(f"New graph: {new_stats['transfer_edge_count']} transfer edges")
    
    print("\nNodes without edges:")
    print(f"Old graph: {old_stats['nodes_without_edges']} isolated nodes")
    print(f"New graph: {new_stats['nodes_without_edges']} isolated nodes")
    
    # Compare top lines by edge count
    print("\nTop 5 lines by edge count (old graph):")
    for line, count in sorted(old_stats['edges_by_line'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {line}: {count} edges")
    
    print("\nTop 5 lines by edge count (new graph):")
    for line, count in sorted(new_stats['edges_by_line'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {line}: {count} edges")
    
    # Compare stations
    compare_stations(old_graph, new_graph)
    
    # Compare connections
    compare_connections(old_graph, new_graph)
    
    print("\nDone!")

if __name__ == "__main__":
    main() 