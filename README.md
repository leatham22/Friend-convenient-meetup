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

3. **Version Control**
   - Git basics
   - GitHub repository management
   - Proper .gitignore setup

## Technical Details

### API Endpoints Used
- Main endpoint: `https://api.tfl.gov.uk/StopPoint/Mode/tube,overground,dlr,elizabeth-line`
- Test endpoint (Victoria station): `https://api.tfl.gov.uk/StopPoint/940GZZLUVIC`

### Project Structure
```
project/
├── main.py           # Main application
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
- Calculates optimal meeting point based on:
  - Walking time to starting stations
  - TfL journey times between stations
  - Total combined travel time for all participants

### Known Limitations
- Requires valid station names exactly as in TfL database
- Minimum 2 people required for calculation
- Currently command-line interface only

## Next Steps
- Add error handling for invalid station names
- Implement station name suggestions
- Add support for additional transport modes
- Create a web interface 