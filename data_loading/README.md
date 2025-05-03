# Data Loading Package (`data_loading`)

## Purpose

This package is responsible for loading the pre-processed NetworkX transport graph data from its stored JSON file format. It reconstructs the graph structure, including nodes (stations/hubs) with their attributes and edges (connections/lines) with their weights (travel times), making it available for the main application logic.

## Modules

### `load_data.py`

Contains the function to load and parse the graph data.

#### Functions:

*   **`load_networkx_graph_and_station_data(graph_path)`**: Reads a JSON file specified by `graph_path`, parses the node and edge data (expecting specific keys like 'nodes', 'links'/'edges', 'id', 'source', 'target', 'key', 'weight', etc.), and constructs a `networkx.MultiDiGraph` object. It also creates and returns a lookup dictionary mapping station/hub names (node IDs) to their corresponding attribute dictionaries, which is useful for quick access to station details like coordinates and Naptan IDs. 