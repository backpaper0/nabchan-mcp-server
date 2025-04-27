"""
MCPサーバー本体。
"""

import json
from typing import Literal, TypedDict
from mcp.server.fastmcp import FastMCP
from pydantic import Field
import duckdb


from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    PydanticBaseSettingsSource,
)

import nabchan_mcp_server.index as idx


class Settings(BaseSettings):
    transport: Literal["stdio", "sse"] = "stdio"
    host: str | None = None
    port: int | None = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            CliSettingsSource(settings_cls, cli_parse_args=True),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )


class SearchResult(TypedDict):
    url: str
    title: str
    description: str


settings = Settings()

conn = duckdb.connect("index.db", read_only=True)


instructions = "Nablarchのドキュメントを検索するMCPサーバー"

mcp = FastMCP("nabchan", instructions=instructions)
if settings.host:
    mcp.settings.host = settings.host
if settings.port:
    mcp.settings.port = settings.port


@mcp.tool(
    description="URLが示すNablarchのドキュメントを返します。ドキュメントはMarkdown形式で返されます。"
)
def read_document(url: str = Field(description="ドキュメントのURL")) -> str:
    result = conn.execute(
        "SELECT markdown FROM documents WHERE url = $url", {"url": url}
    ).fetchone()
    return result[0] if result else ""


@mcp.tool(
    description="Nablarchのドキュメントを全文検索します。結果にはURL、タイトル、概要が含まれます。"
)
def search_document(
    search_query: str = Field(description="検索クエリ"),
    result_limit: int = Field(description="検索結果の最大件数"),
) -> str:
    results = [
        SearchResult(url=url, title=title, description=description)
        for url, title, description in idx.search_index(
            search_query=search_query,
            result_limit=result_limit,
            select_columns=["url", "title", "description"],
            conn=conn,
        )
    ]

    # mcp/server/fastmcp/server.pyの_convert_to_content関数で素朴にjson.dumps()
    # されているためUnicodeエスケープされないためにはstr、あるいはTextContent型で返す必要がある。
    # ここではstrで返す。
    return json.dumps(results, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport=settings.transport)
