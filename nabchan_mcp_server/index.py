from typing import Any
from lindera_py import Segmenter, Tokenizer, load_dictionary
import duckdb

dictionary = load_dictionary("ipadic")
segmenter = Segmenter("normal", dictionary)
tokenizer = Tokenizer(segmenter)


def tokenize(text: str) -> str:
    return " ".join(token.text for token in tokenizer.tokenize(text))


def _search_index(
    search_query: str,
    result_limit: int,
    select_columns: list[str],
    conn: duckdb.DuckDBPyConnection,
) -> list[Any]:
    query = f"""
        SELECT {", ".join(select_columns)}
        FROM (
            SELECT *, fts_main_documents.match_bm25(url, $content, fields := 'content') AS score
            FROM documents
        ) docs
        WHERE score IS NOT NULL
        ORDER BY score DESC
        OFFSET 0 LIMIT $limit
        """

    content = tokenize(search_query)

    return conn.execute(
        query,
        {"content": content, "limit": result_limit},
    ).fetchall()


def search_index(
    search_query: str,
    result_limit: int,
    select_columns: list[str],
    conn: duckdb.DuckDBPyConnection | None = None,
) -> list[Any]:
    if conn:
        return _search_index(
            search_query,
            result_limit,
            select_columns,
            conn,
        )

    with duckdb.connect("index.db", read_only=True) as _conn:
        return _search_index(
            search_query,
            result_limit,
            select_columns,
            _conn,
        )


# DuckDBのextensionをダウンロードするための雑な検索
if __name__ == "__main__":
    search_index("Nablarch", 1, ["url"])
