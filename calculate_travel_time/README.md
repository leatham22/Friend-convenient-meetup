# Travel Time Calculation Package (`calculate_travel_time`)

## Purpose

This package is responsible for calculating travel times between stations. It implements a two-stage approach:

1.  **NetworkX Estimation:** Uses the loaded NetworkX graph and a custom Dijkstra algorithm to quickly estimate travel times for a larger set of spatially filtered candidate stations. This stage includes penalties for line transfers.
2.  **TfL API Calculation:** Uses the official TfL Journey Planner API to get more accurate travel times for the top candidate stations identified in the NetworkX stage.

## Modules

### `time_calculator.py`

Contains the functions for both NetworkX-based and TfL API-based travel time calculations.

#### Functions:

*   **`dijkstra_with_transfer_penalty(graph, start_station_name, end_station_name)`**: Implements a Dijkstra shortest path algorithm on the NetworkX graph (`graph`) between a `start_station_name` and `end_station_name`. It uses the 'weight' attribute of edges as the travel time and applies a 5-minute penalty when the path involves changing lines (i.e., the edge key representing the line/mode changes), excluding changes to/from 'transfer' pseudo-lines. Note that the initial walk time to the start station is *not* included in this calculation and must be added separately. Returns the calculated path cost in minutes or `float('inf')` if no path exists.
*   **`calculate_networkx_estimates(filtered_stations_attributes, people_data, G)`**: Orchestrates the first stage of travel time calculation. It iterates through the list of `filtered_stations_attributes` (potential meeting points) and, for each station, calculates the estimated travel time from each person's start station using `dijkstra_with_transfer_penalty`. It adds the person's `time_to_station` (walk time) to the Dijkstra path cost. It computes the total and average estimated travel time for each potential meeting station. Returns a list of tuples `(total_time, avg_time, name, attributes)`, sorted by average time, containing the results for stations reachable by everyone according to the graph estimates.
*   **`calculate_tfl_times(top_stations_attributes, people_data, api_key)`**: Orchestrates the second stage of travel time calculation using the TfL API. It takes the `top_stations_attributes` (typically the top 10 from the NetworkX stage), determines the appropriate Naptan ID for each potential meeting station using `determine_api_naptan_id` (from `api_interaction.tfl_api`), and calls `get_travel_time` (also from `api_interaction.tfl_api`) to query the TfL API for the journey time for each person to that station. It adds the person's `time_to_station` (walk time). It calculates the total and average travel time based on TfL results. Returns a tuple containing: (1) a list of TFL results `(total_time, avg_time, name, attributes)` for successfully calculated journeys, and (2) the attributes dictionary of the station identified as having the lowest total TFL travel time. 