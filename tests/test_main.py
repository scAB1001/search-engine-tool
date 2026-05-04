import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.main import app, complete_word, find_nearest_xml

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
    # Multi-word test without quotes
    result = runner.invoke(app, ["print", "good", "friends"])

    assert result.exit_code == 0
    assert "not found in the index" in result.stdout


def test_cli_print_success(mock_get_path: MagicMock, mock_index_file: Path) -> None:
    """Test 'print' successfully formats and outputs the stats table."""
    mock_get_path.return_value = mock_index_file
    result = runner.invoke(app, ["print", "good"])

    assert result.exit_code == 0
    # Changed to match the exact string your CLI outputs
    assert "Base Score" in result.stdout
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
    result = runner.invoke(app, ["find", "nonsense"])

    assert result.exit_code == 0
    assert "No results found for 'nonsense'" in result.stdout


def test_cli_find_success(mock_get_path: MagicMock, mock_index_file: Path) -> None:
    """
    Test 'find' successfully formats and outputs the ranked results table using BM25.
    """
    mock_get_path.return_value = mock_index_file

    # Reverted to searching only for "good" since it is the only word in the mock DB
    result = runner.invoke(app, ["find", "good", "--strategy", "bm25"])

    assert result.exit_code == 0
    assert "matching document(s) for good" in result.stdout
    assert "page_1_quote_0" in result.stdout
    assert "(BM25)" in result.stdout


# ==========================================
# TEST COMMAND: SITEMAP
# ==========================================

def test_cli_sitemap_without_index(mock_get_path: MagicMock, tmp_path: Path) -> None:
    """Test 'sitemap' aborts if index is missing."""
    mock_get_path.return_value = tmp_path / "missing.json"
    result = runner.invoke(app, ["sitemap"])
    assert result.exit_code == 1


@patch("src.main.requests.head")
def test_cli_sitemap_success_with_header(
    mock_head: MagicMock,
    mock_get_path: MagicMock,
    mock_index_file: Path,
    tmp_path: Path
) -> None:
    """Test 'sitemap' correctly parses an active Last-Modified HTTP header."""
    mock_get_path.return_value = mock_index_file

    # Mock a successful HEAD request with a valid HTTP-Date
    mock_response = MagicMock()
    mock_response.headers = {"Last-Modified": "Wed, 21 Oct 2015 07:28:00 GMT"}
    mock_head.return_value = mock_response

    output_file = tmp_path / "sitemap.xml"
    result = runner.invoke(app, ["sitemap", "--output", str(output_file)])

    assert result.exit_code == 0
    assert "Professional Sitemap generated" in result.stdout
    assert output_file.exists()

    xml_content = output_file.read_text()
    assert "<loc>http://test</loc>" in xml_content
    # Verifies the email.utils parsedate logic correctly converted it to ISO 8601
    assert "<lastmod>2015-10-21</lastmod>" in xml_content
    assert "<priority>1.0</priority>" in xml_content


@patch("src.main.requests.head")
def test_cli_sitemap_fallback_on_network_error(
    mock_head: MagicMock,
    mock_get_path: MagicMock,
    mock_index_file: Path,
    tmp_path: Path
) -> None:
    """Test 'sitemap' falls back to the current date if the network fails."""
    mock_get_path.return_value = mock_index_file

    import requests
    mock_head.side_effect = requests.RequestException("Network Error")

    output_file = tmp_path / "sitemap.xml"
    result = runner.invoke(app, ["sitemap", "--output", str(output_file)])

    assert result.exit_code == 0

    xml_content = output_file.read_text()
    # It shouldn't crash; it should just write the file with today's date
    assert "<loc>http://test</loc>" in xml_content
    assert "<lastmod>" in xml_content


def test_cli_sitemap_no_urls(mock_get_path: MagicMock, empty_index_file: Path) -> None:
    """Test 'sitemap' exits gracefully if the registry is empty."""
    # Uses the new conftest fixture!
    mock_get_path.return_value = empty_index_file

    result = runner.invoke(app, ["sitemap"])
    assert result.exit_code == 0
    assert "No URLs found" in result.stdout


@patch("src.main.requests.head")
def test_cli_sitemap_depths_and_missing_header(
    mock_head: MagicMock,
    mock_get_path: MagicMock,
    multi_url_index_file: Path,
    tmp_path: Path
) -> None:
    """Test URL depth prioritization and header fallback logic."""
    # Uses the new conftest fixture!
    mock_get_path.return_value = multi_url_index_file

    mock_response = MagicMock()
    mock_response.headers = {}
    mock_head.return_value = mock_response

    output_file = tmp_path / "sitemap.xml"
    result = runner.invoke(app, ["sitemap", "--output", str(output_file)])

    assert result.exit_code == 0

    xml_content = output_file.read_text()
    assert "<priority>1.0</priority>" in xml_content
    assert "<priority>0.8</priority>" in xml_content
    assert "<priority>0.5</priority>" in xml_content


@patch("src.main.requests.head")
def test_cli_sitemap_relative_path(
    mock_head: MagicMock,
    mock_get_path: MagicMock,
    mock_index_file: Path,
    monkeypatch,
    tmp_path: Path
) -> None:
    """Test 'sitemap' correctly routes relative output paths into a data/ directory."""
    mock_get_path.return_value = mock_index_file

    mock_response = MagicMock()
    mock_response.headers = {}
    mock_head.return_value = mock_response

    # Prevents the test from creating a real 'data' folder in your actual project root!
    monkeypatch.chdir(tmp_path)

    # Pass a RELATIVE string path rather than an absolute Path object
    result = runner.invoke(app, ["sitemap", "--output", "custom_sitemap.xml"])

    assert result.exit_code == 0

    # Verify the code correctly prepended 'data/' and created the folder
    expected_path = tmp_path / "data" / "custom_sitemap.xml"
    assert expected_path.exists()
    assert "<loc>http://test</loc>" in expected_path.read_text()

# ==========================================
# TEST COMMAND: SHOW_SITEMAP
# ==========================================

def test_find_nearest_xml_empty_dir(tmp_path: Path) -> None:
    """Test find_nearest_xml returns None when directory is empty or missing."""
    assert find_nearest_xml(tmp_path / "nonexistent") is None

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    assert find_nearest_xml(empty_dir) is None


def test_find_nearest_xml_returns_latest(tmp_path: Path) -> None:
    """Test find_nearest_xml returns the most recently modified .xml file."""
    import time

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    old_file = data_dir / "old.xml"
    old_file.write_text("<root/>")
    old_time = time.time() - 100
    os.utime(old_file, (old_time, old_time))

    new_file = data_dir / "new.xml"
    new_file.write_text("<root/>")

    result = find_nearest_xml(data_dir)
    assert result == new_file

    # Should ignore non-xml files
    (data_dir / "other.txt").write_text("text")
    result2 = find_nearest_xml(data_dir)
    assert result2 == new_file


def test_cli_show_sitemap_no_file_no_sitemap(monkeypatch, tmp_path: Path) -> None:
    """Test show-sitemap fails when no .xml file exists in data/."""
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    result = runner.invoke(app, ["show-sitemap"])
    assert result.exit_code == 1


def test_cli_show_sitemap_auto_finds_latest(monkeypatch, tmp_path: Path) -> None:
    """Test show-sitemap automatically finds and displays the latest sitemap."""
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    sitemap_path = data_dir / "sitemap.xml"
    sitemap_path.write_text('''<?xml version="1.0" ?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://quotes.toscrape.com/</loc>
    <lastmod>2026-05-04</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>''')

    result = runner.invoke(app, ["show-sitemap"])
    assert result.exit_code == 0
    assert "Sitemap: sitemap.xml" in result.stdout
    # Check the domain name (not the full URL) as Rich may add hyperlinks/ANSI codes
    assert "2026-05-04" in result.stdout
    assert "daily" in result.stdout
    assert "1.0" in result.stdout


def test_cli_show_sitemap_with_explicit_file(monkeypatch, tmp_path: Path) -> None:
    """Test show-sitemap --file displays a specific sitemap file."""
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    sitemap_path = data_dir / "custom.xml"
    sitemap_path.write_text('''<?xml version="1.0" ?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/</loc>
    <lastmod>2025-01-01</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
</urlset>''')

    result = runner.invoke(app, ["show-sitemap", "--file", "custom.xml"])
    assert result.exit_code == 0
    assert "Sitemap: custom.xml" in result.stdout
    assert "https://example.com/" in result.stdout
    assert "2025-01-01" in result.stdout
    assert "monthly" in result.stdout
    assert "0.5" in result.stdout


def test_cli_show_sitemap_with_nonexistent_file(monkeypatch, tmp_path: Path) -> None:
    """Test show-sitemap with a file that doesn't exist in data/."""
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    result = runner.invoke(app, ["show-sitemap", "--file", "missing.xml"])
    assert result.exit_code == 1
    expected_path = str(Path("data") / "missing.xml")
    assert f"Error: Sitemap file not found at {expected_path}" in result.stdout


def test_cli_show_sitemap_no_urls(monkeypatch, tmp_path: Path) -> None:
    """Test show-sitemap displays a warning when the sitemap has no <url> elements."""
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    empty_sitemap = data_dir / "empty.xml"
    empty_sitemap.write_text('''<?xml version="1.0" ?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
</urlset>''')

    result = runner.invoke(app, ["show-sitemap", "--file", "empty.xml"])
    assert result.exit_code == 0
    assert "No <url> elements found in the sitemap." in result.stdout


def test_cli_show_sitemap_xml_parse_error(monkeypatch, tmp_path: Path) -> None:
    """Test show-sitemap handles XML parse errors gracefully."""
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    broken_sitemap = data_dir / "broken.xml"
    broken_sitemap.write_text("This is not XML at all")

    result = runner.invoke(app, ["show-sitemap", "--file", "broken.xml"])
    assert result.exit_code == 1
    assert "XML Parse Error" in result.stdout


def test_cli_show_sitemap_general_exception(monkeypatch, tmp_path: Path) -> None:
    """Test show-sitemap catches general exceptions (e.g., file read error)."""
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    sitemap_path = data_dir / "valid.xml"
    sitemap_path.write_text("<urlset/>")

    # Force an exception during parsing by mocking ET.parse
    with patch("xml.etree.ElementTree.parse",
               side_effect=RuntimeError("Simulated crash")):
        result = runner.invoke(app, ["show-sitemap", "--file", "valid.xml"])
        assert result.exit_code == 1
        assert "Unexpected error" in result.stdout
        assert "Simulated crash" in result.stdout


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


# ==========================================
# TEST CLI HELP AND WELCOME PANEL
# ==========================================

def test_cli_base_command_shows_welcome_panel() -> None:
    """Test that calling the app without a subcommand triggers the welcome panel."""
    # Invoke the app with no arguments
    result = runner.invoke(app, [])

    assert result.exit_code == 0
    # Check for the specific version/title string in the Rich Panel
    assert "Search Engine CLI" in result.stdout
    assert "Run --help to see available commands" in result.stdout


def test_cli_help_shows_rich_docstring() -> None:
    """Test that the global help shows our custom docstring with Rich markup."""
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    # Check that our specific callback docstring is rendered
    assert "Built with ❤️  by Andreas for COMP3011" in result.stdout
    assert "Okapi BM25" in result.stdout
    assert "Database Operations" in result.stdout  # Verifies Help Panels exist


def test_complete_word_success(mock_index_file: Path, monkeypatch) -> None:
    """Test that autocompletion returns matching words from the index."""
    # We need to ensure get_index_path points to our mock file
    # during the autocompletion call.
    from src import main
    monkeypatch.setattr(main, "get_index_path", lambda: mock_index_file)

    # If 'good' is in your mock_index_file
    suggestions = complete_word("go")
    assert "good" in suggestions

    # Test case-insensitivity and non-matches
    assert len(complete_word("xyz")) == 0


def test_complete_word_no_index(tmp_path: Path, monkeypatch) -> None:
    """Test autocompletion handles missing index gracefully."""
    from src import main
    missing_path = tmp_path / "nowhere.json"
    monkeypatch.setattr(main, "get_index_path", lambda: missing_path)

    suggestions = complete_word("any")
    assert suggestions == []
