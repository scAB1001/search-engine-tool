[![CI](https://github.com/scAB1001/search-engine-tool/actions/workflows/ci.yaml/badge.svg?branch=main)](https://github.com/scAB1001/search-engine-tool/actions/workflows/ci.yaml)
[![codecov](https://codecov.io/gh/scAB1001/search-engine-tool/graph/badge.svg?token=919TUQ3FW1)](https://codecov.io/gh/scAB1001/search-engine-tool)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/downloads/release/python-3120/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com)

# Search Engine Tool (COMP3011)

![Search Engine Demonstration](docs/comp3011_cwk2_core_demo.gif)

**BSc Computer Science — COMP3011 Web Services and Web Data, Coursework 2**
**University of Leeds, School of Computing, 2025/26**

---

## 📖 Project Overview and Purpose

This project is an elite, production-grade CLI Search Engine built for the COMP3011 module. It is designed to crawl [quotes.toscrape.com](https://quotes.toscrape.com/), construct a mathematical inverted index, and rank search results using industry-standard Information Retrieval algorithms.

**Key Architectural Features:**
* **Ranking Algorithms:** Fully implements **TF-IDF** and **Okapi BM25** scoring models.
* **Advanced NLP:** Uses the **Porter Stemming Algorithm** for morphological tokenisation and provides stem-aware hit highlighting in the CLI.
* **Contextual Extents (Zones):** Applies weight multipliers based on where a term is found (e.g., higher relevance for Author matches vs. Text matches).
* **Ethical Web Crawling:** Strictly enforces a 6-second politeness window with dynamic jitter to prevent server overload.
* **DevOps & UI Polish:** Features a beautiful `Rich` terminal UI, dynamic `TAB` autocompletion for index keys, programmatic XML Sitemap generation via HTTP `HEAD` requests, and 100% test coverage.

### robots.txt compliance

The crawler respects a 6‑second politeness window with jitter but does not parse robots.txt because quotes.toscrape.com is a dedicated training site with no restrictive directives. In a production system, a robots.txt parser would be implemented.

---

## 📂 Structure and Architecture

```bash
search-engine-tool/
├── .github/                 # CI/CD workflows, Codecov integration, and PR templates
├── data/                    # Local storage for the compiled JSON index and XML sitemap
├── src/                     # Core Application Logic
│   ├── crawler.py           # Handles HTTP requests, LXML parsing, and strict rate-limiting
│   ├── indexer.py           # Tokenises text (Porter Stemmer) and maps the inverted index
│   ├── search.py            # Executes DAAT queries against the index (TF-IDF/BM25)
│   ├── logger.py            # Centralised logging configuration
│   └── main.py              # Typer CLI entrypoint with Rich UI and Autocompletion
├── tests/                   # 100% Coverage Test Suite
│   ├── conftest.py          # Centralised Pytest fixtures and mocked data payloads
│   ├── test_crawler.py      # Validates politeness window and network exception handling
│   ├── test_indexer.py      # Validates mathematical frequencies and index structures
│   ├── test_search.py       # Validates scoring algorithms and Boolean intersections
│   └── test_main.py         # Validates CLI routing, edge cases, and UI outputs
├── .pre-commit-config.yaml  # Local "Shift-Left" quality gates (Ruff, Mypy)
├── pyproject.toml           # `uv` project dependencies and metadata
└── README.md                # Project documentation
```

---

## 📦 Dependencies and Installation

This project uses [uv](https://github.com/astral-sh/uv) as its package and environment manager for extremely fast, deterministic builds.

**Core Dependencies:**
* `typer` & `rich`: CLI interface and terminal UI formatting.
* `requests` & `beautifulsoup4` & `lxml`: HTML fetching and parsing.
* `nltk`: Natural Language Toolkit (specifically the PorterStemmer).

### Setup Instructions

**Clone the repository:**
```bash
  git clone https://github.com/scAB1001/search-engine-tool.git
  cd search-engine-tool
```

**Install and Update Dependencies:**
```bash
  # Sync the dependencies from the lock file
  uv sync --all-groups

  # Update/install any dependencies
  uv run pre-commit install
  uv run pre-commit autoupdate

  # Regenerate Lock file
  uv lock --upgrade
  uv lock --check

  # Export requirements
  uv export --format requirements.txt --output-file requirements.txt
```

#### Run within the virtual environment (for development)

**Install dependencies and the CLI executable natively:**
```bash
  uv pip install -e .
```

*Note: Installing with `-e .` links the `search-engine` command directly to your virtual environment.*

**Activate the Virtual Environment:**
```bash
  source .venv/bin/activate
```

#### Run from any environment (for production LTS)

**Install dependencies and the CLI executable globally:**
```bash
  uv tool install .
```

*Tip: If you make any changes, run the command with `-n --reinstall'. to skip cache.*

#### Enable Dynamic Autocompletion (Optional but recommended)

```bash
  search-engine --install-completion
  source ~/.bashrc  # Or ~/.zshrc depending on your shell
```

---

## 🚀 Usage Examples

The CLI is divided into Database Operations, Search Operations, and Utilities. You can run `search-engine --help` at any time for a global interactive menu.

### 1. Build the Index (`build`)

Crawls the target website, processes the text, calculates global term frequencies, and serialises the inverted index to disk.
```bash
  search-engine build

  # Or, limit the crawl to a specific number of pages:
  search-engine build --max-pages 3
```

*Bonus Feature:* Specify how many pages you would like to crawl with `--max-pages`.

### 2. Verify the Index (`load`)

Loads the index into memory to verify data integrity and file structure.
```bash
  search-engine load
```

### 3. Inspect Term Statistics (`print`)

Outputs the global Collection Frequency, Base IDF score, and a tabular breakdown of Term Frequencies and positional extents across all documents containing the word.

```bash
  search-engine print einstein

  # Try autocomplete
  search-engine print ein[TAB]
```

*Bonus Feature*: Press `TAB` after typing part of your search term to see auto-completed suggestions from your database!

### 4. Search the Index (`find`)

Executes a multi-word query against the index. Returns beautifully formatted Rich panels with contextual snippets, hit highlighting, and author metadata.

```bash
  # Default TF-IDF search:
  search-engine find good friends

  # Advanced Okapi BM25 search:
  search-engine find Einstein thinking --strategy bm25
```

*Bonus Feature*: Specify the index method to use with `--strategy`. Leave either the default (TF-IDF) or choose the alternative (BM25)

### 5. Generate a Sitemap (`sitemap`)

*Bonus Feature:* Dynamically generates a `sitemaps.org/0.9` compliant XML file by pinging HTTP `HEAD` requests to verify live `Last-Modified` headers, alongside heuristic URL depth prioritisation.

```bash
  # Generates and saves the sitemap XML to dir/
  search-engine sitemap --output sitemap.xml

  # Display the latest sitemap in dir/ as a table
  search-engine show-sitemap

  # Display a specified sitemap XML in dir/
  search-engine show-sitemap -f sitemap.xml
```

---

## 🧪 Testing Instructions

This project strictly enforces an **80% test coverage** requirement across all statements and branches.
All outbound HTTP requests are fully mocked; tests will not hit live servers.

*Note: `uv run` can be omitted if executing withing the virtual environment.*

**Run the standard test suite:**
```bash
uv run pytest
```

**Run tests with the detailed coverage report:**
```bash
uv run pytest -v --cov=src
```

**Run local linting and type-checking (Ruff & Mypy):**
```bash
uv run pre-commit run --all-files
```

## License

This repository contains coursework submitted for academic assessment at the University of Leeds. All rights reserved. Reproduction or reuse of any component without written permission is not permitted.
