#!/usr/bin/env python3
"""
Get Timetable Data

This script uses the TfL API (Line/Timetable endpoint) to fetch timetable 
information for Tube and DLR lines using their terminal stations as starting points.
The fetched data is cached locally in JSON files, one per line.

Usage:
    python3 get_timetable_data.py [--line <line_id>]

Arguments:
    --line (optional): Process only a specific line ID (e.g., district).
                       If omitted, all lines in terminal_stations.json will be processed.

Output:
    Creates JSON files in graph_data/timetable_cache/ containing the raw 
    timetable data fetched from the API for each processed line.
"""

import json
import os
import requests
import time
import argparse
from requests.exceptions import RequestException
from dotenv import load_dotenv # Import the function

# --- Configuration ---
# Load environment variables from .env file first
load_dotenv()

# API configuration
API_BASE_URL = "https://api.tfl.gov.uk/Line"
CACHE_DIR = "../graph_data/timetable_cache"

# Try to get TfL API key from environment variables *after* loading .env
TFL_API_KEY = os.environ.get("TFL_API_KEY")
# TFL_APP_ID = os.environ.get("TFL_APP_ID", "") # Removed unnecessary App ID

API_PARAMS = {}
if TFL_API_KEY:
    API_PARAMS["app_key"] = TFL_API_KEY
# if TFL_APP_ID: # Removed unnecessary App ID check
#     API_PARAMS["app_id"] = TFL_APP_ID
# --- End Configuration ---

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
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {file_path}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred loading {file_path}: {e}")
        return None

def fetch_timetable(line_id, from_stop_id):
    """
    Fetches timetable data for a given line and starting station ID.
    
    Args:
        line_id (str): The ID of the line (e.g., 'district').
        from_stop_id (str): The Naptan ID of the starting terminal station.
        
    Returns:
        dict: The API response JSON data, or None if the request fails.
    """
    api_url = f"{API_BASE_URL}/{line_id}/Timetable/{from_stop_id}"
    print(f"  Fetching: {line_id} from {from_stop_id}...")
    
    try:
        response = requests.get(api_url, params=API_PARAMS)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        print(f"    Status: {response.status_code}")
        return response.json()
    except RequestException as e:
        print(f"    Error fetching timetable for {line_id} from {from_stop_id}: {e}")
        # Specifically check for 404 Not Found, as some terminals might not work with the API
        if response is not None and response.status_code == 404:
            print(f"    Warning: Station {from_stop_id} might not be a valid timetable start point for line {line_id}.")
        return None
    except Exception as e:
        print(f"    An unexpected error occurred during API call: {e}")
        return None

def fetch_point_to_point_timetable(line_id, from_stop_id, to_stop_id):
    """
    Fetches timetable data between two specific stop points on a line.
    Uses the /Line/{id}/Timetable/{fromStopPointId}/to/{toStopPointId} endpoint.

    Args:
        line_id (str): The ID of the line.
        from_stop_id (str): The Naptan ID of the starting station.
        to_stop_id (str): The Naptan ID of the destination station.

    Returns:
        dict: The API response JSON data, or None if the request fails.
    """
    api_url = f"{API_BASE_URL}/{line_id}/Timetable/{from_stop_id}/to/{to_stop_id}"
    print(f"  Fetching point-to-point: {line_id} from {from_stop_id} to {to_stop_id}...")

    try:
        response = requests.get(api_url, params=API_PARAMS)
        response.raise_for_status() # Raise an exception for bad status codes
        print(f"    Status: {response.status_code}")
        return response.json()
    except RequestException as e:
        print(f"    Error fetching point-to-point timetable for {line_id} ({from_stop_id} -> {to_stop_id}): {e}")
        # Check for 404 specifically
        if response is not None and response.status_code == 404:
            print(f"    Warning: No direct timetable found between {from_stop_id} and {to_stop_id} on line {line_id}.")
        return None
    except Exception as e:
        print(f"    An unexpected error occurred during point-to-point API call: {e}")
        return None

def save_to_cache(data, file_path):
    """
    Saves data to a JSON file in the cache directory.
    
    Args:
        data (dict): The data to save.
        file_path (str): The full path to the cache file.
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"    Successfully cached data to {os.path.basename(file_path)}")
    except IOError as e:
        print(f"    Error saving cache file {file_path}: {e}")
    except Exception as e:
        print(f"    An unexpected error occurred while saving cache: {e}")

def main():
    """Main function to fetch and cache timetable data."""
    parser = argparse.ArgumentParser(description="Fetch TfL timetable data for specified lines.")
    parser.add_argument("--line", help="Specific line ID to process (e.g., district). Processes all if omitted.")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    terminals_file = os.path.join(script_dir, '../graph_data/terminal_stations.json')
    cache_base_dir = os.path.join(script_dir, CACHE_DIR)

    print("Loading terminal stations...")
    terminal_stations = load_json_data(terminals_file, "Terminal stations")
    if terminal_stations is None:
        print("Exiting due to error loading terminal stations.")
        return

    lines_to_process = {}
    if args.line:
        # Process only the specified line
        if args.line in terminal_stations:
            lines_to_process[args.line] = terminal_stations[args.line]
            print(f"Processing specified line: {args.line}")
        else:
            print(f"Error: Specified line '{args.line}' not found in {terminals_file}. Available: {list(terminal_stations.keys())}")
            return
    else:
        # Process all lines found in the terminals file
        lines_to_process = terminal_stations
        print(f"Processing all {len(lines_to_process)} lines found in {terminals_file}.")

    # Check for API credentials *after* attempting to load from .env
    if not API_PARAMS:
        print("\nWarning: TfL API credentials (TFL_API_KEY) not found in environment variables or .env file.")
        print("API calls may be rate-limited or fail.")
    else:
        print("\nAPI Key found. Proceeding with authenticated calls.") # Added confirmation message

    # Process each line
    for line_id, terminals in lines_to_process.items():
        print(f"\nProcessing line: {line_id} (Terminals: {terminals})")
        line_cache_data = {
            "line_id": line_id,
            "fetch_timestamp": time.time(),
            "timetables": {}
        }
        
        if not terminals:
            print(f"  Skipping line {line_id} as no terminals were identified.")
            continue

        # Fetch timetable for each terminal on the line
        for terminal_id in terminals:
            # Fetch data from API
            timetable_data = fetch_timetable(line_id, terminal_id)
            
            # Add fetched data to our line cache structure if successful
            if timetable_data:
                line_cache_data["timetables"][terminal_id] = timetable_data
            else:
                 print(f"    No data fetched for terminal {terminal_id}. It might be stored as null in the cache.")
                 # Store null or an error marker if needed, or just skip
                 line_cache_data["timetables"][terminal_id] = None # Indicate fetch attempt failed
            
            # Delay between API calls to respect usage limits
            time.sleep(1) 

        # --- Add specific point-to-point fetches for known problematic segments ---            
        point_to_point_fetches = []
        if line_id == 'dlr':
            point_to_point_fetches.append(('940GZZDLSTD', '940GZZDLCAN'))
        elif line_id == 'district':
            point_to_point_fetches.append(('940GZZLUECT', '940GZZLUKOY'))
        elif line_id == 'central':
            point_to_point_fetches.append(('940GZZLUGGH', '940GZZLUHLT'))
        
        if point_to_point_fetches:
            print(f"\n  Performing additional point-to-point fetches for line: {line_id}")
            for from_id, to_id in point_to_point_fetches:
                p2p_timetable_data = fetch_point_to_point_timetable(line_id, from_id, to_id)
                # Add the data under a specific key like 'FROM_to_TO'
                cache_key = f"{from_id}_to_{to_id}"
                if p2p_timetable_data:
                    line_cache_data["timetables"][cache_key] = p2p_timetable_data
                    print(f"    Added point-to-point data for {cache_key}")
                else:
                    line_cache_data["timetables"][cache_key] = None # Indicate failed fetch
                    print(f"    No data fetched for point-to-point {cache_key}. Storing null.")
                time.sleep(1) # Delay between API calls
        # --- End point-to-point fetches ---    
            
        # Save the collected data (including terminal and point-to-point) for this line
        cache_file_path = os.path.join(cache_base_dir, f"{line_id}.json")
        save_to_cache(line_cache_data, cache_file_path)

    print("\nFinished processing all requested lines.")

if __name__ == "__main__":
    main() 