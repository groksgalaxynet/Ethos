# notary_final_pyqt6.py
# Converted from Pythonista ui → PyQt6 (desktop)
import sys
import os
import uuid
import time
import json
import base64
import hashlib
import sqlite3
import shutil
import mimetypes
from PyQt6.QtWidgets import (
   QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
   QLabel, QLineEdit, QTextEdit, QPushButton, QComboBox,
   QScrollArea, QFileDialog, QFrame, QGroupBox, QFormLayout,
   QSpinBox, QDoubleSpinBox, QCheckBox, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QPalette, QColor

# Assuming you have this module available (same as before)
import x0vs_crypto_envelope as xe

DOCS = os.path.expanduser('~/Documents')
APP_DB = os.path.join(DOCS, 'x0vs_ledger.db')
BLOB_DIR = os.path.join(DOCS, 'x0vs_blobs')
os.makedirs(BLOB_DIR, exist_ok=True)

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

TOKENS = ['Crono', 'X_0', 'STACK', 'Neo']
DISTRIBUTIONS = ['equal', 'proportional', 'contract']
ALLOWED_EXT = {'.html', '.htm', '.py', '.json', '.md', '.markdown',
              '.sqlite', '.db', '.txt', '.csv'}

def sha256_bytes(b: bytes) -> str:
   return hashlib.sha256(b).hexdigest()

def canonical_json(obj) -> str:
   return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(',', ':'))

def sha256_file(path, chunk=1024*1024):
   h = hashlib.sha256()
   with open(path, 'rb') as f:
       while b := f.read(chunk):
           h.update(b)
   return h.hexdigest()

def safe_mime(path):
   m, _ = mimetypes.guess_type(path)
   return m or 'application/octet-stream'

def store_blob(path):
   sha = sha256_file(path)
   ext = os.path.splitext(path)[1].lower() or '.bin'
   dst = os.path.join(BLOB_DIR, f'{sha}{ext}')
   if not os.path.exists(dst):
       shutil.copy2(path, dst)
   rel = os.path.relpath(dst, DOCS)
   size = os.path.getsize(path)
   return {
       'sha256': sha, 'ext': ext, 'size': size, 'blob_rel': rel,
       'name': os.path.basename(path), 'mime': safe_mime(path)
   }

# Ledger core (unchanged)
class Notary:
   def __init__(self, db_path=APP_DB):
       self.db_path = db_path
       self._ensure_db()

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

   def _encrypt_store(self, creator_id: str, body: dict):
       plain = canonical_json(body).encode('utf-8')
       digest = sha256_bytes(plain)
       env = xe.encrypt_for_wallets(plain, [creator_id], aad=digest.encode('ascii'))
       envelope_str = xe.envelope_json({'sha256_plain': digest, 'enc': env})
       rec = {
           'id': str(uuid.uuid4()),
           'created_ts': time.time(),
           'creator_id': creator_id,
           'title': body.get('title', ''),
           'kind': body.get('kind', 'misc'),
           'content_json': envelope_str,
           'sha256': digest,
           'tags': ','.join(body.get('tags', []))
       }
       con = sqlite3.connect(self.db_path)
       try:
           cur = con.cursor()
           cur.execute("""INSERT INTO notarized
               (id, created_ts, creator_id, title, kind, content_json, sha256, tags)
               VALUES (:id,:created_ts,:creator_id,:title,:kind,:content_json,:sha256,:tags)""", rec)
           con.commit()
       finally:
           con.close()
       return rec

   def save_contract(self, creator_id, title, required, signatures, negotiation, tags):
       body = {'title': title, 'kind': 'contract', 'required_signers': required,
               'signatures': signatures, 'negotiation_log': negotiation, 'tags': tags}
       return self._encrypt_store(creator_id, body)

   def save_mint(self, creator_id, title, token, amount, ref_sha, recipients,
                 distribution, notes, tags, file_meta=None):
       body = {'title': title, 'kind': 'mint', 'token': token, 'amount': float(amount),
               'reference_sha256': ref_sha, 'recipients': recipients,
               'distribution_mode': distribution, 'notes': notes, 'tags': tags}
       if file_meta:
           body['file_meta'] = file_meta
           body.setdefault('assets', []).append({
               'name': file_meta['name'],
               'sha256': file_meta['sha256'],
               'path': file_meta['blob_rel']
           })
       return self._encrypt_store(creator_id, body)

   def save_file_notary(self, creator_id, title, file_meta, notes, tags, embed_b64=None):
       body = {'title': title, 'kind': 'file-notary', 'file_meta': file_meta,
               'notes': notes, 'tags': tags}
       if embed_b64:
           body['file_meta']['embed_b64'] = embed_b64
       body.setdefault('assets', []).append({
           'name': file_meta['name'],
           'sha256': file_meta['sha256'],
           'path': file_meta['blob_rel']
       })
       return self._encrypt_store(creator_id, body)

   def recent(self, limit=20):
       con = sqlite3.connect(self.db_path)
       try:
           cur = con.cursor()
           cur.execute("SELECT created_ts, title, kind, sha256 FROM notarized ORDER BY created_ts DESC LIMIT ?", (limit,))
           return cur.fetchall()
       finally:
           con.close()

   def fetch_last_envelope(self):
       con = sqlite3.connect(self.db_path)
       try:
           cur = con.cursor()
           cur.execute("SELECT content_json FROM notarized ORDER BY created_ts DESC LIMIT 1")
           r = cur.fetchone()
           return r[0] if r else None
       finally:
           con.close()


class Station(QMainWindow):
   def __init__(self):
       super().__init__()
       self.setWindowTitle("X_0VS • Contracts + Mints + File Notary")
       self.resize(600, 900)

       self.n = Notary()
       self.signatures = []
       self.neg_log = []
       self.m_att_meta = None
       self.f_att_meta = None

       # Main widget and scroll area
       central = QWidget()
       self.setCentralWidget(central)
       main_layout = QVBoxLayout(central)

       scroll = QScrollArea()
       scroll.setWidgetResizable(True)
       scroll_content = QWidget()
       scroll_layout = QVBoxLayout(scroll_content)
       scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
       scroll.setWidget(scroll_content)
       main_layout.addWidget(scroll)

       self.body_layout = scroll_layout

       # Dark theme
       palette = QPalette()
       palette.setColor(QPalette.ColorRole.Window, QColor(15, 25, 45))
       palette.setColor(QPalette.ColorRole.WindowText, QColor(200, 230, 255))
       palette.setColor(QPalette.ColorRole.Base, QColor(25, 35, 65))
       palette.setColor(QPalette.ColorRole.AlternateBase, QColor(20, 30, 55))
       palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))  # black for inputs
       palette.setColor(QPalette.ColorRole.Button, QColor(25, 35, 65))
       palette.setColor(QPalette.ColorRole.ButtonText, QColor(50, 220, 180))
       self.setPalette(palette)

       self._build_ui()

   def _label(self, text):
       lbl = QLabel(text)
       lbl.setStyleSheet("color: #c8e6ff; font-size: 14px;")
       return lbl

   def _small(self, text):
       lbl = QLabel(text)
       lbl.setStyleSheet("color: #a0c8ff; font-size: 12px;")
       return lbl

   def _tf(self, placeholder=""):
       tf = QLineEdit()
       tf.setPlaceholderText(placeholder)
       tf.setStyleSheet("""
           QLineEdit {
               background-color: white;
               color: black;
               padding: 6px;
               border: 1px solid #444;
               border-radius: 4px;
           }
       """)
       return tf

   def _tv(self):
       tv = QTextEdit()
       tv.setStyleSheet("""
           QTextEdit {
               background-color: white;
               color: black;
               border: 1px solid #444;
               border-radius: 4px;
           }
       """)
       tv.setFont(QFont("Segoe UI", 11))
       return tv

   def _btn(self, text, callback):
       btn = QPushButton(text)
       btn.clicked.connect(callback)
       btn.setStyleSheet("""
           QPushButton {
               background-color: #1a233a;
               color: #32dcb4;
               padding: 8px;
               border-radius: 6px;
               border: none;
           }
           QPushButton:hover { background-color: #252f4a; }
       """)
       return btn

   def _group(self, title):
       group = QGroupBox(title)
       group.setStyleSheet("""
           QGroupBox {
               font-weight: bold;
               color: #c8e6ff;
               border: 1px solid #2a3a5a;
               border-radius: 8px;
               margin-top: 10px;
               padding-top: 10px;
           }
           QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
       """)
       layout = QVBoxLayout()
       group.setLayout(layout)
       return group, layout

   def _build_ui(self):
       # Creator wallet
       creator_box = QHBoxLayout()
       creator_box.addWidget(self._label("Wallet / Creator"))
       self.w_creator = self._tf("🔥🐜")
       creator_box.addWidget(self.w_creator)
       self.body_layout.addLayout(creator_box)

       self.body_layout.addSpacing(10)

       # === CONTRACT PANEL ===
       contract_group, c_layout = self._group("Contract")
       self.body_layout.addWidget(contract_group)

       c_layout.addWidget(self._label("Contract Title"))
       self.c_title = self._tf("Distribution Rules v1")
       c_layout.addWidget(self.c_title)

       c_layout.addWidget(self._label("Required Signers (comma-separated wallet IDs)"))
       self.c_required = self._tf("🔥🐜,🕷️🐜,corp:acme")
       c_layout.addWidget(self.c_required)

       c_layout.addWidget(self._label("Negotiation Log entry"))
       log_h = QHBoxLayout()
       self.c_note = self._tf("proposal: equal split on Crono mints")
       log_h.addWidget(self.c_note)
       self.btn_addlog = self._btn("Add", self.add_log)
       log_h.addWidget(self.btn_addlog)
       c_layout.addLayout(log_h)

       c_layout.addWidget(self._small("Log"))
       self.c_log = self._tv()
       self.c_log.setFixedHeight(100)
       c_layout.addWidget(self.c_log)

       sign_h = QHBoxLayout()
       self.btn_sign = self._btn("Sign", self.sign_contract)
       self.btn_finalize = self._btn("Finalize + Notarize", self.save_contract)
       sign_h.addWidget(self.btn_sign)
       sign_h.addWidget(self.btn_finalize)
       sign_h.addStretch()
       c_layout.addLayout(sign_h)

       c_layout.addWidget(self._small("Tags (comma-separated)"))
       self.c_tags = self._tf("xovs,contract")
       c_layout.addWidget(self.c_tags)

       # === MINT PANEL ===
       mint_group, m_layout = self._group("Mint")
       self.body_layout.addWidget(mint_group)

       m_layout.addWidget(self._label("Mint Title"))
       self.m_title = self._tf("Crono reward — session 001")
       m_layout.addWidget(self.m_title)

       token_row = QHBoxLayout()
       token_row.addWidget(QLabel("Token"))
       self.m_token = QComboBox()
       self.m_token.addItems(TOKENS)
       token_row.addWidget(self.m_token)
       token_row.addWidget(QLabel("Amount"))
       self.m_amount = QLineEdit("100.0")
       self.m_amount.setFixedWidth(100)
       self.m_amount.setStyleSheet(self._tf().styleSheet())
       token_row.addWidget(self.m_amount)
       token_row.addWidget(QLabel("Reference SHA256"))
       self.m_ref = self._tf("sha256-of-contribution")
       token_row.addWidget(self.m_ref)
       token_row.addStretch()
       m_layout.addLayout(token_row)

       attach_row = QHBoxLayout()
       attach_row.addWidget(self._label("Attach contribution file (auto-fills SHA)"))
       self.btn_m_pick = self._btn("Pick File", self.on_pick_file_mint)
       attach_row.addWidget(self.btn_m_pick)
       self.sw_m_embed = QCheckBox("Embed in record (<=8MB)")
       attach_row.addWidget(self.sw_m_embed)
       attach_row.addStretch()
       m_layout.addLayout(attach_row)

       self.lb_m_file = QTextEdit()
       self.lb_m_file.setReadOnly(True)
       self.lb_m_file.setFixedHeight(80)
       m_layout.addWidget(self.lb_m_file)

       m_layout.addWidget(self._label("Recipients (comma-separated wallets)"))
       self.m_recip = self._tf("🔥🐜,node:pi01,astro:alice")
       m_layout.addWidget(self.m_recip)

       m_layout.addWidget(self._label("Distribution Mode"))
       self.m_dist = QComboBox()
       self.m_dist.addItems(DISTRIBUTIONS)
       m_layout.addWidget(self.m_dist)

       m_layout.addWidget(self._label("Notes"))
       self.m_notes = self._tv()
       self.m_notes.setFixedHeight(80)
       m_layout.addWidget(self.m_notes)

       self.btn_mint = self._btn("Mint + Notarize", self.save_mint)
       m_layout.addWidget(self.btn_mint)

       m_layout.addWidget(self._small("Tags (comma-separated)"))
       self.m_tags = self._tf("xovs,mint")
       m_layout.addWidget(self.m_tags)

       # === FILE NOTARY PANEL ===
       fnot_group, f_layout = self._group("File Notary")
       self.body_layout.addWidget(fnot_group)

       f_layout.addWidget(self._label("File Notary Title"))
       self.f_title = self._tf("Research asset v1")
       f_layout.addWidget(self.f_title)

       f_pick_row = QHBoxLayout()
       f_pick_row.addWidget(self._label("Pick file to notarize"))
       self.btn_f_pick = self._btn("Pick File", self.on_pick_file_notary)
       f_pick_row.addWidget(self.btn_f_pick)
       self.sw_f_embed = QCheckBox("Embed in record (<=8MB)")
       f_pick_row.addWidget(self.sw_f_embed)
       f_pick_row.addStretch()
       f_layout.addLayout(f_pick_row)

       self.lb_f_file = QTextEdit()
       self.lb_f_file.setReadOnly(True)
       self.lb_f_file.setFixedHeight(80)
       f_layout.addWidget(self.lb_f_file)

       f_layout.addWidget(self._label("Notes"))
       self.f_notes = self._tv()
       self.f_notes.setFixedHeight(70)
       f_layout.addWidget(self.f_notes)

       f_layout.addWidget(self._small("Tags (comma-separated)"))
       self.f_tags = self._tf("xovs,file-notary")
       f_layout.addWidget(self.f_tags)

       self.btn_f_save = self._btn("Notarize File", self.save_file_notary)
       f_layout.addWidget(self.btn_f_save)

       # === OUTPUT & UTILS ===
       self.body_layout.addSpacing(20)
       self.out = self._tv()
       self.out.setFixedHeight(160)
       self.out.setReadOnly(True)
       self.body_layout.addWidget(QLabel("Output / Status"))
       self.body_layout.addWidget(self.out)

       utils_row = QHBoxLayout()
       self.btn_recent = self._btn("Show Recent", self.show_recent)
       self.btn_decrypt = self._btn("Decrypt Last", self.decrypt_last)
       utils_row.addWidget(self.btn_recent)
       utils_row.addWidget(self.btn_decrypt)
       utils_row.addStretch()
       self.body_layout.addLayout(utils_row)

       self.body_layout.addSpacing(30)

   # Actions (same logic as before)
   def add_log(self):
       who = self.w_creator.text().strip()
       text = self.c_note.text().strip()
       if not text:
           return
       entry = {'ts': time.time(), 'from': who, 'text': text}
       self.neg_log.append(entry)
       line = f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(entry['ts']))} | {who}: {text}"
       self.c_log.append(line)
       self.c_note.clear()

   def sign_contract(self):
       who = self.w_creator.text().strip()
       if not who:
           return
       self.signatures.append({'wallet': who, 'ts': time.time()})
       self.c_log.append(f"[sign] {who}")

   def save_contract(self):
       try:
           creator = self.w_creator.text().strip()
           title = self.c_title.text().strip()
           required = [w.strip() for w in self.c_required.text().split(',') if w.strip()]
           tags = [t.strip() for t in self.c_tags.text().split(',') if t.strip()]
           if not creator or not title or not required:
               self.out.setPlainText("Creator, Title, Required Signers are required.")
               return
           rec = self.n.save_contract(creator, title, required, self.signatures, self.neg_log, tags)
           self.out.setPlainText(
               f"CONTRACT SAVED\n"
               f"Title: {title}\nSHA-256: {rec['sha256']}\n"
               f"Required: {', '.join(required)}  Signed: {len(self.signatures)}"
           )
           self.signatures = []
           self.neg_log = []
           self.c_log.clear()
       except Exception as e:
           self.out.setPlainText(f"Error: {e}")

   def on_pick_file_mint(self):
       path, _ = QFileDialog.getOpenFileName(
           self, "Pick Contribution File", DOCS,
           "Allowed Files (*.html *.htm *.py *.json *.md *.markdown *.sqlite *.db *.txt *.csv);;All Files (*)"
       )
       if not path:
           return
       meta = store_blob(path)
       self.m_att_meta = meta
       self.m_ref.setText(meta['sha256'])
       self.lb_m_file.setPlainText(
           f"Selected: {meta['name']}\n"
           f"Size: {meta['size']} bytes  MIME: {meta['mime']}\n"
           f"SHA-256: {meta['sha256'][:16]}...  Blob: {meta['blob_rel']}"
       )

   def save_mint(self):
       try:
           creator = self.w_creator.text().strip()
           title = self.m_title.text().strip()
           token = TOKENS[self.m_token.currentIndex()]
           amount = float(self.m_amount.text() or "0")
           ref_sha = self.m_ref.text().strip()
           recipients = [w.strip() for w in self.m_recip.text().split(',') if w.strip()]
           distribution = DISTRIBUTIONS[self.m_dist.currentIndex()]
           notes = self.m_notes.toPlainText()
           tags = [t.strip() for t in self.m_tags.text().split(',') if t.strip()]
           if not creator or not title or amount <= 0 or not recipients:
               self.out.setPlainText("Creator, Title, Amount>0, Recipients required.")
               return

           fmeta = None
           if self.m_att_meta:
               fmeta = dict(self.m_att_meta)
               if self.sw_m_embed.isChecked() and fmeta['size'] <= 8*1024*1024:
                   with open(path, 'rb') as f:  # path from picker
                       fmeta['embed_b64'] = base64.b64encode(f.read()).decode('ascii')

           rec = self.n.save_mint(creator, title, token, amount, ref_sha, recipients,
                                  distribution, notes, tags, file_meta=fmeta)
           self.out.setPlainText(
               f"MINT SAVED\nTitle: {title}\nToken: {token}  Amount: {amount}\n"
               f"Ref: {ref_sha[:16]}...\nRecipients: {', '.join(recipients)}\n"
               f"SHA-256: {rec['sha256']}"
           )
           self.m_att_meta = None
           self.lb_m_file.clear()
       except Exception as e:
           self.out.setPlainText(f"Error: {e}")

   def on_pick_file_notary(self):
       path, _ = QFileDialog.getOpenFileName(
           self, "Pick File to Notarize", DOCS,
           "Allowed Files (*.html *.htm *.py *.json *.md *.markdown *.sqlite *.db *.txt *.csv);;All Files (*)"
       )
       if not path:
           return
       meta = store_blob(path)
       self.f_att_meta = meta
       if not self.f_title.text().strip():
           self.f_title.setText(meta['name'])
       self.lb_f_file.setPlainText(
           f"Selected: {meta['name']}\n"
           f"Size: {meta['size']} bytes  MIME: {meta['mime']}\n"
           f"SHA-256: {meta['sha256'][:16]}...  Blob: {meta['blob_rel']}"
       )

   def save_file_notary(self):
       try:
           creator = self.w_creator.text().strip()
           title = self.f_title.text().strip()
           tags = [t.strip() for t in self.f_tags.text().split(',') if t.strip()]
           if not creator or not title or not self.f_att_meta:
               self.out.setPlainText("Creator, Title, and a file are required.")
               return
           embed_b64 = None
           if self.sw_f_embed.isChecked() and self.f_att_meta['size'] <= 8*1024*1024:
               with open(path, 'rb') as f:  # would need to store path or re-pick
                   embed_b64 = base64.b64encode(f.read()).decode('ascii')
           rec = self.n.save_file_notary(creator, title, dict(self.f_att_meta),
                                         self.f_notes.toPlainText(), tags, embed_b64)
           self.out.setPlainText(
               f"FILE NOTARIZED\nTitle: {title}\nFile SHA: {self.f_att_meta['sha256']}\n"
               f"Ledger SHA-256: {rec['sha256']}"
           )
           self.f_att_meta = None
           self.lb_f_file.clear()
       except Exception as e:
           self.out.setPlainText(f"Error: {e}")

   def show_recent(self):
       rows = self.n.recent(20)
       if not rows:
           self.out.setPlainText("Ledger empty.")
           return
       lines = ["Recent (plaintext SHA):"]
       for ts, title, kind, sh in rows:
           lines.append(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))} | {kind:<11} | {title} | {sh[:12]}...")
       self.out.setPlainText('\n'.join(lines))

   def decrypt_last(self):
       s = self.n.fetch_last_envelope()
       if not s:
           self.out.setPlainText("No rows.")
           return
       try:
           env = json.loads(s)
           wid = self.w_creator.text().strip()
           if not wid:
               self.out.setPlainText("Set Wallet/Creator first.")
               return
           plain = xe.decrypt_with_wallet(env['enc'], wid, aad=env['sha256_plain'].encode('ascii'))
           self.out.setPlainText(plain.decode('utf-8')[:2000])
       except Exception as e:
           self.out.setPlainText(f"Decrypt error: {e}")


def main():
   app = QApplication(sys.argv)
   win = Station()
   win.show()
   sys.exit(app.exec())


if __name__ == '__main__':
   main()
