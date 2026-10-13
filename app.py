import streamlit as st
import pandas as pd
from analyzers.audit import audit
from crawler.engine import CrawlEngine
from database.db import Database
from reports.exports import findings_csv, html_report, json_export, pages_csv
from services.config import load_settings

st.set_page_config(page_title="Personal Website SEO Crawler", page_icon="🔎", layout="wide")
settings = load_settings()
db = Database(settings["database"])

st.title("Personal Website SEO Crawler")
st.caption("Evidence-based technical SEO auditing for public websites you control.")

with st.sidebar:
    st.header("Navigation")
    section = st.radio("View", ["Overview", "Start Crawl", "Technical SEO", "Page Explorer", "Internal Links", "Images", "Duplicate Content", "Personal Brand", "Recommendations", "Scan History", "Settings"], label_visibility="collapsed")
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
    if st.button("Start crawl", type="primary"):
        if not target.startswith(("https://", "http://")): st.error("Enter an absolute HTTP(S) URL.")
        else:
            run_settings = {**settings, "target_url": target, "allowed_domains": [x.strip().lower() for x in allowed_text.split(",") if x.strip()], "max_pages": max_pages, "max_depth": max_depth, "request_delay": delay, "check_external_links": check_external}
            with st.spinner("Crawling public pages and analyzing evidence..."):
                result = CrawlEngine(run_settings).crawl(); result.findings = audit(result, run_settings); scan_id = db.save_scan(result)
            st.session_state.result = result; st.session_state.scan_id = scan_id; st.success(f"Scan {scan_id} completed with {len(result.pages)} page records and {len(result.findings)} findings.")

result = current_result()
if section != "Start Crawl" and not result:
    st.info("No saved scan is available yet. Start a crawl to populate this view.")
elif section == "Overview" and result:
    st.header("Overview"); summary_metrics(result)
    st.subheader("Fix First")
    st.dataframe(pd.DataFrame([f.to_dict() for f in result.findings[:10]])[["severity", "category", "title", "url", "evidence"]], use_container_width=True, hide_index=True)
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
        st.dataframe(frame[cols], use_container_width=True, hide_index=True)
elif section in {"Technical SEO", "Personal Brand", "Duplicate Content"} and result:
    st.header(section)
    findings = result.findings
    if section == "Technical SEO": findings = [f for f in findings if f.category in {"Technical SEO", "Indexability", "Performance"}]
    elif section == "Personal Brand": findings = [f for f in findings if f.category == "Personal Brand"]
    elif section == "Duplicate Content": findings = [f for f in findings if "Duplicate" in f.title or "Thin-content" in f.title]
    severity = st.multiselect("Severity", ["Critical", "High", "Medium", "Low", "Informational"], default=[])
    if severity: findings = [f for f in findings if f.severity in severity]
    st.dataframe(pd.DataFrame([f.to_dict() for f in findings]) if findings else pd.DataFrame(columns=["title", "url", "evidence"]), use_container_width=True, hide_index=True)
elif section == "Internal Links" and result:
    st.header("Internal Links")
    rows = [{"source": p.url, "target": link["url"], "anchor": link["anchor"]} for p in result.pages for link in p.internal_links]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
elif section == "Images" and result:
    st.header("Images")
    rows = [{"page": p.url, **image} for p in result.pages for image in p.images]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
elif section == "Recommendations" and result:
    st.header("Recommendations")
    for finding in result.findings:
        with st.expander(f"{finding.severity} · {finding.title} · {finding.url}"):
            st.write(f"**Evidence:** {finding.evidence}"); st.write(f"**Why it matters:** {finding.why_it_matters}"); st.write(f"**Recommended fix:** {finding.recommendation}")
            status = st.selectbox("Status", ["Open", "In progress", "Fixed", "Ignored"], index=["Open", "In progress", "Fixed", "Ignored"].index(finding.status), key=finding.stable_id)
            if status != finding.status: db.update_finding_status(st.session_state.scan_id, finding.stable_id, status); st.rerun()
elif section == "Scan History":
    st.header("Scan History"); rows = db.list_scans(); st.dataframe(pd.DataFrame(rows, columns=["id", "target_url", "started_at", "finished_at"]), use_container_width=True, hide_index=True)
    if rows:
        selected = st.number_input("Load scan ID", min_value=rows[-1][0], max_value=rows[0][0], value=rows[0][0], step=1)
        if st.button("Load selected scan"): st.session_state.result = db.load_scan(int(selected)); st.session_state.scan_id = int(selected); st.rerun()
elif section == "Settings":
    st.header("Settings"); st.json({k: v for k, v in settings.items() if k not in {"database"}})
    st.info("Edit config/settings.yaml or environment variables for persistent defaults. Dashboard crawl settings can be adjusted from Start Crawl.")
