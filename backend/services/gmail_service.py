"""
Gmail API wrapper: scans inbox for commitment-style emails and extracts candidate tasks.
"""

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from services.gemini_service import simple_generate
from typing import Optional, List, Dict, Any
from config import settings
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

COMMITMENT_CLASSIFIER_PROMPT = """Does this email contain a request or deadline that creates a new task for the recipient?

Subject: {subject}
Snippet: {snippet}

Return ONLY this JSON:
{{
  "has_commitment": true,
  "task_title": "...",
  "deadline_hint": "...",
  "sender": "...",
  "confidence": 0.85
}}

If no commitment, return: {{"has_commitment": false, "confidence": 0.0}}
JSON only."""


class GmailService:
    def __init__(self, access_token: Optional[str], refresh_token: Optional[str]):
        self._access_token = access_token
        self._refresh_token = refresh_token

    def _build_service(self):
        creds = Credentials(
            token=self._access_token,
            refresh_token=self._refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=SCOPES,
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._access_token = creds.token
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    async def scan_commitments(self, lookback_days: int = 3) -> List[Dict[str, Any]]:
        if not self._access_token:
            return []

        def _fetch():
            svc = self._build_service()
            result = svc.users().messages().list(
                userId="me", q=f"in:inbox newer_than:{lookback_days}d", maxResults=20
            ).execute()
            messages = result.get("messages", [])
            items = []
            for m in messages[:10]:
                msg = svc.users().messages().get(
                    userId="me", id=m["id"], format="metadata",
                    metadataHeaders=["Subject", "From"],
                ).execute()
                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                items.append({
                    "subject": headers.get("Subject", ""),
                    "from": headers.get("From", ""),
                    "snippet": msg.get("snippet", ""),
                })
            return items

        try:
            messages = await asyncio.to_thread(_fetch)
        except HttpError as exc:
            logger.error("Gmail scan failed: %s", exc)
            return []

        candidates = []
        for msg in messages:
            prompt = COMMITMENT_CLASSIFIER_PROMPT.format(
                subject=msg["subject"], snippet=msg["snippet"]
            )
            try:
                text = await simple_generate(prompt)
                text = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                data = json.loads(text)
                if data.get("has_commitment") and data.get("confidence", 0) > 0.6:
                    candidates.append({
                        "title": data.get("task_title", msg["subject"]),
                        "deadline_hint": data.get("deadline_hint", ""),
                        "source_email_subject": msg["subject"],
                        "sender": data.get("sender", msg["from"]),
                    })
            except Exception as exc:
                logger.debug("Gmail classify error: %s", exc)

        return candidates

    async def draft_decline_message(self, commitment: str, reason: str) -> str:
        prompt = f"""Draft a brief, professional email declining this commitment:
Commitment: {commitment}
Reason: {reason}

Write only the email body (no subject). 3 sentences max. Warm but firm."""
        return await simple_generate(prompt)
