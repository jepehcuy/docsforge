"""LLM client with MiMo SSE/reasoning_content adapter."""

import json
import os
import httpx
from openai import AsyncOpenAI


def get_client() -> AsyncOpenAI:
    """Return an AsyncOpenAI client pointing at MiMo-compatible endpoint."""
    return AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", "sk-placeholder"),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )


DEFAULT_MODEL = os.environ.get("DOCSFORGE_MODEL", "xiaomi/mimo-v2.5-pro")


async def chat(
    client: AsyncOpenAI,
    model: str,
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> tuple[str, int]:
    """Call LLM with SSE+reasoning_content fallback for MiMo.

    Returns (content, tokens_used).
    """
    # Try standard openai client first
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        usage = response.usage
        tokens = usage.total_tokens if usage else 0
        if content and content.strip():
            return content, tokens
    except Exception:
        pass

    # Fallback: raw HTTP for MiMo SSE + reasoning_content
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    api_key = os.environ.get("OPENAI_API_KEY", "sk-placeholder")
    tokens_used = 0

    async with httpx.AsyncClient(timeout=180.0) as http:
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
        content = ""

        if "data: " in text:
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("data: ") and line != "data: [DONE]":
                    try:
                        data = json.loads(line[6:])
                        choices = data.get("choices", [])
                        if choices:
                            msg = choices[0].get("message", {})
                            c = msg.get("content", "")
                            r = msg.get("reasoning_content", "")
                            if c and c.strip():
                                content = c
                            elif r and r.strip() and not content:
                                content = r
                        usage = data.get("usage", {})
                        if usage:
                            tokens_used = usage.get("total_tokens", tokens_used)
                    except json.JSONDecodeError:
                        continue
        else:
            try:
                data = json.loads(text)
                choices = data.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    content = msg.get("content", "") or msg.get("reasoning_content", "")
                usage = data.get("usage", {})
                if usage:
                    tokens_used = usage.get("total_tokens", 0)
            except json.JSONDecodeError:
                content = f"[LLM adapter] Could not parse response: {text[:300]}"

        return content, tokens_used
