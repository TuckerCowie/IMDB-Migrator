# IMDB Migration Script - Custom CSV Usage Examples

The IMDB migration script now supports using your own CSV files, allowing you to skip the export phase entirely.

## Basic Usage Examples

### 1. Full Migration (Export + Import)
```bash
python imdb_migration_script.py
```
This will:
- Login to source account
- Export ratings and watchlist
- Login to destination account  
- Import all data

### 2. Use Local CSV Files (ratings.csv and watchlist.csv)
```bash
python imdb_migration_script.py --use-local-csv
```
This will:
- Skip source account login and export
- Use existing `ratings.csv` and `watchlist.csv` files
- Login to destination account
- Import all data

### 3. Use Custom CSV File Paths
```bash
python imdb_migration_script.py --ratings-file /path/to/my_ratings.csv --watchlist-file /path/to/my_watchlist.csv
```
This will:
- Skip source account login and export
- Use your specified CSV files
- Login to destination account
- Import all data

### 4. Migrate Only Ratings with Custom File
```bash
python imdb_migration_script.py --ratings-file my_ratings.csv --ratings-only
```

### 5. Migrate Only Watchlist with Custom File
```bash
python imdb_migration_script.py --watchlist-file my_watchlist.csv --watchlist-only
```

## CSV File Format Requirements

### Ratings CSV Format
Your ratings CSV file must contain these columns:
- `Const` - IMDB ID (e.g., "tt0111161")
- `Your Rating` - Your rating (1-10)

Example:
```csv
Const,Your Rating,Title,Year
tt0111161,9,The Shawshank Redemption,1994
tt0068646,8,The Godfather,1972
```

### Watchlist CSV Format
Your watchlist CSV file must contain:
- `Const` - IMDB ID (e.g., "tt0111161")

Example:
```csv
Const,Title,Year
tt0111161,The Shawshank Redemption,1994
tt0068646,The Godfather,1972
```

## Environment Variables

You can set credentials via environment variables:
```bash
export IMDB_DEST_EMAIL="your-email@example.com"
export IMDB_DEST_PASSWORD="your-password"
python imdb_migration_script.py --ratings-file my_ratings.csv
```

## Headless Mode

Run without visible browser window:
```bash
python imdb_migration_script.py --ratings-file my_ratings.csv --headless
```

## Error Handling

The script will validate your CSV files and provide clear error messages if:
- Files don't exist
- Files are empty
- Required columns are missing
- Files contain no data
- Files can't be read due to format issues 