from enum import StrEnum

from src.indexer import InvertedIndex
from src.logger import logger


class SearchStrategy(StrEnum):
    """Defines the available mathematical ranking algorithms."""
    TF_IDF = "tf-idf"
    BM25 = "bm25"


class SearchEngine:
    """
    Executes queries against an InvertedIndex using Boolean AND intersections
    and ranks the results dynamically using either TF-IDF or Okapi BM25.
    """

    def __init__(self, index: InvertedIndex) -> None:
        self.index_db = index

        # Pre-calculate Average Document Length (avgdl) for BM25
        total_length = sum(doc.get("length", 0)
                           for doc in self.index_db.document_registry.values())
        self.avgdl = total_length / max(1, self.index_db.total_documents)

    def search(
        self,
        query: str,
        strategy: SearchStrategy = SearchStrategy.TF_IDF
    ) -> list[tuple[str, float]]:
        """
        Processes a query and returns ranked document IDs.

        Boolean AND intersection with TF-IDF or BM25 ranking.

        ALGORITHM:
        1. Tokenize and stem query (Porter Stemmer)
        2. Find postings for first token → set A
        3. For each additional token:
            set A = set A ∩ postings[token]
        4. Score matching docs using selected strategy:
            - TF-IDF: score = Σ(TF * IDF * zone_weight)
            - BM25: score = Σ(IDF * (raw_tf * (k1+1)) / (raw_tf + k1*(1-b+b*len_norm)))

        Time Complexity:
            - Query parsing: O(m) where m = query length
            - Intersection: O(k * log n) where k = docs, n = postings
            - Scoring: O(k * m) where k = matching docs, m = query terms
            Total: O(k * m * log n)

        Space Complexity: O(k) for storing results

        Zone Weighting:
            - Author zone: +1.5x multiplier (high semantic value)
            - Tag zone: +0.5x multiplier (moderate value)
            - Text zone: 1.0x baseline
        """
        tokens = self.index_db.tokenize(query)
        if not tokens:
            return []

        for token in tokens:
            if token not in self.index_db.index:
                logger.debug(
                    f"Token '[yellow]{token}[/yellow]' not found in index.")
                return []

        matching_docs = set(self.index_db.index[tokens[0]]["postings"].keys())
        for token in tokens[1:]:
            matching_docs.intersection_update(
                self.index_db.index[token]["postings"].keys()
            )

        if not matching_docs:
            logger.debug(
                "Terms exist individually, but no intersecting pages found.")
            return []

        # BM25 Constants
        k1 = 1.5
        b = 0.75
        results = []

        for doc_id in matching_docs:
            combined_score = 0.0
            doc_length = self.index_db.document_registry.get(
                doc_id, {}).get("length", 1)

            for token in tokens:
                posting = self.index_db.index[token]["postings"][doc_id]
                idf = self.index_db.index[token]["idf"]

                # Boost scores if word appears in high-value metadata
                zone_weight = 1.0
                if "author" in posting["zones"]:
                    zone_weight += 1.5
                if "tag" in posting["zones"]:
                    zone_weight += 0.5

                if strategy == SearchStrategy.BM25:
                    # Okapi BM25 Mathematical Formula
                    raw_tf = len(posting["positions"])
                    numerator = raw_tf * (k1 + 1)
                    denominator = raw_tf + k1 * \
                        (1 - b + b * (doc_length / self.avgdl))
                    term_score = idf * (numerator / denominator)
                    combined_score += (term_score * zone_weight)
                else:
                    # Standard TF-IDF Formula
                    tf = posting["tf"]
                    combined_score += (tf * idf * zone_weight)

            results.append((doc_id, combined_score))

        sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
        logger.info(
            f"Found [green]{len(sorted_results)}[/green] matching pages "
            f"for query: '[cyan]{query}[/cyan]' using [yellow]{strategy.value}[/yellow]"
        )
        return sorted_results
