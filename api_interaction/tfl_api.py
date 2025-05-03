import os
import sys
import requests
import json
from dotenv import load_dotenv

# Base URL for the TfL API (only for journey planning)
TFL_API_BASE_URL = "https://api.tfl.gov.uk/Journey/JourneyResults/"

def get_api_key():
    """
    Retrieves the TfL API key from environment variable or command line.
    """
    load_dotenv()
    api_key = os.environ.get('TFL_API_KEY')
    if api_key:
        print("Using TfL API key from environment variable.")
        return api_key
    return None

def determine_api_naptan_id(station_attributes):
    """
    Determines the appropriate Naptan ID for TfL API calls based on station attributes.

    Args:
        station_attributes (dict): Dictionary of station attributes.

    Returns:
        str or None: The Naptan ID to use, or None if not determinable.
    """
    target_api_id = None
    target_primary_id = station_attributes.get('primary_naptan_id')
    target_constituents = station_attributes.get('constituent_stations', [])

    if target_primary_id and not target_primary_id.startswith("HUB"):
        target_api_id = target_primary_id
    elif target_constituents and isinstance(target_constituents, list) and len(target_constituents) > 0 and isinstance(target_constituents[0], dict) and 'naptan_id' in target_constituents[0]:
        # Check list not empty, first item is dict, key exists
        target_api_id = target_constituents[0].get('naptan_id')
    
    # Fallback if no specific ID is found (should be rare)
    if not target_api_id:
        hub_name = station_attributes.get('hub_name', station_attributes.get('id'))
        # Check if hub_name itself might be a Naptan ID (heuristic: not HUB prefix)
        if hub_name and not hub_name.startswith("HUB") and "HUB" not in hub_name: # Basic check
             print(f"Warning: Falling back to using hub name '{hub_name}' as Naptan ID for API call.")
             target_api_id = hub_name
        
    return target_api_id

def get_travel_time(start_naptan_id, end_naptan_id, api_key):
    """
    Calls the TfL Journey Planner API to get the travel time between two stations using Naptan IDs.

    Args:
        start_naptan_id (str): Naptan ID of the starting station.
        end_naptan_id (str): Naptan ID of the ending station.
        api_key (str): The TfL API key.

    Returns:
        int: Travel time in minutes, or None if the journey cannot be found.
    """
    # Check if start and end IDs are the same
    if start_naptan_id == end_naptan_id:
        print("  Start and end stations are the same (by Naptan ID) - no journey needed")
        return 0

    # Validate Naptan IDs are present
    if not start_naptan_id or not end_naptan_id:
        print(f"  Error: Missing Naptan ID for TfL API call (Start: {start_naptan_id}, End: {end_naptan_id})")
        return None

    # Construct the URL using Naptan IDs
    url = f"{TFL_API_BASE_URL}{start_naptan_id}/to/{end_naptan_id}"

    params = {
        'app_key': api_key,
        'timeIs': 'Departing',
        'journeyPreference': 'leasttime'
    }

    try:
        print(f"  Querying TfL API for journey ({start_naptan_id} -> {end_naptan_id})...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
        journey_data = response.json()

        # Check if the 'journeys' key exists and is not empty
        if not journey_data.get('journeys'):
            # Provide more context in the warning
            print(f"  Warning: No journey found between {start_naptan_id} and {end_naptan_id}.")
            return None

        # Safely access the duration from the first journey
        duration = journey_data['journeys'][0].get('duration')
        if duration is not None:
            print(f"  Found journey duration: {duration} minutes")
        else:
            # Handle case where journey exists but duration is missing
            print(f"  Warning: Journey found between {start_naptan_id} and {end_naptan_id}, but duration is missing.")
        return duration

    except requests.exceptions.RequestException as e:
        # Handle potential network errors, timeouts, etc.
        error_message = f"Error during TfL API request: {e}"
        # Attempt to include TfL error message if response was received
        try:
            if response:
                error_details = response.json()
                if 'message' in error_details:
                    error_message += f" - TfL Message: {error_details['message']}"
        except Exception:
             pass # Ignore if response isn't available or not JSON
        print(f"  {error_message}", file=sys.stderr)
        return None
    except Exception as e:
        # Catch any other unexpected errors (e.g., JSON decoding issues if raise_for_status didn't catch)
        print(f"  An unexpected error occurred processing TfL response: {e}", file=sys.stderr)
        return None 