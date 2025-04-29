"""
検索を試すためのスクリプト。
"""

import json

from argparse import ArgumentParser
from typing import cast
from nabchan_mcp_server.search.factory import create_searcher
from nabchan_mcp_server.search.models import SearchType
from nabchan_mcp_server.db.connection import connect_db


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--search_query",
        "-q",
        type=str,
        required=True,
        help="検索クエリ",
    )
    parser.add_argument(
        "--result_limit",
        "-l",
        type=int,
        default=1,
        help="検索結果の上限",
    )
    parser.add_argument(
        "--search_type",
        "-t",
        type=str,
        choices=["fts", "vss"],
        default="fts",
        help="検索の方式。fts(全文検索)かvss(ベクトル類似検索)を指定する。",
    )
    args = parser.parse_args()

    with connect_db(read_only=False) as conn:
        search_type = cast(SearchType, args.search_type)
        searcher = create_searcher(search_type, conn)

        results = searcher.search(
            search_query=args.search_query,
            result_limit=args.result_limit,
        )

        print(
            json.dumps(
                [result.model_dump() for result in results],
                ensure_ascii=False,
            )
        )
