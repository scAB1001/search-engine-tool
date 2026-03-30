from src.indexer import InvertedIndex
from src.logger import logger


class SearchEngine:
    """
    Executes queries against an InvertedIndex using Boolean AND intersections
    and ranks the results dynamically using TF-IDF scoring.
    """

    def __init__(self, index: InvertedIndex) -> None:
        self.index_db = index

    def search(self, query: str) -> list[tuple[str, float]]:
        """
        Searches the index for the given query.

        Returns:
            A list of tuples containing (document_id, tf_idf_score),
            sorted descending by score.
        """
        # 1. Normalize the query
        tokens = self.index_db._tokenize(query)
        if not tokens:
            return []

        # 2. Early Exit: If any word in the query doesn't exist in the index,
        # the Boolean AND intersection is mathematically guaranteed to be empty.
        for token in tokens:
            if token not in self.index_db.index:
                logger.debug(
                    f"Token '[yellow]{token}[/yellow]' not found in index.")
                return []

        # 3. Boolean AND Intersection
        # Start the intersection set with the documents containing the first token
        matching_docs = set(self.index_db.index[tokens[0]]["postings"].keys())

        # Iteratively intersect with the documents of the remaining tokens
        for token in tokens[1:]:
            matching_docs.intersection_update(
                self.index_db.index[token]["postings"].keys()
            )

        if not matching_docs:
            logger.debug(
                "Terms exist individually, but no intersecting pages found.")
            return []

        # 4. Dynamic TF-IDF Scoring
        results = []
        for doc_id in matching_docs:
            combined_score = 0.0

            for token in tokens:
                idf = self.index_db.index[token]["idf"]
                tf = self.index_db.index[token]["postings"][doc_id]["tf"]
                # The total score for the page is the sum of TF*IDF for each query term
                combined_score += (tf * idf)

            results.append((doc_id, combined_score))

        # 5. Sort descending so the most relevant documents appear first
        sorted_results = sorted(results, key=lambda x: x[1], reverse=True)

        logger.info(f"Found [green]{len(sorted_results)}[/green] "
                    f"matching pages for query: '[cyan]{query}[/cyan]'")
        return sorted_results
