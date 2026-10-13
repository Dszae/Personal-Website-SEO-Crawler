from crawler.models import CrawlResult

def compare_scans(previous: CrawlResult, current: CrawlResult) -> dict:
    old = {f.stable_id: f for f in previous.findings}; new = {f.stable_id: f for f in current.findings}
    old_urls = {p.url for p in previous.pages}; new_urls = {p.url for p in current.pages}
    return {"new_findings": [f.to_dict() for key, f in new.items() if key not in old], "resolved_findings": [f.to_dict() for key, f in old.items() if key not in new], "remaining_findings": [f.to_dict() for key, f in new.items() if key in old], "new_urls": sorted(new_urls - old_urls), "removed_urls": sorted(old_urls - new_urls)}
