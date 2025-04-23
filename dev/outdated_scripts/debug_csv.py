"""
This script is used to debug the Inter_station_times.csv file.
It prints information about the structure of the file to help with debugging.
"""

#!/usr/bin/env python3
import csv

def debug_csv(csv_path):
    """
    Print information about the structure of a CSV file to help with debugging.
    
    Args:
        csv_path: Path to the CSV file to debug
    """
    print(f"Debugging CSV file: {csv_path}")
    
    # Open the file and look at the first few rows
    with open(csv_path, 'r') as f:
        # First just read raw lines
        print("\nFirst 5 raw lines:")
        for i, line in enumerate(f):
            if i >= 5:
                break
            print(f"Line {i+1}: {line.strip()}")
        
        # Reset file pointer to beginning
        f.seek(0)
        
        # Now try to read with the CSV reader
        print("\nReading with CSV DictReader:")
        reader = csv.DictReader(f, skipinitialspace=True)
        
        # Print the fieldnames detected by the reader
        print(f"\nFields detected: {reader.fieldnames}")
        
        # Try to read a few rows
        print("\nFirst 5 rows:")
        for i, row in enumerate(reader):
            if i >= 5:
                break
            print(f"Row {i+1}:")
            for key, value in row.items():
                print(f"  {key}: '{value}'")
            
            # For the first row, specifically check the fields we need
            if i == 0:
                from_key = 'Station from (A)'
                to_key = 'Station to (B)'
                unimpeded_key = 'Un-impeded Running Time (Mins)'
                interpeak_key = 'Inter peak (1000 - 1600) Running time (mins)'
                
                print("\nChecking specific fields in first row:")
                print(f"  '{from_key}' exists: {from_key in row}")
                print(f"  '{to_key}' exists: {to_key in row}")
                print(f"  '{unimpeded_key}' exists: {unimpeded_key in row}")
                print(f"  '{interpeak_key}' exists: {interpeak_key in row}")
                
                if from_key in row:
                    print(f"  Value of '{from_key}': '{row[from_key]}'")
                if to_key in row:
                    print(f"  Value of '{to_key}': '{row[to_key]}'")
                if unimpeded_key in row:
                    print(f"  Value of '{unimpeded_key}': '{row[unimpeded_key]}'")
                if interpeak_key in row:
                    print(f"  Value of '{interpeak_key}': '{row[interpeak_key]}'")

if __name__ == "__main__":
    # Path to the CSV file
    csv_path = "Inter_station_times.csv"
    
    # Debug the CSV
    debug_csv(csv_path) 