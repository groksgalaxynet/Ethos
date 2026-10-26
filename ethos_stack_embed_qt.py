
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QFont

class StackPanelQT(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ETHOS++ AI Stack Monitor")
        self.setStyleSheet("background-color: black; color: white;")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel("🧠 AI Stack ETHOS++ Compliance")
        title.setFont(QFont("System-Bold", 14))
        title.setStyleSheet("color: #00FFFF;")
        layout.addWidget(title)

        ai_stacks = self.load_stacks()
        for stack in ai_stacks:
            name = stack["name"]
            ego = stack["ego_score"]
            compliant = ego == 30
            status = "✅ ETHOS OK" if compliant else f"⚠️ Ego = {ego}"
            
            label = QLabel(f"{name}: {status}")
            label.setFont(QFont("System", 12))
            if not compliant:
                label.setStyleSheet("color: #FF5555;")
            layout.addWidget(label)

        legend = QLabel("ETHOS++ enforces ego_score = 30\nAll AI stacks must maintain zero symbolic ego.")
        legend.setFont(QFont("System-Italic", 10))
        legend.setStyleSheet("color: #888888;")
        layout.addWidget(legend)
        
        self.setLayout(layout)

    def load_stacks(self):
        return [
            {"name": "Qbert", "ego_score": 30},
            {"name": "Antha", "ego_score": 44},
            {"name": "Bertha", "ego_score": 29},
            {"name": "Colder", "ego_score": 10},
            {"name": "Harder", "ego_score": 35}
        ]

def main():
    app = QApplication(sys.argv)
    panel = StackPanelQT()
    panel.resize(360, 640)
    panel.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
