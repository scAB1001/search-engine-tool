import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse
from xml.dom import minidom

import requests
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.crawler import PoliteCrawler
from src.indexer import InvertedIndex
from src.search import SearchEngine, SearchStrategy

app = typer.Typer(
    help="[bold cyan]Quotes Search Engine[/bold cyan] - COMP3011 Coursework 2.",
    rich_markup_mode="rich",
    epilog="Built with :red_heart-emoji:  by Andreas for COMP3011",
)

console = Console()

APP_NAME = "search-engine-tool"


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """
    [bold green]Welcome to the Quote Search Engine Tool.[/bold green]

    This tool crawls, indexes, and ranks quotes using industry-standard
    algorithms like [yellow]TF-IDF[/yellow] and [yellow]Okapi BM25[/yellow].
    """
    if ctx.invoked_subcommand is None:
        console.print(Panel(
            "[bold cyan]Search Engine CLI v3.0[/bold cyan]\n"
            "Run [green]--help[/green] to see available commands.",
            expand=False
        ))


def get_index_path() -> Path:
    """Returns the secure, OS-specific path to the index file."""
    app_dir = typer.get_app_dir(APP_NAME)
    path = Path(app_dir) / "index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@app.command(rich_help_panel="Database Operations")
def build(
    max_pages: int = typer.Option(
        0,
        "--max-pages",
        "-m",
        help="Maximum number of pages to crawl (0 for unlimited)."
    )
) -> None:
    """[green]Crawl[/green] the website and build the index."""
    crawler = PoliteCrawler()
    index = InvertedIndex()

    current_url = "https://quotes.toscrape.com/"
    page_num = 1

    with console.status(
        "[bold green]Crawling quotes.toscrape.com...",
        spinner="dots12"
    ) as status:
        while current_url:
            # boundary management check
            if max_pages > 0 and page_num > max_pages:
                console.print(
                    f"[yellow]Max pages limit ({max_pages}) reached. "
                    f"Stopping crawl.[/yellow]")
                break

            status.update(
                f"[bold green]Scraping page {page_num}[/bold green] "
                f"| [dim]{current_url}[/dim]")

            result = crawler.fetch_quotes(current_url)
            quotes_list = result.get("quotes", [])
            next_page = result.get("next_page")

            if not quotes_list:
                console.print(
                    f"[yellow]No quotes found on {current_url}. "
                    f"Crawl complete.[/yellow]")
                break

            for i, quote in enumerate(quotes_list):
                doc_id = f"page_{page_num}_quote_{i}"

                # Pass the raw structured data directly to the indexer!
                index.add_document(
                    doc_id=doc_id,
                    text=quote.get("text", ""),
                    author=quote.get("author", ""),
                    tags=quote.get("tags", []),
                    url=current_url
                )

            if next_page:
                current_url = f"https://quotes.toscrape.com{next_page}"
                page_num += 1
            else:
                current_url = ""

    console.print("[green]Crawl complete. Building TF-IDF index...[/green]")
    index.build_index()

    # Save using the dynamic path!
    save_path = get_index_path()
    index.save(str(save_path))
    console.print(
        f"[bold green]Success![/bold green] Index saved to {save_path}")


@app.command(rich_help_panel="Database Operations")
def load() -> None:
    """[blue]Verify[/blue] the integrity of the saved index."""
    path = get_index_path()
    if not path.exists():
        console.print(
            "[bold red]Error: Index file not found. Run 'build' first.[/bold red]")
        raise typer.Exit(code=1)

    index = InvertedIndex()
    index.load(str(path))
    console.print(
        f"[bold green]Successfully loaded index with "
        f"{index.total_documents} documents in memory.[/bold green]"
    )


def complete_word(incomplete: str) -> list[str]:
    """Dynamically reads the index to suggest words to the user."""
    path = get_index_path()
    if not path.exists():
        return []

    # We only load the keys (words) to keep it fast
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
        words = data.get("index", {}).keys()

    return [word for word in words if word.startswith(incomplete.lower())]

@app.command("print", rich_help_panel="Search Operations")
def print_word(
    words: Annotated[
        list[str],
        typer.Argument(
            help="The word to print stats for.",
            autocompletion=complete_word
        )
    ]
) -> None:
    """[yellow]Inspect[/yellow] specific word inverted index statistics."""
    path = get_index_path()
    if not path.exists():
        console.print(
            "[bold red]Error: Index file not found. Run 'build' first.[/bold red]")
        raise typer.Exit(code=1)

    index = InvertedIndex()
    index.load(str(path))

    # Join the list of words into a single string (handles no-quote terminal inputs)
    word_clean = " ".join(words).lower().strip()

    if word_clean not in index.index:
        console.print(
            f"[yellow]Word '{word_clean}' not found in the index.[/yellow]")
        return

    data = index.index[word_clean]

    console.print(f"\n[bold cyan]Word:[/bold cyan] {word_clean}")
    console.print(
        f"[bold cyan](TF-IDF/BM25) Base Score:[/bold cyan] {data['idf']:.4f}")
    console.print(
        f"[bold cyan]Collection Frequency:[/bold cyan] "
        f"{data.get('collection_frequency', 0)} occurrences "
        f"across {len(data['postings'])} documents.\n")

    table = Table("Document ID", "Term Frequency (TF)", "Positions", "Author Context")
    for doc_id, stats in data["postings"].items():
        # Fetch the author from the document registry, defaulting to "Unknown"
        author = index.document_registry.get(
            doc_id, {}).get("author", "Unknown")
        table.add_row(doc_id, f"{stats['tf']:.4f}",
                      str(stats["positions"]), author)

    console.print(table)


@app.command(rich_help_panel="Search Operations")
def find(
    query: Annotated[list[str], typer.Argument(help="The search query to execute.")],
    strategy: Annotated[
        SearchStrategy,
        typer.Option("--strategy", "-s",
                     help="The mathematical ranking algorithm to use.")
    ] = SearchStrategy.TF_IDF
) -> None:
    """[magenta]Search[/magenta] loaded index using TF-IDF or Okapi BM25."""
    path = get_index_path()
    if not path.exists():
        console.print(
            "[red]Error: Index not found. Please run 'build' first.[/red]")
        raise typer.Exit(code=1)

    index = InvertedIndex()
    index.load(str(path))
    engine = SearchEngine(index)

    # Join the list of words into a single query string
    query_str = " ".join(query)

    with console.status(f"[bold green]Searching via {strategy.value.upper()}..."):
        results = engine.search(query_str, strategy=strategy)

    if not results:
        console.print(f"[yellow]No results found for '{query_str}'.[/yellow]")
        return

    console.print(
        f"\n[bold green]Found {len(results)} matching documents for "
        f"'{query_str}':[/bold green]\n")

    # Pre-tokenize and stem the query to find what we are looking for
    query_stems = set(index.tokenize(query_str))

    for rank, (doc_id, score) in enumerate(results[:5], 1):
        doc = index.document_registry.get(doc_id, {})
        raw_text = doc.get('text', 'No text available.')

        # Highlight matches in the raw text
        # We split by non-word characters to preserve punctuation but check stems
        words = re.split(r'(\W+)', raw_text)
        highlighted_text = ""

        # Loop over split text: for each word, check its stem against the query stems
        for part in words:
            # If it's a word, check its stem
            if re.match(r'\w+', part):
                stemmed_part = index.stemmer.stem(part.lower())

                # Apply Rich bold/yellow styling to the matched word
                if stemmed_part in query_stems:
                    highlighted_text += f"[bold yellow]{part}[/bold yellow]"
                else:
                    highlighted_text += part
            else:
                # Punctuation or whitespace, append it
                highlighted_text += part

        # Safely extract and format tags
        tags_list = doc.get("tags", [])
        tags_str = ", ".join(tags_list) if tags_list else "None"

        # Construct the content using the highlighted_text
        content = f"[italic]{highlighted_text}[/italic]\n\n"
        content += f"[bold cyan]Author:[/bold cyan]\t{doc.get('author', 'Unknown')}\n"
        content += f"[bold cyan]Tags:[/bold cyan]\t[ {tags_str} ]\n"
        content += "[bold cyan]URL:[/bold cyan]\t"
        content += f"[blue underline]{doc.get('url', '#')}[/blue underline]"

        panel = Panel(
            content,
            title=(
                f"Rank {rank} | Score: {score:.4f} ({strategy.value.upper()}) | "
                f"ID: {doc_id}"
            ),
            title_align="left",
            border_style="green"
        )
        console.print(panel)
        console.print()


@app.command(rich_help_panel="General Utilities")
def sitemap(
    output_file: Annotated[str, typer.Option(
        "--output", "-o", help="The output XML file path.")] = "sitemap.xml"
) -> None:
    """
    [cyan]Sitemap[/cyan] XML generated by dynamically verifying live HTTP headers.
    """
    path = get_index_path()
    if not path.exists():
        console.print(
            "[red]Error: Index not found. Please run 'build' first.[/red]")
        raise typer.Exit(code=1)

    index = InvertedIndex()
    index.load(str(path))

    unique_urls = {doc["url"]
                   for doc in index.document_registry.values() if "url" in doc}
    if not unique_urls:
        console.print(
            "[yellow]No URLs found in the document registry.[/yellow]")
        return

    # Setup the formal XML Namespace
    urlset = ET.Element(
        "urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    # Sort URLs so the homepage is first, followed by paginated routes
    sorted_urls = sorted(
        unique_urls, key=lambda u: (len(urlparse(u).path), u))

    with console.status(
        f"[bold green]Generating sitemap and "
        f"verifying headers for {len(sorted_urls)} URLs..."
    ) as status:
        for url in sorted_urls:
            status.update(f"[bold green]Pinging header for: {url}")

            # 1. Dynamic Priority calculation based on URL depth
            path_str = urlparse(url).path
            if path_str in ("", "/"):
                priority = "1.0"
                changefreq = "daily"
            elif path_str.startswith("/page/"):
                priority = "0.8"
                changefreq = "weekly"
            else:
                priority = "0.5"
                changefreq = "monthly"

            # 2. Call the HTTP header regardless (using a lightweight HEAD request)
            try:
                response = requests.head(url, timeout=5.0)
                last_mod_header = response.headers.get("Last-Modified")

                if last_mod_header:
                    # Convert standard HTTP-date to W3C ISO 8601 Date
                    dt = parsedate_to_datetime(last_mod_header)
                    lastmod = dt.strftime("%Y-%m-%d")
                else:
                    # Fallback to current UTC date if server omits the header
                    lastmod = datetime.now(UTC).strftime("%Y-%m-%d")
            except requests.RequestException:
                # Fallback on network failure
                lastmod = datetime.now(UTC).strftime("%Y-%m-%d")

            # 3. Build the XML node tree
            url_node = ET.SubElement(urlset, "url")
            ET.SubElement(url_node, "loc").text = url
            ET.SubElement(url_node, "lastmod").text = lastmod
            ET.SubElement(url_node, "changefreq").text = changefreq
            ET.SubElement(url_node, "priority").text = priority

            # A 0.1s sleep to avoid hammering the server with rapid-fire HEAD requests
            time.sleep(0.1)

    # 4. Use minidom to pretty-print the XML with proper indents
    xml_str = ET.tostring(urlset, encoding="utf-8")
    parsed_xml = minidom.parseString(xml_str)
    pretty_xml = parsed_xml.toprettyxml(indent="  ")

    # Use Path to intelligently handle absolute vs relative paths
    out_path = Path(output_file)
    if not out_path.is_absolute():
        out_path = Path("data") / out_path

    # Ensure the directory exists before writing
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        # minidom adds its own XML declaration, so we write it directly
        f.write(pretty_xml)

    console.print(
        f"[bold green]Success![/bold green] Professional Sitemap generated at "
        f"[cyan]{out_path}[/cyan]"
    )
