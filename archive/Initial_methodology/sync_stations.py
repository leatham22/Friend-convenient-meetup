import json
import requests
from datetime import datetime
import os
from fuzzywuzzy import fuzz  # We'll use this for comparing station names
import sys
import shutil

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class StationSync:
    def __init__(self):
        self.api_key = os.getenv('TFL_API_KEY')  # Get API key from environment variable
        self.base_url = "https://api.tfl.gov.uk"
        # Update paths to be relative to project root
        self.stations_file = os.path.join(PROJECT_ROOT, 'slim_stations', 'unique_stations.json')
        self.backup_dir = os.path.join(PROJECT_ROOT, 'station_backups')
        self.last_sync_file = os.path.join(PROJECT_ROOT, 'last_sync.txt')
        self.threshold_percentage = 0.9  # Allow 10% variation in station count
        self.lines = {
            'tube': ['bakerloo', 'central', 'circle', 'district', 'hammersmith-city', 
                    'jubilee', 'metropolitan', 'northern', 'piccadilly', 'victoria', 
                    'waterloo-city'],
            'dlr': ['dlr'],
            'overground': ['mildmay', 'windrush', 'lioness', 'weaver', 'suffragette', 'liberty'],
            'elizabeth-line': ['elizabeth']
        }
        # Split patterns into different types for optimization
        self.suffixes = [
            ' underground station',
            ' overground station',
            ' dlr station',
            ' rail station',
            ' station',
            ' underground',
            ' overground',
            ' dlr'
        ]
        self.prefixes = [
            'london ',
        ]
        self.patterns = [
            ' (h&c line)',
            ' (central)',
            ' (dist&picc line)',
            ' (for excel)',
            ' (london)',
            ' ell '  # Added space after to avoid matching words like 'well'
        ]
        # Create backups directory if it doesn't exist
        os.makedirs(self.backup_dir, exist_ok=True)
        
    def normalize_station_name(self, name):
        """Normalize station name by removing common suffixes and standardizing format"""
        if not name:
            return ""
            
        name = name.lower().strip()
        
        # First standardize special characters
        name = name.replace(" & ", " and ")
        name = name.replace("&", "and")  # Handle cases without spaces
        name = name.replace("-", " ")
        name = name.replace("'", "")
        name = name.replace('"', '')
        name = name.replace("(", " ")
        name = name.replace(")", " ")
        
        # Clean spaces after character standardization
        name = ' '.join(name.split())  # More efficient than multiple replace
        
        # Remove prefixes (O(1) operations)
        for prefix in self.prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
                
        # Remove suffixes (O(1) operations)
        for suffix in self.suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
                
        # Clean spaces again
        name = ' '.join(name.split())
        
        # Only do pattern search if still needed (O(n) operations)
        if any(pattern in name for pattern in self.patterns):
            for pattern in self.patterns:
                name = name.replace(pattern, "")
            
        # Final cleanup
        return ' '.join(name.split())

    def process_station_name(self, name):
        """
        Process a station name to return both display name and normalized name
        
        Args:
            name (str): The original station name
            
        Returns:
            tuple: (display_name, normalized_name)
        """
        if not name:
            return "", ""
            
        # Keep original name for display
        display_name = name.strip()
        
        # Get normalized version for matching
        normalized = self.normalize_station_name(name)
        
        return display_name, normalized

    def get_tfl_stations(self, local_station_count):
        """Fetch stations from TfL API using Line endpoint"""
        all_stations = {}  # Dictionary to prevent duplicates
        api_success = False  # Track if we got any successful responses
        min_required_stations = int(local_station_count * self.threshold_percentage)
        
        # Iterate through each mode and its lines
        for mode, lines in self.lines.items():
            for line in lines:
                url = f"{self.base_url}/Line/{line}/StopPoints"
                params = {'app_key': self.api_key} if self.api_key else {}
                
                try:
                    response = requests.get(url, params=params)
                    response.raise_for_status()
                    stations = response.json()
                    
                    # Add each station to our dictionary using normalized name as key
                    for station in stations:
                        station_name = station.get('commonName', '')
                        if station_name and 'lat' in station and 'lon' in station:
                            # Get both display and normalized names
                            display_name, normalized_name = self.process_station_name(station_name)
                            
                            # Store essential data with both names
                            station_data = {
                                'name': display_name,
                                'normalized_name': normalized_name,
                                'lat': station.get('lat'),
                                'lon': station.get('lon'),
                                'child_stations': []
                            }
                            all_stations[normalized_name] = station_data
                            
                            # Also store alternate names if they exist
                            for other_name in station.get('additionalProperties', []):
                                if other_name.get('key') == 'AlternateName':
                                    alt_name = other_name.get('value', '')
                                    if alt_name:
                                        _, alt_normalized = self.process_station_name(alt_name)
                                        # Add as child station
                                        station_data['child_stations'].append({
                                            'name': alt_name.strip(),
                                            'normalized_name': alt_normalized
                                        })
                    api_success = True
                            
                except Exception as e:
                    print(f"Warning: Error fetching {line} line stations: {str(e)}")
        
        stations_list = list(all_stations.values())
        
        # Safety check: If we got too few stations or all API calls failed, return None
        if len(stations_list) < min_required_stations or not api_success:
            print(f"\nError: Retrieved only {len(stations_list)} stations (minimum required: {min_required_stations})")
            print("This might indicate an API issue or network problem.")
            return None
                    
        return stations_list

    def load_local_stations(self):
        """Load our local consolidated stations"""
        try:
            with open(self.stations_file, 'r') as f:
                stations = json.load(f)
                print(f"Loaded {len(stations)} stations from local file")
                return stations
        except FileNotFoundError:
            print(f"Error: No local stations file found ({self.stations_file})")
            return None
        except json.JSONDecodeError:
            print("Error: Local stations file is corrupted")
            return None

    def backup_stations(self):
        """Create a backup of the current stations file"""
        try:
            backup_name = os.path.join(
                self.backup_dir,
                f'unique_stations_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )
            shutil.copy2(self.stations_file, backup_name)
            print(f"\nCreated backup: {backup_name}")
            return backup_name
        except Exception as e:
            print(f"Warning: Failed to create backup: {str(e)}")
            return None

    def restore_from_backup(self, backup_file):
        """Restore stations from a backup file"""
        try:
            shutil.copy2(backup_file, self.stations_file)
            print(f"Successfully restored from backup: {backup_file}")
            return True
        except Exception as e:
            print(f"Error restoring from backup: {str(e)}")
            return False

    def get_latest_backup(self):
        """Find the most recent backup file"""
        backups = [f for f in os.listdir(self.backup_dir) if f.startswith('unique_stations_backup_')]
        if backups:
            return os.path.join(self.backup_dir, max(backups))  # Most recent backup by filename
        return None

    def find_matching_station(self, station_name, stations_list):
        """Find matching station in a list using normalized names and fuzzy matching"""
        best_match = None
        close_matches = []  # Track stations that are close but below threshold
        child_matches = []  # Track potential child station matches
        
        # Normalize the input station name
        normalized_name = self.normalize_station_name(station_name)
        
        # First try exact matching with normalized names
        for station in stations_list:
            normalized_station_name = self.normalize_station_name(station['name'])
            
            # Exact match check
            if normalized_name == normalized_station_name:
                return station
            
            # Calculate fuzzy match ratio
            ratio = fuzz.ratio(normalized_name, normalized_station_name)
            
            # Check for parent station match first
            if ratio > 85:  # Primary match threshold
                best_match = station
            # Only check child stations if parent station is somewhat similar
            elif ratio > 60 and 'child_stations' in station:  # Lower threshold for checking children
                for child in station['child_stations']:
                    child_normalized = self.normalize_station_name(child)
                    child_ratio = fuzz.ratio(normalized_name, child_normalized)
                    if child_ratio > 85:  # Higher threshold for actual match
                        return station  # Return parent station if child matches
                    elif child_ratio > 75:
                        child_matches.append((station['name'], child, child_ratio))
            # Track close but not quite matches
            elif ratio > 75:
                close_matches.append((station['name'], normalized_station_name, ratio))
                
        # If we found a best match, return it
        if best_match:
            return best_match
                
        # If we have close matches but no best match, report them
        if close_matches or child_matches:
            print(f"\nNote: Found close matches for '{station_name}' (normalized: '{normalized_name}') but below threshold:")
            
            # Show regular close matches
            for name, norm_name, ratio in sorted(close_matches, key=lambda x: x[2], reverse=True)[:10]:
                print(f"  - {name} (normalized: '{norm_name}', similarity: {ratio}%)")
            
            # Show child station matches if any
            if child_matches:
                print("\n  Potential child station matches:")
                for parent, child, ratio in sorted(child_matches, key=lambda x: x[2], reverse=True):
                    print(f"  - Child: {child} of Parent: {parent} (similarity: {ratio}%)")
                
        return None

    def sync_stations(self):
        """Main sync function that checks for new or removed stations"""
        print("Starting station sync...")
        
        # Load our local stations
        local_stations = self.load_local_stations()
        if not local_stations:
            print("Error: Cannot proceed without valid local stations data")
            return False
            
        # Get TfL stations
        tfl_stations = self.get_tfl_stations(len(local_stations))
        if not tfl_stations:
            print("Error: Cannot proceed with potentially incomplete TfL data")
            return False
        
        # Track changes
        changes_found = False
        new_stations = []
        removed_stations = []
        
        # Check for new stations (in TfL but not in local)
        for tfl_station in tfl_stations:
            if not self.find_matching_station(tfl_station['name'], local_stations):
                new_stations.append(tfl_station)
                changes_found = True
        
        # Check for removed stations (in local but not in TfL)
        for local_station in local_stations:
            if not self.find_matching_station(local_station['name'], tfl_stations):
                removed_stations.append(local_station)
                changes_found = True
        
        if changes_found:
            # Create backup before proceeding
            backup_file = self.backup_stations()
            if not backup_file:
                print("Error: Cannot proceed without creating backup")
                return False

            # Show and process changes
            accepted_changes = self.process_changes(new_stations, removed_stations, tfl_stations, local_stations)
            
            if accepted_changes:
                # Apply accepted changes
                updated_stations = [s for s in local_stations if s not in accepted_changes['removed']]
                updated_stations.extend(accepted_changes['added'])
                
                # Save updated stations
                with open(self.stations_file, 'w') as f:
                    json.dump(updated_stations, f, indent=2)
                print("\nAccepted changes have been applied successfully!")
                
                # Offer restore option
                while True:
                    restore = input("\nWould you like to restore from the last backup? (yes/no): ").lower()
                    if restore == 'yes':
                        if self.restore_from_backup(backup_file):
                            print("Restored to previous version")
                        break
                    elif restore == 'no':
                        print("Changes have been kept")
                        break
                    else:
                        print("Please enter 'yes' or 'no'")
            else:
                print("\nNo changes were applied")
                return False
        else:
            print("\nNo changes needed. Local stations are up to date.")
            
        # Save sync timestamp
        with open(self.last_sync_file, 'w') as f:
            f.write(datetime.now().isoformat())
            
        return changes_found

    def process_changes(self, new_stations, removed_stations, tfl_stations, local_stations):
        """Process changes with individual selection"""
        accepted_changes = {'added': [], 'removed': []}
        
        while True:
            print("\nProposed changes:")
            
            if new_stations:
                print("\nNew stations to add:")
                for i, station in enumerate(new_stations, 1):
                    print(f"{i}. + {station['name']}")
                    
            if removed_stations:
                print("\nStations to remove:")
                for i, station in enumerate(removed_stations, 1):
                    print(f"{i}. - {station['name']}")
            
            response = input("\nOptions:\n1. View details\n2. Accept all changes\n3. Select individual changes\n4. Skip all changes\nChoice (1-4): ")
            
            if response == '1':
                self.show_detailed_changes(new_stations, removed_stations, tfl_stations)
            elif response == '2':
                accepted_changes['added'] = new_stations
                accepted_changes['removed'] = removed_stations
                break
            elif response == '3':
                # Process additions
                if new_stations:
                    print("\nSelect new stations to add (comma-separated numbers, or 'all'/'none'):")
                    selection = input("> ").lower()
                    if selection == 'all':
                        accepted_changes['added'] = new_stations
                    elif selection != 'none':
                        try:
                            indices = [int(i) - 1 for i in selection.split(',')]
                            accepted_changes['added'] = [new_stations[i] for i in indices if 0 <= i < len(new_stations)]
                        except ValueError:
                            print("Invalid selection, skipping additions")
                
                # Process removals
                if removed_stations:
                    print("\nSelect stations to remove (comma-separated numbers, or 'all'/'none'):")
                    selection = input("> ").lower()
                    if selection == 'all':
                        accepted_changes['removed'] = removed_stations
                    elif selection != 'none':
                        try:
                            indices = [int(i) - 1 for i in selection.split(',')]
                            accepted_changes['removed'] = [removed_stations[i] for i in indices if 0 <= i < len(removed_stations)]
                        except ValueError:
                            print("Invalid selection, skipping removals")
                break
            elif response == '4':
                return None
            else:
                print("Invalid choice, please try again")
        
        return accepted_changes if (accepted_changes['added'] or accepted_changes['removed']) else None

    def show_detailed_changes(self, new_stations, removed_stations, tfl_stations):
        """Show detailed information about proposed changes"""
        print("\nDetailed Changes Report:")
        
        if new_stations:
            print("\nNew Stations Details:")
            for i, station in enumerate(new_stations, 1):
                print(f"\n{i}. + {station['name']}")
                print(f"   Location: {station['lat']}, {station['lon']}")
        
        if removed_stations:
            print("\nRemoved Stations Details:")
            for i, station in enumerate(removed_stations, 1):
                print(f"\n{i}. - {station['name']}")
                # Show any close matches that might indicate a name change
                close_matches = []
                for tfl_station in tfl_stations:
                    ratio = fuzz.ratio(station['name'].lower(), tfl_station['name'].lower())
                    if 75 <= ratio <= 85:
                        close_matches.append((tfl_station['name'], ratio))
                if close_matches:
                    print("   Possible matches in TfL data:")
                    for match_name, ratio in close_matches:
                        print(f"     * {match_name} (similarity: {ratio}%)")

    def get_last_sync_time(self):
        """Get the timestamp of the last successful sync"""
        try:
            with open(self.last_sync_file, 'r') as f:
                return datetime.fromisoformat(f.read().strip())
        except FileNotFoundError:
            return None

def main():
    syncer = StationSync()
    
    # Get last sync time
    last_sync = syncer.get_last_sync_time()
    if last_sync:
        print(f"Last sync was performed at: {last_sync}")
    else:
        print("No previous sync found")
    
    # Perform sync
    if syncer.sync_stations():
        print("\nSync process completed.")
    else:
        print("\nSync process completed with no changes applied.")

if __name__ == "__main__":
    main() 