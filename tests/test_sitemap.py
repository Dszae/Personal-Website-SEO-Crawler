import requests

from crawler.sitemap import discover_sitemap

def _urlset(*urls):
    locs = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    return f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{locs}</urlset>'.encode()

def _index(*urls):
    locs = "".join(f"<sitemap><loc>{url}</loc></sitemap>" for url in urls)
    return f'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{locs}</sitemapindex>'.encode()

def _serve(monkeypatch, pages):
    fetched = []
    class Response:
        def __init__(self, url):
            self.url = url
        @property
        def content(self):
            return pages[self.url]
        def raise_for_status(self):
            if self.url not in pages:
                raise requests.HTTPError(f"404 for {self.url}")
    def fake_get(url, *args, **kwargs):
        fetched.append(url)
        return Response(url)
    monkeypatch.setattr("crawler.sitemap.requests.get", fake_get)
    return fetched

def test_sitemap_index_fetches_each_child_sitemap(monkeypatch):
    fetched = _serve(monkeypatch, {
        "https://example.com/sitemap.xml": _index("https://example.com/sitemap-pages.xml", "https://example.com/sitemap-posts.xml"),
        "https://example.com/sitemap-pages.xml": _urlset("https://example.com/", "https://example.com/about"),
        "https://example.com/sitemap-posts.xml": _urlset("https://example.com/blog/first"),
    })
    entries, errors = discover_sitemap("https://example.com/", "", 1, "test")
    assert [entry["url"] for entry in entries] == ["https://example.com/", "https://example.com/about", "https://example.com/blog/first"]
    assert errors == []
    assert fetched == ["https://example.com/sitemap.xml", "https://example.com/sitemap-pages.xml", "https://example.com/sitemap-posts.xml"]

def test_sitemap_index_from_robots_reads_children_not_root_sitemap(monkeypatch):
    fetched = _serve(monkeypatch, {
        "https://example.com/sitemap_index.xml": _index("https://example.com/page-sitemap.xml"),
        "https://example.com/page-sitemap.xml": _urlset("https://example.com/contact"),
    })
    entries, errors = discover_sitemap("https://example.com/", "Sitemap: https://example.com/sitemap_index.xml", 1, "test")
    assert [entry["url"] for entry in entries] == ["https://example.com/contact"]
    assert errors == []
    assert "https://example.com/sitemap.xml" not in fetched

def test_sitemap_index_cycle_is_read_once(monkeypatch):
    fetched = _serve(monkeypatch, {
        "https://example.com/a.xml": _index("https://example.com/b.xml", "https://example.com/a.xml"),
        "https://example.com/b.xml": _index("https://example.com/a.xml", "https://example.com/pages.xml"),
        "https://example.com/pages.xml": _urlset("https://example.com/"),
    })
    entries, errors = discover_sitemap("https://example.com/", "Sitemap: https://example.com/a.xml", 1, "test")
    assert [entry["url"] for entry in entries] == ["https://example.com/"]
    assert errors == []
    assert sorted(fetched) == ["https://example.com/a.xml", "https://example.com/b.xml", "https://example.com/pages.xml"]

def test_invalid_sitemap_is_reported(monkeypatch):
    class Response:
        content = b"<broken>"
        def raise_for_status(self): pass
    monkeypatch.setattr("crawler.sitemap.requests.get", lambda *args, **kwargs: Response())
    entries, errors = discover_sitemap("https://example.com/", "", 1, "test")
    assert entries == []
    assert errors
