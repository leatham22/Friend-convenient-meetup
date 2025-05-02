# Graph v0.1 - Initial Unweighted Graph

This directory contains the first iteration of scripts used to build and verify an unweighted station graph.

## Brief Description:
*  After identifying that our current logic is untenable due to 500+ TFL API calls, we settled on using a graph structure to do the initial filtering.
*  Therefore the graph was built using the data from previous the datastructure.
*  We attempted to use a CSV file `Inter_station_times.csv` (collected from TFL website) to calculate edge values (time between stops).

## Contents

### Graph Creation:

*   `create_station_graph.py`: The primary script for generating the initial station graph.
*   `check_stations.py`: Basic checks for known missing stations returned by `find_missing_stations.py`
*   `add_missing_stations.py`: Script to add stations identified in `Inter_station_times.csv` that don't exist in `station_graph.json`


### Graph tests:

*   `compare_station_names.py`: Compares station names between old datasource and `station_graph.json` making sure we don't need further name normalisation. 
*   `verify_graph.py`: Script to perform various checks and validations on the generated graph.
*   `test_normalization.py`: Tests the station data normalization process.
*   `find_missing_stations.py`: Identifies stations present in previous source data but missing from the graph datasource. 
*   `check_disconnected_stations.py`: Checks for stations or graph components that are not connected.
*   `check_graph_format.py`: Verifies the format of the generated graph data.
*   `find_missing_csv_entries.py`: Identifies missing entries in the journey times CSV.
*   `check_csv_stations.py`: Checks station names or existence within the journey times CSV `Inter_station_times.csv`
*   `test_station_coverage.py`: Checks if all expected stations are present in the graph.
*   `debug_csv.py`: Script for debugging issues related to loading the CSV data.

### Data: 

*   `station_graph.json`: Output file containing the initial station graph data.
*   `station_graph.normalized.json`: Output file containing the normalized station graph data.
*   `Inter_station_times.csv`: CSV file containing inter-station journey times, collected from TFL website.
















