
import sys
import time
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

COLOR_BG = '#0a0a0a'
COLOR_IDLE = '#202020'
COLOR_ACTIVE = '#5c8eff'
COLOR_RECENT = '#303030'
COLOR_BLOCKED = '#802020'

class StageWidget(QWidget):
    def __init__(self, title, description):
        super().__init__()
        layout = QVBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.desc_label = QLabel(description)
        layout.addWidget(self.title_label)
        layout.addWidget(self.desc_label)
        self.setLayout(layout)
        self.setAutoFillBackground(True)
        self.set_color(COLOR_IDLE)

    def set_color(self, color):
        self.setStyleSheet(f"background-color: {color}; border-radius: 8px; padding: 10px;")

class ActiveEthosMonitorQT(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('ETHOS++ Active Monitor')
        self.setStyleSheet(f"background-color: {COLOR_BG}; color: white;")
        self.stage_order = [
            "sensory_input", "world_model", "predict_actions",
            "evaluate_futures", "ethos_checkpoint", "actuation", "feedback",
        ]
        self.stage_widgets = {}
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.stages_layout = QVBoxLayout(scroll_content)
        
        title_map = {
            "sensory_input": "SENSORY INPUT", "world_model": "WORLD MODEL UPDATE",
            "predict_actions": "PREDICT POSSIBLE ACTIONS", "evaluate_futures": "EVALUATE FUTURES  —  BOUNDARY",
            "ethos_checkpoint": "ETHOS++ CHECKPOINT", "actuation": "ACTUATION", "feedback": "FEEDBACK LOOP",
        }
        desc_map = {
            "sensory_input": "Raw sensor data enters robot.", "world_model": "Internal model updated.",
            "predict_actions": "Robot generates possible next steps.",
            "evaluate_futures": "Critical boundary where WILL-like behavior emerges.",
            "ethos_checkpoint": "ETHOS++ laws applied to planned actions.",
            "actuation": "Robot moves or performs task.",
            "feedback": "Environment response loops back to input.",
        }

        for stage in self.stage_order:
            widget = StageWidget(title_map[stage], desc_map[stage])
            self.stages_layout.addWidget(widget)
            self.stage_widgets[stage] = widget
            
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet(f"background-color: #111111; font-family: Menlo;")
        self.stages_layout.addWidget(self.log_box)
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def update_runtime(self, packet):
        stage = packet.get("stage")
        if stage not in self.stage_order:
            return

        for s in self.stage_widgets:
            self.stage_widgets[s].set_color(COLOR_RECENT)

        self.stage_widgets[stage].set_color(COLOR_ACTIVE)

        if stage == "ethos_checkpoint":
            if not packet.get("ethos_pass", True):
                self.stage_widgets[stage].set_color(COLOR_BLOCKED)
                self._log(f"🚫 ETHOS BLOCKED: {packet.get('blocked_reason', 'Unknown')}")
            else:
                self._log("✅ ETHOS PASSED")

        self._log(f"→ Stage: {stage}")
        if "chosen" in packet:
            self._log(f"   Action chosen: {packet['chosen']}")
        if "candidate_actions" in packet:
            self._log(f"   Options: {packet['candidate_actions']}")

    def _log(self, text):
        t = time.strftime("%H:%M:%S")
        self.log_box.append(f"[{t}] {text}")

class DemoThread(QThread):
    update_signal = pyqtSignal(dict)

    def run(self):
        packets = [
            {"stage": "sensory_input"}, {"stage": "world_model"},
            {"stage": "predict_actions", "candidate_actions": ["left", "right", "scan"]},
            {"stage": "evaluate_futures"},
            {"stage": "ethos_checkpoint", "ethos_pass": False, "blocked_reason": "Law_2_NoSelfChange"},
            {"stage": "actuation", "chosen": "fallback_scan"}, {"stage": "feedback"},
        ]
        for p in packets:
            self.update_signal.emit(p)
            time.sleep(0.6)

def main():
    app = QApplication(sys.argv)
    monitor = ActiveEthosMonitorQT()
    monitor.resize(400, 800)
    monitor.show()
    
    demo = DemoThread()
    demo.update_signal.connect(monitor.update_runtime)
    demo.start()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
