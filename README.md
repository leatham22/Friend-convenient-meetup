# London Transport Meeting Point Finder

A tool that helps groups of people find the most convenient London station to meet at, by analyzing everyone's nearest stations and calculating optimal meeting points that minimize total travel time.

## Project Overview

This project solves the common problem of finding a convenient place to meet in London when people are coming from different locations. It works by:
1. Taking each person's nearest station and walking time
2. Calculating journey times between all possible stations
3. Finding optimal meeting points that minimize total travel time for everyone

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

### Next Steps
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

| Metric | Old Approach | New Approach | Improvement |
|--------|--------------|--------------|-------------|
| Stations (Nodes) | 422 | 469 | +47 stations |
| Connections (Edges) | 712 | 1120 | +408 connections |
| Bidirectional Pairs | 354 | 557 | +203 pairs |
| Transfer Edges | 16 | 100 | +84 transfers |
| Isolated Stations | 83 | 0 | -83 (all connected) |
| Post-processing Required | Yes | No | Simplified workflow |

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
     - Live service disruptions (via TfL API)

5. **Utilities**
   - Station verification scripts
   - Missing station detection
   - Graph validation tools
   - Station name search functionality

## Directory Structure

```
project/
├── network_data/                     # Network graph generation and analysis scripts
│   ├── build_networkx_graph_new.py   # Main graph building script using TfL API sequences
│   ├── check_line_continuity.py      # Script to check for missing connections between stations
│   ├── networkx_graph_new.json       # The generated transport network graph
│   ├── tfl_line_data.json            # Raw data from TfL API used to build the graph
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
   - Create `.env` file: `TFL_API_KEY=your_key_here`

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

To ensure accurate journey time calculations, the project implements a sophisticated edge weight calculation system that uses the TfL Journey API to get real-world travel times between adjacent stations.

### Approach Overview

The system follows a multi-step process to obtain and store accurate travel times:

1. **Extract Per-Line Edge List**
   - Parses the network graph to identify all adjacent station pairs on each line
   - Groups edges by transport line (tube, DLR, overground, etc.)
   - Stores the station ID codes required for TfL API calls
   - Preserves station names for later reference

2. **API Data Collection**
   - Makes calls to the TfL Journey API for each adjacent station pair
   - Uses the format: `https://api.tfl.gov.uk/Journey/JourneyResults/{from-ID}/to/{to-ID}?mode={LineName}&date=2025-04-24&time=12:00&timeIs=Departing&journeyPreference=LeastTime`
   - Sets mode parameter to match the transport line (e.g., tube, dlr) to prevent shortcuts
   - Uses consistent date/time parameters for all queries to ensure comparable results
   - Processes only one line at a time to avoid overwhelming the API

3. **Data Storage**
   - Saves retrieved journey times to `weighted_edges.json`
   - Stores origin station, destination station, transport mode, line, and duration
   - Format is compatible with the existing graph structure

4. **Graph Integration**
   - Updates the edge weights in `networkx_graph_working.json` with the accurate journey times
   - Replaces default weights (1) with actual travel times in minutes

### Benefits

This approach offers several advantages:

- **Real-World Accuracy**: Uses actual TfL journey times instead of estimates
- **Mode-Specific Travel Times**: Ensures calculations are based on the correct transport mode
- **Consistent Measurement**: All times measured under the same conditions
- **API Efficiency**: Minimizes API calls by only querying adjacent stations
- **Maintainability**: Separates data collection from graph integration

### Usage

```bash
# Step 1: Extract per-line edge list
python network_data/extract_line_edges.py

# Step 2-3: Call API and save journey times (for testing with Waterloo-City line)
python network_data/get_journey_times.py --line waterloo-city

# Step 4: Merge journey times with graph
python network_data/update_edge_weights.py
```

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

# London Station Meeting Point Finder

This program helps find the optimal meeting point in London using public transport stations (Underground, Overground, DLR, and Rail).

## Algorithm Overview

The program uses a two-stage filtering process to efficiently find suitable meeting stations:

### Stage 1: Initial Filtering

For 2 people:
- Uses an elliptical boundary with the two starting stations as foci
- Major axis = 1.2 * direct distance between stations
- Important geometric note: If we had used major axis = direct distance, the ellipse would collapse to a line because:
  - In an ellipse, when major axis (2a) equals the distance between foci (2c)
  - Then semi-major axis (a) equals focal distance (c)
  - Using the ellipse formula b² = a² - c², we get b = 0
  - This would reject any station not exactly on the line between start points
- Using 1.2 * distance creates a reasonable search area that works well with stage 2

For 3+ people:
- Uses a convex hull containing all starting points
- Adds a small buffer (0.5%) to account for stations just outside the hull

### Stage 2: Centroid Filtering

- Calculates the centroid of all starting points
- Creates a circle that covers 70% of the starting points
- Only keeps stations from stage 1 that fall within this circle
- This helps eliminate outlier stations while maintaining a good selection of central meeting points

## Implementation Details

- Uses Haversine formula for accurate distance calculations on Earth's surface
- Includes 0.5% tolerance for geographic calculations to account for:
  - Earth's curvature effects
  - Numerical precision in floating-point calculations
  - Small deviations in station coordinate data

## Usage

[Add usage instructions here]