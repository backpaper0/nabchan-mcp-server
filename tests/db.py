from nabchan_mcp_server.db.connection import connect_db
from nabchan_mcp_server.db.operations import DbOperations, Document
from tqdm import tqdm


if __name__ == "__main__":
    documents = [
        Document(
            url="https://example.com/1",
            title="猫1",
            description="...",
            markdown="# 猫はかわいい",
            text_content="猫はかわいい",
        ),
        Document(
            url="https://example.com/2",
            title="猫2",
            description="...",
            markdown="...",
            text_content="猫は癒し",
        ),
        Document(
            url="https://example.com/3",
            title="ミズクラゲ",
            description="...",
            markdown="...",
            text_content="ミズクラゲはかわいい",
        ),
    ]

    with (
        tqdm(total=len(documents) + 2, desc="Build test db") as progress_bar,
        connect_db(read_only=False) as conn,
    ):
        db_operations = DbOperations(conn)

        progress_bar.set_postfix_str("Create table")
        db_operations.create_table()
        progress_bar.update(1)

        for document in documents:
            progress_bar.set_postfix_str(f"Insert row: {document.title}")
            db_operations.insert_row(document)
            progress_bar.update(1)

        progress_bar.set_postfix_str("Create index")
        db_operations.create_index()
        progress_bar.update(1)

        progress_bar.set_postfix_str("Completed")
