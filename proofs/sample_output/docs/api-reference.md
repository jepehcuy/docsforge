# API Reference

httpx public APIs. Sync + async functions. `Client`/`AsyncClient` for sessions.

## Functions

### Top-Level Request Functions

```python
def request(
    method: str,
    url: URL | str,
    *,
    content: RequestContent | None = None,
    data: RequestData | None = None,
    files: RequestFiles | None = None,
    json: Any | None = None,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | tuple[str, str] | None = None,
    proxy: ProxyTypes | None = None,
    proxies: dict[str, ProxyTypes] | None = None,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | bool = True,
    cert: CertTypes | None = None,
    trust_env: bool = True,
) -> Response: ...
```

Single-request convenience. Creates ephemeral `Client`, sends, closes.

```python
def stream(
    method: str,
    url: URL | str,
    *,
    content: RequestContent | None = None,
    data: RequestData | None = None,
    files: RequestFiles | None = None,
    json: Any | None = None,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | tuple[str, str] | None = None,
    proxy: ProxyTypes | None = None,
    proxies: dict[str, ProxyTypes] | None = None,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | bool = True,
    cert: CertTypes | None = None,
    trust_env: bool = True,
) -> Iterator[Response]: ...
```

Context manager for streaming responses.

```python
def get(url: URL | str, **kwargs) -> Response: ...
def options(url: URL | str, **kwargs) -> Response: ...
def head(url: URL | str, **kwargs) -> Response: ...
def post(url: URL | str, **kwargs) -> Response: ...
def put(url: URL | str, **kwargs) -> Response: ...
def patch(url: URL | str, **kwargs) -> Response: ...
def delete(url: URL | str, **kwargs) -> Response: ...
```

All pass `**kwargs` through to `request()`. Method set automatically.

## Classes

### `URL`

Module `httpx._urls`. Immutable URL representation.

```python
class URL:
    def __init__(self, url: URL | str | bytes = "", **kwargs: str | int | None) -> None: ...
```

**Properties (read-only):**

| Property | Type | Description |
|---|---|---|
| `scheme` | `str` | URL scheme |
| `host` | `str` | Hostname |
| `port` | `int \| None` | Port number |
| `path` | `str` | URL-decoded path |
| `query` | `str` | Raw query string |
| `params` | `QueryParams` | Parsed query parameters |
| `fragment` | `str` | Fragment identifier |
| `is_absolute_url` | `bool` | Has scheme + authority |
| `is_relative_url` | `bool` | No scheme |

**Methods:**

```python
def copy_with(self, **kwargs) -> URL: ...
def copy_set_param(self, key: str, value: str | int | float | None) -> URL: ...
def copy_add_param(self, key: str, value: str | int | float | None) -> URL: ...
def copy_remove_param(self, key: str) -> URL: ...
def copy_merge_params(self, params: QueryParamTypes) -> URL: ...
def join(self, url: URL | str) -> URL: ...
```

`join` resolves relative URL against self.

### `QueryParams`

Module `httpx._urls`. Mutable query parameter container.

```python
class QueryParams:
    def __init__(self, params: QueryParamTypes | None = None) -> None: ...
```

**Methods:**

```python
def keys(self) -> KeysView[str]: ...
def values(self) -> ValuesView[str]: ...
def items(self) -> ItemsView[str, str]: ...
def multi_items(self) -> list[tuple[str, str]]: ...
def get(self, key: str, default: str = "") -> str: ...
def get_list(self, key: str) -> list[str]: ...
def set(self, key: str, value: str | int | float | None) -> None: ...
def add(self, key: str, value: str | int | float | None) -> None: ...
def remove(self, key: str) -> None: ...
def merge(self, params: QueryParamTypes) -> None: ...
```

`set` replaces all values for key. `add` appends.

### `Headers`

Module `httpx._models`. Case-insensitive HTTP header mapping.

```python
class Headers:
    def __init__(self, headers: HeaderTypes | None = None, raw: list[RawHeader] | None = None) -> None: ...
```

**Properties:**

| Property | Type |
|---|---|
| `encoding` | `str` |

**Methods:**

```python
def raw(self) -> list[tuple[bytes, bytes]]: ...
def keys(self) -> list[str]: ...
def values(self) -> list[str]: ...
def items(self) -> list[tuple[str, str]]: ...
def multi_items(self) -> list[tuple[str, str]]: ...
def get(self, key: str, default: str | None = None) -> str | None: ...
def get_list(self, key: str) -> list[str]: ...
def update(self, headers: HeaderTypes) -> None: ...
def copy(self) -> Headers: ...
def __getitem__(self, key: str) -> str: ...
def __setitem__(self, key: str, value: str) -> None: ...
def __delitem__(self, key: str) -> None: ...
def __contains__(self, key: object) -> bool: ...
def __iter__(self) -> Iterator[str]: ...
def __len__(self) -> int: ...
def __eq__(self, other: object) -> bool: ...
def __repr__(self) -> str: ...
```

### `Request`

Module `httpx._models`. Immutable HTTP request.

```python
class Request:
    def __init__(
        self,
        method: str,
        url: URL | str,
        *,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: Any | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        params: QueryParamTypes | None = None,
        stream: SyncByteStream | AsyncByteStream | None = None,
    ) -> None: ...
```

**Properties:**

| Property | Type | Description |
|---|---|---|
| `url` | `URL` | Request URL |
| `headers` | `Headers` | Request headers |
| `cookies` | `Cookies` | Request cookies |
| `content` | `bytes \| None` | Read body (returns `None` if not read) |

**Methods:**

```python
def read(self) -> bytes: ...
async def aread(self) -> bytes: ...
def close(self) -> None: ...
async def aclose(self) -> None: ...
```

### `Response`

Module `httpx._models`. HTTP response. Supports sync + async streaming.

```python
class Response:
    def __init__(
        self,
        status_code: int,
        *,
        headers: Headers | None = None,
        stream: SyncByteStream | AsyncByteStream | None = None,
        content: bytes | None = None,
        http_version: str | None = None,
        reason_phrase: str | None = None,
        request: Request | None = None,
        elapsed: timedelta | None = None,
    ) -> None: ...
```

**Properties:**

| Property | Type | Description |
|---|---|---|
| `status_code` | `int` | HTTP status code |
| `http_version` | `str` | e.g. `"HTTP/1.1"` |
| `url` | `URL` | Final URL (after redirects) |
| `request` | `Request` | Associated request |
| `elapsed` | `timedelta` | Request duration |
| `content` | `bytes` | Decoded body |
| `text` | `str` | Decoded text |
| `encoding` | `str \| None` | Content encoding |
| `cookies` | `Cookies` | Response cookies |
| `links` | `dict` | Parsed Link header |

**Methods:**

```python
def raise_for_status(self) -> None: ...
def json(self, **kwargs) -> Any: ...
def close(self) -> None: ...
async def aclose(self) -> None: ...
def read(self) -> bytes: ...
async def aread(self) -> bytes: ...
def iter_bytes(self, chunk_size: int | None = None) -> Iterator[bytes]: ...
def iter_text(self, chunk_size: int | None = None) -> Iterator[str]: ...
def iter_lines(self) -> Iterator[str]: ...
def iter_raw(self, chunk_size: int | None = None) -> Iterator[bytes]: ...
async def aiter_bytes(self, chunk_size: int | None = None) -> AsyncIterator[bytes]: ...
async def aiter_text(self, chunk_size: int | None = None) -> AsyncIterator[str]: ...
async def aiter_lines(self) -> AsyncIterator[str]: ...
async def aiter_raw(self, chunk_size: int | None = None) -> AsyncIterator[bytes]: ...
```

`raise_for_status()` raises `HTTPStatusError` for 4xx/5xx. `iter_*` consume stream incrementally.

### `Cookies`

Module `httpx._models`. Cookie container.

```python
class Cookies:
    def __init__(self, cookies: CookieTypes | None = None) -> None: ...
```

**Methods:**

```python
def set(
    self,
    name: str,
    value: str,
    *,
    path: str = "/",
    domain: str | None = None,
    secure: bool = False,
    expires: int | None = None,
    httponly: bool = False,
) -> None: ...
def get(self, name: str, default: str | None = None) -> str | None: ...
def delete(self, name: str, *, path: str = "/", domain: str | None = None) -> None: ...
def clear(self, domain: str | None = None, path: str | None = None) -> None: ...
def update(self, cookies: CookieTypes) -> None: ...
```

Dict-like access: `cookies["name"]`, `del cookies["name"]`, iteration.

### `Client`

Module `httpx._client`. Sync HTTP client. Connection pool, redirects, auth.

```python
class Client(BaseClient):
    def __init__(
        self,
        *,
        auth: AuthTypes | None = None,
        cookies: CookieTypes | None = None,
        headers: HeaderTypes | None = None,
        params: QueryParamTypes | None = None,
        base_url: URL | str = "",
        proxy: ProxyTypes | None = None,
        proxies: dict[str, ProxyTypes] | None = None,
        mounts: dict[str, BaseTransport | AsyncBaseTransport] | None = None,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        follow_redirects: bool = False,
        limits: Limits | None = None,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        event_hooks: dict[str, list[Callable]] | None = None,
        base_transport: BaseTransport | None = None,
        proxy_transport: BaseTransport | None = None,
        verify: ssl.SSLContext | bool = True,
        cert: CertTypes | None = None,
        trust_env: bool = True,
    ) -> None: ...
```

**Properties:**

| Property | Type | Description |
|---|---|---|
| `is_closed` | `bool` | Client closed state |
| `base_url` | `URL` | Base URL prefix |
| `headers` | `Headers` | Default headers |
| `cookies` | `Cookies` | Session cookies |
| `params` | `QueryParams` | Default query params |

**HTTP Methods:**

```python
def request(self, method: str, url: URL | str, **kwargs) -> Response: ...
def get(self, url: URL | str, **kwargs) -> Response: ...
def post(self, url: URL | str, **kwargs) -> Response: ...
# ... all HTTP methods

def stream(self, method: str, url: URL | str, **kwargs) -> ContextManager[Iterator[Response]]: ...
def send(self, request: Request, **kwargs) -> Response: ...
def build_request(self, method: str, url: URL | str, **kwargs) -> Request: ...
```

**Lifecycle:**

```python
def close(self) -> None: ...
def __enter__(self) -> Client: ...
def __exit__(self, ...) -> None: ...
```

### `AsyncClient`

Module `httpx._client`. Async HTTP client. Same interface as `Client` but async.

```python
class AsyncClient(BaseClient):
    def __init__(self, **kwargs) -> None: ...
    # Same parameters as Client
```

**HTTP Methods (all async):**

```python
async def request(self, method: str, url: URL | str, **kwargs) -> Response: ...
async def get(self, url: URL | str, **kwargs) -> Response: ...
# ... all HTTP methods
```
