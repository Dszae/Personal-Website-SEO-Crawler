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
    for sitemap_url in dict.fromkeys(candidates):
        try:
            response = requests.get(sitemap_url, headers={"User-Agent": user_agent}, timeout=timeout)
            response.raise_for_status()
            root = ElementTree.fromstring(response.content)
            tag = root.tag.rsplit("}", 1)[-1]
            if tag == "sitemapindex":
                for node in root.findall("sm:sitemap/sm:loc", NS):
                    child, child_errors = discover_sitemap(node.text or "", "", timeout, user_agent)
                    entries.extend(child); errors.extend(child_errors)
            elif tag == "urlset":
                for node in root.findall("sm:url", NS):
                    loc = node.findtext("sm:loc", default="", namespaces=NS).strip()
                    lastmod = node.findtext("sm:lastmod", default="", namespaces=NS).strip()
                    if loc:
                        entries.append({"url": loc, "lastmod": lastmod})
            else:
                errors.append(f"Unsupported sitemap root in {sitemap_url}")
        except (requests.RequestException, ElementTree.ParseError) as exc:
            errors.append(f"Sitemap {sitemap_url}: {exc}")
    return entries, errors
