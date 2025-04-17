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