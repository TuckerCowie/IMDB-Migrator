import pytest
from unittest.mock import MagicMock, patch
import os
from imdb_migration_script import IMDBMigrator
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

@pytest.fixture
def mock_webdriver():
    with patch('imdb_migration_script.webdriver') as mock:
        mock.Chrome.return_value = MagicMock()
        yield mock

@pytest.fixture
def mock_wait():
    with patch('selenium.webdriver.support.wait.WebDriverWait') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def migrator(mock_webdriver, mock_wait):
    migrator = IMDBMigrator(headless=True)
    migrator.wait = mock_wait
    yield migrator
    migrator.close()

def test_login_success(migrator):
    # Mock successful login
    mock_element = MagicMock()
    migrator.wait.until.return_value = mock_element
    migrator.driver.find_element.return_value = mock_element

    result = migrator.login("test@example.com", "password123")
    assert result == True

def test_login_failure(migrator):
    # Mock failed login
    migrator.wait.until.side_effect = TimeoutException()
    
    result = migrator.login("test@example.com", "wrong_password")
    assert result == False

def test_logout_success(migrator):
    # Mock successful logout
    mock_element = MagicMock()
    migrator.wait.until.return_value = mock_element
    
    result = migrator.logout()
    assert result == True

def test_rate_movie_success(migrator):
    # Mock successful movie rating
    mock_element = MagicMock()
    migrator.wait.until.return_value = mock_element
    
    result = migrator.rate_movie("tt0111161", 10)  # Using Shawshank Redemption as example
    assert result == True

def test_add_to_watchlist_success(migrator):
    # Mock successful watchlist addition
    mock_element = MagicMock()
    mock_element.text = "Add to Watchlist"
    migrator.wait.until.return_value = mock_element
    
    result = migrator.add_to_watchlist("tt0111161")
    assert result == True

def test_add_to_watchlist_already_added(migrator):
    # Mock item already in watchlist
    mock_element = MagicMock()
    mock_element.text = "In Watchlist"
    migrator.wait.until.return_value = mock_element
    
    result = migrator.add_to_watchlist("tt0111161")
    assert result == True



def test_wait_for_download_success(migrator, tmp_path):
    # Create a temporary file to simulate download
    test_file = tmp_path / "ratings.csv"
    test_file.write_text("test data")
    migrator.download_dir = str(tmp_path)
    
    result = migrator.wait_for_download("ratings.csv", timeout=1)
    assert result == str(test_file)

def test_wait_for_download_timeout(migrator, tmp_path):
    migrator.download_dir = str(tmp_path)
    
    result = migrator.wait_for_download("nonexistent.csv", timeout=1)
    assert result is None
