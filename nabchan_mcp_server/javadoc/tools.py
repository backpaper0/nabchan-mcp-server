"""MCP tools for Javadoc operations."""

from typing import Dict, List, Optional, Union
from pathlib import Path
import mcp.types as types
from nabchan_mcp_server.db.connection import connect_db
from .operations import JavadocDbOperations


class JavadocTools:
    """MCP tools for querying Javadoc information from database."""
    
    def __init__(self):
        """Initialize the Javadoc tools."""
        pass
    
    async def list_packages(self, version: str = "LATEST") -> List[Dict[str, str]]:
        """Get a list of all packages in the specified Javadoc version.
        
        Args:
            version: Javadoc version (e.g., "LATEST", "6u3", "5u25")
            
        Returns:
            List of packages with their names and summaries
        """
        try:
            with connect_db() as conn:
                operations = JavadocDbOperations(conn)
                return operations.get_all_packages(version)
        except Exception as e:
            return [{"error": str(e)}]
    
    async def get_package_details(self, package_name: str, version: str = "LATEST") -> Dict[str, Union[str, List[Dict[str, str]]]]:
        """Get detailed information about a specific package.
        
        Args:
            package_name: Full package name (e.g., "nablarch.core.db")
            version: Javadoc version
            
        Returns:
            Package information including summary and class list
        """
        try:
            with connect_db() as conn:
                operations = JavadocDbOperations(conn)
                result = operations.get_package_info(package_name, version)
                if result is None:
                    return {"error": f"Package not found: {package_name}"}
                return result
        except Exception as e:
            return {"error": str(e)}
    
    async def get_class_details(self, class_name: str, version: str = "LATEST") -> Dict[str, Union[str, List[Dict[str, str]]]]:
        """Get detailed information about a specific class.
        
        Args:
            class_name: Full class name (e.g., "nablarch.core.db.DbAccessException")
            version: Javadoc version
            
        Returns:
            Class information including summary and method list
        """
        try:
            with connect_db() as conn:
                operations = JavadocDbOperations(conn)
                result = operations.get_class_info(class_name, version)
                if result is None:
                    return {"error": f"Class not found: {class_name}"}
                return result
        except Exception as e:
            return {"error": str(e)}
    
    async def search_javadoc(self, keyword: str, version: str = "LATEST") -> Dict[str, List[Dict[str, str]]]:
        """Search for classes and methods by keyword.
        
        Args:
            keyword: Search keyword
            version: Javadoc version
            
        Returns:
            Dictionary with 'classes' and 'methods' lists
        """
        try:
            with connect_db() as conn:
                operations = JavadocDbOperations(conn)
                return operations.search_by_keyword(keyword, version)
        except Exception as e:
            return {"error": str(e), "classes": [], "methods": []}


# Tool definitions for MCP
def get_javadoc_tools():
    """Get MCP tool definitions for Javadoc operations."""
    return [
        types.Tool(
            name="javadoc_list_packages",
            description="Get a list of all packages in the Javadoc",
            inputSchema={
                "type": "object",
                "properties": {
                    "version": {
                        "type": "string",
                        "description": "Javadoc version (default: LATEST)",
                        "default": "LATEST"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="javadoc_get_package",
            description="Get summary and class list for a specific package",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "Full package name (e.g., nablarch.core.db)"
                    },
                    "version": {
                        "type": "string",
                        "description": "Javadoc version (default: LATEST)",
                        "default": "LATEST"
                    }
                },
                "required": ["package_name"]
            }
        ),
        types.Tool(
            name="javadoc_get_class",
            description="Get summary and method list for a specific class",
            inputSchema={
                "type": "object",
                "properties": {
                    "class_name": {
                        "type": "string",
                        "description": "Full class name (e.g., nablarch.core.db.DbAccessException)"
                    },
                    "version": {
                        "type": "string",
                        "description": "Javadoc version (default: LATEST)",
                        "default": "LATEST"
                    }
                },
                "required": ["class_name"]
            }
        ),
        types.Tool(
            name="javadoc_search",
            description="Search for classes and methods by keyword",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Search keyword"
                    },
                    "version": {
                        "type": "string",
                        "description": "Javadoc version (default: LATEST)",
                        "default": "LATEST"
                    }
                },
                "required": ["keyword"]
            }
        )
    ]