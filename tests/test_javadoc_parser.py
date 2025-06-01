"""Tests for Javadoc parser."""

import unittest
from pathlib import Path
from nabchan_mcp_server.javadoc.simple_parser import JavadocParser


class TestJavadocParser(unittest.TestCase):
    """Test cases for JavadocParser."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data path."""
        cls.test_data_path = Path(__file__).parent / "javadoc_test_data"
        
    def test_init_parser(self):
        """Test parser initialization."""
        parser = JavadocParser(self.test_data_path, "TEST")
        self.assertEqual(parser.version, "TEST")
        self.assertTrue(parser.javadoc_path.exists())
        self.assertTrue(parser.is_modern)  # element-list exists
        
    def test_init_parser_invalid_path(self):
        """Test parser initialization with invalid path."""
        with self.assertRaises(ValueError) as context:
            JavadocParser("/invalid/path", "TEST")
        self.assertIn("Javadoc path does not exist", str(context.exception))
        
    def test_get_all_packages(self):
        """Test getting all packages."""
        parser = JavadocParser(self.test_data_path, "TEST")
        packages = parser.get_all_packages()
        
        self.assertEqual(len(packages), 2)
        package_names = [p['name'] for p in packages]
        self.assertIn("com.example.package1", package_names)
        self.assertIn("com.example.package2", package_names)
        
    def test_get_package_info(self):
        """Test getting package information."""
        parser = JavadocParser(self.test_data_path, "TEST")
        package_info = parser.get_package_info("com.example.package1")
        
        self.assertEqual(package_info['name'], "com.example.package1")
        self.assertEqual(len(package_info['classes']), 2)
        
        class_names = [c['name'] for c in package_info['classes']]
        self.assertIn("TestClass1", class_names)
        self.assertIn("TestInterface", class_names)
        
    def test_get_package_info_not_found(self):
        """Test getting package info for non-existent package."""
        parser = JavadocParser(self.test_data_path, "TEST")
        with self.assertRaises(ValueError) as context:
            parser.get_package_info("com.example.nonexistent")
        self.assertIn("Package not found", str(context.exception))
        
    def test_get_class_info(self):
        """Test getting class information."""
        parser = JavadocParser(self.test_data_path, "TEST")
        class_info = parser.get_class_info("com.example.package1.TestClass1")
        
        self.assertEqual(class_info['name'], "com.example.package1.TestClass1")
        self.assertEqual(class_info['type'], "class")
        self.assertEqual(len(class_info['methods']), 2)
        
        method_names = [m['name'] for m in class_info['methods']]
        self.assertIn("testMethod1", method_names)
        self.assertIn("testMethod2", method_names)
        
    def test_get_class_info_not_found(self):
        """Test getting class info for non-existent class."""
        parser = JavadocParser(self.test_data_path, "TEST")
        with self.assertRaises(ValueError) as context:
            parser.get_class_info("com.example.NonExistentClass")
        self.assertIn("Class not found", str(context.exception))
        
    def test_search_by_keyword(self):
        """Test searching by keyword."""
        parser = JavadocParser(self.test_data_path, "TEST")
        
        # Create a simple type-search-index.js for testing
        index_file = parser.javadoc_path / "type-search-index.js"
        index_content = '''typeSearchIndex = [
            {"l": "TestClass1", "p": "com.example.package1", "c": "class"},
            {"l": "TestInterface", "p": "com.example.package1", "c": "interface"}
        ];'''
        index_file.write_text(index_content)
        
        results = parser.search_by_keyword("Test")
        
        self.assertEqual(len(results['classes']), 2)
        self.assertEqual(results['classes'][0]['name'], "TestClass1")
        self.assertEqual(results['classes'][0]['package'], "com.example.package1")
        
        # Clean up
        index_file.unlink()


if __name__ == '__main__':
    unittest.main()