# SQLite Database MCP Server Lab

This Model Context Protocol (MCP) server connects to a local SQLite database containing students, courses, and enrollment information. It is built using Python and the `FastMCP` framework.

## Requirements

- Python 3.10+
- `uv` (recommended for dependency-free execution) or `pip`

## File Structure

- `db.py`: Database adaptor layer handling SQLite connection, querying, inserting, aggregates, and strict validation.
- `init_db.py`: SQLite initialization script to create the DB file and seed initial data.
- `mcp_server.py`: FastMCP server entrypoint exposing tools and resources.
- `start_inspector.sh`: Helper shell script to launch the Model Context Protocol Inspector.
- `tests/test_server.py`: Unit tests checking core database features and server handlers.

---

## 1. Setup Database

Initialize and seed the database by running:

```bash
python3 init_db.py
```

This creates the database file `sqlite_lab.db` in the project root with the following tables:
- `students`: `id` (INTEGER PRIMARY KEY), `name` (TEXT), `cohort` (TEXT), `email` (TEXT UNIQUE)
- `courses`: `id` (INTEGER PRIMARY KEY), `title` (TEXT), `instructor` (TEXT), `credits` (INTEGER)
- `enrollments`: `student_id` (INTEGER), `course_id` (INTEGER), `grade` (TEXT), `score` (REAL)

---

## 2. Running & Testing Locally

### Option A: Ephemeral run via `uv` (No setup required)

To run the automated test suite without installing python packages globally:

```bash
uv run --with fastmcp --with pytest python3 -m unittest tests/test_server.py
```

### Option B: Local Virtual Environment (`.venv`)

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install packages:
   ```bash
   pip install fastmcp pytest
   ```
3. Run tests:
   ```bash
   python3 -m unittest tests/test_server.py
   ```

---

## 3. MCP Resource & Tool Definitions

### Tools

1. **`search`**: Retrieve rows matching filters. Supports:
   - Filters: dict (e.g. `{"cohort": "A1"}`) or list of filters (e.g. `[{"column": "score", "operator": ">=", "value": 90.0}]`)
   - Operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `LIKE`, `IN`
   - Ordering: `order_by` column, `descending` boolean
   - Pagination: `limit` and `offset`
2. **`insert`**: Insert a new row. Requires `table` and `values` (dict). Returns the inserted payload with its generated ID. Empty values are rejected.
3. **`aggregate`**: Perform metrics (`count`, `avg`, `sum`, `min`, `max`) on columns. Supports `group_by` columns.

### Resources

- **`schema://database`**: Exposes the complete list of tables and column names.
- **`schema://table/{table_name}`**: Exposes columns of a specific table.

---

## 4. MCP Client Integration

### MCP Inspector

To test the server interactively using the visual tool:

```bash
./start_inspector.sh
```

### Gemini CLI

Register the server to your Gemini CLI:

```bash
gemini mcp add sqlite-lab uv --args "run,--with,fastmcp,python3,$(pwd)/mcp_server.py" --description "SQLite lab FastMCP server" --timeout 10000
```

Verify connection:
```bash
gemini mcp list
```

Ask Gemini to interact with the database:
```bash
gemini --allowed-mcp-server-names sqlite-lab --yolo -p "Use the sqlite-lab MCP server and show me students in cohort A1"
```

### Claude Code

Example `.mcp.json` config:

```json
{
  "mcpServers": {
    "sqlite-lab": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--with",
        "fastmcp",
        "python3",
        "/ABSOLUTE/PATH/TO/implementation/mcp_server.py"
      ]
    }
  }
}
```
