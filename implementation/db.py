import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union

class ValidationError(Exception):
    """Raised when a query or request validation fails to prevent unsafe execution."""
    pass

class SQLiteAdapter:
    def __init__(self, db_path: str = "sqlite_lab.db"):
        self.db_path = os.path.abspath(db_path)
        self.schema_cache: Dict[str, List[str]] = {}
        self.refresh_schema_cache()

    def connect(self) -> sqlite3.Connection:
        """Establishes and returns a connection with Row factory enabled."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found at {self.db_path}. Please initialize the database first.")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def refresh_schema_cache(self):
        """Fetches active tables and columns to populate/refresh the validation cache."""
        if not os.path.exists(self.db_path):
            return
        
        conn = self.connect()
        try:
            # Query non-system tables
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row["name"] for row in cursor.fetchall()]
            
            new_cache = {}
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table});")  # table name is from system catalog, safe
                columns = [row["name"] for row in cursor.fetchall()]
                new_cache[table] = columns
                
            self.schema_cache = new_cache
        finally:
            conn.close()

    def get_schema(self) -> Dict[str, List[str]]:
        """Returns the cached database schema."""
        self.refresh_schema_cache()
        return self.schema_cache

    def validate_table(self, table: str):
        """Ensures the table exists in the schema cache."""
        self.refresh_schema_cache()
        if table not in self.schema_cache:
            raise ValidationError(f"Unknown table: '{table}'. Available tables are: {list(self.schema_cache.keys())}")

    def validate_column(self, table: str, column: str):
        """Ensures the column exists in the specified table."""
        self.validate_table(table)
        if column not in self.schema_cache[table]:
            raise ValidationError(f"Unknown column: '{column}' in table '{table}'. Available columns: {self.schema_cache[table]}")

    def _parse_filters(self, table: str, filters: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]) -> Tuple[str, List[Any]]:
        """
        Parses filter arguments and returns a tuple (sql_clause, params).
        Supported operators: '=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN'
        """
        if not filters:
            return "", []

        clauses = []
        params = []
        allowed_operators = {"=", "!=", ">", "<", ">=", "<=", "LIKE", "IN"}

        # Normalize dictionary filter to a list of filters
        normalized_filters = []
        if isinstance(filters, dict):
            for col, val in filters.items():
                normalized_filters.append({
                    "column": col,
                    "operator": "=",
                    "value": val
                })
        elif isinstance(filters, list):
            normalized_filters = filters
        else:
            raise ValidationError("Filters must be a dictionary or a list of dictionaries.")

        for f in normalized_filters:
            if not isinstance(f, dict):
                raise ValidationError("Each filter must be a dictionary.")
            
            col = f.get("column")
            op = f.get("operator", "=").upper()
            val = f.get("value")

            if col is None:
                raise ValidationError("Filter missing 'column' field.")
            
            self.validate_column(table, col)

            if op not in allowed_operators:
                raise ValidationError(f"Unsupported filter operator: '{op}'. Allowed: {list(allowed_operators)}")

            if op == "IN":
                if not isinstance(val, (list, tuple)):
                    raise ValidationError("Value for 'IN' operator must be a list or tuple.")
                if not val:
                    raise ValidationError("Value for 'IN' operator cannot be empty.")
                placeholders = ", ".join("?" for _ in val)
                clauses.append(f"{col} IN ({placeholders})")
                params.extend(val)
            else:
                clauses.append(f"{col} {op} ?")
                params.append(val)

        where_clause = " WHERE " + " AND ".join(clauses) if clauses else ""
        return where_clause, params

    def search(
        self,
        table: str,
        columns: Optional[List[str]] = None,
        filters: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
        limit: int = 20,
        offset: int = 0,
        order_by: Optional[str] = None,
        descending: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Safely searches the database and returns matching rows as a list of dicts.
        """
        self.validate_table(table)

        # Validate columns
        if columns:
            for col in columns:
                self.validate_column(table, col)
            selected_cols = ", ".join(columns)
        else:
            selected_cols = "*"

        # Build filter clause
        where_clause, params = self._parse_filters(table, filters)

        # Build order by clause
        order_clause = ""
        if order_by:
            self.validate_column(table, order_by)
            direction = "DESC" if descending else "ASC"
            order_clause = f" ORDER BY {order_by} {direction}"

        # Limit and Offset validation & parameterization
        if not isinstance(limit, int) or limit < 0:
            raise ValidationError("Limit must be a non-negative integer.")
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("Offset must be a non-negative integer.")

        sql = f"SELECT {selected_cols} FROM {table}{where_clause}{order_clause} LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def insert(self, table: str, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safely inserts a row and returns the inserted payload.
        """
        self.validate_table(table)
        
        if not values:
            raise ValidationError("Insert values cannot be empty.")

        for col in values.keys():
            self.validate_column(table, col)

        columns_str = ", ".join(values.keys())
        placeholders = ", ".join("?" for _ in values)
        params = list(values.values())

        sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders});"

        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            last_id = cursor.lastrowid
            conn.commit()
            
            # Retrieve the inserted row
            # If the table has an auto-increment integer primary key (like id), we fetch by id
            # Otherwise we fetch by the matching fields
            if last_id and "id" in self.schema_cache[table]:
                cursor.execute(f"SELECT * FROM {table} WHERE id = ?", (last_id,))
            else:
                # Query by all columns matching the inserted values
                where_clauses = [f"{col} = ?" for col in values.keys()]
                where_sql = " AND ".join(where_clauses)
                cursor.execute(f"SELECT * FROM {table} WHERE {where_sql} ORDER BY rowid DESC LIMIT 1", params)
                
            row = cursor.fetchone()
            return dict(row) if row else values
        except sqlite3.IntegrityError as e:
            raise ValidationError(f"Database integrity error: {str(e)}")
        finally:
            conn.close()

    def aggregate(
        self,
        table: str,
        metric: str,
        column: Optional[str] = None,
        filters: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
        group_by: Optional[Union[str, List[str]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Safely calculates aggregates (count, avg, sum, min, max) and returns rows.
        """
        self.validate_table(table)

        allowed_metrics = {"count", "avg", "sum", "min", "max"}
        metric_lower = metric.lower()
        if metric_lower not in allowed_metrics:
            raise ValidationError(f"Unsupported metric: '{metric}'. Allowed: {list(allowed_metrics)}")

        # Validate column
        if column == "*" or not column:
            if metric_lower != "count":
                raise ValidationError(f"Column '*' or None is only valid with 'count' metric, not '{metric}'.")
            target_col = "*"
        else:
            self.validate_column(table, column)
            target_col = column

        # Build group_by clause and list of columns
        select_group_cols = ""
        group_clause = ""
        if group_by:
            if isinstance(group_by, str):
                group_cols = [group_by]
            elif isinstance(group_by, list):
                group_cols = group_by
            else:
                raise ValidationError("Group_by must be a string or list of strings.")

            for g_col in group_cols:
                self.validate_column(table, g_col)
            
            select_group_cols = ", ".join(group_cols) + ", "
            group_clause = " GROUP BY " + ", ".join(group_cols)

        # Build filters
        where_clause, params = self._parse_filters(table, filters)

        sql = f"SELECT {select_group_cols}{metric_lower}({target_col}) AS value FROM {table}{where_clause}{group_clause}"

        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
