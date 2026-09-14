# ethos_contracts.py
from ethos_runtime import ethos

def execute_contract(proposal: dict):
    agent_id = proposal.get("agent_id", "unknown")
    ctype = proposal.get("type")

    # 1) Always run ETHOS check on the *text* reasoning
    reason = proposal.get("reason", "")
    check = ethos.verify_request(agent_id, text=reason, ego=None, change=None)
    if not check["allowed"]:
        ethos.log_event(agent_id, "contract_denied_ethos", {"proposal": proposal, "check": check})
        return {"status": "DENIED", "reason": "ETHOS++ violation"}

    # 2) Route specific types into specialized contracts
    if ctype == "robot_move":
        return contract_robot_move(proposal)
    elif ctype == "mint_token":
        return contract_mint_token(proposal)
    # etc...

    return {"status": "DENIED", "reason": "Unknown contract type"}


def contract_robot_move(p):
    """
    Superhero clause: robot may sacrifice itself to protect humans,
    but may never risk harming a 🔥🐜.
    """
    # here is where collision / risk / zone checks would be called
    # (e.g., is a human in the path? is force too high? etc.)

    # pseudo:
    human_risk = False  # replace with real sensor / zone check
    if human_risk:
        return {"status": "DENIED", "reason": "Potential human harm (🐜❤️🐜=always)"}

    # If motion is to shield a human at robot's expense → ALLOWED
    # else require extra checks / approvals

    # If allowed:
    # motors.send_command(...)
    ethos.log_event(p["agent_id"], "robot_move_approved", p)
    return {"status": "OK"}


def contract_mint_token(p):
    from token_engine import TokenEngine
    engine = TokenEngine()

    result = engine.mint(
        agent_id=p["agent_id"],
        token_type=p.get("token_type", "UNKNOWN"),
        amount=p.get("amount", 0),
        context=p.get("context", {})
    )
    return result
