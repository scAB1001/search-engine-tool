# search-engine-tool

[![CI](https://github.com/scAB1001/search-engine-tool/actions/workflows/ci.yaml/badge.svg?branch=main)](https://github.com/scAB1001/search-engine-tool/actions/workflows/ci.yaml)
[![codecov](https://codecov.io/gh/scAB1001/search-engine-tool/graph/badge.svg?token=919TUQ3FW1)](https://codecov.io/gh/scAB1001/search-engine-tool)

## Project overview and purpose

### Structure and Purpose

```bash
search-engine-tool/
├── .github/workflows/       # CI/CD (Ruff, Mypy, Pytest)
├── src/
│   ├── __init__.py
│   ├── crawler.py           # Handles HTTP requests and the strict 6-second politeness window [cite: 17]
│   ├── indexer.py           # Processes text and builds the inverted index (we'll implement TF-IDF here) [cite: 18, 168]
│   ├── search.py            # Executes queries against the index (handling case-insensitivity) [cite: 19]
│   └── main.py              # The CLI entrypoint (build, load, print, find commands) [cite: 27-36]
├── tests/
│   ├── conftest.py          # Fixtures for mocked HTML responses
│   ├── test_crawler.py      # Validates rate-limiting and error handling [cite: 109, 141]
│   ├── test_indexer.py      # Validates inverted index structure and word statistics [cite: 110, 163]
│   └── test_search.py       # Validates multi-word queries and edge cases [cite: 111, 163]
├── data/
│   └── index.json           # The compiled index file [cite: 112, 114]
├── .pre-commit-config.yaml  # Local "Shift-Left" quality gates
├── pyproject.toml           # uv project configuration
└── README.md                # Comprehensive setup, usage, and architecture documentation [cite: 116-121]
```

A tool to crawl https://quotes.toscrape.com/.
Features include: creating an inverted index of all word occurrences, allow the user to find pages containing certain search terms.

## Installation/setup instructions



## Usage examples for all four commands



## Testing instructions

### 📊 Testing & Coverage Analytics

This project enforces a strict **80% test coverage** requirement. The CI/CD pipeline actively monitors branch health, and test analytics are visualised below via Codecov.

## Any dependencies and how to install them
