#!/bin/bash
# Secure IMDB Migration Runner Script
# This script helps you run the migration without exposing credentials

echo "=============================="
echo "IMDB Migration Tool"
echo "=============================="
echo

# Check if using local CSV files
if [[ "$1" == "--use-local-csv" ]]; then
    echo "Using local CSV files mode - skipping source account credentials"
    echo
else
    # Get source credentials
    read -p "Enter source account email: " SOURCE_EMAIL
    read -s -p "Enter source account password: " SOURCE_PASSWORD
    echo
    export IMDB_SOURCE_EMAIL="$SOURCE_EMAIL"
    export IMDB_SOURCE_PASSWORD="$SOURCE_PASSWORD"
fi

# Get destination credentials
read -p "Enter destination account email: " DEST_EMAIL
read -s -p "Enter destination account password: " DEST_PASSWORD
echo
echo

export IMDB_DEST_EMAIL="$DEST_EMAIL"
export IMDB_DEST_PASSWORD="$DEST_PASSWORD"

# Run the migration with all arguments passed through
echo "Starting migration..."
python imdb_migrate.py "$@"

# Clear credentials from environment
unset IMDB_SOURCE_EMAIL
unset IMDB_SOURCE_PASSWORD
unset IMDB_DEST_EMAIL
unset IMDB_DEST_PASSWORD

echo
echo "Credentials cleared from memory."