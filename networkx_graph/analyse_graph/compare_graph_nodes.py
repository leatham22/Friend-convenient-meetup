"""
Compares the set of nodes (stations/hubs) between two NetworkX graph files
stored in node-link JSON format.

Identifies nodes present in one graph but not the other.
"""

import logging
import os
import sys

# Import the specific function from graph_utils
try:
    # Assumes graph_utils.py is in the same directory
    # Import both loading functions
    from graph_utils import load_node_link_graph, load_graph_from_json
except ImportError:
    logging.error("Failed to import loading functions from graph_utils.py. Ensure it exists in the same directory.")
    sys.exit(1)

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get the directory where the current script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define paths relative to the script's directory
# Go up one level from script dir (analyse_graph) to networkx_graph, then into graph_data
GRAPH_DATA_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "graph_data"))
LEGACY_GRAPH_FILE = os.path.join(GRAPH_DATA_ROOT, "legacy_data", "networkx_graph_new.json") # Your older graph file
NEW_GRAPH_FILE = os.path.join(GRAPH_DATA_ROOT, "networkx_graph_hubs_base.json") # Your newer hub graph file

# Check if files exist (optional but good for debugging)
if not os.path.exists(LEGACY_GRAPH_FILE):
    logging.warning(f"Legacy graph file not found at resolved path: {LEGACY_GRAPH_FILE}")
if not os.path.exists(NEW_GRAPH_FILE):
    logging.warning(f"New graph file not found at resolved path: {NEW_GRAPH_FILE}")

# --- Main Comparison Logic ---

def compare_nodes(file1, file2):
    """
    Loads two graphs and compares their node sets.

    Args:
        file1 (str): Path to the first graph file (node-link JSON).
        file2 (str): Path to the second graph file (node-link JSON).
    """
    logging.info(f"Loading graph 1 (legacy): {file1}")
    # Load the first graph (legacy) using the custom JSON loader
    g1 = load_graph_from_json(file1)
    if g1 is None:
        logging.error(f"Failed to load graph from {file1}. Exiting.")
        return

    logging.info(f"Loading graph 2 (new hub): {file2}")
    # Load the second graph (new hub graph) using the node-link loader
    g2 = load_node_link_graph(file2)
    if g2 is None:
        logging.error(f"Failed to load graph from {file2}. Exiting.")
        return

    logging.info("Comparing node sets...")

    # Get the set of node names (stations/hubs) from each graph
    nodes1 = set(g1.nodes())
    nodes2 = set(g2.nodes())

    # Find nodes unique to the first graph (present in legacy, missing in new by name)
    nodes_only_in_1_by_name = nodes1 - nodes2
    # Find nodes unique to the second graph (present in new, missing in legacy by name)
    # This comparison remains the same, as new hubs shouldn't map back to legacy in this way
    nodes_only_in_2 = nodes2 - nodes1

    # --- Refined check for nodes missing from Graph 2 (New Hub Graph) ---
    logging.info("Performing refined check for nodes missing from new hub graph...")
    # Create a set of all constituent Naptan IDs from the new hub graph for efficient lookup
    all_constituent_ids_in_g2 = set()
    for hub_node, hub_data in g2.nodes(data=True):
        # Ensure constituent_naptan_ids exists and is iterable
        ids = hub_data.get('constituent_naptan_ids')
        if ids and isinstance(ids, list):
            all_constituent_ids_in_g2.update(ids)
        elif ids: # Handle case if it's present but not a list (log warning)
            logging.warning(f"Hub {hub_node} has non-list 'constituent_naptan_ids': {type(ids)}. Skipping.")

    # Now, check if nodes from G1 are truly missing or just absorbed into a hub in G2
    truly_missing_from_g2 = []
    for node_name in nodes_only_in_1_by_name:
        # Attempt to get the Naptan ID from the legacy node
        # *** Assuming the Naptan ID attribute in the legacy graph is 'id' ***
        legacy_node_data = g1.nodes.get(node_name, {})
        legacy_naptan_id = legacy_node_data.get('id') # <-- Check this attribute name if issues arise

        if legacy_naptan_id:
            # Check if this ID is part of any hub in G2
            if legacy_naptan_id not in all_constituent_ids_in_g2:
                # If the ID is not found in any constituent list, it's truly missing
                truly_missing_from_g2.append(node_name)
            # else: Node is represented within a hub in G2, so not truly missing
        else:
            # If the legacy node doesn't have an 'id' attribute, we can't check constituents
            # We'll keep it in the list as potentially missing based on name
            logging.warning(f"Node '{node_name}' from {os.path.basename(file1)} lacks an 'id' attribute for constituent check. Reporting based on name.")
            truly_missing_from_g2.append(node_name)


    logging.info("-" * 40)
    # Report nodes present in the first file but not the second (refined check)
    if truly_missing_from_g2:
        logging.info(f"Nodes present ONLY in {os.path.basename(file1)} (and not absorbed into hubs in {os.path.basename(file2)}) ({len(truly_missing_from_g2)}):")
        # Print sorted list for easier reading
        for node in sorted(truly_missing_from_g2):
            logging.info(f"  - {node}")
    else:
        logging.info(f"All nodes from {os.path.basename(file1)} are either present by name or absorbed into hubs in {os.path.basename(file2)}.")

    logging.info("-" * 40)
    logging.info("Comparison complete.")

# --- Script Execution ---
if __name__ == "__main__":
    # Run the comparison function with the configured file paths
    compare_nodes(LEGACY_GRAPH_FILE, NEW_GRAPH_FILE) 