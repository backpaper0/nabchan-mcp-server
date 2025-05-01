from typing import Callable
from duckdb import DuckDBPyConnection
from nabchan_mcp_server.search.fts import tokenize
from pydantic import BaseModel


class Document(BaseModel):
    url: str
    title: str
    description: str
    markdown: str
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
            CREATE TABLE IF NOT EXISTS documents (
                url TEXT,
                title TEXT,
                description TEXT,
                markdown TEXT,
                morpheme_sequence TEXT,
                PRIMARY KEY (url)
            )
            """
        )
        if self._enabled_vss:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS document_vectors (
                    url TEXT,
                    embedding_vector FLOAT[2048],
                    PRIMARY KEY (url),
                    FOREIGN KEY (url) REFERENCES documents(url)
                )
                """
            )

    def insert_row(self, document: Document) -> None:
        morpheme_sequence = tokenize(document.text_content)
        self._conn.execute(
            """
            INSERT INTO documents (url, title, description, markdown, morpheme_sequence)
            VALUES ($url, $title, $description, $markdown, $morpheme_sequence)
            """,
            {
                **document.model_dump(exclude={"text_content"}),
                "morpheme_sequence": morpheme_sequence,
            },
        )
        if self._enabled_vss:
            embedding_vector = self._vectorize_document(document.text_content)
            self._conn.execute(
                """
                INSERT INTO document_vectors (url, embedding_vector)
                VALUES ($url, $embedding_vector)
                """,
                {
                    "url": document.url,
                    "embedding_vector": embedding_vector,
                },
            )

    def create_index(self) -> None:
        self._conn.install_extension("fts")
        self._conn.load_extension("fts")
        self._conn.execute(
            """
            PRAGMA create_fts_index('documents', 'url', 'morpheme_sequence',
                stemmer = 'none', stopwords = 'none', ignore = '', strip_accents = false, lower = false)
            """
        )
        if self._enabled_vss:
            self._conn.install_extension("vss")
            self._conn.load_extension("vss")
            self._conn.execute("SET hnsw_enable_experimental_persistence = true")
            self._conn.execute(
                """
                CREATE INDEX documents_hsnw_index ON document_vectors USING HNSW (embedding_vector)
                """
            )
