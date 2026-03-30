from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.main import app

runner = CliRunner()


# ==========================================
# TEST ORCHESTRATION (BUILD)
# ==========================================

@patch("src.main.InvertedIndex")
@patch("src.main.PoliteCrawler")
def test_cli_build_happy_path(
    mock_crawler_cls: MagicMock,
    mock_index_cls: MagicMock,
    mock_get_path: MagicMock,
    tmp_path: Path
) -> None:
    """Test the 'build' command naturally exhausts the pagination loop."""
    mock_crawler = mock_crawler_cls.return_value

    # Simulate a final page that HAS quotes, but NO next_page.
    mock_crawler.fetch_quotes.side_effect = [
        {
            "quotes": [{"text": "A quote", "author": "An Author", "tags": ["test"]}],
            "next_page": None
        }
    ]

    mock_index = mock_index_cls.return_value
    mock_get_path.return_value = tmp_path / "test_index.json"

    result = runner.invoke(app, ["build"])

    assert result.exit_code == 0
    assert "Crawl complete" in result.stdout
    mock_index.add_document.assert_called_once_with(
        doc_id="page_1_quote_0",
        text="A quote",
        author="An Author",
        tags=["test"],
        url="https://quotes.toscrape.com/"
    )
    mock_index.save.assert_called_once()


@patch("src.main.InvertedIndex")
@patch("src.main.PoliteCrawler")
def test_cli_build_premature_break(
    mock_crawler_cls: MagicMock,
    mock_index_cls: MagicMock,
    mock_get_path: MagicMock,
    tmp_path: Path
) -> None:
    """Test the 'build' command breaks gracefully when a page returns no quotes."""
    mock_crawler = mock_crawler_cls.return_value
    mock_crawler.fetch_quotes.return_value = {"quotes": [], "next_page": None}
    mock_get_path.return_value = tmp_path / "test_index.json"

    result = runner.invoke(app, ["build"])

    assert result.exit_code == 0
    assert "No quotes found on" in result.stdout
    assert "Crawl complete" in result.stdout


@patch("src.main.InvertedIndex")
@patch("src.main.PoliteCrawler")
def test_cli_build_max_pages_limit(
    mock_crawler_cls: MagicMock,
    mock_index_cls: MagicMock,
    mock_get_path: MagicMock,
    tmp_path: Path
) -> None:
    """Test the 'build' command safely aborts when hitting the --max-pages limit."""
    mock_crawler = mock_crawler_cls.return_value

    # Simulate an infinite loop of pages.
    mock_crawler.fetch_quotes.return_value = {
        "quotes": [{"text": "Infinite quote", "author": "Bot", "tags": []}],
        "next_page": "/page/next/"
    }

    mock_get_path.return_value = tmp_path / "test_index.json"

    result = runner.invoke(app, ["build", "--max-pages", "1"])

    assert result.exit_code == 0
    assert "Max pages limit (1) reached" in result.stdout

    mock_index = mock_index_cls.return_value
    mock_index.add_document.assert_called_once_with(
        doc_id="page_1_quote_0",
        text="Infinite quote",
        author="Bot",
        tags=[],
        url="https://quotes.toscrape.com/"
    )


# ==========================================
# TEST COMMAND: LOAD
# ==========================================

def test_cli_load_without_index(mock_get_path: MagicMock, tmp_path: Path) -> None:
    """Test 'load' aborts if index is missing."""
    mock_get_path.return_value = tmp_path / "missing.json"
    result = runner.invoke(app, ["load"])

    assert result.exit_code == 1
    assert "not found" in result.stdout.lower()


def test_cli_load_success(mock_get_path: MagicMock, mock_index_file: Path) -> None:
    """Test 'load' successfully reads from disk."""
    mock_get_path.return_value = mock_index_file
    result = runner.invoke(app, ["load"])

    assert result.exit_code == 0
    assert "Successfully loaded index" in result.stdout


# ==========================================
# TEST COMMAND: PRINT
# ==========================================

def test_cli_print_without_index(mock_get_path: MagicMock, tmp_path: Path) -> None:
    """Test 'print' aborts if index is missing."""
    mock_get_path.return_value = tmp_path / "missing.json"
    result = runner.invoke(app, ["print", "good"])
    assert result.exit_code == 1


def test_cli_print_word_not_found(
        mock_get_path: MagicMock,
        mock_index_file: Path
) -> None:
    """Test 'print' handles queries for words not in the DB."""
    mock_get_path.return_value = mock_index_file
    result = runner.invoke(app, ["print", "nonsense"])

    assert result.exit_code == 0
    assert "not found in the index" in result.stdout


def test_cli_print_success(mock_get_path: MagicMock, mock_index_file: Path) -> None:
    """Test 'print' successfully formats and outputs the stats table."""
    mock_get_path.return_value = mock_index_file
    result = runner.invoke(app, ["print", "good"])

    assert result.exit_code == 0
    assert "IDF Score" in result.stdout
    # Asserts the specific document ID from our new conftest schema
    assert "page_1_quote_0" in result.stdout


# ==========================================
# TEST COMMAND: FIND
# ==========================================

def test_cli_find_without_index(mock_get_path: MagicMock, tmp_path: Path) -> None:
    """Test 'find' aborts if index is missing."""
    mock_get_path.return_value = tmp_path / "missing.json"
    result = runner.invoke(app, ["find", "good"])

    assert result.exit_code == 1
    assert "Index not found" in result.stdout


def test_cli_find_no_results(mock_get_path: MagicMock, mock_index_file: Path) -> None:
    """Test 'find' gracefully handles queries with zero matching documents."""
    mock_get_path.return_value = mock_index_file
    # Changed from ["find", "good", "nonsense"] to a single string argument
    result = runner.invoke(app, ["find", "nonsense"])

    assert result.exit_code == 0
    # Updated to match the new Epic 3 failure string
    assert "No results found for 'nonsense'" in result.stdout


def test_cli_find_success(mock_get_path: MagicMock, mock_index_file: Path) -> None:
    """
    Test 'find' successfully formats and outputs the ranked results table using BM25.
    """
    mock_get_path.return_value = mock_index_file
    # Let's test passing the new Strategy Enum through Typer!
    result = runner.invoke(app, ["find", "good", "--strategy", "bm25"])

    assert result.exit_code == 0
    assert "matching documents for 'good'" in result.stdout
    assert "page_1_quote_0" in result.stdout
    assert "Rank 1" in result.stdout


# ==========================================
# TEST PATH RESOLUTION
# ==========================================

@patch("src.main.typer.get_app_dir")
def test_get_index_path(mock_get_app_dir: MagicMock, tmp_path: Path) -> None:
    """Test that the index path is correctly resolved and directories are created."""
    mock_get_app_dir.return_value = str(tmp_path / "app_dir")

    from src.main import get_index_path
    path = get_index_path()

    assert path.parent.exists()
    assert path.name == "index.json"
    assert str(tmp_path) in str(path)
