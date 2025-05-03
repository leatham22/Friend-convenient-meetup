"""
This script adds potential walking transfer edges between nearby distinct hubs.
It uses the TFL API to find nearby stops and then checks if there are any distinct hubs nearby.
If so, it adds a transfer edge between the two hubs.
"""

import networkx as nx
import requests
import json
import os
import logging
import time
import math
# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Retrieve the TFL API key from environment variables
TFL_API_KEY = os.getenv("TFL_API_KEY")
if not TFL_API_KEY:
    logging.warning("TFL_API_KEY not found in environment variables. Proceeding without API key (may hit rate limits).")

# Input graph file from the first script
INPUT_GRAPH_FILE = 'output/stage1_networkx_graph_hubs_base.json'
# Output files for the graph with transfer edges and the list of transfers to weight
OUTPUT_GRAPH_FILE = 'output/stage2_networkx_graph_hubs_with_transfers.json'
OUTPUT_TRANSFER_LIST_FILE = 'output/inter_hub_transfers_to_weight.json'

# Ensure the output directory exists (handled by build_hub_graph.py)
# os.makedirs(os.path.dirname(OUTPUT_GRAPH_FILE), exist_ok=True)

# TFL API endpoint for finding nearby StopPoints
TFL_API_NEARBY_URL = "https://api.tfl.gov.uk/StopPoint"
# Parameters for the nearby search
NEARBY_RADIUS_METERS = 250 # Search radius in meters
NEARBY_STOP_TYPES = "NaptanMetroStation,NaptanRailStation" # Include relevant station types
# Define the transport modes considered part of our core graph network
# Nearby stops served *only* by modes outside this set (like national-rail)
# will be checked if they exist in our base graph before adding transfers.
ALLOWED_MODES = {'tube', 'dlr', 'overground', 'elizabeth-line'}

# API Request handling
API_RETRY_DELAY = 5 # Seconds to wait before retrying a failed API call
API_MAX_RETRIES = 3 # Maximum number of retries for failed API calls

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
            json.dump(graph_data, f, indent=4)
        logging.info(f"Graph successfully saved to {filepath} in node-link format (using 'edges' key).")
    except Exception as e:
        # Log any errors during the file saving process
        logging.error(f"Error saving graph to {filepath}: {e}")

def save_transfer_list(transfer_list, filepath):
    """
    Saves the list of hub pairs needing transfer weighting to a JSON file.
    """
    try:
        # Write the list of transfer pairs to the specified file path
        with open(filepath, 'w') as f:
            json.dump(transfer_list, f, indent=4)
        logging.info(f"Transfer list successfully saved to {filepath}")
    except Exception as e:
        # Log any errors during the file saving process
        logging.error(f"Error saving transfer list to {filepath}: {e}")

def fetch_nearby_stops(lat, lon, radius, stop_types):
    """
    Fetches nearby stop points from the TFL API with retry logic.
    """
    params = {
        'lat': lat,
        'lon': lon,
        'radius': radius,
        'stopTypes': stop_types,
        'useStopPointHierarchy': 'false' # We want individual stops to find their parents
    }
    # Add the API key to the request parameters if it exists
    if TFL_API_KEY:
        params['app_key'] = TFL_API_KEY

    retries = 0
    while retries < API_MAX_RETRIES:
        try:
            # Make the API request
            response = requests.get(TFL_API_NEARBY_URL, params=params)
            # Check for HTTP errors
            response.raise_for_status()
            # Parse the JSON response
            data = response.json()
            # Return the list of stop points found
            return data.get('stopPoints', [])
        except requests.exceptions.HTTPError as e:
            # Specifically handle potential rate limiting (429) or other HTTP errors
            logging.warning(f"HTTP Error fetching nearby stops for ({lat}, {lon}): {e}. Status: {e.response.status_code}")
            if e.response.status_code == 429:
                 logging.warning(f"Rate limit hit. Retrying in {API_RETRY_DELAY} seconds...")
            else:
                 logging.warning(f"Retrying in {API_RETRY_DELAY} seconds...")
        except requests.exceptions.RequestException as e:
            # Handle other potential network errors
            logging.warning(f"Network error fetching nearby stops for ({lat}, {lon}): {e}. Retrying in {API_RETRY_DELAY} seconds...")
        except json.JSONDecodeError:
            # Handle errors in parsing the API response
            logging.error(f"Error decoding JSON response from TFL Nearby API for ({lat}, {lon}). Skipping this hub.")
            return [] # Return empty list on decode error for this specific call

        # Wait before retrying
        retries += 1
        time.sleep(API_RETRY_DELAY)

    # Log failure after all retries are exhausted
    logging.error(f"Failed to fetch nearby stops for ({lat}, {lon}) after {API_MAX_RETRIES} retries.")
    return [] # Return an empty list if all retries fail

# --- Main Logic ---

def add_proximity_transfers():
    """
    Adds potential walking transfer edges between nearby distinct hubs.
    """
    logging.info("Starting the process to add proximity transfer edges...")

    # 1. Load the Base Hub Graph
    G = load_graph(INPUT_GRAPH_FILE)
    if not G:
        return # Exit if graph loading failed

    # 2. Create Mappings
    # Create a dictionary mapping the node name (hub name) to its attributes
    hub_node_to_attributes = {node: data for node, data in G.nodes(data=True)}
    # Create a dictionary mapping the primary Naptan ID (hub ID) back to the node name
    primary_id_to_hub_node = {data['primary_naptan_id']: node for node, data in G.nodes(data=True)}

    # 3. Initialize Transfer List and Added Transfers Set
    # This list will store pairs of primary Naptan IDs for hubs that need walking time calculation
    inter_hub_transfers_to_weight = []
    # This set keeps track of transfer pairs we've already added edges for, preventing duplicates
    # Store pairs as sorted tuples to handle (A,B) and (B,A) equivalently
    added_transfer_edges = set()
    # This list will store details of National Rail hubs skipped because they weren't in the base graph
    skipped_national_rail_hubs = []

    logging.info("Iterating through hubs to find nearby potential transfers...")
    # 4. Iterate Through Hubs and Find Nearby Hubs via API
    hub_count = G.number_of_nodes()
    for i, (h1_name, h1_attributes) in enumerate(hub_node_to_attributes.items()):
        logging.info(f"Processing hub {i+1}/{hub_count}: {h1_name}")
        h1_lat = h1_attributes.get('lat')
        h1_lon = h1_attributes.get('lon')
        h1_primary_id = h1_attributes.get('primary_naptan_id')

        # Ensure we have the necessary info for the API call
        if not all([h1_lat, h1_lon, h1_primary_id]):
            logging.warning(f"Skipping hub {h1_name} due to missing lat/lon/primary_id.")
            continue

        # Call TFL API to find nearby stops
        nearby_stops = fetch_nearby_stops(h1_lat, h1_lon, NEARBY_RADIUS_METERS, NEARBY_STOP_TYPES)

        # 5. Process Nearby Stops and Add Transfer Edges
        nearby_hubs_found_in_radius = set() # Track hubs found in this iteration
        for nearby_stop in nearby_stops:
            # Get the Naptan ID and potentially the topMostParentId of the nearby stop
            nearby_naptan_id = nearby_stop.get('naptanId')
            nearby_hub_id = nearby_stop.get('topMostParentId', nearby_naptan_id) # Use naptanId if parent is missing
            nearby_common_name = nearby_stop.get('commonName', 'Unknown Name') # Get common name for logging

            if not nearby_hub_id:
                 logging.debug(f"Skipping nearby stop {nearby_naptan_id or 'Unknown Naptan'} as it has no determinable hub ID.")
                 continue # Skip if we can't determine a hub ID

            # Find the corresponding hub node name in our graph for this nearby hub ID
            h2_name = primary_id_to_hub_node.get(nearby_hub_id)
            # Determine if the corresponding hub exists in our graph
            hub_in_graph = h2_name is not None

            # --- Check if the nearby stop is National Rail-only and not in our graph ---
            # Extract the transport modes for the nearby stop point
            stop_modes = {group.get('modeName') for group in nearby_stop.get('lineModeGroups', []) if group.get('modeName')}
            # Check if 'national-rail' is a mode and no allowed modes are present
            is_national_rail_only = 'national-rail' in stop_modes and not stop_modes.intersection(ALLOWED_MODES)

            # If it's National Rail-only AND its hub is NOT in our graph, skip it
            if is_national_rail_only and not hub_in_graph:
                skipped_info = f"Skipped National Rail-only hub not in graph: {nearby_common_name} (Hub ID: {nearby_hub_id})"
                logging.info(skipped_info)
                # Add to list for final summary, avoiding duplicates if the same NR hub is found multiple times
                if skipped_info not in skipped_national_rail_hubs:
                    skipped_national_rail_hubs.append(skipped_info)
                continue # Move to the next nearby stop

            # Check if the nearby stop belongs to a hub known in our graph
            if not h2_name:
                # This case should now primarily catch non-National Rail hubs that are not in our graph,
                # or National Rail hubs that *are* served by allowed modes but still aren't in our graph (less likely).
                logging.debug(f"Skipping nearby stop {nearby_common_name} (Hub ID: {nearby_hub_id}) as its hub is not in our graph (and not NR-only). Modes: {stop_modes}")
                continue

            # Check if it's the same hub we started with
            if h1_name == h2_name:
                continue # Don't process transfers to the same hub
            
            # --- Log all distinct nearby hubs found within radius --- 
            if h2_name not in nearby_hubs_found_in_radius:
                 logging.debug(f"Hub '{h1_name}' found nearby hub '{h2_name}' (Hub ID: {nearby_hub_id}) within {NEARBY_RADIUS_METERS}m radius.")
                 nearby_hubs_found_in_radius.add(h2_name)
            
            # --- Process potential transfer --- 
            h2_attributes = hub_node_to_attributes.get(h2_name) # We know h2_name exists now
            h2_primary_id = h2_attributes.get('primary_naptan_id')
            if not h2_primary_id:
                logging.warning(f"Skipping potential transfer to {h2_name} as it lacks a 'primary_naptan_id' attribute.")
                continue # Skip if H2 is missing primary ID

            # Define the transfer pair (sorted tuple to ensure uniqueness regardless of order)
            transfer_pair = tuple(sorted((h1_name, h2_name)))

            # --- Conditions for adding transfer edge ---
            # a) Check if we've already added a transfer edge for this pair in this run
            if transfer_pair in added_transfer_edges:
                logging.debug(f"Skipping transfer check between {h1_name} and {h2_name}: Already processed/added.")
                continue

            # b) Check if a direct *non-transfer* connection already exists between these hubs
            has_direct_line = False
            # Check H1 -> H2 edges
            if G.has_edge(h1_name, h2_name):
                for key, data in G.get_edge_data(h1_name, h2_name).items():
                    if not data.get('transfer', False):
                        has_direct_line = True
                        logging.debug(f"Skipping potential transfer {h1_name} -> {h2_name}: Direct line edge exists (Key: {key}, Line: {data.get('line')}).")
                        break
            # Check H2 -> H1 edges if no direct line found yet
            if not has_direct_line and G.has_edge(h2_name, h1_name):
                for key, data in G.get_edge_data(h2_name, h1_name).items():
                     if not data.get('transfer', False):
                        has_direct_line = True
                        logging.debug(f"Skipping potential transfer {h2_name} -> {h1_name}: Direct line edge exists (Key: {key}, Line: {data.get('line')}).")
                        break

            if has_direct_line:
                # Mark as processed even if skipped, to avoid re-checking from the other direction
                added_transfer_edges.add(transfer_pair) 
                continue

            # --- Add the transfer edge (if all checks passed) ---
            logging.info(f"ADDING transfer edge: {h1_name} <-> {h2_name}")

            # Add bidirectional edges representing the walking transfer
            G.add_edge(
                h1_name, h2_name, key='transfer',
                transfer=True,
                mode='walking',
                line='walking',
                weight=None # Weight (duration) will be calculated in the next script
            )
            G.add_edge(
                h2_name, h1_name, key='transfer',
                transfer=True,
                mode='walking',
                line='walking',
                weight=None
            )

            # Mark this pair as added
            added_transfer_edges.add(transfer_pair)

            # Add the primary Naptan ID pair to the list for weighting
            inter_hub_transfers_to_weight.append(tuple(sorted((h1_primary_id, h2_primary_id))))
            logging.debug(f"Added pair ({h1_primary_id}, {h2_primary_id}) to weighting list.")


    logging.info(f"Identified {len(inter_hub_transfers_to_weight)} potential inter-hub transfers to weight.")

    # 6. Save the Updated Graph and the Transfer List
    save_graph(G, OUTPUT_GRAPH_FILE)
    # Remove duplicates from the transfer list before saving
    unique_transfers = list(dict.fromkeys(inter_hub_transfers_to_weight))
    save_transfer_list(unique_transfers, OUTPUT_TRANSFER_LIST_FILE)

    # Log the skipped National Rail hubs
    if skipped_national_rail_hubs:
        logging.info("--- Skipped National Rail-Only Hubs (Not in Base Graph) ---")
        for skipped_hub in skipped_national_rail_hubs:
            logging.info(skipped_hub)
        logging.info("----------------------------------------------------------")
    else:
        logging.info("No National Rail-only hubs were skipped for not being in the base graph.")

    logging.info("Proximity transfer addition process completed.")

# --- Script Execution ---
if __name__ == "__main__":
    # Run the main function when the script is executed
    add_proximity_transfers() 