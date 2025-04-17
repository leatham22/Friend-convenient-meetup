# Local Data Scripts

This directory contains scripts for managing and processing local station data.

## Scripts

- `sync_stations.py`: Main script for synchronizing station data with TfL API
- `slim_stations.py`: Creates optimized versions of station data files
- `collect_initial_stations.py`: Initial data collection script for new deployments

## Usage

These scripts handle the core data management functionality:
1. Collecting station data from TfL API
2. Processing and optimizing the data
3. Managing backups and synchronization

### Prerequisites
- Python 3.x
- TfL API key (set in `.env` file)
- Required Python packages from `requirements.txt` 