from crawler.robots import load_robots


class _Response:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text
        self.ok = status_code < 400


def _serve(monkeypatch, status_code, text):
    monkeypatch.setattr("crawler.robots.requests.get", lambda *args, **kwargs: _Response(status_code, text))


def test_a_robots_file_is_parsed(monkeypatch):
    _serve(monkeypatch, 200, "User-agent: *\nDisallow: /private\n")
    parser, text, error = load_robots("https://example.com/", "test-bot", 1)
    assert not parser.can_fetch("test-bot", "https://example.com/private/page")
    assert parser.can_fetch("test-bot", "https://example.com/blog")
    assert text.startswith("User-agent")
    assert error == ""


def test_an_error_page_is_not_read_as_robots_rules(monkeypatch):
    # A custom 404 page is HTML, not robots.txt. Text on it that happens to look
    # like a rule (here a help page quoting an example file) must not block the
    # crawl, appear as the site's robots.txt, or add sitemap candidates.
    page = "<html><body><h1>Not found</h1><pre>User-agent: *\nDisallow: /\nSitemap: https://example.com/old.xml</pre></body></html>"
    _serve(monkeypatch, 404, page)
    parser, text, error = load_robots("https://example.com/", "test-bot", 1)
    assert parser.can_fetch("test-bot", "https://example.com/any/page")
    assert text == ""
    assert error == "robots.txt returned HTTP 404"
