import csv
import io
import json
from html import escape
from crawler.models import CrawlResult

def pages_csv(result: CrawlResult) -> str:
    fields = ["url", "status_code", "title", "meta_description", "canonical", "robots", "depth", "incoming_links", "response_ms", "word_count", "error"]
    output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=fields); writer.writeheader()
    for page in result.pages: writer.writerow({field: getattr(page, field) for field in fields})
    return output.getvalue()

def findings_csv(result: CrawlResult) -> str:
    fields = ["stable_id", "title", "severity", "category", "url", "evidence", "why_it_matters", "recommendation", "confidence", "confirmed", "status"]
    output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=fields); writer.writeheader()
    for finding in result.findings: writer.writerow({field: getattr(finding, field) for field in fields})
    return output.getvalue()

def json_export(result: CrawlResult) -> str:
    return json.dumps({"target_url": result.target_url, "started_at": result.started_at, "finished_at": result.finished_at, "settings": result.settings, "pages": [p.to_dict() for p in result.pages], "findings": [f.to_dict() for f in result.findings]}, indent=2)

def html_report(result: CrawlResult) -> str:
    rows = "".join(f"<tr><td>{escape(f.severity)}</td><td>{escape(f.category)}</td><td>{escape(f.title)}</td><td>{escape(f.url)}</td><td>{escape(f.evidence)}</td><td>{escape(f.recommendation)}</td></tr>" for f in result.findings)
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>SEO report - {escape(result.target_url)}</title><style>body{{font:15px system-ui;max-width:1200px;margin:40px auto;color:#17202a}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #d9dee5;padding:8px;text-align:left;vertical-align:top}}th{{background:#eef1f4}}</style></head><body><h1>Personal Website SEO Crawler</h1><p>Target: {escape(result.target_url)}<br>Scan: {escape(result.finished_at)}</p><h2>Findings ({len(result.findings)})</h2><table><tr><th>Severity</th><th>Category</th><th>Issue</th><th>URL</th><th>Evidence</th><th>Recommendation</th></tr>{rows}</table></body></html>"""
