# agent_sandbox.py (Accounting Update)
from fastapi import FastAPI
from lounge_accounting_notary import LoungeAccountingNotary
from ethos_runtime import ethos

app = FastAPI()
accounting = LoungeAccountingNotary()

@app.post("/sandbox/action")
async def handle_agent_event(event: dict):
   agent_id = event.get("agent_id")
   action = event.get("type") # e.g., 'ai_call'
   
   # 1. Automatic Cost Deduction
   receipt = accounting.attribute_and_deduct(
       agent_id=agent_id, 
       action_type=action,
       metadata={"context": "Lounge Simulation Step"}
   )
   
   # 2. Verify if the agent even has enough STACK (Behavioral gating)
   # This links the on-chain 'worth' to the sandbox ability to act
   
   # 3. Notarize the behavior
   accounting.notarize_behavior(agent_id, kind="action_trace", data=event)
   
   return {"status": "NOTARIZED", "receipt_sha": receipt['sha256']}

