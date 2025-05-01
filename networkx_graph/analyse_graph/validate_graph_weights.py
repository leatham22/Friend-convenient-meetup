#!/usr/bin/env python3
"""
Validate Graph Weights Consistency

This script checks for consistency between the main network graph structure
and the separately calculated edge weight files.

It performs the following checks:
1.  Finds edges present in the weight files but missing from the main graph.
2.  Finds relevant edges (Tube, DLR, Overground, Elizabeth Line) in the main
    graph that are missing from the weight files.
3.  Checks for overlap between the Tube/DLR weight file and the Overground/Elizabeth
    weight file (should be none).
4.  Checks for invalid weight values (null or <= 0) in the weight files.

Usage:
    python3 validate_graph_weights.py
"""

import json
import os
import logging
from collections import defaultdict

# --- Configuration ---
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Determine script directory and data directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '../graph_data') # Assumes data is one level up in graph_data

# Define input file paths relative to DATA_DIR
GRAPH_FILE = os.path.join(DATA_DIR, 'networkx_graph_hubs_final.json')
# Consolidated weights file for all calculated modes
WEIGHTS_FILE = os.path.join(DATA_DIR, 'calculated_hub_edge_weights.json')
# OG_ELIZ_WEIGHTS_FILE = os.path.join(DATA_DIR, 'Edge_weights_overground_elizabeth.json') # Removed

# Define the modes/lines considered relevant for weight calculation
RELEVANT_MODES = {'tube', 'dlr', 'overground', 'elizabeth-line'}

# --- Helper Functions ---

def load_json_data(filepath):
    """Loads JSON data from a file, handling errors."""
    if not os.path.exists(filepath):
        logging.error(f"File not found: {filepath}")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {filepath}: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred loading {filepath}: {e}")
        return None

def get_edge_keys_from_list(edge_list, source_key='source', target_key='target', line_key='line'):
    """Extracts (source, target, line) tuples from a list of edge dictionaries."""
    keys = set()
    if not isinstance(edge_list, list):
        logging.warning(f"Expected a list of edges, but got {type(edge_list)}. Cannot extract keys.")
        return keys

    for i, edge in enumerate(edge_list):
        if not isinstance(edge, dict):
            logging.warning(f"Item {i} is not a dictionary: {edge}. Skipping.")
            continue
        try:
            source = edge[source_key]
            target = edge[target_key]
            line = edge[line_key]
            keys.add((str(source), str(target), str(line))) # Ensure keys are strings
        except KeyError as e:
            logging.warning(f"Edge missing key {e} at index {i}: {edge}. Skipping edge key extraction.")
        except Exception as e:
            logging.warning(f"Error processing edge at index {i}: {edge}. Error: {e}. Skipping edge key extraction.")
    return keys

def check_weight_values(edge_list, filepath):
    """Checks for null or non-positive weights in a list of edge dictionaries."""
    invalid_weights = []
    if not isinstance(edge_list, list):
        logging.warning(f"Weight data from {filepath} is not a list. Cannot check weights.")
        return invalid_weights

    for i, edge in enumerate(edge_list):
         if not isinstance(edge, dict):
             continue # Error already logged by get_edge_keys_from_list
         try:
             weight = edge.get('weight')
             if weight is None:
                 invalid_weights.append({
                     'index': i,
                     'edge': (edge.get('source'), edge.get('target'), edge.get('line')),
                     'reason': 'Weight is null/missing',
                     'data': edge
                 })
             elif not isinstance(weight, (int, float)):
                  invalid_weights.append({
                     'index': i,
                     'edge': (edge.get('source'), edge.get('target'), edge.get('line')),
                     'reason': f'Weight is not numeric ({type(weight).__name__})',
                     'data': edge
                 })
             elif weight <= 0:
                 invalid_weights.append({
                     'index': i,
                     'edge': (edge.get('source'), edge.get('target'), edge.get('line')),
                     'reason': f'Weight is not positive ({weight})',
                     'data': edge
                 })
         except Exception as e:
            logging.warning(f"Error checking weight for edge at index {i} in {filepath}: {edge}. Error: {e}")

    return invalid_weights

# --- Main Validation Logic ---

def main():
    """Runs the validation checks."""
    logging.info("Starting graph and weight validation...")

    # 1. Load Data
    logging.info(f"Loading main graph from: {GRAPH_FILE}")
    graph_data = load_json_data(GRAPH_FILE)
    logging.info(f"Loading consolidated weights from: {WEIGHTS_FILE}")
    weights_data = load_json_data(WEIGHTS_FILE)
    # og_eliz_weights_data = load_json_data(OG_ELIZ_WEIGHTS_FILE) # Removed

    # Check if loading failed
    # if graph_data is None or tube_dlr_weights_data is None or og_eliz_weights_data is None:
    if graph_data is None or weights_data is None:
        logging.error("Failed to load one or more required data files. Aborting validation.")
        return

    # 2. Extract Edge Keys and Relevant Graph Edges
    logging.info("Extracting edge keys...")

    # Main Graph Edges
    graph_edge_keys = set()
    relevant_graph_edge_keys = set()
    line_modes = defaultdict(set) # Store modes associated with each line in the graph

    if isinstance(graph_data.get('edges'), list):
        graph_edges_list = graph_data['edges']
        for edge in graph_edges_list:
            if not isinstance(edge, dict): continue
            try:
                source = edge['source']
                target = edge['target']
                line = edge.get('line') or edge.get('key') # Use 'line' or fallback to 'key'
                mode = edge.get('mode', 'unknown')

                if source is None or target is None or line is None:
                     logging.warning(f"Graph edge missing source/target/line: {edge}. Skipping.")
                     continue

                edge_key = (str(source), str(target), str(line))
                graph_edge_keys.add(edge_key)
                line_modes[str(line)].add(str(mode))

                # Check if this graph edge *should* have a weight calculated
                # Consider it relevant if its mode OR any mode associated with its line is relevant
                if mode in RELEVANT_MODES or any(m in RELEVANT_MODES for m in line_modes[str(line)]):
                     relevant_graph_edge_keys.add(edge_key)

            except KeyError as e:
                logging.warning(f"Graph edge missing key {e}: {edge}. Skipping.")
            except Exception as e:
                 logging.warning(f"Error processing graph edge: {edge}. Error: {e}. Skipping.")
        logging.info(f"Found {len(graph_edge_keys)} total edges in the graph file.")
        logging.info(f"Identified {len(relevant_graph_edge_keys)} relevant edges (Tube/DLR/Overground/Elizabeth) in the graph file.")
    else:
        logging.error("'edges' key not found or not a list in graph data. Cannot extract graph edges.")
        return

    # Weight File Edges
    # tube_dlr_weight_keys = get_edge_keys_from_list(tube_dlr_weights_data) # Renamed
    # logging.info(f"Found {len(tube_dlr_weight_keys)} edge keys in Tube/DLR weight file.")
    # og_eliz_weight_keys = get_edge_keys_from_list(og_eliz_weights_data) # Removed
    # logging.info(f"Found {len(og_eliz_weight_keys)} edge keys in Overground/Elizabeth weight file.")
    all_weight_keys = get_edge_keys_from_list(weights_data)
    logging.info(f"Found {len(all_weight_keys)} total unique edge keys in the consolidated weight file: {os.path.basename(WEIGHTS_FILE)}.")

    # 3. Perform Comparisons

    logging.info("\n--- Comparison Results ---")

    # Check 1: Edges in weight file but missing from the main graph
    missing_in_graph = all_weight_keys - graph_edge_keys
    if missing_in_graph:
        logging.warning(f"Found {len(missing_in_graph)} edges in the weight file ({os.path.basename(WEIGHTS_FILE)}) that are MISSING from the main graph file:")
        for i, edge in enumerate(sorted(list(missing_in_graph))):
            logging.warning(f"  {i+1}. {edge[0]} -> {edge[1]} (Line: {edge[2]})")
            # # Add logic here to find which weight file it came from if needed # Removed comment
            # origin_file = TUBE_DLR_WEIGHTS_FILE if edge in tube_dlr_weight_keys else OG_ELIZ_WEIGHTS_FILE # Removed
            # logging.warning(f"     (Origin: {os.path.basename(origin_file)})") # Removed
    else:
        logging.info(f"OK: All edges found in the weight file ({os.path.basename(WEIGHTS_FILE)}) are also present in the main graph file.")

    # Check 2: Relevant edges in the main graph missing from weight file
    missing_in_weights = relevant_graph_edge_keys - all_weight_keys
    if missing_in_weights:
        logging.warning(f"Found {len(missing_in_weights)} relevant edges (Tube/DLR/OG/Eliz) in the graph file that are MISSING weights in {os.path.basename(WEIGHTS_FILE)}:")
        for i, edge in enumerate(sorted(list(missing_in_weights))):
            logging.warning(f"  {i+1}. {edge[0]} -> {edge[1]} (Line: {edge[2]})")
    else:
        logging.info(f"OK: All relevant edges (Tube/DLR/Overground/Elizabeth) in the graph file have corresponding entries in the weight file ({os.path.basename(WEIGHTS_FILE)}).")

    # Check 3: Overlap between weight files (Removed)
    # weight_overlap = tube_dlr_weight_keys.intersection(og_eliz_weight_keys)
    # if weight_overlap:
    #     logging.error(f"CRITICAL: Found {len(weight_overlap)} edges present in BOTH weight files (should not happen!):")
    #     for i, edge in enumerate(sorted(list(weight_overlap))):
    #         logging.error(f"  {i+1}. {edge[0]} -> {edge[1]} (Line: {edge[2]})")
    # else:
    #     logging.info("OK: No overlap found between the two weight files.")

    # 4. Check Weight Values
    logging.info("\n--- Weight Value Checks ---")
    # invalid_tube_dlr = check_weight_values(tube_dlr_weights_data, TUBE_DLR_WEIGHTS_FILE) # Use combined data
    invalid_weights = check_weight_values(weights_data, WEIGHTS_FILE)
    # invalid_og_eliz = check_weight_values(og_eliz_weights_data, OG_ELIZ_WEIGHTS_FILE) # Removed

    # if invalid_tube_dlr:
    if invalid_weights:
        # logging.warning(f"Found {len(invalid_tube_dlr)} invalid weights in {os.path.basename(TUBE_DLR_WEIGHTS_FILE)}:")
        logging.warning(f"Found {len(invalid_weights)} invalid weights in {os.path.basename(WEIGHTS_FILE)}:")
        # for item in invalid_tube_dlr:
        for item in invalid_weights:
            logging.warning(f"  - Index {item['index']}: Edge {item['edge']} - Reason: {item['reason']}")
    else:
        # logging.info(f"OK: All weights checked in {os.path.basename(TUBE_DLR_WEIGHTS_FILE)} appear valid (present and > 0).")
        logging.info(f"OK: All weights checked in {os.path.basename(WEIGHTS_FILE)} appear valid (present and > 0).")

    # if invalid_og_eliz:
    #     logging.warning(f"Found {len(invalid_og_eliz)} invalid weights in {os.path.basename(OG_ELIZ_WEIGHTS_FILE)}:")
    #     for item in invalid_og_eliz:
    #         logging.warning(f"  - Index {item['index']}: Edge {item['edge']} - Reason: {item['reason']}")
    # else:
    #     logging.info(f"OK: All weights checked in {os.path.basename(OG_ELIZ_WEIGHTS_FILE)} appear valid (present and > 0).")


    logging.info("\nValidation finished.")

if __name__ == "__main__":
    main() 