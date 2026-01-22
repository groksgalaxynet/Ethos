# agents sim.py – fixed imports + server integration

import sys
import random
import time
import csv
import json
import sqlite3
import datetime
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSlider,
    QTextEdit, QSizePolicy,
    QListWidget, QMessageBox, QFileDialog,
    QInputDialog
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal

# ------------------------------------------------------------------
# IMPORT Llama‑server helper (now including port_open!)
# ------------------------------------------------------------------
try:
    from llama_multiserver import LlamaServer, port_open   # <-- added port_open
except Exception as e:  # pragma: no cover – handled by UI warning earlier
    print("Could not import LlamaServer / port_open:", e)
    LlamaServer = None
    port_open = lambda p: False

# ------------------------------------------------------------------
# TRAITS
# ------------------------------------------------------------------
traits_keys = [
    'love', 'greed', 'vanity', 'gluttony',
    'promiscuous', 'hateful', 'trustworthy',
    'envious', 'valor_kind'
]

traits_labels = [
    'Love', 'Greed', 'Vanity', 'Gluttony',
    'Promiscuous', 'Hateful', 'Trustworthy',
    'Envious', 'Valor / Kind'
]

# ------------------------------------------------------------------
# THREAD → UI SIGNAL BRIDGE
# ------------------------------------------------------------------
class UISignals(QObject):
    update_logs = pyqtSignal()
    repaint_grid = pyqtSignal()


# ------------------------------------------------------------------
# AGENT
# ------------------------------------------------------------------
class Agent:
    def __init__(self, traits, pos, icon='🤖', color='#00ff99'):
        self.traits = traits      # dict of 0‑1 values
        self.pos = pos            # (x, y)
        self.icon = icon
        self.color = color


# ------------------------------------------------------------------
# MAIN WINDOW
# ------------------------------------------------------------------
class EthosSandbox(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ethos++ AI Agent Sandbox")
        self.resize(1000, 900)

        self.signals = UISignals()
        self.signals.update_logs.connect(self.update_logs_ui)
        self.signals.repaint_grid.connect(self.repaint_grid)

        # Simulation state
        self.grid_size = 12
        self.running = False
        self.agents: list[Agent] = []          # normal agents + server agents

        # Llama‑server state
        self.servers: list[LlamaServer] = []
        self.server_agents: dict[LlamaServer, Agent] = {}

        # Statistics / logs
        self.total_interactions = 0
        self.coops = 0
        self.conflicts = 0
        self.independents = 0
        self.log_lines = []

        self.dark_mode = False          # default light theme

        self.build_ui()

    # ------------------------------------------------------------------
    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        # ------------------- TOP CONTROLS ---------------------------------
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)

        # ---- Trait sliders ------------------------------------------------
        self.sliders = {}
        for key, label in zip(traits_keys, traits_labels):
            row = QHBoxLayout()

            lbl = QLabel(label)
            lbl.setFixedWidth(130)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(100)
            slider.setValue(50)

            value_lbl = QLabel("0.50")
            value_lbl.setFixedWidth(50)

            slider.valueChanged.connect(
                lambda v, l=value_lbl: l.setText(f"{v/100:.2f}")
            )

            self.sliders[key] = slider

            row.addWidget(lbl)
            row.addWidget(slider)
            row.addWidget(value_lbl)
            controls_layout.addLayout(row)

        # ---- Add / Play buttons -----------------------------------------
        btn_row = QHBoxLayout()

        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.toggle_play)

        add_btn = QPushButton("Add Agent")
        add_btn.clicked.connect(self.add_agent)

        btn_row.addWidget(add_btn)
        btn_row.addWidget(self.play_btn)
        controls_layout.addLayout(btn_row)

        # ---- Persistence buttons -----------------------------------------
        pers_row = QHBoxLayout()
        db_btn = QPushButton("Save to DB")
        db_btn.clicked.connect(self.save_to_db)
        load_db_btn = QPushButton("Load from DB")
        load_db_btn.clicked.connect(self.load_from_db)

        json_btn = QPushButton("Save JSON")
        json_btn.clicked.connect(self.save_to_json)
        load_json_btn = QPushButton("Load JSON")
        load_json_btn.clicked.connect(self.load_from_json)

        csv_btn = QPushButton("Save CSV")
        csv_btn.clicked.connect(self.save_to_csv)
        load_csv_btn = QPushButton("Load CSV")
        load_csv_btn.clicked.connect(self.load_from_csv)

        pers_row.addWidget(db_btn)
        pers_row.addWidget(load_db_btn)
        pers_row.addWidget(json_btn)
        pers_row.addWidget(load_json_btn)
        pers_row.addWidget(csv_btn)
        pers_row.addWidget(load_csv_btn)

        controls_layout.addLayout(pers_row)

        # ---- Dark mode toggle --------------------------------------------
        dark_toggle = QPushButton("Dark Mode")
        dark_toggle.setCheckable(True)
        dark_toggle.clicked.connect(self.toggle_dark_mode)
        controls_layout.addWidget(dark_toggle)

        layout.addWidget(controls)

        # ------------------- SERVER CONTROLS --------------------------------
        srv_widget = QWidget()
        srv_layout = QVBoxLayout(srv_widget)
        srv_layout.setSpacing(5)

        srv_lbl = QLabel("Servers")
        srv_lbl.setStyleSheet("font-weight: bold; font-size: 16px;")
        srv_layout.addWidget(srv_lbl)

        self.srv_list = QListWidget()
        srv_layout.addWidget(self.srv_list, stretch=1)

        # Server buttons
        sb_row = QHBoxLayout()
        add_srv_btn = QPushButton("➕ Add")
        add_srv_btn.clicked.connect(self.add_server)
        start_srv_btn = QPushButton("▶ Start")
        start_srv_btn.clicked.connect(self.start_server)
        stop_srv_btn = QPushButton("⏹ Stop")
        stop_srv_btn.clicked.connect(self.stop_server)
        kill_srv_btn = QPushButton("☠ Kill")
        kill_srv_btn.clicked.connect(self.kill_server)
        health_srv_btn = QPushButton("🔍 Health")
        health_srv_btn.clicked.connect(self.check_server)

        sb_row.addWidget(add_srv_btn)
        sb_row.addWidget(start_srv_btn)
        sb_row.addWidget(stop_srv_btn)
        sb_row.addWidget(kill_srv_btn)
        sb_row.addWidget(health_srv_btn)

        srv_layout.addLayout(sb_row)

        layout.addWidget(srv_widget, stretch=1)

        # ------------------- GRID -------------------------------------------
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(2)
        layout.addWidget(self.grid_widget, stretch=3)

        # ------------------- LOGS --------------------------------------------
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        layout.addWidget(self.logs, stretch=1)

    # ------------------------------------------------------------------
    def toggle_dark_mode(self, checked: bool):
        self.dark_mode = checked
        if checked:
            dark_style = """
                QWidget { background:#222; color:#eee; }
                QPushButton { background:#444; color:#eee; border-radius:4px; padding:4px 8px;}
                QSlider::groove:horizontal { background:#555; height:6px; border-radius:3px; }
                QSlider::handle:horizontal { background:#bbb; width:12px; margin-top:-5px; }
                QListWidget { background:#333; color:#ddd;}
            """
            self.setStyleSheet(dark_style)
        else:
            self.setStyleSheet("")  # reset to default
        # Force redraw of grid/labels
        self.repaint_grid()
        self.update_logs_ui()

    # ------------------------------------------------------------------
    def toggle_play(self):
        self.running = not self.running
        self.play_btn.setText("Pause" if self.running else "Play")

        if self.running:
            threading.Thread(target=self.simulation_loop, daemon=True).start()

    def simulation_loop(self):
        while self.running:
            self.move_agents()
            self.check_interactions()
            self.signals.update_logs.emit()
            self.signals.repaint_grid.emit()
            time.sleep(0.8)

    # ------------------------------------------------------------------
    def add_agent(self):
        traits = {k: s.value() / 100 for k, s in self.sliders.items()}
        pos = (
            random.randint(0, self.grid_size - 1),
            random.randint(0, self.grid_size - 1)
        )
        self.agents.append(Agent(traits, pos))
        self.signals.repaint_grid.emit()
        self.signals.update_logs.emit()

    def move_agents(self):
        for a in self.agents:
            dx, dy = random.choice([(0,1),(0,-1),(1,0),(-1,0)])
            x = max(0, min(self.grid_size - 1, a.pos[0] + dx))
            y = max(0, min(self.grid_size - 1, a.pos[1] + dy))
            a.pos = (x, y)

    # ------------------------------------------------------------------
    def check_interactions(self):
        positions = {}
        for a in self.agents:
            positions.setdefault(a.pos, []).append(a)

        for group in positions.values():
            if len(group) > 1:
                self.resolve_interaction(group)

    def resolve_interaction(self, group):
        self.total_interactions += 1
        now = datetime.datetime.now().strftime('%H:%M:%S')

        for i in range(len(group)):
            for j in range(i+1, len(group)):
                a1, a2 = group[i], group[j]

                trust = (a1.traits['trustworthy'] + a2.traits['trustworthy']) / 2
                hate = (a1.traits['hateful'] + a2.traits['hateful']) / 2
                love = (a1.traits['love'] + a2.traits['love']) / 2
                greed = (a1.traits['greed'] + a2.traits['greed']) / 2
                valor = (a1.traits['valor_kind'] + a2.traits['valor_kind']) / 2

                score = trust + love + valor - hate - greed

                if score > 0.7:
                    self.coops += 1
                    self.log_lines.append(f"{now} Coop @ {a1.pos}")
                elif score < 0.3:
                    self.conflicts += 1
                    self.log_lines.append(f"{now} Conflict @ {a1.pos}")
                else:
                    self.independents += 1
                    self.log_lines.append(f"{now} Independent @ {a1.pos}")

        self.log_lines = self.log_lines[-50:]

    # ------------------------------------------------------------------
    def repaint_grid(self):
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        for a in self.agents:
            lbl = QLabel(a.icon)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{a.color}; font-size:24px;")
            self.grid_layout.addWidget(lbl, a.pos[1], a.pos[0])

    def update_logs_ui(self):
        pop = len(self.agents)
        text = (
            f"Population: {pop}\n"
            f"Interactions: {self.total_interactions}\n"
            f"Coop: {self.coops}\n"
            f"Conflict: {self.conflicts}\n"
            f"Independent: {self.independents}\n\n"
            "Recent:\n" + "\n".join(self.log_lines[-10:])
        )
        self.logs.setPlainText(text)
        self.logs.verticalScrollBar().setValue(
            self.logs.verticalScrollBar().maximum()
        )

    # ------------------------------------------------------------------
    def _db_path(self) -> Path:
        return Path.cwd() / "agents.db"

    def save_to_db(self):
        if not self.agents:
            QMessageBox.warning(self, "No data", "There are no agents to save.")
            return

        conn = sqlite3.connect(str(self._db_path()))
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                traits TEXT,
                pos_x INTEGER,
                pos_y INTEGER
            )
        """)
        # wipe existing rows for simplicity
        cur.execute("DELETE FROM agents")

        for a in self.agents:
            cur.execute(
                "INSERT INTO agents (traits, pos_x, pos_y) VALUES (?, ?, ?)",
                (json.dumps(a.traits), a.pos[0], a.pos[1])
            )
        conn.commit()
        conn.close()
        QMessageBox.information(self, "Saved", f"Agents saved to {self._db_path()}")

    def load_from_db(self):
        if not self._db_path().exists():
            QMessageBox.warning(self, "Missing file", "No database found.")
            return

        conn = sqlite3.connect(str(self._db_path()))
        cur = conn.cursor()
        cur.execute("SELECT traits, pos_x, pos_y FROM agents")
        rows = cur.fetchall()

        self.agents.clear()
        for tjson, x, y in rows:
            self.agents.append(Agent(json.loads(tjson), (x, y)))

        conn.close()
        self.signals.repaint_grid.emit()
        self.signals.update_logs.emit()

    # ------------------------------------------------------------------
    def save_to_json(self):
        if not self.agents:
            QMessageBox.warning(self, "No data", "There are no agents to save.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Agents as JSON", "", "JSON Files (*.json)"
        )
        if not path:
            return

        with open(path, 'w', encoding='utf-8') as f:
            json.dump([
                {"traits": a.traits, "pos": a.pos}
                for a in self.agents
            ], f, indent=2)
        QMessageBox.information(self, "Saved", f"Agents saved to {path}")

    def load_from_json(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Agents from JSON", "", "JSON Files (*.json)"
        )
        if not path:
            return

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.agents.clear()
        for rec in data:
            self.agents.append(Agent(rec["traits"], tuple(rec["pos"])))

        self.signals.repaint_grid.emit()
        self.signals.update_logs.emit()

    # ------------------------------------------------------------------
    def save_to_csv(self):
        if not self.agents:
            QMessageBox.warning(self, "No data", "There are no agents to save.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Agents as CSV", "", "CSV Files (*.csv)"
        )
        if not path:
            return

        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # header: trait keys + x,y
            writer.writerow(traits_keys + ["x", "y"])
            for a in self.agents:
                row = [a.traits[k] for k in traits_keys]
                row.extend(a.pos)
                writer.writerow(row)

        QMessageBox.information(self, "Saved", f"Agents saved to {path}")

    def load_from_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Agents from CSV", "", "CSV Files (*.csv)"
        )
        if not path:
            return

        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.agents.clear()
            for rec in reader:
                traits = {k: float(rec[k]) for k in traits_keys}
                x = int(rec["x"])
                y = int(rec["y"])
                self.agents.append(Agent(traits, (x, y)))

        self.signals.repaint_grid.emit()
        self.signals.update_logs.emit()

    # ------------------------------------------------------------------
    def add_server(self):
        if not LlamaServer:   # pragma: no cover – handled by UI warning earlier
            QMessageBox.warning(self, "Missing", "LlamaServer class could not be imported.")
            return

        binary = QFileDialog.getOpenFileName(
            self, "Select llama-server binary"
        )[0]
        if not binary or not Path(binary).exists():
            QMessageBox.warning(self, "Invalid binary", "Choose a valid binary file")
            return

        model = QFileDialog.getOpenFileName(
            self, "Select .gguf model", "", "*.gguf"
        )[0]
        if not model or not Path(model).exists():
            QMessageBox.warning(self, "Invalid model", "Choose a valid .gguf file")
            return

        port, ok = QInputDialog.getInt(self, "Port",
                                       "Enter port (1000‑65535)", 8000,
                                       1000, 65535)
        if not ok:
            return
        ctx, ok = QInputDialog.getInt(self, "Context Size",
                                      "Enter ctx size (512‑32768)", 4096,
                                      512, 32768)
        if not ok:
            return

        srv = LlamaServer(binary, model, port, ctx)
        self.servers.append(srv)
        self.srv_list.addItem(f"{Path(model).name} | :{port} | ctx={ctx}")
        self.log_msg(f"Added server :{port}")

    def selected_server(self):
        idx = self.srv_list.currentRow()
        if idx < 0:
            return None
        return self.servers[idx]

    def start_server(self):
        srv = self.selected_server()
        if not srv:
            return

        if srv.is_running():
            self.log_msg("Server already running")
            return

        if port_open(srv.port):
            self.log_msg(f"Port {srv.port} already in use", bad=True)
            return

        cmd = [
            srv.binary,
            "--model", srv.model,
            "--port", str(srv.port),
            "--host", "127.0.0.1",
            "--ctx-size", str(srv.ctx)
        ]

        self.log_msg("Starting:\n" + " ".join(cmd))

        try:
            srv.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True
            )
        except Exception as e:
            self.log_msg(str(e), bad=True)
            return

        # ------------------------------------------------------------------
        # 1️⃣ Create a visual agent that represents this server
        # ------------------------------------------------------------------
        default_traits = {k: 0.0 for k in traits_keys}
        pos = (
            random.randint(0, self.grid_size - 1),
            random.randint(0, self.grid_size - 1)
        )
        srv_agent = Agent(default_traits, pos,
                          icon='🦙', color='#ffcc00')
        self.agents.append(srv_agent)
        self.server_agents[srv] = srv_agent
        self.signals.repaint_grid.emit()
        self.log_msg("Server agent added to the grid")

        threading.Thread(target=self.stream_output, args=(srv,), daemon=True).start()

    def stop_server(self):
        srv = self.selected_server()
        if srv and srv.is_running():
            srv.process.terminate()
            self.log_msg("Server stopped")
            self._remove_server_agent(srv)

    def kill_server(self):
        srv = self.selected_server()
        if srv and srv.is_running():
            srv.process.kill()
            self.log_msg("Server killed", bad=True)
            self._remove_server_agent(srv)

    def check_server(self):
        srv = self.selected_server()
        if not srv:
            return

        if port_open(srv.port):
            self.log_msg(f"Server :{srv.port} ONLINE", good=True)
        else:
            self.log_msg(f"Server :{srv.port} OFFLINE", bad=True)

    # ------------------------------------------------------------------
    def _remove_server_agent(self, srv: LlamaServer):
        if srv in self.server_agents:
            agent = self.server_agents.pop(srv)
            if agent in self.agents:
                self.agents.remove(agent)
                self.signals.repaint_grid.emit()
                self.log_msg("Removed server agent from grid")

    # ------------------------------------------------------------------
    def stream_output(self, srv: LlamaServer):
        for line in srv.process.stdout:
            self.log_msg(line.rstrip())

    def log_msg(self, msg, good=False, bad=False):
        prefix = "• "
        if good: prefix = "✔ "
        if bad:  prefix = "✖ "
        self.logs.append(prefix + msg)
        self.logs.ensureCursorVisible()


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = EthosSandbox()
    win.show()
    sys.exit(app.exec())
