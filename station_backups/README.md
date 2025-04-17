# Station Backups

This directory contains backup files of station data, created automatically during synchronization operations.

## Purpose

- Provides version history of station data changes
- Allows rollback to previous versions if needed
- Maintains data safety during updates

## Backup Format

Backup files are named with timestamps:
`unique_stations_backup_YYYYMMDD_HHMMSS.json`

Example: `unique_stations_backup_20240315_143022.json`

## Usage

Backups are automatically created by:
- `sync_stations.py` before updating station data
- Manual backup operations

To restore from a backup, use the restore function in `sync_stations.py` 