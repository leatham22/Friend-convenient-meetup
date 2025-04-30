# Create Graph

This directory contains scripts responsible for building the London transport network graph using a **hub-based** model and calculating journey times (weights) for its edges.

## Purpose

The primary goal is to construct a `NetworkX` MultiDiGraph where:
*   **Nodes** represent *station hubs* (grouping related stations like Underground, Rail, DLR under a single parent ID).
*   **Edges** represent connections:
    *   **Line Edges:** Direct travel segments between *different* hubs on a specific transport line (e.g., Tube, DLR, Overground, Elizabeth Line, National Rail).
    *   **Transfer Edges:** Potential walking connections between geographically close but distinct hubs.

This hub-based approach simplifies transfers within the same station complex and aims to improve pathfinding robustness.

## New Hub-Based Workflow Scripts

This new workflow uses three main scripts executed sequentially:

1.  **`build_hub_graph.py`**:
    *   **Purpose**: Creates the foundational base graph with a single-node-per-hub structure.
    *   **Input**: Fetches raw line sequence data from the TfL API (using cached `tfl_all_line_sequence_data.json` in `../graph_data/` or fetching if missing/stale).
    *   **Process**: Identifies unique stations, groups them by `topMostParentId` into hubs, creates one node per hub aggregating station details (name, primary Naptan ID, lat/lon, modes, lines, constituent Naptan IDs, zone). Adds directed edges *only* between *different* hubs based on line sequences. Edges represent line segments (`transfer=False`) with `weight=null` initially.
    *   **Output**: Creates `../graph_data/networkx_graph_hubs_base.json` (NetworkX node-link format).
    *   **Requires**: `TFL_API_KEY` environment variable (optional for cached data, required for fetching).
    *   **Extra details**: Has a couple of manual fixes due to inconsistent TFL API data, eg WIllesden Green Underground Station is quoted as being on Metrapolitan line on API data, but it hasnt run on that line since 1979. Also West India Quay being skipped in one direction. 

2.  **`add_proximity_transfers.py`**:
    *   **Purpose**: Adds potential walking transfer edges (with null weights) between geographically close but distinct hubs.
    *   **Input**: `../graph_data/networkx_graph_hubs_base.json`.
    *   **Process**: Loads the base graph. For each hub, queries the TfL StopPoint API to find nearby hubs within a radius. If a nearby distinct hub is found *and* no direct line edge already connects them, adds bidirectional edges with `transfer=True`, `mode='walking'`, `line='walking'`, `key='transfer'`, and `weight=null`. Records pairs of hub Naptan IDs needing weight calculation.
    *   **Output**:
        *   `../graph_data/networkx_graph_hubs_with_transfers.json` (Graph with null-weighted transfer edges added).
        *   `../graph_data/inter_hub_transfers_to_weight.json` (List of [primary_naptan_id_1, primary_naptan_id_2] pairs for transfers).
    *   **Requires**: Network connection (for TfL StopPoint API calls).

3.  **`calculate_transfer_weights.py`**:
    *   **Purpose**: Calculates walking durations for the proximity-based transfer edges and updates their weights.
    *   **Input**: `../graph_data/networkx_graph_hubs_with_transfers.json`, `../graph_data/inter_hub_transfers_to_weight.json`.
    *   **Process**: Loads the graph and the transfer list. For each pair of hub Naptan IDs, calls the TfL Journey API (`mode=walking`) to get the duration in minutes. Updates the `weight` attribute on the corresponding bidirectional transfer edges (key='transfer'). If the API call fails or returns no duration, the weight is set to `null`.
    *   **Output**: Creates the final hub graph `../graph_data/networkx_graph_hubs_final.json` with calculated walking transfer weights.
    *   **Requires**: `TFL_API_KEY` environment variable (mandatory for Journey API calls).

---

## Legacy/Alternative Weighting Scripts (Timetable-Based)

*(These scripts operate on the older, station-level graph structure or may be adapted for the hub graph line edges in the future. They are not part of the primary hub-based workflow described above for generating the initial weighted graph with walking transfers.)*

*   **`find_terminal_stations.py`**: Identifies potential terminal stations for timetable fetching.
*   **`get_timetable_data.py`**: Fetches TfL Timetable data using terminals.
*   **`process_timetable_data.py`**: Calculates average journey times from timetables.
*   **`get_missing_journey_times.py`**: Supplements timetable data with Journey API calls for specific edges.
*   **`get_journey_times.py`**: Uses Journey API for specific modes (e.g., Overground/Elizabeth).
*   **`update_edge_weights.py`**: Merges calculated journey times into a graph.
*   **`apply_arbitrary_timestamp.py`**: Utility for timestamping weight files.

## Hub-Based Workflow Execution

The typical workflow to generate the complete, hub-based weighted graph is:

1.  **Set Environment Variable**: Ensure `TFL_API_KEY` is set with your TfL API key.
    ```bash
    export TFL_API_KEY="your_api_key_here"
    ```
2.  **Build Base Hub Graph**: Run `python3 build_hub_graph.py`.
3.  **Add Proximity Transfers**: Run `python3 add_proximity_transfers.py`.
4.  **Calculate Transfer Weights**: Run `python3 calculate_transfer_weights.py`.

The final graph will be in `../graph_data/networkx_graph_hubs_final.json`.

*Note: Scripts should generally be run from the root directory of the project (the parent of `networkx_graph`). File paths within the scripts assume this structure.* 

## Environment Setup

*   Python 3
*   Required libraries (install via `pip`): `requests`, `networkx`, `python-dotenv` (check individual script imports for specifics).
*   TfL API Key: Obtain from [TfL API Portal](https://api-portal.tfl.gov.uk/) and set as an environment variable `TFL_API_KEY` (e.g., in a `.env` file in the project root or exported in your shell). 