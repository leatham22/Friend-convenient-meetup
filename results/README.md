# Results Presentation Package (`results`)

## Purpose

This package is responsible for formatting and displaying the final results of the meeting point calculation to the user. It takes the best identified meeting station and the list of TfL API-calculated travel times to present a clear summary.

## Modules

### `display.py`

Contains the function for displaying the final output.

#### Functions:

*   **`display_results(best_meeting_station_attributes, people_data, tfl_results, api_key)`**: Formats and prints the final results. 
    *   If a `best_meeting_station_attributes` dictionary is provided, it extracts the station name, coordinates, and determines the Naptan ID used for final calculations (using `determine_api_naptan_id` from `api_interaction.tfl_api`).
    *   It finds the corresponding total and average travel times for the best station from the `tfl_results` list.
    *   It prints a summary section including the best station's name, coordinates, Naptan ID, total combined travel time, and average travel time per person.
    *   It then prints a detailed breakdown for each person, showing their walk time to their start station and the TfL API journey time from their start station to the *best* meeting station (re-calculating this specific journey using `get_travel_time` from `api_interaction.tfl_api` for the final display).
    *   Finally, it sorts the `tfl_results` and displays up to 5 alternative meeting locations with their total and average TFL travel times.
    *   If no suitable meeting station was found (`best_meeting_station_attributes` is `None`), it prints a message indicating failure. 