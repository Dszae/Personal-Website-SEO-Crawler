from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

ALLOWED_SCHEMES = {"http", "https"}

def normalize_url(url: str, base: str | None = None, strip_query: bool = False) -> str:
    value = urljoin(base, url) if base else url
    parts = urlsplit(value.strip())
    if parts.scheme.lower() not in ALLOWED_SCHEMES or not parts.netloc:
        raise ValueError("Only absolute HTTP(S) URLs are allowed")
    host = (parts.hostname or "").lower().rstrip(".")
    port = parts.port
    if (parts.scheme.lower() == "http" and port == 80) or (parts.scheme.lower() == "https" and port == 443):
        port = None
    netloc = host if port is None else f"{host}:{port}"
    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"
    query = "" if strip_query else urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    return urlunsplit((parts.scheme.lower(), netloc, path, query, ""))

def same_origin(left: str, right: str) -> bool:
    a, b = urlsplit(left), urlsplit(right)
    return a.scheme.lower() == b.scheme.lower() and (a.hostname or "").lower() == (b.hostname or "").lower() and a.port == b.port

def is_http_url(url: str) -> bool:
    try:
        return urlsplit(url).scheme.lower() in ALLOWED_SCHEMES and bool(urlsplit(url).netloc)
    except ValueError:
        return False
