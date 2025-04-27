FROM python:3.11

RUN pip install uv

COPY pyproject.toml /workspace/
COPY uv.lock /workspace/

RUN uv --directory /workspace sync

COPY nabchan_mcp_server /workspace/nabchan_mcp_server
COPY index.db /workspace/index.db

WORKDIR /workspace

# DuckDBのextensionをダウンロードするため、一度検索しておく
RUN uv run python -m nabchan_mcp_server.index

ENV TRANSPORT=sse

ENTRYPOINT ["uv", "run", "python", "-m", "nabchan_mcp_server.main"]