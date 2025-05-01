"""
This script updates the weights of the edges in the graph with the calculated weights.
It uses the calculated_hub_edge_weights.json file to update the weights of the edges in the graph.
The output is saved to the networkx_graph_hubs_final_weighted.json file.
"""

import json
import networkx as nx
from networkx.readwrite import json_graph
import os

def load_json_data(file_path):
    """Loads data from a JSON file."""
    # Explain: This function opens and reads a JSON file specified by file_path.
    # Explain: It uses a 'with' statement to ensure the file is properly closed even if errors occur.
    # Explain: json.load() parses the JSON data from the file object into a Python object (dict or list).
    # Explain: Returns the loaded Python object.
    print(f"Loading JSON data from: {file_path}")
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        print(f"Successfully loaded data from {file_path}")
        return data
    except FileNotFoundError:
        # Explain: Handles the case where the specified file does not exist.
        print(f"Error: File not found at {file_path}")
        return None
    except json.JSONDecodeError:
        # Explain: Handles the case where the file is not valid JSON.
        print(f"Error: Could not decode JSON from {file_path}")
        return None
    except Exception as e:
        # Explain: Catches any other unexpected errors during file loading.
        print(f"An unexpected error occurred while loading {file_path}: {e}")
        return None

def create_weights_lookup(weights_data):
    """Creates a lookup dictionary for edge weights."""
    # Explain: This function transforms the list of edge weight dictionaries into a lookup dictionary.
    # Explain: This makes finding the weight for a specific edge much faster later on.
    print("Creating lookup dictionary for calculated edge weights...")
    lookup = {}
    # Explain: Iterates through each edge dictionary in the input list weights_data.
    for edge_data in weights_data:
        # Explain: Extracts the source node ('source'), target node ('target'), and line information from the weights file.
        # Explain: Corrected keys from 'u'/'v' to 'source'/'target' to match the calculated_hub_edge_weights.json structure.
        u = edge_data.get('source')
        v = edge_data.get('target')
        line = edge_data.get('line')
        weight = edge_data.get('weight')

        # Explain: Checks if all necessary keys (source, target, line, weight) are present in the dictionary.
        if u is not None and v is not None and line is not None and weight is not None:
            # Explain: Creates a unique key for the edge using a tuple (source, target, line). Tuples are hashable and can be used as dictionary keys.
            key = (u, v, line)
            # Explain: Checks if this edge key already exists in the lookup. This helps identify potential duplicate edge definitions in the weights data.
            if key in lookup:
                print(f"Warning: Duplicate edge found in weights data for key {key}. Overwriting weight.")
            # Explain: Stores the weight in the lookup dictionary with the edge tuple as the key.
            lookup[key] = weight
        else:
            # Explain: Prints a warning if an edge dictionary is missing required information.
            print(f"Warning: Skipping edge data due to missing keys: {edge_data}")
    print(f"Created lookup with {len(lookup)} entries.")
    return lookup

def update_graph_edge_weights(graph_path, weights_path, output_path):
    """Loads graph, updates non-transfer edge weights, and saves the updated graph."""
    # Explain: This is the main function coordinating the process.
    # Explain: It takes paths for the input graph, weights file, and the desired output file.

    # --- Load Graph Data ---
    # Explain: Loads the graph structure from the specified JSON file using the load_json_data helper function.
    graph_data = load_json_data(graph_path)
    if graph_data is None:
        print("Failed to load graph data. Exiting.")
        return # Explain: Exits the function if graph loading failed.

    # Explain: Parses the loaded JSON data into a NetworkX MultiDiGraph object.
    # Explain: MultiDiGraph is used because the original graph allows multiple edges between the same nodes (e.g., different lines).
    print("Parsing graph data into NetworkX MultiDiGraph...")
    try:
        # Explain: Explicitly set edges='edges' to match the key used in the JSON file for the edge list.
        # Explain: This resolves the KeyError and addresses the FutureWarning.
        G = json_graph.node_link_graph(graph_data, edges="edges")
        print("Successfully parsed graph data.")
    except Exception as e:
        print(f"Error parsing graph data into NetworkX graph: {e}")
        return # Explain: Exits if parsing fails.

    # --- Load Weights Data ---
    # Explain: Loads the calculated edge weights from the specified JSON file.
    weights_data = load_json_data(weights_path)
    if weights_data is None:
        print("Failed to load weights data. Exiting.")
        return # Explain: Exits if weights loading failed.

    # Explain: Creates the efficient lookup dictionary from the weights data.
    weights_lookup = create_weights_lookup(weights_data)
    # Explain: Print the size of the lookup dictionary for debugging.
    print(f"DEBUG: Size of weights_lookup: {len(weights_lookup)}")
    # Explain: Print a sample key from the lookup for debugging, if it's not empty.
    if weights_lookup:
        sample_lookup_key = next(iter(weights_lookup.keys()))
        print(f"DEBUG: Sample key from weights_lookup: {sample_lookup_key} (Type: {type(sample_lookup_key[0])}, {type(sample_lookup_key[1])}, {type(sample_lookup_key[2])})")
    else:
        print("DEBUG: weights_lookup is empty!")

    # Explain: Creates a copy of the keys from the lookup to track which weights have been used.
    # Explain: Using a set allows for efficient removal later.
    unmatched_weights = set(weights_lookup.keys())

    # --- Update Edge Weights ---
    print("Starting edge weight update process...")
    updated_count = 0
    skipped_transfer_count = 0
    match_not_found_count = 0
    debug_print_count = 0 # Counter for limiting debug prints

    # Explain: Iterates through all edges in the graph. G.edges(data=True, keys=True) provides access to source (u), target (v), edge key (k), and edge attributes (d).
    # Explain: Using keys=True is important for MultiDiGraphs to distinguish between parallel edges.
    for u, v, k, d in G.edges(data=True, keys=True):
        # Explain: Gets the 'transfer' attribute, defaulting to False if it doesn't exist.
        is_transfer_attr = d.get('transfer', False)
        # Explain: Gets the 'key' attribute (used in older versions or potentially alongside 'transfer').
        key_attr = k # In MultiDiGraph, the 'key' from the iterator is the edge key distinguishing parallel edges.

        # Explain: Checks if the edge is a transfer edge based on either the 'transfer' attribute being True or the edge key being the string "transfer".
        if is_transfer_attr is True or key_attr == "transfer":
            skipped_transfer_count += 1
            # print(f"Skipping transfer edge: ({u}, {v}, key='{k}')") # Optional: uncomment for very detailed logging
            continue # Explain: Skips to the next edge if it's identified as a transfer edge.

        # --- Process Non-Transfer Edge ---
        # Explain: Extracts the 'line' attribute for the non-transfer edge.
        line = d.get('line')
        # Explain: Checks if the 'line' attribute exists for this non-transfer edge. It's crucial for matching.
        if line is None:
            print(f"Warning: Non-transfer edge ({u}, {v}, key='{k}') is missing 'line' attribute. Cannot update weight.")
            match_not_found_count += 1 # Count as not found as we can't look it up
            continue # Explain: Skips this edge if 'line' is missing.

        # Explain: Creates the lookup key for the current edge using (source, target, line).
        edge_key = (u, v, line)

        # Explain: DEBUG: Print the edge key being searched for, but only a few times to avoid spamming the console.
        if debug_print_count < 5:
            print(f"DEBUG: Searching for edge_key: {edge_key} (Type: {type(u)}, {type(v)}, {type(line)})")
            debug_print_count += 1

        # Explain: Checks if this edge key exists in the weights lookup dictionary.
        if edge_key in weights_lookup:
            # Explain: Retrieves the calculated weight from the lookup.
            new_weight = weights_lookup[edge_key]
            # Explain: Updates the 'weight' attribute of the current edge in the graph.
            G[u][v][k]['weight'] = new_weight
            updated_count += 1
            # Explain: Removes the key from the set of unmatched weights, indicating this weight has been used.
            # Explain: Using discard is safe as it won't raise an error if the key is somehow already removed.
            unmatched_weights.discard(edge_key)
            # print(f"Updated weight for edge ({u}, {v}, line='{line}', key='{k}') to {new_weight}") # Optional: uncomment for very detailed logging
        else:
            # Explain: Handles the case where a non-transfer edge in the graph doesn't have a matching entry in the weights data.
            # Explain: Commenting out the print statement below to reduce terminal noise during debugging.
            # print(f"Error: No matching weight found for non-transfer edge: u='{u}', v='{v}', line='{line}', key='{k}'")
            match_not_found_count += 1

    print("\n--- Update Summary ---")
    print(f"Total edges processed: {G.number_of_edges()}")
    print(f"Non-transfer edges updated: {updated_count}")
    print(f"Transfer edges skipped: {skipped_transfer_count}")
    print(f"Non-transfer edges where matching weight not found: {match_not_found_count}")

    # Explain: Checks if there are any weights from the weights_data that were not used to update any edge in the graph.
    if unmatched_weights:
        print(f"\nWarning: {len(unmatched_weights)} calculated weights were not matched to any non-transfer edge in the graph:")
        # Explain: Iterates through the remaining keys in the unmatched_weights set and prints them.
        for unmatched_key in unmatched_weights:
            print(f"  - Unmatched weight key: {unmatched_key} (Weight: {weights_lookup.get(unmatched_key)})")
    else:
        print("\nAll calculated weights were successfully matched and applied to graph edges.")

    # --- Save Updated Graph ---
    # Explain: Converts the updated NetworkX graph back into node-link JSON format suitable for saving.
    print(f"\nSaving updated graph to: {output_path}")
    try:
        updated_graph_data = json_graph.node_link_data(G)
        # Explain: Opens the specified output file in write mode ('w').
        with open(output_path, 'w') as f:
            # Explain: Writes the JSON data to the file.
            # Explain: indent=4 makes the output JSON file human-readable.
            json.dump(updated_graph_data, f, indent=4)
        print(f"Successfully saved updated graph to {output_path}")
    except Exception as e:
        # Explain: Handles any errors that occur during the saving process.
        print(f"Error saving updated graph: {e}")

# --- Main Execution Block ---
if __name__ == "__main__":
    # Explain: This block ensures the code inside only runs when the script is executed directly (not imported as a module).
    print("Script started.")
    # Define relative paths from the script's location
    # Explain: os.path.dirname(__file__) gets the directory where the script is located.
    # Explain: os.path.abspath converts it to an absolute path.
    # Explain: os.path.join is used to construct paths in a platform-independent way.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Explain: Navigates up one level from script_dir to get the project's base directory (assuming script is in create_graph).
    base_dir = os.path.dirname(script_dir)

    # Explain: Defines the paths to the input graph, calculated weights, and the output file relative to the base directory.
    graph_file = os.path.join(base_dir, 'graph_data', 'networkx_graph_hubs_with_transfer_weights.json')
    weights_file = os.path.join(base_dir, 'graph_data', 'calculated_hub_edge_weights.json')
    output_file = os.path.join(base_dir, 'graph_data', 'networkx_graph_hubs_final_weighted.json')

    # Explain: Calls the main function to perform the update process.
    update_graph_edge_weights(graph_file, weights_file, output_file)

    print("Script finished.") 