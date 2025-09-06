import os
import pytest
from unittest.mock import MagicMock, patch

from src.modules.AccessAnalyzer.url_scan import word_list_reader, check_url_status, url_scanner
from src.modules.AccessAnalyzer.login_access import login_acess

# Path for a temporary wordlist file
TEMP_WORDLIST_PATH = "temp_test_wordlist.txt"

@pytest.fixture(scope="module")
def setup_wordlist():
    # Create a dummy wordlist file for testing
    with open(TEMP_WORDLIST_PATH, "w") as f:
        f.write("/admin\n")
        f.write("/dashboard\n")
        f.write("  /users  \n") # Test stripping whitespace
        f.write("\n") # Test empty lines
        f.write("/settings\n")
    yield
    # Clean up the dummy wordlist file after tests
    os.remove(TEMP_WORDLIST_PATH)

def test_word_list_reader(setup_wordlist):
    paths = word_list_reader(TEMP_WORDLIST_PATH)
    assert paths == ["/admin", "/dashboard", "/users", "/settings"]

def test_word_list_reader_file_not_found():
    paths = word_list_reader("non_existent_file.txt")
    assert paths == []

@pytest.mark.parametrize("url, login_url, goto_status, final_url, expected_result", [
    ("http://test.com/admin", "http://test.com/login", 200, "http://test.com/admin", True),
    ("http://test.com/restricted", "http://test.com/login", 302, "http://test.com/login", False), # Redirected to login
    ("http://test.com/error", "http://test.com/login", 404, "http://test.com/error", False),
    ("http://test.com/admin", "http://test.com/login", None, "http://test.com/admin", False), # No response
])
def test_check_url_status(url, login_url, goto_status, final_url, expected_result):
    mock_page = MagicMock()
    mock_response = MagicMock()
    mock_response.status = goto_status
    mock_page.goto.return_value = mock_response
    mock_page.url = final_url # Simulate the final URL after goto

    result = check_url_status(mock_page, url, login_url)
    assert result == expected_result

@patch('src.modules.AccessAnalyzer.url_scan.login_acess')
@patch('src.modules.AccessAnalyzer.url_scan.check_url_status')
@patch('src.modules.AccessAnalyzer.url_scan.word_list_reader')
def test_url_scanner_success(mock_word_list_reader, mock_check_url_status, mock_login_acess):
    mock_login_acess.return_value = True
    mock_word_list_reader.return_value = ["/admin", "/dashboard"]
    
    # Simulate both URLs being accessible
    mock_check_url_status.side_effect = [True, True] 

    login_url = "http://mock.com/login"
    base_url = "http://mock.com/"
    word_list_path = "dummy_path.txt"

    # Capture print output
    with patch('builtins.print') as mock_print:
        url_scanner(login_url, base_url, word_list_path, headless=True)
        
        # Assert that login_acess was called
        mock_login_acess.assert_called_once_with(ANY, login_url)
        
        # Assert that check_url_status was called for both URLs
        mock_check_url_status.assert_any_call(ANY, "http://mock.com/admin", login_url)
        mock_check_url_status.assert_any_call(ANY, "http://mock.com/dashboard", login_url)
        
        # Assert that the success message was printed
        mock_print.assert_any_call(f"Encontradas 2 URLs acessíveis:")

@patch('src.modules.AccessAnalyzer.url_scan.login_acess')
@patch('src.modules.AccessAnalyzer.url_scan.check_url_status')
@patch('src.modules.AccessAnalyzer.url_scan.word_list_reader')
def test_url_scanner_login_failure(mock_word_list_reader, mock_check_url_status, mock_login_acess):
    mock_login_acess.return_value = False # Simulate login failure
    mock_word_list_reader.return_value = ["/admin"] # Wordlist doesn't matter here

    login_url = "http://mock.com/login"
    base_url = "http://mock.com/"
    word_list_path = "dummy_path.txt"

    with patch('builtins.print') as mock_print:
        url_scanner(login_url, base_url, word_list_path, headless=True)
        
        mock_login_acess.assert_called_once_with(ANY, login_url)
        mock_check_url_status.assert_not_called() # Should not proceed to check URLs
        mock_print.assert_any_call("Falha no login. Abortando o scan.")

@patch('src.modules.AccessAnalyzer.url_scan.login_acess')
@patch('src.modules.AccessAnalyzer.url_scan.check_url_status')
@patch('src.modules.AccessAnalyzer.url_scan.word_list_reader')
def test_url_scanner_no_urls(mock_word_list_reader, mock_check_url_status, mock_login_acess):
    mock_login_acess.return_value = True
    mock_word_list_reader.return_value = [] # Simulate empty wordlist

    login_url = "http://mock.com/login"
    base_url = "http://mock.com/"
    word_list_path = "dummy_path.txt"

    with patch('builtins.print') as mock_print:
        url_scanner(login_url, base_url, word_list_path, headless=True)
        
        mock_login_acess.assert_not_called() # No need to login if no URLs
        mock_check_url_status.assert_not_called()
        mock_print.assert_any_call("Nenhuma URL para escanear.")

# Helper for ANY matcher
class Any:
    def __eq__(self, other):
        return True

ANY = Any()
