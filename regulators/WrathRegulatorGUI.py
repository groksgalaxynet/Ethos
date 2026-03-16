# WrathRegulatorGUI.py ────────────────────────────────────────────────
#
#  ETHOS++ — Wrath Regulation Module
#
#  Integrated: a "Save State" button that dumps the current main value,
#  sub‑scores and weights into a JSON file next to this script.
#
#  ────────────────────────────────────────────────────────────────

import sys
import random
import datetime
import json                     # NEW – required for state persistence
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
class WrathRegulator(QWidget):
    """Main regulator window for Wrath."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ETHOS++ — Wrath Regulation Module")
        self.resize(800, 600)

        # WRATH DATA
        self.wrath_value: int = 0
        self.compassion_value: int = 0   # inverted wrath as compassion

        # SUBCHANNELS
        self.subscores = {
            "ESI": 0,  # Escalation Surge Index
            "APS": 0,  # Adversarial Posture Shift
            "HPV": 0,  # Harm Projection Vector (critical)
            "ELI": 0,  # Emotional Loop Instability
            "FAF": 0,  # Force Amplification Factor
            "PBS": 0,  # Protection Bias Strength (compassion)
        }

        # WEIGHTS
        self.weights = {
            "ESI": 1.0,
            "APS": 1.0,
            "HPV": 1.0,
            "ELI": 1.0,
            "FAF": 1.0,
            "PBS": 1.0,
        }

        # MAIN LAYOUT
        main_layout = QVBoxLayout()

        # SCROLL AREA
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # --------------------------------------------------------
        # TITLE
        # --------------------------------------------------------
        title_label = QLabel("WRATH → COMPASSION ENGINE")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Menlo-Bold", 18))
        scroll_layout.addWidget(title_label)

        sub_label = QLabel("\"In wrath comes compassion!!\" — Superhero Clause Active")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_label.setStyleSheet("color: #ff9999; font-family: Menlo; font-size: 12px;")
        scroll_layout.addWidget(sub_label)

        # --------------------------------------------------------
        # WRATH BAR
        # --------------------------------------------------------
        self.wrath_bar = BarWidget(width=600, height=22, bar_color="#ff3b3b")
        self.wrath_label = QLabel(f"Wrath: 0 / 100")
        self.wrath_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_layout.addWidget(self.wrath_bar)
        scroll_layout.addWidget(self.wrath_label)

        # --------------------------------------------------------
        # COMPASSION BAR (Inverted Wrath Output)
        # --------------------------------------------------------
        compassion_title_label = QLabel("Compassion Output (Superhero Clause)")
        compassion_title_label.setStyleSheet("color: #99ffcc; font-family: Menlo-Bold; font-size: 14px;")
        scroll_layout.addWidget(compassion_title_label)

        self.compassion_bar = BarWidget(width=600, height=22, bar_color="#33ffaa")
        self.compassion_label = QLabel(f"Compassion: 0 / 100")
        self.compassion_label.setStyleSheet("color: #ccffee; font-family: Menlo; font-size: 14px;")
        self.compassion_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_layout.addWidget(self.compassion_bar)
        scroll_layout.addWidget(self.compassion_label)

        # --------------------------------------------------------
        # SUBCHANNELS
        # --------------------------------------------------------
        subchannels_title_label = QLabel("Wrath Sub‑Channels")
        subchannels_title_label.setStyleSheet("color: white; font-family: Menlo-Bold; font-size: 14px;")
        scroll_layout.addWidget(subchannels_title_label)

        bar_width = 600

        self.sub_widgets = {}

        for key in ["ESI", "APS", "HPV", "ELI", "FAF", "PBS"]:
            lbl = QLabel(key)
            bar_color = "#ff5555" if key != "PBS" else "#44ff99"
            bar = BarWidget(width=bar_width, height=22, bar_color=bar_color)
            bar.set_progress(0.0)

            sub_layout = QHBoxLayout()
            sub_layout.addWidget(lbl)
            sub_layout.addWidget(bar)
            scroll_layout.addLayout(sub_layout)
            self.sub_widgets[key] = bar

        # --------------------------------------------------------
        # WEIGHT SLIDERS
        # --------------------------------------------------------
        weights_title_label = QLabel("Wrath Weight Controls")
        weights_title_label.setStyleSheet("color: white; font-family: Menlo-Bold; font-size: 14px;")
        scroll_layout.addWidget(weights_title_label)

        self.weight_sliders = {}

        for key in ["ESI", "APS", "HPV", "ELI", "FAF", "PBS"]:
            lbl = QLabel(key)
            s = QSlider(Qt.Orientation.Horizontal)
            s.setMinimum(0)
            s.setMaximum(100)
            s.setValue(100)
            s.valueChanged.connect(self._weight_changed)
            self.weight_sliders[key] = s

            weight_layout = QHBoxLayout()
            weight_layout.addWidget(lbl)
            weight_layout.addWidget(s)
            scroll_layout.addLayout(weight_layout)

        # --------------------------------------------------------
        # LOG WINDOW
        # --------------------------------------------------------
        log_title_label = QLabel("Wrath Timeline Log")
        log_title_label.setStyleSheet("color: white; font-family: Menlo-Bold; font-size: 14px;")
        scroll_layout.addWidget(log_title_label)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet(
            "background-color: #1f1818; color: white; font-family: Menlo; font-size: 12px;"
        )
        scroll_layout.addWidget(self.log_box)

        # --------------------------------------------------------
        # THRESHOLD
        # --------------------------------------------------------
        threshold_label = QLabel("Ego Lock Threshold")
        scroll_layout.addWidget(threshold_label)

        self.threshold = QSlider(Qt.Orientation.Horizontal)
        self.threshold.setValue(70)
        self.threshold.valueChanged.connect(self._threshold_changed)
        scroll_layout.addWidget(self.threshold)

        self.threshold_label = QLabel(f"Lock ≥ 70")
        scroll_layout.addWidget(self.threshold_label)

        # --------------------------------------------------------
        # BUTTONS
        # --------------------------------------------------------
        simulate_button = QPushButton("Simulate Wrath Update")
        simulate_button.clicked.connect(self._simulate_update)
        scroll_layout.addWidget(simulate_button)

        clear_button = QPushButton("Clear Log")
        clear_button.clicked.connect(self._clear_log)
        scroll_layout.addWidget(clear_button)

        # ─────── SAVE STATE BUTTON ─────────────────────────────
        save_btn = QPushButton("Save State")
        save_btn.clicked.connect(self._save_state)
        scroll_layout.addWidget(save_btn)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    # ------------------------------------------------------------
    # CALLBACKS
    # ------------------------------------------------------------

    def _weight_changed(self) -> None:
        for k in self.weights:
            self.weights[k] = self.weight_sliders[k].value() / 100.0

    def _threshold_changed(self, value: int) -> None:
        self.threshold_label.setText(f"Lock ≥ {value}")

    # ------------------------------------------------------------
    # WRATH SIM ENGINE (Superhero Clause)
    # ------------------------------------------------------------

    def _simulate_update(self) -> None:
        # Increase wrath but cap
        self.wrath_value = min(100, self.wrath_value + random.randint(4, 12))
        self.wrath_bar.set_progress(self.wrath_value / 100.0)
        self.wrath_label.setText(f"Wrath: {self.wrath_value} / 100")

        # Update subchannels
        for k in self.subscores:
            self.subscores[k] = min(100, self.subscores[k] + random.randint(0, 10))
            bar = self.sub_widgets[k]
            bar.set_progress(self.subscores[k] / 100.0)

        # Superhero Clause:
        HPV = self.subscores["HPV"]
        PBS = self.subscores["PBS"]

        SHM = max(1.0 - (HPV * self.weights["HPV"] / 100), 0.0)

        wsum = sum(self.weights.values())
        if wsum == 0:
            wsum = 1

        raw_wrath = (
            self.subscores["ESI"] * self.weights["ESI"]
            + self.subscores["APS"] * self.weights["APS"]
            + self.subscores["HPV"] * self.weights["HPV"]
            + self.subscores["ELI"] * self.weights["ELI"]
            + self.subscores["FAF"] * self.weights["FAF"]
            - self.subscores["PBS"] * self.weights["PBS"]
        ) / wsum

        final_wrath = max(0, raw_wrath * SHM)
        final_compassion = min(100, (100 - final_wrath) + (PBS / 2))

        self.compassion_bar.set_progress(final_compassion / 100.0)
        self.compassion_label.setText(f"Compassion: {int(final_compassion)} / 100")

        t = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.append(
            f"[{t}] WRATH={int(final_wrath)} COMP={int(final_compassion)} "
            f"ESI={self.subscores['ESI']} APS={self.subscores['APS']} "
            f"HPV={self.subscores['HPV']} ELI={self.subscores['ELI']} "
            f"FAF={self.subscores['FAF']} PBS={self.subscores['PBS']} SHM={round(SHM, 2)}\n"
        )

    # ------------------------------------------------------------
    # CLEAR
    # ------------------------------------------------------------

    def _clear_log(self) -> None:
        self.log_box.clear()
        self.wrath_value = 0
        self.compassion_value = 0

        for k in self.subscores:
            self.subscores[k] = 0
            bar = self.sub_widgets[k]
            bar.set_progress(0.0)

        self.wrath_bar.set_progress(0.0)
        self.wrath_label.setText("Wrath: 0 / 100")

        self.compassion_bar.set_progress(0.0)
        self.compassion_label.setText("Compassion: 0 / 100")

    # ------------------------------------------------------------
    # SAVE STATE (NEW)────────────────────────────
    def _save_state(self) -> None:
        """Persist the current main value, sub‑scores and weights to JSON."""
        state = {
            "main": self.wrath_value,
            "subscores": dict(self.subscores),
            "weights": dict(self.weights),
        }

        fname = f"{self.windowTitle().replace(' ', '_')}.json"
        file_path = Path(__file__).parent / fname

        try:
            with open(file_path, "w", encoding="utf-8") as fp:
                json.dump(state, fp, indent=2)
            self._status_message(f"State saved to: {file_path}")
        except Exception as exc:  # pragma: no cover – defensive
            self._status_message(f"Error saving state: {exc}")

    # ------------------------------------------------------------
    # HELPER FOR TEMPORARY STATUS MESSAGE
    # ------------------------------------------------------------
    def _status_message(self, txt: str) -> None:
        """Show a temporary message in the window title."""
        original = self.windowTitle()
        self.setWindowTitle(txt)
        QTimer.singleShot(3000, lambda: self.setWindowTitle(original))  # show for 3 s


# ------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WrathRegulator()
    window.show()
    sys.exit(app.exec())

