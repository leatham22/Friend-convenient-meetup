import json
import math
import os
from collections import defaultdict
import requests
from typing import Dict, List, Tuple

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_stations(filename):
    filepath = os.path.join(PROJECT_ROOT, filename)
    with open(filepath, 'r') as f:
        stations = json.load(f)
    return {s['name']: s for s in stations}

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two points"""
    R = 6371000  # Earth's radius in meters
    
    # Convert to radians
    lat1, lon1 = math.radians(lat1), math.radians(lon1)
    lat2, lon2 = math.radians(lat2), math.radians(lon2)
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate the bearing (direction) from point 1 to point 2"""
    # Convert to radians
    lat1, lon1 = math.radians(lat1), math.radians(lon1)
    lat2, lon2 = math.radians(lat2), math.radians(lon2)
    
    dlon = lon2 - lon1
    
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    
    bearing = math.atan2(y, x)
    # Convert to degrees
    bearing = math.degrees(bearing)
    # Normalize to 0-360
    bearing = (bearing + 360) % 360
    
    # Convert to cardinal directions
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    index = round(bearing / 45) % 8
    return directions[index]

def get_key_type(station_data):
    """Determine if a station is using HubNaptanCode or location-based key"""
    # Check if station has child_stations (indicating it's a hub)
    if 'child_stations' in station_data and station_data['child_stations']:
        return 'hub'
    return 'location'

def get_primary_line_type(station_data) -> str:
    """Determine the primary line type for a station based on its name"""
    name = station_data['name'].lower()
    if 'dlr' in name:
        return 'dlr'
    elif 'underground' in name:
        return 'tube'
    elif 'elizabeth' in name or name == 'abbey wood':  # Abbey Wood is part of Elizabeth line
        return 'elizabeth-line'
    elif 'rail' in name or any(x in name for x in ['overground', 'riverside']):
        return 'overground'
    return 'unknown'

def is_interchange_station(station_data) -> bool:
    """Enhanced interchange detection"""
    modes = set(station_data.get('modes', []))
    lines = set()
    
    # Extract unique line names
    for line in station_data.get('lines', []):
        if isinstance(line, str):
            lines.add(line)
        elif isinstance(line, dict) and 'name' in line:
            lines.add(line['name'])
    
    # Consider it an interchange if:
    # 1. Has multiple modes OR
    # 2. Has multiple lines within the same mode OR
    # 3. Has child stations
    return (len(modes) > 1 or 
            len(lines) > 1 or 
            (station_data.get('child_stations', []) and len(station_data['child_stations']) > 0))

def fetch_station_entrances(station_name: str) -> List[Dict]:
    """Fetch station entrance coordinates from TFL API"""
    # Clean the station name
    search_name = station_name.replace(' Underground Station', '')
    search_name = search_name.replace(' DLR Station', '')
    search_name = search_name.replace(' Station', '')
    
    try:
        # Search for the station
        url = f"https://api.tfl.gov.uk/StopPoint/Search/{search_name}"
        response = requests.get(url)
        data = response.json()
        
        if 'matches' in data and data['matches']:
            station_id = data['matches'][0]['id']
            
            # Get detailed station info including entrances
            url = f"https://api.tfl.gov.uk/StopPoint/{station_id}"
            response = requests.get(url)
            data = response.json()
            
            # Extract entrance coordinates
            entrances = []
            if 'additionalProperties' in data:
                for prop in data['additionalProperties']:
                    if prop.get('key') == 'Entrance':
                        entrance = {
                            'name': prop.get('value', ''),
                            'lat': float(prop.get('lat', 0)),
                            'lon': float(prop.get('lon', 0))
                        }
                        entrances.append(entrance)
            
            return entrances
    except Exception as e:
        print(f"Error fetching entrances for {station_name}: {str(e)}")
    
    return []

def analyze_differences():
    old_stations = load_stations('station_backups/unique_stations_backup_20250417_131811.json')
    new_stations = load_stations('slim_stations/unique_stations.json')
    
    # Initialize analysis data structures
    differences = []
    key_type_stats = {'hub': 0, 'location': 0}
    direction_stats = defaultdict(int)
    line_type_stats = defaultdict(lambda: {'count': 0, 'total_dist': 0})
    entrance_analysis = []
    
    for name in set(old_stations.keys()) & set(new_stations.keys()):
        old = old_stations[name]
        new = new_stations[name]
        
        if old['lat'] != new['lat'] or old['lon'] != new['lon']:
            # Calculate distance
            dist = calculate_distance(
                old['lat'], old['lon'],
                new['lat'], new['lon']
            )
            
            # Calculate direction of change
            direction = calculate_bearing(
                old['lat'], old['lon'],
                new['lat'], new['lon']
            )
            
            # Determine key type and line type
            key_type = get_key_type(new)
            line_type = get_primary_line_type(new)
            
            # Enhanced interchange detection
            is_interchange = is_interchange_station(new)
            
            # Store all analysis data
            diff_data = {
                'name': name,
                'distance': dist,
                'direction': direction,
                'key_type': key_type,
                'line_type': line_type,
                'is_interchange': is_interchange,
                'old_coords': {'lat': old['lat'], 'lon': old['lon']},
                'new_coords': {'lat': new['lat'], 'lon': new['lon']}
            }
            differences.append(diff_data)
            
            # Update statistics
            key_type_stats[key_type] += 1
            direction_stats[direction] += 1
            line_type_stats[line_type]['count'] += 1
            line_type_stats[line_type]['total_dist'] += dist
            
            # For significant differences, analyze entrance positions
            if dist > 80:  # Analyze stations with >80m difference
                entrances = fetch_station_entrances(name)
                if entrances:
                    # Find closest and furthest entrances to both old and new coordinates
                    entrance_dists_old = []
                    entrance_dists_new = []
                    for entrance in entrances:
                        dist_to_old = calculate_distance(
                            entrance['lat'], entrance['lon'],
                            old['lat'], old['lon']
                        )
                        dist_to_new = calculate_distance(
                            entrance['lat'], entrance['lon'],
                            new['lat'], new['lon']
                        )
                        entrance_dists_old.append(dist_to_old)
                        entrance_dists_new.append(dist_to_new)
                    
                    entrance_analysis.append({
                        'name': name,
                        'num_entrances': len(entrances),
                        'min_dist_to_old': min(entrance_dists_old),
                        'max_dist_to_old': max(entrance_dists_old),
                        'min_dist_to_new': min(entrance_dists_new),
                        'max_dist_to_new': max(entrance_dists_new)
                    })
    
    # Sort by distance
    differences.sort(key=lambda x: x['distance'], reverse=True)
    
    # Print analysis
    print("\nLocation Difference Analysis:")
    print(f"Total stations with different coordinates: {len(differences)}")
    
    if differences:
        print("\nLargest differences:")
        for diff in differences[:10]:
            print(f"- {diff['name']}: {diff['distance']:.1f}m")
            print(f"  Direction: {diff['direction']}, Type: {diff['key_type']}, "
                  f"Line: {diff['line_type']}, Interchange: {'Yes' if diff['is_interchange'] else 'No'}")
        
        # Calculate statistics
        distances = [d['distance'] for d in differences]
        avg_dist = sum(distances) / len(distances)
        max_dist = max(distances)
        min_dist = min(distances)
        
        print(f"\nDistance Statistics:")
        print(f"- Average difference: {avg_dist:.1f}m")
        print(f"- Maximum difference: {max_dist:.1f}m")
        print(f"- Minimum difference: {min_dist:.1f}m")
        
        print(f"\nKey Type Analysis:")
        print(f"- Hub-based stations: {key_type_stats['hub']}")
        print(f"- Location-based stations: {key_type_stats['location']}")
        
        print(f"\nLine Type Analysis:")
        for line_type, stats in line_type_stats.items():
            if stats['count'] > 0:
                avg_dist = stats['total_dist'] / stats['count']
                print(f"- {line_type}: {stats['count']} stations, avg diff: {avg_dist:.1f}m")
        
        print(f"\nDirectional Analysis:")
        for direction, count in sorted(direction_stats.items()):
            print(f"- {direction}: {count} stations ({(count/len(differences)*100):.1f}%)")
        
        print(f"\nInterchange Analysis:")
        interchange_count = sum(1 for d in differences if d['is_interchange'])
        print(f"- Interchange stations: {interchange_count} ({(interchange_count/len(differences)*100):.1f}%)")
        print(f"- Single-line stations: {len(differences)-interchange_count} "
              f"({((len(differences)-interchange_count)/len(differences)*100):.1f}%)")
        
        if entrance_analysis:
            print(f"\nEntrance Analysis (for stations with >80m difference):")
            for station in entrance_analysis:
                print(f"\n{station['name']}:")
                print(f"- Number of entrances: {station['num_entrances']}")
                print(f"- Distance to old coordinates: {station['min_dist_to_old']:.1f}m - {station['max_dist_to_old']:.1f}m")
                print(f"- Distance to new coordinates: {station['min_dist_to_new']:.1f}m - {station['max_dist_to_new']:.1f}m")
        
        # Count significant differences
        sig_diffs = sum(1 for d in differences if d['distance'] > 100)
        print(f"\nStations with >100m difference: {sig_diffs}")
        
        # Analyze correlation between distance and station type
        hub_distances = [d['distance'] for d in differences if d['key_type'] == 'hub']
        loc_distances = [d['distance'] for d in differences if d['key_type'] == 'location']
        
        if hub_distances:
            avg_hub_dist = sum(hub_distances) / len(hub_distances)
            print(f"\nAverage difference for hub-based stations: {avg_hub_dist:.1f}m")
        if loc_distances:
            avg_loc_dist = sum(loc_distances) / len(loc_distances)
            print(f"Average difference for location-based stations: {avg_loc_dist:.1f}m")

if __name__ == "__main__":
    analyze_differences() 