# Configuration

## Installation

```bash
pip install httpx
```

## Prerequisites

- Python 3.7+
- Dependencies: `httpcore>=0.15.0,<0.16.0`, `certifi`, `idna`, `sniffio`

## Development Setup

1. Clone repository: `git clone https://github.com/encode/httpx`
2. Create virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Install package in dev mode: `pip install -e .`
6. Run tests: `pytest`
7. Run linters: `flake8 httpx tests`
8. Type check: `mypy httpx`

## Core Configuration Classes

### `Timeout`

Module `httpx._config`.

```python
Timeout(timeout=5.0, connect=None, read=None, write=None, pool=None)
```

- `timeout`: overall timeout (seconds)
- `connect`: connection timeout
- `read`: response read timeout
- `write`: request write timeout
- `pool`: connection pool timeout

Default: `DEFAULT_TIMEOUT_CONFIG = Timeout(timeout=5.0)`

### `Limits`

Module `httpx._config`.

```python
Limits(max_connections=100, max_keepalive_connections=20, keepalive_expiry=None)
```

Default: `DEFAULT_LIMITS = Limits(max_connections=100, max_keepalive_connections=20)`

### `Proxy`

Module `httpx._config`.

```python
Proxy(url, headers=None, auth=None)
```

## Environment Variables

### HTTPX Variables

| Variable | Description |
|---|---|
| `HTTPX_PROXY` | Proxy URL for all requests |
| `HTTPX_NO_PROXY` | Comma-separated list of domains to bypass proxy |
| `HTTPX_PROXY_<SCHEME>` | Proxy for specific scheme (HTTP/HTTPS) |

### System Variables

| Variable | Description |
|---|---|
| `SSL_CERT_FILE` | Path to SSL certificate bundle |
| `REQUEST_CA_BUNDLE` | Request CA bundle path |
| `CURL_CA_BUNDLE` | cURL CA bundle path |

### Authentication Variables

| Variable | Description |
|---|---|
| `NETRC` | Path to .netrc file (default: `~/.netrc`) |
| `NETRC_MACHINE` | Machine for .netrc lookup |

`.netrc` format:

```
machine <host> login <user> password <pass>
```

## Build & Deploy

```bash
# Build
python -m build

# Upload
twine upload dist/*

# Docs
mkdocs serve  # local
mkdocs gh-deploy  # GitHub Pages
```

## Troubleshooting

### SSL Errors

- Set `SSL_CERT_FILE` environment variable
- Use `httpx.create_ssl_context()` for custom SSL configuration
- Disable verification (insecure): `client = httpx.Client(verify=False)`

### Proxy Issues

- Check `HTTP_PROXY`/`HTTPS_PROXY` system variables
- Use `httpx.Proxy()` class for explicit proxy configuration
- Test with: `client = httpx.Client(proxy="http://proxy.example.com:8080")`

### Timeout Errors

- Default timeout: 5 seconds
- Increase: `client = httpx.Client(timeout=30.0)`
- Configure per-operation: `client.get(url, timeout=10.0)`

### Connection Limits

- Default: 100 connections, 20 keepalive
- Adjust: `httpx.Limits(max_connections=200)`
- Monitor with: `client = httpx.Client(limits=limits)`
