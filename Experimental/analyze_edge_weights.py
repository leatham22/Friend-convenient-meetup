#!/usr/bin/env python3
"""
Analyze Edge Weights

Performs analysis on calculated edge weight JSON files:
1. Duration Sanity Check: Identifies edges with durations outside a defined
   reasonable range.
2. Symmetry Analysis: Compares forward (A->B) and reverse (B->A) journey times
   for the same station pair/line and reports significant differences.
3. Schema Verification: Checks if all records contain expected keys and basic
   data types.

Usage:
    python3 analyze_edge_weights.py
"""

import json
import os
import math
from collections import defaultdict

# --- Configuration ---
# Input Files
TUBE_DLR_WEIGHTS_FILE = "Edge_weights_tube_dlr.json"
OG_EL_WEIGHTS_FILE = "Edge_weights_overground_elizabeth.json"

# 1. Duration Sanity Check Thresholds
MIN_REASONABLE_DURATION = 1.0 # Should match the minimum set during calculation
MAX_REASONABLE_DURATION = 20.0 # Max expected minutes between *adjacent* stations

# 2. Symmetry Analysis Thresholds
MAX_SYMMETRY_DIFF_MINS = 2.0   # Max absolute difference allowed (e.g., 5 min vs 7 min)
MAX_SYMMETRY_DIFF_PERCENT = 0.5 # Max relative difference allowed (e.g., 50%)

# 3. Schema Verification Definition
EXPECTED_SCHEMA = {
    "source": str,
    "target": str,
    "line": str,
    "line_name": str,
    "mode": str,
    "duration": (int, float), # Expecting numbers (int or float)
    "weight": (int, float),
    "transfer": bool,
    "calculated_timestamp": str # Assuming ISO format string
    # Add other keys like 'direction', 'branch' if they should always exist
    # "direction": str,
    # "branch": str,
}
REQUIRED_KEYS = set(EXPECTED_SCHEMA.keys())
# --- End Configuration ---

def load_edge_list(file_path):
    """
    Loads a list of edge dictionaries from a JSON file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        list: The loaded list of edge dictionaries, or None if an error occurs
              or the file does not contain a list.
    """
    # Check if the file exists
    if not os.path.exists(file_path):
        print(f"Error: File not found - {file_path}")
        return None
    # Check if the file is empty (valid JSON for an empty list)
    if os.path.getsize(file_path) == 0:
        print(f"Info: File is empty - {file_path}. Returning empty list.")
        return []

    try:
        # Open and load the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Ensure the loaded data is a list
        if not isinstance(data, list):
             print(f"Error: Expected a list of edges in {file_path}, but got {type(data)}.")
             return None
        return data
    except json.JSONDecodeError as e:
        # Handle JSON decoding errors
        print(f"Error decoding JSON from {file_path}: {e}")
        return None
    except Exception as e:
        # Handle other potential errors
        print(f"An unexpected error occurred loading {file_path}: {e}")
        return None

# --- Analysis Functions ---

def check_duration_sanity(edges, min_dur, max_dur):
    """
    Checks edge durations against min/max thresholds.

    Args:
        edges (list): List of edge dictionaries.
        min_dur (float): Minimum acceptable duration.
        max_dur (float): Maximum acceptable duration.

    Returns:
        list: A list of edge dictionaries with durations outside the range.
    """
    outliers = []
    if not edges:
        return outliers
    
    for edge in edges:
        duration = edge.get('duration')
        # Check if duration exists and is a number
        if duration is not None and isinstance(duration, (int, float)):
            # Check if duration is outside the defined bounds
            if not (min_dur <= duration <= max_dur):
                outliers.append(edge)
        else:
            # Append edges with missing or non-numeric duration as outliers too
            print(f"Warning: Edge found with invalid duration for sanity check: {edge.get('source')}->{edge.get('target')} on {edge.get('line')}")
            outliers.append(edge)
    return outliers

def check_symmetry(edges, max_diff_abs, max_diff_rel):
    """
    Analyzes journey time symmetry between forward and reverse edges.

    Args:
        edges (list): List of edge dictionaries.
        max_diff_abs (float): Maximum allowed absolute difference in minutes.
        max_diff_rel (float): Maximum allowed relative difference (0.0 to 1.0).

    Returns:
        list: A list of tuples, each containing (edge_pair_key, duration_A_B, duration_B_A, diff_abs, diff_rel).
              Includes pairs with significant asymmetry.
    """
    asymmetric_pairs = []
    if not edges:
        return asymmetric_pairs

    # Group edges by undirected pair: frozenset({source, target}) | line
    pairs = defaultdict(dict) # key: pair_key, value: {direction_key: duration}
    for edge in edges:
        source = edge.get('source')
        target = edge.get('target')
        line = edge.get('line')
        duration = edge.get('duration')

        # Ensure basic info is present and duration is valid
        if not all([source, target, line]) or not isinstance(duration, (int, float)):
            print(f"Warning: Skipping edge with missing info/duration for symmetry check: {edge}")
            continue

        # Create keys
        pair_key = f"{frozenset({source, target})}|{line}" # Key independent of direction
        direction_key = f"{source}|{target}|{line}" # Key specific to direction
        
        # Store the duration for this specific direction
        if direction_key in pairs[pair_key]:
            print(f"Warning: Duplicate directional edge found for symmetry check: {direction_key}")
        pairs[pair_key][direction_key] = duration

    # Now analyze the grouped pairs
    for pair_key, directions in pairs.items():
        if len(directions) == 2: # We have both A->B and B->A
            keys = list(directions.keys())
            dur_A_B = directions[keys[0]]
            dur_B_A = directions[keys[1]]
            
            # Ensure both durations are positive for relative difference calculation
            if dur_A_B > 0 and dur_B_A > 0:
                 diff_abs = abs(dur_A_B - dur_B_A)
                 # Use the larger duration as the denominator for relative difference
                 # to keep it between 0 and 1 (or slightly over 1 if one is tiny)
                 denominator = max(dur_A_B, dur_B_A)
                 diff_rel = diff_abs / denominator if denominator > 0 else 0

                 # Check if the difference exceeds either threshold
                 if diff_abs > max_diff_abs or diff_rel > max_diff_rel:
                    asymmetric_pairs.append((pair_key, keys[0], dur_A_B, keys[1], dur_B_A, diff_abs, diff_rel))
            else:
                 print(f"Warning: Non-positive duration found for symmetry check in pair {pair_key}, skipping comparison.")
                 # Optionally add to a separate list if you want to report these specifically

        elif len(directions) == 1:
            # Only one direction exists in the file for this pair/line
            # This is not necessarily an error (check_missing_edges handles graph consistency),
            # but we can optionally report it here if desired.
            # print(f"Info: Only one direction found for pair {pair_key}: {list(directions.keys())[0]}")
            pass # Currently doing nothing, as check_missing_edges covers this
        # else: should not happen if duplicate warning works

    return asymmetric_pairs

def check_schema(edges, schema, required_keys):
    """
    Verifies that edges conform to the expected schema.

    Args:
        edges (list): List of edge dictionaries.
        schema (dict): Dictionary defining expected keys and their types (or tuple of types).
        required_keys (set): Set of keys that must be present.

    Returns:
        list: A list of tuples, each containing (edge_identifier, error_message).
    """
    schema_errors = []
    if not edges:
        return schema_errors

    for i, edge in enumerate(edges):
        edge_id = f"Index {i}: {edge.get('source','?')}->{edge.get('target','?')} ({edge.get('line','?')})"
        
        if not isinstance(edge, dict):
            schema_errors.append((edge_id, "Record is not a dictionary"))
            continue

        # Check for missing required keys
        missing = required_keys - set(edge.keys())
        if missing:
            schema_errors.append((edge_id, f"Missing required keys: {missing}"))

        # Check for type errors for keys defined in schema
        for key, expected_type in schema.items():
            if key in edge:
                value = edge[key]
                if not isinstance(value, expected_type):
                     # Allow duration/weight to be int even if float expected, etc.
                     # Check specifically for number types if tuple provided
                     is_number_type = isinstance(expected_type, tuple) and any(isinstance(value, t) for t in expected_type if t in [int, float])
                     is_expected_type_match = isinstance(value, expected_type)

                     if not (is_expected_type_match or is_number_type):
                          schema_errors.append((edge_id, f"Type error for key '{key}'. Expected {expected_type}, got {type(value).__name__}."))
    return schema_errors

# --- Main Execution ---

def main():
    """
    Main function to load files and run all analyses.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    all_files_ok = True

    # --- Analyze Tube/DLR File ---
    print(f"\n--- Analyzing {TUBE_DLR_WEIGHTS_FILE} ---")
    tube_dlr_path = os.path.join(script_dir, TUBE_DLR_WEIGHTS_FILE)
    tube_dlr_edges = load_edge_list(tube_dlr_path)

    if tube_dlr_edges is not None:
        # 1. Duration Sanity
        print("\n1. Checking Duration Sanity...")
        duration_outliers_td = check_duration_sanity(tube_dlr_edges, MIN_REASONABLE_DURATION, MAX_REASONABLE_DURATION)
        if duration_outliers_td:
            print(f"[WARNING] Found {len(duration_outliers_td)} edges with durations outside [{MIN_REASONABLE_DURATION}, {MAX_REASONABLE_DURATION}] minutes:")
            for edge in duration_outliers_td:
                print(f"  - {edge.get('source')} -> {edge.get('target')} ({edge.get('line')}, {edge.get('mode')}): {edge.get('duration')}")
            all_files_ok = False
        else:
            print("[OK] All edge durations are within the expected range.")

        # 2. Symmetry
        print("\n2. Checking Journey Time Symmetry...")
        asymmetric_pairs_td = check_symmetry(tube_dlr_edges, MAX_SYMMETRY_DIFF_MINS, MAX_SYMMETRY_DIFF_PERCENT)
        if asymmetric_pairs_td:
            print(f"[WARNING] Found {len(asymmetric_pairs_td)} pairs with significant time asymmetry:")
            # Sort by absolute difference descending for visibility
            asymmetric_pairs_td.sort(key=lambda x: x[5], reverse=True)
            for _, key_ab, dur_ab, key_ba, dur_ba, diff_abs, diff_rel in asymmetric_pairs_td:
                print(f"  - Pair: {key_ab.split('|')[0]} <-> {key_ab.split('|')[1]} ({key_ab.split('|')[2]})")
                print(f"      {dur_ab:.1f} min vs {dur_ba:.1f} min (Diff: {diff_abs:.1f} min / {diff_rel:.1%})")
            all_files_ok = False
        else:
            print("[OK] No significant journey time asymmetry found between directions.")

        # 3. Schema
        print("\n3. Checking Schema...")
        schema_errors_td = check_schema(tube_dlr_edges, EXPECTED_SCHEMA, REQUIRED_KEYS)
        if schema_errors_td:
            print(f"[WARNING] Found {len(schema_errors_td)} schema violations:")
            for edge_id, msg in schema_errors_td:
                print(f"  - {edge_id}: {msg}")
            all_files_ok = False
        else:
            print("[OK] All records conform to the expected schema.")
    else:
        print(f"Skipping analysis for {TUBE_DLR_WEIGHTS_FILE} due to loading errors.")
        all_files_ok = False

    # --- Analyze Overground/Elizabeth File ---
    print(f"\n--- Analyzing {OG_EL_WEIGHTS_FILE} ---")
    og_el_path = os.path.join(script_dir, OG_EL_WEIGHTS_FILE)
    og_el_edges = load_edge_list(og_el_path)

    if og_el_edges is not None:
        # 1. Duration Sanity
        print("\n1. Checking Duration Sanity...")
        duration_outliers_oe = check_duration_sanity(og_el_edges, MIN_REASONABLE_DURATION, MAX_REASONABLE_DURATION)
        if duration_outliers_oe:
            print(f"[WARNING] Found {len(duration_outliers_oe)} edges with durations outside [{MIN_REASONABLE_DURATION}, {MAX_REASONABLE_DURATION}] minutes:")
            for edge in duration_outliers_oe:
                print(f"  - {edge.get('source')} -> {edge.get('target')} ({edge.get('line')}, {edge.get('mode')}): {edge.get('duration')}")
            all_files_ok = False
        else:
            print("[OK] All edge durations are within the expected range.")

        # 2. Symmetry
        print("\n2. Checking Journey Time Symmetry...")
        asymmetric_pairs_oe = check_symmetry(og_el_edges, MAX_SYMMETRY_DIFF_MINS, MAX_SYMMETRY_DIFF_PERCENT)
        if asymmetric_pairs_oe:
            print(f"[WARNING] Found {len(asymmetric_pairs_oe)} pairs with significant time asymmetry:")
            asymmetric_pairs_oe.sort(key=lambda x: x[5], reverse=True)
            for _, key_ab, dur_ab, key_ba, dur_ba, diff_abs, diff_rel in asymmetric_pairs_oe:
                print(f"  - Pair: {key_ab.split('|')[0]} <-> {key_ab.split('|')[1]} ({key_ab.split('|')[2]})")
                print(f"      {dur_ab:.1f} min vs {dur_ba:.1f} min (Diff: {diff_abs:.1f} min / {diff_rel:.1%})")
            all_files_ok = False
        else:
            print("[OK] No significant journey time asymmetry found between directions.")

        # 3. Schema
        print("\n3. Checking Schema...")
        schema_errors_oe = check_schema(og_el_edges, EXPECTED_SCHEMA, REQUIRED_KEYS)
        if schema_errors_oe:
            print(f"[WARNING] Found {len(schema_errors_oe)} schema violations:")
            for edge_id, msg in schema_errors_oe:
                print(f"  - {edge_id}: {msg}")
            all_files_ok = False
        else:
            print("[OK] All records conform to the expected schema.")
    else:
        print(f"Skipping analysis for {OG_EL_WEIGHTS_FILE} due to loading errors.")
        all_files_ok = False

    # --- Final Summary ---
    print("\n--- Analysis Summary ---")
    if all_files_ok:
        print("All checks passed for both files!")
    else:
        print("One or more issues found. Please review the warnings above.")
    print("------------------------")

if __name__ == "__main__":
    main() 