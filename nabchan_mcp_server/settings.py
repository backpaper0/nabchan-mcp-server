from typing import Literal

from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    PydanticBaseSettingsSource,
)

from nabchan_mcp_server.search.models import SearchType


class Settings(BaseSettings):
    transport: Literal["stdio", "sse"] = "stdio"
    host: str | None = None
    port: int | None = None
    search_type: SearchType = "fts"
    db_file: str = "documents.db"

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
            CliSettingsSource(
                settings_cls, cli_parse_args=True, cli_ignore_unknown_args=True
            ),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )


settings = Settings()
