from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from src.crawler import PoliteCrawler
from src.indexer import InvertedIndex
from src.search import SearchEngine

app = typer.Typer(help="Search Engine Tool for quotes.toscrape.com")
console = Console()

APP_NAME = "search-engine-tool"


def get_index_path() -> Path:
    """Returns the secure, OS-specific path to the index file."""
    app_dir = typer.get_app_dir(APP_NAME)
    path = Path(app_dir) / "index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@app.command()
def build(
    max_pages: int = typer.Option(
        0,
        "--max-pages",
        "-m",
        help="Maximum number of pages to crawl (0 for unlimited)."
    )
) -> None:
    """Crawls the website, builds the TF-IDF index, and saves it to disk."""
    crawler = PoliteCrawler()
    index = InvertedIndex()

    current_url = "https://quotes.toscrape.com/"
    page_num = 1

    with console.status("[bold green]Crawling quotes.toscrape.com...") as status:
        while current_url:
            # boundary management check
            if max_pages > 0 and page_num > max_pages:
                console.print(
                    f"[yellow]Max pages limit ({max_pages}) reached. "
                    f"Stopping crawl.[/yellow]")
                break

            status.update(
                f"[bold green]Scraping page {page_num}: {current_url}...")

            result = crawler.fetch_quotes(current_url)
            quotes_List = result.get("quotes", [])
            next_page = result.get("next_page")

            if not quotes_List:
                console.print(
                    f"[yellow]No quotes found on {current_url}. "
                    f"Crawl complete.[/yellow]")
                break

            for i, quote in enumerate(quotes_List):
                doc_id = f"page_{page_num}_quote_{i}"
                text = quote.get("text", "")
                author = quote.get("author", "")
                tags = " ".join(quote.get("tags", []))

                combined_text = f"{text} {author} {tags}"
                index.add_document(doc_id, combined_text)

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


@app.command()
def load() -> None:
    """Loads the index from the file system to verify integrity."""
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


@app.command("print")
def print_word(word: str) -> None:
    """Prints the inverted index statistics for a particular word."""
    path = get_index_path()
    if not path.exists():
        console.print(
            "[bold red]Error: Index file not found. Run 'build' first.[/bold red]")
        raise typer.Exit(code=1)

    index = InvertedIndex()
    index.load(str(path))

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
    path = get_index_path()
    if not path.exists():
        console.print(
            "[bold red]Error: Index file not found. Run 'build' first.[/bold red]")
        raise typer.Exit(code=1)

    index = InvertedIndex()
    index.load(str(path))
    engine = SearchEngine(index)

    full_query = " ".join(query)
    results = engine.search(full_query)

    if not results:
        console.print(
            f"[yellow]No documents found containing all words in: "
            f"'{full_query}'[/yellow]"
        )
        return

    console.print(
        f"\n[bold green]Found {len(results)} matching documents for "
        f"'{full_query}':[/bold green]"
    )
    table = Table("Rank", "Document ID", "TF-IDF Score")
    for i, (doc_id, score) in enumerate(results, 1):
        table.add_row(str(i), doc_id, f"{score:.4f}")
    console.print(table)
    print("\n")


if __name__ == "__main__":
    app()
