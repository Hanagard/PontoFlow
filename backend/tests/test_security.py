from starlette.requests import Request

from lib.security import client_ip


def make_request(peer: str, headers: dict[str, str] | None = None) -> Request:
    raw_headers = [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw_headers,
                    "client": (peer, 12345), "server": ("testserver", 80), "scheme": "http"})


def test_forwarded_header_is_ignored_without_trusted_proxy(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "")
    request = make_request("198.51.100.10", {"X-Forwarded-For": "203.0.113.9"})
    assert client_ip(request) == "198.51.100.10"


def test_forwarded_chain_is_used_only_behind_trusted_proxy(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "127.0.0.1,10.0.0.0/8")
    request = make_request("127.0.0.1", {"X-Forwarded-For": "203.0.113.9, 10.1.2.3"})
    assert client_ip(request) == "203.0.113.9"
