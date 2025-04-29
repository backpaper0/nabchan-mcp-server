from nabchan_mcp_server.search.models import Searcher, SearchResult
import duckdb
from lindera_py import Segmenter, Tokenizer, load_dictionary

dictionary = load_dictionary("ipadic")
segmenter = Segmenter("normal", dictionary)
tokenizer = Tokenizer(segmenter)


def tokenize(text: str) -> str:
    return " ".join(token.text for token in tokenizer.tokenize(text))


class FtsSearcher(Searcher):
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        super().__init__(conn)

    def search(self, search_query: str, result_limit: int) -> list[SearchResult]:
        query = """
            SELECT url, title, description, score
            FROM (
                SELECT *, fts_main_documents.match_bm25(url, $morpheme_sequence, fields := 'morpheme_sequence') AS score
                FROM documents
            ) docs
            WHERE score IS NOT NULL
            ORDER BY score DESC
            LIMIT $limit
            """

        morpheme_sequence = tokenize(search_query)

        return [
            SearchResult(url=url, title=title, description=description, score=score)
            for url, title, description, score in self._conn.execute(
                query,
                {"morpheme_sequence": morpheme_sequence, "limit": result_limit},
            ).fetchall()
        ]
