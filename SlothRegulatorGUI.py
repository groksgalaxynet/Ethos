# SlothRegulatorGUI.py ────────────────────────────────────────────────
#
#  ETHOS++ — Sloth Regulation Module
#
#  Rewired to include a “Save State” button that dumps the current
#  `sloth_value`, all sub‑scores and weights into a JSON file next to this script.
#
#  The original logic is preserved; only the persistence layer has been added.
#
#  ────────────────────────────────────────────────────────────────

import sys
import random
import datetime
import json                    # NEW – for serialising state
from pathlib import Path       # NEW – convenient file handling
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QPushButton,
    QTextEdit,
)
from PyQt6.QtCore import Qt, QRect, QTimer
from PyQt6.QtGui import QColor, QPainter


# ------------------------------------------------------------
# CUSTOM BAR VIEW (replacement for ProgressView)
# ------------------------------------------------------------
class BarWidget(QWidget):
    def __init__(self, bar_color="#39ff14"):
        super().__init__()
        self.bar_color = QColor(bar_color)
        self.progress: float = 0.0
        self.setFixedHeight(22)

    def set_progress(self, progress: float) -> None:
        """Set the progress as a percentage (0‑1)."""
        self.progress = max(0.0, min(progress, 1.0))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        fill_width = int(self.progress * self.width())
        painter.fillRect(QRect(0, 0, fill_width, self.height()), self.bar_color)


# ------------------------------------------------------------
# MAIN SLOTH REGULATOR GUI
# ------------------------------------------------------------
class SlothRegulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ETHOS++ — Sloth Regulation Module")
        self.resize(500, 900)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Dark background
        self.setStyleSheet(
            "background-color: #0d101b; color: white; font-family: Menlo;"
        )

        # Title
        title = QLabel("Sloth Coefficient Monitor")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18pt; font-weight: bold;")
        main_layout.addWidget(title)

        # Main Sloth bar
        self.sloth_bar = BarWidget("#4aa8ff")
        main_layout.addWidget(self.sloth_bar)

        self.sloth_label = QLabel("Sloth: 0 / 100")
        self.sloth_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.sloth_label)

        # Sub‑channels title
        sub_title = QLabel("Sloth Sub‑Channels")
        sub_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        main_layout.addWidget(sub_title)

        self.subscores = {"CWI": 0, "EDR": 0, "RAF": 0, "TCF": 0, "ISL": 0, "EAD": 0}
        self.sub_bars: dict[str, BarWidget] = {}

        for key in self.subscores:
            hbox = QHBoxLayout()
            lbl = QLabel(key)
            lbl.setFixedWidth(60)
            bar = BarWidget("#39ffb0")
            bar.progress = 0
            self.sub_bars[key] = bar
            hbox.addWidget(lbl)
            hbox.addWidget(bar)
            main_layout.addLayout(hbox)

        # Weights title
        w_title = QLabel("Sloth Weight Controls")
        w_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        main_layout.addWidget(w_title)

        self.weights = {"CWI": 1.0, "EDR": 1.0, "RAF": 1.0, "TCF": 1.0, "ISL": 1.0, "EAD": 1.0}
        self.weight_sliders: dict[str, QSlider] = {}

        for key in self.weights:
            hbox = QHBoxLayout()
            lbl = QLabel(key)
            lbl.setFixedWidth(60)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(100)
            slider.valueChanged.connect(self.weight_changed)
            self.weight_sliders[key] = slider
            hbox.addWidget(lbl)
            hbox.addWidget(slider)
            main_layout.addLayout(hbox)

        # Threshold
        t_lbl = QLabel("Ego Lock Threshold")
        main_layout.addWidget(t_lbl)

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(70)
        self.threshold_slider.valueChanged.connect(self.threshold_changed)
        main_layout.addWidget(self.threshold_slider)

        self.threshold_label = QLabel("Lock ≥ 70")
        main_layout.addWidget(self.threshold_label)

        # Log
        log_title = QLabel("Sloth Timeline Log")
        log_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        main_layout.addWidget(log_title)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(260)
        self.log_box.setStyleSheet(
            "background-color: #1e1e28; color: white; font-family: Menlo;"
        )
        main_layout.addWidget(self.log_box)

        # Buttons
        sim_btn = QPushButton("Simulate Sloth Update")
        sim_btn.setStyleSheet("background-color: #4444ff; padding: 12px;")
        sim_btn.clicked.connect(self.simulate_update)
        main_layout.addWidget(sim_btn)

        clear_btn = QPushButton("Clear Log")
        clear_btn.setStyleSheet("background-color: #333333; padding: 12px;")
        clear_btn.clicked.connect(self.clear_log)
        main_layout.addWidget(clear_btn)

        # NEW: Save State button
        save_btn = QPushButton("Save State")
        save_btn.setStyleSheet("background-color: #ff8800; color: white; padding: 12px;")
        save_btn.clicked.connect(self._save_state)
        main_layout.addWidget(save_btn)

        main_layout.addStretch()

    # ------------------------------------------------------------
    # CALLBACKS
    # ------------------------------------------------------------
    def weight_changed(self) -> None:
        for k, slider in self.weight_sliders.items():
            self.weights[k] = slider.value() / 100.0

    def threshold_changed(self, value: int) -> None:
        self.threshold_label.setText(f"Lock ≥ {value}")

    # ------------------------------------------------------------
    # SIMULATION
    # ------------------------------------------------------------
    def simulate_update(self) -> None:
        """Simulate an update to the sloth values and subscores."""
        self.sloth_value = min(100, self.sloth_value + random.randint(3, 10))
        self.sloth_bar.set_progress(self.sloth_value / 100.0)
        self.sloth_label.setText(f"Sloth: {self.sloth_value} / 100")

        for k in self.subscores:
            self.subscores[k] = min(
                100,
                self.subscores[k] + random.randint(0, 8),
            )
            bar = self.sub_bars[k]
            bar.set_progress(self.subscores[k] / 100.0)

        # Weighted score
        wsum = sum(self.weights.values()) or 1
        ss = sum(self.subscores[k] * self.weights[k] for k in self.subscores) / wsum
        ss_int = int(ss)

        t = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = (
            f"[{t}] SS={ss_int} | "
            f"CWI={self.subscores['CWI']} EDR={self.subscores['EDR']} "
            f"RAF={self.subscores['RAF']} TCF={self.subscores['TCF']} "
            f"ISL={self.subscores['ISL']} EAD={self.subscores['EAD']} "
            f"W={self.weights}\n"
        )
        self.log_box.append(log_entry)

    # ------------------------------------------------------------
    # CLEAR
    # ------------------------------------------------------------
    def clear_log(self) -> None:
        self.log_box.clear()
        self.sloth_value = 0
        self.sloth_bar.set_progress(0.0)
        self.sloth_label.setText("Sloth: 0 / 100")
        for k in self.subscores:
            self.subscores[k] = 0
            bar = self.sub_bars[k]
            bar.set_progress(0.0)

    # ------------------------------------------------------------
    # SAVE STATE (NEW)──────────────────────────────────────
    def _save_state(self) -> None:
        """Persist the current sloth state to a JSON file."""
        state = {
            "sloth_value": getattr(self, "sloth_value", 0),
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
    window = SlothRegulator()
    window.show()
    sys.exit(app.exec())

