"""
MCPサーバー本体。
"""

from typing import TypedDict
from mcp.server.fastmcp import FastMCP
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
from whoosh.query import Term

from argparse import ArgumentParser


class SearchResult(TypedDict):
    url: str
    title: str
    description: str


index = open_dir("index")


parser = ArgumentParser()
parser.add_argument("--transport", "-t", type=str, default="stdio")
parser.add_argument("--host", "-H", type=str, default="0.0.0.0")
parser.add_argument("--port", "-p", type=int, default=8000)
args = parser.parse_args()

mcp = FastMCP("nabchan", host=args.host, port=args.port)


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
    mcp.run(transport=args.transport)
