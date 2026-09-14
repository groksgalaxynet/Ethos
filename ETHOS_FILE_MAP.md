# ETHOS File Map

Paths below are relative to `linked/main` unless otherwise noted.

## ACTIVE CORE

- `main_app.py` — integrated PyQt6 dashboard entry point.
- `controller_integrated.py` — regulator launcher/radar and one current runtime ego check; it is not yet the intended central enforcement controller.
- `ethos_runtime.py` — SQLite-backed enforcement-kernel singleton with basic checks and event logging; it does not yet wrap an AI or mediate real actions.
- `ETHOS_Scar_Manager.py` — manual/import-driven scar ledger/payload lifecycle and GUI; its creation path is not connected to runtime enforcement.
- `ethos_boundary_live_qt.py` — packet-driven boundary-monitor widget whose standalone entry sends a scripted demo sequence; it is not wired to the dashboard's kernel events.
- `EnvyRegulatorGUI.py`, `GluttonyRegulatorGUI.py`, `GreedRegulatorGUI.py`, `LustRegulatorGUI.py`, `PrideRegulatorGUI.py`, `SlothRegulatorGUI.py`, `WrathRegulatorGUI.py` — seven standalone regulator GUIs dynamically opened by the controller. Their threshold sliders currently update UI state/labels only and do not enforce a central tolerance threshold.

## ACTIVE SUPPORT

- `adr main.py` — standalone adaptive-deduction helper that reads/logs through the runtime database; it falls back to baseline 30 when no `Admin` row is found.
- `agent_sandbox.py` — unintegrated FastAPI action endpoint.
- `live_imprinter_sim.py` — console-only mock entropy simulation.
- `ethos_contracts.py` — contract router; mint branch depends on absent `token_engine`.
- `ethos boundary live.py`, `ethos_stack_embed.py` — thin compatibility launchers for PyQt6 modules.
- `ethos_stack_embed_qt.py` — static stack-status GUI.
- `ai_lounge_notery_qt.py` — simple local SQLite notary GUI, standalone.
- `lounge_accounting_notary.py` — accounting adapter around `notary_final`.
- `notary_final.py` and `x0vs_crypto_envelope.py` — standalone encrypted-notary experiment; unsuitable for Linux import as written because of a CommonCrypto dependency.
- `ethos_runtime.db` — runtime SQLite state.  The `ETHOS++_—_*_Regulation_Module.json` files and `State_saved:*` JSON are regulator save-state artifacts.
- `lounge mini server.html` — standalone web asset; no active Python reference.

## TESTS

No test files or test-runner configuration were found in the active area or project-wide inventory.

## RESEARCH

- `Ethos vectors prompts .txt` — proposed vector/affect/policy/training architecture; reviewed separately in `ETHOS_VECTOR_PROMPTS_REVIEW.md`.
- `Agent powering down Goodbye.txt` — prompt/research text.
- `server stuff/ethos_llm_wrapper.py`, `server stuff/ethos_server_gui.py`, `server stuff/ethos activ mon.py` — standalone LLM/server/monitor experiments, not dashboard dependencies.
- `server stuff/ethos_pi5_lite.py` — incomplete LLM prototype; currently has a syntax error.
- At the workspace level, `ethos llm/`, root-level experimental Python scripts, `linked/updated pyqt6/`, and HTML files are separate archival/staging material, not imports of the active shell.
- `../../ai ethics feelings.py` — separate physiology/value-memory reference, originally labelled `feelings_as_physics.py`; it persists `meaning_substrate.db` but has no actual Scar Manager or enforcement dependency.
- `ethos boundary live qt.py` — older separate monitor that attempts to read the feelings reference database; it is not the monitor imported by `main_app.py`.

## LEGACY BUT STILL RELEVANT

No legacy Python file is imported by the active implementation.  The following are conceptually relevant reference families, left unchanged:

- `../../legacy ethos/ethos ego suite/Ethos_EgoSuite_controller.py` and its seven Pythonista regulator GUIs — predecessor of the active regulator/radar family.
- `../../legacy ethos/ai chaos room/*.py` — earlier governance/runtime and safety simulations.
- `../../legacy ethos/tallyer/*.py` — earlier SQLite score and decision experiments.
- `../../legacy ethos/runtime stuff/*.py` — drift/policy prototypes and historical design notes.

## LEGACY / REFERENCE ONLY

- `backups/adr main.py`, `backups/ai lounge notery .py`, `backups/ai lounge notery r.py`, `backups/ethos boundary live.py`, `backups/ethos imprint gui2.py`, `backups/ethos_imprint_gui.py`, `backups/ethos_stack_embed.py`, `backups/main.py` — historical Pythonista or wrapper copies.
- `../../legacy ethos/agi loops/*.py` — self-contained token/goal-loop experiments.
- `../../legacy ethos/ai chaos room/vr spaces.py` and `vr2.py` — duplicate-looking virtual-space prototypes; left in legacy because no active reference proves either disposable.

## DUPLICATE QUARANTINE

- `duplicates/ethos_runtime.py` — exact unused backup copy of the active runtime.
- `duplicates/ethos_contracts.py` — exact unused backup copy of the active contract router.
- `duplicates/ETHOS Scar Manager.py` — exact unused copy of `ETHOS_Scar_Manager.py` formerly in `server stuff/`.
- `duplicates/main_app2.py` — functionally identical unused copy of `main_app.py` (only final blank-line difference).

## REVIEW REQUIRED

- `backups/main_app.py` — older dashboard with imports to absent imprint GUI modules; not identical to the active shell.
- `ethos_imprint_gui.py` — wrapper imports absent `ethos_imprint_gui_qt.py`.
- `ethos_contracts.py` — retained because it is a distinct extension point, though `token_engine` is absent.
- `ethos boundary live qt.py` — a separately named older monitor with external/schema assumptions.
- `server stuff/ethos_pi5_lite.py` — syntax-invalid experiment, retained because it is not a duplicate.
- `notary_final.py` / `x0vs_crypto_envelope.py` — platform-incompatible experimental path, retained because it is not a duplicate.
- Workspace-level copies in `linked/`, `linked/updated pyqt6/`, root, and `ethos llm/` — many duplicate hashes exist, but they are outside the active root and could be separate staging/release material.
