# Spatial Filtering Package (`spatial_filtering`)

## Purpose

This package provides functions for spatially filtering potential meeting point stations based on the geographic distribution of the users' starting locations. It employs geometric techniques like convex hulls, ellipses, and centroid calculations to narrow down the search space before more computationally intensive travel time calculations are performed.

## Modules

### `filtering_logic.py`

Contains the core logic for spatial filtering.

#### Functions:

*   **`haversine_distance(lat1, lon1, lat2, lon2)`**: Calculates the great-circle distance (in kilometers) between two latitude/longitude points using the Haversine formula. Used as a utility for various geometric calculations.
*   **`is_within_radius(centroid_lat, centroid_lon, radius_km, station_lat, station_lon)`**: Checks if a given station's coordinates fall within a specified radius (in kilometers) from a central point (centroid). Used in the centroid filtering step.
*   **`create_convex_hull(points)`**: Computes the convex hull for a set of 2D points (latitude/longitude). Returns the points forming the hull vertices and the Scipy `ConvexHull` object.
*   **`point_in_hull(point, hull_points, hull)`**: Determines if a given point lies inside (or on the boundary of) a pre-computed convex hull. Includes a small buffer expansion on the hull for robustness.
*   **`filter_stations_by_convex_hull(stations, start_locations)`**: Filters a list of stations, keeping only those that fall within the convex hull generated from the users' starting locations. Primarily used when there are 3 or more users.
*   **`calculate_centroid_with_coverage(locations, coverage_percent=0.7)`**: Calculates the geographic centroid of a list of locations and determines the minimum radius required to enclose a specified percentage (default 70%) of those locations.
*   **`point_in_ellipse(point_lat, point_lon, focus1_lat, focus1_lon, focus2_lat, focus2_lon, major_axis)`**: Determines if a given point lies within an ellipse defined by two foci (the start locations of two users) and a major axis length. Uses the property that the sum of distances from any point on the ellipse to the two foci is constant (equal to the major axis length).
*   **`filter_stations_optimized(all_stations, people_data)`**: Orchestrates the two-step spatial filtering process:
    1.  **Initial Filter:** Uses `filter_stations_by_convex_hull` for 3+ users or an elliptical boundary (`point_in_ellipse`) for 2 users.
    2.  **Centroid Filter:** Further refines the filtered list by keeping only stations within a radius around the centroid (calculated via `calculate_centroid_with_coverage` or as the midpoint for 2 users) that covers 70% of the initial starting locations. 