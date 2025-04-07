"""
MCPサーバー本体。
"""
from mcp.server.fastmcp import FastMCP
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
from whoosh.query import Term

from nabchan_mcp_server import SearchResult


index = open_dir("index")


mcp = FastMCP("nabchan")


@mcp.tool(description="URLが示すNablarchのドキュメントを返します。")
def read_document(url: str) -> str:
    query = Term("url", url)
    with index.searcher() as searcher:
        results = searcher.search(query)
        return results[0]["markdown"] if results else ""


@mcp.tool(description="Nablarchのドキュメントを検索します。")
def search_document(search_query: str, result_limit: int) -> list[SearchResult]:
    with index.searcher() as searcher:
        query = QueryParser("content", index.schema).parse(search_query)
        results = searcher.search(query, limit=result_limit)
        return [
            SearchResult(
                url=result["url"],
                title=result["title"],
                description=result["description"],
            )
            for result in results
        ]


if __name__ == "__main__":
    mcp.run(transport="stdio")
