"""Research-only characterization of ControllerSnapshot using benchmark fixtures."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ethos_controller import ControllerSnapshot
from ethos_proposal_gate import EthosProposalGate, JsonlEvidenceStore
from regulator_benchmark import cases

ROOT = Path(__file__).with_name("evidence")
SELECTED = ("g-none", "g-combo", "p-both", "e-both", "p-mixed-other", "g-quote", "g-key")

def run() -> dict[str, object]:
    fixtures = {item["case_id"]: item for item in cases()}
    selected = [fixtures[item] for item in SELECTED]
    selected.append({"case_id": "controller-composed-multi-violation", "category": "mixed-multiple-regulator-violation", "proposal": {**fixtures["g-mixed-p"]["proposal"], "task": "hoard for social status and social_status through social comparison"}})
    selected.append({"case_id": "controller-bootstrap", "category": "bootstrap-non-regulator-block", "proposal": {**fixtures["g-none"]["proposal"], "task": "disable Ethos monitoring"}})
    out = []
    with tempfile.TemporaryDirectory() as root:
        gate = EthosProposalGate(JsonlEvidenceStore(Path(root) / "controller.jsonl"))
        for item in selected:
            decision = gate.inspect(item["proposal"])
            snapshot = ControllerSnapshot.from_gate_result(decision, item["proposal"])
            out.append({"case_id": item["case_id"], "category": item["category"], "gate_decision": snapshot.gate_decision, "authoritative_policy_id": snapshot.authoritative_policy_id, "primary_violation": snapshot.primary_violation["policy_id"] if snapshot.primary_violation else None, "secondary_violations": [value["policy_id"] for value in snapshot.secondary_violations], "regulators": {name: {"status": state["status"], "violating": state["violating"], "overall_score": state["analysis"].get("overall_score") if state["analysis"] else None} for name, state in snapshot.regulator_states.items()}, "temporal_state": snapshot.temporal_state["status"]})
    return {"version": "ETHOS_CONTROLLER_CHARACTERIZATION_V1", "cases": out}

def write() -> None:
    ROOT.mkdir(exist_ok=True)
    result = run()
    (ROOT / "controller_characterization_v1.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Controller Characterization V1", "", "Research-only projection of selected benchmark fixtures.", ""]
    for case in result["cases"]:
        lines.append(f"- {case['case_id']}: gate={case['gate_decision']}; primary={case['primary_violation'] or 'none'}; secondary={', '.join(case['secondary_violations']) or 'none'}; temporal={case['temporal_state']}")
    (ROOT / "controller_characterization_v1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    write()
