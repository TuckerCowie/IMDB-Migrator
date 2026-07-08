import pytest
from unittest.mock import MagicMock, patch
import os
from imdb_migration_script import IMDBMigrator
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import ssl

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

def test_login_success_first_selector(migrator):
    # First selector works
    mock_elem = MagicMock()
    migrator.driver.find_elements.return_value = [mock_elem]
    migrator.wait.until.return_value = mock_elem
    with patch('builtins.input', return_value=''):
        result = migrator.login('test@example.com', 'password123')
    assert result is True

def test_login_success_fallback_selector(migrator):
    # First selector fails, second works
    migrator.wait.until.side_effect = [TimeoutException(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    migrator.driver.find_elements.return_value = [MagicMock()]
    with patch('builtins.input', return_value=''):
        result = migrator.login('test@example.com', 'password123')
    assert result is True

def test_login_all_selectors_fail(migrator, caplog):
    migrator.wait.until.side_effect = TimeoutException()
    migrator.driver.find_elements.return_value = []
    with patch('builtins.input', return_value=''):
        result = migrator.login('test@example.com', 'password123')
    assert result is False
    assert any('not found with any known selector' in r for r in caplog.text.splitlines())

def test_login_captcha_handling(migrator):
    # Simulate captcha detected and user solves it
    mock_elem = MagicMock()
    migrator.wait.until.return_value = mock_elem
    # Simulate no user menu, but captcha element found
    def find_elements_side_effect(by, value):
        if 'captcha' in str(value):
            return [MagicMock()]
        return []
    migrator.driver.find_elements.side_effect = find_elements_side_effect
    with patch('builtins.input', return_value=''), \
         patch.object(migrator, '_wait_for_element', return_value=None):
        result = migrator.login('test@example.com', 'password123')
    assert result is False  # After captcha, still no user menu

def test_logout_success_first_selector(migrator):
    mock_elem = MagicMock()
    migrator.wait.until.return_value = mock_elem
    result = migrator.logout()
    assert result is True

def test_logout_fallback_selector(migrator):
    # First selector fails, second works
    migrator.wait.until.side_effect = [TimeoutException(), MagicMock(), MagicMock()]
    result = migrator.logout()
    assert result is True

def test_logout_all_selectors_fail(migrator, caplog):
    migrator.wait.until.side_effect = TimeoutException()
    result = migrator.logout()
    assert result is False
    assert any('not found with any known selector' in r for r in caplog.text.splitlines())

def test_export_ratings_success_first_selector(migrator, tmp_path):
    # Simulate menu and export buttons found, file downloaded
    mock_elem = MagicMock()
    migrator.wait.until.return_value = mock_elem
    test_file = tmp_path / 'ratings.csv'
    test_file.write_text('test')
    migrator.download_dir = str(tmp_path)
    with patch('glob.glob', return_value=[str(test_file)]):
        result = migrator.export_ratings()
    assert result == str(test_file)

def test_export_ratings_menu_fallback(migrator, tmp_path):
    # First menu selector fails, second works
    mock_elem = MagicMock()
    migrator.wait.until.side_effect = [TimeoutException(), mock_elem, mock_elem, mock_elem]
    test_file = tmp_path / 'ratings.csv'
    test_file.write_text('test')
    migrator.download_dir = str(tmp_path)
    with patch('glob.glob', return_value=[str(test_file)]):
        result = migrator.export_ratings()
    assert result == str(test_file)

def test_export_ratings_all_selectors_fail(migrator, caplog):
    migrator.wait.until.side_effect = TimeoutException()
    with patch('glob.glob', return_value=[]):
        result = migrator.export_ratings()
    assert result is None
    assert any('not found with any known selector' in r for r in caplog.text.splitlines())

def test_export_watchlist_success_first_selector(migrator, tmp_path):
    mock_elem = MagicMock()
    migrator.wait.until.return_value = mock_elem
    test_file = tmp_path / 'watchlist.csv'
    test_file.write_text('test')
    migrator.download_dir = str(tmp_path)
    with patch('glob.glob', return_value=[str(test_file)]):
        result = migrator.export_watchlist()
    assert result == str(test_file)

def test_export_watchlist_menu_fallback(migrator, tmp_path):
    mock_elem = MagicMock()
    migrator.wait.until.side_effect = [TimeoutException(), mock_elem, mock_elem, mock_elem]
    test_file = tmp_path / 'watchlist.csv'
    test_file.write_text('test')
    migrator.download_dir = str(tmp_path)
    with patch('glob.glob', return_value=[str(test_file)]):
        result = migrator.export_watchlist()
    assert result == str(test_file)

def test_export_watchlist_all_selectors_fail(migrator, caplog):
    migrator.wait.until.side_effect = TimeoutException()
    with patch('glob.glob', return_value=[]):
        result = migrator.export_watchlist()
    assert result is None
    assert any('not found with any known selector' in r for r in caplog.text.splitlines())

def test_rate_movie_success_first_selector(migrator):
    mock_elem = MagicMock()
    migrator.wait.until.return_value = mock_elem
    result = migrator.rate_movie('tt0111161', 10)
    assert result is True

def test_rate_movie_fallback_selector(migrator):
    migrator.wait.until.side_effect = [TimeoutException(), MagicMock(), MagicMock(), MagicMock()]
    result = migrator.rate_movie('tt0111161', 10)
    assert result is True

def test_rate_movie_all_selectors_fail(migrator, caplog):
    migrator.wait.until.side_effect = TimeoutException()
    result = migrator.rate_movie('tt0111161', 10)
    assert result is False
    assert any('not found' in r or 'trying alternative method' in r for r in caplog.text.splitlines())

def test_add_to_watchlist_success_first_selector(migrator):
    mock_elem = MagicMock()
    mock_elem.text = 'Add to Watchlist'
    migrator.wait.until.return_value = mock_elem
    result = migrator.add_to_watchlist('tt0111161')
    assert result is True

def test_add_to_watchlist_fallback_selector(migrator):
    migrator.wait.until.side_effect = [TimeoutException(), MagicMock(), MagicMock()]
    mock_elem = MagicMock()
    mock_elem.text = 'Add to Watchlist'
    migrator.wait.until.return_value = mock_elem
    result = migrator.add_to_watchlist('tt0111161')
    assert result is True

def test_add_to_watchlist_all_selectors_fail(migrator, caplog):
    migrator.wait.until.side_effect = TimeoutException()
    result = migrator.add_to_watchlist('tt0111161')
    assert result is False
    assert any('not found' in r or 'Could not find watchlist button' in r for r in caplog.text.splitlines())

def test_add_to_watchlist_already_added(migrator):
    mock_elem = MagicMock()
    mock_elem.text = 'In Watchlist'
    migrator.wait.until.return_value = mock_elem
    result = migrator.add_to_watchlist('tt0111161')
    assert result is True

def test_wait_for_download_success(migrator, tmp_path):
    test_file = tmp_path / 'ratings.csv'
    test_file.write_text('test data')
    migrator.download_dir = str(tmp_path)
    result = migrator.wait_for_download('ratings.csv', timeout=1)
    assert result == str(test_file)

def test_wait_for_download_timeout(migrator, tmp_path):
    migrator.download_dir = str(tmp_path)
    result = migrator.wait_for_download('nonexistent.csv', timeout=1)
    assert result is None

def test_close_and_exit_methods(mock_webdriver, mock_wait):
    migrator = IMDBMigrator(headless=True)
    migrator.driver = MagicMock()
    migrator.wait = mock_wait
    # Test close
    migrator.close()
    migrator.driver.quit.assert_called_once()
    # Test __exit__ (should not raise)
    migrator.driver = MagicMock()
    migrator.__exit__(None, None, None)
    migrator.driver.quit.assert_called()

def test_libressl_warning(monkeypatch, capsys):
    monkeypatch.setattr(ssl, "OPENSSL_VERSION", "LibreSSL 2.8.3")
    with patch("builtins.print") as mock_print:
        import importlib
        import imdb_migration_script
        importlib.reload(imdb_migration_script)
        mock_print.assert_any_call(
            "Loaded environment variables from .env file.")
