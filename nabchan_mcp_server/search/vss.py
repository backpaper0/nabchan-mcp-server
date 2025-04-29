import torch
from transformers import AutoModel, AutoTokenizer
import duckdb
from nabchan_mcp_server.search.models import Searcher, SearchResult

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


class VssSearcher(Searcher):
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        super().__init__(conn)

    def search(self, search_query: str, result_limit: int) -> list[SearchResult]:
        query = """
            SELECT url, title, description, score
            FROM (
                SELECT *, array_distance(embedding_vector, CAST($embedding_vector AS FLOAT[2048])) AS score
                FROM documents
            ) docs
            WHERE score IS NOT NULL
            ORDER BY score
            LIMIT $limit
            """

        embedding_vector = vectorize(search_query)

        return [
            SearchResult(url=url, title=title, description=description, score=score)
            for url, title, description, score in self._conn.execute(
                query,
                {"embedding_vector": embedding_vector, "limit": result_limit},
            ).fetchall()
        ]
