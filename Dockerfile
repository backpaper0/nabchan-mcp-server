FROM python:3.11

COPY requirements.txt /workspace/

RUN pip install -r /workspace/requirements.txt

COPY nabchan_mcp_server /workspace/nabchan_mcp_server
COPY documents.db /workspace/documents.db

WORKDIR /workspace

# DuckDBのextensionをダウンロードしておく
RUN python -m nabchan_mcp_server.db.connection

ENV TRANSPORT=sse

ENTRYPOINT ["python", "-m", "nabchan_mcp_server.main"]