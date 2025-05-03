# API Interaction Package (`api_interaction`)

## Purpose

This package encapsulates all interactions with the external Transport for London (TfL) Unified API. It handles retrieving the API key, determining the correct Naptan ID for API calls, and querying the Journey Planner endpoint.

## Modules

### `tfl_api.py`

Contains functions for interacting with the TfL API.

#### Constants:

*   **`TFL_API_BASE_URL`**: The base URL for the TfL Journey Planner API endpoint (`https://api.tfl.gov.uk/Journey/JourneyResults/`).

#### Functions:

*   **`get_api_key()`**: Retrieves the TfL API key. It first checks the `TFL_API_KEY` environment variable (using `python-dotenv` to load `.env` files). Returns the key if found, otherwise `None`. (Note: Argument parsing for the key is handled in the `user_input` package).
*   **`determine_api_naptan_id(station_attributes)`**: Determines the most appropriate Naptan ID to use for TfL API calls based on a station's attribute dictionary. It prioritizes non-hub `primary_naptan_id` values, then falls back to the Naptan ID of the first constituent station if available. As a final fallback, it might use the station's main ID (`hub_name` or `id`) if it doesn't appear to be a hub identifier. This logic is crucial for querying the correct entity in the TfL API, especially for complex hubs.
*   **`get_travel_time(start_naptan_id, end_naptan_id, api_key)`**: Queries the TfL Journey Planner API to find the shortest journey time between a `start_naptan_id` and an `end_naptan_id`. It constructs the request URL, includes the `api_key`, requests the fastest journey departing now, handles potential API errors (like no journey found or request exceptions), and returns the journey duration in minutes if successful, otherwise `None`. 