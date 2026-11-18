import os
from starlette.requests import Request
from lib.security import client_ip

def make_request(peer: str, forwarded: str = "") -> Request:
    headers = []
    if forwarded:
        headers.append((b"x-forwarded-for", forwarded.encode("ascii")))
    return Request({"type":"http","http_version":"1.1","method":"GET","scheme":"http","path":"/","raw_path":b"/","query_string":b"","headers":headers,"client":(peer,12345),"server":("testserver",80)})

def test_forwarded_header_is_ignored_without_trusted_proxy(monkeypatch):
    monkeypatch.delenv("TRUSTED_PROXY_CIDRS", raising=False)
    assert client_ip(make_request("198.51.100.10", "203.0.113.9")) == "198.51.100.10"

def test_forwarded_header_is_used_only_from_trusted_proxy(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "10.0.0.0/8")
    assert client_ip(make_request("10.0.0.5", "203.0.113.9")) == "203.0.113.9"

def test_forwarded_chain_skips_trusted_hops(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "10.0.0.0/8,192.0.2.0/24")
    assert client_ip(make_request("10.0.0.5", "203.0.113.9, 192.0.2.15")) == "203.0.113.9"

def test_malformed_forwarded_values_fall_back_to_peer(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "10.0.0.0/8")
    assert client_ip(make_request("10.0.0.5", "not-an-ip")) == "10.0.0.5"
