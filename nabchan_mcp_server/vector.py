from typing import Any
import torch
from transformers import AutoModel, AutoTokenizer
import duckdb

tokenizer = AutoTokenizer.from_pretrained(
    "pfnet/plamo-embedding-1b", trust_remote_code=True
)
model = AutoModel.from_pretrained("pfnet/plamo-embedding-1b", trust_remote_code=True)

device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)


def vectorize(text: str) -> list[float]:
    with torch.inference_mode():
        embedding: torch.Tensor = model.encode_query(text, tokenizer)
        return embedding[0].tolist()


def _search_index(
    search_query: str,
    result_limit: int,
    select_columns: list[str],
    conn: duckdb.DuckDBPyConnection,
) -> list[Any]:
    query = f"""
        SELECT {", ".join(select_columns)}
        FROM (
            SELECT *, array_distance(vec, CAST($vec AS FLOAT[2048])) AS score
            FROM documents
        ) docs
        ORDER BY score ASC
        LIMIT $limit
        """

    vec = vectorize(search_query)

    return conn.execute(
        query,
        {"vec": vec, "limit": result_limit},
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
