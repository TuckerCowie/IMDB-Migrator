#!/usr/bin/env python3
"""
IMDB Ratings and Watchlist Migration Script
Fully automated migration from one IMDB account to another
"""

import pandas as pd
import time
import os
import argparse
import glob
import getpass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# File paths
RATINGS_FILE = "ratings.csv"
WATCHLIST_FILE = "watchlist.csv"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "imdb_exports")

# Delays (in seconds) - Increase if you get rate limited
DELAY_BETWEEN_ACTIONS = 2
DELAY_BETWEEN_MOVIES = 3

class IMDBMigrator:
    def __init__(self, headless=False, download_dir=DOWNLOAD_DIR):
        """Initialize the Chrome driver with download settings"""
        # Create download directory if it doesn't exist
        os.makedirs(download_dir, exist_ok=True)
        self.download_dir = download_dir
        
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Configure download settings
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 10)
        
        # Enable file downloads in headless mode
        if headless:
            self.driver.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')
            params = {'cmd': 'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': download_dir}}
            self.driver.execute("send_command", params)
    
    def login(self, email, password):
        """Log into IMDB account"""
        logger.info(f"Logging into IMDB account: {email[:3]}***")
        
        try:
            # Go to IMDB
            self.driver.get("https://www.imdb.com")
            time.sleep(2)
            
            # Click Sign In
            sign_in = self.wait.until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Sign In"))
            )
            sign_in.click()
            time.sleep(1)
            
            # Click "Sign in with IMDb"
            imdb_signin = self.wait.until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Sign in with IMDb"))
            )
            imdb_signin.click()
            
            # Enter credentials
            email_input = self.wait.until(
                EC.presence_of_element_located((By.ID, "ap_email"))
            )
            email_input.send_keys(email)
            
            password_input = self.driver.find_element(By.ID, "ap_password")
            password_input.send_keys(password)
            
            # Click sign in button
            signin_button = self.driver.find_element(By.ID, "signInSubmit")
            signin_button.click()
            
            # Wait for login to complete
            time.sleep(5)
            
            # Check if login successful by looking for user menu
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "navbar__user"))
                )
                logger.info("Login successful!")
                return True
            except TimeoutException:
                logger.error("Login failed - please check credentials or solve CAPTCHA if present")
                return False
                
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return False
    
    def logout(self):
        """Log out of current IMDB account"""
        logger.info("Logging out of current account...")
        try:
            # Go to IMDB homepage
            self.driver.get("https://www.imdb.com")
            time.sleep(2)
            
            # Click on user menu
            user_menu = self.wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "navbar__user"))
            )
            user_menu.click()
            time.sleep(1)
            
            # Click sign out
            signout = self.wait.until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Sign out"))
            )
            signout.click()
            time.sleep(3)
            
            logger.info("Logged out successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
            return False
    
    def wait_for_download(self, filename_pattern, timeout=30):
        """Wait for a file to be downloaded"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            files = glob.glob(os.path.join(self.download_dir, filename_pattern))
            if files:
                # Wait a bit more to ensure download is complete
                time.sleep(2)
                return files[0]
            time.sleep(1)
        return None
    
    def export_ratings(self):
        """Export ratings from current account"""
        logger.info("Exporting ratings...")
        try:
            # Clear any existing ratings export
            for f in glob.glob(os.path.join(self.download_dir, "ratings*.csv")):
                os.remove(f)
            
            # Navigate to ratings
            self.driver.get("https://www.imdb.com/list/ratings")
            time.sleep(3)
            
            # Check if user has any ratings
            try:
                no_ratings = self.driver.find_element(By.XPATH, "//*[contains(text(), 'You have not rated any titles')]")
                logger.warning("No ratings found in source account")
                return None
            except NoSuchElementException:
                pass  # Ratings exist, continue
            
            # Click the three dots menu
            menu_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='List page options']"))
            )
            menu_button.click()
            time.sleep(1)
            
            # Click Export
            export_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Export']"))
            )
            export_button.click()
            
            # Wait for download
            downloaded_file = self.wait_for_download("ratings*.csv")
            if downloaded_file:
                # Rename to standard name
                new_path = os.path.join(self.download_dir, RATINGS_FILE)
                os.rename(downloaded_file, new_path)
                logger.info(f"✓ Ratings exported successfully to {new_path}")
                return new_path
            else:
                logger.error("Failed to download ratings file")
                return None
                
        except Exception as e:
            logger.error(f"Error exporting ratings: {str(e)}")
            return None
    
    def export_watchlist(self):
        """Export watchlist from current account"""
        logger.info("Exporting watchlist...")
        try:
            # Clear any existing watchlist export
            for f in glob.glob(os.path.join(self.download_dir, "watchlist*.csv")):
                os.remove(f)
            
            # Navigate to watchlist
            self.driver.get("https://www.imdb.com/list/watchlist")
            time.sleep(3)
            
            # Check if user has any items in watchlist
            try:
                empty_watchlist = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Your Watchlist is empty')]")
                logger.warning("No items found in watchlist")
                return None
            except NoSuchElementException:
                pass  # Watchlist has items, continue
            
            # Click the three dots menu
            menu_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='List page options']"))
            )
            menu_button.click()
            time.sleep(1)
            
            # Click Export
            export_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Export']"))
            )
            export_button.click()
            
            # Wait for download
            downloaded_file = self.wait_for_download("watchlist*.csv")
            if downloaded_file:
                # Rename to standard name
                new_path = os.path.join(self.download_dir, WATCHLIST_FILE)
                os.rename(downloaded_file, new_path)
                logger.info(f"✓ Watchlist exported successfully to {new_path}")
                return new_path
            else:
                logger.error("Failed to download watchlist file")
                return None
                
        except Exception as e:
            logger.error(f"Error exporting watchlist: {str(e)}")
            return None
    
    def rate_movie(self, imdb_id, rating):
        """Rate a movie/show by its IMDB ID"""
        try:
            # Go directly to the title page
            self.driver.get(f"https://www.imdb.com/title/{imdb_id}/")
            time.sleep(DELAY_BETWEEN_ACTIONS)
            
            # Find and click the star rating button
            try:
                # Look for the rating widget
                rating_button = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='hero-rating-bar__user-rating__score']"))
                )
                rating_button.click()
                time.sleep(1)
                
                # Select the appropriate star
                star_selector = f"button[aria-label='Rate {int(rating)}']"
                star = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, star_selector))
                )
                star.click()
                
                logger.info(f"✓ Rated {imdb_id} with {rating} stars")
                return True
                
            except TimeoutException:
                # Try alternative method
                logger.warning(f"Could not find rating widget for {imdb_id}, trying alternative method")
                return False
                
        except Exception as e:
            logger.error(f"Error rating {imdb_id}: {str(e)}")
            return False
    
    def add_to_watchlist(self, imdb_id):
        """Add a movie/show to watchlist by its IMDB ID"""
        try:
            # Go directly to the title page
            self.driver.get(f"https://www.imdb.com/title/{imdb_id}/")
            time.sleep(DELAY_BETWEEN_ACTIONS)
            
            # Find and click the watchlist button
            try:
                # Look for watchlist button
                watchlist_button = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='hero-rating-bar__watchlist-button']"))
                )
                
                # Check if already in watchlist
                button_text = watchlist_button.text
                if "In Watchlist" in button_text:
                    logger.info(f"⏭️  {imdb_id} already in watchlist")
                    return True
                
                watchlist_button.click()
                logger.info(f"✓ Added {imdb_id} to watchlist")
                return True
                
            except TimeoutException:
                logger.warning(f"Could not find watchlist button for {imdb_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding {imdb_id} to watchlist: {str(e)}")
            return False
    
    def migrate_ratings(self, ratings_file):
        """Migrate all ratings from CSV file"""
        logger.info(f"\n{'='*50}")
        logger.info("Starting ratings migration...")
        logger.info(f"{'='*50}\n")
        
        try:
            # Read ratings CSV
            df = pd.read_csv(ratings_file)
            total = len(df)
            success = 0
            
            for idx, row in df.iterrows():
                imdb_id = row['Const']
                rating = row['Your Rating']
                title = row.get('Title', imdb_id)
                
                logger.info(f"\n[{idx+1}/{total}] Processing: {title}")
                
                if self.rate_movie(imdb_id, rating):
                    success += 1
                
                time.sleep(DELAY_BETWEEN_MOVIES)
            
            logger.info(f"\n{'='*50}")
            logger.info(f"Ratings migration complete: {success}/{total} successful")
            logger.info(f"{'='*50}\n")
            
        except Exception as e:
            logger.error(f"Error reading ratings file: {str(e)}")
    
    def migrate_watchlist(self, watchlist_file):
        """Migrate all watchlist items from CSV file"""
        logger.info(f"\n{'='*50}")
        logger.info("Starting watchlist migration...")
        logger.info(f"{'='*50}\n")
        
        try:
            # Read watchlist CSV
            df = pd.read_csv(watchlist_file)
            total = len(df)
            success = 0
            
            for idx, row in df.iterrows():
                imdb_id = row['Const']
                title = row.get('Title', imdb_id)
                
                logger.info(f"\n[{idx+1}/{total}] Processing: {title}")
                
                if self.add_to_watchlist(imdb_id):
                    success += 1
                
                time.sleep(DELAY_BETWEEN_MOVIES)
            
            logger.info(f"\n{'='*50}")
            logger.info(f"Watchlist migration complete: {success}/{total} successful")
            logger.info(f"{'='*50}\n")
            
        except Exception as e:
            logger.error(f"Error reading watchlist file: {str(e)}")
    
    def close(self):
        """Close the browser"""
        self.driver.quit()

def get_credentials(args):
    """Get credentials from environment variables, command line, or interactive prompt"""
    credentials = {}
    
    # Try environment variables first
    credentials['source_email'] = os.environ.get('IMDB_SOURCE_EMAIL', args.source_email)
    credentials['source_password'] = os.environ.get('IMDB_SOURCE_PASSWORD', args.source_password)
    credentials['dest_email'] = os.environ.get('IMDB_DEST_EMAIL', args.dest_email)
    credentials['dest_password'] = os.environ.get('IMDB_DEST_PASSWORD', args.dest_password)
    
    # Interactive prompts for missing credentials
    if not args.use_local_csv:
        if not credentials['source_email']:
            credentials['source_email'] = input("Enter source account email: ").strip()
        if not credentials['source_password']:
            credentials['source_password'] = getpass.getpass("Enter source account password: ")
    
    if not credentials['dest_email']:
        credentials['dest_email'] = input("Enter destination account email: ").strip()
    if not credentials['dest_password']:
        credentials['dest_password'] = getpass.getpass("Enter destination account password: ")
    
    # Validate we have what we need
    if not args.use_local_csv:
        if not credentials['source_email'] or not credentials['source_password']:
            logger.error("Source account credentials are required for automated export")
            return None
    
    if not credentials['dest_email'] or not credentials['dest_password']:
        logger.error("Destination account credentials are required")
        return None
    
    return credentials

def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(
        description='IMDB Account Migration Tool',
        epilog='Credentials can be provided via environment variables (IMDB_SOURCE_EMAIL, etc.) or will be prompted interactively.'
    )
    
    # Credential arguments (optional - not recommended for passwords)
    parser.add_argument('--source-email', help='Source account email (or use IMDB_SOURCE_EMAIL env var)')
    parser.add_argument('--source-password', help='Source account password (NOT RECOMMENDED - use env var or prompt)')
    parser.add_argument('--dest-email', help='Destination account email (or use IMDB_DEST_EMAIL env var)')
    parser.add_argument('--dest-password', help='Destination account password (NOT RECOMMENDED - use env var or prompt)')
    
    # Other arguments
    parser.add_argument('--use-local-csv', action='store_true', 
                       help='Skip automated export and use local CSV files')
    parser.add_argument('--headless', action='store_true',
                       help='Run browser in headless mode (no visible window)')
    parser.add_argument('--ratings-only', action='store_true',
                       help='Migrate ratings only')
    parser.add_argument('--watchlist-only', action='store_true',
                       help='Migrate watchlist only')
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("IMDB ACCOUNT MIGRATION TOOL")
    print("="*60 + "\n")
    
    # Get credentials securely
    credentials = get_credentials(args)
    if not credentials:
        sys.exit(1)
    
    # Initialize migrator
    print("\nInitializing browser driver...")
    migrator = IMDBMigrator(headless=args.headless)
    
    try:
        ratings_file = None
        watchlist_file = None
        
        # Phase 1: Export from source account (if not using local files)
        if not args.use_local_csv:
            print(f"\n{'='*60}")
            print("PHASE 1: EXPORTING FROM SOURCE ACCOUNT")
            print(f"{'='*60}\n")
            
            # Login to source account
            if not migrator.login(credentials['source_email'], credentials['source_password']):
                print("Failed to login to source account. Please check credentials.")
                sys.exit(1)
            
            # Export data based on user preference
            if not args.watchlist_only:
                ratings_file = migrator.export_ratings()
            
            if not args.ratings_only:
                watchlist_file = migrator.export_watchlist()
            
            # Logout from source account
            migrator.logout()
            time.sleep(3)
            
        else:
            # Use local files
            print("Using local CSV files...")
            if not args.watchlist_only and os.path.exists(RATINGS_FILE):
                ratings_file = RATINGS_FILE
                print(f"Found local ratings file: {ratings_file}")
            if not args.ratings_only and os.path.exists(WATCHLIST_FILE):
                watchlist_file = WATCHLIST_FILE
                print(f"Found local watchlist file: {watchlist_file}")
        
        # Phase 2: Import to destination account
        print(f"\n{'='*60}")
        print("PHASE 2: IMPORTING TO DESTINATION ACCOUNT")
        print(f"{'='*60}\n")
        
        # Login to destination account
        if not migrator.login(credentials['dest_email'], credentials['dest_password']):
            print("Failed to login to destination account. Please check credentials.")
            sys.exit(1)
        
        # Migrate data
        if ratings_file and not args.watchlist_only:
            migrator.migrate_ratings(ratings_file)
        elif not ratings_file and not args.watchlist_only:
            print("No ratings file available to migrate")
        
        if watchlist_file and not args.ratings_only:
            migrator.migrate_watchlist(watchlist_file)
        elif not watchlist_file and not args.ratings_only:
            print("No watchlist file available to migrate")
        
        print("\n" + "="*60)
        print("MIGRATION COMPLETE!")
        print("Please check your destination account to verify.")
        print(f"Exported files are saved in: {migrator.download_dir}")
        print("="*60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user.")
    except Exception as e:
        print(f"\n\nUnexpected error: {str(e)}")
    finally:
        migrator.close()

if __name__ == "__main__":
    main()