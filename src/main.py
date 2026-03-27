from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from src.crawler import PoliteCrawler
from src.indexer import InvertedIndex
from src.search import SearchEngine

# Initialize the Typer CLI app and the Rich console for beautiful formatting
app = typer.Typer(help="Search Engine Tool for quotes.toscrape.com")
console = Console()

INDEX_FILE = Path("data/index.json")


@app.command()
def build() -> None:
    """Crawls the website, builds the TF-IDF index, and saves it to disk."""
    crawler = PoliteCrawler(delay_seconds=6.0)
    index = InvertedIndex()

    base_url = "https://quotes.toscrape.com/page/{}/"
    page = 1

    console.print(
        "[bold green]Starting politeness-aware crawl...[/bold green]")

    # Ensure the data directory exists [cite: 112-114]
    INDEX_FILE.parent.mkdir(exist_ok=True)

    # Loop through the pagination until we hit a page with no quotes
    while True:
        url = base_url.format(page)
        console.print(f"Scraping {url}...")
        quotes = crawler.fetch_quotes(url)

        if not quotes:
            console.print(
                f"[yellow]No more quotes found on page {page}. \
                    Crawl complete.[/yellow]")
            break

        for i, quote in enumerate(quotes):
            # Create a unique document ID for each quote
            doc_id = f"page_{page}_quote_{i}"
            # Combine text and author to make both searchable
            text = f"{quote['text']} {quote['author']}"
            index.add_document(doc_id, text)

        page += 1

    console.print("[bold blue]Building TF-IDF Index...[/bold blue]")
    index.build_index()
    index.save(str(INDEX_FILE))
    console.print(
        f"[bold green]Successfully saved index to {INDEX_FILE}[/bold green]")


@app.command()
def load() -> None:
    """Loads the index from the file system to verify integrity."""
    if not INDEX_FILE.exists():
        console.print(
            "[bold red]Error: Index file not found. Run 'build' first.[/bold red]")
        raise typer.Exit(code=1)

    index = InvertedIndex()
    index.load(str(INDEX_FILE))
    console.print(
        f"[bold green]Successfully loaded index "
        f"with {index.total_documents} documents in memory.[/bold green]"
    )


@app.command("print")
def print_word(word: str) -> None:
    """Prints the inverted index statistics for a particular word."""
    if not INDEX_FILE.exists():
        console.print(
            "[bold red]Error: Index file not found. Run 'build' first.[/bold red]")
        raise typer.Exit(code=1)

    index = InvertedIndex()
    index.load(str(INDEX_FILE))

    word_clean = word.lower().strip()
    if word_clean not in index.index:
        console.print(
            f"[yellow]Word '{word}' not found in the index.[/yellow]")
        return

    data = index.index[word_clean]
    console.print(f"\n[bold cyan]Word:[/bold cyan] {word_clean}")
    console.print(f"[bold cyan]IDF Score:[/bold cyan] {data['idf']:.4f}")
    console.print(
        f"[bold cyan]Found in {len(data['postings'])} documents.[/bold cyan]\n")

    table = Table("Document ID", "Term Frequency (TF)", "Positions")
    for doc_id, stats in data["postings"].items():
        table.add_row(doc_id, f"{stats['tf']:.4f}", str(stats["positions"]))
    console.print(table)


@app.command()
def find(query: list[str]) -> None:
    """Finds a given query phrase in the index and returns ranked pages."""
    if not INDEX_FILE.exists():
        console.print(
            "[bold red]Error: Index file not found. Run 'build' first.[/bold red]")
        raise typer.Exit(code=1)

    index = InvertedIndex()
    index.load(str(INDEX_FILE))
    engine = SearchEngine(index)

    # Typer captures multi-word arguments as a list, so we join them back into a string
    full_query = " ".join(query)
    results = engine.search(full_query)

    if not results:
        console.print(
            f"[yellow]No documents found containing "
            f"all words in: '{full_query}'[/yellow]"
        )
        return

    console.print(
        f"\n[bold green]Found {len(results)} matching documents "
        f"for '{full_query}':[/bold green]"
    )
    table = Table("Rank", "Document ID", "TF-IDF Score")
    for i, (doc_id, score) in enumerate(results, 1):
        table.add_row(str(i), doc_id, f"{score:.4f}")
    console.print(table)
    print("\n")


if __name__ == "__main__":
    app()
