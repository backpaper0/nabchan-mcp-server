"""
インデックスを構築するスクリプト。
"""

from argparse import ArgumentParser
import asyncio
from pathlib import Path
from whoosh.index import create_in

from nabchan_mcp_server.index import schema
from bs4 import BeautifulSoup
from tqdm import tqdm
from html2text import html2text


async def main(nablarch_document_path: Path, index_path: Path) -> None:
    if not index_path.exists():
        index_path.mkdir(parents=True)
    file_index = create_in(index_path, schema)

    writer = file_index.writer()

    html_files = [
        html_file
        for html_file in nablarch_document_path.rglob("*.html")
        if "en" not in html_file.parts
    ]

    for html_file in tqdm(html_files):
        html = html_file.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        title = (
            str(soup.title.string) if soup.title and soup.title.string else "No Title"
        )
        content = soup.get_text(strip=True)
        url = "https://" + "/".join(html_file.parts)
        description = content[:100]
        markdown = html2text(html)

        writer.add_document(
            title=title,
            content=content,
            url=url,
            description=description,
            markdown=markdown,
        )

    writer.commit()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--nablarch_version",
        type=str,
        default="LATEST",
        help="Nablarchのドキュメントのバージョン",
    )
    args = parser.parse_args()
    nablarch_document_path = (
        Path("nablarch.github.io") / "docs" / args.nablarch_version / "doc"
    )
    index_path = Path("index")
    asyncio.run(
        main(
            nablarch_document_path=nablarch_document_path,
            index_path=index_path,
        )
    )
