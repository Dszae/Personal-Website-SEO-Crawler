from crawler.models import CrawlResult, Finding
from reports.exports import findings_csv, html_report, json_export

def test_report_exports():
    result = CrawlResult("https://example.com/", "start", "finish", findings=[Finding("id", "Issue", "Low", "Content", "https://example.com/", "e", "w", "r")])
    assert "Issue" in findings_csv(result)
    assert "<!doctype html>" in html_report(result)
    assert '"target_url": "https://example.com/"' in json_export(result)
