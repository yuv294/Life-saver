from fastapi import HTTPException, Depends, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from database import get_db
from models.user import User
from config import settings
import logging
from typing import Optional

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

_firebase_initialized = False


def init_firebase() -> None:
    global _firebase_initialized
    if _firebase_initialized or firebase_admin._apps:
        _firebase_initialized = True
        return
    sa_dict = settings.firebase_service_account_dict
    cred = credentials.Certificate(sa_dict) if sa_dict else credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {"projectId": settings.firebase_project_id})
    _firebase_initialized = True
    logger.info("Firebase Admin initialized")


async def _get_or_create_dev_user(db: AsyncSession) -> User:
    """Return a fixed local dev user (creating it once). Local testing only."""
    result = await db.execute(select(User).where(User.google_id == "dev-local-user"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            google_id="dev-local-user",
            email=settings.dev_user_email,
            display_name="Dev User",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def get_current_user(
    http_creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    # Local dev bypass: no token, or the literal token "dev", maps to a fixed dev user.
    if settings.dev_auth_bypass and (not http_creds or http_creds.credentials == "dev"):
        return await _get_or_create_dev_user(db)

    if not http_creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")

    try:
        decoded = firebase_auth.verify_id_token(http_creds.credentials)
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}")

    google_id = decoded["uid"]
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            google_id=google_id,
            email=decoded.get("email", ""),
            display_name=decoded.get("name"),
            avatar_url=decoded.get("picture"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


async def require_internal(x_internal_secret: Optional[str] = Header(None)) -> None:
    """Guard for Cloud Scheduler endpoints — verifies internal secret header."""
    if x_internal_secret != settings.internal_api_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
