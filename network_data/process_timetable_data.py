#!/usr/bin/env python3
"""
Process Timetable Data

This script processes the cached raw timetable data fetched by 
get_timetable_data.py. It calculates the travel time between adjacent 
stations for each line based on the TfL timetable information.

It identifies and reports discrepancies where different travel times are found
for the same station pair on the same line (e.g., from different terminals or branches).

The output is a JSON file containing a list of edges with calculated durations,
formatted similarly to the edges in the main network graph file.

Usage:
    python3 process_timetable_data.py [--line <line_id>]

Arguments:
    --line (optional): Process only a specific cached line file (e.g., district).
                       If omitted, all .json files in timetable_cache/ will be processed.

Output:
    Creates calculated_timetable_edges.json in the network_data directory.
    Prints discrepancies found in travel times to the console.
"""

import json
import os
import argparse
from collections import defaultdict
import math # Import math for isnan check
import statistics # For calculating average

CACHE_DIR = "timetable_cache"
OUTPUT_FILE = "calculated_timetable_edges.json"
GRAPH_FILE = "networkx_graph_new.json"
DISCREPANCY_THRESHOLD = 2 # Max difference in minutes to allow averaging
MIN_DURATION = 0.1 # Minimum duration in minutes if calculation results in <= 0

def load_json_data(file_path, data_description):
    """
    Loads JSON data from a file with error handling.
    
    Args:
        file_path (str): Path to the JSON file.
        data_description (str): Description of the data for error messages.
        
    Returns:
        dict or list: Loaded JSON data, or None if an error occurs.
    """
    if not os.path.exists(file_path):
        print(f"Error: {data_description} file not found at {file_path}")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Handle potentially empty files
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

def process_cached_line(line_cache_data, station_id_to_name, valid_original_edges):
    """
    Processes cached timetable data for a single line to calculate durations,
    only storing durations for edges that exist in the original graph.
    
    Args:
        line_cache_data (dict): The cached data for one line.
        station_id_to_name (dict): Mapping from Naptan ID to station name.
        valid_original_edges (set): A set of tuples (from_id, to_id, line_id) representing
                                     valid edges from the original graph file.
        
    Returns:
        dict: Mapping (from_stop_id, to_stop_id, line_id) -> list of durations.
    """
    # { (from_stop_id, to_stop_id, line_id) : [duration1, duration2,...] }
    durations_by_direction_line = defaultdict(list)
    
    line_id = line_cache_data.get("line_id")
    timetables = line_cache_data.get("timetables", {})

    if not line_id:
        print("Warning: Skipping cache data with missing line_id.")
        return durations_by_direction_line

    # Iterate through each terminal's timetable data for this line
    for terminal_id, timetable in timetables.items():
        # Skip if data fetching failed for this terminal (marked as None in cache)
        if timetable is None:
            # print(f"  Skipping failed fetch for terminal {terminal_id} on line {line_id}") # Reduced verbosity
            continue 
            
        # Navigate the complex structure to get to the intervals
        actual_timetable = timetable.get("timetable")
        if not actual_timetable:
            continue
            
        departure_stop_id = actual_timetable.get("departureStopId")
        routes = actual_timetable.get("routes", [])
        
        for route in routes:
            station_intervals_list = route.get("stationIntervals", [])
            for station_interval_group in station_intervals_list:
                intervals = station_interval_group.get("intervals", [])
                last_stop_id = departure_stop_id
                last_time = 0.0
                
                # Process intervals to calculate adjacent times
                for interval in intervals:
                    current_stop_id = interval.get("stopId")
                    current_time = interval.get("timeToArrival")

                    # Check if data is valid AND if the stop is different from the last one
                    if current_stop_id and last_stop_id and current_stop_id != last_stop_id and current_time is not None and not math.isnan(current_time):
                        
                        # --- NEW Check: Ensure this edge exists in the original graph --- 
                        edge_key = (last_stop_id, current_stop_id, line_id)
                        # We check both directions as the base graph might define A->B but timetable calculates B->A
                        if edge_key in valid_original_edges or (current_stop_id, last_stop_id, line_id) in valid_original_edges:
                            # Calculate duration from the *previous* station in the sequence
                            duration = current_time - last_time
                            
                            # Ensure duration is non-negative
                            if duration <= 0: 
                                duration = MIN_DURATION # Set a minimum duration
                            
                            # Store the duration ONLY if the edge is valid
                            durations_by_direction_line[edge_key].append(duration) # Store as float
                        # else:
                            # Optional: Log edges from timetable API that are skipped because they aren't in the base graph
                            # name1 = station_id_to_name.get(last_stop_id, last_stop_id)
                            # name2 = station_id_to_name.get(current_stop_id, current_stop_id)
                            # print(f"    Skipping duration calculation for non-graph edge: {name1} -> {name2} on line {line_id}")
                        # --- End NEW Check --- 
                        
                        # Update for the next iteration (regardless of whether duration was stored)
                        last_stop_id = current_stop_id
                        last_time = current_time
                    # Handle cases where the current interval is invalid or the stop is the same as the last
                    elif current_stop_id and current_time is not None and not math.isnan(current_time):
                         # If the stop is the same, just update the 'last' trackers
                         last_stop_id = current_stop_id
                         last_time = current_time
                    else:
                         # print(f"    Warning: Skipping interval with missing data: {interval} on line {line_id} from {terminal_id}") # Reduced verbosity
                         # If an interval is skipped, reset the 'last' tracking
                         last_stop_id = None 
                         last_time = 0.0
                         break # Stop processing this specific interval sequence
                         
    return durations_by_direction_line

def get_final_duration(durations, line_id, from_id, to_id):
    """
    Determines the final duration for a directional pair, handling discrepancies.
    
    Args:
        durations (list): List of calculated durations for this pair.
        line_id (str): Line ID for logging.
        from_id (str): Source station ID for logging.
        to_id (str): Target station ID for logging.
        
    Returns:
        float: The final calculated duration (averaged or first value, rounded to 1 decimal), or None if input is empty.
    """
    if not durations:
        return None
        
    unique_durations = set(durations)
    
    if len(unique_durations) == 1:
        return durations[0] # No discrepancy
    else:
        min_d = min(durations)
        max_d = max(durations)
        diff = max_d - min_d
        
        # Check if discrepancy is within threshold
        if diff <= DISCREPANCY_THRESHOLD:
            # Average the durations
            avg_duration = statistics.mean(durations)
            final_duration = max(MIN_DURATION, round(avg_duration, 1)) # Round to 1 decimal, ensure minimum
            # print(f"    Averaging durations for {line_id}: {from_id} -> {to_id}. Original: {sorted(durations)}, Avg: {avg_duration:.2f}, Final: {final_duration}")
            return final_duration
        else:
            # Discrepancy is too large - use average anyway but warn
            print(f"  Warning: Large discrepancy for Line: {line_id}, Stations: {from_id} -> {to_id}. Times (minutes): {sorted(list(unique_durations))}. Using average.")
            avg_duration = statistics.mean(durations)
            final_duration = max(MIN_DURATION, round(avg_duration, 1)) # Round to 1 decimal, ensure minimum
            return final_duration

def report_discrepancies(all_durations):
    """
    Identifies and prints discrepancies in calculated durations.
    
    Args:
        all_durations (dict): Dictionary mapping (from_id, to_id, line_id) to list of durations.
    """
    print("\nChecking for discrepancies...")
    discrepancy_count = 0
    large_discrepancy_count = 0
    
    for (from_id, to_id, line_id), durations in all_durations.items():
        unique_durations = set(durations)
        if len(unique_durations) > 1:
            discrepancy_count += 1
            min_d = min(durations)
            max_d = max(durations)
            if max_d - min_d > DISCREPANCY_THRESHOLD:
                large_discrepancy_count += 1
                print(f"  *LARGE* Discrepancy found for Line: {line_id}, Stations: {from_id} -> {to_id}, Times (minutes): {sorted(list(unique_durations))}")
            # else:
                # Optionally print minor discrepancies being averaged
                # print(f"  Minor discrepancy found for Line: {line_id}, Stations: {from_id} -> {to_id}, Times (minutes): {sorted(list(unique_durations))}")
            
    if discrepancy_count == 0:
        print("  No discrepancies found.")
    else:
        print(f"  Found {discrepancy_count} directional pairs with discrepant times ({large_discrepancy_count} with large discrepancies > {DISCREPANCY_THRESHOLD} mins).")

def create_output_edges(all_durations, graph_data):
    """
    Creates the final edge list using processed durations and reports discrepancies
    against the original graph edges (for Tube and DLR only).
    
    Args:
        all_durations (dict): Dictionary mapping (from_id, to_id, line_id) to list of durations.
        graph_data (dict): The loaded main network graph data.
        
    Returns:
        list: A list of final edge dictionaries with calculated durations.
    """
    print("\nCreating final edge list with processed durations...")
    output_edges = []
    original_edges_all = graph_data.get('edges', []) # Renamed to avoid confusion
    nodes_data = graph_data.get('nodes', {})
    station_id_to_name = {data.get('id'): name for name, data in nodes_data.items() if data.get('id')}
    station_name_to_id = {v: k for k, v in station_id_to_name.items()}
    
    # --- Edge Comparison Logic --- 
    # Store original TUBE/DLR non-transfer edges as (from_id, to_id, line_id)
    original_tube_dlr_edges = set()
    # Store the details for easier reporting
    original_edge_details = {}
    # Lookup for original edges: (from_id, to_id, line_id) -> edge_details
    original_edge_lookup = {}

    # Filter original edges to only include Tube and DLR for comparison
    valid_modes = {'tube', 'dlr'}
    for edge in original_edges_all:
        # Only consider non-transfer edges with a valid mode (tube/dlr)
        if not edge.get('transfer') and edge.get('line') and edge.get('mode') in valid_modes:
            source_name = edge.get('source')
            target_name = edge.get('target')
            line_id = edge.get('line')
            source_id = station_name_to_id.get(source_name)
            target_id = station_name_to_id.get(target_name)
            
            if source_id and target_id and line_id:
                key = (source_id, target_id, line_id)
                original_tube_dlr_edges.add(key) # Add to the set for comparison
                original_edge_lookup[key] = edge # Keep lookup for all matched edges
                original_edge_details[key] = { # Store info for reporting missing calculated edges
                    "source_name": source_name,
                    "target_name": target_name,
                    "line": line_id,
                    "mode": edge.get('mode') # Include mode for clarity if needed
                } 
            else:
                # This warning is less critical now, could be commented out
                # print(f"    Warning: Could not get IDs for original edge: {source_name} -> {target_name} on line {line_id}")
                pass

    # Keep track of edges found in calculated data but not in the original TUBE/DLR graph
    # Note: This set should be empty now due to the check in process_cached_line, but we keep the reporting structure
    calculated_edges_missing_in_original = set()
    # Keep track of edges successfully processed and matched
    processed_directional_pairs = set()
    # --- End Edge Comparison Logic Setup ---

    # Iterate through the calculated durations (which should now only contain valid graph edges)
    for (from_id, to_id, line_id), durations in all_durations.items():
        
        # Check if this specific directional pair has already been processed
        if (from_id, to_id, line_id) in processed_directional_pairs:
            continue
            
        # Get the final duration
        final_duration = get_final_duration(durations, line_id, from_id, to_id)
        
        if final_duration is None:
            continue # Should ideally not happen if calculation succeeded, but safe check

        # --- Edge Matching and Creation ---
        # Since process_cached_line now filters, we expect a match
        original_edge = original_edge_lookup.get((from_id, to_id, line_id)) or original_edge_lookup.get((to_id, from_id, line_id))
        matched_key_direct = (from_id, to_id, line_id)
        matched_key_reverse = (to_id, from_id, line_id)
        
        if original_edge:
             # Remove the *specific matched direction* edge from the set tracking missing calculated edges
             if (from_id, to_id, line_id) == matched_key_direct:
                 original_tube_dlr_edges.discard(matched_key_direct)
             elif (to_id, from_id, line_id) == matched_key_reverse:
                 original_tube_dlr_edges.discard(matched_key_reverse)
             # else: This case should not happen if original_edge was found based on these keys
             
             # Get source and target names from the matched original edge
             source_name = original_edge['source']
             target_name = original_edge['target']
             # Check if the source/target name corresponds to the calculated direction
             source_matches_from = station_name_to_id.get(source_name) == from_id
             target_matches_to = station_name_to_id.get(target_name) == to_id
             
             # If the original edge was the reverse, swap names for output
             if not (source_matches_from and target_matches_to):
                 if station_name_to_id.get(source_name) == to_id and station_name_to_id.get(target_name) == from_id:
                      source_name, target_name = target_name, source_name
                 else:
                      name1 = station_id_to_name.get(from_id, from_id)
                      name2 = station_id_to_name.get(to_id, to_id)
                      print(f"Error: ID/Name mismatch for edge {name1} ({from_id}) -> {name2} ({to_id}) on line {line_id}. Original: {original_edge['source']} -> {original_edge['target']}. Skipping output edge.")
                      continue 
             
             output_edge = {
                 "source": source_name, 
                 "target": target_name,
                 "line": line_id,
                 "line_name": original_edge.get('line_name', ''),
                 "mode": original_edge.get('mode', ''),
                 "duration": final_duration,
                 "weight": final_duration,
                 "transfer": False,
                 "direction": original_edge.get('direction', ''),
                 "branch": original_edge.get('branch', ''),
             }
             output_edges.append(output_edge)
             processed_directional_pairs.add((from_id, to_id, line_id))

        else:
            # This case *should not* happen anymore due to the pre-filtering in process_cached_line
            # If it does, it indicates an issue with the filtering logic or the lookups.
            calculated_edges_missing_in_original.add((from_id, to_id, line_id))
        # --- End Edge Matching and Creation ---
        
    print(f"Created {len(output_edges)} processed directional Tube/DLR edges matching the original graph.")

    # --- Reporting Discrepancies --- 
    print("\n--- Edge Discrepancy Report (Tube/DLR Only) ---")
    # This list should ideally be empty now.
    if calculated_edges_missing_in_original:
        print(f"\n*UNEXPECTED* Warning: {len(calculated_edges_missing_in_original)} Edges Calculated from Timetable but NOT Found in Original Graph ({GRAPH_FILE}):")
        sorted_missing_original = sorted(list(calculated_edges_missing_in_original))
        for i, (f_id, t_id, l_id) in enumerate(sorted_missing_original):
            name1 = station_id_to_name.get(f_id, f_id)
            name2 = station_id_to_name.get(t_id, t_id)
            print(f"  {i+1}. Line: {l_id}, Direction: {name1} ({f_id}) -> {name2} ({t_id})")
    # else:
        # print("\nAll edges calculated from the timetable corresponded to edges in the original graph (as expected).")

    # original_tube_dlr_edges now contains Tube/DLR edges from the original graph for which no duration was calculated
    if original_tube_dlr_edges:
        print(f"\nWarning: {len(original_tube_dlr_edges)} Tube/DLR Edges Found in Original Graph ({GRAPH_FILE}) but NOT Calculated from Timetable:")
        sorted_missing_calculated = sorted(list(original_tube_dlr_edges), key=lambda x: (x[2], original_edge_details.get(x, {}).get("source_name", "")))
        for i, key in enumerate(sorted_missing_calculated):
            details = original_edge_details.get(key)
            if details:
                 print(f"  {i+1}. Line: {details['line']}, Direction: {details['source_name']} ({key[0]}) -> {details['target_name']} ({key[1]})")
            else:
                 print(f"  {i+1}. Line: {key[2]}, Direction: {key[0]} -> {key[1]}")
    else:
         print(f"\nAll non-transfer Tube/DLR edges from the original graph had corresponding timetable calculations.")
    print("--- End Edge Discrepancy Report ---")
    # --- End Reporting Discrepancies --- 

    return output_edges

def main():
    """Main function to process cached timetable data."""
    parser = argparse.ArgumentParser(description="Process cached TfL timetable data.")
    parser.add_argument("--line", help="Specific line ID (cache file name without .json) to process.")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_dir_path = os.path.join(script_dir, CACHE_DIR)
    output_file_path = os.path.join(script_dir, OUTPUT_FILE)
    graph_file_path = os.path.join(script_dir, GRAPH_FILE)
    
    if not os.path.isdir(cache_dir_path):
        print(f"Error: Cache directory not found at {cache_dir_path}")
        print("Please run get_timetable_data.py first.")
        return

    print(f"Loading main graph data from {graph_file_path}...")
    graph_data = load_json_data(graph_file_path, "Graph data")
    if graph_data is None:
        print("Exiting due to error loading graph data.")
        return
        
    # Create station ID to name mapping
    nodes_data = graph_data.get('nodes', {})
    station_id_to_name = {data.get('id'): name for name, data in nodes_data.items() if data.get('id')}
    station_name_to_id = {v: k for k, v in station_id_to_name.items()}
    if not station_id_to_name or not station_name_to_id:
        print("Error: Could not create station ID/name mappings from graph data.")
        return

    # --- Create set of valid original Tube/DLR edges --- 
    original_edges_all = graph_data.get('edges', [])
    valid_original_tube_dlr_edges = set()
    valid_modes = {'tube', 'dlr'}
    for edge in original_edges_all:
        if not edge.get('transfer') and edge.get('line') and edge.get('mode') in valid_modes:
            source_name = edge.get('source')
            target_name = edge.get('target')
            line_id = edge.get('line')
            source_id = station_name_to_id.get(source_name)
            target_id = station_name_to_id.get(target_name)
            if source_id and target_id and line_id:
                valid_original_tube_dlr_edges.add((source_id, target_id, line_id))
    print(f"Identified {len(valid_original_tube_dlr_edges)} valid Tube/DLR edges in the original graph for comparison.")
    # --- End valid edge set creation --- 

    # Aggregate durations from all relevant cache files
    all_calculated_durations = defaultdict(list)

    files_to_process = []
    if args.line:
        file_path = os.path.join(cache_dir_path, f"{args.line}.json")
        if os.path.exists(file_path):
            files_to_process.append(file_path)
            print(f"Processing specified cache file: {os.path.basename(file_path)}")
        else:
            print(f"Error: Cache file for line '{args.line}' not found at {file_path}")
            return
    else:
        print(f"Processing all .json files in {cache_dir_path}...")
        try:
            files_to_process = [os.path.join(cache_dir_path, f) for f in os.listdir(cache_dir_path) if f.endswith('.json')]
            print(f"Found {len(files_to_process)} cache files to process.")
        except FileNotFoundError:
             print(f"Error: Cache directory not found at {cache_dir_path}")
             return
        except Exception as e:
             print(f"Error listing cache directory {cache_dir_path}: {e}")
             return

    if not files_to_process:
        print("No cache files found to process.")
        return

    # Process each cache file, passing the set of valid edges
    for cache_file in files_to_process:
        # print(f"\nProcessing cache file: {os.path.basename(cache_file)}") # Reduced verbosity
        line_cache_data = load_json_data(cache_file, f"Cache file {os.path.basename(cache_file)}")
        if line_cache_data:
            # Pass the valid edges set here
            line_durations = process_cached_line(line_cache_data, station_id_to_name, valid_original_tube_dlr_edges)
            # Merge durations into the main dictionary
            for key, durations in line_durations.items():
                all_calculated_durations[key].extend(durations)
        # else:
            # print(f"  Skipping processing for {os.path.basename(cache_file)} due to load error or empty content.") # Reduced verbosity

    # Report duration discrepancies (this remains unchanged)
    report_discrepancies(all_calculated_durations)
    
    # Create the final output structure and report edge discrepancies
    output_edges = create_output_edges(all_calculated_durations, graph_data)

    # Save the processed edges
    print(f"\nSaving calculated edges to {output_file_path}...")
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(output_edges, f, indent=2)
        print("Successfully saved calculated edges.")
    except IOError as e:
        print(f"Error saving output file {output_file_path}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while saving the output: {e}")

if __name__ == "__main__":
    main() 