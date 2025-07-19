@echo off
REM Secure IMDB Migration Runner Script for Windows
REM This script helps you run the migration without exposing credentials

echo ==============================
echo IMDB Migration Tool
echo ==============================
echo.

REM Check if using local CSV files
if "%1"=="--use-local-csv" (
    echo Using local CSV files mode - skipping source account credentials
    echo.
) else (
    REM Get source credentials
    set /p IMDB_SOURCE_EMAIL=Enter source account email: 
    set /p IMDB_SOURCE_PASSWORD=Enter source account password: 
)

REM Get destination credentials
set /p IMDB_DEST_EMAIL=Enter destination account email: 
set /p IMDB_DEST_PASSWORD=Enter destination account password: 
echo.

REM Run the migration with all arguments
echo Starting migration...
python imdb_migrate.py %*

REM Clear credentials from environment
set IMDB_SOURCE_EMAIL=
set IMDB_SOURCE_PASSWORD=
set IMDB_DEST_EMAIL=
set IMDB_DEST_PASSWORD=

echo.
echo Credentials cleared from memory.