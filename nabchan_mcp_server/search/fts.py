import duckdb
from lindera_py import Segmenter, Tokenizer, load_dictionary  # type: ignore

from nabchan_mcp_server.search.models import Searcher, SearchResult

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
            SELECT docs.url, docs.title, docs.description, scores.score
            FROM documents docs
            LEFT OUTER JOIN (
                SELECT url, fts_main_word_segmentations.match_bm25(url, $content, fields := 'content') AS score
                FROM word_segmentations
            ) scores
            ON docs.url = scores.url
            WHERE scores.score IS NOT NULL
            ORDER BY 4 DESC, 1 ASC
            LIMIT $limit
            """

        content = tokenize(search_query)

        return [
            SearchResult(url=url, title=title, description=description, score=score)
            for url, title, description, score in self._conn.execute(
                query,
                {"content": content, "limit": result_limit},
            ).fetchall()
        ]
