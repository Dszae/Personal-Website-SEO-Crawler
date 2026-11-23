from analyzers.audit import audit
from crawler.models import CrawlResult, Finding, PageRecord
from database.db import Database

def test_repeated_issues_on_one_page_do_not_break_saving(tmp_path):
    # A logo without alt text in the header and the footer, and a broken link
    # in both the navigation and the footer: each repeat yields the same
    # stable_id, which the findings table's primary key rejects.
    logo = {"url": "https://example.com/logo.png", "alt": None}
    broken = {"url": "https://example.com/gone", "anchor": "Gone"}
    home = PageRecord(url="https://example.com/", fetched=True, title="Example home page", h1=["Home"], word_count=200, images=[logo, logo], internal_links=[broken, broken])
    gone = PageRecord(url="https://example.com/gone", status_code=404, error="HTTP 404")
    result = CrawlResult("https://example.com/", "start", "finish", {}, [home, gone])
    result.findings = audit(result, {"allowed_domains": ["example.com"], "brand_name": "Example"})
    ids = [finding.stable_id for finding in result.findings]
    assert len(ids) == len(set(ids))
    assert sum(f.title == "Image missing alt attribute" for f in result.findings) == 1
    assert sum(f.title == "Broken internal link" for f in result.findings) == 1
    db = Database(str(tmp_path / "scan.sqlite3"))
    assert len(db.load_scan(db.save_scan(result)).findings) == len(ids)

def test_scan_round_trip(tmp_path):
    db = Database(str(tmp_path / "scan.sqlite3"))
    finding = Finding("id1", "Test", "Low", "Content", "https://example.com/", "evidence", "why", "fix")
    result = CrawlResult("https://example.com/", "start", "finish", {}, [PageRecord(url="https://example.com/")], [finding])
    scan_id = db.save_scan(result)
    loaded = db.load_scan(scan_id)
    assert loaded.pages[0].url == result.pages[0].url
    assert loaded.findings[0].stable_id == "id1"
    db.update_finding_status(scan_id, "id1", "Fixed")
    assert db.load_scan(scan_id).findings[0].status == "Fixed"
