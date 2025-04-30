"""
This script calculates the walking duration for transfer edges between hubs using the TFL Journey Planner API.
It then updates the graph with the calculated weights.
"""

import networkx as nx
import requests
import json
import os
import logging
import time
import math
from dotenv import load_dotenv # Added dotenv

# --- Configuration ---
load_dotenv() # Load environment variables
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Input files from the previous script
INPUT_GRAPH_FILE = 'networkx_graph/graph_data/networkx_graph_hubs_with_transfers.json'
INPUT_TRANSFER_LIST_FILE = 'networkx_graph/graph_data/inter_hub_transfers_to_weight.json'
# Final output graph file
OUTPUT_GRAPH_FILE = 'networkx_graph/graph_data/networkx_graph_hubs_final.json'

# Ensure the output directory exists
os.makedirs(os.path.dirname(OUTPUT_GRAPH_FILE), exist_ok=True)

# TFL API endpoint for Journey Planner
TFL_API_JOURNEY_URL = "https://api.tfl.gov.uk/Journey/JourneyResults/{from_id}/to/{to_id}"

# API Key (Retrieved from environment variable)
# IMPORTANT: Set the TFL_API_KEY environment variable before running this script.
# Example: export TFL_API_KEY='YOUR_ACTUAL_API_KEY'
TFL_API_KEY = os.environ.get('TFL_API_KEY')
if not TFL_API_KEY:
    logging.error("TFL_API_KEY environment variable not set. Cannot query Journey API.")
    # Exit if API key is absolutely required and no fallback is desired
    exit(1)

# API Request handling
API_RETRY_DELAY = 10 # Increased delay for Journey Planner (potentially stricter limits)
API_MAX_RETRIES = 4 # Allow more retries
REQUEST_TIMEOUT = 30 # Timeout for API requests in seconds
FETCH_DELAY = 0.3 # Small delay between API calls

# --- Helper Functions ---

def load_graph(filepath):
    """
    Loads a NetworkX graph from a JSON file (node-link format).
    Explicitly uses link="edges" to look for edges under the 'edges' key.
    """
    try:
        with open(filepath, 'r') as f:
            graph_data = json.load(f)
        # Create a graph from node-link data, specifying link="edges"
        # The standard keys ('id', 'source', 'target', 'key') are usually inferred correctly,
        # but specify link='edges' because we saved with that key.
        G = nx.node_link_graph(graph_data, directed=True, multigraph=True, link='edges')
        logging.info(f"Successfully loaded graph from {filepath}")
        return G
    except FileNotFoundError:
        logging.error(f"Error: Input graph file not found at {filepath}")
        exit(1)
    except json.JSONDecodeError:
        logging.error(f"Error: Could not decode JSON from {filepath}")
        exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred while loading the graph: {e}")
        exit(1)

def load_transfer_list(filepath):
    """
    Loads the list of hub pairs needing transfer weighting from a JSON file.
    """
    try:
        with open(filepath, 'r') as f:
            transfer_list = json.load(f)
        logging.info(f"Successfully loaded transfer list from {filepath}")
        # Ensure elements are tuples if loaded from JSON lists
        return [tuple(pair) for pair in transfer_list]
    except FileNotFoundError:
        logging.error(f"Error: Input transfer list file not found at {filepath}")
        exit(1)
    except json.JSONDecodeError:
        logging.error(f"Error: Could not decode JSON from {filepath}")
        exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred while loading the transfer list: {e}")
        exit(1)

def save_graph(graph, filepath):
    """
    Saves the NetworkX graph to a JSON file in node-link format.
    Uses edges="edges" for forward compatibility with NetworkX.
    """
    try:
        # Convert the graph data to node-link format, specifying edges="edges"
        graph_data = nx.node_link_data(graph, edges="edges")
        # Write the graph data to the specified file path
        with open(filepath, 'w') as f:
            # Use null instead of NaN for missing weights
            json.dump(graph_data, f, indent=4, allow_nan=False)
        logging.info(f"Graph successfully saved to {filepath} in node-link format (using 'edges' key).")
    except Exception as e:
        # Log any errors during the file saving process
        logging.error(f"Error saving graph to {filepath}: {e}")

def get_walking_duration(from_id, to_id):
    """
    Uses the TFL Journey Planner API to find the walking duration between two Naptan IDs.
    Includes retry logic. Returns duration in minutes or None on failure.
    """
    if not TFL_API_KEY:
        # This case is now handled by the initial check, but added as safeguard
        logging.error("TFL_API_KEY is required for TFL Journey API calls.")
        return None

    # Construct the API URL
    api_url = TFL_API_JOURNEY_URL.format(from_id=from_id, to_id=to_id)
    # Specify parameters: walking mode only, and add API key
    params = {
        'mode': 'walking',
        'app_key': TFL_API_KEY
    }
    retries = 0
    while retries < API_MAX_RETRIES:
        try:
            # Make the API request with a timeout
            response = requests.get(api_url, params=params, timeout=REQUEST_TIMEOUT)
            # Check for HTTP errors (4xx, 5xx)
            response.raise_for_status()
            # Parse the JSON response
            data = response.json()

            # Extract duration from the first itinerary
            if data.get('journeys') and len(data['journeys']) > 0:
                duration = data['journeys'][0].get('duration')
                if duration is not None:
                    logging.debug(f"API success: Found walking duration {duration} mins for {from_id} -> {to_id}")
                    return duration # Return the found duration
                else:
                    logging.warning(f"API success but no duration found in journey for {from_id} -> {to_id}. Response: {data}")
            else:
                 logging.warning(f"API success but no journeys found for {from_id} -> {to_id}. Response: {data}")

            # If data was received but duration/journey wasn't found as expected
            return None # Return None as we couldn't extract the value

        except requests.exceptions.HTTPError as e:
            logging.warning(f"HTTP Error fetching walking duration for {from_id} -> {to_id}: {e}. Status: {e.response.status_code}")
            if e.response.status_code == 429:
                 logging.warning(f"Rate limit hit. Retrying in {API_RETRY_DELAY * (retries + 1)} seconds...")
                 time.sleep(API_RETRY_DELAY * (retries + 1)) # Exponential backoff for rate limits
            elif e.response.status_code == 400:
                 logging.error(f"Bad Request (400) for {from_id} -> {to_id}. Check Naptan IDs. API URL: {response.request.url}")
                 return None # Don't retry bad requests, return None
            else:
                 logging.warning(f"Retrying in {API_RETRY_DELAY} seconds...")
                 time.sleep(API_RETRY_DELAY)

        except requests.exceptions.Timeout:
            logging.warning(f"Timeout fetching walking duration for {from_id} -> {to_id}. Retrying in {API_RETRY_DELAY} seconds...")
            time.sleep(API_RETRY_DELAY)
        except requests.exceptions.RequestException as e:
            logging.warning(f"Network error fetching walking duration for {from_id} -> {to_id}: {e}. Retrying in {API_RETRY_DELAY} seconds...")
            time.sleep(API_RETRY_DELAY)
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON response from TFL Journey API for {from_id} -> {to_id}. Skipping.")
            return None # Don't retry decoding errors, return None

        # Increment retry counter
        retries += 1

    # If all retries fail
    logging.error(f"Failed to get walking duration for {from_id} -> {to_id} after {API_MAX_RETRIES} retries. Setting weight to None.")
    return None # Return None if all retries failed

# --- Main Logic ---

def calculate_transfer_weights():
    """
    Calculates walking durations for transfer edges using TFL Journey API and updates the graph.
    Sets weight to None if duration cannot be fetched.
    """
    logging.info("Starting the transfer weight calculation process...")

    # 1. Load Graph and Transfer List
    G = load_graph(INPUT_GRAPH_FILE)
    transfers_to_weight = load_transfer_list(INPUT_TRANSFER_LIST_FILE)
    if not G or not transfers_to_weight:
        logging.error("Missing graph or transfer list. Aborting.")
        return

    # 2. Create Mapping
    primary_id_to_hub_node = {data['primary_naptan_id']: node for node, data in G.nodes(data=True)}

    logging.info(f"Calculating walking weights for {len(transfers_to_weight)} transfer pairs...")
    # 3. Iterate Through Transfers and Get Weights
    processed_count = 0
    api_failures = 0
    for id1, id2 in transfers_to_weight:
        processed_count += 1
        logging.info(f"Processing pair {processed_count}/{len(transfers_to_weight)}: {id1} <-> {id2}")

        # Find the corresponding hub node names in the graph using primary IDs
        h1_name = primary_id_to_hub_node.get(id1)
        h2_name = primary_id_to_hub_node.get(id2)

        if not h1_name or not h2_name:
            logging.warning(f"Could not find nodes for primary IDs {id1} or {id2} in the graph. Skipping pair.")
            continue

        # Get the node data for each hub
        try:
            h1_data = G.nodes[h1_name]
            h2_data = G.nodes[h2_name]
        except KeyError:
            logging.warning(f"Node data not found for {h1_name} or {h2_name} despite being in primary_id mapping. Skipping pair.")
            continue

        # Retrieve the list of Naptan IDs associated with each hub
        h1_naptan_ids = h1_data.get('constituent_naptan_ids')
        h2_naptan_ids = h2_data.get('constituent_naptan_ids')

        # Check if Naptan ID lists exist and are not empty
        if not h1_naptan_ids or not h2_naptan_ids:
            logging.warning(f"Naptan ID list missing or empty for hub {h1_name} or {h2_name}. Skipping pair.")
            continue

        # Select the first Naptan ID from each list to use for the API call
        # This assumes the first Naptan ID is a valid representative for the hub location
        naptan_id_for_api_1 = h1_naptan_ids[0]
        naptan_id_for_api_2 = h2_naptan_ids[0]

        logging.debug(f"Using Naptan IDs {naptan_id_for_api_1} (for {h1_name}) and {naptan_id_for_api_2} (for {h2_name}) for API call.")

        # Get walking duration from TFL API using the selected representative Naptan IDs
        time.sleep(FETCH_DELAY) # Small delay before each API call
        duration = get_walking_duration(naptan_id_for_api_1, naptan_id_for_api_2)

        # Log the hub names and the obtained duration
        logging.info(f"API result for {h1_name} <-> {h2_name}: Duration = {duration} minutes")

        if duration is None:
            api_failures += 1
            # Log using the hub names for clarity in logs
            logging.warning(f"Setting weight to None for transfer {h1_name} <-> {h2_name} (API query used {naptan_id_for_api_1} <-> {naptan_id_for_api_2})")
        # If duration is 0, treat it as a very small positive value for pathfinding (e.g., 0.1)
        # or keep as 0 if direct connection is implied? Let's keep as None for now if API fails,
        # but maybe set to a small epsilon if API returns 0?
        # Decision: keep duration as returned by API (could be 0), or None if API fails.

        # 4. Update Edge Weights in the Graph (set to None if duration is None)
        try:
            # Update the weight for the H1 -> H2 transfer edge (key='transfer')
            if G.has_edge(h1_name, h2_name, key='transfer'):
                G.edges[h1_name, h2_name, 'transfer']['weight'] = duration # Assign duration (can be int or None)
                logging.debug(f"Updated weight for {h1_name} -> {h2_name} [transfer] to {duration}")
            else:
                logging.warning(f"Transfer edge {h1_name} -> {h2_name} [key='transfer'] not found in graph.")

            # Update the weight for the H2 -> H1 transfer edge (key='transfer')
            if G.has_edge(h2_name, h1_name, key='transfer'):
                G.edges[h2_name, h1_name, 'transfer']['weight'] = duration # Assign duration (can be int or None)
                logging.debug(f"Updated weight for {h2_name} -> {h1_name} [transfer] to {duration}")
            else:
                logging.warning(f"Transfer edge {h2_name} -> {h1_name} [key='transfer'] not found in graph.")

        except KeyError as e:
             logging.error(f"Error updating edge weight for {h1_name} <-> {h2_name}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error updating edge weight for {h1_name} <-> {h2_name}: {e}")

    logging.info(f"Finished calculating transfer weights. {api_failures} pairs failed API lookup and were assigned None weight.")

    # 5. Save the Final Graph
    save_graph(G, OUTPUT_GRAPH_FILE)

    logging.info("Transfer weight calculation process completed.")

# --- Script Execution ---
if __name__ == "__main__":
    # Initial check for API key moved to top
    if not TFL_API_KEY:
        # Message already logged, exit handled at top if needed
        pass # Allow execution if exit(1) is commented out at the top

    # Run the main function
    calculate_transfer_weights() 