"""
Free AI Providers Management System

Auto-discovers and initializes only FREE AI providers:
1. Ollama (local, open-source, 100% free)
2. Groq API (free tier with generous limits)
3. Together AI (free tier with credits)
4. Hugging Face Inference (free tier)
5. Local LLama.cpp (open-source, free)

No API fees, no credit card required for core functionality.
"""
import asyncio
import logging
import os
import subprocess
import httpx
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)


class FreeAIProviderManager:
    """Manages all FREE AI providers with auto-detection."""

    PROVIDERS = {
        "ollama": {
            "type": "local",
            "url": "http://localhost:11434",
            "health_endpoint": "/api/tags",
            "default_model": "qwen2.5:14b",
            "executable": "ollama",
            "cost": "FREE (local)",
            "description": "Open-source, runs locally, no internet needed",
        },
        "groq": {
            "type": "cloud",
            "url": "https://api.groq.com/openai/v1",
            "default_model": "mixtral-8x7b-32768",
            "env_key": "GROQ_API_KEY",
            "cost": "FREE (30k tokens/min)",
            "description": "Fast inference, free tier, no credit card",
            "signup": "https://console.groq.com",
        },
        "together": {
            "type": "cloud",
            "url": "https://api.together.xyz/v1",
            "default_model": "meta-llama/Llama-2-70b-chat-hf",
            "env_key": "TOGETHER_API_KEY",
            "cost": "FREE ($1 credit/month)",
            "description": "Free tier with monthly credits",
            "signup": "https://www.together.ai",
        },
        "huggingface": {
            "type": "cloud",
            "url": "https://api-inference.huggingface.co",
            "default_model": "meta-llama/Llama-2-70b-chat-hf",
            "env_key": "HUGGINGFACE_API_KEY",
            "cost": "FREE (rate limited)",
            "description": "Free inference with rate limits",
            "signup": "https://huggingface.co",
        },
    }

    def __init__(self):
        self.available_providers: Dict[str, Dict] = {}
        self.active_provider: Optional[str] = None
        self.logger = logging.getLogger(__name__)

    async def auto_detect_and_setup_all(self) -> Tuple[bool, str]:
        """Auto-detect and setup all FREE AI providers."""
        self.logger.info("[*] Starting auto-detection of FREE AI providers...")
        setup_results = []

        for provider_name in self.PROVIDERS.keys():
            result = await self._setup_provider(provider_name)
            setup_results.append((provider_name, result))
            if result["available"]:
                self.available_providers[provider_name] = result
                self.logger.info(
                    f"[+] {provider_name}: READY ({result.get('cost', 'FREE')})"
                )
            else:
                self.logger.debug(
                    f"[-] {provider_name}: {result.get('error', 'Not available')}"
                )

        if not self.available_providers:
            return False, (
                "No FREE AI providers detected.\n"
                "Quick setup:\n"
                "  1. Ollama: https://ollama.ai\n"
                "  2. Groq: https://console.groq.com (get free API key)\n"
                "  3. Together: https://www.together.ai (get free credits)"
            )

        # Select primary provider (prefer local Ollama, then free cloud)
        self.active_provider = self._select_primary_provider()
        self.logger.info(f"[+] Primary provider: {self.active_provider.upper()}")

        summary = f"Auto-detected {len(self.available_providers)} FREE provider(s)"
        return True, summary

    async def _setup_provider(self, provider_name: str) -> Dict:
        """Setup individual provider."""
        provider_config = self.PROVIDERS[provider_name]
        result = {
            "name": provider_name,
            "available": False,
            "cost": provider_config.get("cost", "FREE"),
        }

        if provider_config["type"] == "local":
            # Check if local service is running
            available, error = await self._check_local_service(provider_config)
            if available:
                result["available"] = True
                result["url"] = provider_config["url"]
                result["model"] = provider_config["default_model"]
            else:
                result["error"] = error
                # Try to auto-launch
                if provider_name == "ollama":
                    launch_ok, msg = await self._launch_ollama()
                    if launch_ok:
                        result["available"] = True
                        result["url"] = provider_config["url"]
                        result["model"] = provider_config["default_model"]
        else:
            # Check if cloud API key exists
            api_key = os.getenv(provider_config.get("env_key", ""))
            if api_key:
                # Verify API key works
                available = await self._verify_api_key(provider_name, api_key)
                if available:
                    result["available"] = True
                    result["api_key"] = api_key
                    result["url"] = provider_config["url"]
                    result["model"] = provider_config["default_model"]
                else:
                    result["error"] = "API key invalid or quota exceeded"
            else:
                result["error"] = (
                    f"Set {provider_config.get('env_key')} environment variable"
                )
                result["signup_url"] = provider_config.get("signup", "")

        return result

    async def _check_local_service(self, config: Dict) -> Tuple[bool, str]:
        """Check if local service is running."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{config['url']}{config.get('health_endpoint', '/health')}"
                )
                return response.status_code == 200, ""
        except Exception as e:
            return False, str(e)

    async def _launch_ollama(self) -> Tuple[bool, str]:
        """Try to auto-launch Ollama."""
        try:
            # Check if ollama executable exists
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                return False, "Ollama not installed"

            # Try to launch Ollama in background
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Wait for it to start
            await asyncio.sleep(5)

            # Verify it's running
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get("http://localhost:11434/api/tags")
                if response.status_code == 200:
                    return True, "Ollama launched successfully"
        except Exception as e:
            return False, str(e)

        return False, "Could not launch Ollama"

    async def _verify_api_key(self, provider: str, api_key: str) -> bool:
        """Verify API key is valid."""
        try:
            config = self.PROVIDERS[provider]
            headers = {"Authorization": f"Bearer {api_key}"}

            async with httpx.AsyncClient(timeout=10) as client:
                if provider == "groq":
                    # Test Groq API
                    response = await client.post(
                        f"{config['url']}/chat/completions",
                        headers=headers,
                        json={"model": "mixtral-8x7b-32768", "messages": []},
                        timeout=10,
                    )
                    # Expect 400 (empty messages) not 401 (auth error)
                    return response.status_code != 401

                elif provider == "together":
                    response = await client.get(
                        "https://api.together.xyz/v1/models",
                        headers=headers,
                        timeout=10,
                    )
                    return response.status_code == 200

                elif provider == "huggingface":
                    response = await client.post(
                        "https://api-inference.huggingface.co/models/meta-llama/Llama-2-7b-hf",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json={"inputs": "test"},
                        timeout=10,
                    )
                    return response.status_code != 403

            return False
        except Exception:
            return False

    def _select_primary_provider(self) -> str:
        """Select best available FREE provider."""
        # Priority: local Ollama > Groq > Together > HuggingFace
        priority = ["ollama", "groq", "together", "huggingface"]
        for provider in priority:
            if provider in self.available_providers:
                return provider
        # Fallback to first available
        return list(self.available_providers.keys())[0]

    def get_active_provider_config(self) -> Dict:
        """Get configuration for active provider."""
        if not self.active_provider or self.active_provider not in self.available_providers:
            raise ValueError("No active provider available")
        return self.available_providers[self.active_provider]

    def get_all_providers_status(self) -> Dict[str, Dict]:
        """Get status of all providers."""
        status = {}
        for name, provider in self.PROVIDERS.items():
            if name in self.available_providers:
                status[name] = {
                    "status": "AVAILABLE",
                    "cost": provider.get("cost", "FREE"),
                    "model": self.available_providers[name].get("model", "auto"),
                }
            else:
                status[name] = {
                    "status": "NOT_AVAILABLE",
                    "cost": provider.get("cost", "FREE"),
                    "reason": "Install or set API key",
                }
        return status


# Global singleton instance
_manager_instance: Optional[FreeAIProviderManager] = None


async def get_free_ai_manager() -> FreeAIProviderManager:
    """Get or create global free AI provider manager."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = FreeAIProviderManager()
        await _manager_instance.auto_detect_and_setup_all()
    return _manager_instance


def get_active_free_provider() -> Optional[str]:
    """Get currently active free provider."""
    global _manager_instance
    if _manager_instance:
        return _manager_instance.active_provider
    return None


def get_all_free_providers() -> List[str]:
    """Get list of available free providers."""
    global _manager_instance
    if _manager_instance:
        return list(_manager_instance.available_providers.keys())
    return []
