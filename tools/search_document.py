"""
検索を試すためのスクリプト。
"""

import json
from whoosh.index import open_dir
from whoosh.qparser import QueryParser

from argparse import ArgumentParser


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

    index = open_dir("index")
    with index.searcher() as searcher:
        query = QueryParser("content", index.schema).parse(args.search_query)
        results = searcher.search(query, limit=args.result_limit)
        print(json.dumps([result.fields() for result in results], ensure_ascii=False))
