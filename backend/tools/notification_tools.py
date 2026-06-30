"""
Notification tool wrapper for Gemini function calling.
"""

from services.firebase_service import FirebaseService
from typing import Dict, Any, Optional


async def send_push_notification(
    firebase_service: FirebaseService,
    title: str,
    body: str,
    fcm_token: str,
    deep_link: Optional[str] = None,
) -> Dict[str, Any]:
    return await firebase_service.send_push(
        title=title,
        body=body,
        fcm_token=fcm_token,
        deep_link=deep_link,
    )
