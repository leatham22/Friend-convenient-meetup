
import sys

# Import functions from newly created modules
from spatial_filtering.filtering_logic import filter_stations_optimized
from data_loading.load_data import load_networkx_graph_and_station_data
from user_input.input_handling import parse_arguments, get_user_inputs
from calculate_travel_time.time_calculator import calculate_networkx_estimates, calculate_tfl_times
from results.display import display_results

# --- Path to NetworkX Graph Data --- (Keep constants needed by main orchestration here)
GRAPH_PATH = "networkx_graph/create_graph/output/final_networkx_graph.json"

# --- Main Execution ---

def main():
    """
    Main function to find the optimal meeting location using optimized station filtering.
    """
    args = parse_arguments()
    print(f"\nUsing API Key: {'*' * (len(args.api_key) - 4) + args.api_key[-4:]}")

    # Load NetworkX graph AND station data lookup from the graph file
    # Pass the graph path to the loading function
    G, station_data_lookup = load_networkx_graph_and_station_data(GRAPH_PATH)
    if G is None or station_data_lookup is None:
        print("Could not load the NetworkX graph or station data. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Get user input
    people_data = get_user_inputs(station_data_lookup)
    if not people_data: # Exit if user input failed or was insufficient
        print("Exiting due to insufficient user input.")
        sys.exit(1)

    # Filter stations using optimized method
    # Create the list of station attributes needed for filtering
    all_stations_list_for_filtering = [
        attributes for attributes in station_data_lookup.values()
        if 'lat' in attributes and 'lon' in attributes 
    ]
    if not all_stations_list_for_filtering:
        print("Error: No stations with coordinates found in the graph data for filtering.", file=sys.stderr)
        sys.exit(1)
        
    filtered_stations_attributes = filter_stations_optimized(all_stations_list_for_filtering, people_data)
    if not filtered_stations_attributes:
        print("\nNo stations found within the initial filtering criteria (convex hull/ellipse and centroid).")
        sys.exit(1)

    # --- Stage 1: Calculate initial estimates using NetworkX Graph --- 
    networkx_results = calculate_networkx_estimates(filtered_stations_attributes, people_data, G)
    
    if not networkx_results:
        print("\nNo suitable stations found after NetworkX estimation (no paths found for all participants).")
        sys.exit(1)
        
    # Select top 10 stations based on NetworkX results (get attributes list)
    top_10_stations_attributes = [res[3] for res in networkx_results[:10]]

    # --- Stage 2: Calculate accurate travel times for Top 10 using TfL API ---
    tfl_results, best_meeting_station_attributes = calculate_tfl_times(
        top_10_stations_attributes, 
        people_data, 
        args.api_key
    )

    # --- Final Result Display ---
    display_results(best_meeting_station_attributes, people_data, tfl_results, args.api_key)


if __name__ == "__main__":
    main()