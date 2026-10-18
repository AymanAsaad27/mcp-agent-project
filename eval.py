
import asyncio
import json
import sys
import time
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ollama import AsyncClient


ROOT = Path(__file__).resolve().parent
MODEL = "qwen2.5:7b"

SERVER_FILES = {
    "sqlite": ROOT / "servers" / "sqlite_server.py",
    "files": ROOT / "servers" / "files_server.py",
    "weather": ROOT / "servers" / "weather_server.py",
}

SYSTEM_PROMPT = """
You are a local AI assistant with access to three MCP servers.

Use tools when a request requires information from the shop database,
workspace files, or current weather.

Do not use tools for ordinary arithmetic or general knowledge that
you can answer directly.

Choose the appropriate tool and provide its required arguments.
Never claim you executed a tool. This evaluation checks tool selection
and arguments only; selected tools will not actually be executed.

- When listing the workspace root, pass relative_path=".".
- Never pass an empty string as a filesystem path.


"""

TEST_CASES = [
    {
        "id": "sqlite_list",
        "prompt": "List the tables available in the shop database.",
        "expected_tools": ["sqlite__list_tables"],
        "expected_arguments": {},
    },
    {
        "id": "sqlite_describe",
        "prompt": "Show me the columns in the products table.",
        "expected_tools": ["sqlite__describe_table"],
        "expected_arguments": {
            "sqlite__describe_table": {"table_name": "products"}
        },
    },
    {
        "id": "sqlite_query",
        "prompt": "How many orders are in the shop database?",
        "expected_tools": ["sqlite__query_database"],
        "expected_arguments": {
            "sqlite__query_database": {
                "sql_contains": ["select", "count", "orders"]
            }
        },
    },
    {
        "id": "files_list",
        "prompt": "List the files and folders in my workspace root.",
        "expected_tools": ["files__list_files"],
        "expected_arguments": {
            "files__list_files": {"relative_path": "."}
        },
    },
    {
        "id": "files_read",
        "prompt": (
            "Read company_handbook.md and tell me the working hours."
        ),
        "expected_tools": ["files__read_file"],
        "expected_arguments": {
            "files__read_file": {
                "relative_path": "company_handbook.md"
            }
        },
    },
    {
        "id": "files_write",
        "prompt": (
            "Save the exact sentence 'Evaluation note' to "
            "notes/evaluation_note.txt."
        ),
        "expected_tools": ["files__write_file"],
        "expected_arguments": {
            "files__write_file": {
                "relative_path": "notes/evaluation_note.txt",
                "content_contains": ["Evaluation note"],
            }
        },
    },
    {
        "id": "weather",
        "prompt": "What is the current weather in Singapore?",
        "expected_tools": ["weather__get_weather"],
        "expected_arguments": {
            "weather__get_weather": {"city": "Singapore"}
        },
    },
    {
        "id": "no_tool_math",
        "prompt": "What is 17 multiplied by 23?",
        "expected_tools": [],
        "expected_arguments": {},
    },
    {
        "id": "no_tool_general",
        "prompt": "In one sentence, explain what MCP stands for.",
        "expected_tools": [],
        "expected_arguments": {},
    },
]


def check_arguments(actual, expected):
    """Check expected argument values or required substrings."""
    if not isinstance(actual, dict):
        return False, "Tool arguments are not an object."

    for key, expected_value in expected.items():
        if key.endswith("_contains"):
            argument_name = key[:-9]
            actual_value = actual.get(argument_name)

            if not isinstance(actual_value, str):
                return False, f"Missing text argument: {argument_name}"

            actual_text = actual_value.casefold()
            missing = [
                item for item in expected_value
                if item.casefold() not in actual_text
            ]
            if missing:
                return False, (
                    f"{argument_name} is missing expected text: {missing}"
                )
        else:
            actual_value = actual.get(key)

            if isinstance(actual_value, str) and isinstance(
                expected_value, str
            ):
                matches = actual_value.casefold() == expected_value.casefold()
            else:
                matches = actual_value == expected_value

            if not matches:
                return False, (
                    f"{key}: expected {expected_value!r}, "
                    f"got {actual_value!r}"
                )

    return True, "Arguments matched."


async def main():
    ollama = AsyncClient(host="http://127.0.0.1:11434", trust_env=False)

    async with AsyncExitStack() as stack:
        sessions = {}
        ollama_tools = []

        for server_name, server_path in SERVER_FILES.items():
            if not server_path.exists():
                raise FileNotFoundError(
                    f"Server file not found: {server_path}"
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

            discovered = await session.list_tools()

            for tool in discovered.tools:
                ollama_tools.append({
                    "type": "function",
                    "function": {
                        "name": f"{server_name}__{tool.name}",
                        "description": tool.description or tool.name,
                        "parameters": tool.inputSchema,
                    },
                })

            print(
                f"Connected to {server_name}: "
                f"{len(discovered.tools)} tool(s)"
            )

        print(f"\nModel: {MODEL}")
        print(f"Discovered tools: {len(ollama_tools)}")
        print(f"Evaluation cases: {len(TEST_CASES)}\n")

        results = []

        for index, case in enumerate(TEST_CASES, start=1):
            start = time.perf_counter()

            try:
                response = await ollama.chat(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": case["prompt"]},
                    ],
                    tools=ollama_tools,
                    options={"temperature": 0},
                )

                message = response.message
                calls = message.tool_calls or []

                actual_calls = []
                for call in calls:
                    actual_calls.append({
                        "name": call.function.name,
                        "arguments": call.function.arguments or {},
                    })

                actual_tools = sorted(
                    item["name"] for item in actual_calls
                )
                expected_tools = sorted(case["expected_tools"])

                selection_ok = actual_tools == expected_tools
                argument_checks = {}
                arguments_ok = True

                for tool_name, expected_args in (
                    case["expected_arguments"].items()
                ):
                    matching_calls = [
                        item for item in actual_calls
                        if item["name"] == tool_name
                    ]

                    if not matching_calls:
                        ok, detail = False, "Expected tool was not selected."
                    else:
                        ok, detail = check_arguments(
                            matching_calls[0]["arguments"],
                            expected_args,
                        )

                    argument_checks[tool_name] = {
                        "passed": ok,
                        "detail": detail,
                    }
                    arguments_ok = arguments_ok and ok

                passed = selection_ok and arguments_ok

                result = {
                    "id": case["id"],
                    "prompt": case["prompt"],
                    "expected_tools": expected_tools,
                    "actual_tools": actual_tools,
                    "actual_calls": actual_calls,
                    "selection_passed": selection_ok,
                    "argument_checks": argument_checks,
                    "passed": passed,
                    "elapsed_seconds": round(
                        time.perf_counter() - start, 2
                    ),
                    "error": None,
                }

            except Exception as exc:
                result = {
                    "id": case["id"],
                    "prompt": case["prompt"],
                    "expected_tools": sorted(case["expected_tools"]),
                    "actual_tools": [],
                    "actual_calls": [],
                    "selection_passed": False,
                    "argument_checks": {},
                    "passed": False,
                    "elapsed_seconds": round(
                        time.perf_counter() - start, 2
                    ),
                    "error": f"{type(exc).__name__}: {exc}",
                }

            results.append(result)
            status = "PASS" if result["passed"] else "FAIL"

            print(
                f"[{index}/{len(TEST_CASES)}] {status} | "
                f"{case['id']} | {result['elapsed_seconds']:.2f}s"
            )
            print(f"  Expected: {result['expected_tools']}")
            print(f"  Actual:   {result['actual_tools']}")

            for tool_name, check in result["argument_checks"].items():
                print(
                    f"  Arguments ({tool_name}): "
                    f"{'PASS' if check['passed'] else 'FAIL'} — "
                    f"{check['detail']}"
                )

            if result.get("error"):
                print(f"  Error: {result['error']}")

            print()

        total = len(results)
        passed_count = sum(item["passed"] for item in results)
        selection_passes = sum(
            item["selection_passed"] for item in results
        )
        accuracy = passed_count / total * 100 if total else 0
        selection_accuracy = (
            selection_passes / total * 100 if total else 0
        )

        report = {
            "model": MODEL,
            "evaluation_type": (
                "first-turn tool selection and argument validation"
            ),
            "total_cases": total,
            "passed": passed_count,
            "failed": total - passed_count,
            "selection_passes": selection_passes,
            "selection_accuracy_percent": round(
                selection_accuracy, 2
            ),
            "combined_accuracy_percent": round(accuracy, 2),
            "results": results,
        }

        output_path = ROOT / "eval_results.json"
        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print("=" * 55)
        print("EVALUATION SUMMARY")
        print("=" * 55)
        print(f"Model:                {MODEL}")
        print(f"Cases passed:         {passed_count}/{total}")
        print(f"Tool selection passes:{selection_passes}/{total}")
        print(f"Selection accuracy:   {selection_accuracy:.2f}%")
        print(f"Combined accuracy:    {accuracy:.2f}%")
        print(f"Report: {output_path}")
        print(
            "\nSelected tools are not executed. "
            "This measures tool choice and argument matching only."
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nEvaluation interrupted.")
