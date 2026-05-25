# Examples

## Basic Usage

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

## Client Configuration

```python
# Create client with custom settings
client = httpx.Client(
    base_url='https://api.example.com',
    headers={'Authorization': 'Bearer token123'},
    timeout=10.0
)

# Get request with path params
response = client.get('/users/{id}', path_params={'id': 42})
print(response.json())

# POST with JSON
response = client.post('/users', json={'name': 'Alice'})
print(response.status_code)
```

## Advanced Usage

```python
# Custom transport for retries
from httpx import AsyncHTTPTransport
transport = AsyncHTTPTransport(retries=3)

async def main():
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get('https://httpbin.org/status/500')
        print(f'Retry status: {response.status_code}')

# Event hooks for logging
def log_response(response):
    print(f'{response.request.method} {response.url} -> {response.status_code}')

with httpx.Client(event_hooks={'response': [log_response]}) as client:
    client.get('https://httpbin.org/get')

# HTTP/2 support
client = httpx.Client(http2=True)
response = client.get('https://example.com')
print(response.http_version)
```

## Custom Auth

```python
from httpx import Auth

class TokenAuth(Auth):
    def auth_flow(self, request):
        request.headers['Authorization'] = f'Bearer {self.token}'
        yield request

client = httpx.Client(auth=TokenAuth(token='secret'))
response = client.get('https://api.example.com')
```

## Streaming

```python
# Sync streaming
with httpx.Client() as client:
    with client.stream('GET', 'https://example.com') as response:
        for chunk in response.iter_bytes():
            process_chunk(chunk)

# Async streaming
async def stream_download():
    async with httpx.AsyncClient() as client:
        async with client.stream('GET', 'https://example.com/large-file') as response:
            async for chunk in response.aiter_bytes():
                print(f'Received {len(chunk)} bytes')
```

## Error Handling

```python
try:
    response = client.get('https://api.com/endpoint')
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    print(f'HTTP error: {e.response.status_code}')
except httpx.ConnectError as e:
    print(f'Connection failed: {e}')
```

## Proxies

```python
client = httpx.Client(
    proxy='http://proxy.example.com:8080',
    proxy_auth=httpx.BasicAuth('user', 'pass')
)
```

## SSL Configuration

```python
import ssl
ctx = ssl.create_default_context()
ctx.load_cert_chain('client.pem', 'key.pem')
client = httpx.Client(verify=ctx)
```

## Session Persistence

```python
client = httpx.Client(cookies={'session': 'abc123'})
response = client.get('https://api.com/me')
```
