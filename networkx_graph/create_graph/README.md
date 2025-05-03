# Graph Creation Pipeline

This directory houses the sequence of Python scripts responsible for building the weighted, hub-based NetworkX graph of the London transport network. The process is orchestrated by the `__init__.py` file within this directory, which defines the `build_graph` function called by the main `build_graph.py` script in the project root.

## Pipeline Overview

The graph creation involves several distinct steps, executed in order:

1.  **`build_hub_graph.py`**: Creates the initial graph structure based on station hubs and the lines connecting them. It identifies unique hubs (stations or groups of nearby stations) and adds nodes and initial edges representing line segments between adjacent hubs.
2.  **`add_proximity_transfers.py`**: Identifies and adds potential transfer links (edges) between hubs that are geographically close but not directly connected by a single line segment.
3.  **`calculate_transfer_weights.py`**: Calculates the time weights (walking time) for the transfer links added in the previous step using the TfL Journey Planner API.
4.  **`get_timetable_data.py`**: Fetches and processes timetable data for London Underground and DLR lines from the TfL API. This data is used to calculate travel times.
5.  **`get_tube_dlr_edge_weights.py`**: Calculates the edge weights (average journey times) for Tube and DLR line segments based on the fetched timetable data.
6.  **`get_overground_Elizabeth_edge_weights.py`**: Calculates the edge weights (average journey times) for Overground and Elizabeth Line segments using the TfL Journey Planner API (as timetable data is less readily available or suitable).
7.  **`validate_graph_weights.py`**: Performs consistency checks between the graph structure and the calculated edge weights before they are merged. It ensures all relevant edges have weights and that weights are valid. **The pipeline halts if validation fails.**
8.  **`update_graph_weights.py`**: Merges the calculated line segment weights (from steps 5 and 6) and transfer weights (from step 3) into the main graph structure, producing the final weighted graph.

## Other Contents

-   **`__init__.py`**: Makes this directory a Python package and defines the main `build_graph` function that runs the pipeline steps sequentially. It imports the necessary functions from the individual step modules.
-   **`output/`**: This subdirectory stores intermediate JSON files generated during the pipeline (e.g., calculated weights) and the final `final_networkx_graph.json` output file.

## Running the Pipeline

While each script performs a specific task, they are designed to be run sequentially as part of the overall pipeline.

**Do not run these scripts individually.**

To execute the entire graph creation process, navigate to the **project's root directory** and run the main build script using **either** of the following commands:

1.  Run as a module:
    ```bash
    python3 -m networkx_graph.build_graph
    ```
2.  Run directly:
    ```bash
    python3 networkx_graph/build_graph.py
    ```

This ensures all steps defined in `__init__.py` are executed in the correct order with the appropriate inputs and outputs.

## Purpose

The primary goal is to construct a `NetworkX` MultiDiGraph where:
*   **Nodes** represent *station hubs* (grouping related stations like Underground, Rail, DLR under a single parent ID).
*   **Edges** represent connections:
    *   **Line Edges:** Direct travel segments between *different* hubs on a specific transport line (e.g., Tube, DLR, Overground, Elizabeth Line, National Rail).
    *   **Transfer Edges:** Potential walking connections between geographically close but distinct hubs.

This hub-based approach simplifies transfers within the same station complex and aims to improve pathfinding robustness.
