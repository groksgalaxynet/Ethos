# controller2.py 
#  ETHOS++ Radar Controller (WORKING)

import sys
import os
import math
import json
import datetime
import importlib.util
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QScrollArea,
)
from PyQt6.QtGui import QPainter, QColor, QPolygonF, QPen
from PyQt6.QtCore import Qt, QPointF


# ------------------------------------------------------------
# RADAR WIDGET ---------------- #
class RadarChart(QWidget):
    def __init__(self, axes: list[str]):
        super().__init__()
        self.axes = axes
        self.values = {a: 0.0 for a in axes}
        self.setMinimumHeight(320)

    def update_values(self, values: dict[str, float]) -> None:
        """Clamp each value to [0,100] and repaint."""
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

        # Draw concentric circles
        p.setPen(QPen(QColor("#444"), 1))
        for f in (0.33, 0.66, 1.0):
            rr = r * f
            p.drawEllipse(int(cx - rr), int(cy - rr), int(rr * 2), int(rr * 2))

        # Draw axes and points
        points: list[QPointF] = []
        for i, name in enumerate(self.axes):
            ang = math.pi / 2 - i * 2 * math.pi / n
            vx = cx + r * (self.values[name] / 100) * math.cos(ang)
            vy = cy - r * (self.values[name] / 100) * math.sin(ang)
            points.append(QPointF(vx, vy))

            lx = cx + (r + 20) * math.cos(ang)
            ly = cy - (r + 20) * math.sin(ang)
            p.setPen(QColor("white"))
            p.drawText(int(lx - 40), int(ly + 5), 80, 20, Qt.AlignmentFlag.AlignCenter, name)

        poly = QPolygonF(points)
        p.setPen(QPen(QColor("#39ffb0"), 2))
        p.setBrush(QColor(57, 255, 176, 60))
        p.drawPolygon(poly)


# ------------------------------------------------------------
# MAIN CONTROLLER ---------------- #
class EthosController(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ETHOS++ Controller")
        self.resize(640, 900)

        # Define the axes that each regulator will report on
        self.axes = [
            "Pride",
            "Envy",
            "Greed",
            "Lust",
            "Sloth",
            "Wrath",
            "Gluttony",
        ]

        # Mapping from axis name → (module‑file, attribute‑name)
        self.file_map = {
            "Pride": ("PrideRegulatorGUI.py", "pride_value"),
            "Envy": ("EnvyRegulatorGUI.py", "envy_value"),
            "Greed": ("GreedRegulatorGUI.py", "greed_value"),
            "Lust": ("LustRegulatorGUI.py", "lust_value"),
            "Sloth": ("SlothRegulatorGUI.py", "sloth_value"),
            "Wrath": ("WrathRegulatorGUI.py", "wrath_value"),
            # NOTE: Gluttony uses the attribute name `glut_value`
            "Gluttony": ("GluttonyRegulatorGUI.py", "glut_value"),
        }

        self.modules: dict[str, QWidget] = {}
        self.values = {a: 0 for a in self.axes}

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        # --- Module buttons (scrollable) -----------------------
        scroll = QScrollArea()
        scroll.setFixedHeight(70)
        scroll.setWidgetResizable(True)

        bar = QWidget()
        bar_l = QHBoxLayout(bar)

        for name in self.axes:
            b = QPushButton(name)
            b.clicked.connect(lambda _, n=name: self.open_module(n))
            bar_l.addWidget(b)

        bar_l.addStretch()
        scroll.setWidget(bar)
        layout.addWidget(scroll)

        # --- Radar ------------------------------------------------
        self.radar = RadarChart(self.axes)
        layout.addWidget(self.radar)

        # --- Sync button -----------------------------------------
        sync = QPushButton("SYNC → RADAR")
        sync.clicked.connect(self.sync)
        layout.addWidget(sync)

        # --- Status label ----------------------------------------
        self.status = QLabel("Ready.")
        self.status.setStyleSheet("color:#aaa")
        layout.addWidget(self.status)

    # ------------------------------------------------------------
    # Open a regulator window
    # ------------------------------------------------------------
    def open_module(self, name: str) -> None:
        """Open (or raise) the requested regulator."""
        if name in self.modules:
            win = self.modules[name]
            win.raise_()
            return

        fname, _ = self.file_map.get(name, ("", ""))
        path = os.path.join(os.path.dirname(__file__), fname)

        # Debug: show which file is being attempted
        print(f"[DEBUG] Loading module for {name} from {path}")

        if not os.path.exists(path):
            self.status.setText(f"Missing: {fname}")
            return

        spec = importlib.util.spec_from_file_location(fname[:-3], path)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)

        # --- Instantiate the regulator window ---------------------
        win: QWidget | None = None

        # Prefer a class whose name matches <Name>Regulator
        candidate_name = f"{name}Regulator"
        if hasattr(mod, candidate_name):
            cls = getattr(mod, candidate_name)
            if isinstance(cls, type) and issubclass(cls, QWidget):
                win = cls()
                print(f"[DEBUG] Instantiated {candidate_name}")

        # Fallback: first real QWidget subclass that isn't a helper bar
        if win is None:
            for obj in mod.__dict__.values():
                if (
                    isinstance(obj, type)
                    and issubclass(obj, QWidget)
                    and obj.__name__ != "BarWidget"
                    and obj.__name__ != "ProgressBar"  # some modules use this name
                ):
                    win = obj()
                    print(f"[DEBUG] Instantiated fallback class {obj.__name__}")
                    break

        if win is None:
            self.status.setText(f"No suitable QWidget subclass in {fname}")
            return

        # Show the window (no explicit flag needed)
        win.show()
        self.modules[name] = win
        self.status.setText(f"Opened {fname}")
        print(f"[DEBUG] Window for {name} shown.")

    # ------------------------------------------------------------
    # Pull values from open modules and update radar
    # ------------------------------------------------------------
    def sync(self) -> None:
        pulled: list[str] = []

        for name, win in self.modules.items():
            attr = self.file_map[name][1]
            if hasattr(win, attr):
                try:
                    self.values[name] = float(getattr(win, attr))
                    pulled.append(name)
                except Exception:  # defensive
                    pass

        self.radar.update_values(self.values)
        self.status.setText(
            f"Synced: {', '.join(pulled)}" if pulled else "No values found yet."
        )


# ------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = EthosController()
    w.show()
    sys.exit(app.exec())
