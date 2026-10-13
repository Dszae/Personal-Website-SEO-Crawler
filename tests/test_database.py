from crawler.models import CrawlResult, Finding, PageRecord
from database.db import Database

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
