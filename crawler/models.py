from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass
class PageRecord:
    url: str
    requested_url: str = ""
    status_code: int | None = None
    final_url: str = ""
    content_type: str = ""
    title: str = ""
    meta_description: str = ""
    canonical: str = ""
    robots: str = ""
    x_robots_tag: str = ""
    h1: list[str] = field(default_factory=list)
    headings: list[dict[str, Any]] = field(default_factory=list)
    internal_links: list[dict[str, str]] = field(default_factory=list)
    external_links: list[dict[str, str]] = field(default_factory=list)
    images: list[dict[str, Any]] = field(default_factory=list)
    structured_data: list[dict[str, Any]] = field(default_factory=list)
    social: dict[str, str] = field(default_factory=dict)
    text_hash: str = ""
    word_count: int = 0
    depth: int = 0
    incoming_links: int = 0
    response_ms: float = 0
    response_bytes: int = 0
    redirect_chain: list[str] = field(default_factory=list)
    error: str = ""
    fetched: bool = False
    in_sitemap: bool = False
    sitemap_lastmod: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class Finding:
    stable_id: str
    title: str
    severity: str
    category: str
    url: str
    evidence: str
    why_it_matters: str
    recommendation: str
    confidence: str = "High"
    confirmed: bool = True
    status: str = "Open"
    score: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class CrawlResult:
    target_url: str
    started_at: str
    finished_at: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    pages: list[PageRecord] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    sitemap_urls: list[str] = field(default_factory=list)
    robots_text: str = ""
    errors: list[str] = field(default_factory=list)
