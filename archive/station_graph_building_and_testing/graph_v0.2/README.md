# Graph v0.2 - Adding Edge Weights

This directory contains scripts focused on implementing networkx graph structure, adding and refining edge weights (journey times) to the station graph and further testing.

## Description:

*  This structure is the building block for what became the final graph structure. 
*  As this structure is so similar to final version, some scripts are missing as they have been iterated on and exist in our final structure. 

## Contents

### Graph Creation:

*   `build_networkx_graph.py`: The first attempt at creating a networkx graph structure.
*   `build_networkx_graph_new.py`: A revised script for building the graph, incorporating a networkx multidigraph structure. 
*   `update_transfers_in_graph.py`: Updates transfer times or connections within the graph to 5 minutes.
*   `get_missing_journey_times.py`: Script to fetch duration for edges with known issues using a different API endpoint. (eg Earl's Court -> Kensington Olympia)
*   `extract_line_edges.py`: Extracts edges from graph belonging to specific lines and outputs into new file which can be edited without messing up original data.
*   `process_timetable_data.py`: Processes timetable data to calculate or verify edge weights. Another version of this is still used in project. 
*   `update_edge_weights.py`: Script specifically for updating edge weights in the graph based off durations extracted from TFL API. 
*   `graph_fixer.py`: Script used to correct missing edge issues found in the initial graph by adding in bidirectional edges. 

### Graph tests:

*   `compare_graphs.py`: Used to compare the graphs outputted by `build_networkx_graph.py` and `build_networkx_graph_new.py`
*   `find_terminal_stations.py`: Script to identify terminal stations within the weighted graph (required some manual additions for optimisation)
*   `check_connectivity.py`: Checks the connectivity of the graph, likely after weight updates.
*   `check_line_continuity.py`: Verifies that stations along a specific line are connected sequentially in the graph.
*   `find_new_stations.py`: Identifies new stations in this graph that didn't exist in our original datastructure. This confirms that new graph is more optimised. 
*   `analyze_edge_weights.py`: Analyzes the distribution or characteristics of the edge weights.
*   `check_missing_edges.py`: Identifies expected edges that are missing from the graph.
*   `analyze_graph.py`: General analysis script for the weighted graph.
*   `analyze_location_diffs.py`: Analyzes differences in station locations between new and old method. 


### Graph Utility function: 

*   `graph_utils(copy).py`: A utility script for graph operations, as it is still used in project we have stored a copy here. 
*   `apply_arbitrary_timestamp.py`: Applies a specific timestamp, used to help incorporate the "sync with tfl data" script.










