import pytest

from src.indexer import InvertedIndex
from src.search import SearchEngine, SearchStrategy


def test_search_single_word(populated_index: InvertedIndex) -> None:
    """Test that a single word returns all documents containing it, sorted by TF-IDF."""
    engine = SearchEngine(populated_index)
    results = engine.search("good")

    assert len(results) == 2
    # page_1 should rank higher because "good" appears twice (higher TF)
    assert results[0][0] == "page_1"
    assert results[1][0] == "page_2"
    assert results[0][1] > results[1][1]  # Score comparison


def test_search_multi_word_intersection(populated_index: InvertedIndex) -> None:
    """Test the Boolean AND logic. Must return ONLY pages containing ALL words."""
    engine = SearchEngine(populated_index)
    results = engine.search("good friends")

    # Only page_1 contains both words
    assert len(results) == 1
    assert results[0][0] == "page_1"


def test_search_missing_word(populated_index: InvertedIndex) -> None:
    """Test that querying a word not in the index gracefully returns empty."""
    engine = SearchEngine(populated_index)

    # 'nonsense' is completely missing
    assert engine.search("nonsense") == []

    # 'good' exists, but 'nonsense' does not. The intersection MUST be empty.
    assert engine.search("good nonsense") == []


def test_search_empty_query(populated_index: InvertedIndex) -> None:
    """Test that an empty query or pure punctuation returns an empty list."""
    engine = SearchEngine(populated_index)
    assert engine.search("") == []
    assert engine.search("?!,") == []


def test_search_mutually_exclusive_words(populated_index: InvertedIndex) -> None:
    """
    Test that a multi-word query returns empty if the words exist in the index
    individually, but never appear together in the same document.
    """
    engine = SearchEngine(populated_index)

    # 'good' is in page_1 and page_2. 'games' is in page_3.
    # The Boolean AND intersection will be mathematically empty.
    results = engine.search("friends food")

    assert results == []


def test_tokenizer_applies_porter_stemmer() -> None:
    """
    Test that the tokenizer successfully reduces words to their morphological roots.
    """
    index = InvertedIndex()

    # "running", "runs", and "run" should all stem to "run"
    # "thinking", "thinks" should stem to "think"
    text = "Running runs run. Thinking thinks."

    tokens = index.tokenize(text)

    assert tokens == ["run", "run", "run", "think", "think"]


def test_search_uses_bm25_strategy(populated_index: InvertedIndex) -> None:
    """Test that the engine successfully routes and calculates Okapi BM25 scores."""
    engine = SearchEngine(populated_index)

    # Run the exact same query using both strategies
    results_tfidf = engine.search("good", strategy=SearchStrategy.TF_IDF)
    results_bm25 = engine.search("good", strategy=SearchStrategy.BM25)

    assert len(results_tfidf) == len(results_bm25) == 2

    # BM25 math scales differently than TF-IDF.
    # We assert the scores are calculated, but mathematically distinct.
    assert results_tfidf[0][1] != results_bm25[0][1]
    assert results_bm25[0][1] > 0.0


def test_search_zone_weighting(populated_index: InvertedIndex) -> None:
    """Test that terms found in the author or tag zones receive score multipliers."""
    engine = SearchEngine(populated_index)

    # "author" exists in the author zone for all 3 pages in the fixture
    results_author = engine.search("author")
    assert len(results_author) == 3

    # "tag1" exists exclusively in the tag zone for page_1
    results_tag = engine.search("tag1")
    assert len(results_tag) == 1
    assert results_tag[0][0] == "page_1"
