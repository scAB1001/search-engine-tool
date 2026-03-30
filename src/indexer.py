import json
import math
import re
from typing import Any

from nltk.stem import PorterStemmer

from src.logger import logger


class InvertedIndex:
    """
    An advanced Inverted Index implementing TF-IDF scoring, Document Registry and Zones.
    """

    def __init__(self) -> None:
        self.index: dict[str, dict[str, Any]] = {}
        self.total_documents: int = 0
        self._raw_documents: dict[str, list[str]] = {}

        # NEW: Stores raw metadata for rich CLI snippets and Okapi BM25 lengths
        self.document_registry: dict[str, dict[str, Any]] = {}

        self.tokenizer_regex = re.compile(r'[a-z0-9]+')
        self.stemmer = PorterStemmer()

    def tokenize(self, text: str) -> list[str]:
        """Cleans text, extracts tokens, and applies Porter Stemming."""
        raw_tokens = self.tokenizer_regex.findall(text.lower())
        return [self.stemmer.stem(token) for token in raw_tokens]

    def add_document(self,
                     doc_id: str,
                     text: str,
                     author: str,
                     tags: list[str],
                     url: str
    ) -> None:
        """Processes a structured document to store zones and metadata."""
        # 1. Tokenize zones separately to track Extents
        zones = {
            "text": self.tokenize(text),
            "author": self.tokenize(author),
            "tag": self.tokenize(" ".join(tags))
        }

        # 2. Combine for total document length
        all_tokens = zones["text"] + zones["author"] + zones["tag"]
        doc_length = len(all_tokens)

        # 3. Store in Document Registry
        self.document_registry[doc_id] = {
            "text": text,
            "author": author,
            "url": url,
            "length": doc_length
        }

        self._raw_documents[doc_id] = all_tokens
        self.total_documents += 1

        # 4. Map tokens with Extents (Zones) and update Collection Frequency
        for zone_name, tokens in zones.items():
            for position, token in enumerate(tokens):
                if token not in self.index:
                    self.index[token] = {
                        "idf": 0.0, "collection_frequency": 0, "postings": {}}

                self.index[token]["collection_frequency"] += 1

                if doc_id not in self.index[token]["postings"]:
                    self.index[token]["postings"][doc_id] = {
                        "tf": 0.0,
                        "positions": [],
                        "zones": set()
                    }

                self.index[token]["postings"][doc_id]["positions"].append(
                    position)
                self.index[token]["postings"][doc_id]["zones"].add(zone_name)

    def build_index(self) -> None:
        """Finalizes the index by calculating the TF and IDF scores."""
        logger.info(
            f"Calculating TF-IDF scores for "
            f"[cyan]{self.total_documents}[/cyan] documents...")

        for _token, data in self.index.items():
            doc_frequency = len(data["postings"])
            data["idf"] = math.log(self.total_documents / doc_frequency)

            for doc_id, posting in data["postings"].items():
                term_count = len(posting["positions"])
                total_words_in_doc = self.document_registry[doc_id]["length"]

                posting["tf"] = term_count / \
                    total_words_in_doc if total_words_in_doc > 0 else 0.0
                # Convert the set to a list so it can be saved to JSON safely
                posting["zones"] = list(posting["zones"])

        self._raw_documents.clear()
        logger.info(
            f"Index built successfully with "
            f"[green]{len(self.index)}[/green] unique terms.")

    def save(self, filepath: str) -> None:
        """Serializes the index and registry to a JSON file."""
        export_data = {
            "metadata": {"total_documents": self.total_documents},
            "document_registry": self.document_registry,
            "index": self.index
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
        logger.info(f"Index successfully saved to [cyan]{filepath}[/cyan]")

    def load(self, filepath: str) -> None:
        """Deserializes the index and registry from a JSON file."""
        try:
            with open(filepath, encoding='utf-8') as f:
                import_data = json.load(f)
                self.total_documents = import_data["metadata"]["total_documents"]
                self.document_registry = import_data.get(
                    "document_registry", {})
                self.index = import_data["index"]
            logger.info(
                f"Loaded index from [cyan]{filepath}[/cyan] "
                f"([green]{self.total_documents}[/green] documents).")
        except FileNotFoundError:
            logger.error(
                f"Index file not found at [cyan]{filepath}[/cyan]. "
                f"Please run 'build' first.")
            raise
