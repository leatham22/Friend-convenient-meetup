"""
This script was used to debug the difference in journey times between the graph time and returned journey time from the TfL API. 
"""

import json
import networkx as nx
import heapq
import requests
import os
import sys
import math
from dotenv import load_dotenv

# --- Configuration ---
GRAPH_PATH = "networkx_graph/create_graph/output/final_networkx_graph.json"
TFL_API_BASE_URL = "https://api.tfl.gov.uk/Journey/JourneyResults/"


# --- Helper Functions (Adapted from main.py) ---

def load_networkx_graph_and_station_data():
    """Loads the NetworkX graph and extracts station data (attributes) from nodes."""
    try:
        with open(GRAPH_PATH, 'r') as f:
            graph_data = json.load(f)

        G = nx.MultiDiGraph()
        station_data_lookup = {}

        # Process nodes (list of dicts in the final graph format)
        if 'nodes' in graph_data and isinstance(graph_data['nodes'], list):
            for node_dict in graph_data['nodes']:
                if isinstance(node_dict, dict) and 'id' in node_dict:
                    node_id = node_dict['id'] # Node ID is the hub name
                    try:
                        # Add node directly with its attributes from the JSON dict
                        G.add_node(node_id, **node_dict) 
                        # *** Crucially, populate the lookup AFTER adding to graph, using graph's data view ***
                        station_data_lookup[node_id] = G.nodes[node_id] 
                    except Exception as e:
                         print(f"Error adding node or populating lookup for '{node_id}': {e}")
                else:
                    print(f"Warning: Skipping node due to missing 'id' or unexpected format: {node_dict}")
        else:
            print("Warning: 'nodes' key not found or not a list in graph data.")

        # Process edges (list of dicts)
        # Use 'links' key first, fallback to 'edges'
        edge_list_key = 'links' if 'links' in graph_data else 'edges'
        if edge_list_key in graph_data and isinstance(graph_data[edge_list_key], list):
            for edge_dict in graph_data[edge_list_key]:
                # Check for required keys including 'weight'
                if isinstance(edge_dict, dict) and all(k in edge_dict for k in ['source', 'target', 'key', 'weight']):
                    source = edge_dict['source']
                    target = edge_dict['target']
                    key = edge_dict['key'] # This is the line/mode/transfer identifier
                    weight = edge_dict['weight'] 

                    # Ensure nodes exist before adding edge
                    if G.has_node(source) and G.has_node(target):
                         # Add edge with key and weight as an attribute
                        G.add_edge(source, target, key=key, weight=weight)
                    else:
                        print(f"Warning: Skipping edge due to missing node(s): {source} -> {target} (Key: {key})")
                else:
                    print(f"Warning: Skipping invalid edge format or missing required keys (source, target, key, weight) in '{edge_list_key}' list: {edge_dict}")
        else:
            print(f"Warning: Neither 'links' nor 'edges' key found or not a list in graph data.")

        print(f"Loaded NetworkX graph from '{GRAPH_PATH}' with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
        print(f"Created station lookup for {len(station_data_lookup)} stations from graph nodes.")
        return G, station_data_lookup
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading or parsing NetworkX graph JSON: {e}", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred during graph construction: {e}", file=sys.stderr)
        return None, None

def get_api_key():
    """Retrieves the TfL API key."""
    load_dotenv()
    api_key = os.environ.get('TFL_API_KEY')
    if not api_key:
        print("Error: TFL_API_KEY not found in environment variables.", file=sys.stderr)
    return api_key

def get_travel_time_tfl(start_naptan_id, end_naptan_id, api_key):
    """Calls the TfL Journey Planner API using Naptan IDs."""
    # Check if start and end are the same Hub ID. 
    # The API might handle this, but it saves an unnecessary call.
    if start_naptan_id == end_naptan_id:
        print(f"  Start and end Naptan IDs are the same ({start_naptan_id}), returning 0 minutes.")
        return 0 # Travel time within the same hub/station is 0

    if not start_naptan_id or not end_naptan_id:
        print("  Error: Missing Naptan ID for TfL API call.")
        return None

    # Use Naptan IDs directly in the URL
    url = f"{TFL_API_BASE_URL}{start_naptan_id}/to/{end_naptan_id}"

    params = {
        'app_key': api_key,
        'timeIs': 'Departing',
        'journeyPreference': 'leasttime'
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        journey_data = response.json()

        if not journey_data.get('journeys'):
            print(f"  Warning: No TfL journey found between {start_naptan_id} and {end_naptan_id}.")
            return None

        duration = journey_data['journeys'][0].get('duration')
        return duration

    except Exception as e:
        # Attempt to parse TfL error message if available
        error_message = f"Error getting TfL travel time: {e}"
        try:
            error_details = response.json()
            if 'message' in error_details:
                error_message += f" - TfL Message: {error_details['message']}"
        except Exception:
            pass # Ignore if response is not JSON or doesn't contain message
        print(f"  {error_message}", file=sys.stderr)
        return None

def get_journey_details_tfl(start_naptan_id, end_naptan_id, api_key):
    """Calls the TfL Journey Planner API using Naptan IDs and returns the first journey object."""
    # Check if start and end are the same Hub ID. 
    if start_naptan_id == end_naptan_id:
        print(f"  Start and end Naptan IDs are the same ({start_naptan_id}), returning None (no journey needed).")
        # Return a structure indicating 0 duration but no legs? Or just None? Let's return None.
        return None 

    if not start_naptan_id or not end_naptan_id:
        print("  Error: Missing Naptan ID for TfL API call.")
        return None

    # Use Naptan IDs directly in the URL
    url = f"{TFL_API_BASE_URL}{start_naptan_id}/to/{end_naptan_id}"

    params = {
        'app_key': api_key,
        'timeIs': 'Departing',
        'journeyPreference': 'leasttime' # Add parameter to prioritise speed
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        journey_data = response.json()

        if not journey_data.get('journeys'):
            print(f"  Warning: No TfL journey found between {start_naptan_id} and {end_naptan_id}.")
            return None

        # Return the entire first journey object
        return journey_data['journeys'][0]

    except Exception as e:
         # Attempt to parse TfL error message if available
        error_message = f"Error getting TfL journey details: {e}"
        try:
            error_details = response.json()
            if 'message' in error_details:
                error_message += f" - TfL Message: {error_details['message']}"
        except Exception:
            pass # Ignore if response is not JSON or doesn't contain message
        print(f"  {error_message}", file=sys.stderr)
        return None

# --- Modified Dijkstra to return Path and Penalty Details ---

def dijkstra_with_transfer_penalty_and_path(graph, start_station_name, end_station_name):
    """
    Calculates the shortest path travel time using custom Dijkstra,
    incorporating penalties and returning path details.
    Note: This version doesn't include walk time, calculated separately.

    Returns:
        tuple: (min_time, path_nodes, path_keys, total_penalty) or (inf, [], [], 0) if no path.
    """
    # Ensure start/end stations exist in the graph before starting
    if start_station_name not in graph:
        print(f"  Error: Start station '{start_station_name}' not found in the graph.")
        return float('inf'), [], [], 0.0
    if end_station_name not in graph:
        print(f"  Error: End station '{end_station_name}' not found in the graph.")
        return float('inf'), [], [], 0.0
        
    # If start and end are the same, return 0 time immediately
    if start_station_name == end_station_name:
        print(f"  Start and end stations are the same ('{start_station_name}'), path time is 0.")
        return 0.0, [start_station_name], [], 0.0

    pq = [(0.0, start_station_name, None)] # (time, station, line_key_used_to_arrive)
    distances = {(start_station_name, None): 0.0} # Key: (station, line_key), Value: time
    
    # Store predecessors to reconstruct the path: Key: (station, line_key), Value: (prev_station, prev_line_key, edge_duration, penalty_added)
    predecessors = {} 
    
    min_time_to_destination = float('inf')
    final_state_at_destination = None # Store the state (station, line_key) that achieved min_time

    while pq:
        current_time, current_station, previous_line_key = heapq.heappop(pq)

        if current_time > distances.get((current_station, previous_line_key), float('inf')):
            continue

        # Check if this path reached the destination
        if current_station == end_station_name:
            if current_time < min_time_to_destination:
                 min_time_to_destination = current_time
                 final_state_at_destination = (current_station, previous_line_key)
            # Continue searching as other paths/lines might reach destination later but faster overall

        # Optimization: If current path is already longer than best known destination time, prune
        if current_time >= min_time_to_destination:
             continue

        if current_station not in graph:
            continue

        for neighbor_station in graph.neighbors(current_station):
            edge_datas = graph.get_edge_data(current_station, neighbor_station)
            if not edge_datas: continue

            for edge_key, edge_data in edge_datas.items():
                edge_travel_time = edge_data.get('weight', float('inf')) 
                current_edge_line_key = edge_key 

                if edge_travel_time == float('inf') or current_edge_line_key is None:
                    continue

                penalty = 0.0
                if (previous_line_key is not None and 
                    current_edge_line_key != previous_line_key and
                    previous_line_key != 'transfer' and 
                    current_edge_line_key != 'transfer'):
                    penalty = 5.0 

                new_time = current_time + edge_travel_time + penalty
                neighbor_state = (neighbor_station, current_edge_line_key)

                if new_time < distances.get(neighbor_state, float('inf')):
                    distances[neighbor_state] = new_time
                    heapq.heappush(pq, (new_time, neighbor_station, current_edge_line_key))
                    # Store predecessor info for path reconstruction, store edge_travel_time
                    predecessors[neighbor_state] = (current_station, previous_line_key, edge_travel_time, penalty)

    # Path Reconstruction
    if final_state_at_destination:
        path_nodes = []
        path_keys = []
        total_penalty = 0.0
        
        curr = final_state_at_destination
        while curr in predecessors:
            prev_station, prev_line_key, edge_travel_time, penalty = predecessors[curr]
            # Insert at the beginning to reverse the path
            path_nodes.insert(0, curr[0]) 
            path_keys.insert(0, curr[1])
            total_penalty += penalty
            curr = (prev_station, prev_line_key)
            
        # Add the start node
        path_nodes.insert(0, start_station_name)
        # path_keys list starts from the key of the *first edge taken*
        
        return min_time_to_destination, path_nodes, path_keys, total_penalty
    else:
        return float('inf'), [], [], 0.0


# --- Main Comparison Logic ---

def main():
    print("--- Journey Time Comparison Debugger ---")
    
    # Load graph and station data lookup from the graph file
    G, station_data_lookup = load_networkx_graph_and_station_data()
    api_key = get_api_key()

    if G is None or station_data_lookup is None or not api_key:
        print("Error loading necessary data (Graph, Station Data, or API Key). Exiting.")
        sys.exit(1)

    # Define example journeys (start_station, end_station, walk_time_to_start)
    journeys = [
        ("Ladbroke Grove Underground Station", "Westminster Underground Station", 3),
        ("Fulham Broadway Underground Station", "Notting Hill Gate Underground Station", 4),
        ("Canary Wharf Underground Station", "Gloucester Road Underground Station", 2),
        ("Earl's Court Underground Station", "Green Park Underground Station", 5), # Example different start
        ("Bond Street Underground Station", "Waterloo Underground Station", 6),
        # Add Homerton journey for diagnostics
        ("Homerton Rail Station", "Stratford Underground Station", 4)
    ]

    print("\nComparing Journeys:")
    print("="*80)

    for start_station, end_station, walk_time in journeys:
        print(f"Journey: {start_station} -> {end_station} (Walk: {walk_time} mins)")
        print("-"*80)

        # --- Graph Calculation ---
        print("Calculating Graph Time...")

        # --- DIAGNOSTICS FOR HOMERTON --- 
        if start_station == "Homerton Rail Station":
            print("  --- Homerton Diagnostics --- ")
            if G.has_node(start_station):
                print(f"  Node '{start_station}' exists in graph.")
                neighbors = list(G.neighbors(start_station))
                print(f"  Neighbors of {start_station}: {neighbors}")
                for neighbor in neighbors:
                    print(f"\n    --- Checking edges from {start_station} to {neighbor} ---")
                    edge_data = G.get_edge_data(start_station, neighbor)
                    # print(f"    Edge data to '{neighbor}':") # Less verbose
                    if edge_data:
                        for key, data in edge_data.items():
                            print(f"      Edge ({start_station} -> {neighbor}) Key ('{key}'): {data}")
                            # Use 'weight' here
                            weight_val = data.get('weight') 
                            if weight_val is None:
                                print("        -> Weight: MISSING or None")
                            elif isinstance(weight_val, (int, float)):
                                print(f"        -> Weight: {weight_val} (Valid type)")
                            else:
                                print(f"        -> Weight: {weight_val} (INVALID TYPE: {type(weight_val)})")
                    else:
                        print("     (No edge data found - unexpected)")

                    # --- Check Neighbor's Outgoing Edges --- 
                    if G.has_node(neighbor):
                        print(f"\n    --- Checking OUTGOING edges from Neighbor: {neighbor} ---")
                        neighbor_neighbors = list(G.neighbors(neighbor))
                        # print(f"    Neighbors of {neighbor}: {neighbor_neighbors}") # Optional verbosity
                        for nn in neighbor_neighbors:
                            nn_edge_data = G.get_edge_data(neighbor, nn)
                            if nn_edge_data:
                                for nn_key, nn_data in nn_edge_data.items():
                                     print(f"      Edge ({neighbor} -> {nn}) Key ('{nn_key}'): {nn_data}")
                                     # Use 'weight' here
                                     nn_weight = nn_data.get('weight') 
                                     if nn_weight is None:
                                         print("        -> Weight: MISSING or None")
                                     elif isinstance(nn_weight, (int, float)):
                                         print(f"        -> Weight: {nn_weight} (Valid type)")
                                     else:
                                         print(f"        -> Weight: {nn_weight} (INVALID TYPE: {type(nn_weight)})")
                            else:
                                print(f"      (No edge data found for {neighbor} -> {nn}) - unexpected")
                    # --- End Check Neighbor's Outgoing Edges --- 

            else:
                print(f"  Node '{start_station}' NOT FOUND in graph.")
            print("\n  --- End Homerton Diagnostics --- ")
        # --- END DIAGNOSTICS --- 

        graph_time_no_walk, path_nodes, path_keys, total_penalty = dijkstra_with_transfer_penalty_and_path(G, start_station, end_station)
        
        if graph_time_no_walk == float('inf'):
            print("  Graph Path: Not found.")
            graph_total_time = float('inf')
        else:
            graph_total_time = graph_time_no_walk + walk_time
            print(f"  Graph Path ({len(path_nodes)} nodes): {' -> '.join(path_nodes)}")
            print(f"  Graph Keys Used: {path_keys}")
             # Calculate base path duration by summing weights (excluding penalty)
            base_path_duration = graph_time_no_walk - total_penalty 
            print(f"  Base Path Duration (sum of edge weights): {base_path_duration:.2f} mins")
            print(f"  Calculated Penalty: {total_penalty:.2f} mins")
            print(f"  Graph Time (excl. walk): {graph_time_no_walk:.2f} mins")
            print(f"  GRAPH TOTAL TIME (incl. walk): {graph_total_time:.2f} mins")
            
        # --- TfL API Calculation ---
        print("\nCalculating TfL API Time...")
        # Get station data (including ID) directly from the graph-based lookup
        start_station_data = station_data_lookup.get(start_station)
        end_station_data = station_data_lookup.get(end_station)

        # --- Add check for missing station data before proceeding ---
        tfl_total_time = None # Initialize to None
        tfl_journey = None    # Initialize to None
        proceed_with_tfl = True # Flag to control API call

        if not start_station_data:
            print(f"  Error: Could not find station data in graph lookup for START station '{start_station}'")
            proceed_with_tfl = False
        if not end_station_data:
             print(f"  Error: Could not find station data in graph lookup for END station '{end_station}'")
             proceed_with_tfl = False

        if proceed_with_tfl:
             # Extract IDs for TfL API call based on the refined logic
             start_primary_id = start_station_data.get('primary_naptan_id')
             # Use the CORRECT key 'constituent_stations'
             start_constituents = start_station_data.get('constituent_stations', []) 
             end_primary_id = end_station_data.get('primary_naptan_id')
             # Use the CORRECT key 'constituent_stations'
             end_constituents = end_station_data.get('constituent_stations', [])   
             
             start_naptan_id = None
             end_naptan_id = None

             # Determine Start Naptan ID
             if start_primary_id and not start_primary_id.startswith("HUB"):
                 start_naptan_id = start_primary_id
             # Use the corrected key 'constituent_stations'
             elif start_constituents and isinstance(start_constituents, list) and len(start_constituents) > 0:
                 # Check first element is dict and has the naptan_id key
                 if isinstance(start_constituents[0], dict) and 'naptan_id' in start_constituents[0]:
                      start_naptan_id = start_constituents[0]['naptan_id']
             
             # Determine End Naptan ID
             if end_primary_id and not end_primary_id.startswith("HUB"):
                 end_naptan_id = end_primary_id
             # Use the corrected key 'constituent_stations'
             elif end_constituents and isinstance(end_constituents, list) and len(end_constituents) > 0:
                 # Check first element is dict and has the naptan_id key
                 if isinstance(end_constituents[0], dict) and 'naptan_id' in end_constituents[0]:
                      end_naptan_id = end_constituents[0]['naptan_id']

             # Validate that we successfully determined both IDs
             if not start_naptan_id:
                 print(f"  Error: Could not determine valid Naptan ID for START station '{start_station}' (Primary: {start_primary_id}, Constituents: {start_constituents})")
                 proceed_with_tfl = False
             if not end_naptan_id:
                 print(f"  Error: Could not determine valid Naptan ID for END station '{end_station}' (Primary: {end_primary_id}, Constituents: {end_constituents})")
                 proceed_with_tfl = False

        # Only call API if we have valid Naptan IDs
        if proceed_with_tfl:
                print(f"  Using Naptan IDs: Start={start_naptan_id}, End={end_naptan_id}")
                # Call TfL API with Naptan IDs
                tfl_journey = get_journey_details_tfl(start_naptan_id, end_naptan_id, api_key)

        # Check tfl_journey which is now the source for duration
        if tfl_journey is None:
             print("  TfL Time: Could not retrieve journey details.")
                 # tfl_total_time remains None
        else:
            tfl_duration = tfl_journey.get('duration')
            if tfl_duration is None:
                 print("  TfL Time: Journey retrieved but duration missing.")
                     # tfl_total_time remains None 
            else:
                tfl_total_time = tfl_duration + walk_time # Calculate total time here
                print(f"  TfL Duration (excl. walk): {tfl_duration} mins")
                print(f"  TFL TOTAL TIME (incl. walk): {tfl_total_time} mins")
                    # Print Journey Legs (only if journey details were successfully retrieved)
                print("  TfL Journey Breakdown:")
                legs = tfl_journey.get('legs', [])
                if not legs:
                    print("    No legs information available.")
                else:
                    for i, leg in enumerate(legs):
                        instruction = leg.get('instruction', {}).get('summary', 'No instruction')
                        mode = leg.get('mode', {}).get('name', 'unknown mode')
                        duration = leg.get('duration', 0)
                        # Add line identifier if available
                        line_id = 'N/A' # Default
                        if leg.get('routeOptions'):
                            line_info = leg['routeOptions'][0].get('lineIdentifier')
                            if line_info:
                                line_id = line_info.get('id', 'N/A')
                                    
                        print(f"    {i+1}. ({mode}, line: {line_id}, {duration} min): {instruction}")

        # --- Summary ---
        print("\nComparison Summary:")
        print(f"  Graph Total: {graph_total_time:.2f} mins" if graph_total_time != float('inf') else "  Graph Total: N/A (Path not found)")
        print(f"  TfL Total:   {tfl_total_time} mins" if tfl_total_time is not None else "  TfL Total:   N/A (API error or no journey)")

        # Check graph time is finite and tfl_total_time is not None before comparing
        if graph_total_time != float('inf') and tfl_total_time is not None:
            diff = tfl_total_time - graph_total_time
            # Ensure graph_total_time is positive before calculating ratio
            if graph_total_time > 0:
                ratio = tfl_total_time / graph_total_time
                print(f"  Difference (TfL - Graph): {diff:.2f} mins")
                print(f"  Ratio (TfL / Graph): {ratio:.2f}")
            else: # Handle case where graph time is 0 (e.g. same station)
                 print(f"  Difference (TfL - Graph): {diff:.2f} mins")
                 print(f"  Ratio (TfL / Graph): Undefined (Graph time is zero)")
        else:
            print("  Could not compare times fully.")
            
        print("="*80)


if __name__ == "__main__":
    main() 