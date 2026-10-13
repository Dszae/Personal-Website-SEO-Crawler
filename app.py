import streamlit as st
import pandas as pd
from analyzers.audit import audit
from crawler.engine import CrawlEngine
from database.db import Database
from reports.exports import findings_csv, html_report, json_export, pages_csv
from services.config import load_settings
from services.comparison import compare_scans

st.set_page_config(page_title="Personal Website SEO Crawler", page_icon="🔎", layout="wide")
settings = load_settings()
db = Database(settings["database"])

st.title("Personal Website SEO Crawler")
st.caption("Evidence-based technical SEO auditing for public websites you control.")

with st.sidebar:
    st.header("Navigation")
    section = st.radio("View", ["Overview", "Start Crawl", "Technical SEO", "Page Explorer", "Internal Links", "External Links", "Images", "Duplicate Content", "Personal Brand", "Recommendations", "Scan History", "Settings"], label_visibility="collapsed")
    st.divider()
    st.caption("Crawls respect robots.txt, configured domains, timeouts, size limits, and public-IP restrictions.")

if "result" not in st.session_state:
    scans = db.list_scans()
    if scans:
        st.session_state.result = db.load_scan(scans[0][0]); st.session_state.scan_id = scans[0][0]

def current_result(): return st.session_state.get("result")

def summary_metrics(result):
    pages = result.pages; fetched = [p for p in pages if p.fetched]; errors = [p for p in pages if p.error or (p.status_code and p.status_code >= 400)]
    cols = st.columns(6)
    for col, label, value in zip(cols, ["URLs discovered", "Fetched", "Errors", "Findings", "Broken internal", "Slow responses"], [len(pages), len(fetched), len(errors), len(result.findings), sum(1 for f in result.findings if f.title == "Broken internal link"), sum(1 for p in pages if p.response_ms > 3000)]): col.metric(label, value)

if section == "Start Crawl":
    st.header("Start Crawl")
    target = st.text_input("Portfolio URL", settings["target_url"])
    allowed_text = st.text_input("Allowed domains (comma-separated)", ",".join(settings["allowed_domains"]))
    c1, c2, c3 = st.columns(3)
    max_pages = c1.number_input("Maximum pages", 1, 2000, int(settings["max_pages"]))
    max_depth = c2.number_input("Maximum depth", 0, 20, int(settings["max_depth"]))
    delay = c3.number_input("Request delay (seconds)", 0.0, 10.0, float(settings["request_delay"]), step=0.05)
    check_external = st.checkbox("Check external links", value=bool(settings["check_external_links"]), help="External links are checked only as bounded status checks and never become crawl targets.")
    render_javascript = st.checkbox("Render JavaScript with Playwright", value=bool(settings["render_javascript"]), help="Optional. Install Playwright and Chromium first. Every browser request is restricted to configured public domains.")
    retain_html = st.checkbox("Retain HTML inspection snapshots", value=bool(settings["retain_html"]), help="Snapshots are disabled by default and stored in SQLite when enabled.")
    if st.button("Start crawl", type="primary"):
        if not target.startswith(("https://", "http://")): st.error("Enter an absolute HTTP(S) URL.")
        else:
            run_settings = {**settings, "target_url": target, "allowed_domains": [x.strip().lower() for x in allowed_text.split(",") if x.strip()], "max_pages": max_pages, "max_depth": max_depth, "request_delay": delay, "check_external_links": check_external, "render_javascript": render_javascript, "retain_html": retain_html}
            with st.spinner("Crawling public pages and analyzing evidence..."):
                result = CrawlEngine(run_settings).crawl(); result.findings = audit(result, run_settings); scan_id = db.save_scan(result)
            st.session_state.result = result; st.session_state.scan_id = scan_id; st.success(f"Scan {scan_id} completed with {len(result.pages)} page records and {len(result.findings)} findings.")

result = current_result()
if section != "Start Crawl" and not result:
    st.info("No saved scan is available yet. Start a crawl to populate this view.")
elif section == "Overview" and result:
    st.header("Overview"); summary_metrics(result)
    st.subheader("Fix First")
    st.dataframe(pd.DataFrame([f.to_dict() for f in result.findings[:10]])[["severity", "category", "title", "url", "evidence"]], width="stretch", hide_index=True, alt="Highest-priority SEO findings")
    if result.pagespeed:
        st.subheader("PageSpeed Insights")
        st.json(result.pagespeed)
    st.subheader("Exports")
    a, b, c, d = st.columns(4)
    a.download_button("Pages CSV", pages_csv(result), f"scan-{st.session_state.scan_id}-pages.csv", "text/csv")
    b.download_button("Findings CSV", findings_csv(result), f"scan-{st.session_state.scan_id}-findings.csv", "text/csv")
    c.download_button("JSON", json_export(result), f"scan-{st.session_state.scan_id}.json", "application/json")
    d.download_button("HTML report", html_report(result), f"scan-{st.session_state.scan_id}.html", "text/html")
elif section == "Page Explorer" and result:
    st.header("Page Explorer")
    query = st.text_input("Filter URLs or titles")
    frame = pd.DataFrame([p.to_dict() for p in result.pages]);
    if not frame.empty:
        if query: frame = frame[frame.apply(lambda row: query.lower() in str(row).lower(), axis=1)]
        cols = ["url", "status_code", "title", "meta_description", "canonical", "robots", "incoming_links", "depth", "response_ms", "error"]
        st.dataframe(frame[cols], width="stretch", hide_index=True, alt="Crawled page explorer")
        selected_url = st.selectbox("Inspect page", frame["url"].tolist())
        selected_page = next(page for page in result.pages if page.url == selected_url)
        with st.container(border=True):
            st.subheader("Page inspection")
            st.json({"url": selected_page.url, "status_code": selected_page.status_code, "title": selected_page.title, "canonical": selected_page.canonical, "response_ms": selected_page.response_ms, "word_count": selected_page.word_count, "redirect_chain": selected_page.redirect_chain})
            if selected_page.html_snapshot:
                st.code(selected_page.html_snapshot, language="html", line_numbers=True)
            else:
                st.info("No HTML snapshot retained for this page. Enable snapshot retention on the next crawl.")
elif section in {"Technical SEO", "Personal Brand", "Duplicate Content"} and result:
    st.header(section)
    findings = result.findings
    if section == "Technical SEO": findings = [f for f in findings if f.category in {"Technical SEO", "Indexability", "Performance"}]
    elif section == "Personal Brand": findings = [f for f in findings if f.category == "Personal Brand"]
    elif section == "Duplicate Content": findings = [f for f in findings if "Duplicate" in f.title or "Thin-content" in f.title]
    severity = st.multiselect("Severity", ["Critical", "High", "Medium", "Low", "Informational"], default=[])
    if severity: findings = [f for f in findings if f.severity in severity]
    st.dataframe(pd.DataFrame([f.to_dict() for f in findings]) if findings else pd.DataFrame(columns=["title", "url", "evidence"]), width="stretch", hide_index=True, alt=f"{section} findings")
elif section == "Internal Links" and result:
    st.header("Internal Links")
    rows = [{"source": p.url, "target": link["url"], "anchor": link["anchor"]} for p in result.pages for link in p.internal_links]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, alt="Internal link relationships")
elif section == "External Links" and result:
    st.header("External Links")
    if result.external_links:
        st.dataframe(pd.DataFrame(result.external_links), width="stretch", hide_index=True, alt="Bounded external link checks")
    else:
        st.info("External-link checking was disabled for this scan or no external links were checked.")
elif section == "Images" and result:
    st.header("Images")
    rows = [{"page": p.url, **image} for p in result.pages for image in p.images]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, alt="Images discovered during the crawl")
elif section == "Recommendations" and result:
    st.header("Recommendations")
    for finding in result.findings:
        with st.expander(f"{finding.severity} · {finding.title} · {finding.url}"):
            st.write(f"**Evidence:** {finding.evidence}"); st.write(f"**Why it matters:** {finding.why_it_matters}"); st.write(f"**Recommended fix:** {finding.recommendation}")
            status = st.selectbox("Status", ["Open", "In progress", "Fixed", "Ignored"], index=["Open", "In progress", "Fixed", "Ignored"].index(finding.status), key=finding.stable_id)
            if status != finding.status: db.update_finding_status(st.session_state.scan_id, finding.stable_id, status); st.rerun()
elif section == "Scan History":
    st.header("Scan History"); rows = db.list_scans(); st.dataframe(pd.DataFrame(rows, columns=["id", "target_url", "started_at", "finished_at"]), width="stretch", hide_index=True, alt="Saved SEO scans")
    if rows:
        selected = st.number_input("Load scan ID", min_value=rows[-1][0], max_value=rows[0][0], value=rows[0][0], step=1)
        if st.button("Load selected scan"): st.session_state.result = db.load_scan(int(selected)); st.session_state.scan_id = int(selected); st.rerun()
        previous_options = [row[0] for row in rows if row[0] != st.session_state.get("scan_id")]
        if previous_options:
            previous_id = st.selectbox("Compare current scan with", previous_options)
            if st.button("Compare scans"):
                comparison = compare_scans(db.load_scan(int(previous_id)), result)
                st.subheader("Visual comparison")
                chart = pd.DataFrame({"state": ["New findings", "Resolved findings", "Remaining findings", "New URLs", "Removed URLs"], "count": [len(comparison["new_findings"]), len(comparison["resolved_findings"]), len(comparison["remaining_findings"]), len(comparison["new_urls"]), len(comparison["removed_urls"])]})
                st.bar_chart(chart, x="state", y="count", width="stretch", alt="Scan comparison counts")
                if comparison["page_changes"]:
                    st.dataframe(pd.DataFrame(comparison["page_changes"]), width="stretch", hide_index=True, alt="Page-level scan changes")
elif section == "Settings":
    st.header("Settings"); st.json({k: v for k, v in settings.items() if k not in {"database"}})
    st.info("Edit config/settings.yaml or environment variables for persistent defaults. Dashboard crawl settings can be adjusted from Start Crawl.")
