from crawler.security import validate_public_url


def run_local_performance(url: str, settings: dict) -> dict:
    """Collect browser navigation signals without Google credentials."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is required for the local performance fallback") from exc

    allowed = set(settings.get("allowed_domains", []))
    timeout = int(float(settings.get("render_timeout", settings.get("timeout", 15))) * 1000)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(java_script_enabled=True, service_workers="block")
        page = context.new_page()

        def guard(route):
            try:
                validate_public_url(route.request.url, allowed, require_allowed=True)
                route.continue_()
            except ValueError:
                route.abort()

        page.route("**/*", guard)
        response = page.goto(url, wait_until="load", timeout=timeout)
        metrics = page.evaluate(
            """() => {
                const navigation = performance.getEntriesByType('navigation')[0] || {};
                const resources = performance.getEntriesByType('resource');
                return {
                    dom_content_loaded_ms: navigation.domContentLoadedEventEnd || null,
                    load_event_ms: navigation.loadEventEnd || null,
                    response_start_ms: navigation.responseStart || null,
                    transfer_size_bytes: navigation.transferSize || null,
                    encoded_body_size_bytes: navigation.encodedBodySize || null,
                    resource_count: resources.length,
                    resource_transfer_bytes: resources.reduce((total, item) => total + (item.transferSize || 0), 0),
                };
            }"""
        )
        final_url = page.url
        status_code = response.status if response else None
        context.close()
        browser.close()
    return {"status": "local_fallback", "requested_url": url, "final_url": final_url, "status_code": status_code, "strategy": "browser", "metrics": metrics, "message": "Local browser timing fallback; not a Google Lighthouse or Core Web Vitals score."}
