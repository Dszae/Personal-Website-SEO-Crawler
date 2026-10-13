import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit
from crawler.models import CrawlResult, Finding

SEVERITY_SCORE = {"Critical": 100, "High": 75, "Medium": 50, "Low": 25, "Informational": 5}

def _finding(kind, title, severity, category, page, evidence, why, recommendation, confidence="High", confirmed=True):
    key = f"{kind}:{page.url}:{evidence}"
    return Finding(hashlib.sha1(key.encode()).hexdigest()[:16], title, severity, category, page.url, evidence, why, recommendation, confidence, confirmed, score=SEVERITY_SCORE[severity])

def audit(result: CrawlResult, settings: dict) -> list[Finding]:
    findings = []
    pages = [p for p in result.pages if p.fetched]
    page_by_url = {p.url: p for p in result.pages}
    for source in pages:
        for link in source.internal_links:
            target = page_by_url.get(link["url"])
            if target and (target.error or (target.status_code and target.status_code >= 400)):
                findings.append(_finding("broken-internal-link", "Broken internal link", "High", "Links", source, f"{link['url']} returned {target.status_code or target.error}.", "Broken internal links interrupt navigation and prevent crawlers from reaching the target page.", "Repair the target URL or remove the link.", "High", True))
    title_groups = defaultdict(list); description_groups = defaultdict(list); h1_groups = defaultdict(list); hash_groups = defaultdict(list)
    for page in pages:
        if not page.title:
            findings.append(_finding("missing-title", "Missing page title", "High", "Technical SEO", page, "No non-empty <title> was found.", "Titles help users and search engines understand page purpose.", "Add a unique, descriptive title for this page."))
        elif len(page.title) < 15 or len(page.title) > 65:
            findings.append(_finding("title-length", "Unusual title length", "Low", "Content", page, f"Title length is {len(page.title)} characters.", "Very short or long titles may communicate page intent less clearly.", "Review the title for clarity and concise page-specific wording.", "Medium", False))
        title_groups[page.title.strip().lower()].append(page)
        if not page.meta_description:
            findings.append(_finding("missing-description", "Missing meta description", "Medium", "Technical SEO", page, "No meta description was found in fetched HTML.", "Search engines may generate their own snippets; a useful description can communicate relevance.", "Add a unique, accurate description for this page."))
        elif len(page.meta_description) < 50 or len(page.meta_description) > 170:
            findings.append(_finding("description-length", "Unusual meta description length", "Low", "Content", page, f"Description length is {len(page.meta_description)} characters.", "Descriptions outside common display ranges may be truncated or underspecified.", "Review the copy for clarity and page-specific relevance.", "Medium", False))
        description_groups[page.meta_description.strip().lower()].append(page)
        if not page.h1:
            findings.append(_finding("missing-h1", "Missing H1 heading", "Medium", "Content", page, "No H1 was found.", "A meaningful primary heading improves document structure and usability.", "Add one descriptive H1 that reflects the page topic."))
        elif len(page.h1) > 1:
            findings.append(_finding("multiple-h1", "Multiple H1 headings", "Low", "Content", page, f"Found {len(page.h1)} H1 elements.", "Multiple H1s are a review recommendation, not automatically a Google penalty.", "Confirm the heading hierarchy is intentional and clear.", "High", True))
        h1_groups["|".join(x.lower() for x in page.h1)].append(page)
        if not page.canonical:
            findings.append(_finding("missing-canonical", "Missing canonical URL", "Low", "Indexability", page, "No canonical link element was found.", "Canonical signals can help consolidate duplicate URL variants.", "Add a self-referencing canonical where canonicalization is needed.", "Medium", False))
        else:
            try:
                canonical = normalize_canonical(page.canonical, page.url)
                if urlsplit(canonical).hostname not in settings.get("allowed_domains", []):
                    findings.append(_finding("external-canonical", "Canonical points outside allowed domain", "High", "Indexability", page, canonical, "An unexpected canonical can consolidate signals away from this site.", "Verify the canonical target and keep it within the intended site domain."))
            except ValueError:
                findings.append(_finding("invalid-canonical", "Invalid canonical URL", "High", "Indexability", page, page.canonical, "Invalid canonical values cannot reliably consolidate URL signals.", "Use an absolute or valid site-relative HTTP(S) canonical URL."))
        for block in page.structured_data:
            if not block.get("valid", True):
                findings.append(_finding("invalid-jsonld", "Invalid JSON-LD", "Medium", "Structured Data", page, block.get("error", "JSON-LD could not be parsed."), "Malformed JSON-LD cannot be interpreted by crawlers or structured-data tools.", "Fix the JSON syntax and validate the block with a dedicated structured-data validator."))
                continue
            data = block.get("data")
            objects = data if isinstance(data, list) else [data]
            for item in objects:
                if not isinstance(item, dict):
                    findings.append(_finding("jsonld-shape", "Unsupported JSON-LD shape", "Low", "Structured Data", page, "A JSON-LD block did not contain an object.", "Structured-data consumers generally expect typed objects.", "Use a typed JSON-LD object or remove the unused block.", "Medium", False))
                    continue
                if not item.get("@context") or not item.get("@type"):
                    findings.append(_finding("jsonld-required-fields", "JSON-LD is missing context or type", "Low", "Structured Data", page, f"@context={bool(item.get('@context'))}, @type={bool(item.get('@type'))}.", "Context and type are needed to interpret JSON-LD vocabulary.", "Add the appropriate @context and @type, then validate the markup."))
                if item.get("@type") == "Person" and not item.get("name"):
                    findings.append(_finding("person-schema-name", "Person JSON-LD is missing a name", "Medium", "Personal Brand", page, "A Person object has no name field.", "A person entity cannot be clearly identified without a name.", "Add the verified person's name if this markup is factually justified."))
        jsonld_blocks = [json.dumps(block.get("data"), sort_keys=True) for block in page.structured_data if block.get("valid", True) and block.get("data") is not None]
        if len(jsonld_blocks) != len(set(jsonld_blocks)):
            findings.append(_finding("duplicate-jsonld", "Duplicate JSON-LD blocks", "Low", "Structured Data", page, f"Found {len(jsonld_blocks) - len(set(jsonld_blocks))} repeated JSON-LD block(s).", "Repeated structured-data blocks can create maintenance and interpretation ambiguity.", "Keep one authoritative block for each entity or intentionally distinct type."))
        if "noindex" in page.robots.lower() or "noindex" in page.x_robots_tag.lower():
            findings.append(_finding("noindex", "Page sends a noindex directive", "Medium", "Indexability", page, f"robots={page.robots!r}, X-Robots-Tag={page.x_robots_tag!r}", "This crawl evidence indicates the page requests exclusion, but does not prove Google index status.", "Confirm this directive is intentional for the page."))
        for image in page.images:
            if image.get("alt") is None:
                findings.append(_finding("image-alt", "Image missing alt attribute", "Medium", "Images", page, image.get("url", ""), "The image has no alt attribute.", "Add concise descriptive alt text, or use alt=\"\" when the image is intentionally decorative."))
        if "og:title" not in page.social or "og:description" not in page.social:
            findings.append(_finding("social-metadata", "Incomplete Open Graph metadata", "Low", "Technical SEO", page, "og:title or og:description is missing.", "Social metadata helps control how shared pages are represented.", "Add page-specific Open Graph title and description."))
        if page.incoming_links == 0 and page.url != result.target_url:
            findings.append(_finding("orphan-candidate", "Orphan page candidate", "Medium", "Links", page, "No incoming internal links were discovered in this crawl.", "Pages without discovered internal links may be harder to reach; incomplete JavaScript rendering can affect this result.", "Add an intentional internal link from a relevant page.", "Medium", False))
        if not page.internal_links:
            findings.append(_finding("no-outgoing-links", "No outgoing internal links", "Low", "Links", page, "No internal links were discovered.", "Internal links help users and crawlers navigate the site.", "Add relevant navigation or contextual links where useful.", "Medium", False))
        if page.response_ms > 3000:
            findings.append(_finding("slow-response", "Slow HTTP response", "Medium", "Performance", page, f"Response time was {page.response_ms} ms.", "Response time is a basic signal, not a full Core Web Vitals or mobile usability measurement.", "Profile server and resource delivery; validate with real-user or Lighthouse measurements.", "High", True))
        if page.word_count < 80 and page.url not in {result.target_url, urljoin(result.target_url, "/contact")}:
            findings.append(_finding("thin-content", "Thin-content candidate", "Low", "Content", page, f"Only {page.word_count} visible words remained after boilerplate removal.", "Short utility pages can be valid; this is a review candidate, not an automatic quality judgment.", "Confirm the page serves a distinct user purpose and add useful detail if needed.", "Medium", False))
        if page.in_sitemap and page.status_code and page.status_code >= 400:
            findings.append(_finding("sitemap-error", "Sitemap URL returns an error", "High", "Indexability", page, f"Sitemap-listed URL returned HTTP {page.status_code}.", "Sitemaps should identify canonical, reachable URLs.", "Remove or repair the URL in the sitemap."))
        if page.in_sitemap and page.sitemap_lastmod:
            try:
                sitemap_date = datetime.fromisoformat(page.sitemap_lastmod.replace("Z", "+00:00"))
                if sitemap_date.tzinfo is None: sitemap_date = sitemap_date.replace(tzinfo=timezone.utc)
                if page.last_modified:
                    header_date = parsedate_to_datetime(page.last_modified)
                    if abs((sitemap_date - header_date).total_seconds()) > 86400:
                        findings.append(_finding("sitemap-lastmod-mismatch", "Sitemap lastmod differs from HTTP Last-Modified", "Low", "Indexability", page, f"sitemap={page.sitemap_lastmod}, HTTP Last-Modified={page.last_modified}", "Conflicting freshness signals reduce confidence in the published modification date.", "Update the sitemap or response header so the dates reflect the actual content change.", "High", True))
            except (TypeError, ValueError, IndexError):
                findings.append(_finding("invalid-lastmod", "Invalid sitemap lastmod", "Low", "Indexability", page, page.sitemap_lastmod, "Malformed lastmod values are not reliable freshness metadata.", "Use an ISO 8601 date or timestamp in the sitemap.", "High", True))
    for label, groups in (("title", title_groups), ("description", description_groups), ("H1", h1_groups), ("content", hash_groups)):
        for value, group in groups.items():
            if value and len(group) > 1:
                for page in group:
                    severity = "Medium" if label in {"title", "description"} else "Low"
                    findings.append(_finding(f"duplicate-{label}", f"Duplicate {label}", severity, "Content", page, f"Shared with {len(group) - 1} other page(s): {value[:120]}", "Repeated page signals can make page differentiation less clear.", f"Make the {label} unique where the pages serve different purposes.", "High", True))
    for page in pages:
        if page.text_hash: hash_groups[page.text_hash].append(page)
    # Exact duplicate text groups are evaluated after hashes are collected.
    for value, group in hash_groups.items():
        if value and len(group) > 1:
            for page in group:
                findings.append(_finding("duplicate-content", "Duplicate page content", "Medium", "Content", page, f"Exact normalized text hash shared by {len(group)} pages.", "Identical content across URLs can make the preferred URL unclear.", "Consolidate, differentiate, or canonicalize the duplicate pages."))
    for link in result.external_links:
        if link.get("error") or (link.get("status_code") and link["status_code"] >= 400):
            findings.append(_finding("broken-external-link", "Broken external link", "Low", "Links", _page_for_url(result, link.get("source", "")), f"{link.get('url')} returned {link.get('status_code') or link.get('error')}.", "Broken outbound links can reduce trust and create a poor user experience.", "Update or remove the external link.", "High", True))
    brand = settings.get("brand_name", "Dipesh Sapkota").lower()
    home = next((p for p in pages if p.url == result.target_url), None)
    if home and brand not in (home.title + " " + home.meta_description + " " + " ".join(home.h1)).lower():
        findings.append(_finding("brand-identity", "Homepage identity is not explicit", "Medium", "Personal Brand", home, f"The configured brand name {settings.get('brand_name')!r} was not found in title, description, or H1.", "Clear identity helps visitors and search systems understand who the site represents.", "Use the verified professional name in descriptive homepage metadata or a meaningful H1.", "High", True))
    about = [p for p in pages if "/about" in p.url]
    if not about:
        findings.append(_finding("about-discoverability", "About page not discovered", "Low", "Personal Brand", result.pages[0] if result.pages else _stub(result.target_url), "No URL containing /about was discovered.", "An about page can provide context for a personal portfolio.", "Add or link an about page if it is part of the intended site structure.", "Medium", False))
    return sorted(findings, key=lambda f: (-f.score, f.category, f.url))

def normalize_canonical(value: str, base: str) -> str:
    candidate = urljoin(base, value)
    parts = urlsplit(candidate)
    if parts.scheme not in {"http", "https"} or not parts.netloc: raise ValueError("canonical is not HTTP(S)")
    return candidate

def _stub(url):
    from crawler.models import PageRecord
    return PageRecord(url=url)

def _page_for_url(result: CrawlResult, url: str):
    return next((page for page in result.pages if page.url == url), _stub(url or result.target_url))
