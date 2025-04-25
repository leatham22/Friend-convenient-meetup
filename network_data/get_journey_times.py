#!/usr/bin/env python3
"""
Get Journey Times

This script calls the TfL Journey API to get accurate journey times between
adjacent stations and saves the results to a JSON file.

Usage:
    python get_journey_times.py --line waterloo-city

Arguments:
    --line: The line to process (e.g., waterloo-city, bakerloo, etc.)
    
Output:
    Creates or appends to weighted_edges.json in the network_data directory
"""

import json
import os
import argparse
import time
import requests
from datetime import datetime
import urllib.parse

# API configuration
API_ENDPOINT = "https://api.tfl.gov.uk/Journey/JourneyResults"
DEFAULT_PARAMS = {
    "date": "20250425",  # Current date to avoid disruptions
    "time": "1500",       # Avoid peak hours
    "timeIs": "Departing",
    "journeyPreference": "LeastInterchange"
}

# Try to get TfL API key from environment variables
TFL_API_KEY = os.environ.get("TFL_API_KEY", "")
TFL_APP_ID = os.environ.get("TFL_APP_ID", "")

# If API key is available, add it to default params
if TFL_API_KEY:
    DEFAULT_PARAMS["app_key"] = TFL_API_KEY
if TFL_APP_ID:
    DEFAULT_PARAMS["app_id"] = TFL_APP_ID

def load_line_edges(file_path):
    """
    Load the line edges data from a JSON file.
    
    Args:
        file_path (str): Path to the line edges JSON file
        
    Returns:
        dict: The loaded line edges data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return {}

def load_existing_weighted_edges(file_path):
    """
    Load existing weighted edges if file exists, otherwise return empty dict.
    
    Args:
        file_path (str): Path to the weighted edges JSON file
        
    Returns:
        dict: The loaded weighted edges data or empty dict
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_weighted_edges(weighted_edges, file_path):
    """
    Save the weighted edges data to a JSON file.
    
    Args:
        weighted_edges (dict): The weighted edges data
        file_path (str): Path to save the JSON file
    """
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(weighted_edges, file, indent=2)

def get_journey_time(from_id, to_id, mode, line):
    """
    Get journey time between two stations using the TfL API.
    
    Args:
        from_id (str): The source station ID
        to_id (str): The target station ID
        mode (str): The transport mode (tube, dlr, etc.)
        line (str): The line name
        
    Returns:
        int: Journey time in minutes, or None if request failed
    """
    # Build the API URL
    url = f"{API_ENDPOINT}/{from_id}/to/{to_id}"
    
    # Create parameters for API call with all required parameters
    params = {
        "timeIs": DEFAULT_PARAMS["timeIs"],
        "journeyPreference": DEFAULT_PARAMS["journeyPreference"],
        "mode": mode,
        "date": DEFAULT_PARAMS["date"],
        "time": DEFAULT_PARAMS["time"]
    }
    
    # Add API key if available
    if "app_key" in DEFAULT_PARAMS:
        params["app_key"] = DEFAULT_PARAMS["app_key"]
    if "app_id" in DEFAULT_PARAMS:
        params["app_id"] = DEFAULT_PARAMS["app_id"]
    
    try:
        # Print URL and params for debugging (hiding API key)
        debug_params = params.copy()
        if "app_key" in debug_params:
            debug_params["app_key"] = "****"
        print(f"Calling API: {url} with params: {debug_params}")
        
        # Make the API request
        response = requests.get(url, params=params)
        print(f"API response status: {response.status_code}")
        
        # Handle non-200 responses
        if response.status_code != 200:
            print(f"API request failed with status code {response.status_code}")
            return None
        
        data = response.json()
        
        # Extract journey time from the response
        if "journeys" in data and data["journeys"]:
            # Look through all journeys to find one that uses only our specified line
            for journey in data["journeys"]:
                if "legs" in journey:
                    legs = journey["legs"]
                    
                    # Filter out walking legs
                    transit_legs = [leg for leg in legs if leg.get("mode", {}).get("id") != "walking"]
                    
                    # Print journey details for debugging
                    print(f"Journey has {len(legs)} legs ({len(transit_legs)} transit legs):")
                    for i, leg in enumerate(legs):
                        leg_mode = leg.get("mode", {}).get("id", "unknown")
                        route_options = leg.get("routeOptions", [])
                        leg_line = route_options[0].get("lineIdentifier", {}).get("id") if route_options else None
                        leg_duration = leg.get("duration", 0)
                        print(f"  Leg {i+1}: Mode={leg_mode}, Line={leg_line}, Duration={leg_duration} mins")
                    
                    # Check if this journey has exactly one transit leg and it's using our specified line
                    if len(transit_legs) == 1:
                        transit_leg = transit_legs[0]
                        route_options = transit_leg.get("routeOptions", [])
                        leg_line = route_options[0].get("lineIdentifier", {}).get("id") if route_options else None
                        
                        if leg_line == line:
                            print(f"  Found valid single-leg journey using line: {line}")
                            leg_duration = transit_leg.get("duration")
                            if leg_duration is not None:
                                print(f"  Leg duration: {leg_duration} minutes")
                                # Fix for zero duration journeys
                                if leg_duration == 0:
                                    print(f"  Adjusting zero duration journey to 1 minute")
                                    return 1
                                return leg_duration
                            
                            # If leg duration isn't available, use journey duration
                            journey_duration = journey.get("duration")
                            if journey_duration is not None:
                                print(f"  Using journey duration: {journey_duration} minutes")
                                # Fix for zero duration journeys
                                if journey_duration == 0:
                                    print(f"  Adjusting zero duration journey to 1 minute")
                                    return 1
                                return journey_duration
            
            # If we didn't find a valid journey, print a warning
            print(f"Warning: No valid single-leg journey found for {from_id} to {to_id} on {line}")
            return None
        
        print(f"No journey found for {from_id} to {to_id} on {line}")
        return None
    
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None

def process_line_edges(line_name, edges, existing_weighted_edges=None):
    """
    Process edges for a specific line and get journey times.
    
    Args:
        line_name (str): The name of the line to process
        edges (list): List of edge data for the line
        existing_weighted_edges (dict): Existing weighted edges data
        
    Returns:
        list: Weighted edges with journey times
    """
    if existing_weighted_edges is None:
        existing_weighted_edges = {}
    
    weighted_edges = []
    
    print(f"Processing {len(edges)} station pairs for {line_name}...")
    
    # Process each edge
    for i, edge in enumerate(edges):
        source_id = edge.get('source_id')
        target_id = edge.get('target_id')
        source_name = edge.get('source_name')
        target_name = edge.get('target_name')
        mode = edge.get('mode')
        line = edge.get('line')
        line_name = edge.get('line_name')
        
        # Create a unique key for this edge
        edge_key = f"{source_name}|{target_name}|{line}"
        
        # Check if we already have this edge in existing data
        if edge_key in existing_weighted_edges:
            print(f"  [{i+1}/{len(edges)}] Already have data for {source_name} to {target_name}")
            weighted_edges.append(existing_weighted_edges[edge_key])
            continue
        
        print(f"  [{i+1}/{len(edges)}] Getting journey time for {source_name} to {target_name}...")
        
        # Get journey time from the API
        duration = get_journey_time(source_id, target_id, mode, line)
        
        # Add a delay to avoid overwhelming the API
        time.sleep(1)
        
        if duration is None:
            print(f"    Failed to get journey time for {source_name} to {target_name}")
            continue
        
        # Create the weighted edge
        weighted_edge = {
            "origin": source_name,
            "destination": target_name,
            "origin_id": source_id,
            "destination_id": target_id,
            "mode": mode,
            "line": line,
            "line_name": line_name,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to the list
        weighted_edges.append(weighted_edge)
        
        # Add to existing data with the edge key
        existing_weighted_edges[edge_key] = weighted_edge
    
    return weighted_edges

def main():
    """Main function to process lines and get journey times"""
    parser = argparse.ArgumentParser(description="Get journey times for a specific line")
    parser.add_argument("--line", required=True, help="Line to process (e.g., waterloo-city)")
    args = parser.parse_args()
    
    # File paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    line_edges_file = os.path.join(script_dir, 'line_edges.json')
    weighted_edges_file = os.path.join(script_dir, 'weighted_edges.json')
    
    # Load line edges data
    print(f"Loading line edges from {line_edges_file}...")
    line_edges = load_line_edges(line_edges_file)
    
    if not line_edges:
        print("No line edges found. Run extract_line_edges.py first.")
        return
    
    # Check if the requested line exists
    if args.line not in line_edges:
        print(f"Line '{args.line}' not found in line_edges.json.")
        print(f"Available lines: {', '.join(line_edges.keys())}")
        return
    
    # Load existing weighted edges if available
    print(f"Loading existing weighted edges from {weighted_edges_file}...")
    existing_data = load_existing_weighted_edges(weighted_edges_file)
    
    # Convert existing data to a dictionary keyed by "origin|destination|line"
    existing_weighted_edges = {}
    for edge in existing_data.get("edges", []):
        key = f"{edge['origin']}|{edge['destination']}|{edge['line']}"
        existing_weighted_edges[key] = edge
    
    # Process the requested line
    edges = line_edges[args.line]
    weighted_edges = process_line_edges(args.line, edges, existing_weighted_edges)
    
    # Prepare the data structure for saving
    all_weighted_edges = existing_data.get("edges", [])
    
    # Remove existing edges for this line
    all_weighted_edges = [edge for edge in all_weighted_edges if edge.get("line") != args.line]
    
    # Add the new weighted edges
    all_weighted_edges.extend(weighted_edges)
    
    # Create the final data structure
    weighted_edges_data = {
        "edges": all_weighted_edges,
        "last_updated": datetime.now().isoformat()
    }
    
    # Save the data
    print(f"Saving weighted edges to {weighted_edges_file}...")
    save_weighted_edges(weighted_edges_data, weighted_edges_file)
    
    print(f"Done! Processed {len(weighted_edges)} edges for line '{args.line}'.")

if __name__ == "__main__":
    main() 