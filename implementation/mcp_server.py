import os
import json
from typing import Any, Dict, List, Optional
from fastmcp import FastMCP
from db import SQLiteAdapter, ValidationError

# Initialize FastMCP Server
mcp = FastMCP("sqlite-lab")

# Determine DB path dynamically relative to this file
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../sqlite_lab.db"))
adapter = SQLiteAdapter(db_path=DB_PATH)

@mcp.tool(name="search")
def search(
    table: str,
    filters: Optional[Any] = None,
    columns: Optional[List[str]] = None,
    limit: int = 20,
    offset: int = 0,
    order_by: Optional[str] = None,
    descending: bool = False
) -> str:
    """
    Search and retrieve rows from a database table with support for filters, ordering, and pagination.

    :param table: Name of the table to search (e.g. 'students', 'courses', 'enrollments')
    :param filters: Dict of equality filters (e.g., {"cohort": "A1"}) or a List of filter dicts 
                    containing "column", "operator", "value" (e.g., [{"column": "score", "operator": ">=", "value": 90}])
                    Supported operators: '=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN'
    :param columns: List of column names to return (selects all columns if not specified)
    :param limit: Maximum number of rows to return (default is 20)
    :param offset: Pagination offset (default is 0)
    :param order_by: Column name to sort by (optional)
    :param descending: Set to True for descending order, False for ascending (default is False)
    """
    try:
        results = adapter.search(
            table=table,
            columns=columns,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending
        )
        return json.dumps(results, indent=2)
    except ValidationError as e:
        return f"Validation Error: {str(e)}"
    except Exception as e:
        return f"Unexpected Error: {str(e)}"


@mcp.tool(name="insert")
def insert(table: str, values: Dict[str, Any]) -> str:
    """
    Insert a new row into a database table.

    :param table: Name of the table to insert into (e.g. 'students', 'courses', 'enrollments')
    :param values: Dictionary mapping column names to values for the new row (e.g. {"name": "Frank", "cohort": "A1", "email": "frank@example.com"})
    """
    try:
        inserted_row = adapter.insert(table=table, values=values)
        return json.dumps({
            "message": "Row inserted successfully.",
            "row": inserted_row
        }, indent=2)
    except ValidationError as e:
        return f"Validation Error: {str(e)}"
    except Exception as e:
        return f"Unexpected Error: {str(e)}"


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: Optional[str] = None,
    filters: Optional[Any] = None,
    group_by: Optional[List[str]] = None
) -> str:
    """
    Compute aggregate metrics on a table (e.g. count, avg, sum, min, max) with optional filtering and grouping.

    :param table: Name of the table (e.g. 'enrollments')
    :param metric: Aggregate function to run: 'count', 'avg', 'sum', 'min', 'max' (case-insensitive)
    :param column: Column name to apply the metric to (required for avg/sum/min/max, optional/defaults to '*' for count)
    :param filters: Dict of equality filters or List of filter dicts (same schema as search)
    :param group_by: Optional list of column names to group the results by (e.g. ['student_id'])
    """
    try:
        results = adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filters,
            group_by=group_by
        )
        return json.dumps(results, indent=2)
    except ValidationError as e:
        return f"Validation Error: {str(e)}"
    except Exception as e:
        return f"Unexpected Error: {str(e)}"


@mcp.resource("schema://database")
def database_schema() -> str:
    """
    Returns the complete schema of the database, detailing all tables and their columns.
    """
    try:
        schema = adapter.get_schema()
        return json.dumps({
            "schema_type": "database_schema",
            "tables": schema
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to retrieve database schema: {str(e)}"}, indent=2)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """
    Returns the schema definition for a specific table.

    :param table_name: The table to retrieve schema information for
    """
    try:
        adapter.validate_table(table_name)
        schema = adapter.get_schema()
        columns = schema.get(table_name, [])
        return json.dumps({
            "table_name": table_name,
            "columns": columns
        }, indent=2)
    except ValidationError as e:
        return json.dumps({"error": f"Validation Error: {str(e)}"}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Unexpected Error: {str(e)}"}, indent=2)


if __name__ == "__main__":
    mcp.run()
