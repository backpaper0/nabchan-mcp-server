#!/usr/bin/env python3
"""
Build all indices (documents and Javadoc) for the MCP server.
"""

import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path


def run_command(command: list[str], description: str) -> int:
    """Run a command and return its exit code."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print('='*60)
    
    result = subprocess.run(command, capture_output=False)
    
    if result.returncode == 0:
        print(f"✓ {description} completed successfully")
    else:
        print(f"✗ {description} failed with exit code {result.returncode}")
    
    return result.returncode


def main():
    parser = ArgumentParser(description="Build all indices for the MCP server")
    parser.add_argument(
        "--version",
        type=str,
        default="LATEST",
        help="Nablarch version to index (default: LATEST)"
    )
    parser.add_argument(
        "--skip-documents",
        action="store_true",
        help="Skip building document index"
    )
    parser.add_argument(
        "--skip-javadoc",
        action="store_true",
        help="Skip building Javadoc index"
    )
    parser.add_argument(
        "--parallels",
        type=int,
        default=20,
        help="Number of parallel tasks (default: 20)"
    )
    parser.add_argument(
        "--llm",
        type=str,
        default="gpt-4o-mini",
        help="LLM model for document summarization (default: gpt-4o-mini)"
    )
    args = parser.parse_args()
    
    # Check if directories exist
    nablarch_path = Path("nablarch.github.io")
    if not nablarch_path.exists():
        print(f"Error: Nablarch documentation not found at {nablarch_path}")
        print("Please clone the Nablarch documentation repository first.")
        return 1
    
    doc_path = nablarch_path / "docs" / args.version / "doc"
    javadoc_path = nablarch_path / "docs" / args.version / "javadoc"
    
    if not doc_path.exists():
        print(f"Error: Documentation not found at {doc_path}")
        return 1
    
    if not javadoc_path.exists():
        print(f"Error: Javadoc not found at {javadoc_path}")
        return 1
    
    exit_code = 0
    
    # Build document index
    if not args.skip_documents:
        command = [
            sys.executable,
            "-m", "tools.build_index",
            "--nablarch_version", args.version,
            "--parallels", str(args.parallels),
            "--llm", args.llm
        ]
        
        exit_code = run_command(command, "Building document index")
        if exit_code != 0:
            return exit_code
    
    # Build Javadoc index
    if not args.skip_javadoc:
        command = [
            sys.executable,
            "-m", "tools.build_javadoc_index",
            "--javadoc_version", args.version,
            "--parallels", str(args.parallels)
        ]
        
        exit_code = run_command(command, "Building Javadoc index")
        if exit_code != 0:
            return exit_code
    
    print(f"\n{'='*60}")
    print("✓ All indices built successfully!")
    print('='*60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())