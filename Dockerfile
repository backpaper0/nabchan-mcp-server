FROM python:3.11

RUN pip install uv

COPY pyproject.toml /workspace/
COPY uv.lock /workspace/

RUN uv --directory /workspace sync

COPY nabchan_mcp_server /workspace/nabchan_mcp_server
COPY index /workspace/index

WORKDIR /workspace

ENV TRANSPORT=sse

CMD ["uv", "run", "python", "-m", "nabchan_mcp_server.main"]