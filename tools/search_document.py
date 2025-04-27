"""
検索を試すためのスクリプト。
"""

import json

from argparse import ArgumentParser
import nabchan_mcp_server.index as idx


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
    args = parser.parse_args()

    results = idx.search_index(
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
