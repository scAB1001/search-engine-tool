import json
import math
import re
from typing import Any

from src.logger import logger

# TODO: IMplement network error handling

class InvertedIndex:
    """
    An advanced Inverted Index implementing TF-IDF scoring for optimal search relevance.
    """

    def __init__(self) -> None:
        # Schema: {
        #   word: {
        #       "idf": float, "postings": {
        #           doc_id: {
        #               "tf": float,
        #               "positions": [int]
        #           }
        #       }
        #   }
        # }
        self.index: dict[str, dict[str, Any]] = {}
        self.total_documents: int = 0

        # Temporary storage during the crawl phase before TF-IDF is finalized
        self._raw_documents: dict[str, list[str]] = {}

    def _tokenize(self, text: str) -> list[str]:
        """
        Cleans text by removing punctuation and converting to lowercase.
        Case sensitivity requirement: 'Good' == 'good'.
        """
        text = text.lower()
        # Remove anything that isn't a letter or number (strips punctuation)
        text = re.sub(r'[^a-z0-9\s]', '', text)
        # Split by whitespace and remove empty strings
        return [word for word in text.split() if word]

    def add_document(self, doc_id: str, text: str) -> None:
        """Processes a raw document and stores its tokens and positions."""
        tokens = self._tokenize(text)
        self._raw_documents[doc_id] = tokens
        self.total_documents += 1

        for position, token in enumerate(tokens):
            if token not in self.index:
                self.index[token] = {"idf": 0.0, "postings": {}}

            if doc_id not in self.index[token]["postings"]:
                self.index[token]["postings"][doc_id] = {
                    "tf": 0.0, "positions": []}

            self.index[token]["postings"][doc_id]["positions"].append(position)

    def build_index(self) -> None:
        """
        Finalizes the index by calculating the TF and IDF scores for all tokens.
        This must be called after all documents have been added.
        """
        logger.info(
            f"Calculating TF-IDF scores for {self.total_documents} documents...")

        # TODO: Use token
        for token, data in self.index.items():
            # 1. Calculate IDF (Inverse Document Frequency)
            doc_frequency = len(data["postings"])
            data["idf"] = math.log(self.total_documents / doc_frequency)

            print(token)

            # 2. Calculate TF (Term Frequency) for each document
            for doc_id, posting in data["postings"].items():
                term_count = len(posting["positions"])
                total_words_in_doc = len(self._raw_documents[doc_id])
                posting["tf"] = term_count / total_words_in_doc

        # Clear raw documents to free memory since the index is complete
        self._raw_documents.clear()
        logger.info(
            f"Index built successfully with {len(self.index)} unique terms.")

    def save(self, filepath: str) -> None:
        """Serializes the index to a JSON file."""
        export_data = {
            "metadata": {"total_documents": self.total_documents},
            "index": self.index
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
        logger.info(f"Index successfully saved to {filepath}")

    def load(self, filepath: str) -> None:
        """Deserializes the index from a JSON file."""
        try:
            with open(filepath, encoding='utf-8') as f:
                import_data = json.load(f)
                self.total_documents = import_data["metadata"]["total_documents"]
                self.index = import_data["index"]
            logger.info(
                f"Loaded index from {filepath} ({self.total_documents} documents).")
        except FileNotFoundError:
            logger.error(
                f"Index file not found at {filepath}. Please run 'build' first.")
            raise
