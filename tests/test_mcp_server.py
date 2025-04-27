import json
from mcp.client.stdio import stdio_client
import unittest
from mcp import ClientSession, StdioServerParameters
from mcp.types import TextContent

_server_params = StdioServerParameters(
    command="docker",
    args=[
        "run",
        "-i",
        "--rm",
        "--network",
        "none",
        "-e",
        "TRANSPORT=stdio",
        "nabchan-mcp-server",
    ],
)


class TestSearchDocuments(unittest.IsolatedAsyncioTestCase):
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
                arguments={
                    "url": "https://nablarch.github.io/docs/LATEST/doc/about_nablarch/concept.html"
                },
            )
            self.assertEqual(len(response.content), 1)

    async def test_search_documents(self):
        async with (
            stdio_client(_server_params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            response = await session.call_tool(
                "search_document",
                arguments={
                    "search_query": "Nablarchのコンセプトを知りたい。",
                    "result_limit": 3,
                },
            )
            self.assertEqual(len(response.content), 1)
            self.assertIsInstance(response.content[0], TextContent)
            docs = json.loads(response.content[0].text)
            self.assertIsInstance(docs, list)
            self.assertEqual(len(docs), 3)
