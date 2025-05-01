"""
This script builds the base hub graph.
It fetches the TFL line sequence data and processes it to identify hubs and stations.
It then creates a NetworkX graph with single nodes per hub and inter-hub line connections.
"""

import networkx as nx
import requests
import json
import os
import logging
import time
from dotenv import load_dotenv

# --- Configuration ---
# Load environment variables (like TFL_API_KEY)
load_dotenv()

# Set up logging to provide informative output during script execution
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define file paths for input data cache and output graph
OUTPUT_DIR = 'networkx_graph/graph_data' # Use a common output dir variable
TFL_DATA_CACHE = os.path.join(OUTPUT_DIR, 'tfl_all_line_sequence_data.json') # More descriptive cache name
OUTPUT_GRAPH_FILE = os.path.join(OUTPUT_DIR, 'networkx_graph_hubs_base.json')
# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# TFL API Configuration
TFL_API_KEY = os.getenv("TFL_API_KEY")
if not TFL_API_KEY:
    logging.warning("TFL_API_KEY environment variable not set. API calls may fail.")
    # Allow script to continue, but API calls might be rate-limited or fail

BASE_URL = "https://api.tfl.gov.uk"
TRANSPORT_MODES = ["tube", "dlr", "elizabeth-line", "overground"]
# Note: National Rail sequences might be less detailed or structured differently in TFL API

# API Request handling
API_RETRY_DELAY = 5 # Seconds to wait before retrying a failed API call
API_MAX_RETRIES = 3 # Maximum number of retries
REQUEST_TIMEOUT = 20 # Timeout for API requests
FETCH_DELAY = 0.3 # Small delay between API calls to avoid hitting rate limits

# --- Mappings ---
# Explicit mapping from specific line IDs to canonical TfL API modes
# This helps where the API might not return the mode or uses a specific line ID
LINE_ID_TO_MODE_MAP = {
    # Tube
    "bakerloo": "tube",
    "central": "tube",
    "circle": "tube",
    "district": "tube",
    "hammersmith-city": "tube",
    "jubilee": "tube",
    "metropolitan": "tube",
    "northern": "tube",
    "piccadilly": "tube",
    "victoria": "tube",
    "waterloo-city": "tube",
    # DLR
    "dlr": "dlr",
    # Elizabeth Line
    "elizabeth": "elizabeth-line", # Actual line ID is just 'elizabeth'
    # Overground (use canonical 'overground' mode for API calls)
    "london-overground": "overground", # Base ID
    "weaver": "overground",
    "suffragette": "overground",
    "windrush": "overground",
    "mildmay": "overground",
    "lioness": "overground",
    "liberty": "overground",
    # Add other lines if necessary, e.g., trams, river-bus, cable-car
    # "tram": "tram",
}

# --- Helper Functions ---

def _make_tfl_request(url, params=None):
    """Helper function to make a single TFL API request with retries."""
    if not TFL_API_KEY:
        logging.error("Cannot make TFL request: TFL_API_KEY not set.")
        return None # Or raise an exception

    # Always add the API key to parameters
    request_params = params.copy() if params else {}
    request_params['app_key'] = TFL_API_KEY

    retries = 0
    while retries < API_MAX_RETRIES:
        try:
            response = requests.get(url, params=request_params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
            return response.json()
        except requests.exceptions.HTTPError as e:
            logging.warning(f"HTTP Error ({e.response.status_code}) for {url}: {e}. Retrying...")
            # Handle rate limiting specifically if needed (status code 429)
            if e.response.status_code == 429:
                 logging.warning(f"Rate limit likely hit. Waiting {API_RETRY_DELAY * (retries + 1)}s...")
                 time.sleep(API_RETRY_DELAY * (retries + 1))
            else:
                 time.sleep(API_RETRY_DELAY)
        except requests.exceptions.Timeout:
            logging.warning(f"Timeout for {url}. Retrying...")
            time.sleep(API_RETRY_DELAY)
        except requests.exceptions.RequestException as e:
            logging.warning(f"Request failed for {url}: {e}. Retrying...")
            time.sleep(API_RETRY_DELAY)
        except json.JSONDecodeError:
            logging.error(f"Failed to decode JSON response from {url}.")
            return None # Don't retry if response is not valid JSON

        retries += 1

    logging.error(f"Failed to fetch data from {url} after {API_MAX_RETRIES} retries.")
    return None

def get_lines_for_mode(mode):
    """Fetches all line IDs for a given transport mode."""
    logging.info(f"Fetching lines for mode: {mode}")
    url = f"{BASE_URL}/Line/Mode/{mode}"
    lines_data = _make_tfl_request(url)
    if lines_data:
        return [line.get('id') for line in lines_data if line.get('id')] # Return list of line IDs
    else:
        logging.error(f"Could not fetch lines for mode: {mode}")
        return []

def get_line_sequence_data(line_id):
    """Fetches the route sequence data for a specific line ID."""
    logging.info(f"Fetching sequence data for line: {line_id}")
    url = f"{BASE_URL}/Line/{line_id}/Route/Sequence/all"
    params = {"excludeCrowding": "true"}
    sequence_data = _make_tfl_request(url, params=params)
    if sequence_data:
        # Add the line_id to the returned data for easier processing later
        sequence_data['retrieved_line_id'] = line_id
        # Remove the unreliable heuristic for guessing 'modeName'
        # We will determine the mode based on the line_id using LINE_ID_TO_MODE_MAP later
        # if 'modeName' not in sequence_data:
        #     if line_id in ['dlr','elizabeth-line', 'london-overground']:
        #          sequence_data['modeName'] = line_id.replace('london-','')
        #     elif line_id in ['bakerloo', 'central', 'circle', 'district', 'hammersmith-city', 'jubilee', 'metropolitan', 'northern', 'piccadilly', 'victoria', 'waterloo-city']:
        #          sequence_data['modeName'] = 'tube'

        return sequence_data
    else:
        logging.warning(f"Could not fetch sequence data for line: {line_id}")
        return None

def fetch_all_tfl_data(modes, cache_path):
    """
    Fetches all line sequence data for the specified modes, using cache if available.
    Returns a list of sequence data objects, one for each successfully fetched line.
    """
    # Check cache first
    if os.path.exists(cache_path):
        cache_mod_time = os.path.getmtime(cache_path)
        if (time.time() - cache_mod_time) < 7 * 24 * 60 * 60:
            logging.info(f"Using cached TFL line data from {cache_path}")
            with open(cache_path, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    logging.error(f"Error decoding cache file {cache_path}. Fetching fresh data.")
        else:
            logging.info("Cached TFL data is older than 7 days. Fetching fresh data.")
    else:
        logging.info("No cached TFL data found. Fetching from API.")

    all_sequence_data = []
    lines_to_fetch = set()

    # 1. Get all line IDs for all modes
    for mode in modes:
        line_ids = get_lines_for_mode(mode)
        lines_to_fetch.update(line_ids)
        time.sleep(FETCH_DELAY) # Small delay between mode requests

    logging.info(f"Found {len(lines_to_fetch)} unique lines to fetch sequence data for.")

    # 2. Fetch sequence data for each unique line ID
    fetched_count = 0
    for line_id in lines_to_fetch:
        sequence_data = get_line_sequence_data(line_id)
        if sequence_data:
            all_sequence_data.append(sequence_data)
            fetched_count += 1
        # Apply delay even if fetch failed to avoid hammering API on retries
        time.sleep(FETCH_DELAY)

    logging.info(f"Successfully fetched sequence data for {fetched_count}/{len(lines_to_fetch)} lines.")

    # 3. Save fetched data to cache
    if all_sequence_data:
        try:
            with open(cache_path, 'w') as f:
                json.dump(all_sequence_data, f, indent=4)
            logging.info(f"Saved fetched TFL line data to {cache_path}")
        except Exception as e:
            logging.error(f"Error saving TFL data to cache {cache_path}: {e}")

    return all_sequence_data


def save_graph(graph, filepath):
    """
    Saves the NetworkX graph to a JSON file in node-link format.
    This format is directly loadable by nx.node_link_graph().
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


# --- Main Graph Building Logic ---

def build_base_hub_graph():
    """
    Builds the base graph with single nodes per hub and inter-hub line connections.
    """
    logging.info("Starting the hub graph building process...")

    # 1. Fetch or Load TFL Line Data (Aggregated across modes/lines)
    # This now returns a list of sequence data objects, one per line
    all_line_sequences = fetch_all_tfl_data(TRANSPORT_MODES, TFL_DATA_CACHE)
    if not all_line_sequences:
        logging.error("Failed to get TFL line sequence data. Aborting graph build.")
        return None

    # 2. Hub Identification and Mapping Creation
    hub_info = {} # topMostParentId -> {hub_name, lat, lon, zone, primary_naptan_id, modes, lines, constituent_stations}
    station_to_hub_id = {} # stationId (naptanId) -> topMostParentId

    logging.info("Processing TFL data to identify hubs and stations...")
    # Iterate through the sequence data for each line
    for line_sequence_data in all_line_sequences:
        line_id = line_sequence_data.get('retrieved_line_id') # Use the ID we fetched with
        # Determine the correct mode using the mapping, default to 'unknown' if not found
        mode_name = LINE_ID_TO_MODE_MAP.get(line_id, 'unknown')
        if mode_name == 'unknown':
             logging.warning(f"Line ID '{line_id}' not found in LINE_ID_TO_MODE_MAP. Mode set to 'unknown'. Update map if needed.")

        # Process stopPointSequences (preferred data source)
        for sequence in line_sequence_data.get('stopPointSequences', []):
            for stop in sequence.get('stopPoint', []):
                station_id = stop.get('id') or stop.get('stationId') # TFL uses both 'id' and 'stationId'
                if not station_id:
                    logging.debug(f"Skipping stop point with no ID in line {line_id}")
                    continue

                station_name = stop.get('name')
                lat = stop.get('lat')
                lon = stop.get('lon')
                zone = stop.get('zone')
                # Determine hub ID
                hub_id = stop.get('topMostParentId', station_id) # Default to self if no parent
                if not hub_id: hub_id = station_id

                station_to_hub_id[station_id] = hub_id

                # Aggregate hub info
                if hub_id not in hub_info:
                    # Initialize hub info (using first encountered details as base)
                    hub_info[hub_id] = {
                        'hub_name': station_name, # Use first name, try to refine below
                        'primary_naptan_id': hub_id,
                        'lat': lat, 'lon': lon, 'zone': zone,
                        'modes': set(), 'lines': set(), 
                        # Initialize the new structure for constituent stations (temp dict)
                        'constituent_stations': {} 
                    }
                    # Attempt to find parent details for better name/coords
                    parent_info_found = False
                    for prop in stop.get('additionalProperties', []):
                        if prop.get('category') == 'StopSharing' and prop.get('key') == 'ParentId' and prop.get('sourceSystemKey') == 'NaPTAN' and prop.get('value') == hub_id:
                            hub_info[hub_id]['hub_name'] = stop.get('commonName', station_name)
                            hub_info[hub_id]['lat'] = stop.get('lat', lat)
                            hub_info[hub_id]['lon'] = stop.get('lon', lon)
                            parent_info_found = True
                            break

                # Add current station's details to hub
                # Use station_id as key and station_name as value in the temp dict
                if station_name: # Ensure station has a name
                     hub_info[hub_id]['constituent_stations'][station_id] = station_name
                else:
                     logging.warning(f"Constituent station {station_id} for hub {hub_id} has no name. Skipping.")
                    
                # Add lines and modes
                if line_id: hub_info[hub_id]['lines'].add(line_id)
                if mode_name != 'unknown': hub_info[hub_id]['modes'].add(mode_name)
                # Add modes from the stop point itself if available
                hub_info[hub_id]['modes'].update(stop.get('modes', []))

    # Refine hub modes (remove empty strings, duplicates already handled by set)
    for hub_id in hub_info:
        hub_info[hub_id]['modes'] = {m for m in hub_info[hub_id]['modes'] if m} # Filter out empty strings

    # Convert sets to lists for JSON serialization and finalize constituent_stations
    for hub_id in hub_info:
        hub_info[hub_id]['modes'] = sorted(list(hub_info[hub_id]['modes'])) # Sort for consistency
        hub_info[hub_id]['lines'] = sorted(list(hub_info[hub_id]['lines']))
        
        # Convert the temporary constituent_stations dict to the final list of dicts
        constituent_list = [
            {'name': name, 'naptan_id': naptan_id} 
            for naptan_id, name in hub_info[hub_id]['constituent_stations'].items()
        ]
        # Sort the list for consistency (e.g., by Naptan ID)
        hub_info[hub_id]['constituent_stations'] = sorted(constituent_list, key=lambda x: x['naptan_id'])
        
        # Remove the old constituent_naptan_ids key if it somehow exists (it shouldn't with new init)
        # hub_info[hub_id].pop('constituent_naptan_ids', None) 

    logging.info(f"Identified {len(hub_info)} unique hubs.")

    # 3. Initialize Graph and Add Hub Nodes
    G = nx.MultiDiGraph()
    logging.info("Adding hub nodes to the graph...")
    hub_name_to_id = {} # Helper mapping for the correction below
    for hub_id, attributes in hub_info.items():
        node_name = attributes['hub_name']
        if not node_name:
             logging.warning(f"Hub {hub_id} has no name. Using ID as name.")
             node_name = hub_id
             attributes['hub_name'] = node_name # Ensure hub_name attribute exists
        try:
            G.add_node(node_name, **attributes)
            hub_name_to_id[node_name] = hub_id # Store reverse mapping
        except Exception as e:
             logging.error(f"Error adding node '{node_name}' with attributes {attributes}: {e}")

    logging.info(f"Added {G.number_of_nodes()} nodes to the graph.")

    # --- Manual Data Correction --- 
    # Willesden Green (940GZZLUWIG) is often incorrectly assigned to Metropolitan by TFL API.
    willesden_green_naptan = "940GZZLUWIG"
    willesden_hub_id = station_to_hub_id.get(willesden_green_naptan)
    if willesden_hub_id:
        willesden_hub_node_name = hub_info.get(willesden_hub_id, {}).get('hub_name')
        if willesden_hub_node_name and G.has_node(willesden_hub_node_name):
            hub_lines = G.nodes[willesden_hub_node_name].get('lines', [])
            if 'metropolitan' in hub_lines:
                logging.info(f"Correcting node data: Removing 'metropolitan' from lines list for hub '{willesden_hub_node_name}' containing {willesden_green_naptan}")
                hub_lines.remove('metropolitan')
                G.nodes[willesden_hub_node_name]['lines'] = sorted(hub_lines) # Keep it sorted
        else:
             logging.warning(f"Could not find hub node name '{willesden_hub_node_name}' for Willesden Green correction ({willesden_hub_id})")
    else:
        logging.debug(f"Willesden Green station {willesden_green_naptan} not found in station_to_hub_id mapping. Cannot apply correction.")
    # --- End Manual Data Correction ---

    # 4. Add Inter-Hub Line Edges
    logging.info("Adding inter-hub line edges to the graph...")
    edge_count = 0
    # Re-iterate through the line sequence data to create edges
    for line_sequence_data in all_line_sequences:
        line_id = line_sequence_data.get('retrieved_line_id')
        # Determine the correct mode using the mapping for edge attributes
        mode = LINE_ID_TO_MODE_MAP.get(line_id, 'unknown')
        if mode == 'unknown' and line_id: # Avoid logging if line_id itself was missing
             logging.warning(f"Edge creation: Mode unknown for line ID '{line_id}'. Check LINE_ID_TO_MODE_MAP.")

        for sequence in line_sequence_data.get('stopPointSequences', []):
            branch_id = sequence.get('branchId', 0)
            direction = sequence.get('direction', 'unknown')
            ordered_stops = sequence.get('stopPoint', [])

            for i in range(len(ordered_stops) - 1):
                station_a_id = ordered_stops[i].get('id') or ordered_stops[i].get('stationId')
                station_b_id = ordered_stops[i+1].get('id') or ordered_stops[i+1].get('stationId')

                if not station_a_id or not station_b_id:
                    continue # Skip if IDs are missing

                hub_a_id = station_to_hub_id.get(station_a_id)
                hub_b_id = station_to_hub_id.get(station_b_id)

                # Proceed only if both hubs are found and they are different hubs
                if hub_a_id and hub_b_id and hub_a_id != hub_b_id:
                    hub_a_info = hub_info.get(hub_a_id)
                    hub_b_info = hub_info.get(hub_b_id)

                    if not hub_a_info or not hub_b_info:
                         logging.warning(f"Hub info missing for {hub_a_id} or {hub_b_id}. Skipping edge.")
                         continue

                    hub_a_name = hub_a_info.get('hub_name')
                    hub_b_name = hub_b_info.get('hub_name')

                    if not hub_a_name or not hub_b_name:
                         logging.warning(f"Hub name missing for {hub_a_id} or {hub_b_id}. Skipping edge.")
                         continue

                    # Check if nodes exist before adding edge
                    if not G.has_node(hub_a_name) or not G.has_node(hub_b_name):
                        logging.warning(f"Nodes {hub_a_name} or {hub_b_name} not found in graph. Skipping edge.")
                        continue

                    try:
                        G.add_edge(
                            hub_a_name, hub_b_name,
                            key=line_id, # Use line_id as the key
                            line=line_id,
                            mode=mode,
                            direction=direction,
                            branch=branch_id,
                            transfer=False,
                            weight=None # Weights calculated later or in different script
                        )
                        edge_count += 1
                    except Exception as e:
                         logging.error(f"Error adding edge {hub_a_name} -> {hub_b_name} (key: {line_id}): {e}")

    logging.info(f"Added {edge_count} inter-hub line edges.")

    # --- Post-Processing Corrections ---
    # 1. Remove incorrect Metropolitan edges from Willesden Green
    willesden_green_naptan = "940GZZLUWIG"
    willesden_hub_id = station_to_hub_id.get(willesden_green_naptan)
    willesden_hub_node_name = None
    if willesden_hub_id:
        willesden_hub_node_name = hub_info.get(willesden_hub_id, {}).get('hub_name')

    if willesden_hub_node_name and G.has_node(willesden_hub_node_name):
        edges_to_remove = []
        # Check outgoing edges
        for u, v, key, data in G.out_edges(willesden_hub_node_name, keys=True, data=True):
            if data.get('line') == 'metropolitan':
                edges_to_remove.append((u, v, key))
        # Check incoming edges
        for u, v, key, data in G.in_edges(willesden_hub_node_name, keys=True, data=True):
            if data.get('line') == 'metropolitan':
                edges_to_remove.append((u, v, key))

        if edges_to_remove:
            logging.info(f"Removing {len(edges_to_remove)} incorrect Metropolitan line edges connected to {willesden_hub_node_name}.")
            for u, v, key in edges_to_remove:
                if G.has_edge(u, v, key=key):
                    G.remove_edge(u, v, key=key)
                else:
                     logging.warning(f"Attempted to remove non-existent edge during correction: {u}->{v} key:{key}")

    # 2. Add missing direct Metropolitan edge between Finchley Road and Wembley Park
    finchley_rd_naptan = "940GZZLUFYR"
    wembley_pk_naptan = "940GZZLUWYP"
    finchley_hub_id = station_to_hub_id.get(finchley_rd_naptan)
    wembley_hub_id = station_to_hub_id.get(wembley_pk_naptan)
    finchley_hub_name = hub_info.get(finchley_hub_id, {}).get('hub_name') if finchley_hub_id else None
    wembley_hub_name = hub_info.get(wembley_hub_id, {}).get('hub_name') if wembley_hub_id else None

    if finchley_hub_name and wembley_hub_name and G.has_node(finchley_hub_name) and G.has_node(wembley_hub_name):
        logging.info(f"Adding direct Metropolitan edge between {finchley_hub_name} and {wembley_hub_name}.")
        common_edge_attrs = {
            'line': 'metropolitan',
            'mode': 'tube',
            'direction': 'bidirectional_added', # Indicate it was manually added
            'branch': 0, # Or appropriate value
            'transfer': False,
            'weight': None
        }
        # Add edge Finchley -> Wembley
        if not G.has_edge(finchley_hub_name, wembley_hub_name, key='metropolitan'):
            G.add_edge(finchley_hub_name, wembley_hub_name, key='metropolitan', **common_edge_attrs)
            edge_count += 1 # Increment edge count
        else:
            logging.debug(f"Edge {finchley_hub_name}->{wembley_hub_name} (metropolitan) already exists.")
        # Add edge Wembley -> Finchley
        if not G.has_edge(wembley_hub_name, finchley_hub_name, key='metropolitan'):
            G.add_edge(wembley_hub_name, finchley_hub_name, key='metropolitan', **common_edge_attrs)
            edge_count += 1 # Increment edge count
        else:
            logging.debug(f"Edge {wembley_hub_name}->{finchley_hub_name} (metropolitan) already exists.")
    else:
        logging.warning("Could not find hub nodes for Finchley Road and/or Wembley Park. Cannot add direct Metropolitan edge.")
    # --- End Post-Processing Corrections ---

    logging.info(f"Final Graph (after corrections): {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # 5. Save the Graph
    save_graph(G, OUTPUT_GRAPH_FILE)

    logging.info("Base hub graph build process completed.")
    return G

# --- Script Execution ---
if __name__ == "__main__":
    build_base_hub_graph() 