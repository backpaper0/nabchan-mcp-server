import json
from typing import cast
from mcp.client.stdio import stdio_client
import unittest
from mcp import ClientSession, StdioServerParameters
from mcp.types import TextContent

_server_params = StdioServerParameters(
    command="uv",
    args=[
        "run",
        "-m",
        "nabchan_mcp_server.main",
        "--db_file=test.db",
    ],
)


class IntegrationTestMcpServer(unittest.IsolatedAsyncioTestCase):
    async def test_list_tools(self):
        async with (
            stdio_client(_server_params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            tools = set([tool.name for tool in (await session.list_tools()).tools])
            self.assertSetEqual(tools, {"read_document", "search_document"})

    async def test_read_document(self):
        async with (
            stdio_client(_server_params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            response = await session.call_tool(
                "read_document",
                arguments={"url": "https://example.com/1"},
            )
            self.assertEqual(len(response.content), 1)
            self.assertIsInstance(response.content[0], TextContent)
            text_content = cast(TextContent, response.content[0])
            self.assertEqual(text_content.text, "# 猫はかわいい")

    async def test_search_documents(self):
        async with (
            stdio_client(_server_params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            response = await session.call_tool(
                "search_document",
                arguments={
                    "search_query": "猫はかわいい",
                    "result_limit": 3,
                },
            )
            self.assertEqual(len(response.content), 1)
            self.assertIsInstance(response.content[0], TextContent)
            text_content = cast(TextContent, response.content[0])
            docs = json.loads(text_content.text)
            self.assertIsInstance(docs, list)
            self.assertEqual(len(docs), 3)
            self.assertEqual(len(docs[0]), 3)
            self.assertIn("url", docs[0])
            self.assertIn("title", docs[0])
            self.assertIn("description", docs[0])
