from argparse import ArgumentParser
import asyncio
from pathlib import Path
from whoosh.index import create_in

from nabchan_mcp_server import schema
from bs4 import BeautifulSoup
from tqdm import tqdm
from html2text import html2text


async def main(nablarch_document_path: Path, index_path: Path) -> None:
    if not index_path.exists():
        index_path.mkdir(parents=True)
    file_index = create_in(index_path, schema)

    writer = file_index.writer()

    html_dir = nablarch_document_path / "_build" / "html"
    html_files = [html_file for html_file in html_dir.rglob("*.html")]
    baseurl = "https://nablarch.github.io/docs/LATEST/doc/"

    for html_file in tqdm(html_files):
        html = html_file.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        title = (
            str(soup.title.string) if soup.title and soup.title.string else "No Title"
        )
        content = soup.get_text(strip=True)
        url = baseurl + "/".join(html_file.relative_to(html_dir).parts)
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
        "--nablarch_document_path",
        type=Path,
        required=True,
        help="Nablarchのドキュメントのパス",
    )
    parser.add_argument(
        "--index_path",
        type=Path,
        required=True,
        help="インデックスのパス",
    )
    args = parser.parse_args()
    asyncio.run(
        main(
            nablarch_document_path=args.nablarch_document_path,
            index_path=args.index_path,
        )
    )
