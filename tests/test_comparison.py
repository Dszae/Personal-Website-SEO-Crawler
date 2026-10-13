from crawler.models import CrawlResult, Finding
from services.comparison import compare_scans

def test_scan_comparison():
    old = CrawlResult('https://example.com/', '', findings=[Finding('old', 'Old', 'Low', 'Content', 'u', 'e', 'w', 'r')])
    new = CrawlResult('https://example.com/', '', findings=[Finding('new', 'New', 'Low', 'Content', 'u', 'e', 'w', 'r')])
    comparison = compare_scans(old, new)
    assert len(comparison['new_findings']) == 1
    assert len(comparison['resolved_findings']) == 1
