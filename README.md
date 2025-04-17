# London Transport Meeting Point Finder

A tool that helps groups of people find the most convenient London station to meet at, by analyzing everyone's nearest stations and calculating optimal meeting points that minimize total travel time.

## Project Overview

This project solves the common problem of finding a convenient place to meet in London when people are coming from different locations. It works by:
1. Taking each person's nearest station and walking time
2. Calculating journey times between all possible stations
3. Finding optimal meeting points that minimize total travel time for everyone

The project includes sophisticated station data management to ensure accurate station matching and journey time calculations.

## Key Features

1. **Station Data Management**
   - Automatic station data synchronization with TfL API
   - Proper handling of multi-entrance stations
   - Support for all London rail modes (Tube, DLR, Overground, Elizabeth Line)

2. **Data Organization**
   - Raw station data with full TfL API information
   - Slim station data for efficient processing
   - Child station tracking for better station matching

3. **API Integration**
   - Reliable Line-based station fetching
   - Automatic retries with exponential backoff
   - Proper error handling

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
   python3 collect_initial_stations.py
   
   # Create slim versions
   python3 slim_stations.py
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
   python3 sync_stations.py
   ```

## Technical Details

### Station Data Structure
1. **Raw Data**
   - Full station information from TfL
   - Includes modes, lines, etc.
   - Used for debugging and future features

2. **Slim Data**
   - Only essential fields:
     - name
     - lat/lon (for journey times)
     - child_stations (for matching)

### Station Matching
1. **Primary Method**: HubNaptanCode
   - Groups related stations (e.g., different entrances)
   - Most reliable for multi-mode stations

2. **Fallback Method**: Location
   - Groups stations by coordinates
   - ~11m accuracy (4 decimal places)

### API Endpoints
- Primary: `/Line/{line}/StopPoints`
  - More reliable than StopPoint endpoint
  - Better data organization
  - Automatic retries on failure

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Your chosen license] 