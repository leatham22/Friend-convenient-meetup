#!/usr/bin/env python3
"""
Update Transfer Links in NetworkX Graph JSON

Reads the consolidated networkx graph JSON file, identifies transfer links
within the 'links' array, and updates specific fields:
- Changes the value associated with the key "key" to the string "transfer".
- Sets the value associated with the key "weight" to 5.

Overwrites the original file with the modified data.

Usage:
    python3 update_transfers_in_graph.py
"""

import json
import os

# --- Configuration ---
# Input and Output File (relative to the script's directory)
# Assumes script is in network_data directory
GRAPH_FILE = "../graph_data/networkx_graph_new.json" 

# Values to set for transfer edges
TRANSFER_KEY_VALUE = "transfer"
TRANSFER_WEIGHT_VALUE = 5
# --- End Configuration ---

def update_transfer_links(file_path):
    """Loads graph data, updates transfer links, and saves back to the file."""
    print(f"Processing {file_path}...")

    # --- Load Data ---
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"Error: File not found - {file_path}")
            return False
        # Check if file is empty
        if os.path.getsize(file_path) == 0:
             print(f"Error: File is empty - {file_path}")
             return False

        # Open and load the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("Successfully loaded graph data.")

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {file_path}: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred loading {file_path}: {e}")
        return False

    # --- Validate Structure and Find Links ---
    # Ensure the loaded data is a dictionary
    if not isinstance(data, dict):
        print(f"Error: Expected a dictionary structure in {file_path}, but got {type(data)}.")
        return False
    
    # Check for the 'edges' key (corrected from 'links')
    if "edges" not in data:
        print(f"Error: Could not find the 'edges' key in the root of {file_path}.")
        return False
    
    # Ensure 'edges' is a list
    edges = data["edges"] # Corrected variable name
    if not isinstance(edges, list):
        print(f"Error: Expected 'edges' to be a list in {file_path}, but got {type(edges)}.")
        return False
    
    print(f"Found {len(edges)} edges to process.") # Corrected variable name

    # --- Modify Links ---
    modified_count = 0
    # Iterate through the list of edges (corrected variable name)
    for i, edge in enumerate(edges):
        # Check if the edge is a dictionary
        if not isinstance(edge, dict):
            print(f"Warning: Item at index {i} in the 'edges' array is not a dictionary, skipping.") # Corrected key name
            continue

        # Check if the 'transfer' key exists and is True
        if edge.get("transfer") is True:
            # --- Apply Modifications ---
            # 1. Update the value for the 'key' field
            edge["key"] = TRANSFER_KEY_VALUE 
            # 2. Update the value for the 'weight' field
            edge["weight"] = TRANSFER_WEIGHT_VALUE 
            modified_count += 1
            # --- End Modifications ---

    print(f"Found and modified {modified_count} transfer edges.") # Corrected term
    if modified_count == 0:
        print("No transfer edges needed modification.") # Corrected term

    # --- Save Data ---
    try:
        # Save the entire modified data structure back to the original file
        # Using indent=2 for readability, although it increases file size
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2) 
        print(f"Successfully saved updated graph data back to {file_path}")
        return True # Indicate success
    except IOError as e:
        print(f"Error writing updated data to {file_path}: {e}")
        return False # Indicate failure
    except Exception as e:
        print(f"An unexpected error occurred saving {file_path}: {e}")
        return False # Indicate failure

def main():
    """Main function to run the update process."""
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct the full path to the graph file
    graph_file_path = os.path.join(script_dir, GRAPH_FILE)

    print("--- Starting Transfer Link Update ---")
    success = update_transfer_links(graph_file_path)

    print("\n--- Update Process Summary ---")
    if success:
        print("Update completed successfully.")
    else:
        print("Update failed. Please check errors above.")
    print("----------------------------")

if __name__ == "__main__":
    main() 