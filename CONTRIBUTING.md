# Contributing

Thanks for helping improve Personal Website SEO Crawler.

## Development setup

Use Python 3.11 or newer, create a virtual environment, and install the dependencies:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the test suite before opening a pull request:

```powershell
python -m pytest
```

## Pull requests

- Keep changes focused and explain the user-facing or safety impact.
- Add or update tests for crawler, analyzer, persistence, and report behavior.
- Do not add credentials, cookies, private URLs, generated databases, or downloaded site content.
- Keep crawl limits conservative and preserve configured domain and private-network protections.
- Document any new external service, dependency, or limitation.

## Scope

This project is intended for websites that the operator owns or is authorized to audit. Contributions must not add CAPTCHA bypasses, authentication bypasses, unrestricted URL fetching, or high-volume crawling behavior.
