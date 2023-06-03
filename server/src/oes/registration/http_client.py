"""HTTP client module."""
from contextvars import ContextVar
from http.cookiejar import Cookie, CookieJar
from typing import Optional

import httpx

http_client_context: ContextVar[Optional[httpx.AsyncClient]] = ContextVar(
    "http_client_context", default=None
)
"""The client context."""

USER_AGENT = "OES Registration Server 0.1"
"""User agent."""


class NullCookieJar(CookieJar):
    """``CookieJar`` that does not store cookies."""

    def set_cookie(self, cookie: Cookie):
        # Do not set
        return


def setup_http_client() -> httpx.AsyncClient:
    """Set up the http client."""
    client = httpx.AsyncClient(
        headers={
            "User-Agent": USER_AGENT,
        },
        cookies=NullCookieJar(),
    )
    http_client_context.set(client)
    return client


def get_http_client() -> httpx.AsyncClient:
    """Get a :class:`httpx.AsyncClient`."""
    client = http_client_context.get()
    if not client:
        raise RuntimeError("HTTP client not configured")
    return client


async def shutdown_http_client():
    """Shut down the http client."""
    client = http_client_context.get()
    if client:
        await client.aclose()
