#!/usr/bin/env python3
"""
Simple test runner for media_search service.
Run this after starting the service with docker-compose.
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Run the comprehensive tests."""
    print("🚀 Media Search Service Test Runner")
    print("=" * 50)
    
    # Change to the tests directory
    test_dir = Path(__file__).parent / "tests"
    test_script = test_dir / "test_full_workflow.py"
    
    if not test_script.exists():
        print(f"❌ Test script not found: {test_script}")
        sys.exit(1)
    
    # Run the tests
    try:
        print("Running comprehensive workflow tests...")
        result = subprocess.run([
            sys.executable, str(test_script),
            "--url", "http://localhost:5001",
            "--wait", "10"
        ], check=True)
        
        print("\n🎉 All tests completed successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code: {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 