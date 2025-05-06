import duckdb
import torch
from transformers import AutoModel, AutoTokenizer  # type: ignore

from nabchan_mcp_server.search.models import Searcher, SearchResult

tokenizer = AutoTokenizer.from_pretrained(
    "pfnet/plamo-embedding-1b", trust_remote_code=True
)
model = AutoModel.from_pretrained("pfnet/plamo-embedding-1b", trust_remote_code=True)

device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)


def vectorize_query(text: str) -> list[float]:
    with torch.inference_mode():
        embedding: torch.Tensor = model.encode_query(text, tokenizer)
        return embedding[0].tolist()


def vectorize_document(text: str) -> list[float]:
    with torch.inference_mode():
        embedding: torch.Tensor = model.encode_document(text, tokenizer)
        return embedding[0].tolist()


class VssSearcher(Searcher):
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        super().__init__(conn)

    def search(self, search_query: str, result_limit: int) -> list[SearchResult]:
        query = """
            SELECT docs.url, docs.title, docs.description, scores.score
            FROM
                documents docs
            LEFT OUTER JOIN (
                SELECT url, array_distance(content, CAST($content AS FLOAT[2048])) AS score
                FROM document_vectors
            ) scores
            ON docs.url = scores.url
            WHERE scores.score IS NOT NULL
            ORDER BY scores.score
            LIMIT $limit
            """

        content = vectorize_query(search_query)

        return [
            SearchResult(url=url, title=title, description=description, score=score)
            for url, title, description, score in self._conn.execute(
                query,
                {"content": content, "limit": result_limit},
            ).fetchall()
        ]
