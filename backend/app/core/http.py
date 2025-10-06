import httpx
from contextlib import asynccontextmanager

DEFAULT_UA = (
    "HackAnythingScanner/0.1 (+https://example.local; contact=student@example.edu) "
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

TIMEOUT = httpx.Timeout(10.0, connect=5.0)
HEADERS = {"User-Agent": DEFAULT_UA, "Accept": "*/*"}

@asynccontextmanager
async def client_for():
    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        headers=HEADERS,
        follow_redirects=True,
        http2=True,
        verify=True,
    ) as client:
        yield client
