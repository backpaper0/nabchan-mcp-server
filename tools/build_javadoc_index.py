"""
Build Javadoc index script.
"""

import asyncio
from argparse import ArgumentParser
from pathlib import Path
from typing import List, Tuple
from tqdm.asyncio import tqdm

from nabchan_mcp_server.db.connection import connect_db
from nabchan_mcp_server.javadoc.simple_parser import JavadocParser
from nabchan_mcp_server.javadoc.operations import (
    JavadocDbOperations,
    JavadocPackage,
    JavadocClass,
    JavadocMethod
)


async def process_package(
    semaphore: asyncio.Semaphore,
    parser: JavadocParser,
    package_name: str,
    version: str
) -> Tuple[JavadocPackage, List[JavadocClass]]:
    """Process a single package and extract its classes."""
    async with semaphore:
        try:
            package_info = parser.get_package_info(package_name)
            package = JavadocPackage(
                name=package_name,
                version=version,
                summary=package_info.get("summary", "")
            )
            
            classes = []
            for class_info in package_info.get("classes", []):
                # Extract simple class name
                simple_name = class_info["name"]
                full_class_name = f"{package_name}.{simple_name}"
                
                javadoc_class = JavadocClass(
                    name=full_class_name,
                    package_name=package_name,
                    version=version,
                    type=class_info.get("type", "class"),
                    summary=class_info.get("summary", "")
                )
                classes.append(javadoc_class)
            
            return package, classes
        except Exception as e:
            print(f"Error processing package {package_name}: {e}")
            return JavadocPackage(name=package_name, version=version), []


async def process_class(
    semaphore: asyncio.Semaphore,
    parser: JavadocParser,
    class_name: str,
    version: str
) -> List[JavadocMethod]:
    """Process a single class and extract its methods."""
    async with semaphore:
        try:
            class_info = parser.get_class_info(class_name)
            methods = []
            
            for method_info in class_info.get("methods", []):
                method = JavadocMethod(
                    name=method_info["name"],
                    class_name=class_name,
                    version=version,
                    signature=method_info.get("signature", method_info["name"] + "(...)"),
                    modifiers=method_info.get("modifiers", ""),
                    summary=method_info.get("summary", ""),
                    type=method_info.get("type", "method")
                )
                methods.append(method)
            
            return methods
        except Exception as e:
            print(f"Error processing class {class_name}: {e}")
            return []


async def add_to_database(queue: asyncio.Queue) -> None:
    """Worker to add items to database from queue."""
    with connect_db(read_only=False) as conn:
        operations = JavadocDbOperations(conn)
        operations.create_tables()
        
        while True:
            item = await queue.get()
            if item is None:
                break
            
            try:
                if isinstance(item, JavadocPackage):
                    operations.insert_package(item)
                elif isinstance(item, JavadocClass):
                    operations.insert_class(item)
                elif isinstance(item, JavadocMethod):
                    operations.insert_method(item)
            except Exception as e:
                print(f"Error inserting {type(item).__name__}: {e}")
            
            queue.task_done()


async def main(
    javadoc_path: Path,
    version: str,
    parallels: int
) -> None:
    """Main function to build Javadoc index."""
    parser = JavadocParser(javadoc_path.parent.parent.parent, version)
    
    # Get all packages
    print("Getting all packages...")
    packages = parser.get_all_packages()
    print(f"Found {len(packages)} packages")
    
    semaphore = asyncio.Semaphore(parallels)
    queue: asyncio.Queue = asyncio.Queue()
    
    # Start database worker
    db_task = asyncio.create_task(add_to_database(queue))
    
    # Process packages and extract classes
    print("\nProcessing packages...")
    package_tasks = [
        process_package(semaphore, parser, pkg["name"], version)
        for pkg in packages
    ]
    
    all_classes = []
    for coro in tqdm(asyncio.as_completed(package_tasks), total=len(package_tasks)):
        package, classes = await coro
        await queue.put(package)
        for javadoc_class in classes:
            await queue.put(javadoc_class)
            all_classes.append(javadoc_class)
    
    print(f"\nFound {len(all_classes)} classes")
    
    # Process classes and extract methods
    print("\nProcessing classes...")
    class_tasks = [
        process_class(semaphore, parser, cls.name, version)
        for cls in all_classes
    ]
    
    method_count = 0
    for coro in tqdm(asyncio.as_completed(class_tasks), total=len(class_tasks)):
        methods = await coro
        for method in methods:
            await queue.put(method)
            method_count += 1
    
    print(f"\nFound {method_count} methods")
    
    # Signal end and wait for database operations
    await queue.put(None)
    await db_task
    
    print("\nJavadoc index built successfully!")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--javadoc_version",
        type=str,
        default="LATEST",
        help="Javadoc version to index"
    )
    parser.add_argument(
        "--parallels",
        type=int,
        default=10,
        help="Number of parallel processing tasks"
    )
    args = parser.parse_args()
    
    javadoc_path = (
        Path("nablarch.github.io") / "docs" / args.javadoc_version / "javadoc"
    )
    
    if not javadoc_path.exists():
        print(f"Error: Javadoc path does not exist: {javadoc_path}")
        exit(1)
    
    asyncio.run(
        main(
            javadoc_path=javadoc_path,
            version=args.javadoc_version,
            parallels=args.parallels
        )
    )