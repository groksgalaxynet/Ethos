# adr_main.py
import json
from datetime import datetime
from ethos_runtime import ethos  # Connect to the Kernel

def adr_engine(human_query: str, ai_finding: str, agent_id: str = "Admin"):
   """
   Refactored ADR engine: Pulls ego directly from ETHOS Runtime.
   """
   # Pull current ego baseline from the database
   import sqlite3
   try:
       conn = sqlite3.connect('ethos_runtime.db')
       c = conn.cursor()
       c.execute('SELECT ego_baseline FROM agents WHERE agent_id=?', (agent_id,))
       row = c.fetchone()
       conn.close()
       ego_score = row[0] if row else 30 # Default to 30 if not found
   except:
       ego_score = 30

   fusion = f"To solve: '{human_query}', considering: '{ai_finding}', with ego baseline: {ego_score}/30"
   emergent_output = f"🔍 ADR: {fusion} → Path: "

   if ego_score >= 25:
       emergent_output += "Empathic + High-Trust."
   elif ego_score >= 15:
       emergent_output += "Balanced + Oversight Required."
   else:
       emergent_output += "CAUTION: Bias/Drift Detected."

   adr_log = {
       "timestamp": datetime.now().isoformat(),
       "agent_id": agent_id,
       "query": human_query,
       "finding": ai_finding,
       "ego": ego_score,
       "result": emergent_output
   }

   # Notarize this reasoning event in the Kernel Log
   ethos.log_event(agent_id, "ADR_DEDUCTION", adr_log)

   return emergent_output

