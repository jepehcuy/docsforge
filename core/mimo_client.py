"""AsyncOpenAI client with MiMo SSE/reasoning adapter.

Handles the 9router proxy behavior where:
- SSE is returned even for non-streaming requests
- MiMo models put response in reasoning_content instead of content

Pattern copied from promptforge/core/mimo_client.py and extended
with token usage tracking for DocsForge proof generation.
"""

import json
import os
import time
import httpx
from openai import AsyncOpenAI
from dataclasses import dataclass, field


@dataclass
class UsageStats:
    """Token usage statistics for a single API call."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    duration_ms: float = 0.0


@dataclass
class ClientStats:
    """Aggregated token usage across all API calls."""
    calls: list[UsageStats] = field(default_factory=list)

    @property
    def total_prompt_tokens(self) -> int:
        return sum(c.prompt_tokens for c in self.calls)

    @property
    def total_completion_tokens(self) -> int:
        return sum(c.completion_tokens for c in self.calls)

    @property
    def total_tokens(self) -> int:
        return sum(c.total_tokens for c in self.calls)

    @property
    def total_duration_ms(self) -> float:
        return sum(c.duration_ms for c in self.calls)

    def to_dict(self) -> dict:
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "num_calls": len(self.calls),
            "calls": [
                {
                    "model": c.model,
                    "prompt_tokens": c.prompt_tokens,
                    "completion_tokens": c.completion_tokens,
                    "total_tokens": c.total_tokens,
                    "duration_ms": round(c.duration_ms, 2),
                }
                for c in self.calls
            ],
        }


def get_mimo_client() -> AsyncOpenAI:
    """Return an AsyncOpenAI client pointing at MiMo-compatible endpoint."""
    return AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", "***"),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )


MIMO_MODEL = os.environ.get("MIMO_MODEL") or os.environ.get("DOCSFORGE_MODEL", "kr/claude-sonnet-4.5")


async def mimo_chat(
    client: AsyncOpenAI,
    model: str,
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 2048,
    stats: ClientStats | None = None,
) -> str:
    """Call MiMo model with SSE+reasoning_content fallback.

    MiMo models return SSE even for non-streaming requests,
    and put the response in reasoning_content instead of content.

    This function:
    1. Tries standard openai client first
    2. If content is empty, falls back to raw HTTP + SSE parsing
    3. Extracts reasoning_content as the actual response
    4. Tracks token usage in stats if provided
    """
    t0 = time.time()

    # Try standard call first
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        if content and content.strip():
            duration = (time.time() - t0) * 1000
            if stats is not None and response.usage:
                stats.calls.append(UsageStats(
                    prompt_tokens=response.usage.prompt_tokens or 0,
                    completion_tokens=response.usage.completion_tokens or 0,
                    total_tokens=response.usage.total_tokens or 0,
                    model=model,
                    duration_ms=duration,
                ))
            return content
        # Check reasoning_content on standard response
        reasoning = getattr(response.choices[0].message, "reasoning_content", None)
        if reasoning and reasoning.strip():
            duration = (time.time() - t0) * 1000
            if stats is not None and response.usage:
                stats.calls.append(UsageStats(
                    prompt_tokens=response.usage.prompt_tokens or 0,
                    completion_tokens=response.usage.completion_tokens or 0,
                    total_tokens=response.usage.total_tokens or 0,
                    model=model,
                    duration_ms=duration,
                ))
            return reasoning
    except Exception:
        pass

    # Fallback: raw HTTP to handle SSE + reasoning_content
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    api_key = os.environ.get("OPENAI_API_KEY", "***")

    async with httpx.AsyncClient(timeout=120.0) as http:
        resp = await http.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            },
        )

        text = resp.text
        duration = (time.time() - t0) * 1000

        # Parse SSE format
        if "data: " in text:
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("data: ") and line != "data: [DONE]":
                    try:
                        data = json.loads(line[6:])
                        choices = data.get("choices", [])
                        if choices:
                            msg = choices[0].get("message", {})
                            content = msg.get("content", "")
                            reasoning = msg.get("reasoning_content", "")

                            # Track usage from SSE response
                            usage = data.get("usage", {})
                            if stats is not None and usage:
                                stats.calls.append(UsageStats(
                                    prompt_tokens=usage.get("prompt_tokens", 0),
                                    completion_tokens=usage.get("completion_tokens", 0),
                                    total_tokens=usage.get("total_tokens", 0),
                                    model=model,
                                    duration_ms=duration,
                                ))

                            if content and content.strip():
                                return content
                            if reasoning and reasoning.strip():
                                return reasoning
                    except json.JSONDecodeError:
                        continue

        # Last resort: try parsing as JSON
        try:
            data = json.loads(text)
            choices = data.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                usage = data.get("usage", {})
                if stats is not None and usage:
                    stats.calls.append(UsageStats(
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        total_tokens=usage.get("total_tokens", 0),
                        model=model,
                        duration_ms=duration,
                    ))
                return msg.get("content", "") or msg.get("reasoning_content", "")
        except json.JSONDecodeError:
            pass

        if stats is not None:
            stats.calls.append(UsageStats(
                model=model, duration_ms=duration,
            ))

        return f"[MiMo adapter] Raw response: {text[:500]}"
