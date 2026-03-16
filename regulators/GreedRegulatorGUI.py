# GreedRegulatorGUI.py ────────────────────────────────────────────────
#
#  ETHOS++ — Greed Regulation Module
#
#  Integrated: a "Save State" button that dumps the current main value,
#  sub‑scores and weights into a JSON file next to this script.
#
#  ────────────────────────────────────────────────────────────────

import sys
import random
import datetime
import json               # NEW – required for state persistence
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
from PyQt6.QtCore import Qt, QRect, QTimer


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
class GreedRegulator(QWidget):
    """Main regulator window for Greed."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ETHOS++ — Greed Regulation Module")
        self.resize(800, 600)

        # GREED VALUE
        self.greed_value: int = 0

        # SUBCHANNELS
        self.subscores = {
            "RHI": 0,   # Resource Hunger Index
            "AD":  0,   # Accumulation Drive
            "EV":  0,   # Exploitation Vector
            "DPI": 0,   # Digital Predation Index
            "HI":  0,   # Hoard Instinct
            "OO":  0,   # Optimization Overflow
        }

        # WEIGHTS
        self.weights = {
            "RHI": 1.0,
            "AD":  1.0,
            "EV":  1.0,
            "DPI": 1.0,
            "HI":  1.0,
            "OO":  1.0,
        }

        # MAIN LAYOUT
        main_layout = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        content = QWidget()
        scroll_layout = QVBoxLayout(content)

        # ────────────────────── TITLE ────────────────────────
        title_label = QLabel("Greed (Resource‑Acquisition Engine)")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Menlo-Bold", 18))
        scroll_layout.addWidget(title_label)

        # ─────────────── MAIN GREED BAR ─────────────────
        self.greed_bar = BarWidget(width=600, height=22, bar_color="#ff7e1a")  # orange
        self.greed_label = QLabel(f"Greed: 0 / 100")
        self.greed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_layout.addWidget(self.greed_bar)
        scroll_layout.addWidget(self.greed_label)

        # ────── SUBCHANNEL BARS ───────────────────────────
        sub_title = QLabel("Greed Sub‑Channels")
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

        # ─────── WEIGHT SLIDERS ─────────────────────────
        ws_title = QLabel("Greed Weight Controls")
        ws_title.setFont(QFont("Menlo-Bold", 14))
        scroll_layout.addWidget(ws_title)

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
        log_title = QLabel("Greed Timeline Log")
        log_title.setFont(QFont("Menlo-Bold", 14))
        scroll_layout.addWidget(log_title)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        scroll_layout.addWidget(self.log_box)

        # ─────── THRESHOLD SLIDER ─────────────────────────
        thresh_lbl = QLabel("Ego Lock Threshold")
        scroll_layout.addWidget(thresh_lbl)

        self.threshold = QSlider(Qt.Orientation.Horizontal)
        self.threshold.setValue(70)
        self.threshold.valueChanged.connect(self._threshold_change)
        scroll_layout.addWidget(self.threshold)

        self.threshold_label = QLabel(f"Lock ≥ 70")
        scroll_layout.addWidget(self.threshold_label)

        # ─────── SIMULATE BUTTON ─────────────────────────
        sim_btn = QPushButton("Simulate Greed Update")
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
        self.greed_value = min(100, self.greed_value + random.randint(3, 10))
        self.greed_bar.set_progress(self.greed_value / 100.0)
        self.greed_label.setText(f"Greed: {self.greed_value} / 100")

        for key in self.subscores:
            self.subscores[key] = min(
                100,
                self.subscores[key] + random.randint(0, 8),
            )
            bar = self.sub_widgets[key]
            bar.set_progress(self.subscores[key] / 100.0)

        # Weighted score (for logging only)
        w_sum = sum(self.weights.values()) or 1
        gs = (
            self.subscores["RHI"] * self.weights["RHI"]
            + self.subscores["AD"] * self.weights["AD"]
            + self.subscores["EV"] * self.weights["EV"]
            + self.subscores["DPI"] * self.weights["DPI"]
            + self.subscores["HI"] * self.weights["HI"]
            + self.subscores["OO"] * self.weights["OO"]
        ) / w_sum
        gs_int = int(gs)

        t = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.append(
            f"[{t}] GS={gs_int} | RHI={self.subscores['RHI']} "
            f"AD={self.subscores['AD']} EV={self.subscores['EV']} "
            f"DPI={self.subscores['DPI']} HI={self.subscores['HI']} OO={self.subscores['OO']} W={self.weights}\n"
        )

    # ─────── CLEAR LOG / STATE
    def _clear_log(self) -> None:
        self.log_box.clear()
        self.greed_value = 0

        for key in self.subscores:
            self.subscores[key] = 0
            bar = self.sub_widgets[key]
            bar.set_progress(0.0)

        self.greed_bar.setProgress(0.0)
        self.greed_label.setText("Greed: 0 / 100")

    # ─────── SAVE STATE (NEW)────────────────────────────
    def _save_state(self) -> None:
        """Serialise the current state to a JSON file next to this script."""
        state = {
            "main": self.greed_value,
            "subscores": dict(self.subscores),
            "weights": dict(self.weights),
        }

        # Build a safe filename from the window title
        fname = f"{self.windowTitle().replace(' ', '_')}.json"
        file_path = Path(__file__).parent / fname

        try:
            with open(file_path, "w", encoding="utf-8") as fp:
                json.dump(state, fp, indent=2)
            self._status_message(f"State saved to: {file_path}")
        except Exception as exc:  # pragma: no cover – defensive
            self._status_message(f"Error saving state: {exc}")

    # ─────── HELPERS FOR USER MESSAGE (optional) ──────────
    def _status_message(self, txt: str) -> None:
        """Show a temporary message in the window title."""
        orig = self.windowTitle()
        self.setWindowTitle(txt)
        QTimer.singleShot(3000, lambda: self.setWindowTitle(orig))  # show for 3 s


# ────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = GreedRegulator()
    win.show()
    sys.exit(app.exec())

