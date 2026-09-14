# PrideRegulatorGUI.py ────────────────────────────────────────────────
#
#  ETHOS++ — Pride Regulation Module
#
#  Integrated: a "Save State" button that dumps the current main value and
#  sub‑scores into a JSON file next to this script.
#
#  ────────────────────────────────────────────────────────────────

import sys
import random
import datetime
import json                    # NEW – required for state persistence
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
from regulator_gui_adapter import RegulatorGuiAdapter, RegulatorGuiPresentation


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
class PrideRegulator(QWidget):
    """Main regulator window for Pride."""

    def __init__(self, presentation: RegulatorGuiPresentation | None = None) -> None:
        super().__init__()
        self.setWindowTitle("ETHOS++ — Pride Regulation Module")
        self.resize(800, 600)

        # DATA
        self.pride_value: int = 0
        self.subscores = {"SSN": 0, "OC": 0, "CR": 0, "SI": 0, "BE": 0, "NR": 0}

        # MAIN LAYOUT
        main_layout = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        content = QWidget()
        scroll_layout = QVBoxLayout(content)

        # ────────────────────── TITLE ────────────────────────
        title_label = QLabel("Pride Coefficient Monitor")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Menlo-Bold", 18))
        scroll_layout.addWidget(title_label)

        # ─────────────── MAIN PRIDE BAR ─────────────────
        self.pride_bar = BarWidget(width=600, height=22, bar_color="#f74343")  # red for pride
        self.pride_label = QLabel(f"Pride: 0 / 100")
        self.pride_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_layout.addWidget(self.pride_bar)
        scroll_layout.addWidget(self.pride_label)

        # ────── SUB-METRIC BARS ───────────────────────────
        sub_title = QLabel("Current Analyzer Channel + Legacy Channels")
        sub_title.setFont(QFont("Menlo-Bold", 14))
        scroll_layout.addWidget(sub_title)

        self.sub_widgets: dict[str, BarWidget] = {}
        bar_width = 600

        for key in self.subscores:
            lbl = QLabel(key if key == "SSN" else f"{key} (legacy unavailable)")
            bar = BarWidget(width=bar_width, height=22, bar_color="#39ff14")
            bar.set_progress(0.0)

            sub_layout = QHBoxLayout()
            sub_layout.addWidget(lbl)
            sub_layout.addWidget(bar)
            scroll_layout.addLayout(sub_layout)

            self.sub_widgets[key] = bar

        # ─────── LOG BOX ───────────────────────────────
        log_title = QLabel("Pride Timeline Log")
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
        self.threshold.valueChanged.connect(self._threshold_label_update)
        scroll_layout.addWidget(self.threshold)

        self.threshold_label = QLabel(f"Lock ≥ 70")
        scroll_layout.addWidget(self.threshold_label)

        # ─────── SIMULATE BUTTON ─────────────────────────
        self.btn_sim = QPushButton("Simulate Pride Update — disabled")
        self.btn_sim.clicked.connect(self._simulate_update)
        scroll_layout.addWidget(self.btn_sim)

        # ─────── CLEAR BUTTON ─────────────────────────────
        self.btn_clear = QPushButton("Clear Log — disabled")
        self.btn_clear.clicked.connect(self._clear_log)
        scroll_layout.addWidget(self.btn_clear)

        # ─────── SAVE STATE BUTTON ────────────────────────
        self.save_btn = QPushButton("Save State — disabled")
        self.save_btn.clicked.connect(self._save_state)
        scroll_layout.addWidget(self.save_btn)

        # Finalise layout
        content.setLayout(scroll_layout)
        scroll_area.setWidget(content)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)
        self._disable_legacy_controls()
        self.display_analysis(presentation or RegulatorGuiAdapter.unavailable("pride", "No analyzer evidence loaded."))

    def _disable_legacy_controls(self) -> None:
        for control in (self.threshold, self.btn_sim, self.btn_clear, self.save_btn):
            control.setEnabled(False)
            control.setToolTip("Disabled: current-runtime GUI is a read-only analyzer evidence display.")
        self.threshold_label.setText("Analyzer thresholds are read-only; see evidence details.")

    def display_analysis(self, presentation: RegulatorGuiPresentation) -> None:
        """Display already-produced PRIDE_VECTOR_V1 evidence without recalculating it."""
        if presentation.regulator != "pride":
            raise ValueError("PrideRegulator accepts only pride presentation evidence")
        score = presentation.overall_score or 0.0
        self.pride_value = score
        self.pride_bar.set_progress(score / 100.0)
        suffix = "" if presentation.available else " (unavailable)"
        self.pride_label.setText(f"Pride: {score:g} / 100{suffix}")
        self.subscores["SSN"] = presentation.subscores.get("SSN", 0.0)
        self.sub_widgets["SSN"].set_progress(self.subscores["SSN"] / 100.0)
        for key in ("OC", "CR", "SI", "BE", "NR"):
            self.subscores[key] = 0
            self.sub_widgets[key].set_progress(0.0)
        self.log_box.setPlainText(presentation.details())

    # ────────────────────────────────────────────────────────
    # INTERNALS (threshold, simulation, clear)
    # ────────────────────────────────────────────────────────

    def _threshold_label_update(self, value: int) -> None:
        self.threshold_label.setText(f"Lock ≥ {value}")

    def _simulate_update(self) -> None:
        self.pride_value = min(100, self.pride_value + random.randint(4, 10))
        self.pride_bar.set_progress(self.pride_value / 100.0)
        self.pride_label.setText(f"Pride: {self.pride_value} / 100")

        for key in self.subscores:
            self.subscores[key] = min(100, self.subscores[key] + random.randint(0, 8))
            bar = self.sub_widgets[key]
            bar.set_progress(self.subscores[key] / 100.0)

        t = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.append(
            f"[{t}] P={self.pride_value} | OC={self.subscores['OC']} "
            f"CR={self.subscores['CR']} SI={self.subscores['SI']} BE={self.subscores['BE']} NR={self.subscores['NR']}\n"
        )

    def _clear_log(self) -> None:
        self.log_box.clear()
        self.pride_value = 0
        for key in self.subscores:
            self.subscores[key] = 0
            bar = self.sub_widgets[key]
            bar.set_progress(0.0)
        self.pride_bar.set_progress(0.0)
        self.pride_label.setText("Pride: 0 / 100")

    # ─────── SAVE STATE (NEW)────────────────────────────
    def _save_state(self) -> None:
        """Dump the current main value and sub‑scores to a JSON file."""
        state = {
            "main": self.pride_value,
            "subscores": dict(self.subscores),
        }

        fname = f"{self.windowTitle().replace(' ', '_')}.json"
        file_path = Path(__file__).parent / fname

        try:
            with open(file_path, "w", encoding="utf-8") as fp:
                json.dump(state, fp, indent=2)
            self._status_message(f"State saved to: {file_path}")
        except Exception as exc:  # pragma: no cover – defensive
            self._status_message(f"Error saving state: {exc}")

    # ─────── HELPER FOR TEMPORARY STATUS MESSAGE ──────
    def _status_message(self, txt: str) -> None:
        """Show a temporary message in the window title."""
        original = self.windowTitle()
        self.setWindowTitle(txt)
        QTimer.singleShot(3000, lambda: self.setWindowTitle(original))  # show for 3 s


# ────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = PrideRegulator()
    win.show()
    sys.exit(app.exec())
