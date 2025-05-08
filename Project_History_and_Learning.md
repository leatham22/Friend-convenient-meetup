# London Transport Meeting Point Finder

A tool that helps groups of people find the most convenient London station to meet at, by analyzing everyone's nearest stations and calculating optimal meeting points that minimize total travel time.

## Project Overview

This project solves the common problem of finding a convenient place to meet in London when people are coming from different locations. It works by:
1. Taking each person's nearest station and walking time to said station
2. Calculating journey times between all possible stations
3. Finding optimal meeting points that minimize total travel time for everyone


## Latest Implementation: Hub-Based Graph & Weight Calculation

**Status: Completed & Validated**

The project has undergone a significant refactoring towards a **hub-based graph model** to improve pathfinding robustness and simplify transfer handling. This involves several key steps and scripts located in `networkx_graph/create_graph/`:

1.  **Base Hub Graph (`build_hub_graph.py`):**
    *   Creates a graph (`networkx_graph/graph_data/networkx_graph_hubs_base.json`) where each node represents a single station *hub*.
    *   Adds edges representing *line* connections between different hubs, initially with `null` weights.

2.  **Proximity Transfers (`add_proximity_transfers.py`):**
    *   Identifies geographically close hub nodes that lack direct line connections.
    *   Adds potential walking transfer edges (`transfer=True`) between these hubs, also with initial `null` weights.
    *   Outputs `networkx_graph/graph_data/networkx_graph_hubs_with_transfers.json`.

3.  **Transfer Weight Calculation (`calculate_transfer_weights.py`):**
    *   Uses the TfL Journey API (walking mode) to calculate durations for the proximity transfer edges.
    *   Outputs `networkx_graph/graph_data/networkx_graph_hubs_with_transfer_weights.json` (graph with weighted transfers).

4.  **Line Edge Weight Calculation:**
    *   Tube/DLR weights calculated via timetable data (`get_tube_dlr_edge_weights.py`).
    *   Overground/Elizabeth line weights calculated via Journey API (`get_overground_Elizabeth_edge_weights.py`).
    *   Both append results to `networkx_graph/graph_data/calculated_hub_edge_weights.json`.

5.  **Final Graph Update (`update_graph_weights.py`):**
    *   Reads the graph with weighted transfers (`...with_transfer_weights.json`).
    *   Reads the consolidated line edge weights (`calculated_hub_edge_weights.json`).
    *   Updates the `weight` attribute for all line edges.
    *   Outputs the final, fully weighted graph: **`networkx_graph/graph_data/networkx_graph_hubs_final_weighted.json`**. This file is the complete network representation ready for analysis and pathfinding.

**Progression Update:** The main script (`main.py`) and the debug script (`debug_compare_times.py`) have now been updated to load and correctly interpret the structure of this final hub-based graph (`networkx_graph_hubs_final_weighted.json`).

**UX Improvement:** Hub nodes in the graph now store a list of their constituent stations, including names and Naptan IDs (under the `constituent_stations` key). The main script (`main.py`) uses this data to prompt users to select their specific starting station when their input matches a multi-station hub, improving accuracy.

**Next Steps:** Analyze the final graph using scripts in `networkx_graph/analyse_graph/`.

---

LUDOS COMMENT: AT TIME OF WRITING SCRIPTS THEY WORK AS PLANNED. HOWEVER, TFL MAY RELEASE UPDATES SO CHECK WITH API FOR CHANGES.

## Project Status

### Current Features
- ✅ Station data management system
  - Reliable data collection from TfL API
  - Proper handling of multi-entrance stations
  - Regular sync with TfL data
- ✅ Station name normalization system
  - Direct normalization of station names between metadata and graph
  - Mapping between station_graph.json and slim_stations/unique_stations.json
  - Enhanced comparison and validation tools
  - Added disconnected stations detection for graph validation
- ✅ Improved TFL API Data Extraction
  - Using stopPointSequences for accurate station sequences
  - Better connection data based on API-provided sequences
  - More accurate network representation
- ✅ Enhanced graph structure with MultiDiGraph
  - Support for multiple train lines connecting the same stations
  - Preservation of line-specific connection data
  - More accurate representation of the London transport network
- ⏳ Meeting point optimization (in progress)
  - Journey time calculations
  - Total travel time minimization
  - Walking time consideration

### Edge Weight Calculation and Validation (New)

A significant part of the project involves calculating realistic travel times (edge weights) between adjacent stations. This has been achieved through two main methods:

1.  **Tube/DLR Lines:** Primarily uses processed TfL Timetable API data (`network_data/process_timetable_data.py`), supplemented by direct TfL Journey API calls for specific missing edges (`network_data/get_missing_journey_times.py`). Results are stored in `network_data/Edge_weights_tube_dlr.json`.
2.  **Overground/Elizabeth Line:** Uses the TfL Journey API exclusively due to timetable data limitations (`network_data/get_journey_times.py`). Results are stored in `network_data/Edge_weights_overground_elizabeth.json`.

Robust validation scripts (`network_data/check_missing_edges.py`, `network_data/analyze_edge_weights.py`) were developed and run to ensure these calculated weights were consistent with the base network graph structure (`network_data/networkx_graph_new.json`) and to check for data quality issues like schema adherence, duration outliers, and journey time symmetry.

**Graph Finalization:** The calculated weights from `Edge_weights_tube_dlr.json` and `Edge_weights_overground_elizabeth.json`, along with standardized transfer weights, have now been integrated into the main network graph file (`network_data/networkx_graph_new.json`). This file represents the final, weighted MultiDiGraph needed for pathfinding. See `network_data/README.md` for details on the update scripts used.

### Latest Updates
1. **Improved Line Continuity Checking**
   - Completely redesigned branch detection algorithm using network topology analysis
   - Automatically identifies branch points (stations with more than 2 connections)
   - Creates proper sequence tracing for each branch
   - Eliminated false positives for missing connections at branch points
   - Removed reliance on hard-coded branch definitions
   - More accurate representation of the actual London transport network with proper branches

2. **Improved Network Graph Structure**
   - Migrated from NetworkX's DiGraph to MultiDiGraph to properly represent multiple train lines connecting the same stations
   - Fixed issue where only one connection was preserved when multiple lines connect the same stations (like Circle and District lines sharing stations)
   - Each edge now preserves its specific line information without overwriting other connections
   - More accurate representation of the transport network with proper line-specific connections
   - Better support for line continuity validation and journey planning
   - Added key attribute to edge data to uniquely identify edges in the MultiDiGraph structure

3. **Improved Network Graph Building**
   - Implemented a new approach using `stopPointSequences` from the TFL API
   - More accurate representation of connections between stations
   - No need for graph_fixer to repair connections thanks to proper sequence data
   - Better handling of branch lines and service patterns
   - Improved bidirectional connections for more realistic journey planning

4. **Station Name Normalization Improvement**
   - Updated `normalize_stations.py` to ensure exact name matching between graph and metadata
   - Created `compare_station_names.py` for direct validation of station name alignment
   - Now using normalized names across all components for consistent station lookup
   - The graph now contains the exact same station names as the metadata file
   - Fixed handling of similarly named stations (e.g., "Euston" and "Euston Square" are now properly distinct)
   - Improved station name normalization logic to prevent incorrect grouping of distinct stations
   - Consolidated Edgware Road stations: The two Edgware Road stations (Circle Line and Bakerloo) are now represented as a single parent station with the Bakerloo station as a child station for more accurate journey planning
   - Added `check_disconnected_stations.py` to identify isolated stations or disconnected components in the graph

5. **Code Organization**
   - Separated raw and processed data
   - Improved script organization
   - Added data validation tools
   - Moved deprecated scripts to `dev/` directory for historical reference

6. **API Call Logic (TfL Journey Planner)**
   - Updated the logic in `main.py` and `debug_compare_times.py` to use station Naptan IDs instead of latitude/longitude coordinates when calling the TfL Journey Planner API.
   - This change improves the accuracy of journey results by directly referencing specific station infrastructure rather than potentially ambiguous geographic points.
   - The Naptan ID for each station is sourced from the `id` field in the `slim_stations/unique_stations.json` file.

7. **Planned Graph Restructure & Improved Transfers (Multi-Step)**
   - **Problem:** Pathfinding failures identified due to incomplete/missing transfer edges between different modes within station hubs (e.g., Stratford) and between geographically close hubs (e.g., Hammersmith stations).
   - **Solution:** Refactor the graph building into a multi-step process:
     - **Step 1 (`build_hub_graph.py`):** Create a base graph with **one single node per station hub** (grouping by `topMostParentId`). This node aggregates modes, lines, and NaptanIDs. Add *line* edges between these hubs (`transfer=False`, `weight=null`). This eliminates intra-hub transfers and the dependency on `slim_stations/unique_stations.json`.
     - **Step 2 (`add_proximity_transfers.py`):** Use the TfL StopPoint proximity API to find geographically close hub nodes that lack a direct line connection. Add bidirectional `transfer=True`, `mode='walking'`, `weight=null` edges for these pairs. Output the modified graph and a list of these transfers.
     - **Step 3 (`calculate_transfer_weights.py`):** Use the TfL Journey API (`mode=walking`) to calculate durations for the proximity-based transfer edges identified in Step 2 and update their weights in the graph.
     - **Step 4 (Future):** Calculate/update weights for the *line* edges using timetable/journey API data.

### Next Steps
- [ ] **Implement `build_hub_graph.py` (Step 1: Single node per hub, line edges only).**
- [ ] **Implement `add_proximity_transfers.py` (Step 2: Find/add null-weighted walking transfers).**
- [ ] **Implement `calculate_transfer_weights.py` (Step 3: Calculate walking transfer weights).**
- [ ] Complete validation for DLR and Overground stations in the graph
- [ ] Implement journey time calculations
- [ ] Add meeting point optimization algorithm
- [ ] Create user interface for input/output
- [ ] Add support for additional transport modes

## TFL API Data Extraction Improvements

### Previous Approach Problems
The previous approach had several significant issues:
1. **Inaccurate Connection Data**: Used `lineStrings` data which only contained geographical coordinates without any indication of actual station connections
2. **Complex Coordinate Matching**: Required complex coordinate-to-station matching logic, trying to guess which stations were connected based on proximity
3. **Missing Connections**: Failed to identify many valid connections between stations
4. **Incorrect Connections**: Created connections between stations that aren't actually connected
5. **Post-Processing Required**: Required a `graph_fixer.py` script to repair connectivity issues
6. **Isolated Stations**: Left 83 stations disconnected from the network
7. **Incomplete Coverage**: Missed important stations like "Farringdon" and "Canary Wharf"
8. **Development Complexity**: Required complicated workarounds for problematic stations

### New Approach Benefits
The new implementation (`build_networkx_graph_new.py`) resolves these issues with several improvements:
1. **Direct Sequence Data**: Uses `stopPointSequences` section which contains the exact sequence of stations on each line, directly from TFL
2. **Station IDs**: Works directly with station IDs (NaptanIDs) rather than imprecise coordinate matching
3. **Direction-aware**: Captures inbound/outbound direction information
4. **Branch Handling**: Properly handles line branches and route variations
5. **Fallback Mechanism**: Falls back to `orderedLineRoutes` if `stopPointSequences` is unavailable for any line
6. **Better Parent-Child Station Handling**: More accurate representation of transfers between parent and child stations
7. **Comprehensive Coverage**: Increases node count from 422 to 469 stations
8. **Complete Connectivity**: Eliminates all isolated stations (83 → 0)
9. **More Accurate Connections**: Increases edge count from 712 to 1120 connections
10. **Bidirectional Representation**: Increases bidirectional pairs from 354 to 557 for better route planning
11. **Better Transfer Representation**: Increases transfer edges from 16 to 100 for more accurate interchange modeling

### Measurable Improvements
A direct comparison of the old and new approaches shows:

| Metric              | Old Approach | New Approach | Improvement |
|---------------------|--------------|--------------|-------------|
| Stations (Nodes)    | 422          | 469          | +47 stations |
| Connections (Edges) | 712          | 1120         | +408 connections |
| Bidirectional Pairs | 354          | 557          | +203 pairs |
| Transfer Edges      | 16           | 100          | +84 transfers |
| Isolated Stations   | 83           | 0            | -83 (all connected) |
| Post-processing Required | Yes     | No           | Simplified workflow |

### Implementation Details
- Each station in `stopPointSequences` contains complete information (ID, name, coordinates, lines, modes, etc.)
- Station connections are created directly from sequence order rather than geographic proximity
- Parent-child relationships are still maintained for transfer connections
- Direction information is preserved in edge attributes for potential future use in routing algorithms

### Usage
To use the new graph building approach:
```bash
python network_data/build_networkx_graph_new.py
```
The new graph will be saved to `network_data/networkx_graph_new.json`.

## New Graph Building Approach

### TFL API Integration
1. **Direct Line Sequence Data**
   - Using TFL's Line_RouteSequenceByPathIdPathDirectionQueryServiceTypesQueryExcludeCrowding API endpoint
   - Provides station-by-station sequences for each transport line
   - Contains complete station coordinates and line connections
   - Eliminates previous deduplication hacks and station matching issues

2. **Graph Construction Process**
   - Builds station network directly from TFL sequence data
   - Each station contains:
     - Station name and ID
     - Geographical coordinates (latitude/longitude)
     - Connected lines and modes of transport
     - Zone information
     - Parent/child station relationships
   - Edges between stations represent direct connections with travel times
   - Zero-time transfers for parent-child station relationships

3. **Advantages of New Approach**
   - More accurate station positioning
   - Complete coverage of all transport modes
   - Better handling of line branches and directions
   - Simplified station matching with authoritative TFL data
   - Future-proof for station additions and line changes
   - Compatible with NetworkX for advanced graph operations

4. **Implementation Details**
   - Station data stored with full TFL attributes
   - Line data organized by mode of transport
   - Child-parent relationships preserved for zero-transfer connections
   - Edges weighted by journey time between stations



### Graph as Single Source of Truth (Runtime)

For runtime operations like finding meeting points (`main.py`) and debugging journey times (`debug_compare_times.py`), the project now exclusively relies on the data embedded within the NetworkX graph file (`network_data/networkx_graph_new.json`).

- **Data Source**: All necessary station information (including names, Naptan IDs, latitude, longitude) is extracted directly from the *node attributes* within the graph JSON.
- **Consistency**: This ensures that the station names, IDs, and coordinates used for pathfinding (Dijkstra), filtering, and TfL API calls are inherently consistent with the graph structure itself.
- **Simplified Dependencies**: This approach removes the runtime dependency on the separate `slim_stations/unique_stations.json` file for the core application logic, simplifying data handling.

Note: The `slim_stations/unique_stations.json` file is still used during the initial *graph building* process (`network_data/build_networkx_graph_new.py`) to help establish the parent-child relationships and metadata that get embedded into the final graph file.

### Station Graph System (`Station_graph/`)
1. **Graph Generation**
   - Creates a directed graph of London transport stations
   - Calculates travel times between connected stations
   - Handles station name normalization and special cases
   - Automatically maps child platforms to parent stations
   - Currently focused on Underground stations; DLR and Overground stations being added

2. **Data Sources**
   - Uses `raw_stations/unique_stations2.json` for station information
   - Uses `Inter_station_times.csv` for travel times
   - Outputs `station_graph.json` with the complete graph
   - Note: Travel time data for DLR and Overground stations is being added to complete the network

3. **Key Features**
   - Directional travel times between stations
   - Automatic free transfers at the same station
   - Handles special station cases (e.g., Heathrow terminals)
   - Includes verification and validation tools

4. **Journey Time Optimization**
   - Graph-based pathfinding using Dijkstra/A* algorithm (in progress)
   - Will identify top 10 fastest journey options for meeting points
   - Results feed into TfL API for real-time journey planning
   - Takes into account:
     - Direct travel times between stations
     - Transfer times at interchange stations
     - Walking times from starting locations




## Development Progress

### Latest Updates
1. **Station Data Management**
   - Switched to Line endpoint for better reliability
   - Improved station grouping using HubNaptanCode
   - Added child station tracking for better matching
   - Updated metadata to include one entry for Bakersreet
   - Moved outdated validation scripts (compare_station_names.py, find_missing_csv_entries.py, check_csv_stations.py, find_missing_stations.py, debug_csv.py) to dev/outdated_scripts/

2. **Code Organization**
   - Separated raw and processed data
   - Improved script organization
   - Added data validation tools

3. **Documentation**
   - Added detailed code comments
   - Improved README documentation
   - Added progress tracking

### Known Issues
- Some station location discrepancies (mostly minor)
- Elizabeth Line station data needs verification
- Some station name variations need standardization
- DLR and Overground stations are currently missing from the graph structure (in progress)

## Development History

### Initial Development Journey
1. **First Approach: Direct API Usage**
   - Created `test_api.py` to test initial API integration
   - Used StopPoint API endpoint for all operations:
     - First call: Validate input station names
     - Second call: Get stations within radius of group center
   - Performance Issues:
     - 1700+ stations returned for central London
     - 5+ minutes to process just 15/1700 stations
     - Journey time calculations too slow for practical use

2. **Data Investigation**
   - Created `inspect_api_data.py` to analyze API response structure
   - Generated `api_response.json` for detailed data inspection
   - Discovered duplicate entries issue:
     - Multiple entries for entrances, platforms, facilities
     - Found station identification patterns:
       - HubNaptanCode for main stations
       - NaptanID patterns (910G/940G for parents, 9100/9400 for children)
   - Reduced stations from 1700+ to ~466 unique locations
   - Created `compare_stations.py` to validate data accuracy

3. **Local Data Storage Evolution**
   - Realized journey time API only needed lat/long
   - Created local station database to avoid repeated API calls
   - Created `consolidated_stations.py` for initial data structure
   - Implemented station validation using local data
   - Added fuzzy matching for station names

4. **API Endpoint Optimization**
   - Discovered more efficient Line endpoint
   - Created `create_station_mapping.py` for initial mapping attempt
   - Benefits over StopPoint endpoint:
     - Fewer duplicates
     - More reliable data
     - Better structured responses
   - Solved overground stations issue:
     - Updated to new line naming convention (Windrush, etc.)
     - Individual calls for each line

5. **Data Structure Refinement**
   - Created `collect_initial_stations.py` using Line endpoint
   - Created `compare_station_versions.py` to validate new structure
   - Created `slim_stations.py` for optimized data storage
   - Created `sync_stations.py` for automated updates
   - Created `analyze_location_diffs.py` to investigate coordinate differences
   - Implemented:
     - Unified station format
     - Parent-child station relationship
     - Smart deduplication while preserving all station names
     - Location differences investigation (platform vs entrance coordinates)

### API Optimization Journey
1. **Initial Implementation** (see `dev/` folder)
   - Originally made multiple API calls:
     - Two calls to StopPoints endpoint (validation + radius search)
     - Additional calls for journey times
   - Created local data structure to reduce API calls
   - Used `compare_stations.py` to validate data accuracy

2. **Current Optimized Implementation**
   - Single Line endpoint call for all station data
   - Local data storage with efficient sync system
   - Reduced API calls from 3+ to 1 per session
   - Smart station matching using fuzzy logic
   - Optimized data structure for quick lookups

### Data Structure Evolution
1. **Original Structure**
   - Separate files for each transport mode
   - Multiple API calls for validation
   - Basic station matching

2. **Current Structure**
   - Unified station data with mode information
   - Smart deduplication using HubNaptanCode
   - Efficient sync process with fuzzy matching
   - Backup system for data safety

### Performance Improvements
1. **API Usage**
   - Reduced from 3+ API calls to 1
   - Implemented local data storage
   - Smart sync system for updates

2. **Data Processing**
   - Improved station matching algorithm
   - Optimized data structure for quick lookups
   - Added fuzzy matching for better accuracy

3. **Code Organization**
   - Separated active and historical code
   - Improved script organization
   - Better error handling and validation





*(Previous README content below this point may refer to the deprecated workflow and should be reviewed/updated/removed as needed)*
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

## Edge Weight Calculation (Overground/Elizabeth Line)

The process for obtaining edge weights for Overground and Elizabeth line services differs from the Tube/DLR method due to limitations in the TfL Timetable API for these modes.

-   **`get_journey_times.py`**: This script now specifically targets Overground and Elizabeth line station pairs defined in `line_edges.json`.
    -   It calls the TfL Journey Results API for each adjacent station pair (in both directions).
    -   It implements logic to average multiple valid journey times returned by the API, applying thresholds similar to `get_missing_journey_times.py`.
    -   It ensures a minimum journey time (e.g., 1.0 minute) and handles potential API errors.
    -   It saves the calculated edges directly to `Edge_weights_overground_elizabeth.json`.
-   **`Edge_weights_overground_elizabeth.json`**: Contains the calculated edge weights (durations) specifically for Overground and Elizabeth line services.

## Data Validation and Analysis

Several scripts are available to validate and analyze the generated graph and weight data:

-   **`check_line_continuity.py`**: Validates the graph structure by checking for expected connections between adjacent stations on each line, accounting for branches.
-   **`check_missing_edges.py`**: Compares the edges defined in the base graph (`networkx_graph_new.json`) against the calculated weight files (`Edge_weights_tube_dlr.json` and `Edge_weights_overground_elizabeth.json`). It checks for discrepancies in both directions:
    -   Edges in the graph but missing weights.
    -   Edges with weights but not present in the graph for the corresponding mode.
-   **`analyze_edge_weights.py`**: Performs deeper analysis on the weight files:
    -   **Duration Sanity Check**: Flags edges with unusually high or low journey times.
    -   **Symmetry Analysis**: Compares forward (A->B) and reverse (B->A) journey times for the same pair, highlighting significant differences.
    -   **Schema Verification**: Checks if all records contain the expected fields and data types.
-   **`apply_arbitrary_timestamp.py`**: A utility script to add/overwrite the `calculated_timestamp` field in weight files, used primarily to ensure schema consistency for records generated before timestamping was implemented.

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
