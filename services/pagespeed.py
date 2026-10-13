from urllib.parse import quote
import requests


def run_pagespeed(url: str, api_key: str, timeout: float = 30, strategy: str = "mobile") -> dict:
    if not api_key:
        return {"status": "not_configured", "message": "Set SEO_CRAWLER_PAGESPEED_API_KEY to enable PageSpeed Insights."}
    endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {"url": url, "key": api_key, "strategy": strategy, "category": ["performance", "accessibility", "best-practices", "seo"]}
    response = requests.get(endpoint, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    categories = payload.get("lighthouseResult", {}).get("categories", {})
    audits = payload.get("lighthouseResult", {}).get("audits", {})
    return {"status": "ok", "strategy": strategy, "requested_url": url, "categories": {key: value.get("score") for key, value in categories.items()}, "core_web_vitals": {key: audits.get(key, {}).get("displayValue") for key in ["first-contentful-paint", "largest-contentful-paint", "cumulative-layout-shift", "total-blocking-time"] if key in audits}}
