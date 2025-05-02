#!/usr/bin/env python3
"""
Update Edge Weights in NetworkX Graph JSON

Reads the consolidated networkx graph JSON, and updates the 'weight' and 'duration'
fields for non-transfer edges using data from separate edge weight files.

Inputs:
- networkx_graph_new.json (the main graph file)
- Edge_weights_tube_dlr.json (Tube/DLR weights)
- Edge_weights_overground_elizabeth.json (Overground/Elizabeth Line weights)

Output:
- Overwrites networkx_graph_new.json with updated weights.

Usage:
    python3 update_edge_weights.py
"""

import json
import os

# --- Configuration ---
# Assumes script is in the network_data directory
GRAPH_FILE = "../graph_data/networkx_graph_new.json"
TUBE_DLR_WEIGHTS_FILE = "../graph_data/Edge_weights_tube_dlr.json"
OG_EL_WEIGHTS_FILE = "../graph_data/Edge_weights_overground_elizabeth.json"
# --- End Configuration ---

def load_json_data(file_path):
    """Loads data from a JSON file, handling common errors."""
    if not os.path.exists(file_path):
        print(f"Error: Input file not found - {file_path}")
        return None
    if os.path.getsize(file_path) == 0:
        print(f"Warning: Input file is empty - {file_path}. Returning empty list/dict based on extension.")
        # Guess based on common usage, might need adjustment
        return [] if file_path.endswith(".json") else {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Successfully loaded {os.path.basename(file_path)}")
        return data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {file_path}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred loading {file_path}: {e}")
        return None

def build_weight_lookup(edge_list):
    """Builds a lookup dictionary from a list of edge weights.
    
    Args:
        edge_list (list): A list of edge dictionaries.
        
    Returns:
        dict: A dictionary mapping (source, target, line) -> edge_dict
              Returns an empty dict if input is None or not a list.
    """
    lookup = {}
    if not isinstance(edge_list, list):
        print("Error: Expected a list for building weight lookup.")
        return lookup
        
    duplicates_found = 0
    for edge in edge_list:
        # Ensure edge is a dict and has required keys
        if isinstance(edge, dict) and all(k in edge for k in ["source", "target", "line"]):
            key = (edge["source"], edge["target"], edge["line"])
            # Check for duplicate source-target-line combinations
            if key in lookup:
                # print(f"Warning: Duplicate edge found in weight source file for {key}. Keeping first encountered.")
                duplicates_found += 1
            else:
                # Store the entire edge dictionary for easy access to weight/duration
                lookup[key] = edge 
        else:
            print(f"Warning: Skipping invalid edge entry in weight source file: {edge}")
            
    if duplicates_found > 0:
         print(f"Warning: Found {duplicates_found} duplicate source-target-line combinations in weight source file. Used the first occurrence.")
    return lookup

def main():
    """Main function to load data, update weights, and save."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct full paths
    graph_file_path = os.path.join(script_dir, GRAPH_FILE)
    tube_dlr_weights_path = os.path.join(script_dir, TUBE_DLR_WEIGHTS_FILE)
    og_el_weights_path = os.path.join(script_dir, OG_EL_WEIGHTS_FILE)

    print("--- Starting Edge Weight Update --- ")

    # --- Load All Data ---
    print("\nLoading main graph data...")
    graph_data = load_json_data(graph_file_path)
    if graph_data is None or not isinstance(graph_data, dict) or "edges" not in graph_data:
        print("Failed to load or validate main graph data structure. Aborting.")
        return

    print("\nLoading Tube/DLR edge weights...")
    tube_dlr_weights = load_json_data(tube_dlr_weights_path)
    if tube_dlr_weights is None:
        print("Failed to load Tube/DLR weights. Aborting.")
        return

    print("\nLoading Overground/Elizabeth Line edge weights...")
    og_el_weights = load_json_data(og_el_weights_path)
    if og_el_weights is None:
        print("Failed to load Overground/Elizabeth Line weights. Aborting.")
        return

    # --- Build Lookups ---
    print("\nBuilding weight lookups...")
    tube_dlr_lookup = build_weight_lookup(tube_dlr_weights)
    og_el_lookup = build_weight_lookup(og_el_weights)
    print(f"Built Tube/DLR lookup with {len(tube_dlr_lookup)} entries.")
    print(f"Built Overground/EL lookup with {len(og_el_lookup)} entries.")

    # --- Iterate and Update Main Graph Edges ---
    print("\nUpdating weights in main graph...")
    main_edges = graph_data["edges"]
    updated_tube_dlr_count = 0
    updated_og_el_count = 0
    unmatched_count = 0
    transfer_skipped_count = 0
    invalid_edge_count = 0

    for i, edge in enumerate(main_edges):
        if not isinstance(edge, dict):
            print(f"Warning: Skipping invalid item at index {i} in main graph edges list.")
            invalid_edge_count += 1
            continue
            
        # Skip transfer edges
        if edge.get("transfer") is True:
            transfer_skipped_count += 1
            continue

        # Get key fields, ensure they exist
        source = edge.get("source")
        target = edge.get("target")
        line = edge.get("line")

        if not all([source, target, line is not None]): # Allow empty string for line
            print(f"Warning: Skipping main graph edge at index {i} due to missing source/target/line: {edge}")
            invalid_edge_count += 1
            continue
        
        lookup_key = (source, target, line)
        matched = False

        # Check Tube/DLR data first
        if lookup_key in tube_dlr_lookup:
            source_edge_data = tube_dlr_lookup[lookup_key]
            # Update weight (required)
            if "weight" in source_edge_data:
                 edge["weight"] = source_edge_data["weight"]
            else:
                 print(f"Warning: Matched Tube/DLR edge {lookup_key} lacks a 'weight' field.")
                 
            # Update duration (optional, if present in source)
            if "duration" in source_edge_data:
                edge["duration"] = source_edge_data["duration"]
            # Else: duration might not be in source or target, leave target as is.
            
            updated_tube_dlr_count += 1
            matched = True
            # print(f"  Updated {lookup_key} from Tube/DLR weights.") # Verbose logging

        # If not found in Tube/DLR, check Overground/Elizabeth Line data
        elif lookup_key in og_el_lookup:
            source_edge_data = og_el_lookup[lookup_key]
            # Update weight (required)
            if "weight" in source_edge_data:
                 edge["weight"] = source_edge_data["weight"]
            else:
                 print(f"Warning: Matched OG/EL edge {lookup_key} lacks a 'weight' field.")
                 
            # Update duration (optional, if present in source)
            if "duration" in source_edge_data:
                edge["duration"] = source_edge_data["duration"]
            # Else: duration might not be in source or target, leave target as is.
            
            updated_og_el_count += 1
            matched = True
            # print(f"  Updated {lookup_key} from OG/EL weights.") # Verbose logging

        # If not matched in either source file
        if not matched:
            # print(f"Warning: No weight found for non-transfer edge: {source} -> {target} ({line})")
            unmatched_count += 1
            
    print("Weight update scan complete.")

    # --- Save Updated Graph Data ---
    print(f"\nSaving updated graph data back to {graph_file_path}...")
    try:
        with open(graph_file_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2)
        print("Successfully saved updated graph data.")
    except IOError as e:
        print(f"Error writing updated data to {graph_file_path}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred saving {graph_file_path}: {e}")

    # --- Final Summary ---
    print("\n--- Update Summary ---")
    print(f"Processed {len(main_edges)} total edges from {GRAPH_FILE}.")
    print(f"Skipped {transfer_skipped_count} transfer edges.")
    print(f"Skipped {invalid_edge_count} invalid/incomplete edges in main graph.")
    print(f"Updated {updated_tube_dlr_count} edges using {TUBE_DLR_WEIGHTS_FILE}.")
    print(f"Updated {updated_og_el_count} edges using {OG_EL_WEIGHTS_FILE}.")
    print(f"Could not find matching weights for {unmatched_count} non-transfer edges.")
    print("----------------------")

if __name__ == "__main__":
    main() 