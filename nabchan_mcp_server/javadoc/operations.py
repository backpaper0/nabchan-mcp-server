"""Database operations for Javadoc data."""

from typing import List, Dict, Optional
from duckdb import DuckDBPyConnection
from pydantic import BaseModel


class JavadocPackage(BaseModel):
    """Javadoc package information."""
    name: str
    version: str
    summary: str = ""


class JavadocClass(BaseModel):
    """Javadoc class information."""
    name: str
    package_name: str
    version: str
    type: str  # class, interface, enum, annotation, exception, error
    summary: str = ""


class JavadocMethod(BaseModel):
    """Javadoc method information."""
    name: str
    class_name: str
    version: str
    signature: str
    modifiers: str = ""
    summary: str = ""
    type: str  # method, constructor


class JavadocDbOperations:
    """Database operations for Javadoc data."""
    
    def __init__(self, conn: DuckDBPyConnection):
        """Initialize with database connection."""
        self._conn = conn
    
    def create_tables(self) -> None:
        """Create tables for Javadoc data."""
        # Packages table
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS javadoc_packages (
                name TEXT,
                version TEXT,
                summary TEXT,
                PRIMARY KEY (name, version)
            )
            """
        )
        
        # Classes table
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS javadoc_classes (
                name TEXT,
                package_name TEXT,
                version TEXT,
                type TEXT,
                summary TEXT,
                PRIMARY KEY (name, version),
                FOREIGN KEY (package_name, version) REFERENCES javadoc_packages(name, version)
            )
            """
        )
        
        # Methods table
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS javadoc_methods (
                name TEXT,
                class_name TEXT,
                version TEXT,
                signature TEXT,
                modifiers TEXT,
                summary TEXT,
                type TEXT,
                PRIMARY KEY (class_name, signature, version),
                FOREIGN KEY (class_name, version) REFERENCES javadoc_classes(name, version)
            )
            """
        )
        
        # Create indexes for search
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_javadoc_classes_package 
            ON javadoc_classes(package_name, version)
            """
        )
        
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_javadoc_methods_class 
            ON javadoc_methods(class_name, version)
            """
        )
        
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_javadoc_classes_name 
            ON javadoc_classes(name)
            """
        )
        
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_javadoc_methods_name 
            ON javadoc_methods(name)
            """
        )
    
    def insert_package(self, package: JavadocPackage) -> None:
        """Insert a package into the database."""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO javadoc_packages (name, version, summary)
            VALUES ($name, $version, $summary)
            """,
            package.model_dump()
        )
    
    def insert_class(self, javadoc_class: JavadocClass) -> None:
        """Insert a class into the database."""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO javadoc_classes (name, package_name, version, type, summary)
            VALUES ($name, $package_name, $version, $type, $summary)
            """,
            javadoc_class.model_dump()
        )
    
    def insert_method(self, method: JavadocMethod) -> None:
        """Insert a method into the database."""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO javadoc_methods 
            (name, class_name, version, signature, modifiers, summary, type)
            VALUES ($name, $class_name, $version, $signature, $modifiers, $summary, $type)
            """,
            method.model_dump()
        )
    
    def get_all_packages(self, version: str) -> List[Dict[str, str]]:
        """Get all packages for a version."""
        result = self._conn.execute(
            """
            SELECT name, summary 
            FROM javadoc_packages 
            WHERE version = $version
            ORDER BY name
            """,
            {"version": version}
        ).fetchall()
        
        return [{"name": row[0], "summary": row[1]} for row in result]
    
    def get_package_info(self, package_name: str, version: str) -> Optional[Dict]:
        """Get package information including its classes."""
        # Get package info
        package_result = self._conn.execute(
            """
            SELECT summary 
            FROM javadoc_packages 
            WHERE name = $name AND version = $version
            """,
            {"name": package_name, "version": version}
        ).fetchone()
        
        if not package_result:
            return None
        
        # Get classes in package
        classes_result = self._conn.execute(
            """
            SELECT name, type, summary 
            FROM javadoc_classes 
            WHERE package_name = $package_name AND version = $version
            ORDER BY name
            """,
            {"package_name": package_name, "version": version}
        ).fetchall()
        
        classes = [
            {"name": row[0], "type": row[1], "summary": row[2]}
            for row in classes_result
        ]
        
        return {
            "name": package_name,
            "summary": package_result[0],
            "classes": classes
        }
    
    def get_class_info(self, class_name: str, version: str) -> Optional[Dict]:
        """Get class information including its methods."""
        # Get class info
        class_result = self._conn.execute(
            """
            SELECT type, summary 
            FROM javadoc_classes 
            WHERE name = $name AND version = $version
            """,
            {"name": class_name, "version": version}
        ).fetchone()
        
        if not class_result:
            return None
        
        # Get methods in class
        methods_result = self._conn.execute(
            """
            SELECT name, signature, modifiers, summary, type 
            FROM javadoc_methods 
            WHERE class_name = $class_name AND version = $version
            ORDER BY name
            """,
            {"class_name": class_name, "version": version}
        ).fetchall()
        
        methods = [
            {
                "name": row[0],
                "signature": row[1],
                "modifiers": row[2],
                "summary": row[3],
                "type": row[4]
            }
            for row in methods_result
        ]
        
        return {
            "name": class_name,
            "type": class_result[0],
            "summary": class_result[1],
            "methods": methods
        }
    
    def search_by_keyword(self, keyword: str, version: str) -> Dict[str, List[Dict]]:
        """Search for classes and methods by keyword."""
        keyword_pattern = f"%{keyword}%"
        
        # Search classes
        classes_result = self._conn.execute(
            """
            SELECT c.name, c.type, p.name as package_name
            FROM javadoc_classes c
            JOIN javadoc_packages p ON c.package_name = p.name AND c.version = p.version
            WHERE c.version = $version AND LOWER(c.name) LIKE LOWER($pattern)
            ORDER BY c.name
            LIMIT 100
            """,
            {"version": version, "pattern": keyword_pattern}
        ).fetchall()
        
        classes = [
            {"name": row[0], "type": row[1], "package": row[2]}
            for row in classes_result
        ]
        
        # Search methods
        methods_result = self._conn.execute(
            """
            SELECT m.name, m.class_name, m.type
            FROM javadoc_methods m
            WHERE m.version = $version AND LOWER(m.name) LIKE LOWER($pattern)
            ORDER BY m.name
            LIMIT 100
            """,
            {"version": version, "pattern": keyword_pattern}
        ).fetchall()
        
        methods = [
            {"name": row[0], "class": row[1], "type": row[2]}
            for row in methods_result
        ]
        
        return {"classes": classes, "methods": methods}