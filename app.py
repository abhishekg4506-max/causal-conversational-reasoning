
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import csv, os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FILE = os.path.join(DATA_DIR, "conversations.csv")

DB: Dict[str, List[Dict[str, Any]]] = {}

def clean(t: str) -> str:
    return "".join(c.lower() if c.isalnum() or c.isspace() else " " for c in (t or ""))

def load():
    with open(FILE, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            row["turn_id"] = int(row["turn_id"])
            row["clean_text"] = clean(row["text"])
            DB.setdefault(row["call_id"], []).append(row)
    for k in DB:
        DB[k].sort(key=lambda x: x["turn_id"])

load()

NEG = ["not received", "never received", "missing"]
POLICY = ["policy", "cannot"]
ESC = ["escalate", "supervisor"]

def has(text, keys):
    return any(k in text for k in keys)

def analyze(convo):
    factors = []
    if any(has(t["clean_text"], NEG) for t in convo if t["speaker"]=="Customer"):
        factors.append("Delivery failure reported by customer")
    if any(has(t["clean_text"], POLICY) for t in convo if t["speaker"]=="Agent"):
        factors.append("Agent policy constraint")
    return factors

app = FastAPI(title="Pravah Hackathon – Final Submission")

class Req(BaseModel):
    query: str
    event: Optional[str] = None
    call_id: Optional[str] = None
    is_followup: bool = False

CTX = {"event": None, "factors": []}

@app.post("/explain")
def explain(req: Req):
    if not req.is_followup:
        convo = DB.get(req.call_id, [])
        factors = analyze(convo)
        CTX["event"] = req.event
        CTX["factors"] = factors
        return {
            "Outcome Event": req.event,
            "Call ID": req.call_id,
            "Primary Causal Factors": factors,
            "Evidence": [
                {
                    "turn_id": t["turn_id"],
                    "speaker": t["speaker"],
                    "text": t["text"]
                } for t in convo
            ]
        }
    return {
        "Previous Event": CTX["event"],
        "Previous Factors": CTX["factors"],
        "Answer": "Follow-up answered using stored causal context."
    }
