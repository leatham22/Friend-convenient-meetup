# Network Data

This directory contains scripts and data for building and analyzing the London transport network graph.

## Overview

The network_data directory is responsible for:
1. Fetching line and route sequence data from the TfL API
2. Building a comprehensive graph of the London transport network
3. Calculating journey times (weights) between stations for different lines.
4. Validating and analyzing the network structure
5. Storing the network graph and calculated edge weights in usable formats.

## Key Files

- **build_networkx_graph_new.py**: Main script that builds the base transport network graph (nodes and edge structure) without calculated weights.
- **networkx_graph_new.json**: The base graph data (nodes and edges with `weight=null`).
- **process_timetable_data.py**: Processes cached TfL timetable data to calculate initial edge weights for Tube and DLR lines, saving results to `Edge_weights_tube_dlr.json`.
- **get_missing_journey_times.py**: Fetches journey times via TfL Journey API for specific Tube/DLR edges missed by the timetable process and appends them to `Edge_weights_tube_dlr.json`.
- **Edge_weights_tube_dlr.json**: Contains calculated edge weights (durations) for Tube and DLR lines, derived from both timetable processing and direct API calls.
- **find_terminal_stations.py**: Identifies terminal stations for Tube/DLR lines, used by `get_timetable_data.py`.
- **get_timetable_data.py**: Fetches raw timetable data from TfL API using terminals and caches it in `timetable_cache/`.
- **timetable_cache/**: Directory containing cached raw timetable data per line.
- **check_line_continuity.py**: Validates the graph by checking for missing connections between stations.
- **tfl_line_data.json**: Raw line/route sequence data from the TfL API used to build the base graph.
- **terminal_stations.json**: Output of `find_terminal_stations.py`.
- **get_journey_times.py**: (Legacy for Tube/DLR, potentially for Overground/Elizabeth) Uses TfL Journey API to calculate times for *individual* station pairs.
- **line_edges.json**: (Legacy) Output of `extract_line_edges.py`, listing unique adjacent station pairs per line.
- **weighted_edges.json**: (Legacy) Stores journey times from the old `get_journey_times.py` method.

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

2. **Line-specific attributes**: Each connection between stations has line-specific information (line name, mode, direction) that needs to be preserved. This is crucial for pathfinding algorithms.

3. **Accurate network representation**: The real transport network has multiple ways to travel between the same stations, and MultiDiGraph allows us to model this accurately.

4. **Pathfinding with Transfer Penalties**: Using a MultiDiGraph with line information stored on the edges allows pathfinding algorithms (like Dijkstra or A*) to identify when a path switches lines. By inspecting the `line` attribute of consecutive edges in a path, a transfer penalty (e.g., 2 minutes) can be added when a line change occurs. This makes the calculated journey times more realistic.

### Implementation Details

- Each node represents a station with attributes like name, coordinates, and connected lines
- Each edge represents a connection between stations with attributes:
  - `line`: The TfL line ID (e.g., "district", "circle") - **Crucial for pathfinding line change detection.**
  - `line_name`: The official line name (e.g., "District Line", "Circle Line")
  - `mode`: Transport mode (e.g., "tube", "dlr")
  - `direction`: Travel direction ("inbound", "outbound")
  - `branch`: Branch information to handle complex line structures
  - `weight`: Travel time between stations in minutes (to be updated from calculated data).
  - `transfer`: Boolean flag for transfers between parent/child stations (True) or regular line travel (False).
  - `key`: A unique identifier for the edge in the MultiDiGraph (less critical for pathfinding but useful for graph manipulation).

- **Parent/Child Transfers**: Edges where `transfer` is True represent walking transfers within a station complex (e.g., between platforms for different lines at the same station). These currently have a weight of 0 but will be updated to a standard transfer time (e.g., 5 minutes) during the graph update phase.

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

## Workflow

1.  **Graph Generation:** `build_networkx_graph_new.py` uses raw TfL line/route data (`tfl_line_data.json`) and station metadata (`../slim_stations/unique_stations.json`) to create `network_data/networkx_graph_new.json`. This graph is a **MultiDiGraph**. Edges representing line segments initially have `weight=null`. Parent-child transfer edges have a weight of 0.

2.  **Edge Weight Calculation (Tube/DLR Lines - Two-Step Process):**
    a.  **Timetable Processing:**
        i.  `find_terminal_stations.py`: Identifies terminal stations for Tube/DLR lines -> `terminal_stations.json`.
        ii. `get_timetable_data.py`: Fetches raw TfL Timetable API data using terminals -> caches in `network_data/timetable_cache/`.
        iii. `process_timetable_data.py`: Processes cached data, calculates initial **directional** journey times only for *existing edges* in the base graph, handles discrepancies (averaging), and saves results to `Edge_weights_tube_dlr.json`.
    b.  **Handling Missing Edges:**
        i.  `get_missing_journey_times.py`: Reads the current `Edge_weights_tube_dlr.json`. Identifies a predefined list of Tube/DLR edges that were *not* calculated by the timetable process (often due to API limitations or specific service patterns).
        ii. For these specific missing edges, it calls the TfL Journey API (omitting date/time for DLR) to get durations.
        iii. It averages durations if multiple valid ones are returned and appends these newly weighted edges back to `Edge_weights_tube_dlr.json`.

3.  **Edge Weight Calculation (Overground/Elizabeth Line - JourneyResults Method):**
    a.  *(TODO)* `network_data/extract_line_edges.py`: Needs modification to filter for Overground/Elizabeth Line modes from the base graph.
    b.  *(TODO)* `network_data/get_journey_times.py` (or a new script): Needs modification to use the filtered list and query the TfL JourneyResults API.
    c.  *(TODO)* Results need to be stored (e.g., a separate `Edge_weights_other.json` or appended to the main weight file).

4.  **Graph Update:**
    a.  *(Next Step)* A script will be created to merge the durations from `Edge_weights_tube_dlr.json` (and eventually Overground/Elizabeth Line results) into the base graph.
    b.  *(Next Step)* This script will update the `weight` attribute (currently `null`) for the corresponding directional edges in `network_data/networkx_graph_new.json`. Parent/child transfer edges (`transfer=True`) will also have their weights updated to a standard transfer time (e.g., 5 minutes).

5.  **Analysis & Pathfinding:**
    *   Use the final, weighted MultiDiGraph (`networkx_graph_new.json`) for network analysis and meeting point calculations.
    *   Pathfinding algorithms (Dijkstra/A*) will use the `weight` attribute for travel time.
    *   **During pathfinding, the algorithm needs to check the `line` attribute of consecutive edges in the path. If `edge_n.line != edge_n+1.line` (and neither is a transfer edge), a transfer penalty (e.g., 2 minutes) should be added to the total journey time.** 

1.  **`build_networkx_graph_new.py`**: 
    *   **Input**: Raw line sequence data (cached `tfl_line_data.json` or fetched from API).
    *   **Process**: Constructs a base `networkx` MultiDiGraph using `stopPointSequences` data. Identifies stations (nodes) and connections (edges). 
    *   **Output**: `networkx_graph_new.json`. 
        *   Nodes represent stations with details (ID, name, lat/lon, modes, lines, zone).
        *   Edges represent potential connections between stations for specific lines.
        *   **Crucially, edge `weight` attributes are initialized to `null` (JSON for Python's `None`)** to signify that travel time hasn't been calculated yet. 
        *   This script handles parent-child station relationships for transfers (e.g., different entrances/platforms) by adding zero-weight transfer edges.
        *   It also incorporates specific fixes, like removing incorrect Metropolitan line assignments at Willesden Green and skipping the southbound DLR edge from Westferry to West India Quay.
        *   The script now uses only the `TFL_API_KEY` for authentication.

2.  **`update_edge_weights.py` (Located in `dev/original_Station_graph/`)**:
    *   **Purpose**: This was a one-time script used to initialize all edge weights in an existing `networkx_graph_new.json` to `null`. 
    *   **Status**: Archived. The weight initialization step is now integrated directly into `build_networkx_graph_new.py`.

3.  **`find_terminal_stations.py`**: 
    *   **Input**: `networkx_graph_new.json`.
    *   **Process**: Analyzes the graph to identify potential terminal stations for Tube and DLR lines based on connectivity (nodes with degree 1 for a given line).
    *   **Output**: `terminal_stations.json` (list of terminal station Naptan IDs per line).

4.  **`get_timetable_data.py`**: 
    *   **Input**: `terminal_stations.json`.
    *   **Process**: Uses the identified terminals to query the TFL Timetable API (`/Line/{id}/Timetable/{stationId}`). Fetches detailed schedule data for each line starting from its terminals. It now uses only the `TFL_API_KEY`.
    *   **Output**: Caches raw API responses in `timetable_cache/` (one JSON file per line, e.g., `bakerloo.json`).

5.  **`process_timetable_data.py`**: 
    *   **Input**: `timetable_cache/` directory and `networkx_graph_new.json` (for validation).
    *   **Process**: 
        *   Reads cached timetables.
        *   Calculates the average journey duration for each **directional** segment (e.g., Station A -> Station B on Line X) found in the timetables.
        *   Only processes segments that correspond to existing edges for that line in `networkx_graph_new.json`.
        *   Averages durations if multiple values exist for the same directional pair.
        *   Compares the set of processed edges against the original Tube/DLR edges from the graph and reports discrepancies (missing edges in either direction).
    *   **Output**: `calculated_timetable_edges.json` (list of directional Tube/DLR edges with calculated average durations in minutes).

6.  **`merge_travel_times.py`**: 
    *   **Input**: `networkx_graph_new.json` (with null weights), `calculated_timetable_edges.json`.
    *   **Process**: 
        *   Reads the base graph and the calculated timetable edge durations.
        *   Updates the `weight` attribute of corresponding **directional** edges in the graph data with the calculated durations from the timetable data.
        *   *Future Enhancement*: This script will be expanded to also read journey times calculated using the JourneyResults API (for Overground, Elizabeth Line, and timetable fallbacks) and merge those weights as well.
        *   *Future Enhancement*: It should also set a standard weight (e.g., 2 minutes) for transfer edges (where `transfer` attribute is `True`).
    *   **Output**: `networkx_graph_final.json` (The final graph intended for pathfinding, where edge weights represent travel times in minutes or are `null` if no time could be calculated). 