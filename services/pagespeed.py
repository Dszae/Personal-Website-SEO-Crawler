import requests


def run_pagespeed(url: str, api_key: str = "", timeout: float = 30, strategy: str = "mobile") -> dict:
    if strategy not in {"mobile", "desktop"}:
        raise ValueError("PageSpeed strategy must be mobile or desktop")
    endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = [("url", url), ("strategy", strategy)] + [("category", category) for category in ("performance", "accessibility", "best-practices", "seo")]
    if api_key: params.append(("key", api_key))
    try:
        response = requests.get(endpoint, params=params, timeout=timeout, headers={"User-Agent": "PersonalWebsiteSEOCrawler/1.0"})
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = ""
        try: detail = response.json().get("error", {}).get("message", "")
        except (ValueError, AttributeError): pass
        return {"status": "error", "http_status": response.status_code, "message": detail or str(exc), "hint": "Configure a PageSpeed API key if the public quota is exhausted." if response.status_code == 429 else "Check the PageSpeed request and API configuration."}
    except requests.RequestException as exc:
        return {"status": "error", "message": f"PageSpeed API request failed: {exc}", "hint": "Check network access and the PageSpeed endpoint."}
    payload = response.json()
    categories = payload.get("lighthouseResult", {}).get("categories", {})
    audits = payload.get("lighthouseResult", {}).get("audits", {})
    return {"status": "ok", "strategy": strategy, "requested_url": url, "api_key_used": bool(api_key), "categories": {key: {"score": value.get("score"), "percent": round(value.get("score", 0) * 100) if value.get("score") is not None else None} for key, value in categories.items()}, "core_web_vitals": {key: audits.get(key, {}).get("displayValue") for key in ["first-contentful-paint", "largest-contentful-paint", "cumulative-layout-shift", "total-blocking-time"] if key in audits}}
