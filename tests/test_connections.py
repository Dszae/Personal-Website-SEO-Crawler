"""Streamed responses must be closed, or requests cannot return their
connections to the pool and every request opens a new one."""
from urllib.robotparser import RobotFileParser

from crawler.engine import CrawlEngine
from services.external_links import check_external_links
from crawler.models import PageRecord


class _Raw:
    decode_content = False

    def read(self, amount):
        return b"<html><head><title>Home</title></head><body><h1>Home</h1></body></html>"


class _Response:
    def __init__(self, status_code, url, location=None):
        self.status_code = status_code
        self.url = url
        self.headers = {"Content-Type": "text/html"}
        if location:
            self.headers["Location"] = location
        self.is_redirect = location is not None
        self.is_permanent_redirect = False
        self.raw = _Raw()
        self.closed = False

    def close(self):
        self.closed = True


def _allow_all():
    parser = RobotFileParser()
    parser.parse([])
    return parser


def test_the_crawler_closes_redirects_and_pages(monkeypatch):
    monkeypatch.setattr("crawler.engine.load_robots", lambda *args: (_allow_all(), "", ""))
    monkeypatch.setattr("crawler.engine.discover_sitemap", lambda *args: ([], []))
    monkeypatch.setattr("crawler.engine.validate_public_url", lambda *args, **kwargs: None)
    redirect = _Response(301, "https://example.com/", location="https://example.com/home")
    page = _Response(200, "https://example.com/home")
    served = [redirect, page]
    engine = CrawlEngine({"user_agent": "test", "target_url": "https://example.com/", "allowed_domains": ["example.com"], "timeout": 1, "max_pages": 1, "max_depth": 0, "check_sitemap": False})
    monkeypatch.setattr(engine.session, "get", lambda *args, **kwargs: served.pop(0))
    result = engine.crawl()
    assert result.pages[0].title == "Home"
    assert redirect.closed
    assert page.closed


def test_the_external_link_check_closes_its_get_fallback(monkeypatch):
    head = _Response(405, "https://other.org/")
    get = _Response(200, "https://other.org/")

    class _Session:
        def head(self, *args, **kwargs):
            return head

        def get(self, *args, **kwargs):
            return get

    monkeypatch.setattr("services.external_links.requests.Session", _Session)
    monkeypatch.setattr("services.external_links.validate_public_destination", lambda url: None)
    page = PageRecord(url="https://example.com/", external_links=[{"url": "https://other.org/", "anchor": "Other"}])
    [checked] = check_external_links([page], {})
    assert checked["status_code"] == 200
    assert head.closed and get.closed
