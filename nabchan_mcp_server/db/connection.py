from duckdb import connect, DuckDBPyConnection
from nabchan_mcp_server.settings import settings


def connect_db(read_only: bool = True) -> DuckDBPyConnection:
    return connect(settings.db_file, read_only=read_only)


if __name__ == "__main__":
    with connect_db() as conn:
        conn.install_extension("fts")
