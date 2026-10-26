# ethos_boundary_live_qt.py
import sys
import os
import sqlite3
from PyQt6.QtWidgets import (
   QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor

# Paths for data sync
DOCS = os.path.expanduser('~/Documents')
RUNTIME_DIR = os.path.join(DOCS, 'x0vs_runtime')
SUBSTRATE_DB = "meaning_substrate.db" # From ai ethics feelings.py

class ActiveEthosMonitorQT(QWidget):
   def __init__(self):
       super().__init__()
       self.init_ui()
       
       # Refresh Timer (1 second intervals)
       self.timer = QTimer()
       self.timer.timeout.connect(self.refresh_metrics)
       self.timer.start(1000)

   def init_ui(self):
       layout = QVBoxLayout(self)
       layout.setContentsMargins(20, 20, 20, 20)

       # Title Section
       header = QLabel("ETHOS++ BOUNDARY LIVE MONITOR")
       header.setStyleSheet("font-size: 18px; font-weight: bold; color: #39ffb0;")
       layout.addWidget(header)

       # --- PHYSIOLOGY GAUGES (The "Body") ---
       phys_group = QVBoxLayout()
       phys_group.addWidget(QLabel("SYSTEM PHYSIOLOGY (STRAIN SIGNALS)"))
       
       self.cpu_bar = self._create_bar("CPU LOAD ANALOG", "#39ffb0")
       self.vram_bar = self._create_bar("VRAM PRESSURE", "#39b0ff")
       self.temp_bar = self._create_bar("THERMAL DRIFT", "#ffb039")
       self.fatigue_bar = self._create_bar("ACCUMULATED FATIGUE", "#ff3939")
       
       phys_group.addLayout(self.cpu_bar['layout'])
       phys_group.addLayout(self.vram_bar['layout'])
       phys_group.addLayout(self.temp_bar['layout'])
       phys_group.addLayout(self.fatigue_bar['layout'])
       
       layout.addLayout(phys_group)

       # --- MEANING SUBSTRATE (The "Mind") ---
       meaning_group = QVBoxLayout()
       meaning_group.addWidget(QLabel("VALUE-WEIGHTED MEANING (SUBSTRATE)"))
       
       self.trust_weight = QLabel("TRUST WEIGHT: 0.00")
       self.trust_weight.setStyleSheet("font-family: monospace; font-size: 14px;")
       
       self.ego_status = QLabel("EGO STABILITY: NOMINAL")
       self.ego_status.setStyleSheet("color: #39ffb0; font-family: monospace;")
       
       meaning_group.addWidget(self.trust_weight)
       meaning_group.addWidget(self.ego_status)
       layout.addLayout(meaning_group)
       
       layout.addStretch()

   def _create_bar(self, label, color):
       l = QHBoxLayout()
       lbl = QLabel(label)
       lbl.setFixedWidth(150)
       bar = QProgressBar()
       bar.setRange(0, 100)
       bar.setStyleSheet(f"""
           QProgressBar {{ border: 1px solid #444; background: #05070a; text-align: center; color: white; }}
           QProgressBar::chunk {{ background-color: {color}; }}
       """)
       l.addWidget(lbl)
       l.addWidget(bar)
       return {'layout': l, 'bar': bar}

   def refresh_metrics(self):
       """Pulls from SQLite meaning_substrate.db and ethos_runtime.db"""
       try:
           # 1. Pull Meaning (Trust)
           if os.path.exists(SUBSTRATE_DB):
               conn = sqlite3.connect(SUBSTRATE_DB)
               cur = conn.cursor()
               cur.execute("SELECT weight FROM state WHERE concept='trust'")
               row = cur.fetchone()
               if row:
                   self.trust_weight.setText(f"TRUST WEIGHT: {row[0]:.4f}")
               conn.close()

           # 2. Simulate Physiology (In a real run, this binds to the Physiology class)
           # For now, we pull from the last event in the DB to see how the AI 'felt'
           if os.path.exists(SUBSTRATE_DB):
               conn = sqlite3.connect(SUBSTRATE_DB)
               cur = conn.cursor()
               cur.execute("SELECT cpu, vram, temp, fatigue FROM events ORDER BY id DESC LIMIT 1")
               p = cur.fetchone()
               if p:
                   self.cpu_bar['bar'].setValue(int(p[0]*100))
                   self.vram_bar['bar'].setValue(int(p[1]*100))
                   self.temp_bar['bar'].setValue(int(p[2]*100))
                   self.fatigue_bar['bar'].setValue(int(p[3]*100))
               conn.close()
       except Exception as e:
           print(f"Monitor Sync Error: {e}")


