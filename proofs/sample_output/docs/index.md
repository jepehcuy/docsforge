# HTTPX

Python HTTP client library. Full-featured. Sync/async support. HTTP/1.1 and HTTP/2. Built on `httpcore`.

## Quick Start

```python
import httpx

# Sync client
response = httpx.get('https://example.com')
print(response.status_code, response.text)

# Async client
async def main():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://example.com')
        print(response.status_code, response.text)

asyncio.run(main())
```

**Install:**

```bash
pip install httpx
```

## Key Features

- **Sync/Async Support** – consistent API for both
- **HTTP/1.1 and HTTP/2** – via httpcore
- **Connection Pooling** – efficient connection reuse
- **Redirect Handling** – configurable redirect limits
- **Cookie Persistence** – across requests
- **Authentication** – Basic, Digest, NetRC, custom
- **Proxy Support** – HTTP/HTTPS proxies
- **Timeouts** – configurable per operation
- **Streaming** – sync and async streaming responses
- **Type Hints** – `py.typed` marker included

## Resources

- [Architecture](architecture.md)
- [API Reference](api-reference.md)
- [Examples](examples.md)
- [Configuration](configuration.md)
- [Changelog](changelog.md)
