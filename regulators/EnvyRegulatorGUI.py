# EnvyRegulatorGUI.py ────────────────────────────────────────────────
#
#  ETHOS++ — Envy Regulation Module
#
#  Rewired to include a “Save State” button that dumps the current
#  `envy_value` and all sub‑scores into a JSON file next to this script.
#
#  The original logic is preserved; only the new persistence layer has been added.
#
#  ────────────────────────────────────────────────────────────────

import sys
import random
import datetime
import json                     # NEW – used for serialising state
from pathlib import Path        # NEW – convenient file handling

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QPushButton,
    QTextEdit,
)
from PyQt6.QtGui import QPainter, QColor, QFont, QPaintEvent
from PyQt6.QtCore import Qt, QRect, QTimer


# ------------------------------------------------------------
# CUSTOM BAR VIEW (replacement for ProgressView)
# ------------------------------------------------------------
class BarWidget(QWidget):
    def __init__(self, color="#39ff14", height=22):
        super().__init__()
        self.color = QColor(color)
        self.height = height
        self.progress = 0.0

    def set_progress(self, progress):
        self.progress = max(0.0, min(progress, 1.0))
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        fill_width = int(self.width() * min(max(0.0, self.progress), 1.0))
        painter.setBrush(self.color)
        painter.drawRect(QRect(0, 0, fill_width, self.height))


# ------------------------------------------------------------
# MAIN ENVY REGULATOR GUI
# ------------------------------------------------------------
class EnvyRegulator(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ETHOS++ — Envy Regulation Module")
        self.resize(800, 600)

        # ENVY DATA CHANNELS
        self.envy_value: int = 0
        self.subscores: dict[str, int] = {
            "CSV": 0,  # Comparative Self‑Value
            "ETS": 0,  # External Threat Sensitivity
            "IER": 0,  # Identity Erosion Rate
            "HII": 0,  # Harmful Impulse Index
            "RH": 0,   # Recognition Hunger
        }

        # MAIN LAYOUT
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # ----------------- TITLE -----------------------------------
        title_label = QLabel("Envy Coefficient Monitor")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Menlo-Bold", 18))
        main_layout.addWidget(title_label)

        # ----------------- MAIN ENVY BAR --------------------------
        self.envy_bar = BarWidget(color="#f7e92a")  # yellow envy theme
        self.envy_label = QLabel(f"Envy: 0 / 100")
        self.envy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.envy_bar)
        main_layout.addWidget(self.envy_label)

        # ----------------- SUBCHANNEL LIST ------------------------
        sub_title_label = QLabel("Sub‑Channels")
        sub_title_label.setFont(QFont("Menlo-Bold", 14))
        main_layout.addWidget(sub_title_label)

        self.sub_widgets: dict[str, BarWidget] = {}
        for key in ["CSV", "ETS", "IER", "HII", "RH"]:
            lbl = QLabel(key)
            bar = BarWidget()
            bar.set_progress(0.0)
            sub_layout = QHBoxLayout()
            sub_layout.addWidget(lbl)
            sub_layout.addWidget(bar)
            main_layout.addLayout(sub_layout)
            self.sub_widgets[key] = bar

        # ----------------- TIMELINE LOG --------------------------
        log_title_label = QLabel("Envy Timeline Log")
        log_title_label.setFont(QFont("Menlo-Bold", 14))
        main_layout.addWidget(log_title_label)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet(
            "background-color: #1e1e28; color: white; font-family: Menlo;"
        )
        self.log_box.setFixedHeight(260)
        main_layout.addWidget(self.log_box)

        # ----------------- THRESHOLD ---------------------------------
        threshold_slider = QSlider(Qt.Orientation.Horizontal)
        threshold_slider.setValue(70)
        threshold_slider.valueChanged.connect(self._threshold_changed)
        main_layout.addWidget(threshold_slider)

        self.threshold_label = QLabel("Lock ≥ 70")
        self.threshold_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.threshold_label)

        # ----------------- BUTTONS -----------------------------------
        button_layout = QHBoxLayout()

        btn_update = QPushButton("Simulate Envy Update")
        btn_update.clicked.connect(self._simulate_update)
        button_layout.addWidget(btn_update)

        btn_clear = QPushButton("Clear Log")
        btn_clear.clicked.connect(self._clear_log)
        button_layout.addWidget(btn_clear)

        # New: Save State
        btn_save = QPushButton("Save State")
        btn_save.clicked.connect(self._save_state)
        button_layout.addWidget(btn_save)

        main_layout.addLayout(button_layout)

    # ------------------------------------------------------------
    # CALLBACKS
    # ------------------------------------------------------------
    def _threshold_changed(self, value: int) -> None:
        self.threshold_label.setText(f"Lock ≥ {value}")

    def _simulate_update(self) -> None:
        """Simulate an update to the envy values and subscores."""
        self.envy_value = min(100, self.envy_value + random.randint(3, 10))
        self.envy_bar.set_progress(self.envy_value / 100.0)
        self.envy_label.setText(f"Envy: {self.envy_value} / 100")

        # Update sub‑channels
        for key in self.subscores:
            self.subscores[key] = min(100, self.subscores[key] + random.randint(0, 8))
            bar = self.sub_widgets[key]
            bar.set_progress(self.subscores[key] / 100.0)

        # Log event
        t = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = (
            f"[{t}] E={self.envy_value} | "
            f"CSV={self.subscores['CSV']} ETS={self.subscores['ETS']} "
            f"IER={self.subscores['IER']} HII={self.subscores['HII']} RH={self.subscores['RH']}\n"
        )
        self.log_box.append(log_entry)

    def _clear_log(self) -> None:
        """Clear the log and reset all values."""
        self.log_box.clear()
        self.envy_value = 0

        for key in self.subscores:
            self.subscores[key] = 0
            bar = self.sub_widgets[key]
            bar.set_progress(0.0)

        self.envy_label.setText("Envy: 0 / 100")

    # ------------------------------------------------------------
    # SAVE STATE (NEW)──────────────────────────────────────
    def _save_state(self) -> None:
        """Persist the current envy state to a JSON file."""
        state = {
            "envy_value": self.envy_value,
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

    # ------------------------------------------------------------
    # TEMPORARY STATUS MESSAGE (optional helper)
    # ------------------------------------------------------------
    def _status_message(self, text: str) -> None:
        """Show a temporary message in the window title."""
        original = self.windowTitle()
        self.setWindowTitle(text)
        QTimer.singleShot(3000, lambda: self.setWindowTitle(original))  # 3 s

# ------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = EnvyRegulator()
    win.show()
    sys.exit(app.exec())

