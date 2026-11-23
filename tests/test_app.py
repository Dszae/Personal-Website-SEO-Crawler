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


def _page_explorer(tmp_path, monkeypatch, query):
    pages = [
        PageRecord(url="https://example.com/", fetched=True, title="Home"),
        # A long title: pandas abbreviates long values when a row is printed.
        PageRecord(url="https://example.com/notes", fetched=True, title="Field notes " + "on embedded systems, " * 8 + "and a closing word about oscilloscopes"),
    ]
    at = _app_with_scan(tmp_path, monkeypatch, CrawlResult(pages[0].url, "start", "finish", {}, pages, []))
    at.run()
    at.sidebar.radio[0].set_value("Page Explorer").run()
    at.text_input[0].set_value(query).run()
    return at


def test_page_explorer_filter_searches_whole_values(tmp_path, monkeypatch):
    at = _page_explorer(tmp_path, monkeypatch, "oscilloscopes")
    assert not at.exception
    assert at.selectbox[0].options == ["https://example.com/notes"]


def test_page_explorer_filter_with_no_match_does_not_crash(tmp_path, monkeypatch):
    at = _page_explorer(tmp_path, monkeypatch, "no page has this text")
    assert not at.exception
    assert any("No pages match" in info.value for info in at.info)
