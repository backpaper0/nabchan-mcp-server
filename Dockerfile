FROM python:3.11

RUN pip install uv

COPY pyproject.toml /workspace/
COPY uv.lock /workspace/

RUN uv --directory /workspace sync

COPY nabchan_mcp_server /workspace/nabchan_mcp_server
COPY documents.db /workspace/documents.db

WORKDIR /workspace

# DuckDBのextensionをダウンロードしておく
RUN uv run python -m nabchan_mcp_server.db.connection

ENV TRANSPORT=sse

ENTRYPOINT ["uv", "run", "python", "-m", "nabchan_mcp_server.main"]