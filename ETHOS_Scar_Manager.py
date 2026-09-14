# ETHOS++ Scar Manager — current-runtime inspection mode (PyQt6)
"""Existing Scar Manager layout, adapted to read current ETHOS history only."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QPushButton, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from scar_gui_adapter import ScarGuiAdapter, ScarGuiRow


class ScarGUI(QMainWindow):
    """The legacy Scar Manager presentation with no authority to mutate runtime state."""

    def __init__(self, adapter: ScarGuiAdapter | None = None) -> None:
        super().__init__()
        self.adapter = adapter or ScarGuiAdapter()
        self.rows: list[ScarGuiRow] = []
        self.selected_row: ScarGuiRow | None = None
        self.setWindowTitle("ETHOS++ Scar Manager — Current History (Read-Only)")
        self.resize(900, 700)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.addWidget(QLabel("Current ETHOS consequence history — inspection mode; no runtime mutation."))

        btn_row1 = QHBoxLayout()
        btn_row2 = QHBoxLayout()
        self.btn_minor = QPushButton("New Scar (Minor) — disabled")
        self.btn_major = QPushButton("New Scar (Major) — disabled")
        self.btn_import = QPushButton("Refresh Current History")
        self.btn_forgive = QPushButton("Forgive / Remove (2 sig) — disabled")
        self.btn_export = QPushButton("Export CSV — disabled")
        self.btn_exit = QPushButton("Exit")
        for button in (self.btn_minor, self.btn_major, self.btn_forgive, self.btn_export):
            button.setEnabled(False)
            button.setToolTip("Disabled in current-runtime inspection mode; this GUI cannot change ETHOS persistence.")
        self.btn_import.setToolTip("Read the existing current ETHOS history again without changing it.")
        btn_row1.addWidget(self.btn_minor)
        btn_row1.addWidget(self.btn_major)
        btn_row2.addWidget(self.btn_import)
        btn_row2.addWidget(self.btn_forgive)
        btn_row2.addWidget(self.btn_export)
        btn_row2.addWidget(self.btn_exit)
        layout.addLayout(btn_row1)
        layout.addLayout(btn_row2)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "State / Scar", "Policy / Reason", "Occurrence"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.status = QTextEdit()
        self.status.setReadOnly(True)
        self.status.setFixedHeight(160)
        layout.addWidget(self.status)

        self.btn_import.clicked.connect(self.reload)
        self.btn_exit.clicked.connect(self.close)
        self.table.itemSelectionChanged.connect(self.on_select)
        self.reload()

    def reload(self) -> None:
        self.rows, summary, error = self.adapter.load()
        self.selected_row = None
        self.table.clearContents()
        self.table.setRowCount(len(self.rows))
        for index, row in enumerate(self.rows):
            scar_text = row.consequence_state
            if row.scar_id is not None:
                scar_text += f" / {row.scar_severity or 'scar'} #{row.scar_id}"
            reason = row.reason or row.scar_reason or row.policy_family
            for column, value in enumerate((row.violation_id, scar_text, reason, str(row.occurrence))):
                self.table.setItem(index, column, QTableWidgetItem(value))
        if error is not None:
            self.status.setText("Current ETHOS history unavailable.\n" + error)
            return
        self.status.setText(
            "Current ETHOS history loaded (read-only).\n"
            f"Stored violations: {summary.get('total_stored_violations', 0)}\n"
            f"Records linked to scars: {summary.get('count_with_scars', 0)}\n"
            "Select a row to inspect persisted evidence and scar metadata."
        )

    def on_select(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return
        row_index = selected[0].row()
        if 0 <= row_index < len(self.rows):
            self.selected_row = self.rows[row_index]
            self.status.setText(self.adapter.details(self.selected_row))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScarGUI()
    window.show()
    sys.exit(app.exec())
