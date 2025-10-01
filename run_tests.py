#!/usr/bin/env python3
"""
Test runner script for AI Trading Agent
"""

import subprocess
import sys
import os
from pathlib import Path


def run_tests():
    """Run all tests."""
    print("🧪 Running AI Trading Agent Tests")
    print("=================================")
    print("")
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Run pytest
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "--tb=short",
            "--cov=app",
            "--cov-report=term-missing"
        ], check=True)
        
        print("")
        print("✅ All tests passed!")
        return 0
        
    except subprocess.CalledProcessError as e:
        print("")
        print(f"❌ Tests failed with exit code {e.returncode}")
        return e.returncode
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
