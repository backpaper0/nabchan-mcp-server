"""Tests for Javadoc database operations."""

import unittest
import tempfile
from pathlib import Path

import duckdb
from nabchan_mcp_server.javadoc.operations import (
    JavadocDbOperations,
    JavadocPackage,
    JavadocClass,
    JavadocMethod
)


class TestJavadocDbOperations(unittest.TestCase):
    """Test cases for JavadocDbOperations."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.conn = duckdb.connect(self.temp_db.name)
        self.operations = JavadocDbOperations(self.conn)
        self.operations.create_tables()
        
    def tearDown(self):
        """Clean up test database."""
        self.conn.close()
        Path(self.temp_db.name).unlink()
        
    def test_create_tables(self):
        """Test table creation."""
        # Tables should already be created in setUp
        # Verify tables exist
        tables = self.conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        
        self.assertIn("javadoc_packages", table_names)
        self.assertIn("javadoc_classes", table_names)
        self.assertIn("javadoc_methods", table_names)
        
    def test_insert_and_get_package(self):
        """Test inserting and retrieving a package."""
        package = JavadocPackage(
            name="com.example.test",
            version="1.0",
            summary="Test package"
        )
        self.operations.insert_package(package)
        
        packages = self.operations.get_all_packages("1.0")
        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0]['name'], "com.example.test")
        self.assertEqual(packages[0]['summary'], "Test package")
        
    def test_insert_and_get_class(self):
        """Test inserting and retrieving a class."""
        # First insert a package
        package = JavadocPackage(
            name="com.example.test",
            version="1.0",
            summary="Test package"
        )
        self.operations.insert_package(package)
        
        # Then insert a class
        javadoc_class = JavadocClass(
            name="com.example.test.TestClass",
            package_name="com.example.test",
            version="1.0",
            type="class",
            summary="Test class"
        )
        self.operations.insert_class(javadoc_class)
        
        # Get package info should include the class
        package_info = self.operations.get_package_info("com.example.test", "1.0")
        self.assertIsNotNone(package_info)
        self.assertEqual(len(package_info['classes']), 1)
        self.assertEqual(package_info['classes'][0]['name'], "com.example.test.TestClass")
        
    def test_insert_and_get_method(self):
        """Test inserting and retrieving a method."""
        # Set up package and class
        package = JavadocPackage(
            name="com.example.test",
            version="1.0",
            summary="Test package"
        )
        self.operations.insert_package(package)
        
        javadoc_class = JavadocClass(
            name="com.example.test.TestClass",
            package_name="com.example.test",
            version="1.0",
            type="class",
            summary="Test class"
        )
        self.operations.insert_class(javadoc_class)
        
        # Insert methods
        method1 = JavadocMethod(
            name="testMethod",
            class_name="com.example.test.TestClass",
            version="1.0",
            signature="testMethod(String param)",
            modifiers="public",
            summary="Test method",
            type="method"
        )
        self.operations.insert_method(method1)
        
        # Get class info should include the method
        class_info = self.operations.get_class_info("com.example.test.TestClass", "1.0")
        self.assertIsNotNone(class_info)
        self.assertEqual(len(class_info['methods']), 1)
        self.assertEqual(class_info['methods'][0]['name'], "testMethod")
        self.assertEqual(class_info['methods'][0]['signature'], "testMethod(String param)")
        
    def test_search_by_keyword(self):
        """Test searching by keyword."""
        # Set up test data
        package = JavadocPackage(
            name="com.example.test",
            version="1.0",
            summary="Test package"
        )
        self.operations.insert_package(package)
        
        class1 = JavadocClass(
            name="com.example.test.TestException",
            package_name="com.example.test",
            version="1.0",
            type="exception",
            summary="Test exception"
        )
        class2 = JavadocClass(
            name="com.example.test.NormalClass",
            package_name="com.example.test",
            version="1.0",
            type="class",
            summary="Normal class"
        )
        self.operations.insert_class(class1)
        self.operations.insert_class(class2)
        
        method = JavadocMethod(
            name="handleException",
            class_name="com.example.test.NormalClass",
            version="1.0",
            signature="handleException(Exception e)",
            modifiers="public",
            summary="Handle exception",
            type="method"
        )
        self.operations.insert_method(method)
        
        # Search for "exception"
        results = self.operations.search_by_keyword("exception", "1.0")
        
        self.assertEqual(len(results['classes']), 1)
        self.assertEqual(results['classes'][0]['name'], "com.example.test.TestException")
        
        self.assertEqual(len(results['methods']), 1)
        self.assertEqual(results['methods'][0]['name'], "handleException")
        
    def test_get_nonexistent_package(self):
        """Test getting non-existent package."""
        result = self.operations.get_package_info("nonexistent", "1.0")
        self.assertIsNone(result)
        
    def test_get_nonexistent_class(self):
        """Test getting non-existent class."""
        result = self.operations.get_class_info("nonexistent", "1.0")
        self.assertIsNone(result)
        
    def test_multiple_versions(self):
        """Test handling multiple versions."""
        # Insert same package in different versions
        package_v1 = JavadocPackage(
            name="com.example.test",
            version="1.0",
            summary="Version 1.0"
        )
        package_v2 = JavadocPackage(
            name="com.example.test",
            version="2.0",
            summary="Version 2.0"
        )
        self.operations.insert_package(package_v1)
        self.operations.insert_package(package_v2)
        
        # Get packages for each version
        v1_packages = self.operations.get_all_packages("1.0")
        v2_packages = self.operations.get_all_packages("2.0")
        
        self.assertEqual(len(v1_packages), 1)
        self.assertEqual(v1_packages[0]['summary'], "Version 1.0")
        
        self.assertEqual(len(v2_packages), 1)
        self.assertEqual(v2_packages[0]['summary'], "Version 2.0")


if __name__ == '__main__':
    unittest.main()