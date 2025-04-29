# Development Archive

This directory contains scripts that were historically important in the development process but are no longer actively used in the current workflow.

## Purpose
- Archive of previously useful scripts
- Historical reference for development decisions
- Backup of functionality that might be needed for reference

## Directory Structure
- **`original_Station_graph/`**: Contains scripts specific to the original graph building system which has been replaced by the new approach using stopPointSequences
- **Current directory**: Contains general development scripts that were used in early stages of the project but are not specific to the graph system

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

## Data Validation
**`compare_stations.py`**
- **Original Purpose**: Compared our structured data with TfL API responses
- **Why Created**: Needed to validate our initial data structure against TfL data
- **Why Retired**: New sync system with fuzzy matching made this redundant
- **Historical Value**: Shows the validation process we used to ensure data accuracy

**`test_station_coverage.py`**
- **Original Purpose**: Checked if all stations were included in the transport network
- **Why Created**: Needed to validate station coverage completeness
- **Why Retired**: New approach has better inherent coverage as it uses direct API data
- **Impact**: Helped identify gaps in the original station mapping

## Version Control
**`compare_station_versions.py`**
- **Original Purpose**: Tracked changes between different versions of station data
- **Why Created**: Needed to monitor data evolution during development
- **Why Retired**: Functionality now integrated into `sync_stations.py`
- **Legacy**: Influenced current change tracking system

## API Call Evolution
1. **Original Approach** (using scripts in this directory and original_Station_graph/)
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

**See also**: The `original_Station_graph/` subdirectory contains more detailed documentation about the original graph building system.

**Warning**: Scripts in this directory should not be used in the current workflow as they may be outdated or incompatible with the current data structure. 