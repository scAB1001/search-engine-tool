import pytest

from src.indexer import InvertedIndex
from src.search import SearchEngine


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
