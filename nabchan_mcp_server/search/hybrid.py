import duckdb

from nabchan_mcp_server.search.fts import tokenize
from nabchan_mcp_server.search.models import Searcher, SearchResult
from nabchan_mcp_server.search.vss import vectorize_query


class HybridSearcher(Searcher):
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        super().__init__(conn)

    def search(self, search_query: str, result_limit: int) -> list[SearchResult]:
        query = """
            WITH
                segs AS (
                    SELECT docs.url, docs.title, docs.description, scores.score
                    FROM documents docs
                    LEFT OUTER JOIN (
                        SELECT url, fts_main_word_segmentations.match_bm25(url, $word_segmentations_content, fields := 'content') AS score
                        FROM word_segmentations
                    ) scores
                    ON docs.url = scores.url
                    WHERE scores.score IS NOT NULL
                ),
                vecs AS (
                    SELECT docs.url, docs.title, docs.description, scores.score
                    FROM
                        documents docs
                    LEFT OUTER JOIN (
                        SELECT url, array_cosine_similarity(content, CAST($document_vectors_content AS FLOAT[2048])) AS score
                        FROM document_vectors
                    ) scores
                    ON docs.url = scores.url
                    WHERE scores.score IS NOT NULL
                )
            SELECT
                COALESCE(segs.url, vecs.url) AS url,
                COALESCE(segs.title, vecs.title) AS title,
                COALESCE(segs.description, vecs.description) AS description,
                (COALESCE(segs.score, 0.0) / seg_max.score * 0.5) + (COALESCE(vecs.score, 0.0) / vec_max.score * 0.5) AS score
            FROM segs
            FULL OUTER JOIN vecs
            ON segs.url = vecs.url
            CROSS JOIN (SELECT MAX(score) AS score FROM segs) seg_max
            CROSS JOIN (SELECT MAX(score) AS score FROM vecs) vec_max
            ORDER BY 4 DESC, 1 ASC
            LIMIT $limit
            """

        word_segmentations_content = tokenize(search_query)
        document_vectors_content = vectorize_query(search_query)

        return [
            SearchResult(url=url, title=title, description=description, score=score)
            for url, title, description, score in self._conn.execute(
                query,
                {
                    "word_segmentations_content": word_segmentations_content,
                    "document_vectors_content": document_vectors_content,
                    "limit": result_limit,
                },
            ).fetchall()
        ]
