# Development Archive

This directory contains scripts that were historically important in the development process but are no longer actively used in the current workflow.

## Purpose
- Archive of previously useful scripts
- Historical reference for development decisions
- Backup of functionality that might be needed for reference

## Network Graph Scripts

### Old Graph Building Approach
**`build_networkx_graph.py`**
- **Original Purpose**: Built a NetworkX graph of the London transport network
- **Why Created**: Needed to model London's transport system as a graph for pathfinding
- **Why Retired**: Used a flawed approach based on `lineStrings` coordinate data requiring complex coordinate-to-station matching
- **Key Issues**: Generated many incorrect connections and missed valid connections, requiring a graph_fixer script
- **Replacement**: `network_data/build_networkx_graph_new.py` using the `stopPointSequences` data from TFL API

**`graph_fixer.py`**
- **Original Purpose**: Fixed connectivity issues in the graph built by the old approach
- **Why Created**: The old graph building approach produced stations with missing connections and disconnected components
- **Why Retired**: No longer needed as the new approach creates properly connected graphs
- **Historical Value**: Demonstrates the problems with the coordinate-based approach

**`test_station_coverage.py`**
- **Original Purpose**: Checked if all stations were included in the graph
- **Why Created**: Needed to validate station coverage completeness
- **Why Retired**: New approach has better inherent coverage as it uses direct API data
- **Impact**: Helped identify gaps in the original station mapping

## Data Validation Scripts

### CSV Validation Scripts
**`find_missing_csv_entries.py`**
- **Original Purpose**: Identified missing stations in the CSV data
- **Why Created**: Needed to ensure complete station coverage in journey time data
- **Why Retired**: New approach doesn't rely on external CSV data for connections

**`check_csv_stations.py`**
- **Original Purpose**: Verified stations in CSV against TFL API data
- **Why Created**: Needed to ensure CSV station names matched API station names
- **Why Retired**: New approach works directly with API data

**`debug_csv.py`**
- **Original Purpose**: Troubleshooting tool for CSV data issues
- **Why Created**: Needed to identify and fix CSV parsing issues
- **Why Retired**: No longer rely on CSV data for connections

### Data Validation Phase
**`check_stations.py`**
- **Original Purpose**: Simple validation of station data structure
- **Why Created**: Needed a quick way to verify station data integrity
- **Why Retired**: More comprehensive validation now integrated into main scripts

**`compare_stations.py`**
- **Original Purpose**: Compared our structured data with TfL API responses
- **Why Created**: Needed to validate our initial data structure against TfL data
- **Why Retired**: New sync system with fuzzy matching made this redundant
- **Historical Value**: Shows the validation process we used to ensure data accuracy

## Data Structure Development
**`consolidated_stations.py`**
- **Original Purpose**: First attempt at combining station data from different modes
- **Why Created**: Needed to merge separate mode-specific station files
- **Why Retired**: Replaced by more efficient `sync_stations.py` with better deduplication
- **Key Learning**: Led to current unified data structure approach

**`create_station_mapping.py`**
- **Original Purpose**: Created initial mappings between station IDs and names
- **Why Created**: Needed for the original multiple-API-call approach
- **Why Retired**: New Line endpoint approach made separate mappings unnecessary
- **Impact**: Helped identify the need for a more efficient API strategy

## API Testing and Analysis
**`inspect_api_data.py`**
- **Original Purpose**: Analyzed TFL API response structure to understand how to extract data
- **Why Created**: Needed to understand the complex structure of TFL API responses
- **Why Retired**: Knowledge now incorporated into main scripts
- **Historical Value**: Shows how we initially explored the API data

**`test_api.py`**
- **Original Purpose**: Initial test script for TFL API
- **Why Created**: Needed to test API connectivity and response format
- **Why Retired**: Basic testing code now integrated into main scripts

**`api_response.json`**
- **Original Purpose**: Sample API response for analysis
- **Why Created**: Needed for offline analysis of API structure
- **Why Retired**: Now work directly with live API data

## Version Control
**`compare_station_versions.py`**
- **Original Purpose**: Tracked changes between different versions of station data
- **Why Created**: Needed to monitor data evolution during development
- **Why Retired**: Functionality now integrated into `sync_stations.py`
- **Legacy**: Influenced current change tracking system

## API Call Evolution
1. **Original Approach** (using scripts in this directory)
   - StopPoints endpoint called twice:
     - Once for validation
     - Once for radius search
   - Separate journey time calls
   - Multiple data files and mappings
   - Graph building based on geographic coordinates (lineStrings data)
   - Required post-processing to fix graph connectivity issues

2. **Current Approach**
   - Single Line endpoint call for station data
   - StopPointSequences data used for precise station connections
   - Local data storage with efficient sync system
   - Unified data structure
   - More accurate graph representation of the network
   - No post-processing needed

## Note
These scripts are kept for:
- Historical reference
- Documentation of previous approaches
- Potential code reuse if similar functionality is needed
- Understanding the evolution of the codebase

**Warning**: Scripts in this directory should not be used in the current workflow as they may be outdated or incompatible with the current data structure. 