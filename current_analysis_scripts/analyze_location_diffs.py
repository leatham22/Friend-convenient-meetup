import json
import math
import os

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

def analyze_differences():
    old_stations = load_stations('raw_stations/unique_stations.json')
    new_stations = load_stations('raw_stations/unique_stations2.json')
    
    differences = []
    for name in set(old_stations.keys()) & set(new_stations.keys()):
        old = old_stations[name]
        new = new_stations[name]
        if old['lat'] != new['lat'] or old['lon'] != new['lon']:
            dist = calculate_distance(
                old['lat'], old['lon'],
                new['lat'], new['lon']
            )
            differences.append((name, dist))
    
    # Sort by distance
    differences.sort(key=lambda x: x[1], reverse=True)
    
    # Print analysis
    print("\nLocation Difference Analysis:")
    print(f"Total stations with different coordinates: {len(differences)}")
    
    if differences:
        print("\nLargest differences:")
        for name, dist in differences[:10]:
            print(f"- {name}: {dist:.1f}m")
        
        # Calculate statistics
        distances = [d for _, d in differences]
        avg_dist = sum(distances) / len(distances)
        max_dist = max(distances)
        min_dist = min(distances)
        
        print(f"\nStatistics:")
        print(f"- Average difference: {avg_dist:.1f}m")
        print(f"- Maximum difference: {max_dist:.1f}m")
        print(f"- Minimum difference: {min_dist:.1f}m")
        
        # Count significant differences
        sig_diffs = sum(1 for _, d in differences if d > 100)
        print(f"\nStations with >100m difference: {sig_diffs}")

if __name__ == "__main__":
    analyze_differences() 