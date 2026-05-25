# Architecture

## Overview

httpx is an async-capable HTTP client for Python. Built on `httpcore` for transport. Supports HTTP/1.1 and HTTP/2.

## Project Structure

```
httpx/                  # Core package
├── _client.py          # Client implementation
├── _models.py          # Request/Response models
├── _main.py            # CLI entrypoint
├── _api.py             # High-level API functions
├── _urls.py            # URL handling
├── _auth.py            # Authentication handlers
├── _config.py          # Timeout/SSL config
├── _multipart.py       # Multipart data
├── _content.py         # Content encoding/decoding
├── _decoders.py        # Response decoders
├── _exceptions.py      # Exception hierarchy
├── _status_codes.py    # HTTP status codes
├── _utils.py           # Utility functions
├── _types.py           # Type definitions
└── _transports/        # Transport implementations
    ├── base.py         # Abstract transport interfaces
    ├── default.py      # Default httpcore transport
    ├── wsgi.py         # WSGI transport
    ├── asgi.py         # ASGI transport
    └── mock.py         # Mock transport
```

## Design Patterns

| Pattern | Implementation |
|---|---|
| **Transport** | Abstract `BaseTransport`/`AsyncBaseTransport` |
| **Client** | `Client`/`AsyncClient` facade over transport |
| **Strategy** | Multiple transport implementations |
| **Builder** | Client configuration via method chaining |
| **Decorator** | Authentication handlers |
| **Adapter** | Cookie compatibility layers |
| **Command** | CLI interface in `_main.py` |

## Data Flow

1. User creates `Client`/`AsyncClient` with config
2. Client builds `Request` with headers, params, content
3. Transport layer sends via httpcore (or mock/WSGI/ASGI)
4. Raw response decoded to `Response` model
5. Event hooks fire (if configured)
6. Response returned to user
7. Client manages connection pool, redirects, cookies

## Key Components

| Component | Role |
|---|---|
| `Client`/`AsyncClient` | Main entry points. Manage config, pools, middleware |
| `HTTPTransport` | Default httpcore-based transport |
| `Request`/`Response` | HTTP message models |
| `URL`/`QueryParams` | URL handling |
| Auth handlers | `BasicAuth`, `DigestAuth`, `NetRCAuth` |
| `Timeout`/`Limits`/`Proxy` | Configuration objects |
| Decoders | `GZipDecoder`, `BrotliDecoder`, etc. |
| `MultipartStream` | Multipart form encoding |

## Technology Stack

- **Language**: Python 3.8+
- **Async**: asyncio, anyio
- **HTTP core**: httpcore
- **SSL**: certifi
- **Encoding**: chardet
- **CLI**: click
- **Testing**: pytest
- **Docs**: MkDocs + Material theme
- **Build**: pyproject.toml, PEP 517/518
