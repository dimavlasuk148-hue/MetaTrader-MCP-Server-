"""
MT5 process management — auto-launch and detection.

Detects if MT5 terminal is running, starts it if not, handles process lifecycle.
"""
import os
import sys
import time
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("MT5ProcessManager")


def _is_mt5_running() -> bool:
    """
    Check if MetaTrader 5 terminal process is currently running.
    
    Returns:
        bool: True if MT5 process is detected, False otherwise.
    """
    try:
        if sys.platform == "win32":
            # Windows: check for terminal.exe process
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq terminal.exe"],
                capture_output=True,
                text=True,
                timeout=5
            )
            is_running = "terminal.exe" in result.stdout
            logger.debug(f"MT5 process check (Windows): {is_running}")
            return is_running
        else:
            logger.debug("MT5 process detection only supported on Windows")
            return False
    except Exception as e:
        logger.warning(f"Failed to check MT5 process: {e}")
        return False


def _launch_mt5(terminal_path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Launch MetaTrader 5 terminal if not already running.
    
    Args:
        terminal_path: Path to terminal.exe. If None, searches standard locations.
    
    Returns:
        Tuple[bool, Optional[str]]: (success, error_message)
            - (True, None) if already running or successfully launched
            - (False, error_msg) if launch failed
    """
    if _is_mt5_running():
        logger.info("MT5 terminal is already running")
        return True, None
    
    # Determine terminal path
    if not terminal_path:
        terminal_path = _find_mt5_executable()
    
    if not terminal_path or not os.path.exists(terminal_path):
        error_msg = f"MT5 terminal not found at: {terminal_path}"
        logger.error(error_msg)
        return False, error_msg
    
    try:
        logger.info(f"Launching MT5 terminal from: {terminal_path}")
        
        # Launch terminal in background
        if sys.platform == "win32":
            # Use CREATE_NEW_CONSOLE to launch in separate window
            subprocess.Popen(
                [terminal_path],
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )
        else:
            subprocess.Popen([terminal_path])
        
        # Wait for process to start
        logger.info("Waiting for MT5 terminal to start...")
        start_time = time.time()
        timeout = 30
        
        while time.time() - start_time < timeout:
            time.sleep(1)
            if _is_mt5_running():
                logger.info("MT5 terminal successfully launched and started")
                time.sleep(2)  # Give it a moment to fully initialize
                return True, None
        
        logger.warning(f"MT5 process not detected after {timeout} seconds, but launch command completed")
        return True, None  # Process launched, even if detection failed
        
    except Exception as e:
        error_msg = f"Failed to launch MT5 terminal: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def _find_mt5_executable() -> Optional[str]:
    """
    Find MetaTrader 5 terminal.exe in standard installation locations.
    
    Checks:
    1. METATRADER5_PATH environment variable
    2. Program Files (x86) / MetaTrader 5 / terminal.exe
    3. Program Files / MetaTrader 5 / terminal.exe
    4. AppData / MetaTrader 5 / terminal.exe
    
    Returns:
        Optional[str]: Path to terminal.exe if found, None otherwise.
    """
    paths_to_check = []
    
    # Check environment variable
    env_path = os.getenv("METATRADER5_PATH")
    if env_path:
        paths_to_check.append(env_path)
        paths_to_check.append(os.path.join(env_path, "terminal.exe"))
    
    # Standard installation paths (Windows only)
    if sys.platform == "win32":
        program_files_x86 = os.getenv("ProgramFiles(x86)")
        program_files = os.getenv("ProgramFiles")
        appdata = os.getenv("APPDATA")
        
        if program_files_x86:
            paths_to_check.append(os.path.join(program_files_x86, "MetaTrader 5", "terminal.exe"))
        
        if program_files:
            paths_to_check.append(os.path.join(program_files, "MetaTrader 5", "terminal.exe"))
        
        if appdata:
            paths_to_check.append(os.path.join(appdata, "MetaTrader 5", "terminal.exe"))
    
    for path in paths_to_check:
        if path and os.path.exists(path):
            logger.debug(f"Found MT5 terminal at: {path}")
            return path
    
    logger.warning(f"MT5 terminal not found in standard locations. Checked: {paths_to_check}")
    return None


def ensure_mt5_running(terminal_path: Optional[str] = None, auto_launch: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Ensure MetaTrader 5 terminal is running. Auto-launch if configured.
    
    Args:
        terminal_path: Optional path to terminal.exe
        auto_launch: If True, automatically launch MT5 if not running
    
    Returns:
        Tuple[bool, Optional[str]]: (success, error_message)
            - (True, None) if MT5 is running or auto-launch succeeded
            - (False, error_msg) if MT5 not running and auto-launch disabled/failed
    """
    if _is_mt5_running():
        logger.info("MT5 terminal is running")
        return True, None
    
    if not auto_launch:
        error_msg = "MT5 terminal is not running and auto-launch is disabled"
        logger.warning(error_msg)
        return False, error_msg
    
    return _launch_mt5(terminal_path)
