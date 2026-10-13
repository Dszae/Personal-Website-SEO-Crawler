import json

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag

def parse_html(html: bytes, base_url: str, expected_host: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    description = ""
    meta = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "description"})
    if meta: description = (meta.get("content") or "").strip()
    canonical_nodes = soup.find_all("link", rel=lambda value: value and "canonical" in value)
    canonical = (canonical_nodes[0].get("href") or "").strip() if canonical_nodes else ""
    robots_node = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "robots"})
    robots = (robots_node.get("content") or "").strip() if robots_node else ""
    headings = [{"level": int(node.name[1]), "text": node.get_text(" ", strip=True)} for node in soup.find_all([f"h{i}" for i in range(1, 7)])]
    internal, external = [], []
    for node in soup.find_all("a", href=True):
        href = urljoin(base_url, urldefrag(node["href"])[0])
        if not href.startswith(("http://", "https://")): continue
        item = {"url": href, "anchor": node.get_text(" ", strip=True)}
        (internal if href.split("/", 3)[2].lower() == expected_host.lower() else external).append(item)
    images = []
    for node in soup.find_all("img"):
        images.append({"url": urljoin(base_url, node.get("src", "")), "alt": node.get("alt"), "width": node.get("width"), "height": node.get("height")})
    social = {}
    for node in soup.find_all("meta"):
        key = node.get("property") or node.get("name")
        if key and (key.lower().startswith("og:") or key.lower().startswith("twitter:")):
            social[key.lower()] = node.get("content", "").strip()
    jsonld = []
    for node in soup.find_all("script", type="application/ld+json"):
        raw = node.string or node.get_text()
        try:
            jsonld.append({"raw": raw, "valid": True, "data": json.loads(raw)})
        except (TypeError, json.JSONDecodeError) as exc:
            jsonld.append({"raw": raw, "valid": False, "data": None, "error": str(exc)})
    for node in soup(["script", "style", "noscript", "nav", "footer"]): node.decompose()
    text = " ".join(soup.stripped_strings)
    return {"title": title, "description": description, "canonical": canonical, "robots": robots, "headings": headings, "h1": [h["text"] for h in headings if h["level"] == 1], "internal_links": internal, "external_links": external, "images": images, "social": social, "jsonld": jsonld, "text": text}
