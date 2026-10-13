import ipaddress
import socket
from urllib.parse import urlsplit

BLOCKED_HOSTS = {"localhost", "localhost.localdomain"}

def validate_public_url(url: str, allowed_domains: set[str] | None = None, require_allowed: bool = True) -> None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("Target must be an absolute HTTP(S) URL")
    host = parts.hostname.lower().rstrip(".")
    if require_allowed and host not in {d.lower().rstrip(".") for d in (allowed_domains or set())}:
        raise ValueError(f"Host {host} is outside the configured allowed domains")
    if host in BLOCKED_HOSTS:
        raise ValueError("Local hostnames are not crawlable")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parts.port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve host: {exc}") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError(f"Resolved destination {address} is not a public IP")

def validate_redirect(url: str, allowed_domains: set[str]) -> None:
    validate_public_url(url, allowed_domains)

def validate_public_destination(url: str) -> None:
    validate_public_url(url, require_allowed=False)
