#!/usr/bin/env python3
"""
Check Missing Edges

Compares the edges defined in a network graph JSON file against the edges
present in the calculated edge weight JSON files (one for Tube/DLR, one for
Overground/Elizabeth line).

It checks for:
1. Edges present in the graph but missing (in either direction) from the
   corresponding weight file.
2. Edges present in the weight file but not found (in either direction)
   in the graph for the specified modes.

Usage:
    python3 check_missing_edges.py
"""

import json
import os
from collections import defaultdict

# --- Configuration ---
# File containing the full network graph structure
# Assumed format: A list of edge dictionaries, each with at least
# 'source', 'target', 'line', and 'mode' keys.
GRAPH_FILE = "networkx_graph_new.json"

# File containing calculated weights for Tube and DLR
TUBE_DLR_WEIGHTS_FILE = "Edge_weights_tube_dlr.json"
# File containing calculated weights for Overground and Elizabeth Line
OG_EL_WEIGHTS_FILE = "Edge_weights_overground_elizabeth.json"

# Modes to check against the Tube/DLR weights file
TUBE_DLR_MODES = {'tube', 'dlr'}
# Modes to check against the Overground/Elizabeth weights file
# Note: 'elizabeth-line' is the mode ID used by TfL API and likely in the graph
OG_EL_MODES = {'overground', 'elizabeth-line'}
# --- End Configuration ---

def load_json_data(file_path):
    """
    Loads data from a JSON file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        Any: The loaded JSON data, or None if an error occurs.
    """
    # Check if the file exists
    if not os.path.exists(file_path):
        print(f"Error: File not found - {file_path}")
        return None
    # Check if the file is empty
    if os.path.getsize(file_path) == 0:
        print(f"Warning: File is empty - {file_path}. Returning empty list/dict accordingly.")
        # Attempt to guess if it should be list or dict based on typical usage
        if "Edge_weights" in file_path:
             return []
        else:
             # Assuming graph file might be dict or list, but empty list is safer
             return [] # Or perhaps {} if graph format is expected dict

    try:
        # Open and load the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        # Handle JSON decoding errors
        print(f"Error decoding JSON from {file_path}: {e}")
        return None
    except Exception as e:
        # Handle other potential errors
        print(f"An unexpected error occurred loading {file_path}: {e}")
        return None

def create_edge_set_from_weights(edge_list):
    """
    Creates a set of unique edge keys from a list of edge weight dictionaries.
    The key format is "source|target|line".

    Args:
        edge_list (list): A list of edge dictionaries, each expected to have
                          'source', 'target', and 'line' keys.

    Returns:
        set: A set containing unique string keys for each edge. Returns an
             empty set if input is not a list or on error.
    """
    # Check if the input is actually a list
    if not isinstance(edge_list, list):
        print("Error: Expected a list of edges for weights, got something else.")
        return set()

    edge_keys = set()
    # Iterate through each edge dictionary in the list
    for edge in edge_list:
        # Ensure the dictionary is not None and contains the required keys
        if edge and all(k in edge for k in ('source', 'target', 'line')):
            # Create the unique key and add it to the set
            key = f"{edge['source']}|{edge['target']}|{edge['line']}"
            edge_keys.add(key)
        else:
            # Warn about malformed edge entries in the weights file
            print(f"Warning: Skipping malformed edge in weights file: {edge}")
    return edge_keys

def create_edge_map_from_graph(graph_data):
    """
    Creates a dictionary mapping unique edge keys ("source|target|line")
    from graph data (NetworkX JSON format) to their corresponding mode.
    Handles potential duplicates by storing the mode.

    Args:
        graph_data (dict): The loaded graph data, expected to have a key
                           like 'links' or 'edges' containing a list of edge
                           dictionaries. Each edge dict should have 'source', 
                           'target', 'line', and 'mode' keys.

    Returns:
        dict: A dictionary mapping edge keys (str) to modes (str). Returns an
              empty dict if input format is wrong or on error.
    """
    # Check if the input is a dictionary
    if not isinstance(graph_data, dict):
        print("Error: Expected a dictionary for graph data, got something else.")
        return {}

    # Find the key containing the edges (common names are 'links' or 'edges')
    edge_list_key = None
    if 'links' in graph_data and isinstance(graph_data['links'], list):
        edge_list_key = 'links'
    elif 'edges' in graph_data and isinstance(graph_data['edges'], list):
        edge_list_key = 'edges'
    
    if not edge_list_key:
        print(f"Error: Could not find an edge list (expected key 'links' or 'edges') in graph data: {list(graph_data.keys())}")
        return {}

    graph_edge_list = graph_data[edge_list_key]
    edge_map = {}
    # Iterate through each edge dictionary in the graph list
    for edge in graph_edge_list:
         # Ensure the dictionary is not None and contains the required keys
        if edge and all(k in edge for k in ('source', 'target', 'line', 'mode')):
            # key_no_mode = f"{edge['source']}|{edge['target']}|{edge['mode']}" # Original had mode? No, compare source|target|line
            key_no_mode = f"{edge['source']}|{edge['target']}|{edge['line']}" # Key for comparison with weights
            mode = edge.get('mode')

            # Store mode associated with the key (source|target|line)
            # Handle cases where the same source|target|line might appear with different modes
            if key_no_mode in edge_map and edge_map[key_no_mode] != mode:
                 print(f"Warning: Edge {key_no_mode} found in graph with multiple modes: {edge_map[key_no_mode]} and {mode}")
            # Only add if mode is relevant (tube, dlr, overground, elizabeth-line)
            if mode in TUBE_DLR_MODES or mode in OG_EL_MODES:
                 edge_map[key_no_mode] = mode
            # else: # Optional: print if skipping irrelevant modes like 'walking'
            #     print(f"Skipping graph edge with irrelevant mode: {key_no_mode} (Mode: {mode})")

        else:
            # Warn about malformed edge entries in the graph file
            print(f"Warning: Skipping malformed/incomplete edge in graph {edge_list_key} list: {edge}")
    return edge_map


def main():
    """
    Main function to load data and perform the comparison checks.
    """
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct full paths to the data files
    graph_file_path = os.path.join(script_dir, GRAPH_FILE)
    tube_dlr_weights_path = os.path.join(script_dir, TUBE_DLR_WEIGHTS_FILE)
    og_el_weights_path = os.path.join(script_dir, OG_EL_WEIGHTS_FILE)

    # --- Load Data ---
    print(f"Loading graph data from {graph_file_path}...")
    graph_data = load_json_data(graph_file_path) # graph_data is now a dict
    print(f"Loading Tube/DLR weights from {tube_dlr_weights_path}...")
    tube_dlr_weights = load_json_data(tube_dlr_weights_path) # This is a list
    print(f"Loading Overground/Elizabeth weights from {og_el_weights_path}...")
    og_el_weights = load_json_data(og_el_weights_path) # This is a list

    # Basic validation: Ensure data loaded for all files
    if graph_data is None or tube_dlr_weights is None or og_el_weights is None:
        print("Error loading one or more data files. Cannot proceed.")
        return

    # --- Process Data into Sets/Maps ---
    # Process the graph dictionary to extract the edge map
    graph_edge_map = create_edge_map_from_graph(graph_data) # Pass the whole dict
    # Process the weight lists to get sets of keys
    tube_dlr_weight_keys = create_edge_set_from_weights(tube_dlr_weights)
    og_el_weight_keys = create_edge_set_from_weights(og_el_weights)

    if not graph_edge_map:
         print("Could not process graph edges. Exiting.")
         return
    # No need to exit if weight sets are empty, the checks will just find mismatches.

    print(f"\nProcessed {len(graph_edge_map)} unique source|target|line keys from graph.")
    print(f"Processed {len(tube_dlr_weight_keys)} edges from {TUBE_DLR_WEIGHTS_FILE}.")
    print(f"Processed {len(og_el_weight_keys)} edges from {OG_EL_WEIGHTS_FILE}.")

    # --- Perform Checks ---
    missing_from_tube_dlr = []
    missing_from_og_el = []
    extra_in_tube_dlr = list(tube_dlr_weight_keys) # Start with all, remove found ones
    extra_in_og_el = list(og_el_weight_keys) # Start with all, remove found ones

    print("\n--- Checking Graph Edges vs Weight Files ---")
    # Check 1: Graph edges -> Weight files
    for edge_key, mode in graph_edge_map.items():
        source, target, line = edge_key.split('|')
        reverse_key = f"{target}|{source}|{line}"

        if mode in TUBE_DLR_MODES:
            # Check if this edge OR its reverse exists in the tube/dlr weights
            if edge_key not in tube_dlr_weight_keys and reverse_key not in tube_dlr_weight_keys:
                missing_from_tube_dlr.append(f"{edge_key} (Mode: {mode})")
            # If found (either direction), remove from 'extra' lists
            if edge_key in extra_in_tube_dlr:
                extra_in_tube_dlr.remove(edge_key)
            if reverse_key in extra_in_tube_dlr:
                 extra_in_tube_dlr.remove(reverse_key)

        elif mode in OG_EL_MODES:
             # Check if this edge OR its reverse exists in the og/el weights
            if edge_key not in og_el_weight_keys and reverse_key not in og_el_weight_keys:
                missing_from_og_el.append(f"{edge_key} (Mode: {mode})")
             # If found (either direction), remove from 'extra' lists
            if edge_key in extra_in_og_el:
                extra_in_og_el.remove(edge_key)
            if reverse_key in extra_in_og_el:
                 extra_in_og_el.remove(reverse_key)
        # Ignore modes not in either set (e.g., walking, transfers if present)

    # Note: The 'extra' lists now contain only edges from weight files
    # that did NOT correspond to any graph edge (in either direction)
    # with the appropriate mode.

    print("\n--- Results ---")

    # Report Missing from Tube/DLR Weights
    if missing_from_tube_dlr:
        print(f"\n[WARNING] {len(missing_from_tube_dlr)} Tube/DLR edges found in graph but MISSING (both directions) from {TUBE_DLR_WEIGHTS_FILE}:")
        for edge in sorted(missing_from_tube_dlr):
            print(f"  - {edge}")
    else:
        print(f"\n[OK] All Tube/DLR edges found in the graph seem to have a corresponding entry (in at least one direction) in {TUBE_DLR_WEIGHTS_FILE}.")

    # Report Missing from OG/EL Weights
    if missing_from_og_el:
        print(f"\n[WARNING] {len(missing_from_og_el)} Overground/Elizabeth edges found in graph but MISSING (both directions) from {OG_EL_WEIGHTS_FILE}:")
        for edge in sorted(missing_from_og_el):
            print(f"  - {edge}")
    else:
        print(f"\n[OK] All Overground/Elizabeth edges found in the graph seem to have a corresponding entry (in at least one direction) in {OG_EL_WEIGHTS_FILE}.")

    # Report Extra in Tube/DLR Weights
    if extra_in_tube_dlr:
        print(f"\n[WARNING] {len(extra_in_tube_dlr)} edges found in {TUBE_DLR_WEIGHTS_FILE} but NOT corresponding to any Tube/DLR edge (either direction) in the graph:")
        for edge_key in sorted(extra_in_tube_dlr):
            print(f"  - {edge_key}")
    else:
        print(f"\n[OK] All edges in {TUBE_DLR_WEIGHTS_FILE} seem to correspond to a Tube/DLR edge (in at least one direction) in the graph.")

    # Report Extra in OG/EL Weights
    if extra_in_og_el:
        print(f"\n[WARNING] {len(extra_in_og_el)} edges found in {OG_EL_WEIGHTS_FILE} but NOT corresponding to any Overground/Elizabeth edge (either direction) in the graph:")
        for edge_key in sorted(extra_in_og_el):
            print(f"  - {edge_key}")
    else:
        print(f"\n[OK] All edges in {OG_EL_WEIGHTS_FILE} seem to correspond to an Overground/Elizabeth edge (in at least one direction) in the graph.")

    print("\nCheck complete.")

if __name__ == "__main__":
    main()

""" Potential improvements/considerations:
- Graph file format: Assumed a list of dicts. If it's a NetworkX JSON format (nodes+links), parsing needs adjustment.
- Key consistency: Assumes 'source', 'target', 'line', 'mode' are the exact keys. Check files if errors occur.
- Bidirectional definition: Checks if *either* A->B or B->A exists. If the graph *only* contains A->B, but the weights file *only* contains B->A, this script counts it as OK. A stricter check might be needed depending on requirements.
- Mode mapping: Ensure modes in GRAPH_FILE ('overground', 'elizabeth-line', 'tube', 'dlr') match those used in TUBE_DLR_MODES and OG_EL_MODES.
""" 