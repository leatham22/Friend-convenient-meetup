#!/usr/bin/env python3
"""
Get Overground and Elizabeth Line Journey Times

This script calls the TfL Journey API to get accurate journey times between
adjacent stations for the London Overground and Elizabeth lines. It averages
journey times if multiple valid direct routes are returned by the API within
defined thresholds.

The results are saved to Edge_weights_overground_elizabeth.json, matching the
format used for Tube and DLR lines.

Usage:
    python3 get_journey_times.py
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
# File containing adjacent station pairs for each line
LINE_EDGES_FILE = "line_edges.json"
# Output file for the calculated edge weights
OUTPUT_FILE = "Edge_weights_overground_elizabeth.json"
# Lines to process in this script
LINES_TO_PROCESS = [
    "elizabeth",
    # List all Overground lines explicitly by their key in line_edges.json
    "weaver",            # Overground line name
    "suffragette",       # Overground line name
    "windrush",          # Overground line name
    "mildmay",           # Overground line name
    "lioness",           # Overground line name
    "liberty",           # Overground line name
] # Adjust these names based on the actual keys in line_edges.json

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

def load_line_edges(file_path):
    """
    Load the line edges data (adjacent station pairs) from a JSON file.
    This file should contain a dictionary where keys are line IDs
    and values are lists of station pairs for that line.

    Args:
        file_path (str): Path to the line edges JSON file.

    Returns:
        dict: The loaded line edges data, or an empty dict if the file
              is not found or is invalid.
    """
    # Check if the specified file exists
    if not os.path.exists(file_path):
        print(f"Error: Line edges file {file_path} not found.")
        return {} # Return empty dict if file doesn't exist

    try:
        # Open the file for reading with UTF-8 encoding
        with open(file_path, 'r', encoding='utf-8') as file:
            # Load the JSON data from the file
            data = json.load(file)
            # Check if the loaded data is a dictionary (expected format)
            if isinstance(data, dict):
                return data
            else:
                # If not a dictionary, print a warning and return empty
                print(f"Warning: Data in {file_path} is not a dictionary. Cannot process lines.")
                return {}
    except json.JSONDecodeError as e:
        # Handle errors if the file contains invalid JSON
        print(f"Error decoding JSON from {file_path}: {e}. Cannot process lines.")
        return {}
    except Exception as e:
        # Handle any other unexpected errors during file loading
        print(f"An unexpected error occurred loading {file_path}: {e}. Cannot process lines.")
        return {}

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

# Removed process_line_edges function as the logic is integrated into main loop

def main():
    """
    Main function to:
    1. Load line definitions (adjacent stations).
    2. Load existing calculated edge weights (if any).
    3. Iterate through specified lines (Overground, Elizabeth).
    4. For each line, iterate through adjacent station pairs.
    5. Skip pairs already present in the loaded weights.
    6. Call TfL API to get (and average) journey time for new pairs.
    7. Construct edge dictionaries in the target format.
    8. Append new edges to the list.
    9. Save the complete list of edges to the output file.
    """
    # Construct the full paths to input and output files based on script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    line_edges_file_path = os.path.join(script_dir, LINE_EDGES_FILE)
    output_file_path = os.path.join(script_dir, OUTPUT_FILE)

    # --- Load Input Data ---
    # Load the definitions of adjacent stations for all lines
    print(f"Loading line edges from {line_edges_file_path}...")
    all_line_edges = load_line_edges(line_edges_file_path)

    # Check if line edges were loaded successfully
    if not all_line_edges:
        print("Failed to load line edges. Cannot proceed. Ensure line_edges.json exists and is valid.")
        return # Exit if we don't have the input station pairs

    # Load the edges that have already been calculated and saved previously
    print(f"Loading existing calculated edges from {output_file_path}...")
    all_calculated_edges = load_existing_edges(output_file_path)
    print(f"Loaded {len(all_calculated_edges)} existing calculated edges.")

    # Create a set of keys for quick lookup of existing edges to avoid duplicates.
    # The key combines source name, target name, and line ID.
    existing_edge_keys = set()
    for edge in all_calculated_edges:
        # Ensure the existing edge has the necessary keys to create a unique identifier
        if all(k in edge for k in ('source', 'target', 'line')):
            key = f"{edge['source']}|{edge['target']}|{edge['line']}"
            existing_edge_keys.add(key)
        else:
            # Warn if an existing edge is missing key information
            print(f"Warning: Skipping existing edge due to missing keys: {edge.get('source','?')}|{edge.get('target','?')}|{edge.get('line','?')}")
    # --- End Load Input Data ---

    # Counter for newly added edges during this run
    added_count = 0
    # Counter for total pairs processed in this run
    processed_count = 0
    # List to keep track of edges that failed API calls
    failed_edges = []

    # --- Process Each Target Line ---
    print(f"Processing lines: {', '.join(LINES_TO_PROCESS)}")
    for line_id in LINES_TO_PROCESS:
        # Check if the current line_id exists in the loaded line_edges data
        if line_id not in all_line_edges:
            print(f"Warning: Line '{line_id}' not found in {LINE_EDGES_FILE}. Skipping.")
            continue # Move to the next line in LINES_TO_PROCESS

        # Get the list of adjacent station pairs (edges) for the current line
        edges_to_process = all_line_edges[line_id]
        print(f"Processing {len(edges_to_process)} station pairs for line: {line_id}...")

        # Iterate through each station pair (edge) for the current line
        for i, edge_info in enumerate(edges_to_process):
            processed_count += 1 # Count each pair from line_edges.json once
            # Extract necessary information for the API call and output edge
            # Using .get() provides default None if a key is missing, preventing KeyErrors
            source_name = edge_info.get('source_name')
            target_name = edge_info.get('target_name')
            source_id = edge_info.get('source_id')   # Naptan ID
            target_id = edge_info.get('target_id')   # Naptan ID
            mode = edge_info.get('mode')             # e.g., 'overground', 'elizabeth-line'
            # Use the line_id from the outer loop as the definitive line ID
            line_name = edge_info.get('line_name')   # Full line name, e.g., "Elizabeth line"

            # Validate that we have the minimum required info for this pair
            # Need names and IDs for both ends, mode, and the line_id
            if not all([source_name, target_name, source_id, target_id, mode, line_id]):
                print(f"  [{i+1}/{len(edges_to_process)}] Warning: Skipping pair due to missing data: {edge_info}")
                continue # Skip this pair if essential info is missing

            # --- Process Forward Direction: source -> target ---
            forward_key = f"{source_name}|{target_name}|{line_id}"
            print(f"[{i+1}/{len(edges_to_process)}] Checking Forward: {source_name} -> {target_name} on {line_id}")

            # Check if this forward edge has already been calculated and saved
            if forward_key in existing_edge_keys:
                print(f"  Forward edge already exists. Skipping API call.")
            else:
                # --- Forward edge does not exist, proceed with API call ---
                duration = get_and_average_journey_time(source_id, target_id, mode, line_id)
                # Pause execution briefly to avoid overwhelming the API
                print(f"  Waiting {API_DELAY_SECONDS} second(s)...")
                time.sleep(API_DELAY_SECONDS)

                if duration is not None:
                    new_edge = {
                        "source": source_name, "target": target_name, "line": line_id,
                        "line_name": line_name or "", "mode": mode, "duration": duration,
                        "weight": duration, "transfer": False,
                        "calculated_timestamp": datetime.now().isoformat()
                    }
                    all_calculated_edges.append(new_edge)
                    existing_edge_keys.add(forward_key)
                    added_count += 1
                    print(f"  Successfully calculated and added forward edge. Duration: {duration:.1f} mins.")
                else:
                    print(f"  Failed to get journey time for forward edge {source_name} -> {target_name}. Edge not added.")
                    # Record the failure
                    failed_edges.append(f"FORWARD: {source_name} -> {target_name} on {line_id}")

            # --- Process Reverse Direction: target -> source ---
            # Use the same mode and line_id, but swap source/target names and IDs
            reverse_key = f"{target_name}|{source_name}|{line_id}"
            print(f"[{i+1}/{len(edges_to_process)}] Checking Reverse: {target_name} -> {source_name} on {line_id}")

            # Check if this reverse edge has already been calculated and saved
            if reverse_key in existing_edge_keys:
                print(f"  Reverse edge already exists. Skipping API call.")
            else:
                 # --- Reverse edge does not exist, proceed with API call ---
                 # Note: Swapped target_id and source_id in the function call
                duration = get_and_average_journey_time(target_id, source_id, mode, line_id)
                 # Pause execution briefly to avoid overwhelming the API
                print(f"  Waiting {API_DELAY_SECONDS} second(s)...")
                time.sleep(API_DELAY_SECONDS)

                if duration is not None:
                    # Construct the reverse edge dictionary (swap source/target names)
                    new_edge = {
                        "source": target_name, "target": source_name, "line": line_id,
                        "line_name": line_name or "", "mode": mode, "duration": duration,
                        "weight": duration, "transfer": False,
                        "calculated_timestamp": datetime.now().isoformat()
                    }
                    all_calculated_edges.append(new_edge)
                    existing_edge_keys.add(reverse_key)
                    added_count += 1
                    print(f"  Successfully calculated and added reverse edge. Duration: {duration:.1f} mins.")
                else:
                    print(f"  Failed to get journey time for reverse edge {target_name} -> {source_name}. Edge not added.")
                    # Record the failure
                    failed_edges.append(f"REVERSE: {target_name} -> {source_name} on {line_id}")

        # --- End loop for station pairs in the current line ---
    # --- End loop for lines ---

    # --- Save Results ---
    # Check if any new edges were added during this run
    if added_count > 0:
        print(f"Processed {processed_count} total pairs across specified lines.")
        print(f"Added {added_count} new edges. Saving updated list to {output_file_path}...")
        # Save the potentially updated list of all edges back to the file
        save_edges(all_calculated_edges, output_file_path)
    else:
        # No new edges were added, the output file remains unchanged
        print(f"Processed {processed_count} total pairs across specified lines.")
        print("No new edges were added. Output file remains unchanged.")

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