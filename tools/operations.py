from typing import Callable

from duckdb import DuckDBPyConnection
from pydantic import BaseModel

from nabchan_mcp_server.search.fts import tokenize


class Document(BaseModel):
    url: str
    title: str
    description: str
    content: str
    text_content: str


class DbBuildingOperations:
    _conn: DuckDBPyConnection
    _enabled_vss: bool
    _vectorize_document: Callable[[str], list[float]]

    def __init__(self, conn: DuckDBPyConnection, enabled_vss: bool) -> None:
        self._conn = conn
        self._enabled_vss = enabled_vss
        if enabled_vss:
            from nabchan_mcp_server.search.vss import vectorize_document

            self._vectorize_document = vectorize_document
        else:
            self._vectorize_document = lambda _: []

    def create_table(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE documents (
                url TEXT,
                title TEXT,
                description TEXT,
                content TEXT,
                PRIMARY KEY (url)
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE word_segmentations (
                url TEXT,
                content TEXT,
                PRIMARY KEY (url),
                FOREIGN KEY (url) REFERENCES documents(url)
            )
            """
        )
        if self._enabled_vss:
            self._conn.execute(
                """
                CREATE TABLE document_vectors (
                    url TEXT,
                    content FLOAT[2048],
                    PRIMARY KEY (url),
                    FOREIGN KEY (url) REFERENCES documents(url)
                )
                """
            )

    def insert_row(self, document: Document) -> None:
        self._conn.execute(
            """
            INSERT INTO documents (url, title, description, content)
            VALUES ($url, $title, $description, $content)
            """,
            document.model_dump(exclude={"text_content"}),
        )
        self._conn.execute(
            """
            INSERT INTO word_segmentations (url, content)
            VALUES ($url, $content)
            """,
            {
                "url": document.url,
                "content": tokenize(document.text_content),
            },
        )
        if self._enabled_vss:
            self._conn.execute(
                """
                INSERT INTO document_vectors (url, content)
                VALUES ($url, $content)
                """,
                {
                    "url": document.url,
                    "content": self._vectorize_document(document.text_content),
                },
            )

    def create_index(self) -> None:
        self._conn.install_extension("fts")
        self._conn.load_extension("fts")
        self._conn.execute(
            """
            PRAGMA create_fts_index('word_segmentations', 'url', 'content',
                stemmer = 'none', stopwords = 'none', ignore = '', strip_accents = false, lower = false)
            """
        )
        if self._enabled_vss:
            self._conn.install_extension("vss")
            self._conn.load_extension("vss")
            self._conn.execute("SET hnsw_enable_experimental_persistence = true")
            self._conn.execute(
                """
                CREATE INDEX documents_hsnw_index ON document_vectors USING HNSW (content)
                """
            )
