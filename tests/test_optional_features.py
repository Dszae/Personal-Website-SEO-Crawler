from crawler.link_extractor import parse_html
from crawler.models import CrawlResult, PageRecord
from analyzers.audit import audit
from database.db import Database
from services.comparison import compare_scans
from services.pagespeed import run_pagespeed


def test_jsonld_validation_and_duplicate_detection():
    parsed = parse_html(b'''<html><head><script type="application/ld+json">{"@context":"https://schema.org","@type":"Person"}</script><script type="application/ld+json">{"@context":"https://schema.org","@type":"Person"}</script><script type="application/ld+json">{bad</script></head><body><h1>Home</h1></body></html>''', "https://example.com/", "example.com")
    page = PageRecord(url="https://example.com/", fetched=True, title="Home", meta_description="A useful description for this page", h1=["Home"], structured_data=parsed["jsonld"])
    findings = audit(CrawlResult(page.url, "", pages=[page]), {"allowed_domains": ["example.com"], "brand_name": "Example"})
    titles = {finding.title for finding in findings}
    assert "Invalid JSON-LD" in titles
    assert "Duplicate JSON-LD blocks" in titles
    assert "Person JSON-LD is missing a name" in titles


def test_optional_scan_telemetry_round_trip(tmp_path):
    db = Database(str(tmp_path / "scan.sqlite3"))
    result = CrawlResult("https://example.com/", "start", pagespeed={"status": "ok"}, external_links=[{"url": "https://outside.example/", "status_code": 200}])
    scan_id = db.save_scan(result)
    loaded = db.load_scan(scan_id)
    assert loaded.pagespeed["status"] == "ok"
    assert loaded.external_links[0]["status_code"] == 200


def test_comparison_reports_page_metadata_changes():
    old_page = PageRecord(url="https://example.com/", title="Old title")
    new_page = PageRecord(url="https://example.com/", title="New title")
    comparison = compare_scans(CrawlResult(old_page.url, "", pages=[old_page]), CrawlResult(new_page.url, "", pages=[new_page]))
    assert comparison["page_changes"][0]["changes"]["title"] == {"before": "Old title", "after": "New title"}


def test_pagespeed_parses_categories_without_api_key(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"lighthouseResult": {"categories": {"performance": {"score": 0.91}}, "audits": {"largest-contentful-paint": {"displayValue": "1.2 s"}}}}
    monkeypatch.setattr("services.pagespeed.requests.get", lambda *args, **kwargs: Response())
    result = run_pagespeed("https://example.com/", "")
    assert result["status"] == "ok"
    assert result["categories"]["performance"]["percent"] == 91
    assert result["core_web_vitals"]["largest-contentful-paint"] == "1.2 s"


def test_pagespeed_quota_error_is_structured(monkeypatch):
    class Response:
        status_code = 429
        def raise_for_status(self):
            import requests
            raise requests.HTTPError("quota")
        def json(self): return {"error": {"message": "Quota exceeded"}}
    monkeypatch.setattr("services.pagespeed.requests.get", lambda *args, **kwargs: Response())
    result = run_pagespeed("https://example.com/")
    assert result["status"] == "error"
    assert result["http_status"] == 429
    assert "API key" in result["hint"]


