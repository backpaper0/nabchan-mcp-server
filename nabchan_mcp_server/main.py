"""
MCPサーバー本体。
"""

import json

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from nabchan_mcp_server.db.connection import connect_db
from nabchan_mcp_server.search.factory import create_searcher
from nabchan_mcp_server.settings import settings
from nabchan_mcp_server.javadoc.tools import JavadocTools, get_javadoc_tools

instructions = "Nablarchのドキュメントを検索するMCPサーバー"

mcp = FastMCP("nabchan", instructions=instructions)
if settings.host:
    mcp.settings.host = settings.host
if settings.port:
    mcp.settings.port = settings.port


conn = connect_db()
searcher = create_searcher(settings.search_type, conn)
javadoc_tools = JavadocTools()


@mcp.tool(
    description="URLが示すNablarchのドキュメントを返します。ドキュメントはMarkdown形式で返されます。"
)
def read_document(url: str = Field(description="ドキュメントのURL")) -> str:
    result = conn.execute(
        "SELECT content FROM documents WHERE url = $url", {"url": url}
    ).fetchone()
    return result[0] if result else ""


match settings.search_type:
    case "fts":
        _search_type = "BM25を用いた全文検索"
    case "vss":
        _search_type = "コサイン類似度を用いたベクトル類似検索"
    case "hybrid":
        _search_type = "BM25を用いた全文検索とコサイン類似度を用いたベクトル類似検索のハイブリッド検索"


@mcp.tool(
    description=f"Nablarchのドキュメントを検索します。検索ロジックは{_search_type}です。結果にはURL、タイトル、概要が含まれます。"
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


@mcp.tool(
    description="Javadocに含まれるすべてのパッケージの一覧を取得します。"
)
async def javadoc_list_packages(
    version: str = Field(description="Javadocのバージョン (デフォルト: LATEST)", default="LATEST")
) -> str:
    results = await javadoc_tools.list_packages(version)
    return json.dumps(results, ensure_ascii=False)


@mcp.tool(
    description="指定されたパッケージの概要とクラス一覧を取得します。"
)
async def javadoc_get_package(
    package_name: str = Field(description="パッケージ名 (例: nablarch.core.db)"),
    version: str = Field(description="Javadocのバージョン (デフォルト: LATEST)", default="LATEST")
) -> str:
    results = await javadoc_tools.get_package_details(package_name, version)
    return json.dumps(results, ensure_ascii=False)


@mcp.tool(
    description="指定されたクラスの概要とメソッド一覧を取得します。"
)
async def javadoc_get_class(
    class_name: str = Field(description="クラス名 (例: nablarch.core.db.DbAccessException)"),
    version: str = Field(description="Javadocのバージョン (デフォルト: LATEST)", default="LATEST")
) -> str:
    results = await javadoc_tools.get_class_details(class_name, version)
    return json.dumps(results, ensure_ascii=False)


@mcp.tool(
    description="キーワードをもとにして関連するクラス、メソッドを検索します。"
)
async def javadoc_search(
    keyword: str = Field(description="検索キーワード"),
    version: str = Field(description="Javadocのバージョン (デフォルト: LATEST)", default="LATEST")
) -> str:
    results = await javadoc_tools.search_javadoc(keyword, version)
    return json.dumps(results, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport=settings.transport)
