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

def test_homepage_is_recognized_when_target_url_has_no_trailing_slash():
    # The crawler stores page URLs normalized ("https://example.com/"), while
    # the target URL keeps the form it was typed in.
    home = PageRecord(url="https://example.com/", fetched=True, title="Home", h1=["Home"], word_count=10, internal_links=[{"url": "https://example.com/about", "anchor": "About"}])
    about = PageRecord(url="https://example.com/about", fetched=True, title="About", h1=["About"], word_count=200, incoming_links=1, internal_links=[{"url": "https://example.com/", "anchor": "Home"}])
    result = CrawlResult("https://Example.com", "", pages=[home, about])
    findings = audit(result, {"allowed_domains": ["example.com"], "brand_name": "Jane Doe"})
    home_findings = {f.title for f in findings if f.url == home.url}
    assert "Orphan page candidate" not in home_findings
    assert "Thin-content candidate" not in home_findings
    # The brand check runs only once the homepage is found.
    assert "Homepage identity is not explicit" in home_findings

import pytest

def _lastmod_findings(sitemap_lastmod, last_modified=""):
    page = PageRecord(url="https://example.com/", fetched=True, title="Example home page", h1=["Example"], word_count=200, in_sitemap=True, sitemap_lastmod=sitemap_lastmod, last_modified=last_modified)
    findings = audit(CrawlResult(page.url, "", pages=[page]), {"allowed_domains": ["example.com"], "brand_name": "Example"})
    return {f.title for f in findings if "lastmod" in f.title.lower()}

@pytest.mark.parametrize("lastmod", ["2026", "2026-01", "2026-01-02", "2026-01-02T10:00+05:45"])
def test_w3c_datetime_lastmod_forms_are_valid(lastmod):
    # sitemaps.org: lastmod is a W3C Datetime, which may stop at the year or month.
    assert _lastmod_findings(lastmod) == set()

def test_an_impossible_lastmod_is_still_invalid():
    assert _lastmod_findings("2026-13") == {"Invalid sitemap lastmod"}

def test_a_month_lastmod_is_compared_at_month_precision():
    assert _lastmod_findings("2026-01", "Thu, 15 Jan 2026 12:00:00 GMT") == set()
    assert _lastmod_findings("2026-01", "Mon, 16 Mar 2026 12:00:00 GMT") == {"Sitemap lastmod differs from HTTP Last-Modified"}

def test_a_bad_last_modified_header_does_not_blame_the_sitemap():
    assert _lastmod_findings("2026-01-02", "not a date") == set()

def test_a_minus_zero_zone_last_modified_header_is_compared():
    # RFC 5322's "-0000" yields a naive datetime; HTTP dates are always UTC.
    assert _lastmod_findings("2026-01-02", "Fri, 02 Jan 2026 08:00:00 -0000") == set()
    assert _lastmod_findings("2026-01-02", "Fri, 20 Feb 2026 08:00:00 -0000") == {"Sitemap lastmod differs from HTTP Last-Modified"}
