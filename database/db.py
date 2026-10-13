import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from crawler.models import CrawlResult, Finding, PageRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (id INTEGER PRIMARY KEY AUTOINCREMENT, target_url TEXT NOT NULL, started_at TEXT, finished_at TEXT, settings_json TEXT, robots_text TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS pages (scan_id INTEGER NOT NULL, url TEXT, data_json TEXT NOT NULL, PRIMARY KEY(scan_id, url), FOREIGN KEY(scan_id) REFERENCES scans(id));
CREATE TABLE IF NOT EXISTS findings (scan_id INTEGER NOT NULL, stable_id TEXT, data_json TEXT NOT NULL, status TEXT DEFAULT 'Open', PRIMARY KEY(scan_id, stable_id), FOREIGN KEY(scan_id) REFERENCES scans(id));
"""

class Database:
    def __init__(self, path: str):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn: conn.executescript(SCHEMA)
    def connect(self): return sqlite3.connect(self.path)
    def save_scan(self, result: CrawlResult) -> int:
        with self.connect() as conn:
            cur = conn.execute("INSERT INTO scans(target_url, started_at, finished_at, settings_json, robots_text) VALUES(?,?,?,?,?)", (result.target_url, result.started_at, result.finished_at, json.dumps(result.settings), result.robots_text))
            scan_id = cur.lastrowid
            conn.executemany("INSERT INTO pages(scan_id,url,data_json) VALUES(?,?,?)", [(scan_id, p.url, json.dumps(p.to_dict())) for p in result.pages])
            conn.executemany("INSERT INTO findings(scan_id,stable_id,data_json,status) VALUES(?,?,?,?)", [(scan_id, f.stable_id, json.dumps(f.to_dict()), f.status) for f in result.findings])
            return int(scan_id)
    def list_scans(self):
        with self.connect() as conn: return conn.execute("SELECT id,target_url,started_at,finished_at FROM scans ORDER BY id DESC").fetchall()
    def load_scan(self, scan_id: int) -> CrawlResult:
        with self.connect() as conn:
            scan = conn.execute("SELECT target_url,started_at,finished_at,settings_json,robots_text FROM scans WHERE id=?", (scan_id,)).fetchone()
            if not scan: raise KeyError(scan_id)
            pages = [PageRecord(**json.loads(row[0])) for row in conn.execute("SELECT data_json FROM pages WHERE scan_id=?", (scan_id,))]
            findings = [Finding(**json.loads(row[0])) for row in conn.execute("SELECT data_json FROM findings WHERE scan_id=?", (scan_id,))]
        return CrawlResult(scan[0], scan[1], scan[2], json.loads(scan[3]), pages, findings, robots_text=scan[4])
    def update_finding_status(self, scan_id: int, stable_id: str, status: str):
        if status not in {"Open", "In progress", "Fixed", "Ignored"}: raise ValueError("Invalid finding status")
        with self.connect() as conn:
            row = conn.execute("SELECT data_json FROM findings WHERE scan_id=? AND stable_id=?", (scan_id, stable_id)).fetchone()
            if not row: raise KeyError(stable_id)
            data = json.loads(row[0]); data["status"] = status
            conn.execute("UPDATE findings SET data_json=?, status=? WHERE scan_id=? AND stable_id=?", (json.dumps(data), status, scan_id, stable_id))
