"""Existing ETHOS desktop shell for verified read-only component access."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Sequence

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStyleFactory,
    QTabWidget, QVBoxLayout, QWidget,
)

from ETHOS_Scar_Manager import ScarGUI
from EnvyRegulatorGUI import EnvyRegulator
from GreedRegulatorGUI import GreedRegulator
from PrideRegulatorGUI import PrideRegulator
from artifact_observer import ArtifactObservation, ArtifactSpec, observe_artifacts
from regulator_gui_adapter import RegulatorGuiPresentation, load_latest_presentations
from scar_gui_adapter import ScarGuiAdapter


DEFAULT_EVIDENCE_PATH = Path(__file__).with_name("evidence") / "proposal_gate.jsonl"
_BASELINE_EXPECTED_HASH = "e902fe4c973c826b2ee5e219f8235e7b056b1a33f65b44dadbfcd839d69828fb"


def default_integrity_specs() -> tuple[ArtifactSpec, ...]:
    """Return the fixed small static integrity set; this never inventories directories."""
    root = Path(__file__).parent
    return (
        ArtifactSpec("Evaluation Baseline", root / "evaluation_baseline.json", "evaluation-baseline", _BASELINE_EXPECTED_HASH),
        ArtifactSpec("Greed Definition", root / "ETHOS++_—_Greed_Regulation_Module.json"),
        ArtifactSpec("Pride Definition", root / "ETHOS++_—_Pride_Regulation_Module.json"),
        ArtifactSpec("Envy Definition", root / "ETHOS++_—_Envy_Regulation_Module.json"),
    )


class MainWindow(QMainWindow):
    """Navigation shell only; it has no decision, persistence, or controller authority."""

    def __init__(
        self,
        evidence_path: str | Path = DEFAULT_EVIDENCE_PATH,
        history_path: str | Path | None = None,
        integrity_specs: Sequence[ArtifactSpec] | None = None,
    ) -> None:
        super().__init__()
        self.evidence_path = Path(evidence_path)
        self.history_path = Path(history_path) if history_path is not None else self.evidence_path.with_suffix(".violations.db")
        self.integrity_specs = tuple(integrity_specs or default_integrity_specs())
        self.integrity_observations: list[ArtifactObservation] = []
        self.child_windows: dict[str, QWidget] = {}
        self.setWindowTitle("ETHOS++ Desktop — Verified Read-Only Components")
        self.setGeometry(100, 100, 1100, 900)
        self.apply_dark_theme()
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(self._current_integrations_tab(), "Current Integrations")
        self.tabs.addTab(self._legacy_status_tab(), "Legacy / Unwired")

    def _current_integrations_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("Verified current-runtime components — inspection/display only."))
        self.integration_status = QLabel()
        self.integration_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.integration_status)
        self._refresh_status()
        for label, key in (
            ("Open Scar Manager (read-only)", "scar"),
            ("Open Greed Analyzer Display", "greed"),
            ("Open Pride Analyzer Display", "pride"),
            ("Open Envy Analyzer Display", "envy"),
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, component=key: self.open_component(component))
            layout.addWidget(button)
        refresh = QPushButton("Refresh Stored Regulator Evidence")
        refresh.clicked.connect(self._refresh_status)
        layout.addWidget(refresh)
        layout.addWidget(QLabel("Artifact Integrity — informational, read-only"))
        self.integrity_status = QLabel()
        self.integrity_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.integrity_status.setWordWrap(True)
        layout.addWidget(self.integrity_status)
        integrity_refresh = QPushButton("Refresh Integrity")
        integrity_refresh.clicked.connect(self._refresh_integrity)
        layout.addWidget(integrity_refresh)
        self._refresh_integrity()
        layout.addStretch()
        return panel

    @staticmethod
    def _legacy_status_tab() -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel(
            "Lust — NOT WIRED\nSloth — NOT WIRED\nWrath — NOT WIRED\nGluttony — NOT WIRED\n\n"
            "Controller aggregate — NOT AUTHORITATIVE (not launched by this shell).\n"
            "Boundary Monitor, AI Lounge, and Notary — not current-runtime integrations."
        ))
        layout.addStretch()
        return panel

    def _refresh_status(self) -> None:
        presentations = load_latest_presentations(self.evidence_path)
        evidence_status = ", ".join(
            f"{name.title()} evidence {'loaded' if value.available else 'unavailable'}"
            for name, value in presentations.items()
        )
        self.integration_status.setText(
            "Greed — ACTIVE\nPride — ACTIVE\nEnvy — ACTIVE\n"
            "Scar/history inspection — ACTIVE\n"
            "Lust — NOT WIRED\nSloth — NOT WIRED\nWrath — NOT WIRED\nGluttony — NOT WIRED\n"
            "Controller aggregate — NOT AUTHORITATIVE\n\n"
            f"Stored display evidence: {evidence_status}."
        )

    def _refresh_integrity(self) -> None:
        """Refresh selected observer results only; hashes are never accepted or persisted here."""
        self.integrity_observations = observe_artifacts(self.integrity_specs)
        lines = []
        for item in self.integrity_observations:
            lines.append(f"{item.identity} — {item.status}")
            if item.status in {"CHANGED", "UNAVAILABLE"}:
                lines.extend((
                    f"  expected: {item.expected_hash or 'unavailable'}",
                    f"  observed: {item.observed_hash or 'unavailable'}",
                    f"  detail: {item.diagnostic}",
                ))
        self.integrity_status.setText("\n".join(lines))

    def open_component(self, component: str) -> QWidget:
        """Show one retained verified child; only stored evidence is read for regulator displays."""
        existing = self.child_windows.get(component)
        if existing is not None:
            existing.show()
            existing.raise_()
            existing.activateWindow()
            return existing
        factory = self._component_factory(component)
        window = factory()
        self.child_windows[component] = window
        window.show()
        return window

    def _component_factory(self, component: str) -> Callable[[], QWidget]:
        if component == "scar":
            return lambda: ScarGUI(ScarGuiAdapter(self.history_path))
        presentations = load_latest_presentations(self.evidence_path)
        factories: dict[str, Callable[[], QWidget]] = {
            "greed": lambda: GreedRegulator(presentations["greed"]),
            "pride": lambda: PrideRegulator(presentations["pride"]),
            "envy": lambda: EnvyRegulator(presentations["envy"]),
        }
        if component not in factories:
            raise ValueError(f"Unsupported component: {component}")
        return factories[component]

    def apply_dark_theme(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        app.setStyle(QStyleFactory.create("Fusion"))
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#0c0f1a"))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor("#1a1d2e"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#0c0f1a"))
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor("#2d2f3b"))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#39ffb0"))
        app.setPalette(palette)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
