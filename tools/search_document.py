"""
検索を試すためのスクリプト。
"""

import json

from argparse import ArgumentParser
import nabchan_mcp_server.index as idx
import nabchan_mcp_server.vector as vec


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

    search_index = idx.search_index if args.search_type == "fts" else vec.search_index

    results = search_index(
        search_query=args.search_query,
        result_limit=args.result_limit,
        select_columns=["url", "title", "description", "markdown", "score"],
    )

    print(
        json.dumps(
            [
                {
                    "url": url,
                    "title": title,
                    "description": description,
                    "markdown": markdown,
                    "score": score,
                }
                for url, title, description, markdown, score in results
            ],
            ensure_ascii=False,
        )
    )
