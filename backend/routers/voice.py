"""
Voice task entry: audio -> Google Speech-to-Text -> Gemini task parser -> task created.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from auth import get_current_user
from models.user import User
from models.behavioral_event import BehavioralEvent
from services.gemini_service import simple_generate
from routers.tasks import create_task
from schemas.task import TaskCreate
from config import settings
from datetime import datetime, timezone
import httpx
import json
import base64
import logging

router = APIRouter(prefix="/voice", tags=["voice"])
logger = logging.getLogger(__name__)

TASK_EXTRACT_PROMPT = """Extract a task from this voice transcription.

Transcription: "{text}"

Return ONLY this JSON:
{{
  "title": "...",
  "description": "...",
  "deadline": "YYYY-MM-DD or null",
  "estimated_hours": 1.0,
  "complexity": "low|medium|high"
}}"""


@router.post("/transcribe-and-create")
async def transcribe_and_create(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    audio_bytes = await audio.read()
    if len(audio_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio file too large (max 10MB)")

    transcript = await _transcribe(audio_bytes, audio.content_type or "audio/webm")
    if not transcript:
        raise HTTPException(status_code=422, detail="Could not transcribe audio")

    text = await simple_generate(TASK_EXTRACT_PROMPT.format(text=transcript))
    text = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

    try:
        task_data = json.loads(text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Could not parse task from transcript")

    deadline = None
    raw_deadline = task_data.get("deadline")
    if raw_deadline and raw_deadline != "null":
        try:
            deadline = datetime.strptime(raw_deadline, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    task_payload = TaskCreate(
        title=task_data.get("title", transcript[:100]),
        description=task_data.get("description"),
        deadline=deadline,
        estimated_hours=task_data.get("estimated_hours", 1.0),
        complexity=task_data.get("complexity", "medium"),
    )
    task = await create_task(task_payload, current_user, db)

    db.add(BehavioralEvent(
        user_id=current_user.id,
        task_id=task.id,
        event_type="voice_task_added",
        metadata_={"transcript": transcript},
    ))
    await db.commit()

    return {"transcript": transcript, "task": task}


async def _transcribe(audio_bytes: bytes, content_type: str) -> str:
    api_key = settings.google_speech_api_key or settings.gemini_api_key
    if not api_key:
        return ""

    encoding_map = {
        "audio/webm": "WEBM_OPUS",
        "audio/ogg": "OGG_OPUS",
        "audio/mp3": "MP3",
        "audio/mpeg": "MP3",
        "audio/wav": "LINEAR16",
        "audio/x-wav": "LINEAR16",
    }
    encoding = encoding_map.get(content_type, "WEBM_OPUS")

    body = {
        "config": {"encoding": encoding, "sampleRateHertz": 48000, "languageCode": "en-US", "enableAutomaticPunctuation": True},
        "audio": {"content": base64.b64encode(audio_bytes).decode()},
    }

    url = f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=body)

    if r.status_code != 200:
        logger.error("STT error %d: %s", r.status_code, r.text[:200])
        return ""

    results = r.json().get("results", [])
    return results[0]["alternatives"][0].get("transcript", "") if results else ""
