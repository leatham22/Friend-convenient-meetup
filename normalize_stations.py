"""
This script updates station_graph.backup.json to use the exact same station names 
as slim_stations/unique_stations.json, eliminating the need for runtime normalization.

The purpose is to ensure that station names in station_graph.json exactly match 
those in slim_stations/unique_stations.json, so that we can directly look up 
stations without normalizing names at runtime.
"""

#!/usr/bin/env python3
import json
import sys
from typing import Dict, List, Set, Any, Tuple

# -------------------------------------------------------
# NORMALIZATION FUNCTIONS (for mapping purposes only)
# -------------------------------------------------------

def normalize_name(name: str) -> str:
    """
    Used only for mapping stations between files.
    The final output will use the original non-normalized names.
    """
    # Apply simple normalization (strip and lowercase)
    name = name.strip().lower()
    
    # Handle Euston Square specially to keep it distinct from Euston
    # This must be checked BEFORE other transformations
    if 'euston square' in name:
        return 'euston square'
    
    # List of common suffixes to remove
    suffixes = [
        ' underground station',
        ' rail station',
        ' dlr station',
        ' overground station',
        ' (london) rail station',
        ' (london)',
        ' station',
        ' underground',
        ' rail',
        ' dlr',
        ' overground',
        ' (for excel)',
        ' (for maritime greenwich)',
        ' ell'
    ]
    
    # Remove suffixes
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    
    # Normalize special characters
    name = name.replace('-', ' ')
    name = name.replace('&', 'and')
    name = name.replace("'s", 's')
    name = name.replace("'", '')
    name = name.replace("(", "")
    name = name.replace(")", "")
    name = name.replace(",", "")
    name = name.replace(".", "")
    
    # Expand common abbreviations
    if ' st ' in name or name.endswith(' st'):
        name = name.replace(' st ', ' street ').replace(' st$', ' street')
    if name == 'baker st' or name == 'baker st.':
        name = 'baker street'
    
    # Handle special cases for stations with line indicators
    for indicator in [
        ' (bakerloo)', ' (circle line)', ' (h&c line)', ' (handc line)', 
        ' (dist&picc line)', ' (distandpicc line)',
        ' (circle)', ' (central)', ' (met)', ' (metropolitan)', 
        ' metropolitan line', ' circle line', ' bakerloo line',
        ' central line', ' district line', ' piccadilly line',
        ' victoria line', ' jubilee line', ' northern line',
        ' hammersmith city line', ' hammersmith and city line',
        ' elizabeth line', ' london overground', ' dlr'
    ]:
        name = name.replace(indicator, '')
    
    # Handle special cases for Heathrow terminals
    if 'heathrow' in name and ('terminal' in name or 'terminals' in name):
        name = 'heathrow'
    
    # Special cases for known problematic stations
    if 'shepherds bush market' in name:
        name = 'shepherds bush market'
    elif 'shepherds bush' in name:
        name = 'shepherds bush'
    
    if 'kings cross' in name or 'king cross' in name or 'kings cross st pancras' in name:
        name = 'kings cross'
    
    if "st james park" in name or 'st jamess park' in name:
        name = 'st jamess park'
        
    if 'st john' in name or 'st johns wood' in name:
        name = 'st johns wood'
        
    if 'st paul' in name:
        name = 'st pauls'
    
    if 'walthamstow central' in name or ('walthamstow' in name and not 'queens' in name):
        name = 'walthamstow'
    
    if 'baker street' in name:
        name = 'baker street'
    
    if 'paddington' in name:
        name = 'paddington'
        
    if 'hammersmith' in name:
        name = 'hammersmith'
        
    if 'kensington olympia' in name:
        name = 'kensington olympia'
    
    # Handle Euston station (but not Euston Square which is handled earlier)
    if 'london euston' in name or name == 'euston':
        name = 'euston'
        
    if 'london liverpool street' in name or 'liverpool street' in name:
        name = 'liverpool street'
        
    if 'st james street' in name:
        name = 'st james street'
    
    # Final clean up of whitespace
    return ' '.join(name.split())

# -------------------------------------------------------
# DATA LOADING FUNCTIONS
# -------------------------------------------------------

def load_station_metadata(metadata_file: str) -> Tuple[Dict[str, str], Dict[str, str], List[Dict]]:
    """
    Load the station metadata from the JSON file.
    
    Args:
        metadata_file: Path to the JSON file
        
    Returns:
        Tuple containing:
        1. Dictionary mapping normalized names to original station names
        2. Dictionary mapping original names to normalized names
        3. Original metadata list
    """
    try:
        # Read the JSON file containing station data
        with open(metadata_file, 'r') as f:
            stations_data = json.load(f)
        
        print(f"Loaded {len(stations_data)} stations from metadata file")
        
        # Create mappings between normalized and original names
        norm_to_orig = {}  # Normalized name -> Original name
        orig_to_norm = {}  # Original name -> Normalized name
        
        # Process each station in the JSON data
        for station in stations_data:
            # Get the original name
            original_name = station['name']
            
            # Apply normalization (for mapping purposes only)
            normalized_name = normalize_name(original_name)
            
            # Store the mappings
            norm_to_orig[normalized_name] = original_name
            orig_to_norm[original_name] = normalized_name
            
            # Also handle child stations
            for child_name in station.get('child_stations', []):
                child_normalized = normalize_name(child_name)
                # Map the child to the parent station's original name
                norm_to_orig[child_normalized] = original_name
                orig_to_norm[child_name] = child_normalized
        
        print(f"Created mappings for {len(norm_to_orig)} normalized station names")
        return norm_to_orig, orig_to_norm, stations_data
    
    except Exception as e:
        print(f"Error loading station metadata: {str(e)}")
        sys.exit(1)

def load_station_graph(graph_file: str) -> Dict[str, Dict[str, float]]:
    """
    Load the station graph from the JSON file.
    
    Args:
        graph_file: Path to the JSON file
        
    Returns:
        The graph data structure
    """
    try:
        # Read the JSON file containing the graph data
        with open(graph_file, 'r') as f:
            graph_data = json.load(f)
        
        print(f"Loaded graph with {len(graph_data)} nodes")
        return graph_data
    
    except Exception as e:
        print(f"Error loading station graph: {str(e)}")
        sys.exit(1)

# -------------------------------------------------------
# MAPPING FUNCTIONS
# -------------------------------------------------------

def create_station_mapping(graph_data: Dict[str, Dict[str, float]], 
                          norm_to_orig: Dict[str, str]) -> Dict[str, str]:
    """
    Create a mapping from graph station names to metadata station names.
    
    Args:
        graph_data: The graph data
        norm_to_orig: Dictionary mapping normalized names to original names
        
    Returns:
        Dictionary mapping graph names to metadata original names
    """
    # Create a mapping from graph station names to metadata station names
    graph_to_metadata = {}
    
    # Keep track of stations we couldn't map
    unmapped_stations = set()
    
    # For each station in the graph
    for graph_station in graph_data.keys():
        # Normalize the graph station name
        normalized_graph_station = normalize_name(graph_station)
        
        # Check if the normalized name exists in metadata
        if normalized_graph_station in norm_to_orig:
            # Map to the original name in the metadata
            graph_to_metadata[graph_station] = norm_to_orig[normalized_graph_station]
        else:
            # Try some heuristics to find a match
            found_match = False
            
            # Check for partial matches
            for norm_name, orig_name in norm_to_orig.items():
                if normalized_graph_station in norm_name or norm_name in normalized_graph_station:
                    graph_to_metadata[graph_station] = orig_name
                    found_match = True
                    break
            
            if not found_match:
                unmapped_stations.add(graph_station)
    
    print(f"Initially mapped {len(graph_to_metadata)} stations from graph to metadata")
    
    if unmapped_stations:
        print(f"\nCould not automatically map {len(unmapped_stations)} stations:")
        for station in sorted(unmapped_stations):
            print(f"  - '{station}'")
        
        # Add manual mappings for these stations
        manual_mappings = {
            'kings cross': 'Kings Cross Underground Station',
            'paddington': 'Paddington Underground Station',
            'walthamstow': 'Walthamstow Central Underground Station',
            'edgware road': 'Edgware Road (Circle Line) Underground Station',
            'edgware road bakerloo': 'Edgware Road (Bakerloo) Underground Station',
            'hammersmith': 'Hammersmith (H&C Line) Underground Station',
            'hammersmith distandpicc line': 'Hammersmith Underground Station',
            'clapham south': 'Clapham South Underground Station',
            'st jamess park': "St. James's Park Underground Station",
            'st james park': "St. James's Park Underground Station",
            'shepherds bush': "Shepherd's Bush Underground Station",
            'goldhawk road': 'Goldhawk Road Underground Station',
            'heathrow': 'Heathrow Terminals 2 & 3 Underground Station',
            'kensington olympia': 'Kensington (Olympia) Rail Station',
            'london euston': 'Euston Underground Station',
            'euston': 'Euston Underground Station',
            'euston square': 'Euston Square Underground Station',
            'london liverpool street': 'Liverpool Street Underground Station',
            'st james street': 'St James Street Rail Station'
        }
        
        # Apply manual mappings
        for graph_station, metadata_name in manual_mappings.items():
            if graph_station in unmapped_stations:
                # Verify the metadata name exists
                if metadata_name in orig_to_norm:
                    graph_to_metadata[graph_station] = metadata_name
                    unmapped_stations.remove(graph_station)
                else:
                    print(f"Warning: Manual mapping '{metadata_name}' not found in metadata")
        
        # Check if there are still unmapped stations
        if unmapped_stations:
            print(f"\nAfter applying manual mappings, {len(unmapped_stations)} stations still could not be mapped:")
            for station in sorted(unmapped_stations):
                print(f"  - '{station}'")
            print("\nPlease add additional manual mappings for these stations.")
        else:
            print("\nAll stations mapped successfully after applying manual mappings")
    
    return graph_to_metadata, unmapped_stations

# -------------------------------------------------------
# GRAPH UPDATE FUNCTION
# -------------------------------------------------------

def update_graph_with_metadata_names(graph_data: Dict[str, Dict[str, float]], 
                                   graph_to_metadata: Dict[str, str],
                                   output_file: str) -> None:
    """
    Update the graph to use exact station names from metadata.
    
    Args:
        graph_data: The original graph data
        graph_to_metadata: Mapping from graph names to metadata names
        output_file: Path to save the updated graph
    """
    # Create a new graph with full station names
    updated_graph = {}
    
    # Keep track of which stations we've updated
    updated_stations = set()
    
    # For each station in the graph
    for graph_station, connections in graph_data.items():
        # Get the metadata name for this station
        if graph_station in graph_to_metadata:
            metadata_name = graph_to_metadata[graph_station]
            
            # Initialize this station in the updated graph if needed
            if metadata_name not in updated_graph:
                updated_graph[metadata_name] = {}
            
            # For each connected station
            for connected_station, time in connections.items():
                # Get the metadata name for the connected station
                if connected_station in graph_to_metadata:
                    connected_metadata_name = graph_to_metadata[connected_station]
                    
                    # Add the connection with the full metadata names
                    updated_graph[metadata_name][connected_metadata_name] = time
                else:
                    print(f"Warning: Could not find metadata name for connected station '{connected_station}'")
            
            # Mark as updated
            updated_stations.add(graph_station)
        else:
            print(f"Warning: Could not find metadata name for station '{graph_station}'")
    
    # Check if we updated all stations
    if len(updated_stations) < len(graph_data):
        print(f"\nWarning: Only updated {len(updated_stations)} out of {len(graph_data)} stations")
        
        # Show which stations we didn't update
        not_updated = set(graph_data.keys()) - updated_stations
        print(f"Did not update {len(not_updated)} stations:")
        for station in sorted(not_updated):
            print(f"  - '{station}'")
    else:
        print(f"\nUpdated all {len(graph_data)} stations")
    
    # Save the updated graph
    with open(output_file, 'w') as f:
        json.dump(updated_graph, f, indent=2)
    
    print(f"\nSaved updated graph to {output_file}")
    print(f"Original graph had {len(graph_data)} nodes")
    print(f"Updated graph has {len(updated_graph)} nodes")

# -------------------------------------------------------
# MAIN EXECUTION FLOW
# -------------------------------------------------------

def main():
    # Paths to files
    metadata_file = "slim_stations/unique_stations.json"
    graph_file = "station_graph.json"
    output_file = "station_graph.normalized.json"
    
    # Load data from files
    print("Loading station metadata...")
    norm_to_orig, orig_to_norm, station_data = load_station_metadata(metadata_file)
    
    print("\nLoading station graph...")
    graph_data = load_station_graph(graph_file)
    
    # Create a mapping from graph station names to metadata station names
    print("\nCreating mapping from graph stations to metadata stations...")
    graph_to_metadata, unmapped_stations = create_station_mapping(graph_data, norm_to_orig)
    
    # If there are unmapped stations, we can't proceed
    if unmapped_stations:
        print("\nCannot update graph because some stations could not be mapped.")
        print("Please add manual mappings for these stations in the script.")
        return
    
    # Update the graph with metadata station names
    print("\nUpdating graph with metadata station names...")
    update_graph_with_metadata_names(graph_data, graph_to_metadata, output_file)
    
    print("\nDone!")

if __name__ == "__main__":
    main() 