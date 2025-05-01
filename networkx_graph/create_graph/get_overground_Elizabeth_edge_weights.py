#!/usr/bin/env python3
"""
Get Overground and Elizabeth Line Journey Times

This script calls the TfL Journey API to get accurate journey times between
adjacent stations for the London Overground and Elizabeth lines, using the
hub-based graph structure. It averages journey times if multiple valid direct
routes are returned by the API within defined thresholds.

The results are saved to Edge_weights_overground_elizabeth.json, updating any
existing entries or adding new ones.

Usage:
    python3 get_overground_Elizabeth_edge_weights.py
"""

import json
import os
# Removed argparse as we are processing a fixed set of lines
import time
import requests
from datetime import datetime
import urllib.parse
import statistics # Added for averaging journey times

# --- Configuration ---
# Determine the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Define the data directory relative to the script's directory
DATA_DIR = os.path.join(SCRIPT_DIR, "../graph_data")

# Define filenames (relative to DATA_DIR)
GRAPH_DATA_FILE = "networkx_graph_hubs_with_transfer_weights.json"
OUTPUT_FILE = "calculated_hub_edge_weights.json"

# Construct full paths using the absolute DATA_DIR
GRAPH_DATA_FULL_PATH = os.path.join(DATA_DIR, GRAPH_DATA_FILE)
OUTPUT_FILE_FULL_PATH = os.path.join(DATA_DIR, OUTPUT_FILE)

# Lines to process in this script
LINES_TO_PROCESS = [
    "elizabeth",
    "weaver",            # Overground line name
    "suffragette",       # Overground line name
    "windrush",          # Overground line name
    "mildmay",           # Overground line name
    "lioness",           # Overground line name
    "liberty",           # Overground line name
] # Adjust these names based on the actual line IDs in graph data

# API configuration
API_ENDPOINT = "https://api.tfl.gov.uk/Journey/JourneyResults"
# Base parameters for the API call - use a future date and off-peak time
API_PARAMS = {
    "date": "20250510",  # Future date to minimize disruption impact
    "time": "1100",       # Off-peak time
    "timeIs": "Departing",
    "journeyPreference": "LeastInterchange" # Preference for direct routes
}
# Averaging thresholds (from get_missing_journey_times.py)
MAX_DURATION_DIFFERENCE_MINS = 3.0 # Max absolute difference allowed for averaging
MAX_DURATION_DIFFERENCE_PERCENT = 0.3 # Max relative difference allowed for averaging (30%)
# Delay between API calls to avoid hitting rate limits
API_DELAY_SECONDS = 1
# --- End Configuration ---


# --- API Credentials ---
# Try to get TfL API key and App ID from environment variables
# These are needed to make requests to the TfL API
TFL_API_KEY = os.environ.get("TFL_API_KEY", "")
TFL_APP_ID = os.environ.get("TFL_APP_ID", "")

# Add credentials to the base API parameters if they are found
if TFL_API_KEY:
    API_PARAMS["app_key"] = TFL_API_KEY
if TFL_APP_ID:
    API_PARAMS["app_id"] = TFL_APP_ID
# --- End API Credentials ---

def load_graph_data(file_path):
    """
    Load the graph data (nodes and edges) from the NetworkX JSON file.

    Args:
        file_path (str): Path to the graph JSON file.

    Returns:
        tuple: A tuple containing (nodes_list, edges_list), or (None, None)
               if the file is not found or is invalid.
    """
    # Check if the specified file exists
    if not os.path.exists(file_path):
        print(f"Error: Graph data file {file_path} not found.")
        return None, None # Return None if file doesn't exist

    try:
        # Open the file for reading with UTF-8 encoding
        with open(file_path, 'r', encoding='utf-8') as file:
            # Load the JSON data from the file
            data = json.load(file)
            # Check if the loaded data has the expected 'nodes' and 'edges' keys
            if isinstance(data, dict) and 'nodes' in data and 'edges' in data:
                print(f"Successfully loaded {len(data['nodes'])} nodes and {len(data['edges'])} edges.")
                return data.get('nodes', []), data.get('edges', [])
            else:
                # If keys are missing, print a warning and return None
                print(f"Warning: Data in {file_path} is missing 'nodes' or 'edges' key. Cannot process.")
                return None, None
    except json.JSONDecodeError as e:
        # Handle errors if the file contains invalid JSON
        print(f"Error decoding JSON from {file_path}: {e}. Cannot process.")
        return None, None
    except Exception as e:
        # Handle any other unexpected errors during file loading
        print(f"An unexpected error occurred loading {file_path}: {e}. Cannot process.")
        return None, None

def load_existing_edges(file_path):
    """
    Loads previously calculated edges from the output JSON file.
    This function is similar to the one in get_missing_journey_times.py.
    It handles cases where the file doesn't exist, is empty, or contains invalid JSON.

    Args:
        file_path (str): Path to the JSON file containing the list of edges.

    Returns:
        list: Loaded list of edge dictionaries, or an empty list if the file
              cannot be loaded or is not in the expected list format.
    """
    # Check if the file exists before trying to open it
    if not os.path.exists(file_path):
        print(f"Info: Output file {file_path} not found. Starting fresh.")
        return [] # Return an empty list if the file does not exist

    # Check if the file is empty, which is valid JSON for an empty list,
    # but json.load() might fail depending on the library version.
    # It's safer to handle it explicitly.
    if os.path.getsize(file_path) == 0:
        print(f"Info: Output file {file_path} is empty. Starting fresh.")
        return [] # Return an empty list if the file is empty

    try:
        # Open the file for reading
        with open(file_path, 'r', encoding='utf-8') as file:
            # Load the JSON data
            data = json.load(file)
            # Check if the loaded data is a list (the expected format)
            if isinstance(data, list):
                return data # Return the list of edges
            else:
                # If the data is not a list, warn the user and return empty
                print(f"Warning: Data in {file_path} is not a list. Starting fresh.")
                return []
    except json.JSONDecodeError as e:
        # Handle errors if the JSON is invalid
        print(f"Error decoding JSON from {file_path}: {e}. Starting fresh.")
        return []
    except Exception as e:
        # Handle any other unexpected errors during loading
        print(f"An unexpected error occurred loading {file_path}: {e}. Starting fresh.")
        return []

def save_edges(edges, file_path):
    """
    Saves the list of edge dictionaries to a JSON file.
    This function is similar to the one in get_missing_journey_times.py.

    Args:
        edges (list): The list of edge dictionaries to save.
        file_path (str): Path to save the JSON file.
    """
    try:
        # Open the file in write mode ('w') which overwrites the file
        with open(file_path, 'w', encoding='utf-8') as file:
            # Dump the list of edges to the file as JSON
            # indent=2 makes the output file human-readable
            json.dump(edges, file, indent=2)
        # Print a confirmation message
        print(f"Successfully saved {len(edges)} edges to {file_path}")
    except IOError as e:
        # Handle errors that might occur during file writing (e.g., permissions)
        print(f"Error saving output file {file_path}: {e}")
    except Exception as e:
        # Handle any other unexpected errors during saving
        print(f"An unexpected error occurred while saving the output: {e}")


def get_and_average_journey_time(from_id, to_id, mode, line):
    """
    Gets journey time(s) from TfL API for a specific station pair, mode, and line.
    It averages the duration if multiple valid direct journeys are found within
    the defined difference thresholds.
    This function incorporates the logic from get_missing_journey_times.py.

    Args:
        from_id (str): The source station Naptan ID.
        to_id (str): The target station Naptan ID.
        mode (str): The transport mode (e.g., 'overground', 'elizabeth-line').
                     Note: TfL API might use 'elizabeth-line' or 'national-rail'.
                     We may need to adjust the mode parameter if needed.
        line (str): The specific line ID (e.g., 'elizabeth', 'mildmay').

    Returns:
        float: The final calculated journey time in minutes (possibly averaged),
               rounded to 1 decimal place, or None if the API call fails or
               no valid direct journey on the specified line is found.
    """
    # Construct the API URL using the source and target station IDs
    # We need to URL-encode the IDs in case they contain special characters
    url = f"{API_ENDPOINT}/{urllib.parse.quote(from_id)}/to/{urllib.parse.quote(to_id)}"

    # Prepare parameters for this specific API call by copying the base params
    params = API_PARAMS.copy()
    # Add the specific mode for this request
    # TfL uses 'elizabeth-line' and 'overground' as mode IDs
    params["mode"] = mode

    # List to store valid durations found for the specified line
    valid_durations = []

    try:
        # --- Making the API Request ---
        # Print the URL and parameters for debugging purposes
        # Mask the API key if it's present for security
        debug_params = params.copy()
        if "app_key" in debug_params:
            debug_params["app_key"] = "****" # Hide API key in logs
        print(f"  Calling API: {url} with params: {debug_params}")

        # Execute the GET request to the TfL API
        response = requests.get(url, params=params)
        # Print the HTTP status code returned by the API
        print(f"  API response status: {response.status_code}")

        # Check if the request was unsuccessful (status code other than 200 OK)
        if response.status_code != 200:
            print(f"  API request failed with status code {response.status_code}")
            # Try to print the response body, as it might contain error details
            try:
                print(f"  Response body: {response.text}")
            except Exception:
                pass # Ignore errors if the body can't be printed
            return None # Return None to indicate failure

        # --- Processing the API Response ---
        # Parse the JSON response received from the API
        data = response.json()

        # Check if the response contains a 'journeys' key and it's not empty
        if "journeys" in data and data["journeys"]:
            # Iterate through each journey plan returned by the API
            for journey in data["journeys"]:
                # Check if the journey consists of segments ('legs')
                if "legs" in journey:
                    legs = journey["legs"]
                    # Filter out legs that are purely walking, we only want transit legs
                    transit_legs = [leg for leg in legs if leg.get("mode", {}).get("id") != "walking"]

                    # We are looking for direct journeys on the SPECIFIC line we requested.
                    # This means the journey should have exactly one transit leg.
                    if len(transit_legs) == 1:
                        transit_leg = transit_legs[0]
                        # Extract route options to find the line used for this leg
                        route_options = transit_leg.get("routeOptions", [])
                        # Get the line identifier from the first route option, if available
                        # Line ID seems to be under routeOptions[0].lineIdentifier.id
                        leg_line_id = None
                        if route_options and route_options[0].get("lineIdentifier"):
                           leg_line_id = route_options[0]["lineIdentifier"].get("id")

                        # Check if the leg's line ID matches the specific line we are querying for
                        if leg_line_id == line:
                            # Try to get the duration directly from the leg itself
                            leg_duration = transit_leg.get("duration")
                            if leg_duration is not None:
                                # Found a valid leg on the correct line with duration
                                print(f"    Found valid leg: Line={leg_line_id}, Duration={leg_duration} mins")
                                # Ensure duration is at least 1.0 minute (changed from 0.1)
                                valid_durations.append(max(1.0, float(leg_duration)))
                                continue # Process next journey in the response

                            # If the leg duration is missing, fall back to the total journey duration
                            # This might happen sometimes, API inconsistency
                            journey_duration = journey.get("duration")
                            if journey_duration is not None:
                                print(f"    Found valid journey (using journey duration): Line={leg_line_id}, Duration={journey_duration} mins")
                                # Ensure duration is at least 1.0 minute (changed from 0.1)
                                valid_durations.append(max(1.0, float(journey_duration)))
                                continue # Process next journey

            # --- Averaging Logic ---
            # After checking all journeys in the response
            if not valid_durations:
                # No valid durations were found for this specific line and station pair
                print(f"  Warning: No valid single-leg journey found for line {line} between {from_id} and {to_id}")
                return None # Indicate that no valid time was found

            if len(valid_durations) == 1:
                # Exactly one valid duration was found, return it directly
                # Round to 1 decimal place for consistency
                final_duration = round(valid_durations[0], 1)
                print(f"  Single valid duration found: {final_duration:.1f} mins")
                # Make sure it's still at least 1.0 after rounding (changed from 0.1)
                return max(1.0, final_duration)
            else:
                # Multiple valid durations were found, apply the averaging logic
                min_d = min(valid_durations) # Find the minimum duration
                max_d = max(valid_durations) # Find the maximum duration
                diff_abs = max_d - min_d      # Calculate absolute difference
                # Calculate relative difference, avoid division by zero if max_d is 0
                diff_rel = (diff_abs / max_d) if max_d > 0 else 0

                # Log the found durations and the calculated differences
                print(f"  Multiple valid durations found: {sorted(valid_durations)}")
                print(f"    Min: {min_d:.1f}, Max: {max_d:.1f}, Abs Diff: {diff_abs:.1f}, Rel Diff: {diff_rel:.2%}")

                # Check if the differences are within the acceptable thresholds
                if diff_abs <= MAX_DURATION_DIFFERENCE_MINS and diff_rel <= MAX_DURATION_DIFFERENCE_PERCENT:
                    # Differences are small enough, calculate the average
                    avg_duration = statistics.mean(valid_durations)
                    # Round the average to 1 decimal place
                    final_duration = round(avg_duration, 1)
                    print(f"    Difference within threshold. Averaging to: {final_duration:.1f} mins")
                    # Ensure the final average is at least 1.0 (changed from 0.1)
                    return max(1.0, final_duration)
                else:
                    # Differences are too large, print a warning
                    print(f"    Warning: Large difference between durations ({diff_abs:.1f}m / {diff_rel:.2%}).")
                    # Decide how to handle large differences. The original script averaged anyway.
                    # Alternative: could return None, or the minimum, or raise an error.
                    # Let's stick to the original approach: average but warn.
                    avg_duration = statistics.mean(valid_durations)
                    final_duration = round(avg_duration, 1)
                    print(f"    Using average despite large difference: {final_duration:.1f} mins")
                    # Ensure the final average is at least 1.0 (changed from 0.1)
                    return max(1.0, final_duration)

        else:
            # The API response did not contain any 'journeys' data
            print(f"  No journey data found in API response for {from_id} to {to_id}")
            return None # Indicate no journey was found

    except requests.exceptions.RequestException as e:
        # Handle network-related errors during the API request (e.g., connection error)
        print(f"  API request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        # Handle errors if the API response is not valid JSON
        print(f"  Error decoding API response JSON: {e}")
        return None
    except Exception as e:
        # Catch any other unexpected errors during API call or response processing
        print(f"  An unexpected error occurred processing API response: {e}")
        return None

def main():
    """
    Main function to:
    1. Load graph definitions (nodes and edges).
    2. Load existing calculated edge weights (if any).
    3. Iterate through specified lines (Overground, Elizabeth).
    4. Iterate through edges belonging to these lines.
    5. Skip edges already present in the loaded weights.
    6. Determine correct Naptan IDs (handling HUBs).
    7. Call TfL API to get (and average) journey time for new edges.
    8. Construct edge dictionaries in the target format.
    9. Append new edges to the list.
    10. Save the complete list of edges to the output file.
    """
    # Use the pre-calculated absolute paths
    graph_data_file_path = GRAPH_DATA_FULL_PATH
    output_file_path = OUTPUT_FILE_FULL_PATH

    # --- Load Input Data ---
    # Load the graph data (nodes and edges)
    print(f"Loading graph data from {graph_data_file_path}...")
    # Ensure the loading function is called with the correct path
    graph_nodes, graph_edges = load_graph_data(graph_data_file_path)

    # Check if graph data was loaded successfully
    if graph_nodes is None or graph_edges is None:
        print("Failed to load graph data. Cannot proceed.")
        print(f"Ensure the file exists and is valid JSON: {graph_data_file_path}")
        return # Exit if we don't have the input data

    # Build a map from node ID (hub_name) to node data for easy lookup
    node_map = {node['id']: node for node in graph_nodes}
    print(f"Built node map with {len(node_map)} entries.")

    # Load existing edges from the output file.
    # This helps prevent redundant API calls if the script is run multiple times.
    print(f"Loading existing calculated edges from {output_file_path}...")
    # Ensure the loading function is called with the correct path
    all_calculated_edges = load_existing_edges(output_file_path)
    print(f"Loaded {len(all_calculated_edges)} existing calculated edges.")

    # Create a set of keys for quick lookup of existing edges to avoid duplicates.
    # The key combines source name, target name, and line ID.
    existing_edge_keys = set()
    for edge in all_calculated_edges:
        # Ensure the existing edge has the necessary keys to create a unique identifier
        if all(k in edge for k in ('source', 'target', 'line', 'weight')):
            key = f"{edge['source']}|{edge['target']}|{edge['line']}"
            existing_edge_keys.add(key)
        else:
            # Warn if an existing edge is missing key information
            print(f"Warning: Skipping existing edge due to missing keys: {edge}")
    # --- End Load Input Data ---

    # --- Process Edges ---
    # Counter for newly added edges during this run
    added_count = 0
    # Counter for total pairs processed in this run that needed API calls
    api_processed_count = 0
    # List to keep track of edges that failed API calls
    failed_edges = []

    # Iterate through the edges loaded from the graph data file
    print(f"\nProcessing edges from {GRAPH_DATA_FILE} for lines: {', '.join(LINES_TO_PROCESS)}")
    total_edges_in_file = len(graph_edges)
    for i, edge_info in enumerate(graph_edges):

        # Extract basic edge information
        line = edge_info.get('line')
        mode = edge_info.get('mode') # Use mode directly from edge data
        source_name = edge_info.get('source') # This is the Hub Name
        target_name = edge_info.get('target') # This is the Hub Name

        # --- Filter by Line ---
        # Skip edges not belonging to the lines we want to process
        if line not in LINES_TO_PROCESS:
            continue

        # --- Validate Minimum Data ---
        # Check if we have the essential info for this edge
        if not all([source_name, target_name, line, mode]):
            print(f"  [{i+1}/{total_edges_in_file}] Line {line}: Warning - Skipping edge due to missing data: {source_name} -> {target_name}")
            continue

        # --- Check if Edge Already Processed ---
        edge_key = f"{source_name}|{target_name}|{line}"
        if edge_key in existing_edge_keys:
            # print(f"  [{i+1}/{total_edges_in_file}] Line {line}: Edge {source_name} -> {target_name} already exists. Skipping.")
            continue # Skip if already calculated

        # --- Get Naptan IDs for API Call ---
        print(f"\n[{i+1}/{total_edges_in_file}] Processing Edge: {source_name} -> {target_name} on {line} ({mode})")
        api_processed_count += 1 # Increment counter for edges needing API call

        source_node_data = node_map.get(source_name)
        target_node_data = node_map.get(target_name)

        if not source_node_data or not target_node_data:
            print(f"  Error: Node data not found for {source_name} or {target_name}. Skipping edge.")
            failed_edges.append(f"{source_name} -> {target_name} on {line} (Node data missing)")
            continue

        # Determine Source API ID using the refined logic
        source_api_id = None
        source_primary_id = source_node_data.get('primary_naptan_id')
        # Access the new constituent structure
        source_constituents = source_node_data.get('constituent_stations', []) 

        if source_primary_id and not source_primary_id.startswith("HUB"):
            source_api_id = source_primary_id
            print(f"  Source '{source_name}' using primary Naptan: {source_api_id}")
        elif source_constituents and isinstance(source_constituents, list) and len(source_constituents) > 0 and isinstance(source_constituents[0], dict) and 'naptan_id' in source_constituents[0]:
             # Check list is not empty and first item is dict with naptan_id
            source_api_id = source_constituents[0]['naptan_id'] # Use the naptan_id from the first dict
            print(f"  Source '{source_name}' is a HUB ({source_primary_id}). Using first constituent Naptan: {source_api_id}")
        else:
            print(f"  Error: Could not determine valid Naptan ID for source '{source_name}' (Primary: {source_primary_id}, Constituents: {source_constituents}). Skipping edge.")
            failed_edges.append(f"{source_name} -> {target_name} on {line} (Source Naptan ID unresolved)")
            continue
            
        # Determine Target API ID using the refined logic
        target_api_id = None
        target_primary_id = target_node_data.get('primary_naptan_id')
        # Access the new constituent structure
        target_constituents = target_node_data.get('constituent_stations', []) 
        
        if target_primary_id and not target_primary_id.startswith("HUB"):
            target_api_id = target_primary_id
            print(f"  Target '{target_name}' using primary Naptan: {target_api_id}")
        elif target_constituents and isinstance(target_constituents, list) and len(target_constituents) > 0 and isinstance(target_constituents[0], dict) and 'naptan_id' in target_constituents[0]:
            # Check list is not empty and first item is dict with naptan_id
            target_api_id = target_constituents[0]['naptan_id'] # Use the naptan_id from the first dict
            print(f"  Target '{target_name}' is a HUB ({target_primary_id}). Using first constituent Naptan: {target_api_id}")
        else:
            print(f"  Error: Could not determine valid Naptan ID for target '{target_name}' (Primary: {target_primary_id}, Constituents: {target_constituents}). Skipping edge.")
            failed_edges.append(f"{source_name} -> {target_name} on {line} (Target Naptan ID unresolved)")
            continue

        # --- Call API (Check IDs one last time) ---
        if not source_api_id or not target_api_id:
             # This check is slightly redundant due to the continues above, but safe.
             print(f"  Error: Final check failed - missing Naptan ID for API call ({source_api_id=}, {target_api_id=}). Skipping edge.")
             failed_edges.append(f"{source_name} -> {target_name} on {line} (Final Naptan ID check failed)")
             continue

        # Determine the mode to use for the API call
        api_mode = mode # Directly use the mode from the edge
        if mode == 'overground' and line != 'overground': # Check if mode is generic but line is specific OG line
             print(f"  Info: Using generic 'overground' mode for specific line '{line}' API call.")
             # api_mode remains 'overground'
        elif mode == 'elizabeth-line' and line != 'elizabeth':
             print(f"  Info: Using 'elizabeth-line' mode for specific line '{line}' API call.")
             # api_mode remains 'elizabeth-line'

        duration = get_and_average_journey_time(source_api_id, target_api_id, api_mode, line)

        # Pause execution briefly to avoid overwhelming the API
        print(f"  Waiting {API_DELAY_SECONDS} second(s)...")
        time.sleep(API_DELAY_SECONDS)

        # --- Store Result ---
        if duration is not None:
            # Construct the new edge dictionary to match the desired output format
            # Using 'weight' for consistency with graph structure, value is the duration
            new_edge = {
                "source": source_name,
                "target": target_name,
                "line": line,       # e.g., "windrush", "elizabeth"
                "mode": mode,       # e.g., "overground", "elizabeth-line"
                "weight": duration, # Calculated duration in minutes
                "transfer": False,  # Assuming these are direct line edges
                "branch": 0,        # Added: Default branch ID
                "direction": "unknown", # Added: Placeholder direction
                "key": line,        # Added: Use the specific line ID as the key
                "calculated_timestamp": datetime.now().isoformat()
            }
            # Add the line_name if available in the node data (e.g., from source node)
            if source_node_data.get("lines") and line in source_node_data["lines"]:
                 # This assumes the 'lines' list in node data corresponds correctly.
                 # A more robust way might involve mapping line IDs to full names if needed.
                 # For now, let's keep it simple. The 'line' field already holds the ID.
                 pass # We decided 'line' ID is sufficient for now

            all_calculated_edges.append(new_edge)
            existing_edge_keys.add(edge_key) # Mark this edge as processed
            added_count += 1
            print(f"  ---> Successfully calculated and added edge. Duration: {duration:.1f} mins.")
        else:
            print(f"  ---> Failed to get journey time for edge {source_name} -> {target_name} on {line}. Edge not added.")
            failed_edges.append(f"{source_name} -> {target_name} on {line} (API Fail/No Valid Journey)")

    # --- End loop for edges ---

    # --- Save Results ---
    # Check if any new edges were added during this run
    if added_count > 0:
        print(f"\nProcessed {api_processed_count} pairs requiring API calls across specified lines.")
        print(f"Added {added_count} new edges. Saving updated list ({len(all_calculated_edges)} total) to {output_file_path}...")
        # Save the potentially updated list of all edges back to the file
        save_edges(all_calculated_edges, output_file_path)
    else:
        # No new edges needed API calls or were successfully added
        print(f"\nProcessed {api_processed_count} pairs requiring API calls across specified lines.")
        print(f"No new valid edges were added. Output file ({output_file_path}) remains unchanged with {len(all_calculated_edges)} edges.")

    print("Script finished.")

    # --- Print Failure Summary ---
    if failed_edges:
        print("\n--- Summary of Failed Edges ---")
        print(f"Warning: Failed to retrieve journey times for {len(failed_edges)} edges:")
        for failed in failed_edges:
            print(f"  - {failed}")
        print("You may need to investigate these pairs further or check TfL API status.")
        print("-------------------------------")
    # --- End Failure Summary ---

if __name__ == "__main__":
    # This block ensures the main() function is called only when the script is executed directly
    main() 