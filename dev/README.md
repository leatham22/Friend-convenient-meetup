# Development Archive

This directory contains scripts that were historically important in the development process but are no longer actively used in the current workflow.

## Purpose
- Archive of previously useful scripts
- Historical reference for development decisions
- Backup of functionality that might be needed for reference

## Historical Scripts and Their Evolution

### Data Validation Phase
**`compare_stations.py`**
- **Original Purpose**: Compared our structured data with TfL API responses
- **Why Created**: Needed to validate our initial data structure against TfL data
- **Why Retired**: New sync system with fuzzy matching made this redundant
- **Historical Value**: Shows the validation process we used to ensure data accuracy

### Data Structure Development
**`consolidated_stations.py`**
- **Original Purpose**: First attempt at combining station data from different modes
- **Why Created**: Needed to merge separate mode-specific station files
- **Why Retired**: Replaced by more efficient `sync_stations.py` with better deduplication
- **Key Learning**: Led to current unified data structure approach

### Data Mapping Evolution
**`create_station_mapping.py`**
- **Original Purpose**: Created initial mappings between station IDs and names
- **Why Created**: Needed for the original multiple-API-call approach
- **Why Retired**: New Line endpoint approach made separate mappings unnecessary
- **Impact**: Helped identify the need for a more efficient API strategy

### Version Control
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

2. **Current Approach** (in `local_data_scripts`)
   - Single Line endpoint call
   - Local data storage
   - Efficient sync system
   - Unified data structure

## Note
These scripts are kept for:
- Historical reference
- Documentation of previous approaches
- Potential code reuse if similar functionality is needed
- Understanding the evolution of the codebase

**Warning**: Scripts in this directory should not be used in the current workflow as they may be outdated or incompatible with the current data structure. 