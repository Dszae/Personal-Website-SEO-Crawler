from urllib.parse import urljoin
import requests
from crawler.security import validate_public_destination


def check_external_links(pages: list, settings: dict) -> list[dict]:
    limit = int(settings.get("external_link_limit", 25))
    timeout = float(settings.get("external_timeout", settings.get("timeout", 15)))
    max_redirects = int(settings.get("external_max_redirects", 3))
    links = []
    seen = set()
    for page in pages:
        for link in page.external_links:
            url = link.get("url", "")
            if not url.startswith(("http://", "https://")) or url in seen:
                continue
            seen.add(url)
            links.append({"source": page.url, "url": url, "anchor": link.get("anchor", "")})
            if len(links) >= limit:
                break
        if len(links) >= limit:
            break
    session = requests.Session()
    results = []
    for item in links:
        current = item["url"]
        chain = []
        error = ""
        status = None
        try:
            for _ in range(max_redirects + 1):
                validate_public_destination(current)
                response = session.head(current, allow_redirects=False, timeout=timeout)
                if response.status_code in {405, 501}:
                    response = session.get(current, allow_redirects=False, stream=True, timeout=timeout)
                status = response.status_code
                chain.append(current)
                if response.is_redirect or response.is_permanent_redirect:
                    current = urljoin(current, response.headers.get("Location", ""))
                    continue
                break
            else:
                error = "Redirect chain exceeded configured maximum"
        except (requests.RequestException, ValueError, OSError) as exc:
            error = str(exc)
        results.append({**item, "status_code": status, "final_url": current, "redirect_chain": chain, "error": error})
    return results
