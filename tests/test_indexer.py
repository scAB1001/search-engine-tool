import math

import pytest

from src.indexer import InvertedIndex


def test_text_normalization() -> None:
    """Test that punctuation is removed and text is lowercased."""
    index = InvertedIndex()
    tokens = index.tokenize("Hello, World! It's a 'good' day.")

    # Notice that "It's" is now mathematically split into "it" and "s"
    assert tokens == ["hello", "world", "it", "s", "a", "good", "day"]


def test_tf_idf_calculation() -> None:
    """Test that TF and IDF are calculated correctly across multiple documents."""
    index = InvertedIndex()

    index.add_document("doc_1", "Our thinking, our thinking.",
                       "Author One", [], "http://url")
    index.add_document("doc_2", "Our choices.", "Author Two", [], "http://url")

    index.build_index()

    assert "think" in index.index
    assert index.index["think"]["idf"] > 0.0

    # TF for 'think' in doc_1: 2 occurrences / 6 total words
    # (4 text + 2 author) = 0.33....
    tf = index.index["think"]["postings"]["doc_1"]["tf"]
    assert math.isclose(tf, 0.333, abs_tol=0.01)

    assert index.index["our"]["idf"] == 0.0


def test_save_and_load_index(tmp_path) -> None:
    """Test that the index and document registry serialize and deserialize correctly."""
    index = InvertedIndex()
    index.add_document("doc_1", "Save this to disk.",
                       "Albert", ["tech"], "http://url")
    index.build_index()

    filepath = tmp_path / "test_index.json"
    index.save(str(filepath))

    loaded_index = InvertedIndex()
    loaded_index.load(str(filepath))

    # Test the index transferred
    assert "disk" in loaded_index.index
    assert "albert" in loaded_index.index
    assert loaded_index.total_documents == 1

    # NEW: Test the document registry transferred!
    assert "doc_1" in loaded_index.document_registry
    assert loaded_index.document_registry["doc_1"]["author"] == "Albert"
    assert loaded_index.document_registry["doc_1"]["url"] == "http://url"


def test_load_missing_index_file() -> None:
    """
    Test that loading a non-existent index file triggers the exception handler.
    """
    index = InvertedIndex()

    # We assert that executing the code inside this block WILL raise this specific error
    with pytest.raises(FileNotFoundError):
        index.load("path/to/absolute/nowhere.json")


def test_add_document_stores_stemmed_tokens() -> None:
    """Test that documents are added using their stemmed vocabulary."""
    index = InvertedIndex()
    # Pass the required arguments: doc_id, text, author, tags, url
    index.add_document("doc_1", "The engineer is engineering.",
                       "Albert", ["science"], "http://url")

    assert "engin" in index.index
    assert len(index.index["engin"]["postings"]["doc_1"]["positions"]) == 2
    assert "author" in index.index["albert"]["postings"]["doc_1"]["zones"]
