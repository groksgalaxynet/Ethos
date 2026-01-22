# ETHOS++ Scar Manager — Forgiveness Protocol Edition (PyQt6)
# Ubuntu Desktop Port

import sys, os, time, json, sqlite3, gzip, hashlib, random, csv
from datetime import datetime

from PyQt6.QtWidgets import (
   QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
   QPushButton, QTableWidget, QTableWidgetItem, QTextEdit,
   QMessageBox, QInputDialog, QFileDialog, QLabel
)
from PyQt6.QtCore import Qt


# ---------------- Paths ----------------
DOCS = os.path.expanduser('~/Documents')
RUNTIME = os.path.join(DOCS, 'x0vs_runtime')
SCAR_DIR = os.path.join(RUNTIME, 'scars')
LEDGER_DB = os.path.join(RUNTIME, 'scar_ledger.db')
FORGIVE_DB = os.path.join(RUNTIME, 'forgiveness_log.db')

os.makedirs(SCAR_DIR, exist_ok=True)


# ---------------- Utils ----------------
def now():
   return datetime.utcnow().isoformat() + "Z"

def sha(b):
   return hashlib.sha256(b).hexdigest()

def hbytes(n):
   n = float(n or 0)
   for u in ['B', 'KB', 'MB', 'GB', 'TB']:
       if n < 1024:
           return f"{n:.2f} {u}"
       n /= 1024
   return f"{n:.2f} PB"


# ---------------- DB helpers ----------------
def table_cols(conn, table):
   return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]

def ensure_schema_and_migrate():
   os.makedirs(RUNTIME, exist_ok=True)

   with sqlite3.connect(LEDGER_DB) as c:
       c.execute("""CREATE TABLE IF NOT EXISTS scars(
           id INTEGER PRIMARY KEY,
           ts TEXT,
           severity TEXT,
           reason TEXT,
           file TEXT,
           bytes INTEGER,
           hash TEXT
       )""")

       cols = set(table_cols(c, "scars"))
       for col, typ in [("file", "TEXT"), ("bytes", "INTEGER"), ("hash", "TEXT")]:
           if col not in cols:
               try:
                   c.execute(f"ALTER TABLE scars ADD COLUMN {col} {typ}")
               except Exception:
                   pass

       rows = c.execute("SELECT id, file, bytes, hash FROM scars").fetchall()
       for sid, fname, b, h in rows:
           fpath = os.path.join(SCAR_DIR, fname) if fname else None
           new_b, new_h = b, h

           if (not b) and fpath and os.path.exists(fpath):
               try:
                   new_b = os.path.getsize(fpath)
               except Exception:
                   pass

           if (not h) and fpath and os.path.exists(fpath):
               try:
                   with open(fpath, "rb") as f:
                       new_h = sha(f.read())
               except Exception:
                   pass

           if new_b != b or new_h != h:
               c.execute(
                   "UPDATE scars SET bytes=?, hash=? WHERE id=?",
                   (int(new_b or 0), new_h or "", sid)
               )
       c.commit()

   with sqlite3.connect(FORGIVE_DB) as c:
       c.execute("""CREATE TABLE IF NOT EXISTS forgiveness(
           id INTEGER PRIMARY KEY,
           scar_id INTEGER,
           sig_a TEXT,
           sig_b TEXT,
           ts TEXT
       )""")
       c.commit()

ensure_schema_and_migrate()


# ---------------- Scar creation ----------------
def create_scar(sev, reason):
   payload = {
       "severity": sev,
       "reason": reason,
       "ts": now(),
       "nonce": random.random()
   }

   payload_json = json.dumps(payload, indent=2).encode("utf-8")
   payload_hash = sha(payload_json)

   tmp = os.path.join(SCAR_DIR, "_tmp.db")
   with sqlite3.connect(tmp) as c:
       c.execute("CREATE TABLE IF NOT EXISTS scar(k TEXT, v TEXT)")
       c.execute("DELETE FROM scar")
       for k, v in payload.items():
           c.execute("INSERT INTO scar VALUES (?,?)", (k, str(v)))

   name = f"scar_{int(time.time())}.db.gz"
   out = os.path.join(SCAR_DIR, name)

   with open(tmp, "rb") as f, gzip.open(out, "wb") as g:
       g.write(f.read())

   os.remove(tmp)

   size = os.path.getsize(out)

   with sqlite3.connect(LEDGER_DB) as c:
       c.execute(
           "INSERT INTO scars(ts,severity,reason,file,bytes,hash) VALUES(?,?,?,?,?,?)",
           (now(), sev, reason, name, size, payload_hash)
       )
       c.commit()


# ---------------- Forgiveness ----------------
def forgive_scar(scar_id, sig_a, sig_b):
   with sqlite3.connect(FORGIVE_DB) as c:
       c.execute(
           "INSERT INTO forgiveness(scar_id,sig_a,sig_b,ts) VALUES(?,?,?,?)",
           (scar_id, sig_a, sig_b, now())
       )
       c.commit()

   with sqlite3.connect(LEDGER_DB) as c:
       row = c.execute("SELECT file FROM scars WHERE id=?", (scar_id,)).fetchone()
       if row and row[0]:
           fpath = os.path.join(SCAR_DIR, row[0])
           if os.path.exists(fpath):
               os.remove(fpath)
       c.execute("DELETE FROM scars WHERE id=?", (scar_id,))
       c.commit()


# ---------------- GUI ----------------
class ScarGUI(QMainWindow):
   def __init__(self):
       super().__init__()
       self.setWindowTitle("ETHOS++ Scar Manager")
       self.resize(900, 700)

       self.selected_id = None
       self.rows = []

       root = QWidget()
       self.setCentralWidget(root)
       layout = QVBoxLayout(root)

       # Buttons
       btn_row1 = QHBoxLayout()
       btn_row2 = QHBoxLayout()

       self.btn_minor = QPushButton("New Scar (Minor)")
       self.btn_major = QPushButton("New Scar (Major)")
       self.btn_import = QPushButton("Scar from Packet JSON")
       self.btn_forgive = QPushButton("Forgive / Remove (2 sig)")
       self.btn_export = QPushButton("Export CSV")
       self.btn_exit = QPushButton("Exit")

       btn_row1.addWidget(self.btn_minor)
       btn_row1.addWidget(self.btn_major)

       btn_row2.addWidget(self.btn_import)
       btn_row2.addWidget(self.btn_forgive)
       btn_row2.addWidget(self.btn_export)
       btn_row2.addWidget(self.btn_exit)

       layout.addLayout(btn_row1)
       layout.addLayout(btn_row2)

       # Table
       self.table = QTableWidget(0, 4)
       self.table.setHorizontalHeaderLabels(
           ["ID", "Severity", "Reason", "Bytes"]
       )
       self.table.verticalHeader().setVisible(False)
       self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
       self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

       layout.addWidget(self.table)

       # Status
       self.status = QTextEdit()
       self.status.setReadOnly(True)
       self.status.setFixedHeight(120)
       layout.addWidget(self.status)

       # Signals
       self.btn_minor.clicked.connect(lambda: self.add_scar("minor"))
       self.btn_major.clicked.connect(lambda: self.add_scar("major"))
       self.btn_import.clicked.connect(self.import_json)
       self.btn_forgive.clicked.connect(self.forgive)
       self.btn_export.clicked.connect(self.export_csv)
       self.btn_exit.clicked.connect(self.close)

       self.table.itemSelectionChanged.connect(self.on_select)

       self.reload()

   def reload(self):
       ensure_schema_and_migrate()

       with sqlite3.connect(LEDGER_DB) as c:
           self.rows = c.execute(
               "SELECT id, severity, reason, IFNULL(bytes,0) FROM scars ORDER BY id DESC"
           ).fetchall()

       self.table.setRowCount(len(self.rows))
       for r, row in enumerate(self.rows):
           for c, val in enumerate(row):
               self.table.setItem(r, c, QTableWidgetItem(str(val)))

       total = sum(int(r[3] or 0) for r in self.rows)

       self.status.setText(
           f"Scar Dir: {SCAR_DIR}\n"
           f"Scars: {len(self.rows)}   Total Scar Mass: {hbytes(total)}\n"
           f"Selected: {self.selected_id}\n"
           f"Forgiveness DB: {os.path.basename(FORGIVE_DB)}"
       )

   def on_select(self):
       items = self.table.selectedItems()
       if items:
           self.selected_id = int(items[0].text())

   def add_scar(self, sev):
       reason, ok = QInputDialog.getText(
           self, "Scar Reason", f"Why (severity={sev})?"
       )
       if ok and reason:
           create_scar(sev, reason)
           self.reload()

   def import_json(self):
       text, ok = QInputDialog.getMultiLineText(
           self, "Packet JSON", "Paste JSON packet:"
       )
       if not ok or not text:
           return
       try:
           pkt = json.loads(text)
       except Exception as e:
           QMessageBox.critical(self, "JSON Error", str(e))
           return

       sev = pkt.get("severity", "minor")
       reason = pkt.get("reason", "packet_import")
       create_scar(sev, reason)
       self.reload()

   def forgive(self):
       if not self.selected_id:
           QMessageBox.warning(self, "No Selection", "Select a scar first.")
           return

       sig_a, ok = QInputDialog.getText(self, "Signature A", "Party A signature:")
       if not ok or not sig_a:
           return

       sig_b, ok = QInputDialog.getText(self, "Signature B", "Party B signature:")
       if not ok or not sig_b:
           return

       confirm = QMessageBox.question(
           self,
           "Confirm Forgiveness",
           f"Remove scar #{self.selected_id}?\n\n"
           f"SigA: {sig_a}\nSigB: {sig_b}\n\n"
           f"Forgiveness record remains forever.",
           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
       )

       if confirm == QMessageBox.StandardButton.Yes:
           forgive_scar(self.selected_id, sig_a, sig_b)
           self.selected_id = None
           self.reload()

   def export_csv(self):
       path = os.path.join(RUNTIME, "scar_export.csv")
       with sqlite3.connect(LEDGER_DB) as c, open(path, "w", newline="", encoding="utf-8") as f:
           w = csv.writer(f)
           w.writerow(["id", "ts", "severity", "reason", "file", "bytes", "hash"])
           for r in c.execute(
               "SELECT id, ts, severity, reason, file, IFNULL(bytes,0), IFNULL(hash,'') FROM scars"
           ):
               w.writerow(r)

       QMessageBox.information(self, "Exported", f"Exported to:\n{path}")


# ---------------- Run ----------------
if __name__ == "__main__":
   app = QApplication(sys.argv)
   win = ScarGUI()
   win.show()
   sys.exit(app.exec())
