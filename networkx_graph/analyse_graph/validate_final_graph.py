"""
File: networkx_graph/analyse_graph/validate_final_graph.py
Description: Performs validation checks on the final NetworkX graph 
             (networkx_graph_hubs_final.json).
Checks performed:
1. Basic Graph Info: Number of nodes and edges.
2. Edge Type Counts: Counts edges by key ('transfer' or line name for routes).
3. Transfer Edge Weights: Checks how many transfer edges have None vs. valid weights.
4. Graph Connectivity: Checks if the graph is weakly connected (explained).
5. Node Attribute Presence: Verifies essential attributes (excluding id, zone) exist for all nodes.
6. Edge Attribute Presence: Verifies essential attributes exist for relevant edges.
   - Lists route edges missing the 'line' attribute.
"""

import networkx as nx
import json
import os
import sys
import logging
from collections import Counter, defaultdict

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Attempt to import the loading function from the utility script in the same directory
try:
    # Assumes graph_utils.py is in the same directory or Python path
    from graph_utils import load_node_link_graph 
except ImportError as e:
    logging.error(f"Failed to import 'load_node_link_graph' from 'graph_utils.py'. Ensure it's accessible.")
    logging.error(f"Import error: {e}")
    sys.exit(1)

# --- Configuration ---
# Define the path to the final graph file relative to this script's location
FINAL_GRAPH_FILE = "../create_graph/output/final_networkx_graph.json"

# --- Main Validation Logic ---
def validate_graph(graph_filepath):
    """
    Loads the graph and performs validation checks.
    Args:
        graph_filepath (str): The path to the graph JSON file.
    """
    logging.info(f"--- Starting Validation for Graph: {graph_filepath} ---")

    # --- Load the Graph ---
    G = load_node_link_graph(graph_filepath)
    if G is None:
        logging.error("Graph loading failed. Aborting validation.")
        return

    # Ensure G is a MultiDiGraph, as expected from previous steps
    if not isinstance(G, nx.MultiDiGraph):
        logging.warning(f"Loaded graph is not a MultiDiGraph ({type(G)}). Edge checks might behave unexpectedly.")

    # --- Check 1: Basic Graph Info ---
    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()
    logging.info("[Check 1: Basic Info]")
    logging.info(f" - Number of nodes: {num_nodes}")
    logging.info(f" - Number of edges: {num_edges}")
    if num_nodes == 0 or num_edges == 0:
        logging.warning("Graph is empty. Stopping validation.")
        return

    # --- Check 2: Edge Type Counts (based on Key) ---
    logging.info("[Check 2: Edge Counts by Key (Type)]")
    # For MultiDiGraph, G.edges includes keys by default
    edge_key_counts = Counter(k for u, v, k in G.edges(keys=True))
    transfer_edges_count_key = edge_key_counts.get('transfer', 0)
    route_edges_count_key = num_edges - transfer_edges_count_key
    
    logging.info(f" - Transfer edges: {transfer_edges_count_key}")
    logging.info(f" - Adjacent station travel edges: {route_edges_count_key}")
    logging.info(f"   - Unique route keys (lines): {len(edge_key_counts) - (1 if 'transfer' in edge_key_counts else 0)}")
    # Example route keys:
    route_keys_example = [k for k in edge_key_counts if k != 'transfer'][:5]
    logging.info(f"   - Example route keys: {route_keys_example} ...")

    # --- Check 3: Transfer Edge Weights --- 
    logging.info("[Check 3: Transfer Edge Weights]")
    transfer_edges_checked_count = 0
    transfer_edges_none_weight = 0
    transfer_edges_with_weight = 0
    transfer_edges_missing_weight_attr = 0

    # Iterate through edges using the key to identify transfers
    for u, v, k, data in G.edges(keys=True, data=True):
        if k == 'transfer': # Correctly identify transfer edges by key
            transfer_edges_checked_count += 1
            if 'weight' not in data:
                transfer_edges_missing_weight_attr += 1
                logging.debug(f"Transfer edge ({u} -> {v}, key={k}) missing 'weight' attribute.")
            elif data['weight'] is None:
                transfer_edges_none_weight += 1
            else:
                transfer_edges_with_weight += 1
    
    # Check if the number checked matches the count from Check 2
    if transfer_edges_checked_count != transfer_edges_count_key:
         logging.warning(f"Mismatch: Counted {transfer_edges_count_key} edges with key='transfer' but checked {transfer_edges_checked_count} for weight.")
    
    # Report findings
    logging.info(f" - Checked {transfer_edges_checked_count} transfer edges:")
    if transfer_edges_checked_count > 0:
        logging.info(f"   - With a valid weight value: {transfer_edges_with_weight}")
        logging.info(f"   - With weight explicitly set to None: {transfer_edges_none_weight}")
        if transfer_edges_missing_weight_attr > 0:
            logging.warning(f"   - Missing the 'weight' attribute entirely: {transfer_edges_missing_weight_attr}")
        # Sanity check
        if transfer_edges_none_weight + transfer_edges_with_weight + transfer_edges_missing_weight_attr != transfer_edges_checked_count:
            logging.warning("Discrepancy noted in transfer edge weight counting!")
    else:
        logging.info(" - No edges with key='transfer' found.")

    # --- Check 4: Connectivity (Checking for Stranded Stations/Sections) ---
    logging.info("[Check 4: Stranded Stations Check]")
    try:
        # This checks if the entire network is one single piece, 
        # ensuring no stations or sections are completely isolated.
        # It ignores the direction of travel for this check.
        # A value of 'True' means NO stranded stations were found.
        is_one_piece = nx.is_weakly_connected(G)
        logging.info(f" - Are there any stranded stations or isolated sections? No (Result={is_one_piece})")
        if not is_one_piece:
            num_components = nx.number_weakly_connected_components(G)
            logging.warning(f"   - WARNING: Found {num_components} separate, unconnected sections in the network.")
    except Exception as e:
        logging.error(f"Could not perform stranded stations check: {e}")

    # --- Check 5: Node Attribute Presence ---
    logging.info("[Check 5: Node Attributes Presence]")
    # 'id' is the node identifier itself, not an attribute in the data dict after loading.
    # 'zone' check removed as requested.
    essential_node_attrs = ['primary_naptan_id', 'constituent_stations', 'lat', 'lon', 'modes', 'lines', 'hub_name']
    nodes_missing_attrs_summary = Counter()
    nodes_failing_checks = defaultdict(list) # Store nodes failing specific checks
    checked_nodes_count = 0

    for node_id, data in G.nodes(data=True):
        checked_nodes_count += 1
        for attr in essential_node_attrs:
            missing = False
            # Check if key exists
            if attr not in data:
                missing = True
            # Check if value is None (excluding 'zone', which we removed)
            elif data[attr] is None:
                 missing = True
            # Add check for empty lists for attributes that should be lists
            elif isinstance(data[attr], list) and not data[attr]:
                # Flag attributes like modes, lines, constituent_stations if they are empty lists
                if attr in ['modes', 'lines', 'constituent_stations']:
                    missing = True
                    attr = f"{attr}_isEmptyList" # Use a distinct key for reporting empty lists

            if missing:
                 nodes_missing_attrs_summary[attr] += 1
                 nodes_failing_checks[attr].append(node_id)
    
    logging.info(f" - Checked {checked_nodes_count}/{num_nodes} nodes for essential attributes presence.")
    if not nodes_missing_attrs_summary:
        logging.info(" - All nodes appear to have all essential attributes (checked: {', '.join(essential_node_attrs)}). Empty lists flagged if found.")
    else:
        logging.warning(f" - Found nodes missing essential attributes (checked: {', '.join(essential_node_attrs)}):")
        for attr, count in nodes_missing_attrs_summary.items():
             logging.warning(f"   - Nodes missing/None/Empty '{attr}': {count}")
             # List nodes failing the check (limit list size for brevity)
             limit = 5
             failing_nodes_example = nodes_failing_checks[attr][:limit]
             if count > 0:
                 logging.warning(f"     - Examples: {failing_nodes_example}{'...' if count > limit else ''}")

    # --- Check 6: Edge Attribute Presence --- 
    logging.info("[Check 6: Edge Attributes Presence]")
    route_edges_missing_line_attr = 0 # Check for the 'line' attribute itself
    route_edges_line_is_none_or_empty = 0 # Check if 'line' value is bad
    route_edges_checked = 0
    failing_route_edges = []
    other_key_edges_checked = 0
    
    if num_edges > 0:
        for u, v, k, data in G.edges(keys=True, data=True):
            # Check Route Edges (key != 'transfer')
            if k != 'transfer': 
                route_edges_checked += 1
                # Check for presence of 'line' attribute
                if 'line' not in data: 
                    route_edges_missing_line_attr += 1
                    logging.debug(f"Route edge ({u} -> {v}, key={k}) missing 'line' attribute.")
                    if len(failing_route_edges) < 5: failing_route_edges.append((u, v, k))
                # Check if 'line' attribute is None or empty string
                elif not data['line']: 
                    route_edges_line_is_none_or_empty += 1
                    logging.debug(f"Route edge ({u} -> {v}, key={k}) has None or empty 'line' attribute.")
                    if len(failing_route_edges) < 5: failing_route_edges.append((u, v, k))
            # Transfer edges checked in Check 3
            elif k == 'transfer':
                 pass # Already handled
            else:
                 # This case should not be reached if keys are either 'transfer' or line names
                 other_key_edges_checked += 1

        # Report findings for route edges
        logging.info(f" - Checked {route_edges_checked} adjacent station travel edges:")
        if route_edges_missing_line_attr == 0 and route_edges_line_is_none_or_empty == 0:
            logging.info("   - All route edges seem to have a valid 'line' attribute.")
        else:
            if route_edges_missing_line_attr > 0:
                 logging.warning(f"   - Route edges MISSING 'line' attribute: {route_edges_missing_line_attr}")
            if route_edges_line_is_none_or_empty > 0:
                 logging.warning(f"   - Route edges with None/Empty 'line' attribute: {route_edges_line_is_none_or_empty}")
            logging.warning(f"     - Examples: {failing_route_edges} ...")
            
        if other_key_edges_checked > 0:
            logging.warning(f" - Found {other_key_edges_checked} edges with unexpected keys (neither 'transfer' nor line name?).")
    else:
        logging.info(" - Skipping edge attribute check (graph has no edges).")

    logging.info("--- Validation Script Finished ---")

# --- Script Execution ---
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Ensure the path correctly points to the graph data directory relative to this script
    graph_file_path = os.path.abspath(os.path.join(script_dir, FINAL_GRAPH_FILE))

    if not os.path.exists(graph_file_path):
         logging.error(f"FATAL: Graph file not found at: {graph_file_path}")
         logging.error("Please ensure the path in the script is correct relative to the script's location.")
         sys.exit(1)

    validate_graph(graph_file_path) 