from urllib.parse import urljoin
from xml.etree import ElementTree
import requests

def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]

def _children(node, name: str) -> list:
    # Elements are matched by local name, whatever their namespace: real
    # sitemaps also use https://www.sitemaps.org/..., Google's pre-standard
    # 0.84 namespace, or none, and a namespace-bound lookup finds nothing in
    # those, silently.
    return [child for child in node if _local_name(child.tag) == name]

def _child_text(node, name: str) -> str:
    found = _children(node, name)
    return (found[0].text or "").strip() if found else ""

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
    tag = _local_name(root.tag)
    if tag == "sitemapindex":
        for node in _children(root, "sitemap"):
            _read_sitemap(_child_text(node, "loc"), timeout, user_agent, seen, entries, errors)
    elif tag == "urlset":
        for node in _children(root, "url"):
            loc = _child_text(node, "loc")
            lastmod = _child_text(node, "lastmod")
            if loc:
                entries.append({"url": loc, "lastmod": lastmod})
    else:
        errors.append(f"Unsupported sitemap root in {sitemap_url}")
