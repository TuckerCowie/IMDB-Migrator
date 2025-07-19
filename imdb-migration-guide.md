# IMDB Ratings & Watchlist Migration Guide

## Overview
This guide will help you migrate your ratings and watchlist from one IMDB account to another using a fully automated Python script.

## Key Features
- **Fully Automated**: Logs into both accounts and handles export/import automatically
- **Secure Credentials**: Never stores passwords in files - uses environment variables or prompts
- **Flexible Options**: Can use local CSV files or automated export
- **Progress Tracking**: Real-time updates on migration status
- **Cross-Platform**: Works on Windows, Mac, and Linux

## Prerequisites
- Python 3.7 or higher installed on your computer
- Both IMDB account credentials
- Google Chrome browser

## Quick Usage Examples

```bash
# Full automated migration (recommended)
python imdb_migrate.py

# Use existing CSV files (skip export)
python imdb_migrate.py --use-local-csv

# Migrate only ratings
python imdb_migrate.py --ratings-only

# Migrate only watchlist
python imdb_migrate.py --watchlist-only

# Run without visible browser window
python imdb_migrate.py --headless

# Combine options
python imdb_migrate.py --use-local-csv --watchlist-only
```

## Step 1: Set Up Your Credentials

You have three secure options for providing credentials:

### Option 1: Environment Variables (Recommended)
Set environment variables before running the script:

**Mac/Linux:**
```bash
export IMDB_SOURCE_EMAIL="your.source@email.com"
export IMDB_SOURCE_PASSWORD="your_source_password"
export IMDB_DEST_EMAIL="your.destination@email.com"
export IMDB_DEST_PASSWORD="your_destination_password"

python imdb_migrate.py
```

**Windows (Command Prompt):**
```cmd
set IMDB_SOURCE_EMAIL=your.source@email.com
set IMDB_SOURCE_PASSWORD=your_source_password
set IMDB_DEST_EMAIL=your.destination@email.com
set IMDB_DEST_PASSWORD=your_destination_password

python imdb_migrate.py
```

**Windows (PowerShell):**
```powershell
$env:IMDB_SOURCE_EMAIL="your.source@email.com"
$env:IMDB_SOURCE_PASSWORD="your_source_password"
$env:IMDB_DEST_EMAIL="your.destination@email.com"
$env:IMDB_DEST_PASSWORD="your_destination_password"

python imdb_migrate.py
```

### Option 2: Interactive Prompts (Secure)
Simply run the script and it will prompt you for any missing credentials:
```bash
python imdb_migrate.py
```
Passwords will be hidden as you type them.

### Option 3: Command Line Arguments (Less Secure)
⚠️ **Warning**: This method may expose passwords in your shell history or process list.
```bash
python imdb_migrate.py --source-email "email@example.com" --dest-email "other@example.com"
```
### Option 4: Use the Secure Runner Script
We've included helper scripts that handle credentials securely:

**Mac/Linux:**
```bash
chmod +x run_migration.sh
./run_migration.sh
```

**Windows:**
```cmd
run_migration.bat
```

**Optional - Using .env file:**
If you prefer using a `.env` file:
1. Copy `.env.example` to `.env`
2. Fill in your credentials
3. Install python-dotenv: `pip install python-dotenv`
4. Add this to the top of `imdb_migrate.py`:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

## Step 2: Set Up the Migration Tool

1. **Install required Python packages:**
   Open Terminal (Mac/Linux) or Command Prompt (Windows) and run:
   ```bash
   pip install selenium pandas webdriver-manager
   ```

2. **Create a new folder** for this project

3. **Save the migration script:**
   Save the provided `imdb_migrate.py` file in your project folder

## Step 3: Run the Full Automated Migration

1. **Log out of IMDB in your browser** (the script handles all logins)

2. **Run the script (fully automated):**
   ```bash
   python imdb_migrate.py
   ```

   The script will automatically:
   - Log into your source account
   - Export your ratings and watchlist
   - Log out of source account
   - Log into your destination account
   - Import all your data

3. **Optional command line arguments:**
   ```bash
   # Use existing local CSV files (skip export phase)
   python imdb_migrate.py --use-local-csv
   
   # Migrate ratings only
   python imdb_migrate.py --ratings-only
   
   # Migrate watchlist only
   python imdb_migrate.py --watchlist-only
   
   # Run in headless mode (no visible browser)
   python imdb_migrate.py --headless
   
   # Combine options
   python imdb_migrate.py --use-local-csv --ratings-only
   ```

4. **Monitor the progress:**
   - A Chrome browser window will open (unless using --headless)
   - Watch as it automatically navigates through both accounts
   - Progress messages appear in the terminal
   - Exported CSVs are saved to an `imdb_exports` folder

## Step 4: Verify the Migration

1. Once complete, log into your destination IMDB account
2. Check your ratings: https://www.imdb.com/list/ratings
3. Check your watchlist: https://www.imdb.com/list/watchlist

## Troubleshooting

### Common Issues:

1. **"Chrome driver not found" error:**
   - The webdriver-manager should handle this automatically
   - If issues persist, manually download ChromeDriver from https://chromedriver.chromium.org/

2. **Login fails:**
   - Check your credentials (all 4 must be correct)
   - IMDB might have CAPTCHA - the browser window will pause for you to solve it manually
   - Try running without `--headless` to see what's happening

3. **Export fails:**
   - Ensure your source account has ratings/watchlist items
   - Check that the download directory has write permissions
   - Try manual export with `--use-local-csv` option

4. **Ratings not appearing:**
   - IMDB may take a few minutes to update
   - Check if you're logged into the correct destination account
   - Some titles might not be available in all regions

5. **Script runs too fast:**
   - Increase the sleep times in the script
   - IMDB has rate limiting - the script includes delays to prevent this

6. **"File not found" errors:**
   - When using `--use-local-csv`, ensure files are named exactly `ratings.csv` and `watchlist.csv`
   - Check that files are in the same directory as the script

### Safety Tips:
- Never hardcode credentials in the script
- Use environment variables or interactive prompts
- Clear your shell history after using command line arguments
- Consider using the provided runner scripts for added security
- If using a `.env` file (see `.env.example`), never commit it to version control
- Change your passwords after migration if you have any security concerns

## Alternative Method (Manual Export)

If the automated export doesn't work, you can manually export and use the `--use-local-csv` option:

1. **Manually export from source account:**
   - Log into your source IMDB account
   - Go to https://www.imdb.com/list/ratings and export
   - Go to https://www.imdb.com/list/watchlist and export
   - Save files as `ratings.csv` and `watchlist.csv`

2. **Run migration with local files:**
   ```bash
   python imdb_migrate.py --use-local-csv
   ```

3. **Other alternatives:**
   - Use IMDB's list import feature (limited functionality)
   - Browser extensions like "IMDB List Importer" (third-party tools)

## Data Backup

Always keep your exported CSV files as a backup of your IMDB data!