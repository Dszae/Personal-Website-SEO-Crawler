# Personal Website SEO Crawler

Evidence-based technical SEO auditing for websites you control.

[![CI](https://github.com/Dszae/Personal-Website-SEO-Crawler/actions/workflows/ci.yml/badge.svg)](https://github.com/Dszae/Personal-Website-SEO-Crawler/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE)

A local Streamlit application that discovers pages from links and sitemaps, respects `robots.txt`, records HTTP evidence, analyzes technical SEO and personal-brand signals, stores scan history in SQLite, and exports reviewable reports.

## Features

- Optional isolated Playwright rendering with request-level destination checks and per-page HTML snapshots.
- Optional bounded external-link status checks and PageSpeed Insights integration.
- JSON-LD syntax/type checks and sitemap `lastmod` versus HTTP `Last-Modified` comparison.
- Visual scan comparison with page-level metadata changes.
- Pytest coverage for URL handling, security, parsing, analysis, persistence, exports, malformed sitemaps, and scan comparison.

## Supported systems

Windows, macOS, and Linux with Python 3.11 or newer. This workspace was verified with Python 3.14.3.


Optional browser rendering:

```powershell
pip install -e ".[browser]"
python -m playwright install chromium
```

Enable **Render JavaScript with Playwright** from **Start Crawl**. The browser is headless, isolated per page, and every request is checked against the configured public domains. If Playwright or Chromium is unavailable, the scan records a clear error instead of silently claiming rendered coverage.
## Windows setup


External checks are capped by `external_link_limit` and `external_timeout`. PageSpeed Insights can be enabled per scan without a key under Google's limited public quota, but an API key via `SEO_CRAWLER_PAGESPEED_API_KEY` is recommended for reliable quota. If the public quota returns HTTP 429, the crawler automatically falls back to isolated local browser timings and labels them clearly; these are not Google Lighthouse or Core Web Vitals scores. Quota and API failures are shown as structured scan results. HTML snapshots are opt-in with `retain_html` and bounded by `max_snapshot_bytes`.
From PowerShell in the project folder:
- External-link checks, PageSpeed, browser rendering, and snapshots are optional and disabled by default in the no-credential workflow.
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m streamlit run app.py
```

PowerShell may require `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` before activating a newly created environment. The application also works with the configured system Python if you do not create a virtual environment.

Run tests:

```powershell
python -m pytest -q
```

## Using the dashboard

1. Open **Start Crawl**.
2. Enter the portfolio URL and the exact allowed domains. The default is `www.dipeshsapkota7.com.np`; project subdomains are intentionally separate and are not crawled unless explicitly added.
3. Keep the first scan conservative, for example 50 pages, depth 3, 0.25 seconds delay, and 15 second timeout.
4. Review **Overview**, then inspect details in **Page Explorer**, **Technical SEO**, **Internal Links**, **Images**, and **Recommendations**.
5. Mark recommendation status as work progresses and download the report from Overview.

The default configuration is based on the live portfolio's observed public `robots.txt` and sitemap. The sitemap currently exposes the home page, About, Skills, Projects, Certificates, Resume, Gallery, Contact, blog, project routes, and separate project subdomains. The application does not assume that every URL remains present; it discovers them at scan time.

## Configuration

Edit `config/settings.yaml` for persistent defaults. `.env.example` documents environment overrides for the user agent, database, and report directory. Copy it to `.env` only when needed. Never commit secrets.

Important settings include `target_url`, `allowed_domains`, `max_pages`, `max_depth`, `request_delay`, `concurrency`, `timeout`, `max_response_bytes`, `max_redirects`, `check_external_links`, `render_javascript`, `respect_robots`, `database`, and `verified_profiles`.

`concurrency` is retained as a safety setting for future parallel fetching; the current engine is deliberately sequential to make request pacing and evidence ordering predictable.

## Interpreting findings

Findings distinguish confirmed observations from heuristic review candidates. A missing meta description is not described as a ranking penalty; it means search engines may generate their own snippet. A missing canonical, missing H1, thin content, duplicate signal, or orphan candidate needs context. A crawl cannot prove Google index status, Core Web Vitals, mobile usability, backlinks, or rich-result eligibility.

The first recommended scan for this portfolio is 50 pages, depth 3, 0.25 seconds delay, 15 second timeout, robots enabled, sitemap enabled, and external-link checking disabled. After reviewing the first result, increase to the default 200-page limit if needed.

## Reports and comparisons

Overview downloads page CSV, findings CSV, JSON, and a self-contained HTML report. SQLite stores page records, settings, robots text, findings, and statuses in `data/seo_crawler.sqlite3` by default. Scan history can reload previous scans. The comparison service matches findings by stable identifiers and reports new, resolved, remaining, added, and removed URLs.

## Security and limitations

Crawled HTML and XML are untrusted. Parsing is bounded and reports HTML-escape values. The crawler does not execute page JavaScript by default, bypass CAPTCHA or authentication, access `file://`/FTP, or crawl third-party domains deeply. Optional browser rendering, external-link checks, and PageSpeed are bounded and disabled by default in the no-credential workflow.

The live portfolio returns compressed server-rendered HTML, which the fetcher decodes before parsing. Without the optional browser mode, JavaScript-only content that is absent from the HTTP response is not analyzed. When browser mode is enabled, request-level destination checks still apply to every page and asset request.

Do not use this tool to crawl sites you do not own or have permission to audit. Keep limits and delays conservative.

## Project structure

```text
app.py
config/settings.yaml
crawler/       secure fetching, URLs, robots, sitemap, parsing, models
analyzers/     evidence-based SEO and personal-brand audit
database/      SQLite schema and repository
reports/       HTML, CSV, and JSON exports
services/      settings and scan comparison
tests/         automated tests
data/          local database and report output
```

## Future extension points

- Deeper Lighthouse/PageSpeed history and trend visualization.
- More schema-type-specific JSON-LD validation.
- Optional visual screenshots for rendered page comparisons.
