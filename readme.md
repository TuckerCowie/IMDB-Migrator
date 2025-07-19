# IMDB Account Migration Tool

A Python automation tool to migrate ratings and watchlists between IMDB accounts. Features secure credential handling and fully automated export/import capabilities.

## Features

- 🚀 **Fully Automated**: Handles login, export, and import automatically
- 🔐 **Secure**: Never stores credentials in files
- 📊 **Complete Migration**: Transfers both ratings and watchlists
- 🎯 **Flexible**: Options for partial migration or using existing exports
- 🖥️ **Cross-Platform**: Works on Windows, Mac, and Linux

## Prerequisites

- Python 3.7 or higher
- Google Chrome browser
- Two IMDB accounts (source and destination)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/tuckercowie/imdb-migration.git
   cd imdb-migration
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Quick Start (Interactive Mode)

The simplest way to use the tool - it will prompt for credentials:

```bash
python imdb_migrate.py
```

### Using Environment Variables (Recommended)

Set your credentials as environment variables:

```bash
# Mac/Linux
export IMDB_SOURCE_EMAIL="source@email.com"
export IMDB_SOURCE_PASSWORD="your_password"
export IMDB_DEST_EMAIL="dest@email.com"
export IMDB_DEST_PASSWORD="your_password"

python imdb_migrate.py
```

### Using the Secure Runner Scripts

For maximum security, use the provided runner scripts:

```bash
# Mac/Linux
chmod +x run_migration.sh
./run_migration.sh

# Windows
run_migration.bat
```

### Command Line Options

```bash
# Use existing CSV files (skip export phase)
python imdb_migrate.py --use-local-csv

# Migrate only ratings
python imdb_migrate.py --ratings-only

# Migrate only watchlist
python imdb_migrate.py --watchlist-only

# Run without visible browser
python imdb_migrate.py --headless

# Combine options
python imdb_migrate.py --use-local-csv --watchlist-only
```

## How It Works

1. **Export Phase**: Logs into your source account and downloads ratings/watchlist as CSV
2. **Import Phase**: Logs into destination account and recreates all ratings/watchlist items
3. **Verification**: Provides summary of successful migrations

## File Structure

```
imdb-migration/
├── imdb_migrate.py        # Main migration script
├── run_migration.sh       # Mac/Linux secure runner
├── run_migration.bat      # Windows secure runner
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variable template
├── .gitignore           # Git ignore file
├── README.md            # This file
└── imdb_exports/        # Created automatically for CSV exports
```

## Security

- Credentials are never stored in files
- Passwords are hidden during input
- Environment variables are cleared after use
- No sensitive data in git history

## Troubleshooting

### Common Issues

1. **Login fails**: Check credentials and solve any CAPTCHA manually
2. **Export fails**: Ensure source account has data to export
3. **Rate limiting**: Script includes delays, but increase if needed
4. **Missing Chrome driver**: webdriver-manager handles this automatically

### Tips

- Run without `--headless` to see what's happening
- Exported CSVs are saved in `imdb_exports/` directory
- Use `--use-local-csv` if automated export fails
- Some regional content may not transfer between accounts

## Contributing

Feel free to submit issues and enhancement requests!

## Disclaimer

This tool is for personal use only. Please respect IMDB's terms of service and use responsibly.

## License

MIT License - see LICENSE file for details