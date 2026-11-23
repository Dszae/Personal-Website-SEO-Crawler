import csv
import io

from crawler.models import CrawlResult, Finding, PageRecord
from reports.exports import findings_csv, html_report, json_export, pages_csv

def test_csv_cells_cannot_start_a_spreadsheet_formula():
    # Titles, descriptions and canonical values come from the crawled pages,
    # and a cell starting with = + - @ runs as a formula in Excel or Sheets.
    page = PageRecord(url="https://example.com/", title='=HYPERLINK("https://evil.example","Open")', meta_description="+1+1", canonical="@SUM(A1)", robots="-noindex", error="\t=1", response_ms=-1.5)
    finding = Finding("id", "Invalid canonical URL", "High", "Indexability", page.url, "=cmd|' /C calc'!A0", "w", "r")
    result = CrawlResult(page.url, "start", "finish", pages=[page], findings=[finding])
    row = next(csv.DictReader(io.StringIO(pages_csv(result))))
    assert row["title"] == '\'=HYPERLINK("https://evil.example","Open")'
    assert row["meta_description"] == "'+1+1"
    assert row["canonical"] == "'@SUM(A1)"
    assert row["robots"] == "'-noindex"
    assert row["error"] == "'\t=1"
    assert row["url"] == "https://example.com/"
    assert row["response_ms"] == "-1.5"  # numbers are data, not formulas
    assert next(csv.DictReader(io.StringIO(findings_csv(result))))["evidence"] == "'=cmd|' /C calc'!A0"

def test_report_exports():
    result = CrawlResult("https://example.com/", "start", "finish", findings=[Finding("id", "Issue", "Low", "Content", "https://example.com/", "e", "w", "r")])
    assert "Issue" in findings_csv(result)
    assert "<!doctype html>" in html_report(result)
    assert '"target_url": "https://example.com/"' in json_export(result)
