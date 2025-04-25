#!/usr/bin/env python3
"""
Get Missing Journey Times

This script calls the TfL Journey API to get accurate journey times for a
predefined list of missing adjacent station pairs (specifically those missed
by the timetable processing) and appends the results to the
Edge_weights_tube_dlr.json file.

It handles cases where multiple valid journey durations are returned by the API
for the same station pair and line by averaging them if the difference is
within defined thresholds.

Usage:
    python3 get_missing_journey_times.py

Output:
    Appends the calculated edges for the missing pairs to
    Edge_weights_tube_dlr.json in the network_data directory.
"""

import json
import os
import time
import requests
from datetime import datetime
import urllib.parse
import statistics # Added for averaging

# --- Configuration ---
# File to load existing edges from and append to
OUTPUT_FILE = "Edge_weights_tube_dlr.json"
# API configuration
API_ENDPOINT = "https://api.tfl.gov.uk/Journey/JourneyResults"
# Parameters for the API call - use a future date and off-peak time
API_PARAMS = {
    "date": "20250510",  # Future date to minimize disruption impact
    "time": "1100",       # Off-peak time
    "timeIs": "Departing",
    "journeyPreference": "LeastInterchange" # Preference for direct routes
}
# Averaging thresholds
MAX_DURATION_DIFFERENCE_MINS = 3.0 # Max absolute difference allowed for averaging
MAX_DURATION_DIFFERENCE_PERCENT = 0.3 # Max relative difference allowed for averaging (30%)
API_DELAY_SECONDS = 1 # Delay between API calls

# --- List of Missing Edges ---
# These are the edges identified as missing from the timetable data processing.
# We need full details to reconstruct the edge entry.
# (Details obtained by inspecting networkx_graph_new.json)
MISSING_EDGES_DETAILS = [
    {
        "source": "Grange Hill Underground Station", "target": "Hainault Underground Station",
        "source_id": "940GZZLUGGH", "target_id": "940GZZLUHLT",
        "line": "central", "line_name": "Central", "mode": "tube"
    },
    {
        "source": "Earl's Court Underground Station", "target": "Kensington (Olympia) Underground Station",
        "source_id": "940GZZLUECT", "target_id": "940GZZLUKOY",
        "line": "district", "line_name": "District", "mode": "tube"
    },
    {
        "source": "All Saints DLR Station", "target": "Poplar DLR Station",
        "source_id": "940GZZDLALL", "target_id": "940GZZDLPOP",
        "line": "dlr", "line_name": "DLR", "mode": "dlr"
    },
    {
        "source": "Bow Church DLR Station", "target": "Devons Road DLR Station",
        "source_id": "940GZZDLBOW", "target_id": "940GZZDLDEV",
        "line": "dlr", "line_name": "DLR", "mode": "dlr"
    },
    {
        "source": "Devons Road DLR Station", "target": "Langdon Park DLR Station",
        "source_id": "940GZZDLDEV", "target_id": "940GZZDLLDP",
        "line": "dlr", "line_name": "DLR", "mode": "dlr"
    },
    {
        "source": "Langdon Park DLR Station", "target": "All Saints DLR Station",
        "source_id": "940GZZDLLDP", "target_id": "940GZZDLALL",
        "line": "dlr", "line_name": "DLR", "mode": "dlr"
    },
    {
        "source": "Poplar DLR Station", "target": "West India Quay DLR Station",
        "source_id": "940GZZDLPOP", "target_id": "940GZZDLWIQ",
        "line": "dlr", "line_name": "DLR", "mode": "dlr"
    },
    {
        "source": "Pudding Mill Lane DLR Station", "target": "Bow Church DLR Station",
        "source_id": "940GZZDLPUD", "target_id": "940GZZDLBOW",
        "line": "dlr", "line_name": "DLR", "mode": "dlr"
    },
    {
        "source": "Stratford DLR Station", "target": "Pudding Mill Lane DLR Station",
        "source_id": "940GZZDLSTD", "target_id": "940GZZDLPUD",
        "line": "dlr", "line_name": "DLR", "mode": "dlr"
    },
    {
        "source": "West India Quay DLR Station", "target": "Canary Wharf DLR Station",
        "source_id": "940GZZDLWIQ", "target_id": "940GZZDLCAN",
        "line": "dlr", "line_name": "DLR", "mode": "dlr"
    },
]
# --- End Configuration ---

# Try to get TfL API key from environment variables
TFL_API_KEY = os.environ.get("TFL_API_KEY", "")
TFL_APP_ID = os.environ.get("TFL_APP_ID", "")

# If API key is available, add it to default params
if TFL_API_KEY:
    API_PARAMS["app_key"] = TFL_API_KEY
if TFL_APP_ID:
    API_PARAMS["app_id"] = TFL_APP_ID

def load_existing_edges(file_path):
    """
    Loads existing calculated edges from a JSON file.
    Handles file not found or decode errors by returning an empty list.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        list: Loaded list of edge dictionaries, or empty list on error.
    """
    # Check if the file exists first
    if not os.path.exists(file_path):
        print(f"Info: Output file {file_path} not found. Starting fresh.")
        return [] # Return empty list if file doesn't exist

    # Handle potentially empty files
    if os.path.getsize(file_path) == 0:
        print(f"Info: Output file {file_path} is empty. Starting fresh.")
        return []

    try:
        # Try to open and load the JSON data
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            # Check if the loaded data is a list (expected format)
            if isinstance(data, list):
                return data
            else:
                # If not a list, print a warning and return empty list
                print(f"Warning: Data in {file_path} is not a list. Starting fresh.")
                return []
    except json.JSONDecodeError as e:
        # Handle JSON decoding errors
        print(f"Error decoding JSON from {file_path}: {e}. Starting fresh.")
        return []
    except Exception as e:
        # Handle other potential errors during file loading
        print(f"An unexpected error occurred loading {file_path}: {e}. Starting fresh.")
        return []

def save_edges(edges, file_path):
    """
    Saves the list of edge dictionaries to a JSON file.

    Args:
        edges (list): The list of edge dictionaries to save.
        file_path (str): Path to save the JSON file.
    """
    try:
        # Open the file in write mode and dump the JSON data
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(edges, file, indent=2) # Use indent=2 for readability
        print(f"Successfully saved {len(edges)} edges to {file_path}")
    except IOError as e:
        # Handle potential file writing errors
        print(f"Error saving output file {file_path}: {e}")
    except Exception as e:
        # Handle other potential errors during saving
        print(f"An unexpected error occurred while saving the output: {e}")


def get_and_average_journey_time(from_id, to_id, mode, line):
    """
    Gets journey time(s) from TfL API and averages if multiple valid times
    are found within the defined thresholds.

    Args:
        from_id (str): The source station Naptan ID.
        to_id (str): The target station Naptan ID.
        mode (str): The transport mode (e.g., 'tube', 'dlr').
        line (str): The specific line ID (e.g., 'central', 'dlr').

    Returns:
        float: The final calculated journey time in minutes (possibly averaged),
               or None if the API call fails or no valid journey is found.
    """
    # Build the API URL using the source and target IDs
    url = f"{API_ENDPOINT}/{urllib.parse.quote(from_id)}/to/{urllib.parse.quote(to_id)}"

    # Prepare parameters for the API call, copying the base params
    params = API_PARAMS.copy()
    # Add the specific mode for this request
    params["mode"] = mode

    # If the mode is DLR, remove date and time as they seem to prevent results
    if mode == 'dlr':
        print(f"  Mode is DLR, removing date and time from API params.")
        params.pop('date', None) # Remove 'date' key if it exists
        params.pop('time', None) # Remove 'time' key if it exists

    # List to store valid durations found for the specified line
    valid_durations = []

    try:
        # --- Making the API Request ---
        # Print the URL and parameters for debugging (masking API key if present)
        debug_params = params.copy()
        if "app_key" in debug_params:
            debug_params["app_key"] = "****" # Mask the API key for security
        print(f"  Calling API: {url} with params: {debug_params}")

        # Execute the GET request to the TfL API
        response = requests.get(url, params=params)
        # Print the HTTP status code received from the API
        print(f"  API response status: {response.status_code}")

        # Check if the request was unsuccessful (status code not 200)
        if response.status_code != 200:
            print(f"  API request failed with status code {response.status_code}")
            # Print the response body if available, might contain error details
            try:
                print(f"  Response body: {response.text}")
            except Exception:
                pass # Ignore errors trying to print the body
            return None # Indicate failure

        # --- Processing the API Response ---
        # Parse the JSON response from the API
        data = response.json()

        # Check if the response contains 'journeys' and it's not empty
        if "journeys" in data and data["journeys"]:
            # Iterate through each journey returned by the API
            for journey in data["journeys"]:
                # Check if the journey has 'legs' (segments)
                if "legs" in journey:
                    legs = journey["legs"]
                    # Filter out legs that are purely walking
                    transit_legs = [leg for leg in legs if leg.get("mode", {}).get("id") != "walking"]

                    # We are looking for direct journeys on the specified line
                    # Check if there is exactly one non-walking leg
                    if len(transit_legs) == 1:
                        transit_leg = transit_legs[0]
                        # Extract route options to find the line used
                        route_options = transit_leg.get("routeOptions", [])
                        # Get the line identifier from the first route option, if available
                        leg_line = route_options[0].get("lineIdentifier", {}).get("id") if route_options else None

                        # Check if the leg uses the specific line we are querying for
                        if leg_line == line:
                            # Try to get the duration directly from the leg
                            leg_duration = transit_leg.get("duration")
                            if leg_duration is not None:
                                print(f"    Found valid leg: Line={leg_line}, Duration={leg_duration} mins")
                                # Ensure duration is at least 1.0 minute (changed from 0.1)
                                valid_durations.append(max(1.0, float(leg_duration)))
                                continue # Move to the next journey

                            # If leg duration is missing, fall back to the total journey duration
                            journey_duration = journey.get("duration")
                            if journey_duration is not None:
                                print(f"    Found valid journey (using journey duration): Line={leg_line}, Duration={journey_duration} mins")
                                # Ensure duration is at least 1.0 minute (changed from 0.1)
                                valid_durations.append(max(1.0, float(journey_duration)))
                                continue # Move to the next journey

            # --- Averaging Logic ---
            if not valid_durations:
                # No valid durations found for this specific line and pair
                print(f"  Warning: No valid single-leg journey found for line {line} between {from_id} and {to_id}")
                return None

            if len(valid_durations) == 1:
                # Only one valid duration found, return it directly
                # Round to 1 decimal place and ensure minimum 1.0 (changed from 0.1)
                final_duration = max(1.0, round(valid_durations[0], 1))
                print(f"  Single valid duration found: {final_duration:.1f} mins")
                return final_duration
            else:
                # Multiple valid durations found, apply averaging logic
                min_d = min(valid_durations)
                max_d = max(valid_durations)
                diff_abs = max_d - min_d
                # Avoid division by zero if max_d is 0 (unlikely with min 1.0)
                diff_rel = (diff_abs / max_d) if max_d > 0 else 0

                print(f"  Multiple valid durations found: {sorted(valid_durations)}")
                print(f"    Min: {min_d:.1f}, Max: {max_d:.1f}, Abs Diff: {diff_abs:.1f}, Rel Diff: {diff_rel:.2%}")

                # Check if the differences are within the defined thresholds
                if diff_abs <= MAX_DURATION_DIFFERENCE_MINS and diff_rel <= MAX_DURATION_DIFFERENCE_PERCENT:
                    # Differences are acceptable, calculate the average
                    avg_duration = statistics.mean(valid_durations)
                    # Ensure the average is at least the minimum duration (1.0) and round (changed from 0.1)
                    final_duration = max(1.0, round(avg_duration, 1))
                    print(f"    Difference within threshold. Averaging to: {final_duration:.1f} mins")
                    return final_duration
                else:
                    # Differences are too large, print a warning but still average as requested
                    avg_duration = statistics.mean(valid_durations)
                    # Ensure the average is at least the minimum duration (1.0) and round (changed from 0.1)
                    final_duration = max(1.0, round(avg_duration, 1))
                    print(f"    Warning: Large difference between durations ({diff_abs:.1f}m / {diff_rel:.2%}). Using average anyway: {final_duration:.1f} mins")
                    return final_duration

        else:
            # The API response did not contain any journeys
            print(f"  No journey data found in API response for {from_id} to {to_id}")
            return None

    except requests.exceptions.RequestException as e:
        # Handle network errors or other issues during the API request
        print(f"  API request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        # Handle errors parsing the JSON response
        print(f"  Error decoding API response JSON: {e}")
        return None
    except Exception as e:
        # Catch any other unexpected errors during processing
        print(f"  An unexpected error occurred processing API response: {e}")
        return None


def main():
    """
    Main function to fetch journey times for predefined missing edges
    and append them to the output JSON file.
    """
    # Construct the full path to the output file based on the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file_path = os.path.join(script_dir, OUTPUT_FILE)

    # Load the existing edges from the output file
    print(f"Loading existing edges from {output_file_path}...")
    all_edges = load_existing_edges(output_file_path)
    print(f"Loaded {len(all_edges)} existing edges.")

    # Create a set of existing edge keys for quick lookup to avoid duplicates
    # Key format: "source_name|target_name|line_id"
    existing_edge_keys = set()
    for edge in all_edges:
        # Ensure all necessary keys exist in the edge dictionary
        if all(k in edge for k in ('source', 'target', 'line')):
            key = f"{edge['source']}|{edge['target']}|{edge['line']}"
            existing_edge_keys.add(key)
        else:
            # Print a warning if an existing edge is missing required keys
            print(f"Warning: Skipping existing edge due to missing keys: {edge.get('source','?')}|{edge.get('target','?')}|{edge.get('line','?')}")


    # Counter for newly added edges
    added_count = 0

    # Process each predefined missing edge
    print(f"Processing {len(MISSING_EDGES_DETAILS)} potentially missing edges...")
    for i, edge_info in enumerate(MISSING_EDGES_DETAILS):
        source_name = edge_info['source']
        target_name = edge_info['target']
        line_id = edge_info['line']

        # Generate the key for the current missing edge
        current_key = f"{source_name}|{target_name}|{line_id}"

        print(f"[{i+1}/{len(MISSING_EDGES_DETAILS)}] Checking edge: {source_name} -> {target_name} on {line_id}")

        # Check if this edge already exists in the loaded data
        if current_key in existing_edge_keys:
            print(f"  Edge already exists in {OUTPUT_FILE}. Skipping API call.")
            continue # Move to the next missing edge

        # --- Edge does not exist, proceed with API call ---
        source_id = edge_info['source_id']
        target_id = edge_info['target_id']
        mode = edge_info['mode']

        # Get the journey time using the updated function with averaging
        duration = get_and_average_journey_time(source_id, target_id, mode, line_id)

        # Pause execution to avoid hitting API rate limits
        print(f"  Waiting {API_DELAY_SECONDS} second(s)...")
        time.sleep(API_DELAY_SECONDS)

        # Check if a valid duration was obtained
        if duration is not None:
            # --- Construct the new edge dictionary ---
            # This structure should match 'Edge_weights_tube_dlr.json'
            new_edge = {
                "source": source_name,
                "target": target_name,
                "line": line_id,
                "line_name": edge_info.get('line_name', ''), # Use provided line name or default
                "mode": mode,
                "duration": duration, # The calculated (possibly averaged) duration
                "weight": duration,   # Use the same value for weight
                "transfer": False,    # These are direct line edges, not transfers
                # Include other fields if present in edge_info, otherwise default
                "direction": edge_info.get('direction', ''),
                "branch": edge_info.get('branch', ''),
                # Add a timestamp indicating when this specific edge was added/updated
                "calculated_timestamp": datetime.now().isoformat()
            }
            # Append the newly created edge to the main list
            all_edges.append(new_edge)
            # Add the key to the set to prevent adding duplicates within this run
            existing_edge_keys.add(current_key)
            # Increment the counter for added edges
            added_count += 1
            print(f"  Successfully calculated and added edge.")
        else:
            # Failed to get a duration for this edge pair
            print(f"  Failed to get journey time for {source_name} -> {target_name} on {line_id}. Edge not added.")

    # --- Save the final list of edges ---
    if added_count > 0:
        print(f"Added {added_count} new edges. Saving updated list...")
        save_edges(all_edges, output_file_path)
    else:
        print("No new edges were added. Output file remains unchanged.")

    print("Script finished.")

if __name__ == "__main__":
    main() 