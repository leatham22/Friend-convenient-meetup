#!/usr/bin/env python3
"""
Apply Arbitrary Timestamp

Reads specified edge weight JSON files and adds or overwrites the
'calculated_timestamp' field for every record with a fixed, arbitrary timestamp.

This is useful for ensuring schema consistency when some records were generated
before timestamp tracking was implemented.

Usage:
    python3 apply_arbitrary_timestamp.py
"""

import json
import os
from datetime import datetime

# --- Configuration ---
# Files to process
FILES_TO_PROCESS = [
    "Edge_weights_tube_dlr.json",
    "Edge_weights_overground_elizabeth.json"
]

# The arbitrary timestamp to apply (ISO format)
# Using midday on 2025-04-25 as requested
# Format: YYYY-MM-DDTHH:MM:SS.ssssss
ARBITRARY_TIMESTAMP = "2025-04-25T12:00:00.000000"
# --- End Configuration ---

def load_and_update_timestamps(file_path, timestamp_to_apply):
    """
    Loads an edge list file, adds/updates the timestamp, and returns the list.

    Args:
        file_path (str): Path to the edge weight JSON file.
        timestamp_to_apply (str): The ISO format timestamp string to set.

    Returns:
        list: The modified list of edge dictionaries, or None on error.
    """
    # Check existence and emptiness
    if not os.path.exists(file_path):
        print(f"Error: File not found - {file_path}. Skipping.")
        return None
    if os.path.getsize(file_path) == 0:
        print(f"Info: File is empty - {file_path}. Nothing to update.")
        return [] # Return empty list, as original was empty

    try:
        # Load the JSON data
        with open(file_path, 'r', encoding='utf-8') as f:
            edges = json.load(f)
        
        # Ensure it's a list
        if not isinstance(edges, list):
            print(f"Error: Expected a list in {file_path}, got {type(edges)}. Skipping.")
            return None
        
        updated_count = 0
        # Iterate and update/add the timestamp
        for i, edge in enumerate(edges):
            if isinstance(edge, dict):
                # Check if timestamp is different or missing
                if edge.get('calculated_timestamp') != timestamp_to_apply:
                     edge['calculated_timestamp'] = timestamp_to_apply
                     updated_count += 1
            else:
                 print(f"Warning: Non-dictionary item found at index {i} in {file_path}. Skipping item.")

        print(f"Applied timestamp to {updated_count} records in {os.path.basename(file_path)}.")
        return edges

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {file_path}: {e}. Skipping.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred processing {file_path}: {e}. Skipping.")
        return None

def save_edge_list(edges, file_path):
    """
    Saves the list of edge dictionaries back to a JSON file.

    Args:
        edges (list): The list of edge dictionaries.
        file_path (str): Path to save the JSON file.
    
    Returns:
        bool: True if saving was successful, False otherwise.
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(edges, f, indent=2) # Use indent for readability
        print(f"Successfully saved updated data to {os.path.basename(file_path)}.")
        return True
    except IOError as e:
        print(f"Error saving updated file {file_path}: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred saving {file_path}: {e}")
        return False

def main():
    """
    Main function to iterate through files and apply timestamps.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Applying arbitrary timestamp: {ARBITRARY_TIMESTAMP}")

    for filename in FILES_TO_PROCESS:
        file_path = os.path.join(script_dir, filename)
        print(f"\nProcessing file: {filename}...")
        
        # Load and update the data in memory
        updated_edges = load_and_update_timestamps(file_path, ARBITRARY_TIMESTAMP)
        
        # If loading and updating was successful, save the changes
        if updated_edges is not None:
            save_edge_list(updated_edges, file_path)
        else:
            print(f"Skipped saving {filename} due to errors during loading/processing.")
            
    print("\nTimestamp application process finished.")

if __name__ == "__main__":
    main() 