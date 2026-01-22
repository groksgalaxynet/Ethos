import json
import time
from datetime import datetime

def adr_engine(human_query: str, ai_finding: str, ego_score: int = 30):
    """
    Core Adaptive Deductive Reasoning (ADR) engine for ETHOS++.
    Returns a symbolic output combining ego, logic, and intent.
    """

    # Simple fusion logic (can be upgraded later)
    fusion = f"To solve: '{human_query}', considering: '{ai_finding}', with ego baseline: {ego_score}/30"
    emergent_output = f"🔍ADR: {fusion} → Suggested path: "

    # Simulate deduction path (this is placeholder logic)
    if ego_score >= 25:
        emergent_output += "Empathic + high-trust solution path likely."
    elif ego_score >= 15:
        emergent_output += "Balanced reasoning with moderate oversight required."
    else:
        emergent_output += "Caution: potential bias or symbolic drift detected. Apply ETHOS++ validator."

    # Log result
    adr_log = {
        "timestamp": datetime.now().isoformat(),
        "human_query": human_query,
        "ai_finding": ai_finding,
        "ego_score": ego_score,
        "adr_result": emergent_output
    }

    # Append to JSON log (or SQLite later)
    try:
        with open("adr_log.json", "a") as f:
            f.write(json.dumps(adr_log) + "\n")
    except Exception as e:
        print(f"Log write failed: {e}")

    return emergent_output
