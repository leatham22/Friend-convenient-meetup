import argparse
import os
import sys
import math
from fuzzywuzzy import fuzz
# Use relative import assuming api_interaction is a sibling package
from api_interaction.tfl_api import get_api_key 

def find_closest_station_match(station_name, station_data_lookup):
    """
    Finds the closest matching station name present as a node in the graph data.
    Uses exact matching first, then normalized names, and finally fuzzy matching.
    Presents user with options when multiple close matches are found.

    Args:
        station_name (str): The user-provided station name.
        station_data_lookup (dict): Dictionary mapping station names (from graph nodes)
                                   to their attribute dictionaries.

    Returns:
        dict: The station attribute data if found, None otherwise.
    """
    # Normalize the user input
    normalized_input_raw = station_name.lower().strip()

    # Try exact case-insensitive match first against graph node names (keys of the lookup)
    for node_name, node_attributes in station_data_lookup.items():
        if node_name.lower() == normalized_input_raw:
            print(f"Exact match found: '{node_name}'")
            # Return the attributes dictionary for the matched node
            # Check if 'hub_name' is present, otherwise use the matched node_name
            if 'hub_name' in node_attributes:
                return node_attributes
            else:
                # If hub_name is missing but we matched, add the key as the name
                node_attributes['hub_name'] = node_name 
            return node_attributes

    # If no exact match, normalize the input name using the same logic as before
    def normalize_name(name):
        """Helper function to normalize station names"""
        if not name:
            return ""

        name = name.lower().strip()

        # Handle common abbreviations before other normalizations
        common_abbrevs = {
            'st ': 'street ',
            'st.': 'street',
            'rd ': 'road ',
            'rd.': 'road',
            'ave ': 'avenue ',
            'ave.': 'avenue',
            'ln ': 'lane ',
            'ln.': 'lane',
            'pk ': 'park ',
            'pk.': 'park',
            'gdns ': 'gardens ',
            'gdns.': 'gardens',
            'xing ': 'crossing ',
            'xing.': 'crossing',
            'stn ': 'station ',
            'stn.': 'station'
        }

        # Add a space at the end to help match abbreviations at the end of the name
        name = name + ' '
        for abbrev, full in common_abbrevs.items():
            name = name.replace(abbrev, full)
        name = name.strip()  # Remove the extra space we added

        # First handle special patterns that include parentheses
        patterns_with_parens = [
            ' (h and c line)',
            ' (handc line)',
            ' (h&c line)',
            ' (central)',
            ' (dist and picc line)',
            ' (distandpicc line)',
            ' (dist&picc line)',
            ' (for excel)',
            ' (london)',
            ' (berks)',
            ' (for maritime greenwich)',
            ' (for excel)'
        ]
        for pattern in patterns_with_parens:
            name = name.replace(pattern, '')

        # Then standardize remaining special characters
        name = name.replace(" & ", " and ")
        name = name.replace("&", "and")
        name = name.replace("-", " ")
        name = name.replace("'", "")
        name = name.replace('"', '')

        # Now handle any remaining parentheses
        name = name.replace("(", " ")
        name = name.replace(")", " ")

        # Clean spaces
        name = ' '.join(name.split())

        # Remove common prefixes
        prefixes = ['london ']
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]

        # Remove common suffixes
        suffixes = [
            ' underground station',
            ' overground station',
            ' dlr station',
            ' rail station',
            ' station',
            ' underground',
            ' overground',
            ' dlr'
        ]
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]

        # Remove any remaining common patterns
        patterns = [
            ' ell ',
            ' rail ',
            ' tube '
        ]
        for pattern in patterns:
            name = name.replace(pattern, "")

        return ' '.join(name.split())

    normalized_input_processed = normalize_name(normalized_input_raw)

    # Try fuzzy matching against normalized graph node names
    matches = []
    # Iterate through the graph node names and their attributes
    for node_name, node_attributes in station_data_lookup.items():
        # Normalize the graph node name for comparison
        station_normalized = normalize_name(node_name)
        # Calculate fuzzy ratio between normalized input and normalized node name
        ratio = fuzz.ratio(normalized_input_processed, station_normalized)

        # Collect matches above a threshold (e.g., 75)
        if ratio > 75:
            # Store the attributes, ratio, and the original node name
            matches.append((node_attributes, ratio, node_name))

    if not matches:
        # Single consolidated error message
        print(f"\n Error: Station '{station_name}' not found or doesn't closely match any station in the graph data.")
        print(" Please check the spelling and ensure it's a relevant station name as listed in the network graph.")
        print(" Tip: You can use common abbreviations like 'st' for 'street', 'rd' for 'road', etc.")
        return None

    # Sort matches by ratio in descending order
    matches.sort(key=lambda x: x[1], reverse=True)

    # If we have a perfect match (ratio 100), use it
    if matches[0][1] == 100:
        print(f"Close match found: '{matches[0][2]}'")
        # Return the attributes of the best match
        return matches[0][0]

    # If we have multiple close matches, show top 5 options
    print(f"\nMultiple potential matches found for '{station_name}'. Please select the correct station:")
    # Display the original node name found in the graph
    for i, (attributes, ratio, matched_name) in enumerate(matches[:5], 1):
        print(f"{i}. {matched_name} (similarity: {ratio}%)")

    while True:
        try:
            choice = input("\nEnter the number of your station (or 0 to try a different name): ")
            if choice == '0':
                return None
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(matches[:5]):
                # Return the attributes dictionary for the chosen station
                return matches[choice_idx][0]
            print("Invalid selection. Please enter a number between 0 and", min(5, len(matches)))
        except ValueError:
            print("Invalid input. Please enter a number.")

def parse_arguments():
    """
    Parses command-line arguments for API key.
    """
    parser = argparse.ArgumentParser(
        description="Find the most convenient meeting location in London using optimized station filtering."
    )
    parser.add_argument(
        "--api-key",
        help="Your TfL API key. Alternatively, set the TFL_API_KEY environment variable."
    )
    args = parser.parse_args()
    
    # Use get_api_key imported from api_interaction module
    final_api_key = get_api_key() 
    if not final_api_key and args.api_key:
        print("Using TfL API key from command line argument.")
        final_api_key = args.api_key
        
    if not final_api_key:
        # If still no key, attempt to load from .env again explicitly for command line case
        from dotenv import load_dotenv
        load_dotenv()
        final_api_key = os.environ.get('TFL_API_KEY')
        if final_api_key:
             print("Using TfL API key from environment variable (loaded explicitly).")
        else:
            parser.error("TfL API key is required. Provide it via --api-key or the TFL_API_KEY environment variable.")
    
    args.api_key = final_api_key
    return args

def get_user_inputs(station_data_lookup):
    """
    Gathers station names and walk times from the user.

    Args:
        station_data_lookup (dict): Dictionary mapping station names to attributes.

    Returns:
        list: List of dictionaries, each representing a person's data,
              or an empty list if insufficient input is provided.
    """
    people_data = []
    print("\nPlease enter the details for each person.")
    print("Enter the name of their NEAREST Tube/Overground/DLR/Rail station.")
    print("Type 'done' or leave blank when finished.")

    person_count = 1
    while True:
        print(f"\n--- Person {person_count} ---")
        station_name = input(f"Nearest Station Name (or 'done'): ").strip()

        if not station_name or station_name.lower() == 'done':
            if len(people_data) >= 2:
                break
            else:
                print("Please enter details for at least two people.")
                continue

        found_station_attributes = find_closest_station_match(station_name, station_data_lookup)
        if not found_station_attributes:
            continue

        hub_name = found_station_attributes.get('hub_name', found_station_attributes.get('id'))
        station_lat = found_station_attributes.get('lat')
        station_lon = found_station_attributes.get('lon')
        primary_naptan_id = found_station_attributes.get('primary_naptan_id')
        constituent_stations = found_station_attributes.get('constituent_stations', [])

        if not all([hub_name, station_lat, station_lon]):
            print(f"Error: Missing essential attributes for matched station '{station_name}'. Attributes: {found_station_attributes}")
            continue

        chosen_naptan_id = None
        chosen_station_name_for_display = hub_name

        if primary_naptan_id and primary_naptan_id.startswith("HUB") and len(constituent_stations) > 1:
            print(f"\n'{hub_name}' is a hub. Please specify your exact starting station:")
            for idx, constituent in enumerate(constituent_stations):
                print(f"  {idx + 1}. {constituent.get('name', 'Unknown Name')}")
            
            while True:
                try:
                    choice = input(f"Enter the number (1-{len(constituent_stations)}): ").strip()
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(constituent_stations):
                        chosen_constituent = constituent_stations[choice_idx]
                        chosen_naptan_id = chosen_constituent.get('naptan_id')
                        chosen_station_name_for_display = chosen_constituent.get('name', hub_name)
                        if not chosen_naptan_id:
                            print("Error: Selected constituent station is missing Naptan ID.")
                            chosen_naptan_id = None 
                        break 
                    else:
                        print(f"Invalid choice. Please enter a number between 1 and {len(constituent_stations)}.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
        
        # Fallback logic if not a multi-station hub or choice failed
        if not chosen_naptan_id:
            if primary_naptan_id and not primary_naptan_id.startswith("HUB"):
                chosen_naptan_id = primary_naptan_id
            elif constituent_stations and isinstance(constituent_stations, list) and len(constituent_stations) > 0:
                 if isinstance(constituent_stations[0], dict) and 'naptan_id' in constituent_stations[0]:
                      chosen_naptan_id = constituent_stations[0]['naptan_id']
                 else:
                     print(f"Error: Invalid structure for constituent_stations[0] for hub '{hub_name}'. Skipping.")
                     continue 
            # Use hub_name as fallback Naptan ID if it looks like one (doesn't start with HUB)
            elif hub_name and not hub_name.startswith("HUB") and "HUB" not in hub_name: 
                 print(f"Warning: Falling back to using hub name '{hub_name}' as Naptan ID.")
                 chosen_naptan_id = hub_name 
            else:
                 print(f"Error: Could not determine any valid Naptan ID for '{hub_name}'. Skipping.")
                 continue 

        if not chosen_naptan_id:
            print(f"Critical Error: Failed to assign a Naptan ID for station '{hub_name}'. Skipping this person.")
            continue

        while True:
            try:
                walk_time = int(input(f"Time (minutes) to walk TO '{chosen_station_name_for_display}': ").strip())
                if walk_time < 0:
                    print("Walk time cannot be negative.")
                    continue
                break
            except ValueError:
                print("Please enter a valid number of minutes.")

        people_data.append({
            'id': person_count,
            'start_station_name': hub_name, 
            'start_station_lat': station_lat,         
            'start_station_lon': station_lon,         
            'start_naptan_id': chosen_naptan_id,   
            'time_to_station': walk_time
        })

        print(f"Added: Person {person_count} starting from {chosen_station_name_for_display} (Hub: {hub_name}, Naptan: {chosen_naptan_id})")
        person_count += 1
        
    return people_data 