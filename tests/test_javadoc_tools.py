"""Tests for Javadoc MCP tools."""

import unittest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import duckdb
from nabchan_mcp_server.javadoc.tools import JavadocTools
from nabchan_mcp_server.javadoc.operations import (
    JavadocDbOperations,
    JavadocPackage,
    JavadocClass,
    JavadocMethod
)


class TestJavadocTools(unittest.TestCase):
    """Test cases for JavadocTools."""
    
    def setUp(self):
        """Set up test database with sample data."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.conn = duckdb.connect(self.temp_db.name)
        
        # Set up test data
        operations = JavadocDbOperations(self.conn)
        operations.create_tables()
        
        # Add sample data
        package = JavadocPackage(
            name="com.example.test",
            version="TEST",
            summary="Test package for unit tests"
        )
        operations.insert_package(package)
        
        javadoc_class = JavadocClass(
            name="com.example.test.TestClass",
            package_name="com.example.test",
            version="TEST",
            type="class",
            summary="A test class"
        )
        operations.insert_class(javadoc_class)
        
        method1 = JavadocMethod(
            name="testMethod",
            class_name="com.example.test.TestClass",
            version="TEST",
            signature="testMethod(String param)",
            modifiers="public",
            summary="A test method",
            type="method"
        )
        method2 = JavadocMethod(
            name="anotherMethod",
            class_name="com.example.test.TestClass",
            version="TEST",
            signature="anotherMethod()",
            modifiers="private",
            summary="Another method",
            type="method"
        )
        operations.insert_method(method1)
        operations.insert_method(method2)
        
        self.conn.close()
        
    def tearDown(self):
        """Clean up test database."""
        Path(self.temp_db.name).unlink()
        
    @patch('nabchan_mcp_server.javadoc.tools.connect_db')
    def test_list_packages(self, mock_connect_db):
        """Test listing packages."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_connect_db.return_value.__enter__.return_value = mock_conn
        
        # Set up mock return value
        mock_conn.execute.return_value.fetchall.return_value = [
            ("com.example.test", "Test package for unit tests"),
            ("com.example.another", "Another test package")
        ]
        
        tools = JavadocTools()
        
        # Run async test
        async def run_test():
            result = await tools.list_packages("TEST")
            return result
        
        result = asyncio.run(run_test())
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], "com.example.test")
        self.assertEqual(result[0]['summary'], "Test package for unit tests")
        
    @patch('nabchan_mcp_server.javadoc.tools.connect_db')
    def test_list_packages_error(self, mock_connect_db):
        """Test listing packages with error."""
        # Mock database connection to raise exception
        mock_connect_db.side_effect = Exception("Database error")
        
        tools = JavadocTools()
        
        async def run_test():
            result = await tools.list_packages("TEST")
            return result
        
        result = asyncio.run(run_test())
        
        self.assertEqual(len(result), 1)
        self.assertIn("error", result[0])
        self.assertEqual(result[0]["error"], "Database error")
        
    @patch('nabchan_mcp_server.javadoc.tools.connect_db')
    def test_get_package_details(self, mock_connect_db):
        """Test getting package details."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_connect_db.return_value.__enter__.return_value = mock_conn
        
        # Mock package query
        mock_conn.execute.return_value.fetchone.side_effect = [
            ("Test package for unit tests",),  # package summary
        ]
        
        # Mock classes query
        mock_conn.execute.return_value.fetchall.return_value = [
            ("com.example.test.TestClass", "class", "A test class"),
        ]
        
        tools = JavadocTools()
        
        async def run_test():
            result = await tools.get_package_details("com.example.test", "TEST")
            return result
        
        result = asyncio.run(run_test())
        
        self.assertEqual(result['name'], "com.example.test")
        self.assertEqual(result['summary'], "Test package for unit tests")
        self.assertEqual(len(result['classes']), 1)
        self.assertEqual(result['classes'][0]['name'], "com.example.test.TestClass")
        
    @patch('nabchan_mcp_server.javadoc.tools.connect_db')
    def test_get_package_details_not_found(self, mock_connect_db):
        """Test getting package details for non-existent package."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_connect_db.return_value.__enter__.return_value = mock_conn
        
        # Mock empty result
        mock_conn.execute.return_value.fetchone.return_value = None
        
        tools = JavadocTools()
        
        async def run_test():
            result = await tools.get_package_details("nonexistent", "TEST")
            return result
        
        result = asyncio.run(run_test())
        
        self.assertIn("error", result)
        self.assertIn("Package not found", result["error"])
        
    @patch('nabchan_mcp_server.javadoc.tools.connect_db')
    def test_get_class_details(self, mock_connect_db):
        """Test getting class details."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_connect_db.return_value.__enter__.return_value = mock_conn
        
        # Mock class query
        mock_conn.execute.return_value.fetchone.side_effect = [
            ("class", "A test class"),  # class type and summary
        ]
        
        # Mock methods query
        mock_conn.execute.return_value.fetchall.return_value = [
            ("testMethod", "testMethod(String param)", "public", "A test method", "method"),
            ("anotherMethod", "anotherMethod()", "private", "Another method", "method"),
        ]
        
        tools = JavadocTools()
        
        async def run_test():
            result = await tools.get_class_details("com.example.test.TestClass", "TEST")
            return result
        
        result = asyncio.run(run_test())
        
        self.assertEqual(result['name'], "com.example.test.TestClass")
        self.assertEqual(result['type'], "class")
        self.assertEqual(result['summary'], "A test class")
        self.assertEqual(len(result['methods']), 2)
        self.assertEqual(result['methods'][0]['name'], "testMethod")
        
    @patch('nabchan_mcp_server.javadoc.tools.connect_db')
    def test_get_class_details_not_found(self, mock_connect_db):
        """Test getting class details for non-existent class."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_connect_db.return_value.__enter__.return_value = mock_conn
        
        # Mock empty result
        mock_conn.execute.return_value.fetchone.return_value = None
        
        tools = JavadocTools()
        
        async def run_test():
            result = await tools.get_class_details("nonexistent", "TEST")
            return result
        
        result = asyncio.run(run_test())
        
        self.assertIn("error", result)
        self.assertIn("Class not found", result["error"])
        
    @patch('nabchan_mcp_server.javadoc.tools.connect_db')
    def test_search_javadoc(self, mock_connect_db):
        """Test searching Javadoc."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_connect_db.return_value.__enter__.return_value = mock_conn
        
        # Mock search results
        mock_conn.execute.return_value.fetchall.side_effect = [
            # Classes search result
            [("TestException", "exception", "com.example.test")],
            # Methods search result  
            [("testException", "com.example.test.TestClass", "method")]
        ]
        
        tools = JavadocTools()
        
        async def run_test():
            result = await tools.search_javadoc("exception", "TEST")
            return result
        
        result = asyncio.run(run_test())
        
        self.assertEqual(len(result['classes']), 1)
        self.assertEqual(result['classes'][0]['name'], "TestException")
        self.assertEqual(result['classes'][0]['type'], "exception")
        
        self.assertEqual(len(result['methods']), 1)
        self.assertEqual(result['methods'][0]['name'], "testException")
        self.assertEqual(result['methods'][0]['class'], "com.example.test.TestClass")
        
    @patch('nabchan_mcp_server.javadoc.tools.connect_db')
    def test_search_javadoc_error(self, mock_connect_db):
        """Test searching Javadoc with error."""
        # Mock database connection to raise exception
        mock_connect_db.side_effect = Exception("Search error")
        
        tools = JavadocTools()
        
        async def run_test():
            result = await tools.search_javadoc("test", "TEST")
            return result
        
        result = asyncio.run(run_test())
        
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Search error")
        self.assertEqual(result["classes"], [])
        self.assertEqual(result["methods"], [])


class TestJavadocToolsIntegration(unittest.TestCase):
    """Integration tests for JavadocTools using real database."""
    
    def setUp(self):
        """Set up test database with real data."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.original_db_file = None
        
        # Temporarily replace DB_FILE environment variable
        import os
        self.original_db_file = os.environ.get('DB_FILE')
        os.environ['DB_FILE'] = self.temp_db.name
        
        # Set up test data
        conn = duckdb.connect(self.temp_db.name)
        operations = JavadocDbOperations(conn)
        operations.create_tables()
        
        # Add sample data
        package = JavadocPackage(
            name="com.example.integration",
            version="INTEGRATION",
            summary="Integration test package"
        )
        operations.insert_package(package)
        
        javadoc_class = JavadocClass(
            name="com.example.integration.IntegrationTest",
            package_name="com.example.integration",
            version="INTEGRATION",
            type="class",
            summary="Integration test class"
        )
        operations.insert_class(javadoc_class)
        
        method = JavadocMethod(
            name="integrationMethod",
            class_name="com.example.integration.IntegrationTest",
            version="INTEGRATION",
            signature="integrationMethod()",
            modifiers="public",
            summary="Integration test method",
            type="method"
        )
        operations.insert_method(method)
        
        conn.close()
        
    def tearDown(self):
        """Clean up test database."""
        import os
        if self.original_db_file:
            os.environ['DB_FILE'] = self.original_db_file
        else:
            os.environ.pop('DB_FILE', None)
        Path(self.temp_db.name).unlink()
        
    def test_full_workflow(self):
        """Test full workflow with real database."""
        tools = JavadocTools()
        
        async def run_integration_test():
            # Test list packages
            packages = await tools.list_packages("INTEGRATION")
            self.assertEqual(len(packages), 1)
            self.assertEqual(packages[0]['name'], "com.example.integration")
            
            # Test get package details
            package_details = await tools.get_package_details("com.example.integration", "INTEGRATION")
            self.assertEqual(package_details['name'], "com.example.integration")
            self.assertEqual(len(package_details['classes']), 1)
            
            # Test get class details
            class_details = await tools.get_class_details("com.example.integration.IntegrationTest", "INTEGRATION")
            self.assertEqual(class_details['name'], "com.example.integration.IntegrationTest")
            self.assertEqual(len(class_details['methods']), 1)
            
            # Test search
            search_results = await tools.search_javadoc("integration", "INTEGRATION")
            self.assertGreaterEqual(len(search_results['classes']), 1)
            self.assertGreaterEqual(len(search_results['methods']), 1)
        
        asyncio.run(run_integration_test())


if __name__ == '__main__':
    unittest.main()