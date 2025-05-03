import numpy as np
import math
from scipy.spatial import ConvexHull

# --- Station Filtering Functions ---

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points
    on the Earth (specified in decimal degrees) using Haversine formula.

    Args:
        lat1, lon1: Latitude and longitude of point 1 (in degrees).
        lat2, lon2: Latitude and longitude of point 2 (in degrees).

    Returns:
        float: Distance in kilometers.
    """
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def is_within_radius(centroid_lat, centroid_lon, radius_km, station_lat, station_lon):
    """
    Checks if a station is within a given radius from the centroid.

    Args:
        centroid_lat, centroid_lon: Coordinates of the center point.
        radius_km: The maximum distance allowed (in kilometers).
        station_lat, station_lon: Coordinates of the station to check.

    Returns:
        bool: True if the station is within the radius, False otherwise.
    """
    if None in [centroid_lat, centroid_lon, station_lat, station_lon]:
        return False
    distance = haversine_distance(centroid_lat, centroid_lon, station_lat, station_lon)
    return distance <= radius_km

def create_convex_hull(points):
    """
    Creates a convex hull from a set of points and returns the hull points.
    
    Args:
        points (list): List of [lat, lon] coordinates
        
    Returns:
        hull_points (np.array): Array of coordinates forming the convex hull
        hull (ConvexHull): The hull object for additional calculations
    """
    # Convert points to numpy array for ConvexHull calculation
    points_array = np.array(points)
    
    # Create the convex hull
    hull = ConvexHull(points_array)
    
    # Get the points that form the hull
    hull_points = points_array[hull.vertices]
    
    return hull_points, hull

def point_in_hull(point, hull_points, hull):
    """
    Checks if a point lies within the convex hull.
    
    Args:
        point (list): [lat, lon] coordinates to check
        hull_points (np.array): Array of coordinates forming the convex hull
        hull (ConvexHull): The hull object for calculations
        
    Returns:
        bool: True if point is inside hull, False otherwise
    """
    # Add a small buffer to the hull (0.5% expansion)
    centroid = np.mean(hull_points, axis=0)
    hull_points_buffered = np.array([
        p + (p - centroid) * 0.005 for p in hull_points
    ])
    
    # Create new hull with buffered points
    hull_buffered = ConvexHull(hull_points_buffered)
    
    # Test if point is in buffered hull
    new_points = np.vstack((hull_points_buffered, point))
    new_hull = ConvexHull(new_points)
    
    # If the number of vertices is the same, the point was inside
    return len(new_hull.vertices) == len(hull_buffered.vertices)

def filter_stations_by_convex_hull(stations, start_locations):
    """
    Filters stations that lie within the convex hull created by start locations.
    
    Args:
        stations (list): List of station dictionaries
        start_locations (list): List of [lat, lon] coordinates for start points
        
    Returns:
        list: Filtered list of stations within the hull
    """
    # Create convex hull from start locations
    hull_points, hull = create_convex_hull(start_locations)
    
    # Filter stations
    filtered_stations = []
    for station in stations:
        station_point = np.array([station['lat'], station['lon']])
        if point_in_hull(station_point, hull_points, hull):
            filtered_stations.append(station)
            
    print(f"Found {len(filtered_stations)} stations within convex hull.")
    return filtered_stations

def calculate_centroid_with_coverage(locations, coverage_percent=0.7):
    """
    Calculates the centroid and minimum radius needed to cover the specified percentage of locations.
    
    Args:
        locations (list): List of [lat, lon] coordinates
        coverage_percent (float): Percentage of points to cover (0.0 to 1.0)
        
    Returns:
        tuple: (centroid_lat, centroid_lon, radius_km)
    """
    if not locations:
        return None, None, None
    
    # Calculate centroid
    centroid_lat = sum(loc[0] for loc in locations) / len(locations)
    centroid_lon = sum(loc[1] for loc in locations) / len(locations)
    
    # Calculate distances from centroid to all points
    distances = []
    for lat, lon in locations:
        dist = haversine_distance(centroid_lat, centroid_lon, lat, lon)
        distances.append(dist)
    
    # Sort distances and find the radius needed for coverage
    distances.sort()
    coverage_index = int(len(distances) * coverage_percent)
    radius_km = distances[coverage_index - 1]  # -1 because index is 0-based
    
    return centroid_lat, centroid_lon, radius_km

def point_in_ellipse(point_lat, point_lon, focus1_lat, focus1_lon, focus2_lat, focus2_lon, major_axis):
    """
    Determines if a point lies within an ellipse defined by two foci.
    Uses the standard ellipse definition: sum of distances to foci <= major axis
    
    Important geometric note:
    - If major_axis equals the distance between foci (2c), the ellipse collapses to a line
    - We use major_axis = 1.2 * distance to create a reasonable search area
    - This works better with the centroid filtering stage by allowing more initial candidates
    
    Args:
        point_lat, point_lon: Coordinates of the point to check
        focus1_lat, focus1_lon: Coordinates of the first focus (starting point)
        focus2_lat, focus2_lon: Coordinates of the second focus (starting point)
        major_axis: The major axis length of the ellipse (in km)
        
    Returns:
        bool: True if the point is inside or on the ellipse, False otherwise
    """
    # Calculate distances from point to each focus
    dist1 = haversine_distance(point_lat, point_lon, focus1_lat, focus1_lon)
    dist2 = haversine_distance(point_lat, point_lon, focus2_lat, focus2_lon)
    
    # Allow for small numerical error (0.5% tolerance)
    # Increased from 0.1% to 0.5% to account for Earth's curvature effects
    tolerance = major_axis * 0.005
    
    # Check if sum of distances is less than or equal to major axis (with tolerance)
    # This is the definition of an ellipse: sum of distances to foci is constant
    if (dist1 + dist2) > (major_axis + tolerance):
        return False
        
    return True

def filter_stations_optimized(all_stations, people_data):
    """
    Two-step filtering process:
    1. If more than 2 people: Filter stations within convex hull of start locations
       If 2 people: Filter stations within an elliptical area focused around the midpoint
    2. Further filter based on centroid circle covering 70% of start locations
    
    Args:
        all_stations (list): List of all station dictionaries
        people_data (list): List of dictionaries containing people's start locations
        
    Returns:
        list: Filtered list of stations
    """
    # Extract start locations
    start_locations = [(p['start_station_lat'], p['start_station_lon']) 
                      for p in people_data]
    
    # Step 1: Initial Filtering
    print("\nStep 1: Filtering stations...")
    if len(start_locations) > 2:
        print("Using convex hull method for filtering (3+ people)")
        hull_filtered = filter_stations_by_convex_hull(all_stations, start_locations)
    else:
        print("Using elliptical boundary method for filtering (2 people)")
        # Get the two points
        point1_lat, point1_lon = start_locations[0]
        point2_lat, point2_lon = start_locations[1]
        
        # Calculate direct distance between points
        direct_distance = haversine_distance(
            point1_lat, point1_lon,
            point2_lat, point2_lon
        )
        
        # Use 1.2 * distance between stations as the major axis
        # This creates a wider ellipse than using just the direct distance,
        # giving a more reasonable search area that works better with the centroid filtering
        major_axis = direct_distance * 1.2
        
        # Filter stations within the ellipse
        hull_filtered = []
        for station in all_stations:
            if point_in_ellipse(
                station['lat'], station['lon'],
                point1_lat, point1_lon,
                point2_lat, point2_lon,
                major_axis
            ):
                hull_filtered.append(station)
                
        print(f"Found {len(hull_filtered)} stations within elliptical boundary")
        print(f"Direct distance between points: {direct_distance:.2f}km")
        print(f"Ellipse major axis: {major_axis:.2f}km (1.2 * direct distance)")
    
    # Step 2: Centroid Circle Filtering
    print("\nStep 2: Further filtering using centroid circle...")
    
    # For 2 people, calculate the centroid as the midpoint between stations
    if len(start_locations) == 2:
        centroid_lat = (start_locations[0][0] + start_locations[1][0]) / 2
        centroid_lon = (start_locations[0][1] + start_locations[1][1]) / 2
        # Use 70% of the distance to center as the radius
        radius_km = (direct_distance / 2) * 0.7
        print(f"Using midpoint as centroid and {radius_km:.2f}km as radius (70% of distance to center)")
    else:
        # For 3+ people, use the original coverage-based calculation
        centroid_lat, centroid_lon, radius_km = calculate_centroid_with_coverage(
            start_locations, coverage_percent=0.7
        )
    
    final_filtered = []
    for station in hull_filtered:
        if is_within_radius(centroid_lat, centroid_lon, radius_km,
                          station['lat'], station['lon']):
            final_filtered.append(station)
            
    print(f"Final filtered count: {len(final_filtered)} stations")
    return final_filtered 