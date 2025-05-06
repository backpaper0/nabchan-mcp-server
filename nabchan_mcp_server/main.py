"""
MCPサーバー本体。
"""

import json

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from nabchan_mcp_server.db.connection import connect_db
from nabchan_mcp_server.search.factory import create_searcher
from nabchan_mcp_server.settings import settings

instructions = "Nablarchのドキュメントを検索するMCPサーバー"

mcp = FastMCP("nabchan", instructions=instructions)
if settings.host:
    mcp.settings.host = settings.host
if settings.port:
    mcp.settings.port = settings.port


conn = connect_db()
searcher = create_searcher(settings.search_type, conn)


@mcp.tool(
    description="URLが示すNablarchのドキュメントを返します。ドキュメントはMarkdown形式で返されます。"
)
def read_document(url: str = Field(description="ドキュメントのURL")) -> str:
    result = conn.execute(
        "SELECT content FROM documents WHERE url = $url", {"url": url}
    ).fetchone()
    return result[0] if result else ""


@mcp.tool(
    description="Nablarchのドキュメントを全文検索します。結果にはURL、タイトル、概要が含まれます。"
)
def search_document(
    search_query: str = Field(description="検索クエリ"),
    result_limit: int = Field(description="検索結果の最大件数"),
) -> str:
    results = searcher.search(
        search_query=search_query,
        result_limit=result_limit,
    )

    # mcp/server/fastmcp/server.pyの_convert_to_content関数で素朴にjson.dumps()
    # されているためUnicodeエスケープされないためにはstr、あるいはTextContent型で返す必要がある。
    # ここではstrで返す。
    return json.dumps(
        [result.model_dump(exclude={"score"}) for result in results], ensure_ascii=False
    )


if __name__ == "__main__":
    mcp.run(transport=settings.transport)
