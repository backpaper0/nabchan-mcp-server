"""
MCPサーバー本体。
"""

import json
from typing import TypedDict
from mcp.server.fastmcp import FastMCP
from pydantic import Field
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


instructions = "Nablarchのドキュメントを検索するMCPサーバー"

mcp = FastMCP("nabchan", host=args.host, port=args.port, instructions=instructions)


@mcp.tool(
    description="URLが示すNablarchのドキュメントを返します。ドキュメントはMarkdown形式で返されます。"
)
def read_document(url: str) -> str:
    with index.searcher() as searcher:
        query = Term("url", url)
        results = searcher.search(query)
        return results[0]["markdown"] if results else ""


@mcp.tool(
    description="Nablarchのドキュメントを全文検索します。結果にはURL、タイトル、概要が含まれます。"
)
def search_document(
    search_query: str = Field(description="検索クエリ"),
    result_limit: int = Field(description="検索結果の最大件数"),
) -> str:
    with index.searcher() as searcher:
        query = QueryParser("content", index.schema).parse(search_query)
        results = [
            SearchResult(
                url=result["url"],
                title=result["title"],
                description=result["description"],
            )
            for result in searcher.search(query, limit=result_limit)
        ]
        # mcp/server/fastmcp/server.pyの_convert_to_content関数で素朴にjson.dumps()
        # されているためUnicodeエスケープされないためにはstr、あるいはTextContent型で返す必要がある。
        # ここではstrで返す。
        return json.dumps(results, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport=args.transport)
