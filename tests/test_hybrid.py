import unittest

from duckdb import DuckDBPyConnection

from nabchan_mcp_server.db.connection import connect_db
from nabchan_mcp_server.search.hybrid import HybridSearcher


class TestHybrid(unittest.TestCase):
    _conn: DuckDBPyConnection
    _searcher: HybridSearcher

    def setUp(self):
        self._conn = connect_db(read_only=True)
        self._searcher = HybridSearcher(self._conn)

    def tearDown(self):
        if self._conn:
            self._conn.close()

    def test_same_text(self):
        results = self._searcher.search("猫はかわいい", 1)
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.title, "猫1")

    def test_part_of_text_1(self):
        results = self._searcher.search("猫", 2)
        self.assertEqual(len(results), 2)
        titles = [result.title for result in results]
        self.assertIn("猫1", titles)
        self.assertIn("猫2", titles)

    def test_part_of_text_2(self):
        results = self._searcher.search("かわいい", 2)
        self.assertEqual(len(results), 2)
        titles = [result.title for result in results]
        self.assertIn("猫1", titles)
        self.assertIn("ミズクラゲ", titles)
