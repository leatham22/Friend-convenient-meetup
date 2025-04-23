# Station Graph Component

This component of the London Transport Meeting Point Finder generates and analyzes a directed graph of London Underground/TfL stations and the travel times between them. The graph represents parent stations as nodes, with edges representing direct one-way travel times between stations. This is a crucial component for calculating optimal meeting points in the main application.

## Data Sources

The project uses two primary data sources:

1. `raw_stations/unique_stations2.json`: Contains information about parent stations and their child platforms
2. `Inter_station_times.csv`: Contains travel times between stations on different lines

## Generated Output

The script produces `station_graph.json`, a directed graph with the following structure:

```json
{
  "station1": {
    "station2": 2.5,  // Travel time in minutes
    "station3": 1.5
  },
  "station2": {
    "station1": 2.0,
    "station4": 1.0
  },
  ...
}
```

Key features of the generated graph:
- Station names are normalized (lowercase, without suffixes like "station", etc.)
- Travel times are in minutes
- Line transfers at the same station are automatically free (zero cost)
- When multiple lines connect the same two stations, the minimum travel time is used

## How It Works

The script performs the following steps:

1. **Load & normalize station names**:
   - Reads each parent station and its children from the JSON
   - Normalizes names to make matching easier (lowercase, remove common words, etc.)
   - Creates a mapping from any station name to its parent station
   - Handles special cases like "Baker Street (Met)" → "Baker Street"

2. **Build edges from the CSV**:
   - For each row in the travel times CSV, normalizes the station names
   - Maps the stations to their parent stations
   - Uses the travel time (preferring unimpeded travel time, falling back to inter-peak)
   - Creates a directed edge between parent stations

3. **Export the graph**:
   - Outputs the graph as a JSON file with travel times in minutes

## Key Features

The script includes several features to ensure robust station name matching:

1. **Advanced Name Normalization**:
   - Removes station types (DLR, Rail, Underground, etc.)
   - Strips parenthetical information (like line indicators)
   - Standardizes special characters and formats

2. **Special Case Handling**:
   - Handles stations with unique naming variations like "Heathrow Terminals 123"
   - Maps variants of stations like "King's Cross St. Pancras" to a single node
   - Handles stations with line indicators like "Baker Street (Circle)"

3. **Manual Mappings**:
   - Includes special mappings for known station variations in the CSV file
   - Ensures stations like "Paddington (H&C)" map to the main "Paddington" node

## Usage

### Creating the Station Graph

Run the main script to create the station graph:

```
python3 create_station_graph.py
```

### Adding Missing Stations

If you find missing stations after graph creation, run:

```
python3 add_missing_stations.py
```

This script:
- Identifies stations that exist in the CSV but are missing from the graph
- Adds these stations to the graph with proper normalization
- Creates the necessary connections between new and existing stations
- Updates the station_graph.json file with the new data

### Verification Scripts

The project includes these verification scripts:

1. **verify_graph.py**: Tests the graph by finding shortest paths between station pairs
   ```
   python3 verify_graph.py
   ```

2. **check_stations.py**: Searches for stations matching specific terms
   ```
   python3 check_stations.py
   ```

3. **find_missing_csv_entries.py**: Identifies which stations from the CSV are missing from the graph
   ```
   python3 find_missing_csv_entries.py
   ```

4. **check_csv_stations.py**: Analyzes which stations in the CSV file don't have matches in the graph
   ```
   python3 check_csv_stations.py
   ```
5. **find_missing_stations.py**: Identifies which stations from unique_stations.json are missing from the Graph
   ```
   python3 find_missing_stations.py
   ```
## Example Output

The graph includes edges like:

```
shepherds bush → white city: 2.8 minutes
white city → shepherds bush: 3.7 minutes
```

## Notes and Limitations

- The graph is directional - travel times can differ depending on direction
- Not all stations from the TfL network are present in the dataset:
  - Many DLR and Overground stations don't have travel times in the CSV
  - The script reports stations it couldn't find during processing
- Child platforms (e.g., DLR platforms at main stations) are mapped to their parent stations
- The verification script uses a simple BFS algorithm to find paths, which does not guarantee optimal journeys
- The graph represents direct connections only; it does not account for:
  - Transfer times at stations
  - Service frequency
  - Time-dependent travel times (beyond using unimpeded/inter-peak distinctions)

## Future Improvements

Potential enhancements to this project could include:

1. Adding more missing stations to complete the network
2. Implementing a Dijkstra or A* algorithm for more accurate path finding
3. Adding transfer times between lines at stations
4. Incorporating service frequency data
5. Adding time-dependent travel times (peak vs. off-peak)
6. Improving the name normalization for better station matching