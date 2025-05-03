# London Transport NetworkX Graph

This directory contains the core modules for building and analysing the NetworkX graph representation of London's transport network.

## Directory Structure

-   `create_graph/`: Contains the sequential pipeline of Python scripts used to construct the weighted hub-based graph from raw data. This includes fetching data, calculating edge weights (transfers, line travel times), and assembling the final graph.
-   `analyse_graph/`: Contains scripts and utilities for analysing the generated graph, such as validation checks and potentially other analytical tools.
-   `data/`: Stores input data required by the graph creation and analysis scripts, including manually created files and raw data fetched from APIs.

## Building the Graph

To build the complete, weighted transport graph from scratch, navigate to the **project's root directory** (the parent directory of this `networkx_graph` folder) and run the build script using **either** of the following commands:

1.  Run as a module:
    ```bash
    python3 -m networkx_graph.build_graph
    ```
2.  Run directly:
    ```bash
    python3 networkx_graph/build_graph.py
    ```

Both commands execute the `build_graph.py` script and orchestrate the execution of all necessary steps defined within the `create_graph` sub-package.

---






