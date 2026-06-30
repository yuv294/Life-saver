"""
Firebase Cloud Messaging — push notifications via Firebase Admin SDK.
"""

from firebase_admin import messaging
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FirebaseService:
    async def send_push(
        self,
        title: str,
        body: str,
        fcm_token: Optional[str] = None,
        deep_link: Optional[str] = None,
        data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Send a push notification.  fcm_token is required; if absent, logs a warning.
        deep_link is embedded in the data payload so the client app can navigate on tap.
        """
        if not fcm_token:
            logger.warning("send_push called with no FCM token — skipping")
            return {"skipped": True, "reason": "no_fcm_token"}

        payload: Dict[str, str] = data or {}
        if deep_link:
            payload["deep_link"] = deep_link

        message = messaging.Message(
            notification=messaging.Notification(title=title[:50], body=body[:200]),
            data=payload,
            token=fcm_token,
            android=messaging.AndroidConfig(priority="high"),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default", badge=1)
                )
            ),
        )

        try:
            message_id = messaging.send(message)
            logger.info("Push sent: %s → %s", title, message_id)
            return {"message_id": message_id, "title": title}
        except messaging.UnregisteredError:
            logger.warning("FCM token unregistered: %s", fcm_token[:20])
            return {"error": "unregistered_token"}
        except Exception as exc:
            logger.error("FCM send failed: %s", exc)
            return {"error": str(exc)}

    async def send_morning_brief(self, fcm_token: str, brief_text: str) -> Dict[str, Any]:
        first_sentence = brief_text.split(".")[0].strip() + "."
        return await self.send_push(
            title="Your morning brief is ready",
            body=first_sentence[:200],
            fcm_token=fcm_token,
            deep_link="/",
            data={"type": "morning_brief"},
        )

    async def send_cascade_warning(
        self, fcm_token: str, task_title: str, cascade_count: int
    ) -> Dict[str, Any]:
        return await self.send_push(
            title=f"Cascade Risk: {cascade_count} tasks affected",
            body=f'"{task_title}" is at risk. Tap to reschedule.',
            fcm_token=fcm_token,
            deep_link="/tasks",
            data={"type": "cascade_warning"},
        )
