# Custom MCP Agent with Local Ollama

A Python AI agent that connects a locally running language model to custom Model Context Protocol (MCP) servers. It can discover tools dynamically and interact with a SQLite database, a sandboxed filesystem, and a live weather API.

## Features

- Local LLM inference using Qwen 2.5 7B through Ollama.
- Dynamic MCP tool discovery and execution.
- Three independent MCP servers with seven tools.
- Read-only SQLite database access.
- Sandboxed workspace file operations.
- Live weather data using the Open-Meteo API.
- Automated tests and a tool-selection evaluation harness.

## Architecture

```text
User
  |
  v
Python Agent Client <----> Ollama (Qwen 2.5 7B)
  |
  v
MCP Client
  |
  +-- SQLite Server
  |     +-- list_tables
  |     +-- describe_table
  |     +-- query_database
  |
  +-- Filesystem Server
  |     +-- list_files
  |     +-- read_file
  |     +-- write_file
  |
  +-- Weather Server
        +-- get_weather
```

The client discovers tools from the MCP servers, makes their definitions available to the model, executes selected tool calls, and returns results to the model.

## Technology Stack

- Python
- Ollama and Qwen 2.5 7B
- Model Context Protocol (MCP)
- SQLite
- httpx
- pytest
- Open-Meteo API

## Project Structure

```text
mcp-agent-project/
├── client/
│   └── client.py
├── servers/
│   ├── sqlite_server.py
│   ├── files_server.py
│   └── weather_server.py
├── data/
│   └── shop.db
├── workspace/
├── tests/
│   ├── test_servers.py
│   └── test_mcp_integration.py
├── seed_db.py
├── eval.py
├── requirements.txt
├── pytest.ini
├── .gitignore
└── README.md
```

The SQLite database is generated locally and is not committed to Git.

## MCP Tools

### SQLite Server

| Tool | Description |
|---|---|
| `list_tables` | Lists database tables. |
| `describe_table` | Describes a table's columns. |
| `query_database` | Executes permitted read-only SQL queries. |

### Filesystem Server

| Tool | Description |
|---|---|
| `list_files` | Lists files and directories in the workspace. |
| `read_file` | Reads a workspace file. |
| `write_file` | Creates or updates a workspace file. |

### Weather Server

| Tool | Description |
|---|---|
| `get_weather` | Retrieves current weather for a city through Open-Meteo. |

## Setup

### Requirements

- Python 3.14, matching the development environment.
- Ollama installed and running.
- The `qwen2.5:7b` model downloaded.
- Internet access for package installation and weather requests.

### Windows PowerShell

Clone the repository after it has been published, replacing the placeholders with your actual repository details:

```powershell
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
```

Alternatively, navigate to your existing local project directory.

Create and activate a virtual environment:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Download the model:

```powershell
ollama pull qwen2.5:7b
```

Create the sample database:

```powershell
python .\seed_db.py
```

Start the agent:

```powershell
python .\client\client.py
```

Example prompts:

- List the tables in the shop database.
- Which three products have the highest prices?
- Read the company handbook and tell me the refund policy.
- List the files in my workspace root.
- What is the current weather in Singapore?

Enter `exit` to quit.

## Testing

Run the automated tests:

```powershell
python -m pytest -q
```

Latest verified result: **22 tests passed**.

## Tool-Selection Evaluation

Run:

```powershell
python .\eval.py
```

Latest verified results using Qwen 2.5 7B:

- Evaluation cases passed: 9/9.
- Tool-selection cases passed: 9/9.
- Combined tool-selection and argument checks: 9/9.
- Applicable argument checks passed: 5/5.

The evaluation covers database, filesystem, and weather tool selection, as well as prompts that should not require tools.

**Limitations:** This evaluation checks first-turn tool selection and argument matching. It does not execute the selected tools or evaluate final-answer quality. The nine test cases are a small, fixed sample and do not establish general accuracy.

The report is saved to `eval_results.json`.

## Security and Limitations

- SQLite is opened in read-only mode, and query results are limited.
- SQL validation provides additional restrictions but is not a complete SQL security boundary.
- Filesystem operations are restricted to the workspace directory.
- Weather requests depend on the external Open-Meteo service.
- Model-generated tool calls and answers can still be incorrect.
- This is a portfolio project, not a hardened production system.

## Future Improvements

- Expand evaluation with more prompts and edge cases.
- Test end-to-end task success and final-answer accuracy.
- Improve error recovery and structured logging.
- Compare tool-calling performance across different models.
- Add continuous integration for automated tests.

## Author

**Ayman Asaad**

GitHub: [AymanAsaad27](https://github.com/AymanAsaad27)

This project demonstrates practical experience building local LLM agents and connecting them to external capabilities through MCP.
