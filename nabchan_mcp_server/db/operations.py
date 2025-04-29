from duckdb import DuckDBPyConnection
from nabchan_mcp_server.search.fts import tokenize
from nabchan_mcp_server.search.vss import vectorize
from pydantic import BaseModel


class Document(BaseModel):
    url: str
    title: str
    description: str
    markdown: str
    text_content: str


class DbOperations:
    _conn: DuckDBPyConnection

    def __init__(self, conn: DuckDBPyConnection) -> None:
        self._conn = conn

    def create_table(self) -> None:
        for extension in ["fts", "vss"]:
            self._conn.install_extension(extension)
            self._conn.load_extension(extension)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                url TEXT,
                title TEXT,
                description TEXT,
                markdown TEXT,
                morpheme_sequence TEXT,
                embedding_vector FLOAT[2048],
                PRIMARY KEY (url)
            )
            """
        )

    def insert_row(self, document: Document) -> None:
        morpheme_sequence = tokenize(document.text_content)
        embedding_vector = vectorize(document.text_content)
        self._conn.execute(
            """
            INSERT INTO documents (url, title, description, markdown, morpheme_sequence, embedding_vector)
            VALUES ($url, $title, $description, $markdown, $morpheme_sequence, $embedding_vector)
            """,
            {
                **document.model_dump(exclude={"text_content"}),
                "morpheme_sequence": morpheme_sequence,
                "embedding_vector": embedding_vector,
            },
        )

    def create_index(self) -> None:
        self._conn.execute(
            """
            PRAGMA create_fts_index('documents', 'url', 'morpheme_sequence',
                stemmer = 'none', stopwords = 'none', ignore = '', strip_accents = false, lower = false)
            """
        )
        self._conn.execute("SET hnsw_enable_experimental_persistence = true")
        self._conn.execute(
            """
            CREATE INDEX documents_hsnw_index ON documents USING HNSW (embedding_vector)
            """
        )
