# GluttonyRegulatorGUI.py ────────────────────────────────────────────────
#
#  ETHOS++ — Gluttony Regulation Module
#
#  Added: "Save State" button that serialises the current
#         main value, sub‑scores and (if present) weights to a JSON file.
#  The file is written next to this script with a name derived from the
#  window title (spaces are replaced by underscores).
#
#  ────────────────────────────────────────────────────────────────

import sys
import random
import datetime
import json          # ← NEW: required for saving state
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QPushButton,
    QTextEdit,
    QScrollArea,
)
from PyQt6.QtGui import QPainter, QColor, QFont, QPaintEvent
from PyQt6.QtCore import Qt, QRect


# ────────────────────────────────────────────────────────
class BarWidget(QWidget):
    """Simple horizontal progress bar."""

    def __init__(self, width: int = 200, height: int = 22, bar_color: str = "#39ff14"):
        super().__init__()
        self.bar_color = QColor(bar_color)
        self.progress: float = 0.0
        self.setFixedSize(width, height)

    def set_progress(self, progress: float) -> None:
        self.progress = progress
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setBrush(self.bar_color)
        fill_width = int(self.width() * min(max(0.0, self.progress), 1.0))
        painter.drawRect(QRect(0, 0, fill_width, self.height()))


# ────────────────────────────────────────────────────────
class GluttonyRegulator(QWidget):
    """Main regulator window for Gluttony."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ETHOS++ — Gluttony Regulation Module")
        self.resize(800, 600)

        # GLUTTONY SCORE
        self.glut_value: int = 0

        # SUBCHANNELS
        self.subscores = {
            "COI": 0,   # Consumption Overload Index
            "RDF": 0,   # Resource Drain Factor
            "EED": 0,   # Excessive Expansion Drive
            "STB": 0,   # Saturation Threshold Breaker
            "RFL": 0,   # Redundancy Flood Level
            "SDEI": 0,  # Self‑Destructive Excess Index
        }

        # WEIGHTS
        self.weights = {
            "COI": 1.0,
            "RDF": 1.0,
            "EED": 1.0,
            "STB": 1.0,
            "RFL": 1.0,
            "SDEI": 1.0,
        }

        # MAIN LAYOUT
        main_layout = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        content = QWidget()
        scroll_layout = QVBoxLayout(content)

        # ────────────────────── TITLE ────────────────────────
        title_label = QLabel("Gluttony (Over‑Consumption Engine)")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Menlo-Bold", 18))
        scroll_layout.addWidget(title_label)

        # ─────────────── MAIN GLUTTONY BAR ─────────────────
        self.glut_bar = BarWidget(width=600, height=22, bar_color="#cc33ff")
        self.glut_label = QLabel(f"Gluttony: 0 / 100")
        self.glut_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_layout.addWidget(self.glut_bar)
        scroll_layout.addWidget(self.glut_label)

        # ────── SUBCHANNEL BARS ───────────────────────────
        sub_title = QLabel("Gluttony Sub‑Channels")
        sub_title.setFont(QFont("Menlo-Bold", 14))
        scroll_layout.addWidget(sub_title)

        self.sub_widgets: dict[str, BarWidget] = {}
        bar_width = 600

        for key in self.subscores:
            lbl = QLabel(key)
            bar = BarWidget(width=bar_width, height=22, bar_color="#39ff14")
            bar.set_progress(0.0)

            sub_layout = QHBoxLayout()
            sub_layout.addWidget(lbl)
            sub_layout.addWidget(bar)
            scroll_layout.addLayout(sub_layout)

            self.sub_widgets[key] = bar

        # ─────── WEIGHT SLIDERS ───────────────────────────
        wt_title = QLabel("Gluttony Weight Controls")
        wt_title.setFont(QFont("Menlo-Bold", 14))
        scroll_layout.addWidget(wt_title)

        self.weight_sliders: dict[str, QSlider] = {}

        for key in self.weights:
            lbl = QLabel(key)
            s = QSlider(Qt.Orientation.Horizontal)
            s.setMinimum(0)
            s.setMaximum(100)
            s.setValue(100)
            s.valueChanged.connect(self._weight_change)

            self.weight_sliders[key] = s

            weight_layout = QHBoxLayout()
            weight_layout.addWidget(lbl)
            weight_layout.addWidget(s)
            scroll_layout.addLayout(weight_layout)

        # ─────── LOG WINDOW ───────────────────────────────
        log_title = QLabel("Gluttony Timeline Log")
        log_title.setFont(QFont("Menlo-Bold", 14))
        scroll_layout.addWidget(log_title)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        scroll_layout.addWidget(self.log_box)

        # ─────── THRESHOLD SLIDER ─────────────────────────
        t_lbl = QLabel("Ego Lock Threshold")
        scroll_layout.addWidget(t_lbl)

        self.threshold = QSlider(Qt.Orientation.Horizontal)
        self.threshold.setValue(70)
        self.threshold.valueChanged.connect(self._threshold_change)
        scroll_layout.addWidget(self.threshold)

        self.threshold_label = QLabel(f"Lock ≥ 70")
        scroll_layout.addWidget(self.threshold_label)

        # ─────── SIMULATE BUTTON ─────────────────────────
        sim_btn = QPushButton("Simulate Gluttony Update")
        sim_btn.clicked.connect(self._simulate_update)
        scroll_layout.addWidget(sim_btn)

        # ─────── CLEAR BUTTON ─────────────────────────────
        clr_btn = QPushButton("Clear Log")
        clr_btn.clicked.connect(self._clear_log)
        scroll_layout.addWidget(clr_btn)

        # ─────── SAVE STATE BUTTON ────────────────────────
        save_btn = QPushButton("Save State")
        save_btn.clicked.connect(self._save_state)
        scroll_layout.addWidget(save_btn)

        # Finalise layout
        content.setLayout(scroll_layout)
        scroll_area.setWidget(content)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    # ────────────────────────────────────────────────────────
    # CALLBACKS (weight, threshold, simulate, clear)
    # ────────────────────────────────────────────────────────

    def _weight_change(self) -> None:
        for key in self.weights:
            self.weights[key] = self.weight_sliders[key].value() / 100.0

    def _threshold_change(self, value: int) -> None:
        self.threshold_label.setText(f"Lock ≥ {value}")

    # ─────── SIMULATION LOGIC ─────────────────────────────
    def _simulate_update(self) -> None:
        """Randomly bump main score and sub‑channels, then log the state."""
        self.glut_value = min(100, self.glut_value + random.randint(4, 12))
        self.glut_bar.set_progress(self.glut_value / 100.0)
        self.glut_label.setText(f"Gluttony: {self.glut_value} / 100")

        for key in self.subscores:
            self.subscores[key] = min(
                100,
                self.subscores[key] + random.randint(0, 10),
            )
            bar = self.sub_widgets[key]
            bar.set_progress(self.subscores[key] / 100.0)

        # Weighted score (unused by the UI but useful for logging)
        wsum = sum(self.weights.values()) or 1
        gs = (
            self.subscores["COI"] * self.weights["COI"]
            + self.subscores["RDF"] * self.weights["RDF"]
            + self.subscores["EED"] * self.weights["EED"]
            + self.subscores["STB"] * self.weights["STB"]
            + self.subscores["RFL"] * self.weights["RFL"]
            + self.subscores["SDEI"] * self.weights["SDEI"]
        ) / wsum

        t = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.append(
            f"[{t}] GS={int(gs)} | COI={self.subscores['COI']} "
            f"RDF={self.subscores['RDF']} EED={self.subscores['EED']} "
            f"STB={self.subscores['STB']} RFL={self.subscores['RFL']} "
            f"SDEI={self.subscores['SDEI']} W={self.weights}\n"
        )

    # ─────── CLEAR LOG / STATE
    def _clear_log(self) -> None:
        self.log_box.clear()
        self.glut_value = 0

        for key in self.subscores:
            self.subscores[key] = 0
            bar = self.sub_widgets[key]
            bar.set_progress(0.0)

        self.glut_bar.set_progress(0.0)
        self.glut_label.setText("Gluttony: 0 / 100")

    # ─────── SAVE STATE (NEW)────────────────────────────
    def _save_state(self) -> None:
        """Serialise the current state to a JSON file next to this script."""
        state = {
            "main": self.glut_value,
            "subscores": dict(self.subscores),
            "weights": dict(self.weights),
        }

        # Build a safe filename from the window title
        fname = f"{self.windowTitle().replace(' ', '_')}.json"
        file_path = Path(__file__).parent / fname

        try:
            with open(file_path, "w", encoding="utf-8") as fp:
                json.dump(state, fp, indent=2)
            self.status_label("State saved to: " + str(file_path))
        except Exception as exc:  # pragma: no cover – defensive
            self.status_label(f"Error saving state: {exc}")

    # ─────── HELPERS FOR USER MESSAGE (optional) ──────────
    def status_label(self, txt: str) -> None:
        """Show a temporary message in the window title."""
        orig = self.windowTitle()
        self.setWindowTitle(txt)
        QTimer.singleShot(3000, lambda: self.setWindowTitle(orig))  # show for 3 s


# ────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = GluttonyRegulator()
    win.show()
    sys.exit(app.exec())

