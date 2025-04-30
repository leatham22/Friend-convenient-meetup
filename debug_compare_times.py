import json
import networkx as nx
import heapq
import requests
import os
import sys
import math
from dotenv import load_dotenv

# --- Configuration ---
GRAPH_PATH = "networkx_graph/graph_data/networkx_graph_new.json"
TFL_API_BASE_URL = "https://api.tfl.gov.uk/Journey/JourneyResults/"
# STATION_DATA_PATH = "slim_stations/unique_stations.json" # No longer needed

# --- Helper Functions (Adapted from main.py) ---

def load_networkx_graph_and_station_data():
    """Loads the NetworkX graph and extracts station data (attributes) from nodes."""
    try:
        with open(GRAPH_PATH, 'r') as f:
            graph_data = json.load(f)

        G = nx.MultiDiGraph()
        station_data_lookup = {}

        # Add nodes and populate lookup
        if 'nodes' in graph_data and isinstance(graph_data['nodes'], dict):
            for node_name, attributes in graph_data['nodes'].items():
                # Ensure attributes is a dict before adding node and data
                if isinstance(attributes, dict):
                    G.add_node(node_name, **attributes)
                    # Store all attributes in the lookup, keyed by node name
                    station_data_lookup[node_name] = attributes
                else:
                    # Add node even if attributes are missing/malformed, but don't add to lookup
                    G.add_node(node_name)
                    print(f"Warning: Node '{node_name}' has unexpected attribute format: {attributes}")
        else:
            print("Warning: 'nodes' key not found or not a dictionary in graph data.")

        # Add edges (logic remains the same)
        if 'edges' in graph_data and isinstance(graph_data['edges'], list):
            for edge in graph_data['edges']:
                if isinstance(edge, dict) and 'source' in edge and 'target' in edge:
                    source = edge.pop('source')
                    target = edge.pop('target')
                    key = edge.pop('key', None)
                    # Ensure source and target nodes exist before adding edge
                    if G.has_node(source) and G.has_node(target):
                        G.add_edge(source, target, key=key, **edge)
                    else:
                        print(f"Warning: Skipping edge due to missing node(s): {source} -> {target}")
                else:
                    print(f"Warning: Skipping invalid edge format: {edge}")
        else:
            print("Warning: 'edges' key not found or not a list in graph data.")

        print(f"Loaded NetworkX graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
        print(f"Created station data lookup for {len(station_data_lookup)} stations from graph nodes.")
        # Return both the graph and the lookup dictionary
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

            for edge_index, edge_data in edge_datas.items():
                edge_duration = edge_data.get('duration', float('inf'))
                current_edge_line_key = edge_index 

                if edge_duration == float('inf') or current_edge_line_key is None:
                    continue

                penalty = 0.0
                if (previous_line_key is not None and 
                    current_edge_line_key != previous_line_key and
                    previous_line_key != 'transfer' and 
                    current_edge_line_key != 'transfer'):
                    penalty = 5.0 

                new_time = current_time + edge_duration + penalty
                neighbor_state = (neighbor_station, current_edge_line_key)

                if new_time < distances.get(neighbor_state, float('inf')):
                    distances[neighbor_state] = new_time
                    heapq.heappush(pq, (new_time, neighbor_station, current_edge_line_key))
                    # Store predecessor info for path reconstruction
                    predecessors[neighbor_state] = (current_station, previous_line_key, edge_duration, penalty)

    # Path Reconstruction
    if final_state_at_destination:
        path_nodes = []
        path_keys = []
        total_penalty = 0.0
        
        curr = final_state_at_destination
        while curr in predecessors:
            prev_station, prev_line_key, edge_dur, penalty = predecessors[curr]
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
                            duration = data.get('duration')
                            if duration is None:
                                print("        -> Duration: MISSING or None")
                            elif isinstance(duration, (int, float)):
                                print(f"        -> Duration: {duration} (Valid type)")
                            else:
                                print(f"        -> Duration: {duration} (INVALID TYPE: {type(duration)})")
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
                                     nn_duration = nn_data.get('duration')
                                     if nn_duration is None:
                                         print("        -> Duration: MISSING or None")
                                     elif isinstance(nn_duration, (int, float)):
                                         print(f"        -> Duration: {nn_duration} (Valid type)")
                                     else:
                                         print(f"        -> Duration: {nn_duration} (INVALID TYPE: {type(nn_duration)})")
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
            print(f"  Base Path Duration (sum of edge weights): {graph_time_no_walk - total_penalty:.2f} mins")
            print(f"  Calculated Penalty: {total_penalty:.2f} mins")
            print(f"  Graph Time (excl. walk): {graph_time_no_walk:.2f} mins")
            print(f"  GRAPH TOTAL TIME (incl. walk): {graph_total_time:.2f} mins")
            
        # --- TfL API Calculation ---
        print("\nCalculating TfL API Time...")
        # Get station data (including ID) directly from the graph-based lookup
        start_station_data = station_data_lookup.get(start_station)
        end_station_data = station_data_lookup.get(end_station)

        if not start_station_data or not end_station_data:
            print(f"  Error: Could not find station data in graph nodes for '{start_station}' or '{end_station}'")
            tfl_total_time = None
            tfl_journey = None
        else:
            # Extract Naptan ID from the node attributes
            # Ensure the 'id' key exists in the attributes dictionary
            start_naptan_id = start_station_data.get('id')
            end_naptan_id = end_station_data.get('id')

            if not start_naptan_id or not end_naptan_id:
                print(f"  Error: Missing Naptan ID attribute ('id') in graph node data for '{start_station}' (Data: {start_station_data}) or '{end_station}' (Data: {end_station_data})")
                tfl_total_time = None
                tfl_journey = None
            else:
                print(f"  Using Naptan IDs: Start={start_naptan_id}, End={end_naptan_id}")
                # Call TfL API with Naptan IDs
                tfl_journey = get_journey_details_tfl(start_naptan_id, end_naptan_id, api_key)

        # Check tfl_journey which is now the source for duration
        if tfl_journey is None:
             print("  TfL Time: Could not retrieve journey details.")
             tfl_total_time = None # Ensure total time is None if journey failed
        else:
            tfl_duration = tfl_journey.get('duration')
            if tfl_duration is None:
                 print("  TfL Time: Journey retrieved but duration missing.")
                 tfl_total_time = None # Handle missing duration in response
            else:
                tfl_total_time = tfl_duration + walk_time
                print(f"  TfL Duration (excl. walk): {tfl_duration} mins")
                print(f"  TFL TOTAL TIME (incl. walk): {tfl_total_time} mins")
                # Print Journey Legs (remains the same, uses tfl_journey)
                print("  TfL Journey Breakdown:")
                legs = tfl_journey.get('legs', [])
                if not legs:
                    print("    No legs information available.")
                else:
                    for i, leg in enumerate(legs):
                        instruction = leg.get('instruction', {}).get('summary', 'No instruction')
                        mode = leg.get('mode', {}).get('name', 'unknown mode')
                        duration = leg.get('duration', 0)
                        print(f"    {i+1}. ({mode}, {duration} min): {instruction}")

        # --- Summary ---
        print("\nComparison Summary:")
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