# London Transport Meeting Point Finder

A tool that helps groups of people find the most convenient London station to meet at, by analyzing everyone's nearest stations and calculating optimal meeting points that minimize total travel time.

## Project Overview

This project solves the common problem of finding a convenient place to meet in London when people are coming from different locations. It works by:
1. Taking each person's nearest station and walking time to said station
2. Calculating journey times between all possible stations
3. Finding optimal meeting points that minimize total travel time for everyone


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

## Technical Details

### Station Data Management
1. **Data Collection** (`scripts/collect_initial_stations.py`)
   - Uses TfL Line endpoint for reliability
   - Groups stations by HubNaptanCode/location
   - Handles multi-entrance stations

2. **Data Storage**
   - Raw data in `raw_stations/` (full TfL data)
   - Slim data in `slim_stations/` (optimized for processing)
   - Automatic backups in `station_backups/`

3. **Data Sync** (`scripts/sync_stations.py`)
   - Regular updates from TfL API
   - Smart station matching
   - Change verification system

4. **Station Name Normalization** (`normalize_stations.py`)
   - Standardizes station names across all data sources
   - Ensures station names in `station_graph.json` exactly match those in `slim_stations/unique_stations.json`
   - Main purpose: Allow looking up stations directly by name without requiring runtime normalization
   - Both files now use the exact same station names (not normalized):
     - Parent stations in `slim_stations/unique_stations.json` match parent stations in `station_graph.json`
     - Child stations in both files also match exactly
   - Integration with main program:
     ```python
     # No normalization needed - the exact same station names are used in both files
     
     # When looking up a station, use the same name in both files
     metadata = load_station_metadata()
     graph = load_station_graph()
     
     # Station names are exactly the same in both files
     # This is more efficient than normalizing at runtime
     ```
   - Handles special cases:
     - Stations with line indicators (e.g., "Baker Street (Metropolitan)" → "Baker Street Underground Station")
     - Stations with multiple entrances (mapped to their parent station)
     - Child stations mapping to parent stations
     - Abbreviations mapped to their full station names

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

## NetworkX vs TfL API Journey Time Analysis (New)

During development, a comparison was made between journey times calculated using the project's NetworkX graph and custom Dijkstra algorithm versus times retrieved from the official TfL Journey Planner API.

**Key Findings:**

1.  **Graph Calculation (Idealized Time):**
    *   The NetworkX graph stores *inter-station running times* as edge weights (`duration`).
    *   The custom Dijkstra algorithm sums these durations and adds a fixed 5-minute penalty for relevant line changes.
    *   This calculation represents an **idealized minimum travel time**, assuming instant train availability and transfers, focusing primarily on the time spent *moving* between stations.

2.  **TfL API Calculation (Scheduled Time):**
    *   The TfL API (using `journeyPreference=leasttime`, which appears to be the default for coordinate-based queries) calculates the fastest route based on **scheduled services**.
    *   This inherently includes significant additional time factors not present in the static graph data:
        *   Initial wait time for the next scheduled train.
        *   Wait times during transfers for connecting services.
        *   Standard dwell times (stops) at intermediate stations.
        *   Potential buffer times.
    *   This calculation represents a more realistic **scheduled journey time**, including necessary waiting periods.

3.  **Discrepancy and Ratio:**
    *   TfL API times were consistently longer than the NetworkX graph times for the same journeys, often by a factor of ~1.7x to ~2.7x.
    *   This difference is attributed to the API accounting for wait/dwell times, while the graph focuses on running time.
    *   The *ratio* between the two calculations is not constant across different journeys. This means the graph's idealized time doesn't perfectly predict the *relative* scheduled time difference between potential meeting points.

**Implications for the Project:**

*   The NetworkX graph stage effectively identifies candidate meeting stations with low *potential* travel time (minimal running time).
*   The subsequent TfL API calls on the top candidates provide a more conservative, schedule-based time estimate for final comparison.
*   The two-stage approach remains valid: the graph acts as an efficient filter based on idealized speed, and the API provides a schedule-aware refinement for the most promising options. Understanding the difference between the two calculations is crucial for interpreting the final results.

## Directory Structure

```
project/
├── network_data/                     # Network graph generation and analysis scripts
│   ├── build_networkx_graph_new.py   # Main graph building script using TfL API sequences
│   ├── check_line_continuity.py      # Script to check for missing connections between stations
│   ├── networkx_graph_new.json       # The generated transport network graph
│   ├── tfl_line_data.json            # Raw data from TfL API used to build the graph
│   ├── find_terminal_stations.py      # Identifies terminal stations for Tube/DLR lines based on graph connectivity
│   ├── get_timetable_data.py          # Fetches raw timetable data from TfL API using terminal stations and caches it per line
│   ├── line_edges.json               # Extracted adjacent station pairs, grouped by line
│   ├── terminal_stations.json         # Output of find_terminal_stations.py, mapping line IDs to their terminal station Naptan IDs
│   ├── weighted_edges.json            # (Partially deprecated) Stores journey times between stations (previously from get_journey_times.py). Will be updated later with timetable data
│   ├── timetable_cache/              # Directory containing cached raw timetable API responses, one JSON file per line (e.g., district.json)
│   └── ... other network analysis scripts
├── raw_stations/                     # Raw station data from TfL API
│   ├── unique_stations.json          # All stations
│   └── unique_stations_*.json        # Mode-specific stations
├── slim_stations/                    # Minimal station data for processing
│   ├── unique_stations.json          # All stations
│   └── unique_stations_*.json        # Mode-specific stations
├── Station_graph/                    # Station graph generation system
│   ├── create_station_graph.py       # Main graph generation script
│   ├── verify_graph.py               # Graph verification tools
│   ├── add_missing_stations.py       # Station completion tool
│   └── README.md                     # Component documentation
├── scripts/
│   ├── collect_initial_stations.py   # Fetch raw station data
│   ├── slim_stations.py              # Create minimal station data
│   ├── sync_stations.py              # Keep data in sync with TfL
│   └── compare_station_versions.py   # Compare data versions
├── requirements.txt                  # Python dependencies
├── .env                              # API key (not in repo)
└── .gitignore                        # Git ignore rules
```

## Setup

1. **Clone and Install**
   ```bash
   git clone [your-repo-url]
   python3 -m pip install -r requirements.txt
   ```

2. **API Key**
   - Get a free API key from [TfL API Portal](https://api-portal.tfl.gov.uk/)
   - Create `.env` file:
     ```
     TFL_API_KEY=YOUR_ACTUAL_API_KEY_HERE
     ```
   *(Note: A TFL App ID is no longer required)*

3. **Initial Setup**
   ```bash
   # Collect station data
   python3 scripts/collect_initial_stations.py
   
   # Create slim versions
   python3 scripts/slim_stations.py
   ```

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

## Edge Weight Calculation System

To ensure accurate journey time calculations, the project implements different methods depending on the transport mode.

**Tube & DLR Lines (Timetable Method - Primary)**

This is the **primary and preferred** method for most Tube and DLR lines as it uses official timetable data for potentially greater accuracy and consistency.

1. **Identify Terminal Stations**: The `network_data/find_terminal_stations.py` script analyzes the generated graph (`networkx_graph_new.json`) to find the endpoints (stations with only one connection on a specific line) for each Tube and DLR line. Results are saved to `network_data/terminal_stations.json`.

2. **Fetch Timetable Data**: `network_data/get_timetable_data.py` uses the identified terminals. For each line, it queries the TfL `/Line/{lineId}/Timetable/{fromStationId}` API endpoint, starting from each terminal. The raw JSON responses are cached in the `network_data/timetable_cache/` directory (e.g., `district.json`).

3. **Process Timetable Data**: `network_data/process_timetable_data.py` reads the cached data.
   - It calculates the time difference between consecutive stops in the timetable sequences to determine **directional** journey times (A -> B might differ from B -> A).
   - It only calculates durations for station pairs that exist as edges for that line in the base graph (`networkx_graph_new.json`), preventing the creation of edges for non-existent express segments.
   - If multiple durations are found for the same directional pair (e.g., from different branches or terminals), it averages these durations (rounded to 1 decimal, min 0.1).
   - It compares the calculated edges against the original Tube/DLR edges in the base graph and reports any discrepancies (edges existing in one but not the other).
   - The final, valid, directional edges with averaged durations are saved to `network_data/calculated_timetable_edges.json`.

**Overground, Elizabeth Line & Specific Tube/DLR Edge Cases (JourneyResults API Method - Fallback)**

For Overground and Elizabeth Line services, and for specific Tube/DLR segments where the Timetable API method is insufficient (e.g., known problematic branches like the DLR Stratford branch, complex loops like Heathrow T4, the Circle Line due to its looped nature and potential API data gaps, the Central Line Hainault loop, or specific operational segments like the DLR skipping West India Quay southbound), the TfL JourneyResults API is used as a fallback.

1.  **Extract Relevant Edges**: `network_data/extract_line_edges.py` needs modification to filter the graph and extract adjacent station pairs for Overground, Elizabeth Line, and the identified Tube/DLR edge cases (Circle, Heathrow T4 loop, Hainault loop, DLR Stratford branch, DLR WIQ southbound skip).

2.  **Query Journey Planner**: `network_data/get_journey_times.py` (originally designed for this) needs modification to:
    *   Use the filtered edge list.
    *   Query the TfL `/Journey/JourneyResults/{from_id}/to/{to_id}` endpoint for each pair.
    *   Crucially, set the `mode` parameter in the API call to match the specific line (e.g., `overground`, `elizabeth-line`, `dlr`, `tube`) to ensure the API calculates the time using that mode and doesn't find a faster route via a different mode.
    *   Handle potential errors or missing journeys gracefully.

3.  **Store Results**: Journey times are saved to `network_data/weighted_edges.json` (or separate file).

**Graph Integration**

A final script will be created to:
- Read the base graph (`networkx_graph_new.json`).
- Read the calculated durations from `calculated_timetable_edges.json` (Tube/DLR) and the JourneyResults output (Overground/Elizabeth).
- Update the `weight` attribute of the corresponding **directional** edges in the graph.
- Update the `weight` attribute of parent/child transfer edges (`transfer=True`) to a standard penalty (e.g., 5 minutes).
- Save the final, weighted graph.

**Pathfinding Considerations (MultiDiGraph)**

- The final graph is a **MultiDiGraph** where multiple edges (representing different lines) can exist between two stations.
- Pathfinding algorithms (Dijkstra/A*) should operate on this MultiDiGraph.
- **Transfer Penalty:** When traversing the graph, if the algorithm moves from an edge belonging to `line_A` to an edge belonging to `line_B` (where A is not B, and neither edge is a `transfer=True` edge), a time penalty (e.g., 2 minutes) should be added to the cumulative journey time to account for the line change.

## Workflow

1.  **Data Extraction & Graph Creation:**
    *   `network_data/tfl_line_data.json` is fetched/updated (if necessary) containing raw line/route data.
    *   `network_data/build_networkx_graph_new.py` uses this data and station metadata (`slim_stations/unique_stations.json`) to create `network_data/networkx_graph_new.json` with default edge weights of 1 for line segments and 0 for transfers. The graph is a **MultiDiGraph**.

2.  **Edge Weight Calculation (Tube/DLR - Timetable Method):**
    *   `network_data/find_terminal_stations.py` identifies line endpoints from the graph, saving to `network_data/terminal_stations.json`.
    *   `network_data/get_timetable_data.py` uses the terminals to fetch raw TfL Timetable API data for each line, caching responses in `network_data/timetable_cache/`.
    *   `network_data/process_timetable_data.py` processes the cached timetables:
        *   Calculates **directional** travel times between adjacent stations, **only for edges present in the base graph**.
        *   Averages durations for the same directional pair if multiple values exist.
        *   Reports discrepancies between calculated edges and the original Tube/DLR graph edges.
        *   Saves the processed directional edges with averaged durations to `network_data/calculated_timetable_edges.json`.

3.  **Edge Weight Calculation (Overground/Elizabeth Line & Tube/DLR Fallbacks - JourneyResults Method):**
    *   Filter graph edges for Overground/Elizabeth Line and specific Tube/DLR exceptions (Circle, Heathrow T4, Hainault, DLR Stratford, DLR WIQ skip) using `network_data/extract_line_edges.py`.
    *   Query TfL JourneyResults API for these pairs using `network_data/get_journey_times.py` (ensuring correct `mode` parameter).
    *   Results are saved to `network_data/weighted_edges.json` (or separate file).

4.  **Graph Update:**
    *   A script merges durations from `calculated_timetable_edges.json` and the JourneyResults output.
    *   This script updates the `weight` attribute for corresponding directional edges in `network_data/networkx_graph_new.json`. Transfer edge weights are updated to a standard penalty (e.g., 5 mins).

5.  **Analysis & Pathfinding:**
    *   Use the final, weighted MultiDiGraph (`network_data/networkx_graph_new.json`).
    *   Pathfinding algorithms (Dijkstra/A*) use edge `weight`.
    *   **Crucially, implement a check during pathfinding: if moving between edges `e1` and `e2` where `e1.line != e2.line` (and neither is a transfer edge), add a line change penalty (e.g., 2 mins) to the path cost.**

## Usage

1. **Find Meeting Points**
   ```bash
   python3 main.py
   ```
   - Enter each person's nearest station
   - Enter walking time to that station
   - Type 'done' when finished

2. **Update Station Data**
   ```bash
   python3 scripts/sync_stations.py
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Your chosen license]

## Network Data Generation and Processing (`network_data/`)

This directory is central to the project, containing the scripts and data files necessary for creating and weighting the London transport network graph.

1.  **Base Graph Creation**:
    *   `build_networkx_graph_new.py` constructs the fundamental graph structure (`networkx_graph_new.json`) using TfL API data. This initial graph includes nodes (stations) and edges (connections) but edges initially have their `weight` set to `null`.

2. **Tube/DLR Edge Weight Calculation**:
    *   A two-step process generates `Edge_weights_tube_dlr.json`:
        *   **Timetable Processing**: `find_terminal_stations.py` -> `get_timetable_data.py` (caches data) -> `process_timetable_data.py` calculates most Tube/DLR weights based on TfL timetables, handling discrepancies by averaging.
        *   **Missing Edge Handling**: `get_missing_journey_times.py` specifically targets a small set of Tube/DLR edges not covered by the timetable method. It calls the TfL Journey API (adapting parameters for DLR) to get their durations and appends them to the file created by the previous step.

3.  **Other Line Edge Weight Calculation (TODO)**:
    *   A similar process using the TfL Journey API will be needed for Overground and Elizabeth lines.

4.  **Final Graph Update (TODO)**:
    *   A future script will merge the weights from `Edge_weights_tube_dlr.json` (and eventually other lines) back into `networkx_graph_new.json`, updating the `weight` attribute from `null` to the calculated duration. Transfer edge weights will also be set.

This weighted graph is then used for finding optimal meeting points.

## Project Setup
