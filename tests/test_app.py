from streamlit.testing.v1 import AppTest

from crawler.models import CrawlResult, PageRecord
from database.db import Database


def _app_with_scan(tmp_path, monkeypatch, result):
    """Run the dashboard against a temporary database holding one scan."""
    db_path = tmp_path / "scans.sqlite3"
    Database(str(db_path)).save_scan(result)
    monkeypatch.setenv("SEO_CRAWLER_DATABASE", str(db_path))
    return AppTest.from_file("../app.py", default_timeout=60)


def test_overview_renders_a_scan_with_no_findings(tmp_path, monkeypatch):
    # A site with nothing to fix is a valid result, not an error.
    page = PageRecord(url="https://example.com/", fetched=True, title="Home")
    at = _app_with_scan(tmp_path, monkeypatch, CrawlResult(page.url, "start", "finish", {}, [page], []))
    at.run()
    assert not at.exception
    assert at.header[0].value == "Overview"
