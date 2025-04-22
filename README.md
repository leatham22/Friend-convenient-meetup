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
- ⏳ Meeting point optimization (in progress)
  - Journey time calculations
  - Total travel time minimization
  - Walking time consideration

### Next Steps
- [ ] Implement journey time calculations
- [ ] Add meeting point optimization algorithm
- [ ] Create user interface for input/output
- [ ] Add support for additional transport modes

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

## Directory Structure

```
project/
├── raw_stations/              # Raw station data from TfL API
│   ├── unique_stations.json   # All stations
│   └── unique_stations_*.json # Mode-specific stations
├── slim_stations/             # Minimal station data for processing
│   ├── unique_stations.json   # All stations
│   └── unique_stations_*.json # Mode-specific stations
├── scripts/
│   ├── collect_initial_stations.py  # Fetch raw station data
│   ├── slim_stations.py            # Create minimal station data
│   ├── sync_stations.py            # Keep data in sync with TfL
│   └── compare_station_versions.py # Compare data versions
├── requirements.txt           # Python dependencies
├── .env                      # API key (not in repo)
└── .gitignore               # Git ignore rules
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