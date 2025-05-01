#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calculate Hub Edge Weights from Timetable Data

This script processes cached raw timetable data (fetched by get_timetable_data.py)
to calculate the travel time (duration/weight) between adjacent *hub* stations
for Tube and DLR lines, based on the TfL timetable information.

It references the main hub graph structure (networkx_graph_hubs_final.json) to:
1. Identify valid connections between hubs on specific lines.
2. Map Naptan IDs found in the timetable data back to their parent Hub Names.
3. Handle discrepancies where different travel times might be calculated for the
   same hub-to-hub connection (e.g., from different terminals or branches).

The output is a JSON file containing a list of edge dictionaries, formatted
identically to the edges in the main hub graph file, but including only those
edges for which a duration could be calculated, updated with the 'weight' and
a 'calculated_timestamp'.

Usage:
    python3 calculate_hub_edge_weights.py [--line <line_id>]

Arguments:
    --line (optional): Process only a specific cached line file (e.g., district).
                       If omitted, all .json files in timetable_cache/ will be processed.

Output:
    Creates calculated_hub_edge_weights.json in the graph_data directory.
    Prints discrepancies found in travel times and edge matching to the console.
"""

import json
import os
import argparse
from collections import defaultdict
import math # Import math for isnan check
import statistics # For calculating average/median
from datetime import datetime # Import datetime

# --- Configuration ---
# Relative paths from the script's location
CACHE_DIR_RELATIVE = "../graph_data/timetable_cache"
HUB_GRAPH_FILE_RELATIVE = "../graph_data/networkx_graph_hubs_with_transfer_weights.json"
OUTPUT_FILE_RELATIVE = "../graph_data/calculated_hub_edge_weights.json"

# Threshold for averaging durations. If max - min > threshold, we warn but still average.
DISCREPANCY_THRESHOLD_MINUTES = 2
# Minimum duration in minutes if calculation results in <= 0
MIN_DURATION_MINUTES = 0.1
# Modes to process based on timetable data
MODES_TO_PROCESS = {'tube', 'dlr'}
# --- End Configuration ---

def load_json_data(file_path, data_description):
    """
    Loads JSON data from a file with error handling.

    Args:
        file_path (str): Absolute path to the JSON file.
        data_description (str): Description of the data for error messages.

    Returns:
        dict or list: Loaded JSON data, or None if an error occurs.
    """
    if not os.path.exists(file_path):
        print(f"Error: {data_description} file not found at {file_path}")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content:
                print(f"Warning: {data_description} file is empty: {file_path}")
                return None
            return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {file_path}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred loading {file_path}: {e}")
        return None

def build_mappings(hub_graph_data):
    """
    Builds necessary mappings from the hub graph data.

    Args:
        hub_graph_data (dict): The loaded hub graph JSON data.

    Returns:
        tuple: Contains:
            - naptan_to_hub_name (dict): {naptan_id: hub_name}
            - hub_name_to_node_data (dict): {hub_name: node_dict}
            - hub_name_to_primary_id (dict): {hub_name: primary_naptan_id}
        Returns None if graph data is invalid.
    """
    naptan_to_hub_name = {}
    hub_name_to_node_data = {}
    hub_name_to_primary_id = {}

    nodes = hub_graph_data.get('nodes')
    if not isinstance(nodes, list):
        print("Error: Hub graph 'nodes' data is missing or not a list.")
        return None

    for node_data in nodes:
        hub_name = node_data.get('id') # 'id' is the Hub Name
        primary_id = node_data.get('primary_naptan_id')

        if not hub_name:
            print(f"Warning: Node found without an 'id' (Hub Name): {node_data}")
            continue

        if hub_name in hub_name_to_node_data:
            print(f"Warning: Duplicate Hub Name found: {hub_name}. Overwriting.")

        hub_name_to_node_data[hub_name] = node_data
        if primary_id:
            hub_name_to_primary_id[hub_name] = primary_id
            # Map the primary ID itself to the hub name
            naptan_to_hub_name[primary_id] = hub_name

        # Map all constituent Naptan IDs back to the Hub Name
        constituent_ids = node_data.get('constituent_naptan_ids', [])
        if isinstance(constituent_ids, list):
            for naptan_id in constituent_ids:
                # Check if this naptan is already mapped (potentially to another hub - unlikely but possible)
                if naptan_id in naptan_to_hub_name and naptan_to_hub_name[naptan_id] != hub_name:
                    print(f"Warning: Naptan ID {naptan_id} is listed in multiple hubs: "
                          f"{naptan_to_hub_name[naptan_id]} and {hub_name}. Using {hub_name}.")
                naptan_to_hub_name[naptan_id] = hub_name
        else:
            print(f"Warning: 'constituent_naptan_ids' for hub {hub_name} is not a list: {constituent_ids}")


    # Final check: Ensure primary Naptan IDs are mapped if they weren't in constituents
    for hub_name, primary_id in hub_name_to_primary_id.items():
        if primary_id not in naptan_to_hub_name:
             naptan_to_hub_name[primary_id] = hub_name


    print(f"Built mappings: {len(naptan_to_hub_name)} Naptan IDs mapped to "
          f"{len(hub_name_to_node_data)} Hubs.")
    return naptan_to_hub_name, hub_name_to_node_data, hub_name_to_primary_id


def get_valid_hub_edges(hub_graph_data, modes_to_include):
    """
    Extracts valid non-transfer edges between hubs for specified modes.

    Args:
        hub_graph_data (dict): Loaded hub graph data.
        modes_to_include (set): Set of mode strings (e.g., {'tube', 'dlr'}).

    Returns:
        tuple: Contains:
            - valid_edges_set (set): {(source_hub_name, target_hub_name, line_id)}
            - original_edge_lookup (dict): {(source_hub_name, target_hub_name, line_id): edge_dict}
    """
    valid_edges_set = set()
    original_edge_lookup = {}

    edges = hub_graph_data.get('edges')
    if not isinstance(edges, list):
        print("Error: Hub graph 'edges' data is missing or not a list.")
        return valid_edges_set, original_edge_lookup

    for edge in edges:
        source_hub = edge.get('source') # This is the hub name ('id' from node)
        target_hub = edge.get('target')
        line_id = edge.get('line')
        mode = edge.get('mode')
        is_transfer = edge.get('transfer', False)

        # We only want non-transfer edges for the specified modes
        if not is_transfer and source_hub and target_hub and line_id and mode in modes_to_include:
            key = (source_hub, target_hub, line_id)
            valid_edges_set.add(key)
            # Store the original edge data for easy lookup later
            if key in original_edge_lookup:
                 # This indicates a multi-edge between the same hubs on the same line - possible in multigraph
                 # print(f"Debug: Multiple edges found for {key}. Storing list.")
                 if isinstance(original_edge_lookup[key], list):
                     original_edge_lookup[key].append(edge)
                 else: # Convert single edge to list
                     original_edge_lookup[key] = [original_edge_lookup[key], edge]
            else:
                 original_edge_lookup[key] = edge # Store single edge initially

    print(f"Identified {len(valid_edges_set)} unique valid directional Hub edges "
          f"for modes {modes_to_include} in the original graph.")
    return valid_edges_set, original_edge_lookup


def process_timetable_intervals(timetable, departure_stop_id, line_id,
                                naptan_to_hub_name, valid_hub_edges_set):
    """
    Processes the intervals from a single timetable fetch to calculate durations
    between *hubs*, checking against the valid hub edges.

    Args:
        timetable (dict): The timetable data for a specific line/terminal fetch.
        departure_stop_id (str): The Naptan ID of the terminal station for this timetable.
        line_id (str): The ID of the line being processed.
        naptan_to_hub_name (dict): Mapping from Naptan ID to Hub Name.
        valid_hub_edges_set (set): Set of valid (source_hub, target_hub, line_id) tuples.

    Returns:
        defaultdict: Mapping {(source_hub_name, target_hub_name, line_id): [duration1, duration2,...]}
                     for valid hub-to-hub movements found in this timetable.
    """
    # Stores durations calculated *within this specific timetable fetch*
    durations_this_fetch = defaultdict(list)

    # 1. Navigate to the intervals list
    actual_timetable = timetable.get("timetable")
    if not actual_timetable:
        # print(f"    Debug: No 'timetable' key found for {line_id} from {departure_stop_id}")
        return durations_this_fetch
    routes = actual_timetable.get("routes", [])

    # 2. Iterate through routes and station interval groups
    for route in routes:
        station_intervals_list = route.get("stationIntervals", [])
        for station_interval_group in station_intervals_list:
            intervals = station_interval_group.get("intervals", [])

            # Initialize tracking for the start of this sequence
            last_naptan_id = departure_stop_id
            last_hub_name = naptan_to_hub_name.get(last_naptan_id)
            last_time_to_arrival = 0.0 # Timetable starts at 0 from the departure stop

            if not last_hub_name:
                 # This departure Naptan isn't in our hub graph mapping - skip sequence
                 # print(f"    Warning: Departure Naptan {last_naptan_id} not found in hub mapping for line {line_id}. Skipping sequence.")
                 continue # Skip this station_interval_group

            # 3. Process each interval in the sequence
            for interval in intervals:
                current_naptan_id = interval.get("stopId")
                current_time_to_arrival = interval.get("timeToArrival")

                # Basic data validation for the current interval
                if not current_naptan_id or current_time_to_arrival is None or math.isnan(current_time_to_arrival):
                    # print(f"    Warning: Skipping interval with missing data: {interval} on line {line_id} from {departure_stop_id}")
                    # Reset tracking if an interval is bad, as we lose sequence continuity
                    last_naptan_id = None
                    last_hub_name = None
                    last_time_to_arrival = 0.0
                    break # Stop processing this specific interval sequence

                # Find the hub for the current Naptan ID
                current_hub_name = naptan_to_hub_name.get(current_naptan_id)

                if not current_hub_name:
                    # This Naptan ID isn't part of any hub we know about - skip interval
                    # print(f"    Warning: Naptan {current_naptan_id} in timetable not found in hub mapping for line {line_id}. Skipping interval.")
                    # Update last known good state - effectively treating this stop as non-existent for hub timing
                    last_naptan_id = current_naptan_id
                    # last_hub_name remains the same
                    last_time_to_arrival = current_time_to_arrival
                    continue # Move to the next interval

                # --- Core Hub Logic ---
                # Check if we have moved *between different hubs*
                if last_hub_name and current_hub_name != last_hub_name:
                    # Calculate duration since the *last* arrival time tracked
                    duration = current_time_to_arrival - last_time_to_arrival

                    # Ensure duration is realistic
                    if duration <= 0:
                        duration = MIN_DURATION_MINUTES # Use minimum
                    else:
                        duration = round(duration, 2) # Round to 2 decimal places initially

                    # Check if this hub-to-hub edge exists in our graph for this line
                    hub_edge_key = (last_hub_name, current_hub_name, line_id)
                    if hub_edge_key in valid_hub_edges_set:
                        # Valid edge found, store the duration
                        durations_this_fetch[hub_edge_key].append(duration)
                    # else:
                        # Optional: Log hub edges from timetable that are skipped
                        # print(f"    Skipping duration for non-graph hub edge: {last_hub_name} -> {current_hub_name} on {line_id}")
                        # pass

                    # IMPORTANT: Update the 'last' state to the *current* interval,
                    # as this is now the starting point for the *next* potential hub-to-hub duration.
                    last_naptan_id = current_naptan_id
                    last_hub_name = current_hub_name
                    last_time_to_arrival = current_time_to_arrival

                elif last_hub_name and current_hub_name == last_hub_name:
                     # We are still within the same hub (or arrived at the same hub again)
                     # Only update the 'last' state, don't calculate/store duration yet.
                     # This handles cases where the timetable lists multiple stops within the same hub consecutively.
                     last_naptan_id = current_naptan_id
                     # last_hub_name stays the same
                     last_time_to_arrival = current_time_to_arrival
                else:
                    # This case should ideally not be reached if initial last_hub_name was valid
                    # but acts as a safeguard. Reset and break.
                    print(f"    Internal Warning: Reached unexpected state processing interval {interval} for {line_id}. Resetting sequence.")
                    last_naptan_id = None
                    last_hub_name = None
                    last_time_to_arrival = 0.0
                    break # Stop processing this specific interval sequence

            # End of interval loop for this station_interval_group

    # Return all durations calculated from this specific timetable fetch
    return durations_this_fetch

def get_final_duration(durations, line_id, from_hub, to_hub):
    """
    Determines the final duration for a directional hub pair, handling discrepancies.
    Rounds the final result to 1 decimal place.

    Args:
        durations (list): List of calculated durations (float).
        line_id (str): Line ID for logging.
        from_hub (str): Source hub name for logging.
        to_hub (str): Target hub name for logging.

    Returns:
        float: The final calculated duration (averaged or first value, rounded), or None.
    """
    if not durations:
        return None

    # Clean durations (remove any potential None values if they crept in)
    cleaned_durations = [d for d in durations if d is not None]
    if not cleaned_durations:
        return None

    unique_durations = sorted(list(set(cleaned_durations))) # Sorted for consistent logging

    if len(unique_durations) == 1:
        # No discrepancy, just round the single value
        final_duration = max(MIN_DURATION_MINUTES, round(unique_durations[0], 1))
        return final_duration
    else:
        min_d = min(unique_durations)
        max_d = max(unique_durations)
        diff = max_d - min_d

        # Use median instead of mean for slightly better robustness to outliers
        med_duration = statistics.median(cleaned_durations)
        final_duration = max(MIN_DURATION_MINUTES, round(med_duration, 1))

        # Check if discrepancy is large for warning purposes
        if diff > DISCREPANCY_THRESHOLD_MINUTES:
            print(f"  Warning: Large discrepancy for Line: {line_id}, Hubs: {from_hub} -> {to_hub}. "
                  f"Times (minutes): {unique_durations}. Using median: {final_duration}")
        # else:
             # Optional: Log averaging of minor discrepancies
             # print(f"    Averaging durations for {line_id}: {from_hub} -> {to_hub}. "
             #      f"Original: {unique_durations}, Median: {med_duration:.2f}, Final: {final_duration}")

        return final_duration

def create_output_edges(aggregated_durations, original_edge_lookup, valid_hub_edges_set):
    """
    Creates the final list of edge dictionaries with calculated weights.

    Args:
        aggregated_durations (dict): {(source_hub, target_hub, line_id): [durations]}
        original_edge_lookup (dict): {(source_hub, target_hub, line_id): edge_dict or [edge_dicts]}
        valid_hub_edges_set (set): Set of all valid original directional hub edges for processed modes.

    Returns:
        list: List of final edge dictionaries with 'weight' updated.
    """
    print("Creating final edge list with processed durations...")
    output_edges = []
    # Keep track of which original edges we successfully calculated a weight for
    processed_original_keys = set()

    for (source_hub, target_hub, line_id), durations in aggregated_durations.items():
        final_duration = get_final_duration(durations, line_id, source_hub, target_hub)

        if final_duration is None:
            print(f"Warning: Could not determine final duration for {source_hub} -> {target_hub} on {line_id}. Skipping.")
            continue

        # Find the corresponding original edge(s) in the lookup
        original_edge_data = original_edge_lookup.get((source_hub, target_hub, line_id))

        if original_edge_data:
             # Mark this key as processed
             processed_original_keys.add((source_hub, target_hub, line_id))

             # Handle potential multiple edges (if multigraph)
             if isinstance(original_edge_data, list):
                 for edge_copy_data in original_edge_data:
                     # Create a copy to avoid modifying the original lookup
                     output_edge = edge_copy_data.copy()
                     # Update weight and add timestamp
                     output_edge['weight'] = final_duration
                     # Optionally add duration if you want both weight and duration fields
                     # output_edge['duration'] = final_duration
                     output_edge['calculated_timestamp'] = datetime.now().isoformat()
                     output_edges.append(output_edge)
             else: # Single edge case
                 # Create a copy
                 output_edge = original_edge_data.copy()
                 # Update weight and add timestamp
                 output_edge['weight'] = final_duration
                 # output_edge['duration'] = final_duration # Optional
                 output_edge['calculated_timestamp'] = datetime.now().isoformat()
                 output_edges.append(output_edge)
        else:
            # This should NOT happen if process_timetable_intervals correctly used valid_hub_edges_set
             print(f"*UNEXPECTED Error*: Calculated duration for edge {source_hub}->{target_hub} on {line_id}, "
                   "but it wasn't found in the original edge lookup. Skipping output.")

    print(f"Created {len(output_edges)} weighted edge entries.")

    # --- Report Missing Calculations ---
    print("--- Edge Calculation Discrepancy Report ---")
    missing_count = 0
    for key in valid_hub_edges_set:
        if key not in processed_original_keys:
            missing_count += 1
            source_h, target_h, line = key
            # Look up the original edge details for better reporting
            original_details = original_edge_lookup.get(key)
            direction_info = f"{source_h} -> {target_h}"
            if original_details and isinstance(original_details, dict): # Check if single dict before accessing
                 direction_info = f"{original_details.get('source', source_h)} -> {original_details.get('target', target_h)}"
            elif original_details and isinstance(original_details, list): # Handle list case
                 # Just use the first edge in the list for name reporting
                 first_edge = original_details[0]
                 direction_info = f"{first_edge.get('source', source_h)} -> {first_edge.get('target', target_h)}"

            print(f"  Warning: No duration calculated for original graph edge: "
                  f"Line: {line}, Direction: {direction_info}")

    if missing_count == 0:
        print("Successfully calculated durations for all identified valid Tube/DLR hub edges.")
    else:
        print(f"Warning: Could not calculate durations for {missing_count} valid Tube/DLR hub edges found in the original graph.")
    print("--- End Report ---")

    return output_edges

# --- Main Execution ---
def main():
    """Main function to process cached timetable data for hubs."""
    parser = argparse.ArgumentParser(description="Process cached TfL timetable data for hub graph.")
    parser.add_argument("--line", help="Specific line ID (cache file name without .json) to process.")
    args = parser.parse_args()

    # --- Path Setup ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_dir_abs = os.path.abspath(os.path.join(script_dir, CACHE_DIR_RELATIVE))
    hub_graph_file_abs = os.path.abspath(os.path.join(script_dir, HUB_GRAPH_FILE_RELATIVE))
    output_file_abs = os.path.abspath(os.path.join(script_dir, OUTPUT_FILE_RELATIVE))

    if not os.path.isdir(cache_dir_abs):
        print(f"Error: Cache directory not found at {cache_dir_abs}")
        print("Please run get_timetable_data.py first.")
        return

    # --- Load Hub Graph and Build Mappings ---
    print(f"Loading Hub graph data from {hub_graph_file_abs}...")
    hub_graph_data = load_json_data(hub_graph_file_abs, "Hub Graph data")
    if hub_graph_data is None:
        print("Exiting due to error loading hub graph data.")
        return

    mappings = build_mappings(hub_graph_data)
    if mappings is None:
        print("Exiting due to error building mappings.")
        return
    naptan_to_hub_name, _, _ = mappings # We primarily need naptan_to_hub_name here

    valid_hub_edges_set, original_edge_lookup = get_valid_hub_edges(hub_graph_data, MODES_TO_PROCESS)
    if not valid_hub_edges_set:
         print(f"Warning: No valid hub edges found for modes {MODES_TO_PROCESS} in the graph. Cannot calculate weights.")
         # Decide whether to exit or continue (might be valid if only other modes exist)
         # return # Exit if this is unexpected

    # --- Determine Files to Process ---
    files_to_process = []
    if args.line:
        # Ensure the specified line is relevant (e.g., tube or dlr)
        # This check is basic; could refine by checking against modes_to_process if needed
        file_path = os.path.join(cache_dir_abs, f"{args.line}.json")
        if os.path.exists(file_path):
            files_to_process.append(file_path)
            print(f"Processing specified cache file: {os.path.basename(file_path)}")
        else:
            print(f"Error: Cache file for line '{args.line}' not found at {file_path}")
            return
    else:
        print(f"Processing all relevant .json files in {cache_dir_abs}...")
        try:
            all_files = [f for f in os.listdir(cache_dir_abs) if f.endswith('.json')]
            # Filter files based on whether the line name (filename without .json) corresponds to a mode we process
            # This assumes filenames match line IDs used in the hub graph edges' 'line' field.
            relevant_lines = {key[2] for key in valid_hub_edges_set} # Get lines relevant to the modes
            files_to_process = [os.path.join(cache_dir_abs, f) for f in all_files if os.path.splitext(f)[0] in relevant_lines]

            print(f"Found {len(files_to_process)} relevant cache files for modes {MODES_TO_PROCESS}.")
        except FileNotFoundError:
             print(f"Error: Cache directory not found at {cache_dir_abs}")
             return
        except Exception as e:
             print(f"Error listing cache directory {cache_dir_abs}: {e}")
             return

    if not files_to_process:
        print("No relevant cache files found to process for the specified modes.")
        return

    # --- Process Cache Files and Aggregate Durations ---
    # Stores all calculated durations across all files: {(src_hub, tgt_hub, line): [durations]}
    all_aggregated_durations = defaultdict(list)

    for cache_file in files_to_process:
        print(f"Processing cache file: {os.path.basename(cache_file)}")
        line_cache_data = load_json_data(cache_file, f"Cache file {os.path.basename(cache_file)}")

        if not line_cache_data:
            print(f"  Skipping {os.path.basename(cache_file)} due to load error or empty content.")
            continue

        line_id = line_cache_data.get("line_id")
        timetables = line_cache_data.get("timetables", {})

        if not line_id:
            print(f"  Warning: Skipping cache file {os.path.basename(cache_file)} with missing line_id.")
            continue

        # Iterate through each terminal's or point-to-point timetable data within this file
        for timetable_key, timetable_data in timetables.items():
            if timetable_data is None:
                print(f"    Skipping null data entry for key: {timetable_key}")
                continue

            # Determine the effective departure stop ID based on the key format
            departure_naptan_id = None
            if '_to_' in timetable_key:
                # Likely a point-to-point key like 'FROMNAPTAN_to_TONAPTAN'
                parts = timetable_key.split('_to_')
                if len(parts) == 2:
                    departure_naptan_id = parts[0] # Use the 'FROM' part as the departure
                    print(f"    Processing point-to-point timetable: {timetable_key}")
                else:
                    print(f"    Warning: Malformed point-to-point key '{timetable_key}'. Skipping.")
                    continue
            elif timetable_key.startswith('940GZZ') or timetable_key.startswith('910G'): # Basic check for Naptan format
                # Assume it's a standard terminal Naptan ID key
                departure_naptan_id = timetable_key
                # print(f"    Processing terminal timetable: {departure_naptan_id}") # Optional debug log
            else:
                print(f"    Warning: Unrecognized timetable key format '{timetable_key}'. Skipping.")
                continue

            # Ensure we have a valid departure ID to proceed
            if not departure_naptan_id:
                print(f"    Error: Could not determine departure Naptan ID for key '{timetable_key}'. Skipping.")
                continue

            # Process the intervals for this specific timetable fetch
            # using the determined departure_naptan_id
            durations_from_fetch = process_timetable_intervals(
                timetable=timetable_data,
                departure_stop_id=departure_naptan_id, # Use the derived ID
                line_id=line_id,
                naptan_to_hub_name=naptan_to_hub_name,
                valid_hub_edges_set=valid_hub_edges_set
            )

            # Merge the results into the main aggregation dictionary
            for key, durations in durations_from_fetch.items():
                all_aggregated_durations[key].extend(durations)

    # --- Create Output and Save ---
    # Check if any durations were actually calculated
    if not all_aggregated_durations:
        print("No valid hub-to-hub durations could be calculated from the timetable data.")
        print("Please check the cache files and the hub graph structure.")
        return

    # Create the final output structure (list of edge dicts)
    output_edges_list = create_output_edges(all_aggregated_durations, original_edge_lookup, valid_hub_edges_set)

    # Save the processed edges
    print(f"Saving {len(output_edges_list)} calculated hub edges to {output_file_abs}...")
    try:
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_file_abs), exist_ok=True)
        with open(output_file_abs, 'w', encoding='utf-8') as f:
            json.dump(output_edges_list, f, indent=4) # Use indent=4 for readability matching original
        print("Successfully saved calculated hub edges.")
    except IOError as e:
        print(f"Error saving output file {output_file_abs}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while saving the output: {e}")

if __name__ == "__main__":
    # This ensures the script runs when executed directly
    main() 