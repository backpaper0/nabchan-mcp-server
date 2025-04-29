from abc import ABC, abstractmethod
from typing import Literal
import duckdb
from pydantic import BaseModel

SearchType = Literal["fts", "vss"]


class SearchResult(BaseModel):
    url: str
    title: str
    description: str
    score: float


class Searcher(ABC):
    _conn: duckdb.DuckDBPyConnection

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    @abstractmethod
    def search(self, search_query: str, result_limit: int) -> list[SearchResult]: ...
