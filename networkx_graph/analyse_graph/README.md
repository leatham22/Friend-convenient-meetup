# Analyse Graph

This directory contains scripts for validating the integrity and analyzing the properties of the generated London transport network graph and its associated edge weight data.

## Purpose

These scripts help ensure the quality and correctness of the graph data before it's used for pathfinding or other analyses. They check for structural issues, inconsistencies in edge weights, and provide utility functions for interacting with the graph.

## Scripts

*   **`check_line_continuity.py`**: 
    *   **Input**: `../graph_data/networkx_graph_new.json`.
    *   **Purpose**: Validates the graph structure by checking for expected connections between adjacent stations on each line. It intelligently handles branched lines to avoid false positives and reports potentially missing segments.
    *   **How to Run**: `python3 check_line_continuity.py`. Add `--line <line_id>` (e.g., `--line district`) to check a specific line.

*   **`check_missing_edges.py`**: 
    *   **Input**: Base graph `../graph_data/networkx_graph_new.json`, `../graph_data/Edge_weights_tube_dlr.json`, `../graph_data/Edge_weights_overground_elizabeth.json`.
    *   **Purpose**: Compares the edges defined in the base graph against the calculated weight files. It identifies discrepancies: edges present in the graph but missing calculated weights, and edges with weights that don't correspond to an edge in the graph for that mode.
    *   **How to Run**: `python3 check_missing_edges.py`.

*   **`analyze_edge_weights.py`**: 
    *   **Input**: `../graph_data/Edge_weights_tube_dlr.json`, `../graph_data/Edge_weights_overground_elizabeth.json`.
    *   **Purpose**: Performs deeper analysis on the calculated weight files:
        *   **Duration Sanity Check**: Flags edges with unusually high (> 90 min) or low (< 0.5 min) journey times.
        *   **Symmetry Analysis**: Compares forward (A->B) and reverse (B->A) journey times for the same pair, highlighting significant differences.
        *   **Schema Verification**: Checks if all records contain the expected fields (`source`, `target`, `line`, `mode`, `duration_minutes`, `calculated_timestamp`) and data types.
    *   **How to Run**: `python3 analyze_edge_weights.py`.

*   **`graph_utils.py`**: 
    *   **Purpose**: Provides utility functions for loading the graph from JSON and performing common operations. Not typically run directly, but imported by other scripts or notebooks.
    *   **Key Functions**:
        *   `load_graph_from_json(file_path)`: Loads the graph.
        *   `find_shortest_path(G, source, target, weight)`: Calculates the shortest path using Dijkstra.
        *   `find_station_by_substring(G, substring)`: Finds stations by name.
        *   `get_station_info(G, station_name)`: Retrieves node attributes.
        *   `get_connected_stations(G, station_name)`: Finds directly connected stations.
        *   `get_graph_stats(G)`: Calculates basic graph statistics.
        *   `visualize_graph(G, output_file)`: (Requires `matplotlib`) Creates a basic plot.
    *   **Note**: The default graph path within this script needs to be updated to reflect the new structure (`../graph_data/networkx_graph_new.json`).

*   **`extract_line_edges.py`**: 
    *   **Input**: `../graph_data/networkx_graph_new.json`.
    *   **Purpose**: Extracts unique adjacent station pairs for each line from the graph. This was likely used to generate input for `get_journey_times.py` initially.
    *   **Output**: `../graph_data/line_edges.json` (potentially legacy, see `graph_data/legacy_data/README.md`).
    *   **How to Run**: `python3 extract_line_edges.py`.

*   **`analyze_graph.py`**: 
    *   **Input**: `../graph_data/networkx_graph_new.json`.
    *   **Purpose**: Performs basic analysis directly on the graph structure, such as counting nodes/edges, checking connectivity, and potentially other NetworkX-based analyses.
    *   **How to Run**: `python3 analyze_graph.py`.

## How to Use

Run the validation and analysis scripts from the project's root directory after generating the graph and edge weights:

```bash
# Example: Check line continuity
python3 network_data/analyse_graph/check_line_continuity.py

# Example: Analyze edge weights
python3 network_data/analyse_graph/analyze_edge_weights.py
```

Import functions from `graph_utils.py` in other Python scripts or notebooks:

```python
from network_data.analyse_graph.graph_utils import load_graph_from_json, find_shortest_path

# Assuming graph file exists at ../graph_data/networkx_graph_new.json
# relative to where graph_utils is located
GRAPH_PATH = "../graph_data/networkx_graph_new.json" 

G = load_graph_from_json(GRAPH_PATH)
path = find_shortest_path(G, "Station A", "Station B")
print(path)
``` 