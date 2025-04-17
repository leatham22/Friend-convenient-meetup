import requests
import json
from dotenv import load_dotenv
import os
from collections import defaultdict
import time

# Load environment variables from .env file
# This is a secure way to handle API keys without hardcoding them
load_dotenv()

# Constants for API interaction
# Using constants at the top makes it easier to modify values in one place
TFL_BASE_URL = "https://api.tfl.gov.uk"
# List of all tube lines - needed because tube stations must be fetched line by line
TUBE_LINES = [
    'bakerloo', 'central', 'circle', 'district', 'hammersmith-city',
    'jubilee', 'metropolitan', 'northern', 'piccadilly', 'victoria', 'waterloo-city'
]
# List of all overground lines - each line must be fetched separately
# These are the traditional line codes used by TfL
OVERGROUND_LINES = [
    'mildmay',      # Richmond/Clapham Junction to Stratford
    'windrush',     # Highbury & Islington to New Cross/Clapham Junction/Crystal Palace/West Croydon
    'lioness',      # Watford Junction to Euston
    'weaver',       # Liverpool Street to Enfield Town/Cheshunt/Chingford
    'suffragette',  # Gospel Oak to Barking Riverside
    'liberty'       # Romford to Upminster
]

def make_api_request(url, params, max_retries=3, timeout=30):
    """
    Makes an API request with retry logic for reliability.
    
    Why retry logic?
    - Network requests can fail temporarily
    - Retrying with exponential backoff (increasing delays) is a best practice
    - Helps handle temporary API issues or rate limits
    
    Parameters:
    - url: The API endpoint to call
    - params: Dictionary of query parameters (like API key)
    - max_retries: Number of attempts before giving up
    - timeout: How long to wait for each request
    
    Returns:
    - JSON response if successful, None if all retries fail
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()  # Raises an error for bad status codes
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                # Exponential backoff: 5s, 10s, 15s between retries
                sleep_time = (attempt + 1) * 5
                print(f"Waiting {sleep_time} seconds before retrying...")
                time.sleep(sleep_time)
    return None

def get_tfl_stations(mode):
    """
    Fetches stations from TfL API for a specific transport mode.
    
    Different handling for different modes:
    - Tube: Fetched line by line for complete data
    - Overground: Uses single line ID as TfL API hasn't updated to new line names yet
    - DLR and Elizabeth Line: Uses Line endpoint as they're single-line systems
    
    Parameters:
    - mode: Transport mode to load ('tube', 'dlr', 'overground', 'elizabeth-line')
    
    Returns:
    - Set of station names in lowercase (for easier comparison)
    """
    api_key = os.getenv('TFL_API_KEY')
    if not api_key:
        raise ValueError("TFL_API_KEY not found in environment variables")

    stations = set()
    
    if mode == 'tube':
        # Tube stations must be fetched line by line
        for line in TUBE_LINES:
            url = f"{TFL_BASE_URL}/Line/{line}/StopPoints"
            data = make_api_request(url, params={'app_key': api_key})
            if data:
                for station in data:
                    stations.add(station.get('commonName', '').lower())
                    for other_name in station.get('additionalProperties', []):
                        if other_name.get('key') == 'AlternateName':
                            stations.add(other_name.get('value', '').lower())
    elif mode == 'overground':
        # Fetch overground stations line by line to avoid duplicates
        for line in OVERGROUND_LINES:
            url = f"{TFL_BASE_URL}/Line/{line}/StopPoints"
            data = make_api_request(url, params={'app_key': api_key})
            if data:
                for station in data:
                    stations.add(station.get('commonName', '').lower())
                    for other_name in station.get('additionalProperties', []):
                        if other_name.get('key') == 'AlternateName':
                            stations.add(other_name.get('value', '').lower())
    else:
        # DLR and Elizabeth Line use Line endpoint as they're single-line systems
        mode_mapping = {
            'dlr': 'dlr',
            'elizabeth-line': 'elizabeth'
        }
        line = mode_mapping.get(mode)
        if line:
            url = f"{TFL_BASE_URL}/Line/{line}/StopPoints"
            data = make_api_request(url, params={'app_key': api_key})
            if data:
                for station in data:
                    stations.add(station.get('commonName', '').lower())
                    for other_name in station.get('additionalProperties', []):
                        if other_name.get('key') == 'AlternateName':
                            stations.add(other_name.get('value', '').lower())
    
    return stations

def load_our_stations(mode):
    """
    Loads our processed station list from JSON files.
    
    We use lowercase for all comparisons because:
    - Station names might have inconsistent capitalization
    - Case-insensitive comparison is more reliable
    - Prevents missing matches due to case differences
    
    Parameters:
    - mode: Transport mode to load ('tube', 'dlr', 'overground', 'elizabeth-line')
    
    Returns:
    - Set of station names in lowercase
    """
    filename = f'unique_stations_{mode}.json'
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            return {station['name'].lower() for station in data}
    except FileNotFoundError:
        print(f"Warning: {filename} not found")
        return set()

def compare_stations():
    """
    Compares our station lists with official TfL data.
    
    Uses set operations for efficient comparison:
    - A - B: Elements in A that aren't in B (extra stations)
    - B - A: Elements in B that aren't in A (missing stations)
    - Empty intersection means perfect match
    
    The comparison helps identify:
    - Missing stations we should include
    - Extra stations we shouldn't have
    - Potential naming mismatches
    """
    modes = ['tube', 'dlr', 'overground', 'elizabeth-line']
    
    for mode in modes:
        print(f"\nAnalyzing {mode.upper()} stations:")
        print("-" * 50)
        
        our_stations = load_our_stations(mode)
        tfl_stations = get_tfl_stations(mode)
        
        print(f"Our stations count: {len(our_stations)}")
        print(f"TfL stations count: {len(tfl_stations)}")
        
        # Set operations for finding differences
        missing = tfl_stations - our_stations  # Stations we're missing
        extra = our_stations - tfl_stations    # Stations we shouldn't have
        
        if missing:
            print(f"\nMissing stations ({len(missing)}):")
            for station in sorted(missing):
                print(f"- {station}")
        
        if extra:
            print(f"\nExtra stations ({len(extra)}):")
            for station in sorted(extra):
                print(f"- {station}")
        
        if not missing and not extra:
            print("\nPerfect match! All stations accounted for.")

if __name__ == "__main__":
    compare_stations() 