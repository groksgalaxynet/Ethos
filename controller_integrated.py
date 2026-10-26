# controller_integrated.py
import sys
import os
import math
import sqlite3
import importlib.util
from PyQt6.QtWidgets import (
   QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QScrollArea
)
from PyQt6.QtGui import QPainter, QColor, QPolygonF, QPen
from PyQt6.QtCore import Qt, QPointF

# Paths for Scars (matched to your Scar Manager)
DOCS = os.path.expanduser('~/Documents')
RUNTIME_DIR = os.path.join(DOCS, 'x0vs_runtime')
LEDGER_DB = os.path.join(RUNTIME_DIR, 'scar_ledger.db')

class RadarChart(QWidget):
   def __init__(self, axes: list[str]):
       super().__init__()
       self.axes = axes
       self.values = {a: 0.0 for a in axes}
       self.setMinimumHeight(400)

   def update_values(self, values: dict[str, float]) -> None:
       for k, v in values.items():
           if k in self.values:
               self.values[k] = max(0.0, min(100.0, float(v)))
       self.update()

   def paintEvent(self, _):
       p = QPainter(self)
       p.setRenderHint(QPainter.RenderHint.Antialiasing)
       p.fillRect(self.rect(), QColor("#0c0f1a"))
       cx, cy = self.width() / 2, self.height() / 2
       r = min(self.width(), self.height()) * 0.35
       n = len(self.axes)

       p.setPen(QPen(QColor("#444"), 1))
       for f in (0.33, 0.66, 1.0):
           rr = r * f
           p.drawEllipse(int(cx - rr), int(cy - rr), int(rr * 2), int(rr * 2))

       points: list[QPointF] = []
       for i, name in enumerate(self.axes):
           ang = math.pi / 2 - i * 2 * math.pi / n
           vx = cx + r * (self.values[name] / 100) * math.cos(ang)
           vy = cy - r * (self.values[name] / 100) * math.sin(ang)
           points.append(QPointF(vx, vy))
           lx = cx + (r + 35) * math.cos(ang)
           ly = cy - (r + 35) * math.sin(ang)
           p.setPen(QColor("white"))
           p.drawText(int(lx - 40), int(ly - 10), 80, 20, Qt.AlignmentFlag.AlignCenter, name)

       poly = QPolygonF(points)
       p.setPen(QPen(QColor("#39ffb0"), 2))
       p.setBrush(QColor(57, 255, 176, 60))
       p.drawPolygon(poly)

class EthosRadarWidget(QWidget):
   def __init__(self) -> None:
       super().__init__()
       self.axes = ["Pride", "Envy", "Greed", "Lust", "Sloth", "Wrath", "Gluttony"]
       self.file_map = {
           "Pride": ("PrideRegulatorGUI.py", "pride_value"),
           "Envy": ("EnvyRegulatorGUI.py", "envy_value"),
           "Greed": ("GreedRegulatorGUI.py", "greed_value"),
           "Lust": ("LustRegulatorGUI.py", "lust_value"),
           "Sloth": ("SlothRegulatorGUI.py", "sloth_value"),
           "Wrath": ("WrathRegulatorGUI.py", "wrath_value"),
           "Gluttony": ("GluttonyRegulatorGUI.py", "glut_value"),
       }
       self.modules = {}
       self.values = {a: 0.0 for a in self.axes}
       self.init_ui()

   def init_ui(self):
       layout = QVBoxLayout(self)
       
       scroll = QScrollArea()
       scroll.setFixedHeight(60)
       scroll.setWidgetResizable(True)
       bar = QWidget()
       bar_l = QHBoxLayout(bar)
       for name in self.axes:
           b = QPushButton(name)
           b.clicked.connect(lambda _, n=name: self.open_module(n))
           bar_l.addWidget(b)
       scroll.setWidget(bar)
       layout.addWidget(scroll)

       self.radar = RadarChart(self.axes)
       layout.addWidget(self.radar)

       btn_layout = QHBoxLayout()
       sync_btn = QPushButton("PULL FROM GUIS")
       sync_btn.clicked.connect(self.sync_regulators)
       
       enforce_btn = QPushButton("LEGACY VISUALIZATION SUMMARY")
       enforce_btn.clicked.connect(self.run_legacy_visualization)
       
       btn_layout.addWidget(sync_btn)
       btn_layout.addWidget(enforce_btn)
       layout.addLayout(btn_layout)

       self.status = QLabel("Legacy visualization: non-authoritative.")
       self.status.setStyleSheet("color:#39ffb0")
       layout.addWidget(self.status)

   def open_module(self, name: str):
       if name in self.modules:
           self.modules[name].show()
           self.modules[name].raise_()
           return
       fname, _ = self.file_map.get(name, ("", ""))
       path = os.path.join(os.path.dirname(__file__), fname)
       if not os.path.exists(path): return

       spec = importlib.util.spec_from_file_location(fname[:-3], path)
       mod = importlib.util.module_from_spec(spec)
       spec.loader.exec_module(mod)
       
       candidate = f"{name}Regulator"
       if hasattr(mod, candidate):
           win = getattr(mod, candidate)()
           win.show()
           self.modules[name] = win

   def sync_regulators(self):
       for name, win in self.modules.items():
           attr = self.file_map[name][1]
           if hasattr(win, attr):
               self.values[name] = float(getattr(win, attr))
       self.radar.update_values(self.values)

   def get_scar_mass(self):
       """Calculates total weight of current scars."""
       if not os.path.exists(LEDGER_DB): return 0
       try:
           with sqlite3.connect(LEDGER_DB) as conn:
               res = conn.execute("SELECT COUNT(*) FROM scars").fetchone()
               return res[0] if res else 0
       except: return 0

   def run_legacy_visualization(self):
       """Render a legacy aggregate only; it has no authorization authority."""
       scar_count = self.get_scar_mass()
       current_ego = sum(self.values.values()) / len(self.axes)
       self.status.setStyleSheet("color:#ff8800")
       self.status.setText(
           f"NON-AUTHORITATIVE LEGACY VISUALIZATION | Scars: {scar_count} | "
           f"Aggregate: {current_ego:.1f} | ProposalGate is the sole production decision boundary."
       )
