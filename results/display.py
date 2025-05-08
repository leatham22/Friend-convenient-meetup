import sys
# Use relative import assuming api_interaction is a sibling package
from api_interaction.tfl_api import determine_api_naptan_id, get_travel_time

def display_results(best_meeting_station_attributes, people_data, tfl_results, api_key):
    """
    Presents the final results, including the best station and alternatives.

    Args:
        best_meeting_station_attributes (dict or None): Attributes of the best station.
        people_data (list): List of dictionaries containing person data.
        tfl_results (list): List of TFL results: [(total_time, avg_time, name, attributes), ...]
        api_key (str): TfL API key.
    """
    if best_meeting_station_attributes:
        best_name = best_meeting_station_attributes.get('hub_name', best_meeting_station_attributes.get('id', 'Unknown Station'))
        best_lat = best_meeting_station_attributes.get('lat', 'N/A')
        best_lon = best_meeting_station_attributes.get('lon', 'N/A')
        # Use imported determine_api_naptan_id
        best_id_for_api = determine_api_naptan_id(best_meeting_station_attributes)
        
        # Recalculate min_total_time and min_avg_time for the best station from tfl_results
        min_total_time = float('inf')
        min_avg_time = float('inf')
        for total, avg, name, attrs in tfl_results:
            # Compare based on the actual ID or hub name used during TFL calc
            current_name = attrs.get('hub_name', attrs.get('id'))
            if current_name == best_name:
                min_total_time = total
                min_avg_time = avg
                break # Found the best station in the results

        if min_total_time == float('inf'): # Safeguard if best station wasn't in tfl_results for some reason
            print("Error: Could not find the best station's time in the TFL results.")
            # Attempt to find it by total time if names mismatched? Or just report error.
            # For now, report error and try to proceed cautiously.
            pass

        print("\n" + "="*80)
        print("                                    FINAL RESULT (based on TFL API for top NetworkX estimates)")
        print("="*80)
        print(f"The most convenient station found is: {best_name}")
        print(f"Coordinates: {best_lat}, {best_lon}")
        print(f"Using Naptan ID for final checks: {best_id_for_api if best_id_for_api else 'Error: Could not determine ID'}") 
        print(f"\nTotal combined TFL travel time: {min_total_time if min_total_time != float('inf') else 'N/A'} minutes")
        # Fix the f-string formatting error by separating the formatting from the conditional
        avg_time_display = f"{min_avg_time:.1f}" if min_avg_time != float('inf') else "N/A"
        print(f"Average TFL travel time per person: {avg_time_display} minutes")
        print("\nBreakdown by person (TFL API times for best station):")

        if not best_id_for_api:
             print(" Error: Could not determine a valid Naptan ID for the best station to show final breakdown.")
        else:
            for person in people_data:
                start_naptan_id = person.get('start_naptan_id') 
                if not start_naptan_id:
                    print(f"  Person {person['id']} from {person['start_station_name']}: Error retrieving start Naptan ID.")
                    continue
                # Use imported get_travel_time
                tfl_time = get_travel_time(
                    start_naptan_id,
                    best_id_for_api,
                    api_key
                )
                if tfl_time is not None:
                    total_time = person['time_to_station'] + tfl_time
                    print(f"  Person {person['id']} from {person['start_station_name']}:")
                    print(f"    -> Walk to station: {person['time_to_station']} mins")
                    print(f"    -> TfL journey: {tfl_time} mins")
                    print(f"    -> Total time: {total_time} mins")
                else:
                     print(f"  Person {person['id']} from {person['start_station_name']}: Could not retrieve final TFL time.")
        
        print("="*80)
        
        tfl_results.sort() # Sort by total time (index 0)
        if len(tfl_results) > 1: 
            print("\nTop 5 Alternative Meeting Locations (based on TFL API):")
            print("-" * 50)
            alternatives_shown = 0
            for total_time, avg_time, name, station_attributes in tfl_results:
                 current_name = station_attributes.get('hub_name', station_attributes.get('id'))
                 # Exclude the best station from the alternatives list
                 if current_name != best_name and alternatives_shown < 5:
                    print(f"{alternatives_shown + 1}. {name}")
                    print(f"   Total TFL travel time: {total_time} mins")
                    print(f"   Average per person: {avg_time:.1f} mins")
                    print()
                    alternatives_shown += 1
            if alternatives_shown == 0:
                 print("No other viable alternatives found among the top stations processed by TfL API.")

    else:
        print("\n" + "="*80)
        print("Could not find a suitable meeting station where all TFL journeys were possible among the top candidates.")
        print("Please check the starting stations entered or try again later.")
        print("="*80) 