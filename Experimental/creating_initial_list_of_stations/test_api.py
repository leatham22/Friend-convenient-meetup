"""
This script was used to test the TfL API connection and to ensure that the API key is correct. 

It was used in the process of creating the `unique_stations.json` file, which is the master data source for all potential stations a user can start/travel to. 
"""

import os
from dotenv import load_dotenv
import requests

def test_tfl_api():
    # Load environment variables from .env
    print("1. Testing .env file loading...")
    load_dotenv()
    
    # Try to get the API key
    print("\n2. Checking for API key...")
    api_key = os.environ.get('TFL_API_KEY')
    if not api_key:
        print("❌ Error: Could not find TFL_API_KEY in environment variables")
        print("   Make sure your .env file exists and contains: TFL_API_KEY=your_key_here")
        return
    print("✓ API key found!")
    
    # Test the API with a simple request (getting Victoria station info)
    print("\n3. Testing API connection...")
    test_url = "https://api.tfl.gov.uk/StopPoint/940GZZLUVIC"  # Victoria station
    params = {
        'app_key': api_key
    }
    
    try:
        response = requests.get(test_url, params=params)
        response.raise_for_status()  # Check if request was successful
        
        station_data = response.json()
        station_name = station_data.get('commonName', 'Unknown Station')
        
        print("✓ Successfully connected to TfL API!")
        print(f"✓ Test request worked - got data for: {station_name}")
        print("\n🎉 Everything is set up correctly! You can now run your main program.")
        
    except requests.exceptions.RequestException as e:
        print("❌ Error connecting to TfL API:")
        print(f"   {str(e)}")
        print("\nPossible issues:")
        print("1. Check if your API key is correct")
        print("2. Check your internet connection")
        print("3. The TfL API service might be down")

if __name__ == "__main__":
    test_tfl_api() 