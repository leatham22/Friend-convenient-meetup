# Create Graph

This directory contains scripts responsible for building the London transport network graph using a **hub-based** model and calculating journey times (weights) for its edges.

## Purpose

The primary goal is to construct a `NetworkX` MultiDiGraph where:
*   **Nodes** represent *station hubs* (grouping related stations like Underground, Rail, DLR under a single parent ID).
*   **Edges** represent connections:
    *   **Line Edges:** Direct travel segments between *different* hubs on a specific transport line (e.g., Tube, DLR, Overground, Elizabeth Line, National Rail).
    *   **Transfer Edges:** Potential walking connections between geographically close but distinct hubs.

This hub-based approach simplifies transfers within the same station complex and aims to improve pathfinding robustness.

## Hub-Based Workflow & Status

This new workflow uses several main scripts executed sequentially:

1.  **`build_hub_graph.py` (Status: Implemented)**:
    *   Creates the base graph (`../graph_data/networkx_graph_hubs_base.json`) with one node per hub and null-weighted line edges.
    *   Includes manual corrections for TfL API data.

2.  **`add_proximity_transfers.py` (Status: Implemented)**:
    *   Reads the base graph.
    *   Adds null-weighted walking transfer edges between nearby hubs.
    *   Outputs `../graph_data/networkx_graph_hubs_with_transfers.json` (graph) and `../graph_data/inter_hub_transfers_to_weight.json` (list of transfers).

3.  **`calculate_transfer_weights.py` (Status: Implemented)**:
    *   Reads `networkx_graph_hubs_with_transfers.json`.
    *   Calculates weights (walking durations) for transfer edges using the TFL Journey API.
    *   Outputs `../graph_data/networkx_graph_hubs_with_transfer_weights.json` (contains weighted transfers, line edges still null).

4.  **`get_timetable_data.py` (Status: Implemented)**:
    *   Fetches standard timetable data using terminals and specific point-to-point data for known problematic segments.
    *   Caches data in `../graph_data/timetable_cache/`.

5.  **`get_tube_dlr_edge_weights.py` (Status: Implemented)**:
    *   Reads `networkx_graph_hubs_with_transfer_weights.json` (to know which hub connections exist).
    *   Processes cached timetable data (`../graph_data/timetable_cache/`).
    *   Calculates average durations for *Tube/DLR line edges* between hubs.
    *   Appends calculated weights to `../graph_data/calculated_hub_edge_weights.json`.

6.  **`get_overground_Elizabeth_edge_weights.py` (Status: Implemented)**:
    *   Reads `networkx_graph_hubs_with_transfer_weights.json` (to know which hub connections exist).
    *   Uses the TFL Journey API to get journey times for *Overground/Elizabeth line edges* between hubs.
    *   Appends calculated weights to `../graph_data/calculated_hub_edge_weights.json`.

7.  **`update_graph_weights.py` (Status: Implemented)**:
    *   Reads `networkx_graph_hubs_with_transfer_weights.json` (graph with weighted transfers).
    *   Reads `calculated_hub_edge_weights.json` (containing all calculated line edge weights).
    *   Updates the null weights for the line edges in the graph.
    *   Outputs the final, fully weighted graph: `../graph_data/networkx_graph_hubs_final_weighted.json`.

**Current State:**
*   The scripts are implemented to produce a fully weighted hub-based graph.
*   The final output is `networkx_graph_hubs_final_weighted.json`.

**Next Steps:**
*   Analyze the final graph using scripts in the `../analyse_graph/` directory.
*   Further refinement or validation of weights as needed.

---

## Legacy/Alternative Weighting Scripts

*(These scripts may be outdated or operate on different graph structures. Refer to the Hub-Based Workflow above for the current process.)*

*   `find_terminal_stations.py`
*   `process_timetable_data.py`
*   `get_missing_journey_times.py`
*   `get_journey_times.py`
*   `update_edge_weights.py` (Note: A new script with the same name is used in the current workflow)
*   `apply_arbitrary_timestamp.py`

## Hub-Based Workflow Execution

The typical workflow to generate the complete, hub-based weighted graph is:

1.  **Set Environment Variable**: Ensure `TFL_API_KEY` is set with your TfL API key.
    ```bash
    export TFL_API_KEY="your_api_key_here"
    ```
2.  **Build Base Hub Graph**: Run `python3 build_hub_graph.py`.
3.  **Add Proximity Transfers**: Run `python3 add_proximity_transfers.py`.
4.  **Calculate Transfer Weights**: Run `python3 calculate_transfer_weights.py`.
5.  **Fetch Timetable Data**: Run `python3 get_timetable_data.py`.
6.  **Calculate Tube/DLR Line Weights**: Run `python3 get_tube_dlr_edge_weights.py`.
7.  **Calculate Overground/Elizabeth Line Weights**: Run `python3 get_overground_Elizabeth_edge_weights.py`.
8.  **Update Graph with Line Weights**: Run `python3 update_graph_weights.py`.

The final graph will be in `../graph_data/networkx_graph_hubs_final_weighted.json`.

*Note: Scripts should generally be run from this `create_graph` directory, or paths adjusted accordingly if run from the project root.*

## Environment Setup

*   Python 3
*   Required libraries (install via `pip`): `requests`, `networkx`, `python-dotenv` (check individual script imports for specifics).
*   TfL API Key: Obtain from [TfL API Portal](https://api-portal.tfl.gov.uk/) and set as an environment variable `TFL_API_KEY` (e.g., in a `.env` file in the project root or exported in your shell).

### Workflow Steps

1.  **Fetch Raw Data (`fetch_all_tfl_data` in `build_hub_graph.py`)**: 
    *   Queries TfL API for all line IDs for specified modes (Tube, DLR, Overground, Elizabeth Line).
    *   Fetches detailed `/Line/{id}/Route/Sequence/all` data for each unique line.
    *   Caches the aggregated raw data in `graph_data/tfl_all_line_sequence_data.json`.

2.  **Build Base Hub Graph (`build_hub_graph.py`)**: 
    *   **Input**: `graph_data/tfl_all_line_sequence_data.json`.
    *   **Process**: 
        *   Identifies unique hubs based on `topMostParentId`.
        *   Aggregates information for each hub (name, primary Naptan ID, coordinates, modes, lines).
        *   Stores constituent station details: **Crucially, it now saves a list of dictionaries under the `constituent_stations` key for each hub node. Each dictionary contains the `name` and `naptan_id` of a constituent station.** (e.g., `[{'name': 'Station Name', 'naptan_id': '9...'}]`). This replaces the old `constituent_naptan_ids` list.
        *   Creates a `networkx.MultiDiGraph`.
        *   Adds a single node for each unique hub, using the hub name as the node ID and storing all aggregated data as attributes.
        *   Adds edges between hub nodes representing direct line connections derived from the sequence data. These edges have `transfer=False` and `weight=None` initially.
        *   Includes manual corrections (e.g., removing incorrect Metropolitan line edges from Willesden Green, adding missing Metropolitan edge between Finchley Road and Wembley Park).
    *   **Output**: `graph_data/networkx_graph_hubs_base.json` (Base graph with hubs and unweighted line edges).

3.  **Add Proximity Transfers (`add_proximity_transfers.py`)**: 
    *   Reads the base graph.
    *   Adds null-weighted walking transfer edges between nearby hubs.
    *   Outputs `../graph_data/networkx_graph_hubs_with_transfers.json` (graph) and `../graph_data/inter_hub_transfers_to_weight.json` (list of transfers).

4.  **Calculate Transfer Weights (`calculate_transfer_weights.py`)**:
    *   Reads `networkx_graph_hubs_with_transfers.json`.
    *   Calculates weights (walking durations) for transfer edges using the TFL Journey API.
    *   Outputs `../graph_data/networkx_graph_hubs_with_transfer_weights.json` (contains weighted transfers, line edges still null).

5.  **Fetch Timetable Data (`get_timetable_data.py`)**:
    *   Fetches standard timetable data using terminals and specific point-to-point data for known problematic segments.
    *   Caches data in `../graph_data/timetable_cache/`.

6.  **Calculate Tube/DLR Line Weights (`get_tube_dlr_edge_weights.py`)**:
    *   Reads `networkx_graph_hubs_with_transfer_weights.json` (to know which hub connections exist).
    *   Processes cached timetable data (`../graph_data/timetable_cache/`).
    *   Calculates average durations for *Tube/DLR line edges* between hubs.
    *   Appends calculated weights to `../graph_data/calculated_hub_edge_weights.json`.

7.  **Calculate Overground/Elizabeth Line Weights (`get_overground_Elizabeth_edge_weights.py`)**:
    *   Reads `networkx_graph_hubs_with_transfer_weights.json` (to know which hub connections exist).
    *   Uses the TFL Journey API to get journey times for *Overground/Elizabeth line edges* between hubs.
    *   Appends calculated weights to `../graph_data/calculated_hub_edge_weights.json`.

8.  **Update Graph with Line Weights (`update_graph_weights.py`)**:
    *   Reads `networkx_graph_hubs_with_transfer_weights.json` (graph with weighted transfers).
    *   Reads `calculated_hub_edge_weights.json` (containing all calculated line edge weights).
    *   Updates the null weights for the line edges in the graph.
    *   Outputs the final, fully weighted graph: `../graph_data/networkx_graph_hubs_final_weighted.json`. 