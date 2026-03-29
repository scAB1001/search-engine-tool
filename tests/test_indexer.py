import pytest

from src.indexer import InvertedIndex


def test_text_normalization() -> None:
    """Test that punctuation is removed and text is lowercased."""
    index = InvertedIndex()
    tokens = index._tokenize("Hello, World! It's a 'good' day.")

    # Notice that "It's" is now mathematically split into "it" and "s"
    assert tokens == ["hello", "world", "it", "s", "a", "good", "day"]


def test_tf_idf_calculation() -> None:
    """Test that TF and IDF are calculated correctly across multiple documents."""
    index = InvertedIndex()

    # Add two documents. "Thinking" appears in doc_1 twice, and doc_2 zero times.
    # "Our" appears in both.
    index.add_document("doc_1", "Our thinking, our thinking.")
    index.add_document("doc_2", "Our choices.")

    index.build_index()

    # 'thinking' is in 1 out of 2 docs. IDF = ln(2/1) = 0.693...
    assert "thinking" in index.index
    assert index.index["thinking"]["idf"] > 0.0

    # TF for 'thinking' in doc_1: 2 occurrences / 4 total words = 0.5
    assert index.index["thinking"]["postings"]["doc_1"]["tf"] == 0.5
    assert index.index["thinking"]["postings"]["doc_1"]["positions"] == [1, 3]

    # 'our' is in both docs. IDF = ln(2/2) = 0.0
    assert index.index["our"]["idf"] == 0.0


def test_save_and_load_index(tmp_path: pytest.TempPathFactory) -> None:
    """Test that the index can be accurately serialized and deserialized to JSON."""
    # tmp_path is a built-in Pytest fixture that creates a temporary directory
    temp_file = tmp_path / "test_index.json"  # type: ignore

    original_index = InvertedIndex()
    original_index.add_document("doc_1", "Save me to disk.")
    original_index.build_index()
    original_index.save(str(temp_file))

    # Load it into a completely new instance
    loaded_index = InvertedIndex()
    loaded_index.load(str(temp_file))

    assert loaded_index.total_documents == 1
    assert "disk" in loaded_index.index
    assert loaded_index.index["disk"]["postings"]["doc_1"]["positions"] == [3]


def test_load_missing_index_file() -> None:
    """
    Test that loading a non-existent index file triggers the exception handler.
    """
    index = InvertedIndex()

    # We assert that executing the code inside this block WILL raise this specific error
    with pytest.raises(FileNotFoundError):
        index.load("path/to/absolute/nowhere.json")
