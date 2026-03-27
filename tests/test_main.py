import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.main import app

runner = CliRunner()


@pytest.fixture
def mock_index_file(tmp_path: Path) -> Path:
    """
    Creates a temporary, valid index.json file to test CLI happy paths
    without relying on the real crawler running.
    """
    file_path = tmp_path / "index.json"
    dummy_data = {
        "metadata": {"total_documents": 1},
        "index": {
            "good": {
                "idf": 0.5,
                "postings": {
                    "page_1": {"tf": 0.5, "positions": [0, 3]}
                }
            }
        }
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(dummy_data, f)
    return file_path


# ==========================================
# TEST ORCHESTRATION (BUILD)
# ==========================================

@patch("src.main.InvertedIndex")
@patch("src.main.PoliteCrawler")
def test_cli_build(
    mock_crawler_cls: MagicMock,
    mock_index_cls: MagicMock,
    tmp_path: Path
) -> None:
    """Test the 'build' command orchestrates the crawler and indexer correctly."""
    mock_crawler = mock_crawler_cls.return_value
    mock_crawler.fetch_quotes.side_effect = [
        [{"text": "A quote", "author": "An Author"}],
        []
    ]
    mock_index = mock_index_cls.return_value

    with patch("src.main.INDEX_FILE", tmp_path / "test_index.json"):
        result = runner.invoke(app, ["build"])
        assert result.exit_code == 0
        assert "Crawl complete" in result.stdout
        mock_index.add_document.assert_called_once_with(
            "page_1_quote_0", "A quote An Author")
        mock_index.save.assert_called_once()


# ==========================================
# TEST COMMAND: LOAD
# ==========================================

def test_cli_load_without_index(tmp_path: Path) -> None:
    """Test 'load' aborts if index is missing."""
    with patch("src.main.INDEX_FILE", tmp_path / "missing.json"):
        result = runner.invoke(app, ["load"])
        assert result.exit_code == 1
        assert "Error: Index file not found" in result.stdout


def test_cli_load_success(mock_index_file: Path) -> None:
    """Test 'load' successfully reads from disk."""
    with patch("src.main.INDEX_FILE", mock_index_file):
        result = runner.invoke(app, ["load"])
        assert result.exit_code == 0
        assert "Successfully loaded index" in result.stdout


# ==========================================
# TEST COMMAND: PRINT
# ==========================================

def test_cli_print_without_index(tmp_path: Path) -> None:
    """Test 'print' aborts if index is missing."""
    with patch("src.main.INDEX_FILE", tmp_path / "missing.json"):
        result = runner.invoke(app, ["print", "good"])
        assert result.exit_code == 1


def test_cli_print_word_not_found(mock_index_file: Path) -> None:
    """Test 'print' handles queries for words not in the DB."""
    with patch("src.main.INDEX_FILE", mock_index_file):
        result = runner.invoke(app, ["print", "nonsense"])
        assert result.exit_code == 0
        assert "not found in the index" in result.stdout


def test_cli_print_success(mock_index_file: Path) -> None:
    """Test 'print' successfully formats and outputs the stats table."""
    with patch("src.main.INDEX_FILE", mock_index_file):
        result = runner.invoke(app, ["print", "good"])
        assert result.exit_code == 0
        assert "IDF Score" in result.stdout
        assert "page_1" in result.stdout


# ==========================================
# TEST COMMAND: FIND
# ==========================================

def test_cli_find_without_index(tmp_path: Path) -> None:
    """Test 'find' aborts if index is missing."""
    with patch("src.main.INDEX_FILE", tmp_path / "missing.json"):
        result = runner.invoke(app, ["find", "good"])
        assert result.exit_code == 1


def test_cli_find_no_results(mock_index_file: Path) -> None:
    """Test 'find' gracefully handles queries with zero matching documents."""
    with patch("src.main.INDEX_FILE", mock_index_file):
        # Testing a multi-word query where one word doesn't exist
        result = runner.invoke(app, ["find", "good", "nonsense"])
        assert result.exit_code == 0
        assert "No documents found containing all words" in result.stdout


def test_cli_find_success(mock_index_file: Path) -> None:
    """Test 'find' successfully formats and outputs the ranked results table."""
    with patch("src.main.INDEX_FILE", mock_index_file):
        # Testing a valid query
        result = runner.invoke(app, ["find", "good"])
        assert result.exit_code == 0
        assert "matching documents for 'good'" in result.stdout
        assert "page_1" in result.stdout
