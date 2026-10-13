from crawler.link_extractor import parse_html
from crawler.security import validate_public_url


def render_page(url: str, settings: dict) -> tuple[bytes, str]:
    """Render one page in an isolated browser context with request-level checks."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is not installed; install the browser extra and Chromium first") from exc

    allowed = set(settings.get("allowed_domains", []))
    timeout = int(float(settings.get("render_timeout", settings.get("timeout", 15))) * 1000)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(java_script_enabled=True, service_workers="block")
        page = context.new_page()

        def guard(route):
            request_url = route.request.url
            try:
                validate_public_url(request_url, allowed, require_allowed=True)
                route.continue_()
            except ValueError:
                route.abort()

        page.route("**/*", guard)
        page.goto(url, wait_until="networkidle", timeout=timeout)
        html = page.content().encode("utf-8")
        final_url = page.url
        context.close()
        browser.close()
    return html, final_url
