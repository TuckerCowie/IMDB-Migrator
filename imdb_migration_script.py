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
from selenium.webdriver.support.wait import WebDriverWait  # Fixed import per lint
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import sys
from pathlib import Path
from typing import Optional, cast
import ssl
import platform
# Add colorama for colored logs
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    COLOR_ENABLED = True
except ImportError:
    COLOR_ENABLED = False
    class Dummy:
        RESET = RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = ''
        RESET_ALL = ''
    Fore = Style = Dummy()

# .env support
try:
    from dotenv import load_dotenv
    dotenv_loaded = False
    dotenv_path = os.path.join(os.getcwd(), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        dotenv_loaded = True
        print("Loaded environment variables from .env file.")
except ImportError:
    print("python-dotenv not installed. .env file will not be loaded.")

# Homebrew chromedriver usage:
# Assumes chromedriver is installed and available in PATH (e.g., via `brew install chromedriver`)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# File paths
RATINGS_FILE = "ratings.csv"
WATCHLIST_FILE = "watchlist.csv"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "imdb_exports")

# Delays (in seconds) - Increase if you get rate limited
DELAY_BETWEEN_ACTIONS = 2
DELAY_BETWEEN_MOVIES = 3

# Warn if using LibreSSL (can cause issues with webdriver_manager/requests)
if "LibreSSL" in ssl.OPENSSL_VERSION:
    print("WARNING: Your Python is using LibreSSL. Some features (like webdriver_manager) may not work correctly.\n"
          "Consider installing Python via Homebrew to get OpenSSL support.\n"
          "See: https://github.com/SeleniumHQ/selenium/issues/10050\n")

def get_chromedriver_path():
    # 1. Allow override via env var
    env_path = os.environ.get("CHROMEDRIVER_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    # 2. Try common install locations
    system = platform.system()
    if system == "Darwin":  # macOS
        # Homebrew default
        for path in ["/opt/homebrew/bin/chromedriver", "/usr/local/bin/chromedriver"]:
            if os.path.exists(path):
                return path
    elif system == "Windows":
        # Chocolatey or manual install
        for path in [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chromedriver.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chromedriver.exe"),
            r"C:\tools\chromedriver.exe",
            r"C:\chromedriver.exe"
        ]:
            if os.path.exists(path):
                return path
    # 3. Fallback to PATH
    return "chromedriver"

def color_info(msg):
    if COLOR_ENABLED:
        logger.info(Fore.CYAN + msg + Style.RESET_ALL)
    else:
        logger.info(msg)

def color_success(msg):
    if COLOR_ENABLED:
        logger.info(Fore.GREEN + msg + Style.RESET_ALL)
    else:
        logger.info(msg)

def color_warn(msg):
    if COLOR_ENABLED:
        logger.warning(Fore.YELLOW + msg + Style.RESET_ALL)
    else:
        logger.warning(msg)

def color_error(msg):
    if COLOR_ENABLED:
        logger.error(Fore.RED + msg + Style.RESET_ALL)
    else:
        logger.error(msg)

class IMDBMigrator:
    # Default wait times (in seconds)
    DEFAULT_WAIT = 4
    FAST_WAIT = 1
    PAGE_LOAD_WAIT = 1  # Used to be 2-3
    ACTION_WAIT = 0.5   # Used to be 1

    def __init__(self, headless: bool = False, download_dir: str = DOWNLOAD_DIR, debug: bool = False, fast_mode: bool = False):
        """Initialize the Chrome driver with improved settings and error handling"""
        self.download_dir = download_dir
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.debug = debug
        self.fast_mode = fast_mode
        try:
            self.setup_driver(headless, download_dir)
        except Exception as e:
            logger.critical(f"Failed to initialize browser driver: {e}")
            raise

    def log(self, msg):
        if self.debug:
            logger.debug(msg)

    def setup_driver(self, headless, download_dir):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        chromedriver_path = get_chromedriver_path()
        try:
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            logger.critical(f"Failed to initialize Chrome driver from {chromedriver_path}: {e}")
            raise
        # Use shorter waits for fast_mode
        wait_time = self.FAST_WAIT if self.fast_mode else self.DEFAULT_WAIT
        self.wait = WebDriverWait(self.driver, wait_time)
        if headless and self.driver is not None:
            self.driver.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')  # type: ignore[attr-defined]
            params = {'cmd': 'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': download_dir}}
            self.driver.execute("send_command", params)

    def _wait_and_click(self, by, value, timeout=10, error_msg=None):
        if self.driver is None:
            logger.error("WebDriver is not initialized.")
            return None
        try:
            elem = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            elem.click()
            return elem
        except Exception as e:
            msg = error_msg or f"Could not click element by {by}='{value}': {e}"
            logger.error(msg)
            if self.debug:
                logger.exception(e)
            return None

    def _wait_for_element(self, by, value, timeout=10, error_msg=None):
        if self.driver is None:
            logger.error("WebDriver is not initialized.")
            return None
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except Exception as e:
            msg = error_msg or f"Element not found by {by}='{value}': {e}"
            logger.error(msg)
            if self.debug:
                logger.exception(e)
            return None

    def login(self, email, password):
        """Log into IMDB account"""
        # Only clear browser cache before login, not during export/import
        self.clear_browser_cache()
        logger.info(f"Logging into IMDB account: {email[:3]}***")
        if self.driver is None:
            logger.error("WebDriver is not initialized.")
            return False
        try:
            self.driver.get("https://www.imdb.com")
            time.sleep(self.PAGE_LOAD_WAIT if not self.fast_mode else self.ACTION_WAIT)
            # Try multiple selectors for the 'Sign In' button
            sign_in_clicked = False
            selectors = [
                (By.LINK_TEXT, "Sign In"),
                (By.XPATH, "//a[contains(@href, 'signin')]"),
                (By.CSS_SELECTOR, "a.ipc-button[href*='signin']"),
                (By.XPATH, "//span[text()='Sign In']/ancestor::a"),
            ]
            for by, value in selectors:
                logger.debug(f"Trying to find Sign In button with {by}='{value}'")
                try:
                    elem = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((by, value))
                    )
                    elem.click()
                    sign_in_clicked = True
                    logger.debug(f"Clicked Sign In button with {by}='{value}'")
                    break
                except Exception as e:
                    logger.debug(f"Failed to click Sign In with {by}='{value}': {e}")
            if not sign_in_clicked:
                logger.error("Sign In button not found with any known selector.")
                return False
            time.sleep(self.ACTION_WAIT)
            # Try multiple selectors for 'Sign in with IMDb'
            imdb_signin_clicked = False
            selectors = [
                (By.LINK_TEXT, "Sign in with IMDb"),
                (By.XPATH, "//span[contains(text(), 'Sign in with IMDb')]/ancestor::a"),
                (By.XPATH, "//a[contains(@href, 'signin') and contains(@href, 'imdb')]"),
                (By.CSS_SELECTOR, "a.list-group-item[href*='signin'][href*='imdb']"),
            ]
            for by, value in selectors:
                logger.debug(f"Trying to find 'Sign in with IMDb' button with {by}='{value}'")
                try:
                    elem = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((by, value))
                    )
                    elem.click()
                    imdb_signin_clicked = True
                    logger.debug(f"Clicked 'Sign in with IMDb' with {by}='{value}'")
                    break
                except Exception as e:
                    logger.debug(f"Failed to click 'Sign in with IMDb' with {by}='{value}': {e}")
            if not imdb_signin_clicked:
                logger.error("'Sign in with IMDb' button not found with any known selector.")
                return False
            # Enter credentials
            email_input = self._wait_for_element(By.ID, "ap_email", error_msg="Email input not found")
            if not email_input: return False
            email_input.send_keys(email)
            password_input = self._wait_for_element(By.ID, "ap_password", error_msg="Password input not found")
            if not password_input: return False
            password_input.send_keys(password)
            if not self._wait_and_click(By.ID, "signInSubmit", error_msg="Sign in submit button not found"): return False
            # Wait for login to complete or CAPTCHA
            captcha_detected = False
            user_menu_selectors = [
                (By.CLASS_NAME, "navbar__user"),
                (By.CSS_SELECTOR, ".ipc-button__text:has(svg[data-testid='user-avatar'])"),
                (By.CSS_SELECTOR, "label[for='navUserMenu']"),
                (By.CSS_SELECTOR, "[data-testid='user-menu-trigger']"),
                (By.CSS_SELECTOR, "button[aria-label*='account']"),
            ]
            for _ in range(15):  # Wait up to ~30 seconds
                time.sleep(2)
                # Check for user menu (successful login)
                for by, value in user_menu_selectors:
                    try:
                        if self.driver.find_elements(by, value):
                            logger.info(f"Login successful! User menu found with {by}='{value}'")
                            return True
                    except Exception as e:
                        logger.debug(f"User menu not found with {by}='{value}': {e}")
                # Check for CAPTCHA (look for known CAPTCHA elements)
                try:
                    if self.driver.find_elements(By.XPATH, "//*[contains(@id, 'captcha') or contains(@class, 'captcha') or contains(text(), 'Enter the characters you see')]"):
                        captcha_detected = True
                        break
                except Exception:
                    pass
            if captcha_detected:
                logger.warning("CAPTCHA detected during login. Please solve the CAPTCHA in the browser window.")
                input("After solving the CAPTCHA, press Enter here to continue...")
                # After user input, check again for login success
                for _ in range(10):
                    time.sleep(2)
                    for by, value in user_menu_selectors:
                        try:
                            if self.driver.find_elements(by, value):
                                logger.info(f"Login successful after CAPTCHA! User menu found with {by}='{value}'")
                                return True
                        except Exception as e:
                            logger.debug(f"User menu not found with {by}='{value}': {e}")
                logger.error("Login failed after CAPTCHA. Please try again or update user menu selectors.")
                return False
            else:
                logger.error("Login failed or CAPTCHA not detected. Please check credentials or try again. If IMDB UI changed, update user menu selectors in the script.")
                return False
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            if self.debug:
                logger.exception(e)
            return False

    def logout(self):
        """Log out of current IMDB account"""
        logger.info("Logging out of current account...")
        if self.driver is None:
            logger.error("WebDriver is not initialized.")
            return False
        try:
            self.driver.get("https://www.imdb.com")
            time.sleep(self.PAGE_LOAD_WAIT if not self.fast_mode else self.ACTION_WAIT)
            # Try multiple selectors for user menu
            user_menu_clicked = False
            selectors = [
                (By.CLASS_NAME, "navbar__user"),
                (By.CSS_SELECTOR, ".ipc-button__text:has(svg[data-testid='user-avatar'])"),
                (By.CSS_SELECTOR, "label[for='navUserMenu']"),
                (By.CSS_SELECTOR, "[data-testid='user-menu-trigger']"),
                (By.CSS_SELECTOR, "button[aria-label*='account']"),
            ]
            for by, value in selectors:
                logger.debug(f"Trying to find user menu with {by}='{value}'")
                try:
                    elem = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((by, value))
                    )
                    elem.click()
                    user_menu_clicked = True
                    logger.debug(f"Clicked user menu with {by}='{value}'")
                    break
                except Exception as e:
                    logger.debug(f"Failed to click user menu with {by}='{value}': {e}")
            if not user_menu_clicked:
                logger.error("User menu not found with any known selector.")
                return False
            time.sleep(self.ACTION_WAIT)
            # Try multiple selectors for sign out
            signout_clicked = False
            selectors = [
                (By.LINK_TEXT, "Sign out"),
                (By.XPATH, "//a[contains(@href, 'logout')]"),
                (By.XPATH, "//span[text()='Sign out']/ancestor::a"),
                (By.CSS_SELECTOR, "a[href*='logout']"),
            ]
            for by, value in selectors:
                logger.debug(f"Trying to find Sign out with {by}='{value}'")
                try:
                    elem = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((by, value))
                    )
                    elem.click()
                    signout_clicked = True
                    logger.debug(f"Clicked Sign out with {by}='{value}'")
                    break
                except Exception as e:
                    logger.debug(f"Failed to click Sign out with {by}='{value}': {e}")
            if not signout_clicked:
                logger.error("Sign out link not found with any known selector.")
                return False
            logger.info("Logged out successfully!")
            return True
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
            if self.debug:
                logger.exception(e)
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
    
    def clear_browser_cache(self):
        """Clear cookies, local storage, and session storage for a clean session."""
        if self.driver is not None:
            self.driver.delete_all_cookies()
            try:
                self.driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
            except Exception as e:
                logger.debug(f"Could not clear local/session storage: {e}")

    def export_ratings(self):
        """Export ratings from current account (robust, always attempt export, handle errors if file not created/empty)"""
        logger.info("Exporting ratings...")
        if self.driver is None or self.wait is None:
            logger.error("WebDriver or WebDriverWait is not initialized.")
            return None
        assert self.driver is not None
        assert self.wait is not None
        driver = self.driver
        wait = self.wait
        try:
            # Clear any existing ratings export
            for f in glob.glob(os.path.join(self.download_dir, "ratings*.csv")):
                os.remove(f)
            driver.get("https://www.imdb.com/list/ratings")
            time.sleep(self.PAGE_LOAD_WAIT if not self.fast_mode else self.ACTION_WAIT)
            # Click the three dots menu (robust selectors)
            menu_clicked = False
            selectors = [
                (By.CSS_SELECTOR, "button[aria-label='List page options']"),
                (By.XPATH, "//button[contains(@aria-label, 'options')]"),
                (By.CSS_SELECTOR, "button[aria-haspopup='menu']"),
                (By.CSS_SELECTOR, "button[aria-label*='More']"),
            ]
            for by, value in selectors:
                logger.debug(f"Trying to find ratings menu button with {by}='{value}'")
                try:
                    elem = wait.until(
                        EC.element_to_be_clickable((by, value))
                    )
                    elem.click()
                    menu_clicked = True
                    logger.debug(f"Clicked ratings menu button with {by}='{value}'")
                    break
                except Exception as e:
                    logger.debug(f"Failed to click ratings menu button with {by}='{value}': {e}")
            if not menu_clicked:
                logger.error("Ratings menu button not found with any known selector.")
                return None
            time.sleep(self.ACTION_WAIT)
            # Click Export (robust selectors, wait for enabled)
            export_clicked = False
            selectors = [
                (By.XPATH, "//span[text()='Export']"),
                (By.XPATH, "//button[.//span[text()='Export']]"),
                (By.CSS_SELECTOR, "button[aria-label*='Export']"),
                (By.CSS_SELECTOR, "button[data-testid*='export']"),
            ]
            for by, value in selectors:
                logger.debug(f"Trying to find Export button with {by}='{value}'")
                try:
                    elem = wait.until(
                        EC.element_to_be_clickable((by, value))
                    )
                    # Wait for button to be enabled
                    for _ in range(5):
                        if elem.is_enabled():
                            break
                        time.sleep(0.2)
                    elem.click()
                    export_clicked = True
                    logger.debug(f"Clicked Export button with {by}='{value}'")
                    break
                except Exception as e:
                    logger.debug(f"Failed to click Export button with {by}='{value}': {e}")
            if not export_clicked:
                logger.error("Export button not found with any known selector.")
                return None
            # Wait for download
            downloaded_file = self.wait_for_download("ratings*.csv")
            if downloaded_file and os.path.getsize(downloaded_file) > 0:
                new_path = os.path.join(self.download_dir, RATINGS_FILE)
                os.rename(downloaded_file, new_path)
                logger.info(f"✓ Ratings exported successfully to {new_path}")
                return new_path
            else:
                logger.error("Failed to download ratings file or file is empty.")
                return None
        except Exception as e:
            logger.error(f"Error exporting ratings: {str(e)}")
            return None

    def export_watchlist(self):
        """Export watchlist from current account (robust, always attempt export, handle errors if file not created/empty)"""
        logger.info("Exporting watchlist...")
        if self.driver is None or self.wait is None:
            logger.error("WebDriver or WebDriverWait is not initialized.")
            return None
        assert self.driver is not None
        assert self.wait is not None
        driver = self.driver
        wait = self.wait
        try:
            # Clear any existing watchlist export
            for f in glob.glob(os.path.join(self.download_dir, "watchlist*.csv")):
                os.remove(f)
            driver.get("https://www.imdb.com/list/watchlist")
            time.sleep(self.PAGE_LOAD_WAIT if not self.fast_mode else self.ACTION_WAIT)
            # Click the three dots menu (robust selectors)
            menu_clicked = False
            selectors = [
                (By.CSS_SELECTOR, "button[aria-label='List page options']"),
                (By.XPATH, "//button[contains(@aria-label, 'options')]"),
                (By.CSS_SELECTOR, "button[aria-haspopup='menu']"),
                (By.CSS_SELECTOR, "button[aria-label*='More']"),
            ]
            for by, value in selectors:
                logger.debug(f"Trying to find watchlist menu button with {by}='{value}'")
                try:
                    elem = wait.until(
                        EC.element_to_be_clickable((by, value))
                    )
                    elem.click()
                    menu_clicked = True
                    logger.debug(f"Clicked watchlist menu button with {by}='{value}'")
                    break
                except Exception as e:
                    logger.debug(f"Failed to click watchlist menu button with {by}='{value}': {e}")
            if not menu_clicked:
                logger.error("Watchlist menu button not found with any known selector.")
                return None
            time.sleep(self.ACTION_WAIT)
            # Click Export (robust selectors, wait for enabled)
            export_clicked = False
            selectors = [
                (By.XPATH, "//span[text()='Export']"),
                (By.XPATH, "//button[.//span[text()='Export']]"),
                (By.CSS_SELECTOR, "button[aria-label*='Export']"),
                (By.CSS_SELECTOR, "button[data-testid*='export']"),
            ]
            for by, value in selectors:
                logger.debug(f"Trying to find Export button with {by}='{value}'")
                try:
                    elem = wait.until(
                        EC.element_to_be_clickable((by, value))
                    )
                    # Wait for button to be enabled
                    for _ in range(5):
                        if elem.is_enabled():
                            break
                        time.sleep(0.2)
                    elem.click()
                    export_clicked = True
                    logger.debug(f"Clicked Export button with {by}='{value}'")
                    break
                except Exception as e:
                    logger.debug(f"Failed to click Export button with {by}='{value}': {e}")
            if not export_clicked:
                logger.error("Export button not found with any known selector.")
                return None
            # Wait for download
            downloaded_file = self.wait_for_download("watchlist*.csv")
            if downloaded_file and os.path.getsize(downloaded_file) > 0:
                new_path = os.path.join(self.download_dir, WATCHLIST_FILE)
                os.rename(downloaded_file, new_path)
                logger.info(f"✓ Watchlist exported successfully to {new_path}")
                return new_path
            else:
                logger.error("Failed to download watchlist file or file is empty.")
                return None
        except Exception as e:
            logger.error(f"Error exporting watchlist: {str(e)}")
            return None
    
    def rate_movie(self, imdb_id, rating):
        """Rate a movie/show by its IMDB ID"""
        if self.driver is None or self.wait is None:
            logger.error("WebDriver or WebDriverWait is not initialized.")
            return False
        try:
            # Go directly to the title page
            self.driver.get(f"https://www.imdb.com/title/{imdb_id}/")
            time.sleep(DELAY_BETWEEN_ACTIONS)
            # Find and click the star rating button (robust selectors)
            rating_clicked = False
            selectors = [
                (By.CSS_SELECTOR, "[data-testid='hero-rating-bar__user-rating__score']"),
                (By.CSS_SELECTOR, "button[aria-label*='Rate']"),
                (By.XPATH, "//button[contains(@aria-label, 'Rate')]"),
            ]
            for by, value in selectors:
                logger.debug(f"Trying to find rating button with {by}='{value}'")
                try:
                    rating_button = self.wait.until(
                        EC.element_to_be_clickable((by, value))
                    )
                    rating_button.click()
                    rating_clicked = True
                    logger.debug(f"Clicked rating button with {by}='{value}'")
                    break
                except Exception as e:
                    logger.debug(f"Failed to click rating button with {by}='{value}': {e}")
            if not rating_clicked:
                logger.warning(f"Could not find rating widget for {imdb_id}, trying alternative method")
                return False
            time.sleep(1)
            # Select the appropriate star (robust selectors)
            star_clicked = False
            selectors = [
                (By.CSS_SELECTOR, f"button[aria-label='Rate {int(rating)}']"),
                (By.XPATH, f"//button[@aria-label='Rate {int(rating)}']"),
                (By.XPATH, f"//span[text()='{int(rating)}']/ancestor::button"),
            ]
            for by, value in selectors:
                logger.debug(f"Trying to find star button with {by}='{value}'")
                try:
                    star = self.wait.until(
                        EC.element_to_be_clickable((by, value))
                    )
                    star.click()
                    star_clicked = True
                    logger.debug(f"Clicked star button with {by}='{value}'")
                    break
                except Exception as e:
                    logger.debug(f"Failed to click star button with {by}='{value}': {e}")
            if not star_clicked:
                logger.warning(f"Could not find star button for rating {rating} on {imdb_id}")
                return False
            logger.info(f"✓ Rated {imdb_id} with {rating} stars")
            return True
        except Exception as e:
            logger.error(f"Error rating {imdb_id}: {str(e)}")
            if self.debug:
                logger.exception(e)
            return False
    
    def add_to_watchlist(self, imdb_id):
        """Add a movie/show to watchlist by its IMDB ID"""
        if self.driver is None or self.wait is None:
            logger.error("WebDriver or WebDriverWait is not initialized.")
            return False
        try:
            # Go directly to the title page
            self.driver.get(f"https://www.imdb.com/title/{imdb_id}/")
            time.sleep(DELAY_BETWEEN_ACTIONS)
            # Find and click the watchlist button (robust selectors)
            button_found = False
            selectors = [
                (By.CSS_SELECTOR, "[data-testid='hero-rating-bar__watchlist-button']"),
                (By.CSS_SELECTOR, "button[aria-label*='Watchlist']"),
                (By.XPATH, "//button[contains(@aria-label, 'Watchlist')]"),
            ]
            for by, value in selectors:
                logger.debug(f"Trying to find watchlist button with {by}='{value}'")
                try:
                    watchlist_button = self.wait.until(
                        EC.element_to_be_clickable((by, value))
                    )
                    # Check if already in watchlist
                    button_text = watchlist_button.text
                    if "In Watchlist" in button_text:
                        logger.info(f"⏭️  {imdb_id} already in watchlist")
                        return True
                    watchlist_button.click()
                    button_found = True
                    logger.debug(f"Clicked watchlist button with {by}='{value}'")
                    break
                except Exception as e:
                    logger.debug(f"Failed to click watchlist button with {by}='{value}': {e}")
            if not button_found:
                logger.warning(f"Could not find watchlist button for {imdb_id}")
                return False
            logger.info(f"✓ Added {imdb_id} to watchlist")
            return True
        except Exception as e:
            logger.error(f"Error adding {imdb_id} to watchlist: {str(e)}")
            if self.debug:
                logger.exception(e)
            return False
    
    def migrate_ratings(self, ratings_file):
        """Migrate all ratings from CSV file"""
        color_info(f"\n{'='*50}")
        color_info("Starting ratings migration...")
        color_info(f"{'='*50}\n")
        try:
            df = pd.read_csv(ratings_file)
            total = len(df)
            success = 0
            failures = 0
            for idx, row in df.iterrows():
                imdb_id = row['Const']
                rating = row['Your Rating']
                title = row.get('Title', imdb_id)
                idx_display = int(idx) + 1 if isinstance(idx, int) or isinstance(idx, float) else idx
                color_info(f"\n[{idx_display}/{total}] Processing: {title}")
                if self.rate_movie(imdb_id, rating):
                    success += 1
                else:
                    failures += 1
                time.sleep(DELAY_BETWEEN_MOVIES if not self.fast_mode else self.ACTION_WAIT)
                if failures > max(3, total // 10):
                    color_error(f"Too many rating migration failures ({failures}/{total}). Aborting.")
                    return False
            color_success(f"\n{'='*50}")
            color_success(f"Ratings migration complete: {success}/{total} successful")
            color_success(f"{'='*50}\n")
            return True
        except Exception as e:
            color_error(f"Error reading ratings file: {str(e)}")
            return False

    def migrate_watchlist(self, watchlist_file):
        """Migrate all watchlist items from CSV file"""
        color_info(f"\n{'='*50}")
        color_info("Starting watchlist migration...")
        color_info(f"{'='*50}\n")
        try:
            df = pd.read_csv(watchlist_file)
            total = len(df)
            success = 0
            failures = 0
            for idx, row in df.iterrows():
                imdb_id = row['Const']
                title = row.get('Title', imdb_id)
                idx_display = int(idx) + 1 if isinstance(idx, int) or isinstance(idx, float) else idx
                color_info(f"\n[{idx_display}/{total}] Processing: {title}")
                if self.add_to_watchlist(imdb_id):
                    success += 1
                else:
                    failures += 1
                time.sleep(DELAY_BETWEEN_MOVIES if not self.fast_mode else self.ACTION_WAIT)
                if failures > max(3, total // 10):
                    color_error(f"Too many watchlist migration failures ({failures}/{total}). Aborting.")
                    return False
            color_success(f"\n{'='*50}")
            color_success(f"Watchlist migration complete: {success}/{total} successful")
            color_success(f"{'='*50}\n")
            return True
        except Exception as e:
            color_error(f"Error reading watchlist file: {str(e)}")
            return False
    
    def close(self):
        """Close the browser"""
        if self.driver is not None:
            self.driver.quit()  # type: ignore
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources"""
        if hasattr(self, 'driver') and self.driver is not None:
            self.driver.quit()
        # Clean up downloaded files
        if hasattr(self, 'download_dir'):
            for pattern in ['*.csv', '*.crdownload']:
                for f in glob.glob(os.path.join(self.download_dir, pattern)):
                    try:
                        os.remove(f)
                    except OSError:
                        pass

    def get_logged_in_user(self):
        """Try to extract the logged-in user's display name or email from the user menu/profile."""
        if self.driver is None:
            return None
        selectors = [
            (By.CSS_SELECTOR, ".navbar__user span, .ipc-button__text span, [data-testid='user-menu-trigger'] span"),
            (By.CSS_SELECTOR, "[data-testid='user-menu-trigger']"),
            (By.CSS_SELECTOR, "label[for='navUserMenu']"),
            (By.CSS_SELECTOR, "button[aria-label*='account']"),
        ]
        for by, value in selectors:
            try:
                elems = self.driver.find_elements(by, value)
                for elem in elems:
                    text = elem.text.strip()
                    if text:
                        return text
            except Exception:
                continue
        return None

def validate_csv_file(file_path, file_type):
    """Validate that a CSV file exists and has the expected format"""
    if not os.path.exists(file_path):
        return False, f"{file_type} file not found: {file_path}"
    
    if os.path.getsize(file_path) == 0:
        return False, f"{file_type} file is empty: {file_path}"
    
    try:
        df = pd.read_csv(file_path)
        if file_type == "ratings":
            if 'Const' not in df.columns or 'Your Rating' not in df.columns:
                return False, f"{file_type} file missing required columns 'Const' and/or 'Your Rating': {file_path}"
        elif file_type == "watchlist":
            if 'Const' not in df.columns:
                return False, f"{file_type} file missing required column 'Const': {file_path}"
        
        if len(df) == 0:
            return False, f"{file_type} file contains no data: {file_path}"
        
        return True, f"✓ {file_type} file validated: {file_path} ({len(df)} items)"
    except Exception as e:
        return False, f"Error reading {file_type} file {file_path}: {str(e)}"

def get_credentials(args):
    """Get credentials from environment variables, command line, or interactive prompt"""
    credentials = {}
    
    # Try environment variables first
    credentials['source_email'] = os.environ.get('IMDB_SOURCE_EMAIL', args.source_email)
    credentials['source_password'] = os.environ.get('IMDB_SOURCE_PASSWORD', args.source_password)
    credentials['dest_email'] = os.environ.get('IMDB_DEST_EMAIL', args.dest_email)
    credentials['dest_password'] = os.environ.get('IMDB_DEST_PASSWORD', args.dest_password)
    
    # Determine if we need source credentials
    using_custom_files = args.ratings_file or args.watchlist_file
    using_local_files = args.use_local_csv or using_custom_files
    need_source_credentials = not using_local_files
    
    # Interactive prompts for missing credentials
    if need_source_credentials:
        if not credentials['source_email']:
            credentials['source_email'] = input("Enter source account email: ").strip()
        if not credentials['source_password']:
            credentials['source_password'] = getpass.getpass("Enter source account password: ")
    
    if not credentials['dest_email']:
        credentials['dest_email'] = input("Enter destination account email: ").strip()
    if not credentials['dest_password']:
        credentials['dest_password'] = getpass.getpass("Enter destination account password: ")
    
    # Validate we have what we need
    if need_source_credentials:
        if not credentials['source_email'] or not credentials['source_password']:
            logger.error("Source account credentials are required for automated export")
            return None
    
    if not credentials['dest_email'] or not credentials['dest_password']:
        logger.error("Destination account credentials are required")
        return None
    
    return credentials

def main():
    """Main migration function"""
    print("Main function started")
    parser = argparse.ArgumentParser(
        description='IMDB Account Migration Tool - Migrate ratings and watchlist between IMDB accounts',
        epilog='''Usage examples:
  # Full migration with automated export: python imdb_migration_script.py
  # Use local CSV files: python imdb_migration_script.py --use-local-csv
  # Use custom CSV files: python imdb_migration_script.py --ratings-file my_ratings.csv --watchlist-file my_watchlist.csv
  # Migrate only ratings: python imdb_migration_script.py --ratings-only
  # Migrate only watchlist: python imdb_migration_script.py --watchlist-only

Credentials can be provided via environment variables (IMDB_SOURCE_EMAIL, etc.) or will be prompted interactively.'''
    )
    
    # Credential arguments (optional - not recommended for passwords)
    parser.add_argument('--source-email', help='Source account email (or use IMDB_SOURCE_EMAIL env var)')
    parser.add_argument('--source-password', help='Source account password (NOT RECOMMENDED - use env var or prompt)')
    parser.add_argument('--dest-email', help='Destination account email (or use IMDB_DEST_EMAIL env var)')
    parser.add_argument('--dest-password', help='Destination account password (NOT RECOMMENDED - use env var or prompt)')
    
    # Other arguments
    parser.add_argument('--use-local-csv', action='store_true', 
                       help='Skip automated export and use local CSV files (ratings.csv and watchlist.csv)')
    parser.add_argument('--ratings-file', type=str,
                       help='Path to custom ratings CSV file (overrides --use-local-csv)')
    parser.add_argument('--watchlist-file', type=str,
                       help='Path to custom watchlist CSV file (overrides --use-local-csv)')
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
    
    try:
        print("\nInitializing browser driver...")
        migrator = IMDBMigrator(headless=args.headless, fast_mode=True)
        print("Browser driver initialized successfully.\n")

    except Exception as e:
        color_error(f"Error initializing browser driver: {str(e)}")
        sys.exit(1)
    
    try:
        ratings_file = None
        watchlist_file = None
        all_success = True
        
        # Phase 1: Export from source account (if not using local files)
        using_custom_files = args.ratings_file or args.watchlist_file
        using_local_files = args.use_local_csv or using_custom_files
        
        if not using_local_files:
            print(f"\n{'='*60}")
            print("PHASE 1: EXPORTING FROM SOURCE ACCOUNT")
            print(f"{'='*60}\n")
            
            # Login to source account
            if not migrator.login(credentials['source_email'], credentials['source_password']):
                color_error("Failed to login to source account. Please check credentials.")
                sys.exit(1)
            
            # Export data based on user preference
            if not args.watchlist_only:
                ratings_file = migrator.export_ratings()
                if not ratings_file:
                    color_warn("No ratings file exported.")
                    all_success = False
            
            if not args.ratings_only:
                watchlist_file = migrator.export_watchlist()
                if not watchlist_file:
                    color_warn("No watchlist file exported.")
                    all_success = False
            
            # Logout from source account
            migrator.logout()
            time.sleep(3 if not migrator.fast_mode else migrator.ACTION_WAIT)
            
        else:
            # Use local/custom files
            print(f"\n{'='*60}")
            print("USING LOCAL/CUSTOM CSV FILES")
            print(f"{'='*60}\n")
            
            # Handle custom file paths
            if args.ratings_file:
                is_valid, message = validate_csv_file(args.ratings_file, "ratings")
                if is_valid:
                    ratings_file = args.ratings_file
                    print(message)
                else:
                    color_error(message)
                    all_success = False
            elif not args.watchlist_only and os.path.exists(RATINGS_FILE):
                is_valid, message = validate_csv_file(RATINGS_FILE, "ratings")
                if is_valid:
                    ratings_file = RATINGS_FILE
                    print(message)
                else:
                    color_error(message)
                    all_success = False
            
            if args.watchlist_file:
                is_valid, message = validate_csv_file(args.watchlist_file, "watchlist")
                if is_valid:
                    watchlist_file = args.watchlist_file
                    print(message)
                else:
                    color_error(message)
                    all_success = False
            elif not args.ratings_only and os.path.exists(WATCHLIST_FILE):
                is_valid, message = validate_csv_file(WATCHLIST_FILE, "watchlist")
                if is_valid:
                    watchlist_file = WATCHLIST_FILE
                    print(message)
                else:
                    color_error(message)
                    all_success = False
            
            # Check if we have any files to work with
            if not ratings_file and not watchlist_file:
                color_error("No valid CSV files found. Please provide --ratings-file, --watchlist-file, or ensure ratings.csv/watchlist.csv exist.")
                sys.exit(1)
        
        # After export, if neither file is present/non-empty, abort before phase two
        exported_files = []
        if ratings_file and os.path.exists(ratings_file) and os.path.getsize(ratings_file) > 0:
            exported_files.append(ratings_file)
        if watchlist_file and os.path.exists(watchlist_file) and os.path.getsize(watchlist_file) > 0:
            exported_files.append(watchlist_file)
        if not exported_files:
            color_warn("No export files were created or all are empty. Aborting before import phase.")
            migrator.logout()
            migrator.clear_browser_cache()
            migrator.close()
            print("="*60 + "\n")
            return

        # Phase 2: Import to destination account
        print(f"\n{'='*60}")
        print("PHASE 2: IMPORTING TO DESTINATION ACCOUNT")
        print(f"{'='*60}\n")
        
        # Login to destination account
        if not migrator.login(credentials['dest_email'], credentials['dest_password']):
            color_error("Failed to login to destination account. Please check credentials.")
            sys.exit(1)
        
        # After destination login, check that the user is different from the source (if we have source credentials)
        dest_user = migrator.get_logged_in_user()
        if dest_user and 'source_email' in credentials and credentials['source_email']:
            if dest_user.lower() == credentials['source_email'].lower():
                color_error(f"Destination account ({dest_user}) appears to be the same as source account ({credentials['source_email']}). Aborting to prevent overwriting.")
                sys.exit(1)

        # Migrate data
        dest_success = True
        if ratings_file and not args.watchlist_only:
            dest_success = migrator.migrate_ratings(ratings_file)
            if not dest_success:
                color_error("Ratings migration to destination account failed.")
                all_success = False
        elif not ratings_file and not args.watchlist_only:
            color_warn("No ratings file available to migrate")
            all_success = False
        if watchlist_file and not args.ratings_only:
            dest_success = migrator.migrate_watchlist(watchlist_file)
            if not dest_success:
                color_error("Watchlist migration to destination account failed.")
                all_success = False
        elif not watchlist_file and not args.ratings_only:
            color_warn("No watchlist file available to migrate")
            all_success = False
        print("\n" + "="*60)
        if all_success:
            color_success("MIGRATION COMPLETE!\nPlease check your destination account to verify.")
        else:
            color_error("MIGRATION INCOMPLETE. Some actions failed. See logs above.")
        migrator.close()
        # Only clean up files if all_success
        if all_success:
            if hasattr(migrator, 'download_dir'):
                for pattern in ['*.csv', '*.crdownload']:
                    for f in glob.glob(os.path.join(migrator.download_dir, pattern)):
                        try:
                            os.remove(f)
                        except OSError:
                            pass
    except KeyboardInterrupt:
        color_warn("\n\nMigration cancelled by user.")
    except Exception as e:
        color_error(f"\n\nUnexpected error: {str(e)}")
    finally:
        print("="*60 + "\n")
        exported_files = []
        if 'ratings_file' in locals() and ratings_file and os.path.exists(ratings_file) and os.path.getsize(ratings_file) > 0:
            exported_files.append(ratings_file)
        if 'watchlist_file' in locals() and watchlist_file and os.path.exists(watchlist_file) and os.path.getsize(watchlist_file) > 0:
            exported_files.append(watchlist_file)
        if exported_files:
            color_info(f"Exported files are saved in: {migrator.download_dir}")
            for f in exported_files:
                color_info(f"  - {f}")
        else:
            color_warn("No export files were created or all are empty.")

if __name__ == "__main__":
    main()