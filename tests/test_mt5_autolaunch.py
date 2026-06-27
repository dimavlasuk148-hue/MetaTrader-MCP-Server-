#!/usr/bin/env python3
"""
Test script for MT5 auto-launch functionality.

Usage:
    python tests/test_mt5_autolaunch.py
"""
import sys
import os
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from metatrader_client.connection._process_manager import (
    _is_mt5_running,
    _find_mt5_executable,
    ensure_mt5_running
)


def test_process_detection():
    """Test if MT5 process detection works."""
    print("\n" + "="*60)
    print("TEST 1: MT5 Process Detection")
    print("="*60)
    
    is_running = _is_mt5_running()
    print(f"MT5 is running: {is_running}")
    
    if not is_running:
        print("⚠ MT5 terminal is not currently running")
    else:
        print("✓ MT5 terminal is running")
    
    return is_running


def test_find_executable():
    """Test if we can find MT5 executable."""
    print("\n" + "="*60)
    print("TEST 2: Find MT5 Executable")
    print("="*60)
    
    path = _find_mt5_executable()
    
    if path:
        print(f"✓ Found MT5 at: {path}")
        print(f"  Exists: {os.path.exists(path)}")
        return True
    else:
        print("✗ Could not find MT5 executable")
        print("  Please:")
        print("  1. Set METATRADER5_PATH environment variable, or")
        print("  2. Install MetaTrader 5 in standard location, or")
        print("  3. Specify 'path' in connection config")
        return False


def test_ensure_running():
    """Test the ensure_mt5_running function."""
    print("\n" + "="*60)
    print("TEST 3: Ensure MT5 Running (with auto-launch)")
    print("="*60)
    
    success, error = ensure_mt5_running(auto_launch=True)
    
    if success:
        print("✓ MT5 is running or successfully launched")
        print("  Status: Success")
    else:
        print("✗ Failed to ensure MT5 is running")
        print(f"  Error: {error}")
    
    return success


def test_ensure_running_no_launch():
    """Test ensure_mt5_running without auto-launch."""
    print("\n" + "="*60)
    print("TEST 4: Ensure MT5 Running (no auto-launch)")
    print("="*60)
    
    success, error = ensure_mt5_running(auto_launch=False)
    
    if success:
        print("✓ MT5 is already running")
    else:
        print("ℹ MT5 is not running (expected, since auto_launch=False)")
        print(f"  Message: {error}")
    
    return success or error is not None


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("MT5 AUTO-LAUNCH FUNCTIONALITY TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Process detection
    results.append(("Process Detection", test_process_detection()))
    
    # Test 2: Find executable
    results.append(("Find Executable", test_find_executable()))
    
    # Test 3: Ensure running (with auto-launch)
    results.append(("Ensure Running (auto-launch)", test_ensure_running()))
    
    # Test 4: Ensure running (no auto-launch)
    results.append(("Ensure Running (no auto-launch)", test_ensure_running_no_launch()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
