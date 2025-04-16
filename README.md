# London Meeting Point Finder

A Python application that helps friends find the most convenient London station to meet, using the Transport for London (TfL) API. The program calculates the best meeting point by minimizing total travel time for all participants.

## What We've Done

1. **Initial Setup**
   - Created a Python program using the TfL API
   - Set up environment variables for API key security
   - Created proper project structure with requirements.txt

2. **API Integration**
   - Successfully connected to TfL API
   - Updated API endpoints to use current TfL preferred format
   - Created test script to verify API connection

3. **Version Control**
   - Initialized Git repository
   - Set up proper .gitignore for Python project
   - Connected to GitHub repository

4. **Data Processing Improvements**
   - Created inspection script to analyze TfL station data
   - Implemented initial station de-duplication using hubNaptanCode
   - Added mode filtering for relevant transport types
   - Added station name normalization

## Current Challenges

1. **Station De-duplication**
   - Current station identification shows:
     - 534 stations using hubNaptanCode
     - 1017 stations using composite keys (name + coordinates)
     - 1027 unique stations after de-duplication (higher than expected)
   - Some stations still appearing as duplicates (e.g., Abbey Road/All Saints DLR)
   - Need to improve composite key generation and name normalization

2. **Data Volume**
   - Initial API response includes more stations than needed
   - Need to optimize filtering of relevant stations
   - Current mode filtering needs refinement

## Next Steps

1. **Station Identification Improvements**
   - Debug specific cases of station duplication
   - Refine coordinate precision in composite keys
   - Enhance station name normalization
   - Consider additional methods for station matching

2. **Performance Optimization**
   - Implement local station database
   - Add fuzzy matching for station names
   - Reduce unnecessary API calls

## How to Use

1. **Setup**
   ```bash
   # Clone the repository
   git clone [your-repo-url]
   
   # Install requirements
   python3 -m pip install -r requirements.txt
   ```

2. **API Key**
   - Get a free API key from TfL: [TfL API Portal](https://api-portal.tfl.gov.uk/)
   - Create a `.env` file in the project root
   - Add your API key: `TFL_API_KEY=your_api_key_here`

3. **Test API Connection**
   ```bash
   python3 test_api.py
   ```

4. **Run the Program**
   ```bash
   python3 main.py
   ```
   - Enter at least 2 people's nearest stations
   - For each person, provide:
     - Their nearest station name
     - Walking time to that station
   - Type 'done' when finished entering people

## Key Files

- `main.py`: Main program for finding optimal meeting points
- `inspect_api_data.py`: Script for analyzing TfL station data
- `test_api.py`: Script to test TfL API connection
- `requirements.txt`: Python package dependencies
- `.env`: Local file for API key (not in repository)
- `.gitignore`: Specifies which files Git should ignore

## Learning Points

1. **API Usage**
   - Working with RESTful APIs
   - Managing API keys securely
   - Understanding API endpoints and parameters

2. **Python Development**
   - Environment variables
   - Package management
   - API requests and responses
   - Data structure manipulation
   - String normalization techniques

3. **Version Control**
   - Git basics
   - GitHub repository management
   - Proper .gitignore setup

## Technical Details

### API Endpoints Used
- Main endpoint: `https://api.tfl.gov.uk/StopPoint/Mode/tube,overground,dlr,elizabeth-line`
- Test endpoint (Victoria station): `https://api.tfl.gov.uk/StopPoint/940GZZLUVIC`

### Current Implementation Details
1. **Station Identification Methods**
   - Primary: hubNaptanCode (when available)
   - Secondary: composite key (normalized station name + rounded coordinates)
   - Last resort: naptanId
   
2. **Data Processing Pipeline**
   - Initial API fetch (all stations)
   - Mode filtering (tube, overground, dlr, elizabeth-line)
   - Station de-duplication
   - Travel time calculation

3. **Current Debugging Focus**
   - Investigating duplicate stations (e.g., Abbey Road/All Saints DLR)
   - Added debug logging for problematic stations
   - Testing different coordinate precision levels
   - Implementing stricter name normalization

4. **Key Statistics (Last Run)**
   - Total API response: ~2600 stations
   - After mode filtering: Still processing all stations
   - Using hubNaptanCode: 534 stations
   - Using composite keys: 1017 stations
   - Final unique stations: 1027 (needs optimization)

### Project Structure
```
project/
├── main.py           # Main application
├── inspect_api_data.py # Station data analyzer
├── test_api.py       # API connection tester
├── requirements.txt  # Dependencies
├── .env             # API key (not in repo)
└── .gitignore       # Git ignore rules
```

### Dependencies
- requests
- python-dotenv

### Current Features
- Fetches all London stations (Tube, Overground, DLR, Elizabeth Line)
- Filters stations by transport mode
- Attempts station de-duplication
- Calculates optimal meeting point based on:
  - Walking time to starting stations
  - TfL journey times between stations
  - Total combined travel time for all participants

### Known Limitations
- Requires valid station names exactly as in TfL database
- Minimum 2 people required for calculation
- Currently command-line interface only
- Station de-duplication needs improvement
- Some duplicate stations still present in results

## Next Steps
- Improve station de-duplication logic
- Implement station name suggestions
- Add support for additional transport modes
- Create a web interface 
- Optimize API calls and data processing 