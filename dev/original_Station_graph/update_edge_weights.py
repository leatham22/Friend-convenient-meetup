#!/usr/bin/env python3
"""
Update Edge Weights in Graph JSON

This script loads the network graph data from 'networkx_graph_new.json',
iterates through all edges, and sets their 'weight' attribute to None.
This is used to initialize the weights before actual travel times are merged in,
allowing us to track which edges have had their durations calculated.
"""

import json
import os

# Define file paths
# Assume the script is in network_data, so the graph file is in the same directory
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_FILE = os.path.join(OUTPUT_DIR, "networkx_graph_new.json")

def main():
    """Loads the graph, updates edge weights, and saves the graph."""
    
    print(f"Loading graph data from {GRAPH_FILE}...")
    
    # Check if the graph file exists
    if not os.path.exists(GRAPH_FILE):
        print(f"Error: Graph file not found at {GRAPH_FILE}")
        return
        
    try:
        # Load the graph data from the JSON file
        with open(GRAPH_FILE, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
            
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {GRAPH_FILE}: {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred loading {GRAPH_FILE}: {e}")
        return

    # Check if the loaded data has the expected structure
    if "edges" not in graph_data or not isinstance(graph_data["edges"], list):
        print("Error: Graph data does not contain a valid 'edges' list.")
        return

    print(f"Updating weights for {len(graph_data['edges'])} edges...")
    
    # Iterate through each edge and update its weight
    updated_count = 0
    for edge in graph_data["edges"]:
        # Check if the edge is a dictionary and has a 'weight' key
        if isinstance(edge, dict) and "weight" in edge:
            # Set the weight to None
            edge["weight"] = None
            updated_count += 1
        else:
            # Optional: Log a warning if an edge doesn't have the expected structure
            print(f"Warning: Skipping edge due to unexpected format or missing 'weight': {edge}")

    print(f"Successfully set 'weight' to None for {updated_count} edges.")

    try:
        # Save the modified graph data back to the JSON file
        with open(GRAPH_FILE, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2)
        print(f"Successfully saved updated graph data to {GRAPH_FILE}")
        
    except IOError as e:
        print(f"Error saving updated graph file {GRAPH_FILE}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while saving the updated graph: {e}")

if __name__ == "__main__":
    main() 