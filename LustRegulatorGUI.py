# LustRegulatorGUI.py ────────────────────────────────────────────────
#
#  ETHOS++ — Lust Regulation Module
#
#  Fixed: AttributeError: type object 'Qt' has no attribute 'QRect'
#  Fixed: Added QScrollArea for interface persistence and visibility.
#
#  ────────────────────────────────────────────────────────────────

import sys
import random
import json
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QSlider,
    QLabel,
    QPushButton,
    QTextEdit,
    QHBoxLayout,
    QScrollArea,
)
from PyQt6.QtGui import QPainter, QColor, QPaintEvent
from PyQt6.QtCore import Qt, QRect, QTimer


# ------------------------------------------------------------
class BarWidget(QWidget):
    """Simple horizontal progress bar with a fixed colour."""

    def __init__(self, bar_color: str = "#39ff14"):
        super().__init__()
        self.bar_color = QColor(bar_color)
        self.progress: float = 0.0

    def set_progress(self, progress: float) -> None:
        """Set the progress as a percentage (0-1)."""
        self.progress = max(0.0, min(progress, 1.0))
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)

        # Background (dark grey)
        painter.fillRect(event.rect(), QColor("#333"))

        # Fill width based on the current progress value
        fill_width = int(self.width() * self.progress)

        # FIXED: Use QRect from QtCore, not Qt namespace
        painter.fillRect(
            QRect(0, 0, fill_width, self.height()), self.bar_color
        )


# ------------------------------------------------------------
class LustRegulator(QMainWindow):
    """Main regulator window for Lust."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ETHOS++ — Lust Regulation Module")
        self.resize(550, 850)
        
        # Main data structures
        self.lust_value = 0
        self.subscores = {"SDI": 0, "NPL": 0, "IEF": 0, "IFR": 0, "FLS": 0, "DOP": 0}
        self.weights = {"SDI": 1.0, "NPL": 1.0, "IEF": 1.0, "IFR": 1.0, "FLS": 1.0, "DOP": 1.0}

        # --- SCROLL AREA SETUP ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none; background-color: #0f131a;")

        # Container Widget for the scroll area
        container = QWidget()
        container.setStyleSheet("background-color: #0f131a; color: white; font-family: Menlo;")
        scroll_area.setWidget(container)
        self.setCentralWidget(scroll_area)

        layout_main = QVBoxLayout(container)
        layout_main.setContentsMargins(25, 20, 25, 20)
        layout_main.setSpacing(15)

        # ----------------- TITLE ------------------------------------
        title_label = QLabel("Lust Coefficient Monitor")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18pt; font-weight: bold; margin-bottom: 10px;")
        layout_main.addWidget(title_label)

        # ----------------- MAIN LUST BAR ---------------------------
        self.lust_bar = BarWidget(bar_color="#ff3fb4")
        self.lust_bar.setFixedHeight(22)
        layout_main.addWidget(self.lust_bar)

        self.lust_label = QLabel("Lust: 0 / 100")
        self.lust_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_main.addWidget(self.lust_label)

        # ----------------- SUBCHANNELS --------------------------------
        sub_title_label = QLabel("Lust Sub‑Channels")
        sub_title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #39ffb0; margin-top: 10px;")
        layout_main.addWidget(sub_title_label)

        self.sub_widgets = {}
        for key in self.subscores.keys():
            sub_layout = QHBoxLayout()
            label = QLabel(key)
            label.setFixedWidth(60)
            
            bar = BarWidget(bar_color="#39ff14")
            bar.setFixedHeight(22)
            self.sub_widgets[key] = bar
            
            sub_layout.addWidget(label)
            sub_layout.addWidget(bar)
            layout_main.addLayout(sub_layout)

        # ----------------- WEIGHT SLIDERS ---------------------------
        w_title_label = QLabel("Lust Weight Controls")
        w_title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #ff8800; margin-top: 10px;")
        layout_main.addWidget(w_title_label)

        self.weight_sliders = {}
        for key in self.weights.keys():
            sub_layout = QHBoxLayout()
            label = QLabel(key)
            label.setFixedWidth(60)

            s = QSlider(Qt.Orientation.Horizontal)
            s.setRange(0, 100)
            s.setValue(int(self.weights[key] * 100))
            s.valueChanged.connect(lambda value, k=key: self._weight_change(k, value))
            self.weight_sliders[key] = s

            sub_layout.addWidget(label)
            sub_layout.addWidget(s)
            layout_main.addLayout(sub_layout)

        # ----------------- LOG BOX -----------------------------------
        log_title_label = QLabel("Lust Timeline Log")
        log_title_label.setStyleSheet("font-size: 14pt; font-weight: bold; margin-top: 10px;")
        layout_main.addWidget(log_title_label)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(200)
        self.log_box.setStyleSheet(
            "background-color: #1a1e26; border: 1px solid #333; color: white; font-family: Menlo;"
        )
        layout_main.addWidget(self.log_box)

        # ----------------- THRESHOLD SLIDER -----------------------
        t_label = QLabel("Ego Lock Threshold")
        t_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        layout_main.addWidget(t_label)

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_value = 70
        self.threshold_slider.setValue(self.threshold_value)
        self.threshold_slider.valueChanged.connect(self._threshold_changed)
        layout_main.addWidget(self.threshold_slider)

        self.threshold_label = QLabel(f"Lock ≥ {self.threshold_value}")
        layout_main.addWidget(self.threshold_label)

        # ----------------- BUTTONS ----------------------------------
        btn_v_layout = QVBoxLayout()
        btn_v_layout.setSpacing(10)

        sim_btn = QPushButton("Simulate Lust Update")
        sim_btn.setStyleSheet("background-color: #4444ff; color: white; padding: 12px; font-weight: bold;")
        sim_btn.clicked.connect(self._simulate_update)
        btn_v_layout.addWidget(sim_btn)

        save_btn = QPushButton("Save State (JSON)")
        save_btn.setStyleSheet("background-color: #ff8800; color: white; padding: 12px; font-weight: bold;")
        save_btn.clicked.connect(self._save_state)
        btn_v_layout.addWidget(save_btn)

        clr_btn = QPushButton("Clear Log / Reset")
        clr_btn.setStyleSheet("background-color: #333333; color: white; padding: 12px;")
        clr_btn.clicked.connect(self._clear_log)
        btn_v_layout.addWidget(clr_btn)

        layout_main.addLayout(btn_v_layout)
        layout_main.addStretch()

    # ------------------------------------------------------------
    def _weight_change(self, key: str, value: int) -> None:
        self.weights[key] = value / 100.0

    def _threshold_changed(self) -> None:
        self.threshold_value = self.threshold_slider.value()
        self.threshold_label.setText(f"Lock ≥ {self.threshold_value}")

    def _simulate_update(self) -> None:
        """Simulate an update to the lust values and weights."""
        self.lust_value = min(100, self.lust_value + random.randint(3, 10))
        self.lust_bar.set_progress(self.lust_value / 100.0)
        self.lust_label.setText(f"Lust: {self.lust_value} / 100")

        for key in self.sub_widgets.keys():
            self.subscores[key] = min(100, self.subscores[key] + random.randint(0, 8))
            self.sub_widgets[key].set_progress(self.subscores[key] / 100.0)

        # Weighted calculation
        wsum = sum(self.weights.values()) or 1
        weighted_score = (sum(self.subscores[sub] * self.weights[sub] for sub in self.subscores) / wsum) / 2.0
        ls_int = int(weighted_score)

        t = datetime.now().strftime("%H:%M:%S")
        log_entry = (
            f"[{t}] LS={ls_int} | "
            f"SDI={self.subscores['SDI']} NPL={self.subscores['NPL']} "
            f"IEF={self.subscores['IEF']} IFR={self.subscores['IFR']} "
            f"FLS={self.subscores['FLS']} DOP={self.subscores['DOP']} "
            f"W={ {k: round(v,2) for k,v in self.weights.items()} }\n"
        )
        self.log_box.append(log_entry)

    def _save_state(self) -> None:
        """Persist the current lust state to a JSON file."""
        state = {
            "timestamp": datetime.now().isoformat(),
            "lust_value": self.lust_value,
            "subscores": dict(self.subscores),
            "weights": dict(self.weights),
        }
        fname = f"{self.windowTitle().replace(' ', '_')}.json"
        file_path = Path(__file__).parent / fname
        try:
            with open(file_path, "w", encoding="utf-8") as fp:
                json.dump(state, fp, indent=2)
            self._status_message(f"State saved: {fname}")
        except Exception as exc:
            self._status_message(f"Error: {exc}")

    def _clear_log(self) -> None:
        self.log_box.clear()
        self.lust_value = 0
        for key in self.subscores:
            self.subscores[key] = 0
            self.sub_widgets[key].set_progress(0.0)
        self.lust_bar.set_progress(0.0)
        self.lust_label.setText("Lust: 0 / 100")

    def _status_message(self, text: str) -> None:
        original = "ETHOS++ — Lust Regulation Module"
        self.setWindowTitle(text)
        QTimer.singleShot(3000, lambda: self.setWindowTitle(original))


# ------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LustRegulator()
    window.show()
    sys.exit(app.exec())
