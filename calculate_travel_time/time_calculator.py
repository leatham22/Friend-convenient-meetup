import heapq
import networkx as nx
import sys
# Use relative import assuming api_interaction is a sibling package
from api_interaction.tfl_api import determine_api_naptan_id, get_travel_time

def dijkstra_with_transfer_penalty(graph, start_station_name, end_station_name):
    """
    Calculates the shortest path travel time using a custom Dijkstra algorithm
    that incorporates walk time and applies a 5-minute penalty for line/mode changes
    during the search. WALK TIME IS ADDED EXTERNALLY.

    Args:
        graph (nx.MultiDiGraph): The loaded NetworkX graph.
        start_station_name (str): Name of the starting station.
        end_station_name (str): Name of the ending (meeting) station.

    Returns:
        float: Minimum calculated travel time in minutes (excluding initial walk time),
               or float('inf') if no path found.
    """
    # Ensure start/end stations exist in the graph before starting
    if start_station_name not in graph:
        print(f"    Error: Start station '{start_station_name}' not found in the graph.")
        return float('inf')
    if end_station_name not in graph:
        print(f"    Error: End station '{end_station_name}' not found in the graph.")
        return float('inf')

    # If start and end are the same, return 0 time immediately
    if start_station_name == end_station_name:
        print(f"    Start and end stations are the same ('{start_station_name}'), path time is 0.")
        return 0.0

    # Priority queue stores tuples: (current_path_time, current_station_name, line_key_taken_to_reach_station)
    # Initialize time to 0.0 as walk time is handled externally.
    pq = [(0.0, start_station_name, None)]

    # Distances dictionary stores the minimum time found so far to reach a station VIA a specific line key
    # Key: (station_name, line_key), Value: time
    # Initialize start distance to 0.0
    distances = {(start_station_name, None): 0.0}

    # Keep track of the minimum time found to reach the end_station_name, regardless of the line taken
    min_time_to_destination = float('inf')

    while pq:
        # Get the element with the smallest time
        current_time, current_station, previous_line_key = heapq.heappop(pq)

        # If we found a shorter path already to this state (station via previous_line_key), skip
        if current_time > distances.get((current_station, previous_line_key), float('inf')):
            continue

        # If we have reached the destination station, update the overall minimum time found so far
        if current_station == end_station_name:
            min_time_to_destination = min(min_time_to_destination, current_time)
            # continue # Optional optimization

        # If the current path time exceeds the best known time to the destination, we can prune it
        if current_time > min_time_to_destination:
             continue

        # Explore neighbors
        if current_station not in graph:
            print(f"    Warning: Station '{current_station}' not in graph nodes during Dijkstra search.")
            continue

        for neighbor_station in graph.neighbors(current_station):
            # Get all edges between current_station and neighbor_station
            edge_datas = graph.get_edge_data(current_station, neighbor_station)
            if not edge_datas:
                continue # Should not happen with graph.neighbors, but safeguard

            for edge_key, edge_data in edge_datas.items():
                # Use 'weight' instead of 'duration'
                edge_travel_time = edge_data.get('weight', float('inf')) 
                current_edge_line_key = edge_key 

                # Check using edge_travel_time
                if edge_travel_time == float('inf') or current_edge_line_key is None:
                    continue 

                # Calculate penalty
                penalty = 0.0
                if (previous_line_key is not None and 
                    current_edge_line_key != previous_line_key and
                    previous_line_key != 'transfer' and 
                    current_edge_line_key != 'transfer'):
                    penalty = 5.0 

                # Calculate the time to reach the neighbor via THIS specific edge using edge_travel_time
                new_time = current_time + edge_travel_time + penalty 

                # Relaxation step
                if new_time < distances.get((neighbor_station, current_edge_line_key), float('inf')):
                    distances[(neighbor_station, current_edge_line_key)] = new_time
                    heapq.heappush(pq, (new_time, neighbor_station, current_edge_line_key))

    # After the loop, min_time_to_destination holds the minimum time to reach the end station
    if min_time_to_destination == float('inf'):
        print(f"    No path found from {start_station_name} to {end_station_name} using custom Dijkstra.")
    else:
        print(f"    Calculated Dijkstra path cost: {min_time_to_destination:.2f} mins (incl. penalties)")

    return min_time_to_destination

def calculate_networkx_estimates(filtered_stations_attributes, people_data, G):
    """
    Performs the initial travel time estimation using the NetworkX graph.

    Args:
        filtered_stations_attributes (list): List of station attribute dictionaries.
        people_data (list): List of dictionaries containing person data.
        G (nx.MultiDiGraph): The NetworkX graph.

    Returns:
        list: Sorted list of tuples: (total_time, avg_time, name, attributes) 
              for stations reachable by all people according to NetworkX estimates.
    """
    print(f"\n\n--- Stage 1: Calculating initial travel time estimates for {len(filtered_stations_attributes)} stations using NetworkX ---\n")
    networkx_results = []

    for i, meeting_station_attributes in enumerate(filtered_stations_attributes, 1):
        meeting_station_name = meeting_station_attributes.get('hub_name', meeting_station_attributes.get('id'))
        
        if not meeting_station_name:
            print(f"Warning: Skipping filtered station at index {i} due to missing name attribute.")
            continue

        print(f"\nProcessing potential meeting station {i}/{len(filtered_stations_attributes)}: {meeting_station_name} (NetworkX)")
        print("-" * 80)

        current_meeting_total_time_nx = 0
        possible_meeting_nx = True
        person_times_nx = []

        for person in people_data:
            start_station_name = person['start_station_name']
            time_to_station = person['time_to_station']

            nx_path_cost = dijkstra_with_transfer_penalty(
                G,
                start_station_name,
                meeting_station_name
            )

            if nx_path_cost == float('inf'):
                print(f"    Cannot estimate journey for Person {person['id']} from {start_station_name} to {meeting_station_name} using NetworkX (No path found)")
                possible_meeting_nx = False
                break 

            person_total_time_nx = time_to_station + nx_path_cost
            print(f"    Person {person['id']} ({start_station_name}): Walk={time_to_station} + PathCost={nx_path_cost:.2f} -> Total={person_total_time_nx:.2f}")
            
            person_times_nx.append(person_total_time_nx)
            current_meeting_total_time_nx += person_total_time_nx

        if possible_meeting_nx:
            avg_time_nx = current_meeting_total_time_nx / len(people_data)
            print(f"\n    NetworkX Summary for {meeting_station_name}:")
            print(f"      Total estimated time: {current_meeting_total_time_nx:.2f} mins")
            print(f"      Avg. estimated time:  {avg_time_nx:.2f} mins per person")
            networkx_results.append((current_meeting_total_time_nx, avg_time_nx, meeting_station_name, meeting_station_attributes))
        else:
            print(f"    Skipping {meeting_station_name} due to impossible journey estimation.")

    networkx_results.sort(key=lambda x: x[1]) # Sort by average time
    return networkx_results

def calculate_tfl_times(top_stations_attributes, people_data, api_key):
    """
    Calculates accurate travel times for top candidate stations using TfL API.

    Args:
        top_stations_attributes (list): List of attribute dictionaries for top stations.
        people_data (list): List of dictionaries containing person data.
        api_key (str): TfL API key.

    Returns:
        tuple: (list, dict or None) 
               - List of TFL results: [(total_time, avg_time, name, attributes), ...]
               - Attributes dictionary of the best meeting station found via TFL, or None.
    """
    print(f"\n\n--- Stage 2: Calculating accurate travel times for Top {len(top_stations_attributes)} stations using TfL API ---\n")
    
    top_station_names = [s.get('hub_name', s.get('id', 'Unknown')) for s in top_stations_attributes]
    print(f"Top stations based on NetworkX estimate: {top_station_names}")

    min_total_time = float('inf')
    best_meeting_station_attributes = None 
    tfl_results = [] 

    for i, meeting_station_attributes in enumerate(top_stations_attributes, 1):
        meeting_station_name = meeting_station_attributes.get('hub_name', meeting_station_attributes.get('id'))
        # Use imported determine_api_naptan_id
        target_api_id = determine_api_naptan_id(meeting_station_attributes) 

        if not meeting_station_name:
            print(f"Warning: Skipping top station {i} due to missing name attribute. Attributes: {meeting_station_attributes}")
            continue
        if not target_api_id:
             print(f"Warning: Skipping top station {i} ('{meeting_station_name}') due to inability to determine valid Naptan ID.")
             continue

        print(f"\nProcessing Top station {i}/{len(top_stations_attributes)}: {meeting_station_name} (Using Naptan ID: {target_api_id}) (TfL API)")
        print("-" * 80)

        current_meeting_total_time = 0
        possible_meeting = True
        person_times = []

        for person in people_data:
            start_naptan_id = person['start_naptan_id']
            time_to_station = person['time_to_station']

            # Use imported get_travel_time
            tfl_travel_time = get_travel_time(
                start_naptan_id,
                target_api_id,
                api_key
            )

            if tfl_travel_time is None:
                print(f"    Cannot calculate TFL journey from {person['start_station_name']} to {meeting_station_name}")
                possible_meeting = False
                break

            person_total_time = time_to_station + tfl_travel_time
            person_times.append(person_total_time)
            current_meeting_total_time += person_total_time
            
            print(f"  Person {person['id']} from {person['start_station_name']}:")
            print(f"    -> Walk to station: {time_to_station} mins")
            print(f"    -> TfL journey:     {tfl_travel_time} mins")
            print(f"    -> Total TFL time:  {person_total_time} mins")

        if possible_meeting:
            avg_time = current_meeting_total_time / len(people_data)
            print(f"\n  TFL Summary for {meeting_station_name}:")
            print(f"    Total combined TFL travel time: {current_meeting_total_time} mins")
            print(f"    Average TFL travel time: {avg_time:.1f} mins per person")
            tfl_results.append((current_meeting_total_time, avg_time, meeting_station_name, meeting_station_attributes)) 

            if current_meeting_total_time < min_total_time:
                min_total_time = current_meeting_total_time
                best_meeting_station_attributes = meeting_station_attributes
        else:
            print(f"    Skipping {meeting_station_name} for TFL ranking due to impossible journey.")
            
    return tfl_results, best_meeting_station_attributes 