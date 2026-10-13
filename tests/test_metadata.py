from crawler.models import CrawlResult, PageRecord
from analyzers.audit import audit

def test_missing_metadata_and_h1_are_reported():
    page = PageRecord(url="https://example.com/", fetched=True, title="", meta_description="", h1=[], content_type="text/html")
    result = CrawlResult(page.url, "", pages=[page])
    findings = audit(result, {"allowed_domains": ["example.com"], "brand_name": "Example"})
    titles = {finding.title for finding in findings}
    assert "Missing page title" in titles
    assert "Missing meta description" in titles
    assert "Missing H1 heading" in titles

def test_broken_internal_link_is_reported():
    source = PageRecord(url="https://example.com/", fetched=True, title="Home", h1=["Home"], internal_links=[{"url": "https://example.com/missing", "anchor": "Missing"}])
    target = PageRecord(url="https://example.com/missing", status_code=404, error="HTTP 404")
    result = CrawlResult(source.url, "", pages=[source, target])
    findings = audit(result, {"allowed_domains": ["example.com"], "brand_name": "Example"})
    assert any(f.title == "Broken internal link" for f in findings)
