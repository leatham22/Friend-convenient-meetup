# Learning Notes: Working with London Underground Station Data

This document explains key concepts and challenges faced when working with real-world transportation data, particularly in the context of the London Underground station network. 

## The Problem of Inconsistent Data Formats

One of the most common challenges in real-world data processing is dealing with inconsistent naming conventions across different data sources. Let's understand why this happens and how to solve it:

### Why Names Vary Between Datasets

1. **Different Purposes**: Data collected for different purposes (operational vs. public) might use different naming patterns.
2. **Different Sources**: TfL, National Rail, and other organizations might refer to the same station differently.
3. **Historical Changes**: Station names evolve over time but might not be updated consistently across all systems.
4. **Abbreviations**: Systems might use different abbreviations (e.g., "St" vs "Street").

### Solution: Name Normalization

The solution we implemented was a robust name normalization function that transforms various forms of station names into a consistent format. Key steps:

```python
def normalize_station_name(name: str) -> str:
    # Convert to lowercase for case-insensitive matching
    name = name.lower()
    
    # Standardize common variations
    name = name.replace("'s", "s")
    name = name.replace("st.", "st")
    
    # Remove suffixes like "station", "underground", etc.
    name = re.sub(r'\s+(underground|tube|station)$', '', name)
    
    # Handle special cases
    if "kings cross" in name:
        name = "kings cross"
```

This approach allows us to match names like "King's Cross St. Pancras Underground Station" with "KINGS CROSS" in another dataset.

## Graph Representation of Transport Networks

Transport networks like the London Underground are naturally represented as graphs:

### Station Graph Structure

- **Nodes (Vertices)**: Represent stations
- **Edges**: Connections between stations
- **Weights**: Travel times between stations

```json
{
  "kings cross": {
    "euston": 1.32,       // 1.32 minutes to travel to Euston
    "highbury and islington": 2.87  // 2.87 minutes to Highbury & Islington
  }
}
```

### Why Directed Graphs Matter

Our implementation uses a directed graph (where A→B might have a different weight than B→A) because:

1. Travel times can differ depending on direction (due to track gradients, etc.)
2. Some connections are one-way only
3. Some stations might be entry-only or exit-only at certain times

## Handling Missing Data

When working with real-world data, missing information is common. Our approach:

1. **Identify Missing Elements**: Use the `find_missing_csv_entries.py` script to find stations in the CSV but missing from the graph.
2. **Implement Fixes**: Create the `add_missing_stations.py` script to:
   - Add missing stations to the graph
   - Add connections for these stations
   - Apply proper normalization rules

## Data Processing Techniques Used

### 1. Regular Expressions

Regular expressions (regex) were crucial for standardizing text patterns:

```python
# Remove text in parentheses
name = re.sub(r'\s*\([^)]*\)\s*', ' ', name)
```

### 2. Dictionaries and Sets for Efficient Lookups

```python
# Convert graph keys to a set for O(1) lookups
graph_stations = set(graph.keys())

# Check if a station exists in our graph
if station_name not in graph_stations:
    # Station is missing
```

### 3. CSV Processing with DictReader

```python
# Use DictReader to access CSV data by column names
reader = csv.DictReader(f, fieldnames=headers)
for row in reader:
    start = row['Station from (A)']
    end = row['Station to (B)']
```

### 4. Fallback Strategies for Missing Data

```python
# Try to use unimpeded running time, but fall back to inter-peak if unavailable
running_time = row.get(running_time_col)
if not running_time or running_time.strip() == '':
    running_time = row.get(inter_peak_col)
```

## Next Steps for Learning

To continue learning from this project, consider:

1. **Implementing Pathfinding Algorithms**: Try implementing Dijkstra's algorithm to find shortest paths through the network.
2. **Data Visualization**: Use libraries like matplotlib or networkx to visualize the station graph.
3. **Advanced Metrics**: Calculate centrality measures to identify which stations are most critical to the network.
4. **Machine Learning Integration**: Predict travel times based on time of day, day of week, etc.

## Conclusion

Working with real-world transportation data involves many challenges in data cleaning, normalization, and graph construction. The techniques learned here apply to many other domains where you need to combine datasets with inconsistent naming conventions or establish relationships between entities. 