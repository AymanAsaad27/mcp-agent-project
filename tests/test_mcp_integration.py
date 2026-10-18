
import asyncio
import json
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[1]

SERVER_FILES = {
    "sqlite": ROOT / "servers" / "sqlite_server.py",
    "files": ROOT / "servers" / "files_server.py",
    "weather": ROOT / "servers" / "weather_server.py",
}


def result_data(result):
    """Extract structured data from an MCP tool result."""
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured

    text_parts = [
        item.text
        for item in result.content
        if hasattr(item, "text")
    ]

    if not text_parts:
        raise AssertionError("MCP tool returned no readable content.")

    return json.loads("\n".join(text_parts))


def test_mcp_servers_end_to_end():
    asyncio.run(_test_mcp_servers_end_to_end())


async def _test_mcp_servers_end_to_end():
    async with AsyncExitStack() as stack:
        sessions = {}

        # Start each real server and establish an MCP stdio connection.
        for server_name, server_path in SERVER_FILES.items():
            assert server_path.exists(), (
                f"Missing server file: {server_path}"
            )

            parameters = StdioServerParameters(
                command=sys.executable,
                args=[str(server_path)],
                cwd=str(ROOT),
            )

            read_stream, write_stream = (
                await stack.enter_async_context(
                    stdio_client(parameters)
                )
            )

            session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            await session.initialize()
            sessions[server_name] = session

        # Verify dynamic tool discovery.
        expected_tools = {
            "sqlite": {
                "list_tables",
                "describe_table",
                "query_database",
            },
            "files": {
                "list_files",
                "read_file",
                "write_file",
            },
            "weather": {
                "get_weather",
            },
        }

        for server_name, expected in expected_tools.items():
            response = await sessions[server_name].list_tools()
            discovered = {tool.name for tool in response.tools}

            assert discovered == expected, (
                f"{server_name}: expected {expected}, got {discovered}"
            )

        # SQLite: call tools through the MCP protocol.
        tables_result = await sessions["sqlite"].call_tool(
            "list_tables",
            arguments={},
        )
        assert not tables_result.isError

        tables_data = result_data(tables_result)
        assert {"customers", "products", "orders"} <= set(
            tables_data["tables"]
        )

        query_result = await sessions["sqlite"].call_tool(
            "query_database",
            arguments={
                "sql": "SELECT COUNT(*) AS total FROM orders"
            },
        )
        assert not query_result.isError

        query_data = result_data(query_result)
        assert query_data["rows"][0]["total"] == 60

        # Filesystem: read a real file through MCP.
        file_result = await sessions["files"].call_tool(
            "read_file",
            arguments={"relative_path": "company_handbook.md"},
        )
        assert not file_result.isError

        file_data = result_data(file_result)
        assert "Working Hours" in file_data["content"]
        assert "7 business days" in file_data["content"]

        # Weather: test validation without making a network request.
        weather_result = await sessions["weather"].call_tool(
            "get_weather",
            arguments={"city": "   "},
        )
        assert weather_result.isError, (
            "Expected the weather server to reject an empty city."
        )
