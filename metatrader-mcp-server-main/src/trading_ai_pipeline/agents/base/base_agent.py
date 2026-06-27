"""
Base AI Agent interface.

All AI agents inherit from this class. Handles:
- HTTP calls to any OpenAI-compatible API (Ollama, OpenAI, Qwen, DeepSeek, Llama)
- JSON structured output parsing
- Retry logic with exponential backoff
- Token counting
- Timeout handling
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("BaseAgent")

T = TypeVar("T", bound=BaseModel)


class AgentConfig(BaseModel):
    """Configuration for one AI agent."""

    model: str = "qwen2.5:14b"
    api_base: str = "http://localhost:11434/v1"
    api_key: str = "ollama"
    temperature: float = 0.1
    max_tokens: int = 2048
    timeout_seconds: float = 60.0
    max_retries: int = 3
    retry_delay_seconds: float = 2.0
    system_prompt_extra: str = ""  # appended to base system prompt


class AgentResponse(BaseModel, Generic[T]):
    """Wrapper for an agent's structured response."""

    success: bool
    data: Optional[Any] = None        # parsed Pydantic model
    raw_text: str = ""
    error: Optional[str] = None
    tokens_used: int = 0
    model_used: str = ""
    latency_ms: float = 0.0
    retries: int = 0


class BaseAgent(ABC, Generic[T]):
    """
    Abstract base class for all AI agents.

    Subclasses must implement:
    - `output_schema`: the Pydantic class this agent returns
    - `system_prompt`: the agent's role and instructions
    - `build_user_prompt(context)`: builds the user message from pipeline data
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self._client = httpx.Client(timeout=config.timeout_seconds)

    @property
    @abstractmethod
    def output_schema(self) -> Type[T]:
        """The Pydantic model this agent returns."""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The agent's system prompt (role, instructions, output format)."""
        ...

    @abstractmethod
    def build_user_prompt(self, context: Dict[str, Any]) -> str:
        """Build the user message from context data."""
        ...

    def _build_messages(self, user_prompt: str) -> list[Dict[str, str]]:
        system = self.system_prompt
        if self.config.system_prompt_extra:
            system += f"\n\n{self.config.system_prompt_extra}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ]

    def _call_api(self, messages: list[Dict[str, str]]) -> tuple[str, int]:
        """Make one API call. Returns (raw_text, tokens_used)."""
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        url = f"{self.config.api_base.rstrip('/')}/chat/completions"

        response = self._client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return content, tokens

    def _parse_response(self, raw: str) -> T:
        """Parse JSON response into the output schema."""
        # Strip markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

        parsed = json.loads(text)
        return self.output_schema(**parsed)

    def run(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Execute the agent with retry logic.

        Args:
            context: Dictionary of data available to the agent.
                     Typically extracted from PipelineContext.

        Returns:
            AgentResponse with parsed data or error information.
        """
        user_prompt = self.build_user_prompt(context)
        messages = self._build_messages(user_prompt)
        start_time = time.monotonic()

        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                raw_text, tokens = self._call_api(messages)
                parsed = self._parse_response(raw_text)
                latency = (time.monotonic() - start_time) * 1000

                logger.info(
                    f"{self.__class__.__name__} completed | "
                    f"model={self.config.model} | tokens={tokens} | "
                    f"latency={latency:.0f}ms | attempt={attempt + 1}"
                )

                return AgentResponse(
                    success=True,
                    data=parsed,
                    raw_text=raw_text,
                    tokens_used=tokens,
                    model_used=self.config.model,
                    latency_ms=latency,
                    retries=attempt,
                )

            except (httpx.HTTPError, httpx.TimeoutException) as e:
                last_error = f"HTTP error: {e}"
                logger.warning(f"{self.__class__.__name__} HTTP error attempt {attempt + 1}: {e}")
            except json.JSONDecodeError as e:
                last_error = f"JSON parse error: {e}"
                logger.warning(f"{self.__class__.__name__} JSON parse error attempt {attempt + 1}: {e}")
            except ValidationError as e:
                last_error = f"Schema validation error: {e}"
                logger.warning(f"{self.__class__.__name__} validation error attempt {attempt + 1}: {e}")
            except Exception as e:
                last_error = f"Unexpected error: {e}"
                logger.error(f"{self.__class__.__name__} unexpected error attempt {attempt + 1}: {e}")

            if attempt < self.config.max_retries - 1:
                delay = self.config.retry_delay_seconds * (2 ** attempt)
                logger.info(f"Retrying in {delay:.1f}s...")
                time.sleep(delay)

        latency = (time.monotonic() - start_time) * 1000
        return AgentResponse(
            success=False,
            error=last_error,
            model_used=self.config.model,
            latency_ms=latency,
            retries=self.config.max_retries,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
