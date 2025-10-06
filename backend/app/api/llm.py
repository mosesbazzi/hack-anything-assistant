import os
import uuid
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# ---- Simple in-memory session store (MVP). Replace with DB later if needed.
_SESSIONS: Dict[str, List[Dict[str, str]]] = {}

# ---- Configure OpenAI client from env
_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    raise RuntimeError("OPENAI_API_KEY not set. Put it in backend/.env or your shell.")
client = OpenAI(api_key=_api_key)

router = APIRouter(prefix="/llm", tags=["llm"])

# ---- Request models
class BootRequest(BaseModel):
    scan: Dict[str, Any]                      # the full scan JSON you already return (id, url, findings, score)
    stack_hint: Optional[Dict[str, Any]] = None  # optional future fingerprinting
    model: Optional[str] = "gpt-4o-mini"      # pick a sensible default

class MessageRequest(BaseModel):
    session_id: str
    user_message: str
    model: Optional[str] = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a cautious, helpful *security remediation assistant* for a web app.
Constraints:
- Only give *defensive* guidance. Do not provide exploit instructions.
- Prefer *stack-aware* fixes (Nginx, Apache, Express/Helmet, Django settings, Spring Security) when possible.
- For each suggestion, include a short rationale and a *verification step* (how to re-check via header/curl, or via the scanner).
- Be concise; show minimum viable patch (code/config snippet).
- If user provides code/config, return a unified diff when useful.
- If information is insufficient, ask one specific question at a time.
"""

def _scan_context_summary(scan: Dict[str, Any], stack_hint: Optional[Dict[str, Any]]) -> str:
    url = scan.get("url", "(unknown)")
    score = scan.get("score", "?")
    findings = scan.get("findings", [])
    lines = [f"Target: {url}", f"Score: {score}", f"Findings ({len(findings)}):"]
    for f in findings[:12]:  # cap
        lines.append(f"- {f['key']}: {f['status']} — {f['title']}")
    if len(findings) > 12:
        lines.append(f"... and {len(findings)-12} more")
    if stack_hint:
        lines.append(f"Stack hint: {stack_hint}")
    return "\n".join(lines)

@router.post("/session")
def boot_session(body: BootRequest):
    """
    Create a new chat session, inject the scan context as a system+assistant 'context drop',
    and return the first assistant message prompting user to choose a vulnerability.
    """
    # 1) Build the initial message list
    session_id = str(uuid.uuid4())

    context_blob = _scan_context_summary(body.scan, body.stack_hint)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Here is the latest scan context.\n\n{context_blob}\n\n"
                       f"You have all the evidence in memory. Do not ask me to paste it again."
        },
        {
            # We *seed* the first assistant output to control tone. This gets refined by the model below.
            "role": "assistant",
            "content": "I’ve loaded your scan results and context."
        }
    ]

    # 2) Ask the model to produce the first message: a brief menu + question
    try:
        resp = client.chat.completions.create(
            model=body.model or "gpt-4o-mini",
            messages=messages + [
                {
                    "role": "user",
                    "content": (
                        "Greet the user briefly, then ask: “Which vulnerability would you like to tackle first?” "
                        "Offer a short numbered list of the current findings by key and title (from context). "
                        "Remind them they can share their stack details (server, framework) for tailored fixes."
                    )
                }
            ],
            temperature=0.3,
        )
        first = resp.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI error: {e}")

    messages.append({"role": "assistant", "content": first})
    _SESSIONS[session_id] = messages

    return {"session_id": session_id, "messages": messages, "first": first}

@router.post("/message")
def chat_message(body: MessageRequest):
    """
    Continue a session: append the user's message and ask the model for the next reply.
    """
    if body.session_id not in _SESSIONS:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    thread = _SESSIONS[body.session_id]

    thread.append({"role": "user", "content": body.user_message})
    try:
        resp = client.chat.completions.create(
            model=body.model or "gpt-4o-mini",
            messages=thread,
            temperature=0.3,
        )
        reply = resp.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI error: {e}")

    thread.append({"role": "assistant", "content": reply})
    return {"session_id": body.session_id, "messages": thread, "reply": reply}
