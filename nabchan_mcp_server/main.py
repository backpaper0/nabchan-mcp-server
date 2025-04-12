"""
MCPサーバー本体。
"""

import json
from typing import Literal, TypedDict
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
from whoosh.query import Term


from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    PydanticBaseSettingsSource,
)


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

index = open_dir("index")


instructions = "Nablarchのドキュメントを検索するMCPサーバー"

mcp = FastMCP("nabchan", instructions=instructions)
if settings.host:
    mcp.settings.host = settings.host
if settings.port:
    mcp.settings.port = settings.port


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
    mcp.run(transport=settings.transport)
