import hashlib
import logging
import time
from collections import deque
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import requests

from crawler.link_extractor import parse_html
from crawler.models import CrawlResult, PageRecord
from crawler.robots import load_robots
from crawler.security import validate_public_url
from crawler.sitemap import discover_sitemap
from crawler.url_normalizer import normalize_url

log = logging.getLogger(__name__)

class CrawlEngine:
    def __init__(self, settings: dict):
        self.settings = settings
        self.allowed = set(settings.get("allowed_domains", []))
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings["user_agent"]})

    def _request(self, url: str):
        current = url
        chain = []
        for _ in range(int(self.settings.get("max_redirects", 5)) + 1):
            validate_public_url(current, self.allowed)
            response = self.session.get(current, timeout=float(self.settings["timeout"]), allow_redirects=False, stream=True)
            chain.append(current)
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                if not location: break
                from urllib.parse import urljoin
                current = urljoin(current, location)
                continue
            return response, chain
        raise ValueError("Redirect chain exceeded configured maximum")

    def crawl(self) -> CrawlResult:
        started = datetime.now(timezone.utc).isoformat()
        result = CrawlResult(self.settings["target_url"], started, settings=self.settings.copy())
        root = normalize_url(self.settings["target_url"])
        robots, robots_text, robots_error = load_robots(root, self.settings["user_agent"], self.settings["timeout"])
        result.robots_text = robots_text
        if robots_error: result.errors.append(robots_error)
        sitemap_entries, sitemap_errors = discover_sitemap(root, robots_text, self.settings["timeout"], self.settings["user_agent"]) if self.settings.get("check_sitemap", True) else ([], [])
        result.errors.extend(sitemap_errors)
        result.sitemap_urls = [entry["url"] for entry in sitemap_entries]
        queue = deque([(root, 0)])
        seen: set[str] = set()
        sitemap_by_url = {}
        for entry in sitemap_entries:
            try:
                normalized = normalize_url(entry["url"])
                if urlsplit(normalized).hostname in self.allowed:
                    sitemap_by_url[normalized] = entry.get("lastmod", "")
                    if normalized not in seen: queue.append((normalized, 0))
            except ValueError: result.errors.append(f"Invalid sitemap URL: {entry.get('url', '')}")
        while queue and len(seen) < int(self.settings["max_pages"]):
            url, depth = queue.popleft()
            try: url = normalize_url(url)
            except ValueError: continue
            if url in seen or depth > int(self.settings["max_depth"]): continue
            if self.settings.get("respect_robots", True) and not robots.can_fetch(self.settings["user_agent"], url):
                result.pages.append(PageRecord(url=url, requested_url=url, depth=depth, error="Blocked by robots.txt")); seen.add(url); continue
            seen.add(url)
            page = PageRecord(url=url, requested_url=url, depth=depth, in_sitemap=url in sitemap_by_url, sitemap_lastmod=sitemap_by_url.get(url, ""))
            started_request = time.perf_counter()
            try:
                response, chain = self._request(url)
                page.redirect_chain = chain
                page.final_url = normalize_url(response.url)
                page.status_code = response.status_code
                page.content_type = response.headers.get("Content-Type", "")
                page.response_ms = round((time.perf_counter() - started_request) * 1000, 2)
                page.x_robots_tag = response.headers.get("X-Robots-Tag", "")
                response.raw.decode_content = True
                body = response.raw.read(int(self.settings.get("max_response_bytes", 3000000)) + 1)
                page.response_bytes = len(body)
                if len(body) > int(self.settings.get("max_response_bytes", 3000000)):
                    page.error = "Response exceeded configured size limit"
                elif "html" in page.content_type.lower() and response.status_code < 400:
                    parsed = parse_html(body, page.final_url or url, urlsplit(root).hostname or "")
                    page.title = parsed["title"]; page.meta_description = parsed["description"]; page.canonical = parsed["canonical"]; page.robots = parsed["robots"]
                    page.headings = parsed["headings"]; page.h1 = parsed["h1"]; page.images = parsed["images"]; page.social = parsed["social"]; page.structured_data = parsed["jsonld"]
                    page.text_hash = hashlib.sha256(" ".join(parsed["text"].lower().split()).encode()).hexdigest(); page.word_count = len(parsed["text"].split()); page.fetched = True
                    for link in parsed["internal_links"]:
                        try:
                            child = normalize_url(link["url"])
                            if urlsplit(child).hostname in self.allowed:
                                page.internal_links.append({"url": child, "anchor": link["anchor"]})
                                if depth < int(self.settings["max_depth"]): queue.append((child, depth + 1))
                        except ValueError: pass
                    page.external_links = parsed["external_links"]
                elif response.status_code >= 400:
                    page.error = f"HTTP {response.status_code}"
            except (requests.RequestException, ValueError, OSError) as exc:
                page.error = str(exc)
                result.errors.append(f"{url}: {exc}")
            result.pages.append(page)
            if self.settings.get("request_delay", 0): time.sleep(float(self.settings["request_delay"]))
        incoming = {}
        for page in result.pages:
            for link in page.internal_links: incoming[link["url"]] = incoming.get(link["url"], 0) + 1
        for page in result.pages: page.incoming_links = incoming.get(page.url, 0)
        result.finished_at = datetime.now(timezone.utc).isoformat()
        return result
