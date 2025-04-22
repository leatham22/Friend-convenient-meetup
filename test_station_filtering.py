import unittest
import math
import json
from main import (
    haversine_distance,
    point_in_ellipse,
    is_within_radius,
    load_station_data
)

class TestStationFiltering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load real station data for testing
        cls.all_stations = load_station_data()
        
        # Define test stations (from user example)
        cls.ladbroke_grove = {
            'name': 'Ladbroke Grove Underground Station',
            'lat': 51.5173,  # Actual coordinates
            'lon': -0.2106
        }
        cls.canary_wharf = {
            'name': 'Canary Wharf Underground Station',
            'lat': 51.5037,  # Actual coordinates
            'lon': -0.0147
        }
        
    def test_haversine_distance(self):
        """Test distance calculation between Ladbroke Grove and Canary Wharf"""
        distance = haversine_distance(
            self.ladbroke_grove['lat'], 
            self.ladbroke_grove['lon'],
            self.canary_wharf['lat'], 
            self.canary_wharf['lon']
        )
        print(f"\nDistance between stations: {distance:.2f}km")
        self.assertGreater(distance, 0)  # Should be positive
        self.assertLess(distance, 20)    # Should be less than 20km
        
    def test_point_in_ellipse(self):
        """Test if points are correctly identified as inside/outside ellipse"""
        # Calculate direct distance for major axis
        direct_distance = haversine_distance(
            self.ladbroke_grove['lat'], 
            self.ladbroke_grove['lon'],
            self.canary_wharf['lat'], 
            self.canary_wharf['lon']
        )
        
        # Test both stations are on the ellipse (should be True as they define the ellipse)
        result_ladbroke = point_in_ellipse(
            self.ladbroke_grove['lat'], 
            self.ladbroke_grove['lon'],
            self.ladbroke_grove['lat'], 
            self.ladbroke_grove['lon'],
            self.canary_wharf['lat'], 
            self.canary_wharf['lon'],
            direct_distance
        )
        result_canary = point_in_ellipse(
            self.canary_wharf['lat'], 
            self.canary_wharf['lon'],
            self.ladbroke_grove['lat'], 
            self.ladbroke_grove['lon'],
            self.canary_wharf['lat'], 
            self.canary_wharf['lon'],
            direct_distance
        )
        
        print(f"\nLabroke Grove in ellipse: {result_ladbroke}")
        print(f"Canary Wharf in ellipse: {result_canary}")
        
        self.assertTrue(result_ladbroke, "Ladbroke Grove should be in ellipse")
        self.assertTrue(result_canary, "Canary Wharf should be in ellipse")
        
        # Test midpoint (should definitely be in ellipse)
        mid_lat = (self.ladbroke_grove['lat'] + self.canary_wharf['lat']) / 2
        mid_lon = (self.ladbroke_grove['lon'] + self.canary_wharf['lon']) / 2
        
        result_midpoint = point_in_ellipse(
            mid_lat, mid_lon,
            self.ladbroke_grove['lat'], 
            self.ladbroke_grove['lon'],
            self.canary_wharf['lat'], 
            self.canary_wharf['lon'],
            direct_distance
        )
        print(f"Midpoint in ellipse: {result_midpoint}")
        self.assertTrue(result_midpoint, "Midpoint should be in ellipse")
        
    def test_stations_in_ellipse(self):
        """Test how many stations are found within the ellipse"""
        direct_distance = haversine_distance(
            self.ladbroke_grove['lat'], 
            self.ladbroke_grove['lon'],
            self.canary_wharf['lat'], 
            self.canary_wharf['lon']
        )
        
        # Count stations in ellipse
        stations_in_ellipse = []
        for station in self.all_stations:
            if point_in_ellipse(
                station['lat'], station['lon'],
                self.ladbroke_grove['lat'], 
                self.ladbroke_grove['lon'],
                self.canary_wharf['lat'], 
                self.canary_wharf['lon'],
                direct_distance
            ):
                stations_in_ellipse.append(station)
        
        print(f"\nFound {len(stations_in_ellipse)} stations in ellipse")
        print("Stations found:")
        for station in stations_in_ellipse:
            print(f"- {station['name']}")
            
        self.assertGreater(len(stations_in_ellipse), 0, "Should find some stations in ellipse")
        
    def test_circle_filtering(self):
        """Test the centroid circle filtering"""
        # Calculate midpoint
        mid_lat = (self.ladbroke_grove['lat'] + self.canary_wharf['lat']) / 2
        mid_lon = (self.ladbroke_grove['lon'] + self.canary_wharf['lon']) / 2
        
        # Calculate radius (70% of distance to center)
        direct_distance = haversine_distance(
            self.ladbroke_grove['lat'], 
            self.ladbroke_grove['lon'],
            self.canary_wharf['lat'], 
            self.canary_wharf['lon']
        )
        radius_km = (direct_distance / 2) * 0.7
        
        # Count stations in circle
        stations_in_circle = []
        for station in self.all_stations:
            if is_within_radius(
                mid_lat, mid_lon, radius_km,
                station['lat'], station['lon']
            ):
                stations_in_circle.append(station)
                
        print(f"\nFound {len(stations_in_circle)} stations in circle")
        print(f"Circle center: ({mid_lat:.4f}, {mid_lon:.4f})")
        print(f"Circle radius: {radius_km:.2f}km")
        print("Stations found:")
        for station in stations_in_circle:
            print(f"- {station['name']}")
            
        self.assertGreater(len(stations_in_circle), 0, "Should find some stations in circle")
        
    def test_combined_filtering(self):
        """Test the complete filtering process"""
        # Step 1: Ellipse Filtering
        direct_distance = haversine_distance(
            self.ladbroke_grove['lat'], 
            self.ladbroke_grove['lon'],
            self.canary_wharf['lat'], 
            self.canary_wharf['lon']
        )
        
        stations_in_ellipse = []
        for station in self.all_stations:
            if point_in_ellipse(
                station['lat'], station['lon'],
                self.ladbroke_grove['lat'], 
                self.ladbroke_grove['lon'],
                self.canary_wharf['lat'], 
                self.canary_wharf['lon'],
                direct_distance
            ):
                stations_in_ellipse.append(station)
                
        # Step 2: Circle Filtering
        mid_lat = (self.ladbroke_grove['lat'] + self.canary_wharf['lat']) / 2
        mid_lon = (self.ladbroke_grove['lon'] + self.canary_wharf['lon']) / 2
        radius_km = (direct_distance / 2) * 0.7
        
        final_stations = []
        for station in stations_in_ellipse:
            if is_within_radius(
                mid_lat, mid_lon, radius_km,
                station['lat'], station['lon']
            ):
                final_stations.append(station)
                
        print(f"\nComplete filtering process:")
        print(f"1. Found {len(stations_in_ellipse)} stations in ellipse")
        print(f"2. Found {len(final_stations)} stations after circle filtering")
        print("\nFinal stations:")
        for station in final_stations:
            print(f"- {station['name']}")
            
        self.assertGreater(len(final_stations), 0, "Should find some stations after complete filtering")

if __name__ == '__main__':
    unittest.main() 