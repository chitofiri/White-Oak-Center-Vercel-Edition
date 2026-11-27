from datetime import date
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import AuditEvent, CaseParty, CaseRecord, ContactSession, Role, User
from .security import require_roles

router = APIRouter(prefix="/api/client/ai", tags=["client-ai"])

class PromptRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)

class SummaryRequest(BaseModel):
    text: str = Field(min_length=1, max_length=12000)

AI_RULES = (
    "You are a general information assistant for a client using the White Oak Center portal. "
    "Use calm, plain, supportive language. You are not a lawyer, social worker, therapist, "
    "safeguarding professional, or decision-maker. Do not provide legal advice, assess risk, "
    "make safeguarding recommendations, diagnose anyone, decide child contact arrangements, "
    "or judge any person. Do not invent White Oak Center policies, facts, appointments, or "
    "services. For decisions about a child's welfare, safety, contact, court matters, or a "
    "case, direct the user to speak with their assigned White Oak Center professional. "
    "Do not request names, addresses, case details, or other sensitive personal information. "
    "If the user describes immediate danger, tell them to contact local emergency services "
    "or an appropriate safeguarding professional immediately."
)

async def ask_ollama(system_prompt: str, user_prompt: str) -> str:
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 600},
    }
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            answer = response.json()["message"]["content"]
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("Empty model response")
            return answer.strip()
    except (httpx.HTTPError, KeyError, ValueError):
        raise HTTPException(
            status_code=503,
            detail="The AI service is unavailable. Please try again later or contact support.",
        )

def client_case_or_404(db: Session, case_id: int, user: User):
    party = db.scalar(select(CaseParty).where(
        CaseParty.case_id == case_id,
        CaseParty.user_id == user.id,
        CaseParty.is_active.is_(True),
    ))
    if not party:
        raise HTTPException(status_code=404, detail="Case not found.")
    case = db.get(CaseRecord, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case, party

def record_ai_use(db: Session, user: User, action: str, case_id: int | None = None):
    db.add(AuditEvent(
        actor_user_id=user.id,
        action=action,
        object_type="ai_assistance",
        object_id=str(case_id or user.id),
        metadata_summary="AI feature used; prompt and generated content were not stored.",
    ))
    db.commit()

@router.post("/chat")
async def client_ai_chat(
    data: PromptRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.client)),
):
    answer = await ask_ollama(AI_RULES, data.prompt)
    record_ai_use(db, user, "client.ai_chat")
    return {"answer": answer}

@router.post("/draft")
async def client_ai_draft(
    data: PromptRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.client)),
):
    system = AI_RULES + (
        " Help the user draft a polite, clear, neutral message to White Oak Center. "
        "Use only the facts supplied by the user. Do not add legal claims, allegations, "
        "safeguarding conclusions, or invented details. Label the result as a draft for "
        "the user to review before sending."
    )
    answer = await ask_ollama(system, data.prompt)
    record_ai_use(db, user, "client.ai_draft")
    return {"answer": answer}

@router.post("/summarize")
async def client_ai_summarize(
    data: SummaryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.client)),
):
    system = AI_RULES + (
        " Summarize only the text supplied by the user. Do not infer missing facts or "
        "determine credibility, risk, responsibility, or what should happen next. "
        "Separate stated facts from any uncertainty."
    )
    answer = await ask_ollama(system, "Summarize this text in clear, neutral bullet points:\n\n" + data.text)
    record_ai_use(db, user, "client.ai_summarize")
    return {"answer": answer}

@router.get("/analytics/{case_id}")
def client_ai_analytics(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.client)),
):
    case, party = client_case_or_404(db, case_id, user)
    result = {
        "case_number": case.case_number,
        "case_title": case.case_title,
        "case_status": case.status,
        "schedule_access": bool(party.can_view_schedule),
    }
    if party.can_view_schedule:
        sessions = db.scalars(select(ContactSession).where(
            ContactSession.case_id == case_id,
            ContactSession.status != "cancelled",
        )).all()
        today = date.today()
        result["schedule"] = {
            "visible_sessions": len(sessions),
            "upcoming_sessions": sum(1 for item in sessions if item.session_date >= today),
        }
    record_ai_use(db, user, "client.ai_analytics", case_id)
    return result
