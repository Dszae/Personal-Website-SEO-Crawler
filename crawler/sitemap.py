from urllib.parse import urljoin
from xml.etree import ElementTree
import requests

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

def discover_sitemap(root_url: str, robots_text: str, timeout: float, user_agent: str) -> tuple[list[dict[str, str]], list[str]]:
    candidates = []
    for line in robots_text.splitlines():
        if line.lower().startswith("sitemap:"):
            candidates.append(line.split(":", 1)[1].strip())
    if not candidates:
        candidates.append(urljoin(root_url, "/sitemap.xml"))
    entries: list[dict[str, str]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for sitemap_url in candidates:
        _read_sitemap(sitemap_url, timeout, user_agent, seen, entries, errors)
    return entries, errors

def _read_sitemap(sitemap_url: str, timeout: float, user_agent: str, seen: set[str], entries: list[dict[str, str]], errors: list[str]) -> None:
    # Each sitemap is fetched at most once, so an index that lists itself or
    # two indexes that list each other cannot recurse forever.
    if not sitemap_url or sitemap_url in seen:
        return
    seen.add(sitemap_url)
    try:
        response = requests.get(sitemap_url, headers={"User-Agent": user_agent}, timeout=timeout)
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
    except (requests.RequestException, ElementTree.ParseError) as exc:
        errors.append(f"Sitemap {sitemap_url}: {exc}")
        return
    tag = root.tag.rsplit("}", 1)[-1]
    if tag == "sitemapindex":
        for node in root.findall("sm:sitemap/sm:loc", NS):
            _read_sitemap((node.text or "").strip(), timeout, user_agent, seen, entries, errors)
    elif tag == "urlset":
        for node in root.findall("sm:url", NS):
            loc = node.findtext("sm:loc", default="", namespaces=NS).strip()
            lastmod = node.findtext("sm:lastmod", default="", namespaces=NS).strip()
            if loc:
                entries.append({"url": loc, "lastmod": lastmod})
    else:
        errors.append(f"Unsupported sitemap root in {sitemap_url}")
