# User Input Package (`user_input`)

## Purpose

This package handles all direct interaction with the user, including parsing command-line arguments and collecting the necessary starting information for each person (nearest station and walk time). It includes logic for matching user-provided station names against the loaded station data using fuzzy matching and normalization.

## Modules

### `input_handling.py`

Contains functions related to parsing arguments and getting user inputs.

#### Functions:

*   **`find_closest_station_match(station_name, station_data_lookup)`**: Takes a user-provided station name and attempts to find the best match within the `station_data_lookup` dictionary (derived from the loaded graph). It uses a combination of exact matching, name normalization (handling abbreviations, suffixes like "station", special characters), and fuzzy matching (`fuzzywuzzy` library). If multiple close matches are found, it prompts the user to select the correct one. Returns the attribute dictionary of the matched station or `None` if no suitable match is found.
*   **`parse_arguments()`**: Uses `argparse` to define and parse command-line arguments. Currently, it primarily handles the optional provision of the TfL API key via `--api-key`. It also attempts to retrieve the key from the `TFL_API_KEY` environment variable (using `get_api_key` from the `api_interaction` package) as a fallback. Ensures an API key is available before proceeding.
*   **`get_user_inputs(station_data_lookup)`**: Manages the interactive process of collecting data for each person. It repeatedly prompts the user for their nearest station name and the time it takes them to walk to that station.
    *   Uses `find_closest_station_match` to validate and retrieve data for the entered station name.
    *   Handles station hubs by prompting the user to select their specific constituent starting station if the matched station is a hub with multiple Naptan IDs.
    *   Determines the correct Naptan ID to use for the start of the journey based on user selection or fallback logic.
    *   Collects the walk time.
    *   Stores the gathered information (start station name, lat/lon, specific Naptan ID, walk time) for each person in a list of dictionaries.
    *   Ensures at least two people are entered before completing. 