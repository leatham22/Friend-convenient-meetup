# Create Graph

This directory contains the scripts responsible for building the London transport network graph and calculating the journey times (weights) for its edges.

## Purpose

The primary goal is to construct a `NetworkX` MultiDiGraph where nodes are stations and edges represent connections between them. This process involves fetching data from the TfL API, processing it, calculating travel times, and applying these weights to the graph edges.

## Scripts

*   **`build_networkx_graph_new.py`**: 
    *   **Purpose**: Fetches raw line sequence data (using cached `tfl_line_data.json` in `graph_data/legacy_data/` or fetching from the TfL API if missing) and station metadata (`../../slim_stations/unique_stations.json`). Constructs the base `networkx` MultiDiGraph using `stopPointSequences` data.
    *   **Output**: Creates `../graph_data/networkx_graph_new.json`. Nodes represent stations with details (ID, name, lat/lon, modes, lines, zone). Edges represent potential connections between stations for specific lines. Edge `weight` attributes are initialized to `null`. Handles parent-child station transfers by adding zero-weight transfer edges.
    *   **Requires**: `TFL_API_KEY` environment variable.

*   **`find_terminal_stations.py`**: 
    *   **Input**: `../graph_data/networkx_graph_new.json`.
    *   **Purpose**: Analyzes the graph to identify potential terminal stations for Tube and DLR lines based on connectivity.
    *   **Output**: `../graph_data/terminal_stations.json` (list of terminal station Naptan IDs per line).

*   **`get_timetable_data.py`**: 
    *   **Input**: `../graph_data/terminal_stations.json`.
    *   **Purpose**: Uses the identified terminals to query the TfL Timetable API (`/Line/{id}/Timetable/{stationId}`). Fetches detailed schedule data for each line starting from its terminals.
    *   **Output**: Caches raw API responses in `../graph_data/timetable_cache/` (one JSON file per line).
    *   **Requires**: `TFL_API_KEY` environment variable.

*   **`process_timetable_data.py`**: 
    *   **Input**: `../graph_data/timetable_cache/` directory and `../graph_data/networkx_graph_new.json` (for validation).
    *   **Purpose**: Reads cached timetables. Calculates the average journey duration for each directional segment found in the timetables that corresponds to an existing edge in the base graph. Averages durations and reports discrepancies.
    *   **Output**: `../graph_data/Edge_weights_tube_dlr.json` (list of directional Tube/DLR edges with calculated average durations in minutes).

*   **`get_missing_journey_times.py`**: 
    *   **Input**: `../graph_data/Edge_weights_tube_dlr.json`.
    *   **Purpose**: Identifies a predefined list of Tube/DLR edges often missed by the timetable process. Calls the TfL Journey API for these edges, averages valid durations, and appends them to the weight file.
    *   **Output**: Updates `../graph_data/Edge_weights_tube_dlr.json`.
    *   **Requires**: `TFL_API_KEY` environment variable.

*   **`get_journey_times.py`**: 
    *   **Input**: Primarily used for Overground/Elizabeth lines, referencing adjacent pairs (potentially derived from `../graph_data/line_edges.json` if needed, though this file is marked legacy).
    *   **Purpose**: Uses the TfL Journey Results API to get journey times for adjacent station pairs (typically Overground/Elizabeth lines). Averages valid times and applies thresholds.
    *   **Output**: `../graph_data/Edge_weights_overground_elizabeth.json`.
    *   **Requires**: `TFL_API_KEY` environment variable.

*   **`update_transfers_in_graph.py`**: 
    *   **Input**: `../graph_data/networkx_graph_new.json`.
    *   **Purpose**: Identifies transfer edges (where `"transfer": true`) and updates their `"weight"` to a standard penalty (e.g., 5 minutes) and standardizes their `"key"`.
    *   **Output**: Modifies `../graph_data/networkx_graph_new.json` in place (or creates a new file if specified).

*   **`update_edge_weights.py`**: 
    *   **Input**: Base graph `../graph_data/networkx_graph_new.json`, `../graph_data/Edge_weights_tube_dlr.json`, `../graph_data/Edge_weights_overground_elizabeth.json`.
    *   **Purpose**: Merges the calculated journey times from the `Edge_weights_*.json` files into the main graph file, updating the `weight` attribute for non-transfer edges.
    *   **Output**: Creates the final, weighted graph, often saved back to `../graph_data/networkx_graph_new.json` or a new file.

*   **`apply_arbitrary_timestamp.py`**: 
    *   **Input**: An edge weight file (e.g., `../graph_data/Edge_weights_tube_dlr.json`).
    *   **Purpose**: Utility to add or overwrite the `calculated_timestamp` field in weight files, primarily for ensuring schema consistency.
    *   **Output**: Modifies the input weight file in place.

## Workflow

The typical workflow to generate the complete, weighted graph is:

1.  **Set Environment Variable**: Ensure `TFL_API_KEY` is set with your TfL API key.
2.  **Build Base Graph**: Run `python3 build_networkx_graph_new.py`.
3.  **Calculate Tube/DLR Weights**: 
    a.  Run `python3 find_terminal_stations.py`.
    b.  Run `python3 get_timetable_data.py`.
    c.  Run `python3 process_timetable_data.py`.
    d.  Run `python3 get_missing_journey_times.py`.
4.  **Calculate Overground/Elizabeth Weights**: Run `python3 get_journey_times.py`.
5.  **Apply Weights to Graph**: 
    a. Run `python3 update_transfers_in_graph.py` (to set transfer times).
    b. Run `python3 update_edge_weights.py` (to merge calculated journey times).

*Note: Scripts should be run from the root directory of the project (the parent of `network_data`). File paths within the scripts assume this structure.* 

## Environment Setup

*   Python 3
*   Required libraries (install via `pip`): `requests`, `networkx`, `numpy` (check individual script imports for specifics).
*   TfL API Key: Obtain from [TfL API Portal](https://api-portal.tfl.gov.uk/) and set as an environment variable:
    ```bash
    export TFL_API_KEY="your_api_key_here"
    ``` 