# Graph Data

This directory contains various graph representations and associated data files derived from the TfL station and line information.

## Purpose

These files serve as:
- Input for graph-based analysis and algorithms (e.g., pathfinding).
- Intermediate or final outputs of data processing steps involving network structures.
- Records of different versions or specific subsets of the transport network graph.

## Contents

JSON files containing graph structures and related data:

- `incorrect_networkx_graph.json`: First attempt at creating a NetworkX graph, it read the wrong data from API and as such contains errors relating to ability to transfer between stations.
- `first_networkx_graph.json`: First working version of the NetworkX graph, using a (incomplete) similar naming convention to work out which stations should be transferred from one another (eg Stratford DLR staion, Stratford underground station). This resulted in too much "noise" where transport on the same platform had artificial "transfer" edges applied between them. Needed optimisation.
- `old_networkx_graph.json`: The next iteration of the NetworkX graph that dropped the naming convention logic and used our older data source `stations_slim_format.json` to map parent-child stations which we have utilised for transfer edges. This was far more accurate as we had done most the heavy lifting creating our old dataset. 
- `old_networkx_graph_with_transfers.json`: The same as `old_networkx_graph.json` except this time making sure the "transfer" edge data structure matched the structure for all other edges
- `networkx_graph_new.json`: A corrected version of `old_networkx_graph_with_transfers.json` after realising our scripts created duplicate edges.   This was last structure before our current "Hub" structure. It is sufficient for nodes but lacked some key edges that allowed us to transfer from overground/DLR -> tube. 
- `Edge_weights_tube_dlr.json`: Edge weights specifically calculated for Tube and DLR lines using TFL's timetable API data. 
- `line_edges.json`: All edges extracted from `networkx_graph_new.json`. It was used for applying real duration between nodes to edge weighting without touching our datasource. Once we were happy with the results, it was merged into `networkx_graph_new.json`.
- `stations_slim_format.json`: This is an updated version of our old data structure `../slim_stations/unique_stations.json` where the extra transfers and parent-child station relationships have been added. 
- `tfl_line_data.json`: This is the raw data response from API request. It is saved locally so can analyse locally going forward.  