# Network Data

This directory contains scripts and data for building and analyzing the London transport network graph.

## Overview

The network_data directory is responsible for:
1. Fetching line and route sequence data from the TfL API
2. Building a comprehensive graph of the London transport network
3. Validating and analyzing the network structure
4. Storing the network graph in a usable format for journey planning

## Key Files

- **build_networkx_graph_new.py**: Main script that builds the transport network graph
- **check_line_continuity.py**: Validates the graph by checking for missing connections between stations
- **networkx_graph_new.json**: The generated graph data (nodes and edges)
- **tfl_line_data.json**: Raw data from the TfL API used to build the graph

## Recent Improvements

### Improved Line Continuity Checking

The `check_line_continuity.py` script has been completely overhauled to eliminate false positives and better handle branched lines:

1. **Automatic Branch Detection**: 
   - Identifies branch points by analyzing the network topology
   - Detects stations with more than 2 connections as branch points
   - No longer relies on hard-coded branch definitions

2. **Intelligent Sequence Building**:
   - Creates separate sequences for each branch in a line
   - Properly follows connections from branch points
   - Better handles complex network structures

3. **Smart Filtering**:
   - Automatically filters out potential false positives at branch points
   - Recognizes that not all stations on a line should be directly connected
   - Uses adjacency information to determine valid missing connections

4. **Zero False Positives**:
   - Eliminates incorrect reports of missing connections
   - Correctly understands branch structures for lines like District and Jubilee
   - Provides more accurate network validation

5. **Implementation Details**:
   - Branch points are algorithmically identified: `branch_points = {station for station in adjacency if len(adjacency[station]) > 2}`
   - Each branch is processed separately when tracing sequences
   - Missing connections at branch points are filtered out in the final stage

### Enhanced TfL API Data Processing

The scripts have been enhanced to better extract connection data from the TfL API:

1. **Improved stopPointSequences processing**: The build script now more thoroughly processes the stopPointSequences data, capturing more detailed branch information.

2. **Multiple data source fallbacks**: If stopPointSequences aren't available, the script now tries orderedLineRoutes and servicePatterns as fallbacks.

3. **Branch-aware connectivity checking**: The check_line_continuity script now correctly handles branched lines like the Northern and District lines, avoiding false positives.

4. **API-based validation**: Instead of relying on hardcoded connections, validation is now based on the actual network topology.

5. **No more manual connections**: All manual connection patching has been removed. The graph is now built entirely from TfL API data.

### Branch Information Support

The scripts now better handle branched lines by:

1. Extracting and utilizing branch metadata from the API
2. Preserving branch information in the graph edges
3. Using this information for more accurate connectivity validation
4. Algorithmically detecting branches rather than relying on static definitions

## MultiDiGraph Implementation

The latest version of the graph uses NetworkX's MultiDiGraph structure rather than a standard DiGraph. This change provides several important benefits:

### Why MultiDiGraph?

1. **Multiple edges between the same nodes**: Many stations in London are connected by multiple train lines (e.g., Circle and District lines share many stations). A standard DiGraph can only represent one edge between any two nodes, which means it can only represent one train line connecting any pair of stations.

2. **Line-specific attributes**: Each connection between stations has line-specific information (line name, mode, direction) that needs to be preserved.

3. **Accurate network representation**: The real transport network has multiple ways to travel between the same stations, and MultiDiGraph allows us to model this accurately.

### Implementation Details

- Each node represents a station with attributes like name, coordinates, and connected lines
- Each edge represents a connection between stations with attributes:
  - `line`: The TfL line ID (e.g., "district", "circle")
  - `line_name`: The official line name (e.g., "District Line", "Circle Line")
  - `mode`: Transport mode (e.g., "tube", "dlr")
  - `direction`: Travel direction ("inbound", "outbound")
  - `branch`: Branch information to handle complex line structures
  - `weight`: Travel time between stations
  - `transfer`: Boolean flag for zero-time transfers between parent/child stations
  - `key`: A unique identifier for the edge in the MultiDiGraph

### File Structure

The graph is saved as a JSON file with the following structure:

```json
{
  "nodes": {
    "Station Name 1": {
      "id": "station_id_1",
      "name": "Station Name 1",
      "lat": 51.123,
      "lon": -0.123,
      "zone": "1",
      "modes": ["tube"],
      "lines": ["district", "circle"],
      "child_stations": []
    },
    ...
  },
  "edges": [
    {
      "source": "Station Name 1",
      "target": "Station Name 2",
      "line": "district",
      "line_name": "District",
      "mode": "tube",
      "weight": 1,
      "transfer": false,
      "direction": "inbound",
      "branch": "route-1",
      "key": 0
    },
    ...
  ]
}
```

## How to Use

### Building the Network Graph

```bash
# Run from the root directory
python network_data/build_networkx_graph_new.py
```

This script:
1. Fetches line data from the TfL API (if not already cached)
2. Builds a MultiDiGraph structure
3. Adds station nodes and connection edges with branch information
4. Adds parent-child relationships for station transfers
5. Saves the graph to networkx_graph_new.json

### Validating the Network Graph

```bash
# Run from the root directory
python network_data/check_line_continuity.py

# Check a specific line
python network_data/check_line_continuity.py --line district
```

This script:
1. Loads the network graph
2. Analyzes station connections for each line
3. Identifies missing connections, accounting for branched lines
4. Reports issues with line continuity

## Notes on Parent-Child Station Relationships

The scripts now use absolute paths to locate `slim_stations/unique_stations.json` from the project root, ensuring it works correctly regardless of which directory the script is run from. This file contains important parent-child relationships between stations that share the same physical location but serve different transport modes (e.g., Underground and Overground stations).

These relationships are crucial for:
1. Creating zero-weight transfer edges between related stations
2. Ensuring the network is a single connected component
3. Enabling proper journey planning across different transport modes

If the file cannot be found, the script will still build the graph but with reduced connectivity between different transport modes.

## Future Improvements

1. Add edge weights based on actual journey times between stations
2. Improve handling of interchange/transfer stations
3. Add support for more detailed routing information
4. Include service disruption handling 