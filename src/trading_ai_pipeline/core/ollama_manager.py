"""
Ollama process management and auto-discovery.

Automatically detects, launches, and manages local Ollama instances.
No manual configuration needed - everything is automatic.
"""

import logging
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

import httpx

logger = logging.getLogger("OllamaManager")


def _find_ollama_executable() -> Optional[str]:
    """
    Find Ollama executable in standard installation locations.
    
    Returns:
        Path to ollama executable, or None if not found.
    """
    system = platform.system()
    
    if system == "Windows":
        paths = [
            Path("C:\\Users") / os.getenv("USERNAME", "User") / "AppData/Local/Programs/Ollama/ollama.exe",
            Path("C:\\Program Files\\Ollama\\ollama.exe"),
            Path("C:\\Program Files (x86)\\Ollama\\ollama.exe"),
        ]
    elif system == "Darwin":  # macOS
        paths = [
            Path.home() / ".ollama/bin/ollama",
            Path("/usr/local/bin/ollama"),
            Path("/opt/homebrew/bin/ollama"),
        ]
    else:  # Linux
        paths = [
            Path.home() / ".ollama/bin/ollama",
            Path("/usr/bin/ollama"),
            Path("/usr/local/bin/ollama"),
            Path("/opt/ollama/bin/ollama"),
        ]
    
    for path in paths:
        if path.exists() and path.is_file():
            logger.info(f"Found Ollama executable at: {path}")
            return str(path)
    
    return None


def _is_ollama_running(base_url: str = "http://localhost:11434", timeout: float = 2.0) -> bool:
    """
    Check if Ollama server is responding.
    
    Args:
        base_url: Ollama API base URL
        timeout: Request timeout in seconds
        
    Returns:
        True if Ollama is responsive, False otherwise.
    """
    try:
        response = httpx.get(
            f"{base_url}/api/tags",
            timeout=timeout,
        )
        is_running = response.status_code == 200
        if is_running:
            logger.info("Ollama is running and responsive")
        return is_running
    except Exception as e:
        logger.debug(f"Ollama health check failed: {e}")
        return False


def _launch_ollama(ollama_path: str) -> bool:
    """
    Launch Ollama server in background.
    
    Args:
        ollama_path: Path to ollama executable
        
    Returns:
        True if launch was successful (or already running), False on error.
    """
    system = platform.system()
    
    try:
        if system == "Windows":
            # Windows: launch ollama serve in background
            subprocess.Popen(
                [ollama_path, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        elif system == "Darwin":
            # macOS: ollama runs as daemon/service automatically
            # Just ensure it's started
            subprocess.Popen(
                [ollama_path, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        else:
            # Linux: launch in background
            subprocess.Popen(
                [ollama_path, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        
        logger.info(f"Launched Ollama: {ollama_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to launch Ollama: {e}")
        return False


def ensure_ollama_running(
    base_url: str = "http://localhost:11434",
    max_wait_seconds: int = 30,
    auto_launch: bool = True,
) -> Tuple[bool, str]:
    """
    Ensure Ollama is running. Auto-launch if configured and needed.
    
    Args:
        base_url: Ollama API base URL
        max_wait_seconds: Maximum time to wait for Ollama to become responsive
        auto_launch: Whether to auto-launch Ollama if not running
        
    Returns:
        Tuple (success: bool, message: str)
            - (True, "Ollama is running") if Ollama is responsive
            - (False, error_message) if Ollama could not be started
    """
    
    # Check if already running
    if _is_ollama_running(base_url):
        return True, "Ollama is already running"
    
    if not auto_launch:
        return False, "Ollama is not running and auto_launch is disabled"
    
    logger.info("Ollama not detected. Attempting auto-launch...")
    
    # Find ollama executable
    ollama_path = _find_ollama_executable()
    if not ollama_path:
        return False, "Ollama executable not found. Please install from https://ollama.ai"
    
    # Launch Ollama
    if not _launch_ollama(ollama_path):
        return False, f"Failed to launch Ollama from {ollama_path}"
    
    # Wait for Ollama to become responsive
    start_time = time.time()
    while time.time() - start_time < max_wait_seconds:
        if _is_ollama_running(base_url):
            return True, "Ollama started successfully"
        time.sleep(1)
    
    return False, f"Ollama did not become responsive within {max_wait_seconds} seconds"


def get_available_models(
    base_url: str = "http://localhost:11434",
    timeout: float = 5.0,
) -> list[str]:
    """
    Get list of available Ollama models.
    
    Args:
        base_url: Ollama API base URL
        timeout: Request timeout in seconds
        
    Returns:
        List of model names, or empty list if unable to connect.
    """
    try:
        response = httpx.get(
            f"{base_url}/api/tags",
            timeout=timeout,
        )
        if response.status_code == 200:
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            logger.info(f"Available Ollama models: {models}")
            return models
        return []
    except Exception as e:
        logger.warning(f"Could not fetch model list: {e}")
        return []


def ensure_model_available(
    model: str,
    base_url: str = "http://localhost:11434",
    auto_pull: bool = True,
) -> Tuple[bool, str]:
    """
    Ensure a specific model is available. Auto-pull if configured.
    
    Args:
        model: Model name (e.g., "qwen2.5:14b")
        base_url: Ollama API base URL
        auto_pull: Whether to auto-pull model if not available
        
    Returns:
        Tuple (success: bool, message: str)
    """
    available_models = get_available_models(base_url)
    
    # Check if model exists (handle partial matches like "qwen2.5" vs "qwen2.5:14b")
    model_exists = any(m.startswith(model.split(":")[0]) for m in available_models)
    
    if model_exists:
        return True, f"Model {model} is available"
    
    if not auto_pull:
        return False, f"Model {model} not found and auto_pull is disabled"
    
    logger.info(f"Model {model} not found. Attempting to pull...")
    
    try:
        # Ollama pull via subprocess
        subprocess.run(
            ["ollama", "pull", model],
            timeout=600,  # 10 minute timeout
            capture_output=True,
        )
        logger.info(f"Model {model} pulled successfully")
        return True, f"Model {model} pulled successfully"
    except Exception as e:
        logger.error(f"Failed to pull model {model}: {e}")
        return False, f"Failed to pull model {model}: {str(e)}"
