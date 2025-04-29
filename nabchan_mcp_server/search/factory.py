from nabchan_mcp_server.search.models import Searcher, SearchType
from nabchan_mcp_server.search.fts import FtsSearcher
from duckdb import DuckDBPyConnection


def create_searcher(search_type: SearchType, conn: DuckDBPyConnection) -> Searcher:
    match search_type:
        case "fts":
            return FtsSearcher(conn)
        case "vss":
            from nabchan_mcp_server.search.vss import VssSearcher

            return VssSearcher(conn)
