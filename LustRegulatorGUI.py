# LustRegulatorGUI.py ────────────────────────────────────────────────
#
#  ETHOS++ — Lust Regulation Module
#
#  Fixed the `BarWidget.paintEvent` implementation – the original code
#  called ``painter.fillRect(0, 0, fill_width, self.height())`` which
#  does not match any overload of QPainter::fillRect.  The new version
#  explicitly passes a QRect and the bar colour.
#
#  ────────────────────────────────────────────────────────────────

import sys
import random
from datetime import datetime
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
)
from PyQt6.QtGui import QPainter, QColor, QPaintEvent
from PyQt6.QtCore import Qt


# ------------------------------------------------------------
class BarWidget(QWidget):
    """Simple horizontal progress bar with a fixed colour."""

    def __init__(self, bar_color: str = "#39ff14"):
        super().__init__()
        self.bar_color = QColor(bar_color)
        self.progress: float = 0.0

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)

        # Background (dark grey)
        painter.fillRect(event.rect(), QColor("#333"))

        # Fill width based on the current progress value
        fill_width = int(self.width() * self.progress)

        # Draw the coloured bar – use a QRect and the bar colour
        painter.fillRect(
            Qt.QRect(0, 0, fill_width, self.height()), self.bar_color
        )


# ------------------------------------------------------------
class LustRegulator(QMainWindow):
    """Main regulator window for Lust."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ETHOS++ — Lust Regulation Module")
        self.setGeometry(100, 100, 800, 700)
        self.setStyleSheet("background-color: #0f131a;")

        # Main data structures
        self.lust_value = 0
        self.subscores = {
            "SDI": 0,
            "NPL": 0,
            "IEF": 0,
            "IFR": 0,
            "FLS": 0,
            "DOP": 0,
        }

        self.weights = {
            "SDI": 1.0,
            "NPL": 1.0,
            "IEF": 1.0,
            "IFR": 1.0,
            "FLS": 1.0,
            "DOP": 1.0,
        }

        # Main container
        main_container = QWidget(self)
        self.setCentralWidget(main_container)

        layout_main = QVBoxLayout(main_container)

        # ----------------- TITLE ------------------------------------
        title_label = QLabel("Lust Coefficient Monitor")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: white; font-size: 18px;")
        layout_main.addWidget(title_label)

        # ----------------- MAIN LUST BAR ---------------------------
        self.lust_bar = BarWidget(bar_color="#ff3fb4")  # pink/purple
        self.lust_bar.setFixedHeight(22)
        layout_main.addWidget(self.lust_bar)

        self.lust_label = QLabel("Lust: 0 / 100")
        self.lust_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lust_label.setStyleSheet("color: white;")
        layout_main.addWidget(self.lust_label)

        # ----------------- SUBCHANNELS --------------------------------
        sub_title_label = QLabel("Lust Sub‑Channels")
        sub_title_label.setStyleSheet("color: white; font-size: 14px;")
        layout_main.addWidget(sub_title_label)

        self.sub_widgets = {}
        bar_width = 600

        for key in ["SDI", "NPL", "IEF", "IFR", "FLS", "DOP"]:
            sub_layout = QHBoxLayout()

            label = QLabel(key)
            label.setStyleSheet("color: white;")
            sub_layout.addWidget(label)

            bar = BarWidget(bar_color="#39ff14")
            bar.setFixedSize(bar_width, 22)
            self.sub_widgets[key] = bar
            sub_layout.addWidget(bar)

            layout_main.addLayout(sub_layout)

        # ----------------- WEIGHT SLIDERS ---------------------------
        w_title_label = QLabel("Lust Weight Controls")
        w_title_label.setStyleSheet("color: white; font-size: 14px;")
        layout_main.addWidget(w_title_label)

        self.weight_sliders = {}

        for key in ["SDI", "NPL", "IEF", "IFR", "FLS", "DOP"]:
            sub_layout = QHBoxLayout()

            label = QLabel(key)
            label.setStyleSheet("color: white;")
            sub_layout.addWidget(label)

            s = QSlider(Qt.Orientation.Horizontal)
            s.setMinimum(0)
            s.setMaximum(100)
            s.setValue(int(self.weights[key] * 100))
            s.valueChanged.connect(lambda value, k=key: self._weight_change(k, value))
            self.weight_sliders[key] = s

            sub_layout.addWidget(s)

            layout_main.addLayout(sub_layout)

        # ----------------- LOG BOX -----------------------------------
        log_title_label = QLabel("Lust Timeline Log")
        log_title_label.setStyleSheet("color: white; font-size: 14px;")
        layout_main.addWidget(log_title_label)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet(
            "background-color: #0f131a; color: white;"
        )
        self.log_box.setFixedHeight(260)
        layout_main.addWidget(self.log_box)

        # ----------------- THRESHOLD SLIDER & LABEL ---------------
        t_label = QLabel("Ego Lock Threshold")
        t_label.setStyleSheet("color: white;")
        layout_main.addWidget(t_label)

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(100)
        self.threshold_value = 70
        self.threshold_slider.setValue(self.threshold_value)
        self.threshold_slider.valueChanged.connect(self._threshold_changed)
        layout_main.addWidget(self.threshold_slider)

        self.threshold_label = QLabel(f"Lock ≥ {self.threshold_value}")
        self.threshold_label.setStyleSheet("color: white;")
        layout_main.addWidget(self.threshold_label)

        # ----------------- BUTTONS ----------------------------------
        button_layout = QHBoxLayout()

        sim_btn = QPushButton("Simulate Lust Update")
        sim_btn.setStyleSheet("background-color: #4444ff; color: white;")
        sim_btn.clicked.connect(self._simulate_update)
        button_layout.addWidget(sim_btn)

        clr_btn = QPushButton("Clear Log")
        clr_btn.setStyleSheet("background-color: #333333; color: white;")
        clr_btn.clicked.connect(self._clear_log)
        button_layout.addWidget(clr_btn)

        layout_main.addLayout(button_layout)

    # ------------------------------------------------------------
    def _weight_change(self, key: str, value: int) -> None:
        """Update the weight for a specific lust sub‑channel."""
        self.weights[key] = value / 100.0

    # ------------------------------------------------------------
    def _threshold_changed(self) -> None:
        """Update the threshold lock percentage display."""
        self.threshold_value = self.threshold_slider.value()
        self.threshold_label.setText(f"Lock ≥ {self.threshold_value}")

    # ------------------------------------------------------------
    def _simulate_update(self) -> None:
        """Simulate an update to the lust values and weights."""
        # Update overall lust value
        self.lust_value += random.randint(3, 10)
        if self.lust_value > 100:
            self.lust_value = 100

        self.lust_bar.set_progress(self.lust_value / 100.0)
        self.lust_label.setText(f"Lust: {self.lust_value} / 100")

        # Update sub‑channels
        for key in ["SDI", "NPL", "IEF", "IFR", "FLS", "DOP"]:
            self.subscores[key] += random.randint(0, 8)
            if self.subscores[key] > 100:
                self.subscores[key] = 100

            bar_widget = self.sub_widgets[key]
            bar_widget.set_progress(self.subscores[key] / 100.0)

        # Weighted score preview (simplified)
        wsum = sum(self.weights.values()) or 1
        weighted_score = (
            sum(
                self.subscores[sub] * self.weights[sub]
                for sub in self.subscores
            )
            / wsum
        ) / 2.0
        ls_int = int(weighted_score)

        # Log entry
        t = datetime.now().strftime("%H:%M:%S")
        log_entry = (
            f"[{t}] LS={ls_int} | "
            f"SDI={self.subscores['SDI']} NPL={self.subscores['NPL']} "
            f"IEF={self.subscores['IEF']} IFR={self.subscores['IFR']} "
            f"FLS={self.subscores['FLS']} DOP={self.subscores['DOP']} "
            f"W={self.weights}\n"
        )
        self.log_box.append(log_entry)

    # ------------------------------------------------------------
    def _clear_log(self) -> None:
        """Clear the log box and reset all lust values."""
        self.log_box.clear()
        self.lust_value = 0

        for key in self.subscores:
            self.subscores[key] = 0
            bar_widget = self.sub_widgets[key]
            bar_widget.set_progress(0.0)

        self.lust_bar.set_progress(0.0)
        self.lust_label.setText("Lust: 0 / 100")


# ------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LustRegulator()
    window.show()
    sys.exit(app.exec())

