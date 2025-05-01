import json
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Define file paths
OUTPUT_DIR = 'networkx_graph/graph_data'
OLD_GRAPH_PATH = os.path.join(OUTPUT_DIR, 'networkx_graph_hubs_base.json')
NEW_GRAPH_PATH = os.path.join(OUTPUT_DIR, 'networkx_graph_hubs_basev2.json')

def load_json_graph(filepath):
    """Loads graph data from a JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {filepath}: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred loading {filepath}: {e}")
        return None

def compare_graphs(old_data, new_data):
    """Compares the two graph data dictionaries, focusing on differences.
    Returns True if they are identical except for constituent representation, False otherwise.
    """
    identical_except_constituents = True
    differences = []

    # 1. Compare graph-level attributes (directed, multigraph, graph dict)
    for key in ["directed", "multigraph", "graph"]:
        if old_data.get(key) != new_data.get(key):
            differences.append(f"Graph attribute '{key}' differs: Old=\"{old_data.get(key)}\" New=\"{new_data.get(key)}\"")
            identical_except_constituents = False

    # 2. Compare Nodes
    old_nodes_list = old_data.get('nodes', [])
    new_nodes_list = new_data.get('nodes', [])

    # Create dictionaries for easier lookup by node id (hub_name)
    old_nodes_dict = {node['id']: node for node in old_nodes_list if isinstance(node, dict) and 'id' in node}
    new_nodes_dict = {node['id']: node for node in new_nodes_list if isinstance(node, dict) and 'id' in node}

    old_node_ids = set(old_nodes_dict.keys())
    new_node_ids = set(new_nodes_dict.keys())

    if old_node_ids != new_node_ids:
        differences.append("Node sets differ.")
        if missing_in_new := old_node_ids - new_node_ids:
            differences.append(f"  Nodes missing in new graph: {missing_in_new}")
        if missing_in_old := new_node_ids - old_node_ids:
            differences.append(f"  Nodes added in new graph: {missing_in_old}")
        identical_except_constituents = False
    else:
        logging.info(f"Node sets are identical ({len(old_node_ids)} nodes). Comparing attributes...")
        # Compare attributes for common nodes
        for node_id in old_node_ids:
            old_node = old_nodes_dict[node_id]
            new_node = new_nodes_dict[node_id]

            # Compare all attributes EXCEPT the constituent lists
            old_attrs_filtered = {k: v for k, v in old_node.items() if k != 'constituent_naptan_ids'}
            new_attrs_filtered = {k: v for k, v in new_node.items() if k != 'constituent_stations'}

            # Sort lists within attributes for consistent comparison
            for key in ['modes', 'lines']:
                if key in old_attrs_filtered and isinstance(old_attrs_filtered[key], list):
                    old_attrs_filtered[key].sort()
                if key in new_attrs_filtered and isinstance(new_attrs_filtered[key], list):
                    new_attrs_filtered[key].sort()

            if old_attrs_filtered != new_attrs_filtered:
                differences.append(f"Node '{node_id}' attributes differ (excluding constituents).")
                # Log specific differences for debugging
                for key in old_attrs_filtered:
                    if key not in new_attrs_filtered:
                        differences.append(f"  - Key '{key}' missing in new node.")
                    elif old_attrs_filtered[key] != new_attrs_filtered[key]:
                        differences.append(f"  - Key '{key}': Old=\"{old_attrs_filtered[key]}\" != New=\"{new_attrs_filtered[key]}\"")
                for key in new_attrs_filtered:
                    if key not in old_attrs_filtered:
                        differences.append(f"  - Key '{key}' added in new node.")
                identical_except_constituents = False

            # Compare constituent data
            old_constituents = sorted(old_node.get('constituent_naptan_ids', []))
            new_constituent_data = new_node.get('constituent_stations', [])
            # Extract and sort Naptan IDs from the new structure
            new_constituent_ids = sorted([item.get('naptan_id') for item in new_constituent_data if isinstance(item, dict) and 'naptan_id' in item])

            if old_constituents != new_constituent_ids:
                differences.append(f"Node '{node_id}' constituent Naptan IDs differ.")
                differences.append(f"  - Old IDs: {old_constituents}")
                differences.append(f"  - New IDs: {new_constituent_ids}")
                identical_except_constituents = False

            # Check for unexpected keys
            if 'constituent_stations' in old_node:
                differences.append(f"Node '{node_id}' in OLD graph unexpectedly contains 'constituent_stations' key.")
                identical_except_constituents = False
            if 'constituent_naptan_ids' in new_node:
                differences.append(f"Node '{node_id}' in NEW graph unexpectedly contains 'constituent_naptan_ids' key.")
                identical_except_constituents = False

    # 3. Compare Edges
    # Use the key specified during saving ('edges')
    old_edges = old_data.get('edges', [])
    new_edges = new_data.get('edges', [])

    if len(old_edges) != len(new_edges):
        differences.append(f"Edge counts differ: Old={len(old_edges)}, New={len(new_edges)}")
        identical_except_constituents = False
    else:
        logging.info(f"Edge counts are identical ({len(old_edges)} edges). Comparing edge data...")
        # Create comparable representations for edges
        # Convert edge dict to a tuple of sorted items for comparison
        def edge_to_comparable(edge):
            # Handle potential variations in weight being None vs. not present
            # Standardize weight to None if it's not a number
            if 'weight' in edge and not isinstance(edge['weight'], (int, float)):
                 edge['weight'] = None # Or remove: del edge['weight'] depending on desired comparison
                 
            # Convert the dictionary to a tuple of sorted key-value pairs
            return tuple(sorted(edge.items()))

        try:
            # Create sets of comparable edge representations
            old_edge_set = {edge_to_comparable(edge) for edge in old_edges}
            new_edge_set = {edge_to_comparable(edge) for edge in new_edges}

            if old_edge_set != new_edge_set:
                differences.append("Edge sets differ.")
                if missing_in_new_edges := old_edge_set - new_edge_set:
                    differences.append(f"  Edges missing in new graph: {missing_in_new_edges}")
                if missing_in_old_edges := new_edge_set - old_edge_set:
                    differences.append(f"  Edges added in new graph: {missing_in_old_edges}")
                identical_except_constituents = False
        except Exception as e:
            differences.append(f"Error comparing edge sets: {e}")
            identical_except_constituents = False

    # 4. Report Results
    if identical_except_constituents:
        logging.info("Graphs are identical except for the expected change in constituent station representation.")
    else:
        logging.error("Graphs differ in ways other than the constituent station representation:")
        for diff in differences:
            logging.error(f"- {diff}")

    return identical_except_constituents

# --- Main Execution ---
if __name__ == "__main__":
    logging.info(f"Comparing {OLD_GRAPH_PATH} and {NEW_GRAPH_PATH}...")

    old_graph_data = load_json_graph(OLD_GRAPH_PATH)
    new_graph_data = load_json_graph(NEW_GRAPH_PATH)

    if old_graph_data and new_graph_data:
        compare_graphs(old_graph_data, new_graph_data)
    else:
        logging.error("Comparison aborted due to file loading errors.") 