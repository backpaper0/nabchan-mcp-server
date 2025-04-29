"""
インデックスを構築するスクリプト。
"""

from argparse import ArgumentParser
import asyncio
from pathlib import Path
from typing import Awaitable, Callable, cast
import aiofiles

from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm
from html2text import html2text
import re
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from langchain_core.rate_limiters import InMemoryRateLimiter

from nabchan_mcp_server.db.connection import connect_db
from nabchan_mcp_server.db.operations import DbOperations, Document


unnecessary_suffix_pattern = re.compile(r" — [^—]+$")

summarize_system_prompt = """あなたは技術文書を簡潔に要約する専門家です。
渡された技術文書の要約を作成してください。

- 技術文書はmarkdown形式で記載されています。
- 要約は300文字以内の日本語で記載してください。
- 要約の形式はプレーンテキストにしてください。
- 主要なポイントや結論を中心にまとめてください。
"""


async def add_document(queue: asyncio.Queue) -> None:
    with connect_db(read_only=False) as conn:
        db_operations = DbOperations(conn)
        db_operations.create_table()
        while True:
            item = await queue.get()
            if item is None:
                break
            document = cast(Document, item)
            db_operations.insert_row(document)
            queue.task_done()
        db_operations.create_index()


async def process_html_file(
    semaphore: asyncio.Semaphore,
    queue: asyncio.Queue,
    html_file: Path,
    generate_description: Callable[[str], Awaitable[str]],
) -> None:
    async with semaphore:
        async with aiofiles.open(html_file, mode="r", encoding="utf-8") as f:
            html = await f.read()
            soup = BeautifulSoup(html, "html.parser")
            main_content = soup.select_one("[role='main']")
            if not main_content:
                # main_contentがないページは除外する
                return

            if html_file.name == "index.html":
                toctrees = main_content.select("div.toctree-wrapper")
                all_divs = main_content.select("div")
                not_toctree_divs = [div for div in all_divs if div not in toctrees]
                if len(not_toctree_divs) == 3:
                    # tocしかないページは除外する
                    return

            title = (
                str(soup.title.string)
                if soup.title and soup.title.string
                else "No Title"
            )
            title = unnecessary_suffix_pattern.sub("", title)
            content = main_content.get_text(strip=True)
            url = "https://" + "/".join(html_file.parts)
            description = await generate_description(content)
            markdown = html2text(
                "".join([str(child) for child in main_content.children])
            )
            document = Document(
                url=url,
                title=title,
                description=description,
                markdown=markdown,
                text_content=content,
            )
            await queue.put(document)


async def main(
    nablarch_document_path: Path,
    parallels: int,
    generate_description: Callable[[str], Awaitable[str]],
) -> None:
    exclude_html_files = (Path("search.html"), Path("genindex.html"))
    html_files = [
        html_file
        for html_file in nablarch_document_path.rglob("*.html")
        if all([name not in html_file.parts for name in ["en", "_static"]])
        and html_file.relative_to(nablarch_document_path) not in exclude_html_files
    ]

    semaphore = asyncio.Semaphore(parallels)
    queue: asyncio.Queue = asyncio.Queue()

    tasks = [
        process_html_file(semaphore, queue, html_file, generate_description)
        for html_file in html_files
    ]

    add_document_task = asyncio.create_task(add_document(queue))
    for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks)):
        await coro
    await queue.put(None)
    await add_document_task


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--nablarch_version",
        type=str,
        default="LATEST",
        help="Nablarchのドキュメントのバージョン",
    )
    parser.add_argument(
        "--parallels",
        type=int,
        default=20,
        help="並列処理の数",
    )
    parser.add_argument(
        "--llm",
        type=str,
        default="gpt-4o-mini",
        help="要約に使用するLLMのモデル名。LLMを使用しない場合はnoneを指定してください。",
    )
    args = parser.parse_args()

    nablarch_document_path = (
        Path("nablarch.github.io") / "docs" / args.nablarch_version / "doc"
    )

    if args.llm == "none":

        async def generate_description(content: str) -> str:
            return content[:300]
    else:
        load_dotenv()
        rate_limiter = InMemoryRateLimiter(
            requests_per_second=1.0, check_every_n_seconds=1.0, max_bucket_size=1.0
        )
        llm = ChatOpenAI(
            model=args.llm,
            temperature=0.0,
            max_retries=10,
            rate_limiter=rate_limiter,
        )

        async def generate_description(content: str) -> str:
            ai_message = await llm.ainvoke(
                [
                    SystemMessage(summarize_system_prompt),
                    HumanMessage(content),
                ]
            )
            return str(ai_message.content)

    asyncio.run(
        main(
            nablarch_document_path=nablarch_document_path,
            parallels=args.parallels,
            generate_description=generate_description,
        )
    )
