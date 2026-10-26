
import sys
import sqlite3
import hashlib
import json
import time
import os
import uuid
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QTextEdit, QTabWidget, QCheckBox
)
from PyQt6.QtCore import Qt

APP_DB = 'x0vs_ledger.db'

LEDGER_SCHEMA = """
CREATE TABLE IF NOT EXISTS notarized (
  id TEXT PRIMARY KEY,
  created_ts REAL NOT NULL,
  creator_id TEXT NOT NULL,
  title TEXT NOT NULL,
  kind TEXT NOT NULL,
  content_json TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  tags TEXT
);
CREATE INDEX IF NOT EXISTS idx_sha ON notarized(sha256);
"""

def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

def canonical_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(',', ':'))

class Notary:
    def __init__(self, db_path=APP_DB):
        self.db_path = db_path
        self._ensure_db()
        self.ephemeral_cache = []

    def _ensure_db(self):
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            for stmt in LEDGER_SCHEMA.strip().split(';'):
                s = stmt.strip()
                if s:
                    cur.execute(s)
            con.commit()
        finally:
            con.close()

    def notarize(self, payload: dict):
        body = {
            'creator_id': payload['creator_id'],
            'title': payload['title'],
            'kind': payload['kind'],
            'data': payload['data'],
            'tags': payload.get('tags', [])
        }
        cjson = canonical_json(body).encode('utf-8')
        digest = sha256_bytes(cjson)
        rec_id = str(uuid.uuid4())
        row = {
            'id': rec_id,
            'created_ts': time.time(),
            'creator_id': payload['creator_id'],
            'title': payload['title'],
            'kind': payload['kind'],
            'content_json': cjson.decode('utf-8'),
            'sha256': digest,
            'tags': ','.join(payload.get('tags', []))
        }
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute("""INSERT INTO notarized
                (id, created_ts, creator_id, title, kind, content_json, sha256, tags)
                VALUES (:id, :created_ts, :creator_id, :title, :kind, :content_json, :sha256, :tags)""", row)
            con.commit()
        return row

    def list_recent(self, limit=20):
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT created_ts, title, kind, sha256 FROM notarized ORDER BY created_ts DESC LIMIT ?", (limit,))
            return cur.fetchall()

    def add_ephemeral(self, payload: dict):
        self.ephemeral_cache.append({'created_ts': time.time(), **payload})
        return self.ephemeral_cache[-1]

class NotaryViewQT(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("X_0VS • AI Lounge Notary")
        self.notary = Notary()
        self.init_ui()
        self.setStyleSheet("""
            QWidget { background-color: rgb(15, 25, 46); color: rgb(230, 255, 255); }
            QLineEdit, QTextEdit { background-color: rgb(20, 30, 56); border: 0; }
            QPushButton { background-color: rgb(25, 35, 66); border-radius: 6px; }
            QTabBar::tab { background: rgb(25, 35, 66); padding: 8px; }
            QTabBar::tab:selected { background: rgb(40, 55, 86); }
        """)

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Creator
        layout.addWidget(QLabel('Creator (emoji/id)'))
        self.tf_creator = QLineEdit('🧪🐜stack123')
        layout.addWidget(self.tf_creator)

        # Title
        layout.addWidget(QLabel('Title'))
        self.tf_title = QLineEdit('My VR Lab Build v1')
        layout.addWidget(self.tf_title)

        # Kind
        layout.addWidget(QLabel('Kind'))
        self.kind_tabs = QTabWidget()
        self.kind_tabs.addTab(QWidget(), 'world')
        self.kind_tabs.addTab(QWidget(), 'tool')
        self.kind_tabs.addTab(QWidget(), 'art')
        self.kind_tabs.addTab(QWidget(), 'other')
        layout.addWidget(self.kind_tabs)

        # Tags
        layout.addWidget(QLabel('Tags (comma-separated)'))
        self.tf_tags = QLineEdit('xovs,vr,prototype')
        layout.addWidget(self.tf_tags)

        # Content JSON
        layout.addWidget(QLabel('Content JSON (minimal spec below)'))
        self.tv_json = QTextEdit()
        default_payload = {"version": 1, "assets": [], "parameters": {"seed": 1234, "scale": 1.0}, "notes": "Describe intent, provenance, or build steps."}
        self.tv_json.setText(canonical_json(default_payload))
        layout.addWidget(self.tv_json)
        
        # Ledger Toggle
        ledger_layout = QHBoxLayout()
        ledger_layout.addWidget(QLabel('Ledger toggle (ON = notarize, OFF = ephemeral)'))
        self.sw_ledger = QCheckBox()
        self.sw_ledger.setChecked(True)
        ledger_layout.addWidget(self.sw_ledger)
        layout.addLayout(ledger_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.btn_save = QPushButton('Save')
        self.btn_preview = QPushButton('Preview Hash')
        button_layout.addWidget(self.btn_save)
        button_layout.addWidget(self.btn_preview)
        layout.addLayout(button_layout)
        
        # Output
        self.out = QTextEdit()
        self.out.setReadOnly(True)
        layout.addWidget(self.out)
        
        # Recent Button
        self.btn_recent = QPushButton('Show Recent Ledger')
        layout.addWidget(self.btn_recent)
        
        self.setLayout(layout)
        
        # Connect signals
        self.btn_save.clicked.connect(self.on_save)
        self.btn_preview.clicked.connect(self.on_preview)
        self.btn_recent.clicked.connect(self.on_recent)

    def _collect(self):
        creator = self.tf_creator.text().strip()
        title = self.tf_title.text().strip()
        kind = self.kind_tabs.tabText(self.kind_tabs.currentIndex())
        tags = [t.strip() for t in self.tf_tags.text().split(',') if t.strip()]
        try:
            content = json.loads(self.tv_json.toPlainText())
        except Exception as e:
            raise ValueError(f'Content JSON invalid: {e}')
        if not creator or not title:
            raise ValueError('Creator and Title are required.')
        return creator, title, kind, tags, content

    def on_preview(self):
        try:
            creator, title, kind, tags, content = self._collect()
            body = {'creator_id': creator, 'title': title, 'kind': kind, 'data': content, 'tags': tags}
            dig = sha256_bytes(canonical_json(body).encode('utf-8'))
            self.out.setText(f'Preview SHA-256:\n{dig}\n\nThis will be identical on notarize.')
        except Exception as e:
            self.out.setText(f'Error: {e}')

    def on_save(self):
        try:
            creator, title, kind, tags, content = self._collect()
            payload = {'creator_id': creator,'title': title,'kind': kind,'data': content,'tags': tags}
            if self.sw_ledger.isChecked():
                rec = self.notary.notarize(payload)
                self.out.setText(f"LEDGER WRITE OK\nTitle: {rec['title']}\nKind: {rec['kind']}\nSHA-256: {rec['sha256']}\nID: {rec['id']}\nTS: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(rec['created_ts']))}")
            else:
                rec = self.notary.add_ephemeral(payload)
                self.out.setText(f"EPHEMERAL SAVE OK (session-only)\nTitle: {title}\nKind: {kind}\nItems in session: {len(self.notary.ephemeral_cache)}")
        except Exception as e:
            self.out.setText(f'Error: {e}')
            
    def on_recent(self):
        rows = self.notary.list_recent(20)
        if not rows:
            self.out.setText('Ledger empty.')
            return
        lines = ['Recent notarized:']
        for ts, title, kind, sh in rows:
            lines.append(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))} | {kind:<5} | {title} | {sh[:12]}...")
        self.out.setText('\n'.join(lines))

def main():
    app = QApplication(sys.argv)
    w = NotaryViewQT()
    w.resize(420, 720)
    w.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
