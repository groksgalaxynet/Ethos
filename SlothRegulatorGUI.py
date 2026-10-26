# SlothRegulatorGUI.py ────────────────────────────────────────────────
#
#  ETHOS++ — Sloth Regulation Module
#
#  Updated: Added QScrollArea to handle tall layouts and initialized 
#  sloth_value to prevent attribute errors.
#
#  ────────────────────────────────────────────────────────────────

import sys
import random
import datetime
import json
from pathlib import Path
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
    QScrollArea,
)
from PyQt6.QtCore import Qt, QRect, QTimer
from PyQt6.QtGui import QColor, QPainter


# ------------------------------------------------------------
# CUSTOM BAR VIEW
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
        self.resize(550, 850)
        
        # Initialize internal state
        self.sloth_value = 0

        # Create Scroll Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none; background-color: #0d101b;")

        # Container Widget
        container = QWidget()
        container.setStyleSheet("background-color: #0d101b; color: white; font-family: Menlo;")
        scroll_area.setWidget(container)
        self.setCentralWidget(scroll_area)

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(15)

        # Title
        title = QLabel("Sloth Coefficient Monitor")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18pt; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title)

        # Main Sloth bar
        self.sloth_bar = BarWidget("#4aa8ff")
        main_layout.addWidget(self.sloth_bar)

        self.sloth_label = QLabel("Sloth: 0 / 100")
        self.sloth_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.sloth_label)

        # Sub‑channels section
        sub_title = QLabel("Sloth Sub‑Channels")
        sub_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #39ffb0; margin-top: 10px;")
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

        # Weights section
        w_title = QLabel("Sloth Weight Controls")
        w_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #ff8800; margin-top: 10px;")
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

        # Threshold section
        t_lbl = QLabel("Ego Lock Threshold")
        t_lbl.setStyleSheet("font-weight: bold; margin-top: 5px;")
        main_layout.addWidget(t_lbl)

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(70)
        self.threshold_slider.valueChanged.connect(self.threshold_changed)
        main_layout.addWidget(self.threshold_slider)

        self.threshold_label = QLabel("Lock ≥ 70")
        main_layout.addWidget(self.threshold_label)

        # Log section
        log_title = QLabel("Sloth Timeline Log")
        log_title.setStyleSheet("font-size: 14pt; font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(log_title)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(200)
        self.log_box.setStyleSheet(
            "background-color: #1e1e28; border: 1px solid #333; color: white; font-family: Menlo;"
        )
        main_layout.addWidget(self.log_box)

        # Action Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)

        sim_btn = QPushButton("Simulate Sloth Update")
        sim_btn.setStyleSheet("background-color: #4444ff; color: white; padding: 12px; font-weight: bold;")
        sim_btn.clicked.connect(self.simulate_update)
        btn_layout.addWidget(sim_btn)

        save_btn = QPushButton("Save State (JSON)")
        save_btn.setStyleSheet("background-color: #ff8800; color: white; padding: 12px; font-weight: bold;")
        save_btn.clicked.connect(self._save_state)
        btn_layout.addWidget(save_btn)

        clear_btn = QPushButton("Clear Log / Reset")
        clear_btn.setStyleSheet("background-color: #333333; color: white; padding: 12px;")
        clear_btn.clicked.connect(self.clear_log)
        btn_layout.addWidget(clear_btn)

        main_layout.addLayout(btn_layout)
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

        # Weighted score calculation
        wsum = sum(self.weights.values()) or 1
        ss = sum(self.subscores[k] * self.weights[k] for k in self.subscores) / wsum
        ss_int = int(ss)

        t = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = (
            f"[{t}] SS={ss_int} | "
            f"CWI={self.subscores['CWI']} EDR={self.subscores['EDR']} "
            f"RAF={self.subscores['RAF']} TCF={self.subscores['TCF']} "
            f"ISL={self.subscores['ISL']} EAD={self.subscores['EAD']} "
            f"W={ {k: round(v,2) for k,v in self.weights.items()} }\n"
        )
        self.log_box.append(log_entry)

    # ------------------------------------------------------------
    # CLEAR / RESET
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
    # SAVE STATE
    # ------------------------------------------------------------
    def _save_state(self) -> None:
        """Persist the current sloth state to a JSON file."""
        state = {
            "timestamp": datetime.datetime.now().isoformat(),
            "sloth_value": self.sloth_value,
            "subscores": dict(self.subscores),
            "weights": dict(self.weights),
        }

        fname = f"{self.windowTitle().replace(' ', '_')}.json"
        file_path = Path(__file__).parent / fname

        try:
            with open(file_path, "w", encoding="utf-8") as fp:
                json.dump(state, fp, indent=2)
            self._status_message(f"State saved to: {fname}")
        except Exception as exc:
            self._status_message(f"Error saving state: {exc}")

    def _status_message(self, text: str) -> None:
        """Show a temporary message in the window title."""
        original = "ETHOS++ — Sloth Regulation Module"
        self.setWindowTitle(text)
        QTimer.singleShot(3000, lambda: self.setWindowTitle(original))


# ------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SlothRegulator()
    window.show()
    sys.exit(app.exec())
