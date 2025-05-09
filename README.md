# London Transport Meeting Point Finder

## Overview
A command-line tool that helps groups find the most convenient meeting point in London by analyzing journey times from each person's nearest station. Uses real-time TfL data and graph-based algorithms to calculate optimal routes.


## Purpose
As part of my journey toward applied AI proficiency, I realized I needed more experience working with APIs, large real-world datasets, and implementing algorithms in a practical context. This project combined all three, while also solving a real-life problem: helping friends settle weekly debates over where to meet in London.

## Development Approach & Relevance to Applied AI
This project was developed using the Cursor AI coding assistant throughout. The goal was not to simplify the problem, but to stay focused on structuring the logic, working with real-world data, and building a robust solution without getting bogged down in syntax.

Using Cursor shifted my development mindset toward systems design: defining architecture, refining logic through iterative prompting, and verifying everything through manual and automated testing. I initially used Claude 3.7 (Sonnet) for its broad-context reasoning, later transitioning to Gemini 2.5 Pro as my prompts became more implementation-focused.

This approach directly supports my AI learning goals. It strengthened my ability to work with large data structures, implement optimization algorithms, and design modular pipelines — all foundational for applied AI work. It also gave me practical insight into how developers can collaborate effectively with LLMs, which is increasingly relevant as AI becomes part of the software development process itself.


## Tech Stack
- Python 3
- NetworkX (for graph operations and algorithms)
- TfL (Transport for London) API 
- NumPy and SciPy (for spatial calculations and convex hull operations)
- Requests (for API communication)
- Heapq (for priority queue in Dijkstra's algorithm)
- Dotenv (for environment variable handling)
- Fuzzywuzzy and python-Levenshtein (for string matching)


## Project Structure
```
├── api_interaction/    # TfL API integration
├── calculate_travel_time/    # Journey time calculation logic
├── data_loading/    # Graph and station data loading
├── networkx_graph/    # Graph creation and analysis
├── results/    # Result formatting and display
├── spatial_filtering/    # Geographic filtering algorithms
├── user_input/    # User input handling
├── main.py    # Application entry point
└── requirements.txt    # Dependencies
```


## Graph Construction Overview 

This section outlines the seven-stage process used to construct the final `MultiDiGraph` representing the London transport network. Each script is modular and reflects a clear phase in the pipeline. All references to data paths (e.g., `.json` files) are relative to the project root.

### 1. Build Base Hub Graph
- Loads the only manually created data file: `root/networkx_graph/data/manually_created/terminal_stations.json`, which lists all terminal stations in the transport network. These are required parameters for using the `Line` endpoint effectively.
- Sequentially calls the TfL `Line` endpoint for all modes of transport, using terminal stations to retrieve line structures.
- Handles known TfL inconsistencies (e.g., Willesden Green appearing on the Metropolitan Line, which hasn’t operated since 1979).
- Constructs the base `MultiDiGraph` with nodes (including hub and individual station metadata) and initial edges between stations on the same line.

### 2. Add Proximity Transfers
- Uses the `StopPoint` endpoint to find stations located within 250 meters of each **hub node**.
- For each valid proximity match, identifies the corresponding node in the graph (converting individual stations to hub identifiers).
- Stores each valid proximity pair as a list of station ID pairs in a JSON file for later walking time lookups.


### 3. Calculate Transfer Weights
- Loads the proximity pairs JSON and makes a `JourneyTime` API request for each pair using `mode=walking`.
- For each valid walking time, adds a directional `transfer` edge between the relevant graph nodes with the appropriate travel time as the edge weight.


### 4. Fetch Timetable Data
- For each **Tube** and **DLR** line, fetches full timetable data via the `TimeTable` API endpoint.
- Caches timetable responses locally for reuse in travel time calculations.

### 5. Calculate Tube/DLR Edge Weights from Timetables
- Reads in all non-transfer edges for Tube and DLR modes.
- Calculates travel times between connected stations using the cached timetable data.
- For any edges missing from the timetable data (e.g., known gaps like Earl’s Court → Kensington Olympia), falls back to direct `JourneyTime` API queries.
- Appends all edge weights (both from timetables and API fallbacks) into a new JSON file that mirrors the graph edge format.


### 6. Calculate Overground/Elizabeth Line Weights Using JourneyTime API
- Reads all non-transfer edges for Overground and Elizabeth Line.
- Since no timetable data exists for these modes, uses the `JourneyTime` API directly for every edge.
- Appends results to the same JSON file created in Step 5.

### 6.5. Validate Collected Edge Weights
- Ensures consistency between the graph and collected edge data:
  - Confirms that all non-transfer edges in the graph exist in the weight JSON, and vice versa.
  - Checks for any invalid edge weights (e.g., negative or zero durations).

### 7. Update Graph with Final Weights
- If validation in Step 6.5 passes, updates the original `MultiDiGraph` with travel time weights from the JSON file.
- The result is a fully weighted, directionally accurate transport graph ready for pathfinding and optimization logic.


## Setup & Execution
### Prerequisites
- Python 3.7 or higher
- A Transport for London (TfL) API key
  - Register for a free key at [TfL API Portal](https://api-portal.tfl.gov.uk/)
  - The application uses the Journey Planner API specifically

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd london-transport-meeting-point-finder

# Install dependencies
pip install -r requirements.txt
```

### Required Data
The application requires a pre-built NetworkX graph file:
```
networkx_graph/create_graph/output/final_networkx_graph.json
```

If this file is not present:
```bash
# Generate the NetworkX graph (from project root)
python3 -m networkx_graph.build_graph

# Alternatively:
python3 networkx_graph/build_graph.py
```

### Running the Application
```bash
# Method 1: Provide API key via command line
python3 main.py --api-key=YOUR_TFL_API_KEY
```

**Alternative API Key Methods:**
```bash
# Method 2: Set as environment variable
export TFL_API_KEY=your_api_key_here
python3 main.py

# Method 3: Create a .env file in the project root
echo "TFL_API_KEY=your_api_key_here" > .env
python3 main.py
```

### Interactive Usage
After launching, the application will:
1. Prompt for each person's nearest station
2. Ask for their walking time to that station
3. Calculate optimal meeting points
4. Display the results along with alternative options, sorted by total travel time 


## Future Improvements

- Handle other modes of transport (cycle and bus) to make project more complete.
- Create a more granular node system where each station-line pair is treated as a distinct node (eg Kings X Northern and Piccadilly Line = two separate nodes). This will make the transfer times between lines far more accurate. 
- Once final station is found, output a visualisation using NetworkX that shows how each person arrives to the location along the graph path edge by edge. As nodes (stations) in graph have coordinate attributes, this will be accurate and a fun visual for UX. 
- Write validation scripts that sits between each step of the graph creation process, this will make sure external users can be sure the graph they created is corrrect. 
- Re-implement the deprecated sync script with our current structure so that we can guarantee up-to-date data each time the tool is run. 
- Build a basic web front-end to allow users to interact with the tool through a browser rather than the terminal.


## Example Terminal Outputs

Note: Full logs are printed to the terminal for debugging purposes, including API responses and journey resolution steps. The below only shows initial output indicating when API key and Graph loaded correctly, and final results.

### Example Output: initialisation
```
Using TfL API key from environment variable.

Using API Key: ****************************3789
Loaded NetworkX graph from 'networkx_graph/create_graph/output/final_networkx_graph.json' with 420 nodes and 1170 edges.
Created station lookup for 420 stations from graph nodes.

Please enter the details for each person.
Enter the name of their NEAREST Tube/Overground/DLR/Rail station.
Type 'done' or leave blank when finished.
```

### Example Output: Results 
```
================================================================================
                                    FINAL RESULT (based on TFL API for top NetworkX estimates)
================================================================================
The most convenient station found is: Paddington Underground Station
Coordinates: 51.516581, -0.175689
Using Naptan ID for final checks: 910GPADTLL

Total combined TFL travel time: 40 minutes
Average TFL travel time per person: 20.0 minutes

Breakdown by person (TFL API times for best station):
  Querying TfL API for journey (940GZZLULAD -> 910GPADTLL)...
  Found journey duration: 5 minutes
  Person 1 from Ladbroke Grove Underground Station:
    -> Walk to station: 4 mins
    -> TfL journey: 5 mins
    -> Total time: 9 mins
  Querying TfL API for journey (940GZZDLCAN -> 910GPADTLL)...
  Found journey duration: 27 minutes
  Person 2 from Canary Wharf Underground Station:
    -> Walk to station: 4 mins
    -> TfL journey: 27 mins
    -> Total time: 31 mins
==================================================================================

Top 5 Alternative Meeting Locations (based on TFL API):
--------------------------------------------------
1. Baker Street Underground Station
   Total TFL travel time: 44 mins
   Average per person: 22.0 mins

2. Edgware Road (Circle Line) Underground Station
   Total TFL travel time: 44 mins
   Average per person: 22.0 mins

3. Farringdon Underground Station
   Total TFL travel time: 45 mins
   Average per person: 22.5 mins

4. Liverpool Street Underground Station
   Total TFL travel time: 48 mins
   Average per person: 24.0 mins

5. Tottenham Court Road Underground Station
   Total TFL travel time: 51 mins
   Average per person: 25.5 mins   
```

