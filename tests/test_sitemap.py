from crawler.sitemap import discover_sitemap

def test_invalid_sitemap_is_reported(monkeypatch):
    class Response:
        content = b"<broken>"
        def raise_for_status(self): pass
    monkeypatch.setattr("crawler.sitemap.requests.get", lambda *args, **kwargs: Response())
    entries, errors = discover_sitemap("https://example.com/", "", 1, "test")
    assert entries == []
    assert errors
