from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin
import requests

def load_robots(root_url: str, user_agent: str, timeout: float) -> tuple[RobotFileParser, str, str]:
    robots_url = urljoin(root_url, "/robots.txt")
    try:
        response = requests.get(robots_url, headers={"User-Agent": user_agent}, timeout=timeout)
        # Only a successful response is a robots.txt. A 4xx body is an error
        # page (usually HTML): read as rules it could block paths, show up as
        # the site's robots.txt, and add bogus "Sitemap:" candidates that
        # suppress the /sitemap.xml fallback. No file means no restrictions.
        text = response.text if response.ok else ""
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(text.splitlines())
        return parser, text, "" if response.ok else f"robots.txt returned HTTP {response.status_code}"
    except requests.RequestException as exc:
        parser = RobotFileParser()
        parser.parse([])
        return parser, "", f"robots.txt unavailable: {exc}"
