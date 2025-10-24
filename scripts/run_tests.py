#!/usr/bin/env python3
"""
Test runner script for Confida.

This script provides a comprehensive test runner with various options
for running different types of tests and generating reports.
"""
import argparse
import subprocess
import sys
import os
from pathlib import Path
from typing import List, Optional
import json
import time
from datetime import datetime

def run_command(command: List[str], capture_output: bool = False) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    try:
        if capture_output:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
        else:
            result = subprocess.run(command, check=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {' '.join(command)}")
        print(f"Error: {e}")
        sys.exit(1)

def run_unit_tests(verbose: bool = False, coverage: bool = True) -> bool:
    """Run unit tests."""
    print("🧪 Running unit tests...")
    
    command = ["pytest", "tests/unit/"]
    if verbose:
        command.append("-v")
    if coverage:
        command.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=html"])
    
    try:
        run_command(command)
        print("✅ Unit tests passed!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Unit tests failed!")
        return False

def run_integration_tests(verbose: bool = False, coverage: bool = True) -> bool:
    """Run integration tests."""
    print("🔗 Running integration tests...")
    
    command = ["pytest", "tests/integration/"]
    if verbose:
        command.append("-v")
    if coverage:
        command.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=html"])
    
    try:
        run_command(command)
        print("✅ Integration tests passed!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Integration tests failed!")
        return False

def run_e2e_tests(verbose: bool = False, coverage: bool = True) -> bool:
    """Run end-to-end tests."""
    print("🎯 Running end-to-end tests...")
    
    command = ["pytest", "tests/e2e/"]
    if verbose:
        command.append("-v")
    if coverage:
        command.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=html"])
    
    try:
        run_command(command)
        print("✅ End-to-end tests passed!")
        return True
    except subprocess.CalledProcessError:
        print("❌ End-to-end tests failed!")
        return False

def run_all_tests(verbose: bool = False, coverage: bool = True, fail_fast: bool = False) -> bool:
    """Run all tests."""
    print("🚀 Running all tests...")
    
    command = ["pytest", "tests/"]
    if verbose:
        command.append("-v")
    if coverage:
        command.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=html", "--cov-fail-under=85"])
    if fail_fast:
        command.append("-x")
    
    try:
        run_command(command)
        print("✅ All tests passed!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Some tests failed!")
        return False

def run_tests_by_marker(marker: str, verbose: bool = False) -> bool:
    """Run tests by marker."""
    print(f"🏷️  Running tests with marker: {marker}")
    
    command = ["pytest", f"-m {marker}", "tests/"]
    if verbose:
        command.append("-v")
    
    try:
        run_command(command)
        print(f"✅ Tests with marker '{marker}' passed!")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Tests with marker '{marker}' failed!")
        return False

def run_specific_test(test_path: str, verbose: bool = False) -> bool:
    """Run a specific test file or test function."""
    print(f"🎯 Running specific test: {test_path}")
    
    command = ["pytest", test_path]
    if verbose:
        command.append("-v")
    
    try:
        run_command(command)
        print(f"✅ Test '{test_path}' passed!")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Test '{test_path}' failed!")
        return False

def run_performance_tests(verbose: bool = False) -> bool:
    """Run performance tests."""
    print("⚡ Running performance tests...")
    
    command = ["pytest", "-m", "performance", "tests/"]
    if verbose:
        command.append("-v")
    command.extend(["--durations=10"])
    
    try:
        run_command(command)
        print("✅ Performance tests passed!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Performance tests failed!")
        return False

def run_security_tests(verbose: bool = False) -> bool:
    """Run security tests."""
    print("🔒 Running security tests...")
    
    command = ["pytest", "-m", "security", "tests/"]
    if verbose:
        command.append("-v")
    
    try:
        run_command(command)
        print("✅ Security tests passed!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Security tests failed!")
        return False

def generate_coverage_report() -> None:
    """Generate comprehensive coverage report."""
    print("📊 Generating coverage report...")
    
    command = [
        "pytest",
        "tests/",
        "--cov=app",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
        "--cov-report=term-missing",
        "--cov-fail-under=85"
    ]
    
    try:
        run_command(command)
        print("✅ Coverage report generated!")
        print("📁 HTML report: htmlcov/index.html")
        print("📁 XML report: coverage.xml")
    except subprocess.CalledProcessError:
        print("❌ Coverage report generation failed!")

def run_linting() -> bool:
    """Run code linting."""
    print("🔍 Running code linting...")
    
    # Run flake8
    try:
        run_command(["flake8", "app/", "tests/", "--max-line-length=100", "--exclude=__pycache__"])
        print("✅ Flake8 linting passed!")
    except subprocess.CalledProcessError:
        print("❌ Flake8 linting failed!")
        return False
    
    # Run black check
    try:
        run_command(["black", "--check", "app/", "tests/"])
        print("✅ Black formatting check passed!")
    except subprocess.CalledProcessError:
        print("❌ Black formatting check failed!")
        return False
    
    # Run isort check
    try:
        run_command(["isort", "--check-only", "app/", "tests/"])
        print("✅ Import sorting check passed!")
    except subprocess.CalledProcessError:
        print("❌ Import sorting check failed!")
        return False
    
    return True

def run_type_checking() -> bool:
    """Run type checking with mypy."""
    print("🔍 Running type checking...")
    
    try:
        run_command(["mypy", "app/", "--ignore-missing-imports"])
        print("✅ Type checking passed!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Type checking failed!")
        return False

def run_security_scanning() -> bool:
    """Run security scanning."""
    print("🔒 Running security scanning...")
    
    # Run bandit
    try:
        run_command(["bandit", "-r", "app/", "-f", "json", "-o", "bandit-report.json"])
        print("✅ Bandit security scan passed!")
    except subprocess.CalledProcessError:
        print("❌ Bandit security scan failed!")
        return False
    
    # Run safety
    try:
        run_command(["safety", "check", "--json", "--output", "safety-report.json"])
        print("✅ Safety dependency scan passed!")
    except subprocess.CalledProcessError:
        print("❌ Safety dependency scan failed!")
        return False
    
    return True

def setup_test_environment() -> None:
    """Set up test environment."""
    print("🔧 Setting up test environment...")
    
    # Set environment variables
    os.environ["DATABASE_URL"] = "sqlite:///./test_confida.db"
    os.environ["REDIS_URL"] = "redis://localhost:6379"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["ENVIRONMENT"] = "test"
    
    # Add project root to Python path
    project_root = Path(__file__).parent.parent
    os.environ["PYTHONPATH"] = str(project_root)
    
    # Create test database (skip for simple tests)
    print("✅ Test environment setup complete!")

def cleanup_test_environment() -> None:
    """Clean up test environment."""
    print("🧹 Cleaning up test environment...")
    
    # Remove test database
    test_db_path = Path("test_confida.db")
    if test_db_path.exists():
        test_db_path.unlink()
        print("✅ Test database cleaned up!")
    
    # Remove coverage files
    coverage_files = ["coverage.xml", "htmlcov/"]
    for file_path in coverage_files:
        path = Path(file_path)
        if path.exists():
            if path.is_dir():
                import shutil
                shutil.rmtree(path)
            else:
                path.unlink()
    
    print("✅ Test environment cleaned up!")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Confida Test Runner")
    parser.add_argument("--type", choices=["unit", "integration", "e2e", "all", "performance", "security"], 
                       default="all", help="Type of tests to run")
    parser.add_argument("--marker", help="Run tests with specific marker")
    parser.add_argument("--test", help="Run specific test file or function")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--fail-fast", "-x", action="store_true", help="Stop on first failure")
    parser.add_argument("--lint", action="store_true", help="Run code linting")
    parser.add_argument("--type-check", action="store_true", help="Run type checking")
    parser.add_argument("--security-scan", action="store_true", help="Run security scanning")
    parser.add_argument("--setup", action="store_true", help="Set up test environment")
    parser.add_argument("--cleanup", action="store_true", help="Clean up test environment")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip cleanup after tests")
    
    args = parser.parse_args()
    
    # Set up test environment if requested
    if args.setup:
        setup_test_environment()
        return
    
    # Clean up test environment if requested
    if args.cleanup:
        cleanup_test_environment()
        return
    
    # Set up test environment
    setup_test_environment()
    
    start_time = time.time()
    success = True
    
    try:
        # Run linting if requested
        if args.lint:
            success &= run_linting()
        
        # Run type checking if requested
        if args.type_check:
            success &= run_type_checking()
        
        # Run security scanning if requested
        if args.security_scan:
            success &= run_security_scanning()
        
        # Run tests based on type
        if args.marker:
            success &= run_tests_by_marker(args.marker, args.verbose)
        elif args.test:
            success &= run_specific_test(args.test, args.verbose)
        elif args.type == "unit":
            success &= run_unit_tests(args.verbose, args.coverage)
        elif args.type == "integration":
            success &= run_integration_tests(args.verbose, args.coverage)
        elif args.type == "e2e":
            success &= run_e2e_tests(args.verbose, args.coverage)
        elif args.type == "performance":
            success &= run_performance_tests(args.verbose)
        elif args.type == "security":
            success &= run_security_tests(args.verbose)
        elif args.type == "all":
            success &= run_all_tests(args.verbose, args.coverage, args.fail_fast)
        
        # Generate coverage report if requested
        if args.coverage and args.type == "all":
            generate_coverage_report()
    
    finally:
        # Clean up test environment unless requested not to
        if not args.no_cleanup:
            cleanup_test_environment()
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n⏱️  Total execution time: {duration:.2f} seconds")
    
    if success:
        print("🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
