import os
import sys
import unittest
import json

# Ensure parent directory is in path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db import SQLiteAdapter, ValidationError
from init_db import create_database

class TestSQLiteAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a test database specifically for tests
        cls.test_db_path = "test_sqlite_lab.db"
        create_database(cls.test_db_path)
        cls.adapter = SQLiteAdapter(cls.test_db_path)

    @classmethod
    def tearDownClass(cls):
        # Clean up test database
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)

    def test_schema_loading(self):
        schema = self.adapter.get_schema()
        self.assertIn("students", schema)
        self.assertIn("courses", schema)
        self.assertIn("enrollments", schema)
        self.assertIn("name", schema["students"])
        self.assertIn("title", schema["courses"])

    def test_search_valid(self):
        # Test searching for students in cohort A1
        results = self.adapter.search(
            table="students",
            filters={"cohort": "A1"},
            order_by="name"
        )
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["name"], "Alice Nguyen")
        self.assertEqual(results[1]["name"], "Bob Tran")

    def test_search_advanced_filters(self):
        # Test searching enrollments with score >= 90
        results = self.adapter.search(
            table="enrollments",
            filters=[{"column": "score", "operator": ">=", "value": 90.0}]
        )
        self.assertEqual(len(results), 5)
        for r in results:
            self.assertTrue(r["score"] >= 90.0)

    def test_search_invalid_table(self):
        with self.assertRaises(ValidationError) as context:
            self.adapter.search(table="invalid_table")
        self.assertIn("Unknown table", str(context.exception))

    def test_search_invalid_column(self):
        with self.assertRaises(ValidationError) as context:
            self.adapter.search(table="students", columns=["invalid_column"])
        self.assertIn("Unknown column", str(context.exception))

    def test_insert_valid(self):
        # Test inserting a new student
        val = {
            "name": "Frank Miller",
            "cohort": "B2",
            "email": "frank@example.com"
        }
        res = self.adapter.insert("students", val)
        self.assertIsNotNone(res.get("id"))
        self.assertEqual(res["name"], "Frank Miller")

        # Verify insertion using search
        search_res = self.adapter.search("students", filters={"email": "frank@example.com"})
        self.assertEqual(len(search_res), 1)
        self.assertEqual(search_res[0]["name"], "Frank Miller")

    def test_insert_empty_rejection(self):
        with self.assertRaises(ValidationError) as context:
            self.adapter.insert("students", {})
        self.assertIn("Insert values cannot be empty", str(context.exception))

    def test_insert_invalid_col_rejection(self):
        with self.assertRaises(ValidationError) as context:
            self.adapter.insert("students", {"invalid_col": "value"})
        self.assertIn("Unknown column", str(context.exception))

    def test_aggregate_valid_count(self):
        res = self.adapter.aggregate(table="students", metric="count")
        self.assertEqual(len(res), 1)
        # Should contain 5 seeded students
        self.assertEqual(res[0]["value"], 5)

    def test_aggregate_group_by(self):
        # Test average score by cohort
        # Joint query via search might be standard, but aggregate on enrollments grouped by student cohort
        # Let's aggregate average score on enrollments grouped by course_id
        res = self.adapter.aggregate(
            table="enrollments",
            metric="avg",
            column="score",
            group_by="course_id"
        )
        self.assertEqual(len(res), 3)  # 3 courses seeded

    def test_aggregate_invalid_metric(self):
        with self.assertRaises(ValidationError) as context:
            self.adapter.aggregate(table="students", metric="invalid_metric")
        self.assertIn("Unsupported metric", str(context.exception))


class TestMCPServerHandlers(unittest.TestCase):
    """Smoke tests for FastMCP server entrypoints/handlers."""
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = "test_sqlite_lab.db"
        create_database(cls.test_db_path)
        # Point server adapter to test DB
        import mcp_server
        mcp_server.adapter = SQLiteAdapter(cls.test_db_path)
        cls.mcp_server = mcp_server

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)

    def test_schema_database_resource(self):
        # Retrieve schema://database resource content
        res = self.mcp_server.database_schema()
        data = json.loads(res)
        self.assertEqual(data["schema_type"], "database_schema")
        self.assertIn("students", data["tables"])

    def test_schema_table_resource(self):
        # Retrieve schema://table/students
        res = self.mcp_server.table_schema("students")
        data = json.loads(res)
        self.assertEqual(data["table_name"], "students")
        self.assertIn("name", data["columns"])

    def test_schema_table_resource_invalid(self):
        res = self.mcp_server.table_schema("invalid_table")
        data = json.loads(res)
        self.assertIn("error", data)
        self.assertIn("Unknown table", data["error"])

    def test_search_tool_handler(self):
        res_str = self.mcp_server.search(table="students", filters={"cohort": "A1"})
        rows = json.loads(res_str)
        self.assertEqual(len(rows), 3)

if __name__ == "__main__":
    unittest.main()
