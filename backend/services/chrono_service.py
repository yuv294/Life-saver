"""
Chronotype inference from behavioral events.

After 14+ task_started/task_completed events the service fits a simple daily
energy curve and returns 30-minute blocks rated 0.0-1.0.  Falls back to a
sane default curve if data is insufficient.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models.behavioral_event import BehavioralEvent
from typing import List, Dict, Any
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Default energy curve (hour → score) — typical morning-biased chronotype
DEFAULT_ENERGY_CURVE = {
    6: 0.5, 7: 0.65, 8: 0.80, 9: 0.95, 10: 1.0, 11: 0.95,
    12: 0.75, 13: 0.60, 14: 0.55, 15: 0.65, 16: 0.70, 17: 0.65,
    18: 0.55, 19: 0.50, 20: 0.45, 21: 0.35, 22: 0.25, 23: 0.15,
}


def _interpolate_energy(hour: int, curve: Dict[int, float]) -> float:
    if hour in curve:
        return curve[hour]
    keys = sorted(curve.keys())
    for i in range(len(keys) - 1):
        if keys[i] < hour < keys[i + 1]:
            lo, hi = keys[i], keys[i + 1]
            t = (hour - lo) / (hi - lo)
            return curve[lo] + t * (curve[hi] - curve[lo])
    return 0.3


def _fit_energy_curve(completion_hours: List[int]) -> Dict[int, float]:
    """
    Build a simple frequency-based energy curve from the hours when the user
    completes tasks.  Normalized so peak = 1.0.
    """
    if not completion_hours:
        return DEFAULT_ENERGY_CURVE
    counts: Dict[int, int] = {}
    for h in completion_hours:
        counts[h] = counts.get(h, 0) + 1
    peak = max(counts.values()) or 1
    return {h: round(c / peak, 2) for h, c in counts.items()}


class ChronoService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_energy_windows(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Return 30-minute energy blocks for the next 48 hours.
        Uses fitted chronotype if available, else default curve.
        """
        curve = await self._get_or_fit_curve(user_id)
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        windows = []
        for offset in range(0, 96):  # 48 hours × 2 (30-min blocks)
            slot_start = now + timedelta(minutes=offset * 30)
            hour = slot_start.hour
            score = _interpolate_energy(hour, curve)
            windows.append({
                "start": slot_start.isoformat(),
                "end": (slot_start + timedelta(minutes=30)).isoformat(),
                "energy_score": score,
                "label": _energy_label(score),
            })
        return windows

    async def _get_or_fit_curve(self, user_id: str) -> Dict[int, float]:
        result = await self.db.execute(
            select(BehavioralEvent).where(
                BehavioralEvent.user_id == user_id,
                BehavioralEvent.event_type == "task_completed",
            )
        )
        events = result.scalars().all()
        if len(events) < 14:
            return DEFAULT_ENERGY_CURVE
        hours = [e.timestamp.astimezone(timezone.utc).hour for e in events]
        return _fit_energy_curve(hours)

    async def best_slot_for_skill(
        self, user_id: str, skill: str, duration_hours: float = 1.0
    ) -> Dict[str, Any]:
        """Find the highest-energy contiguous window for a given skill."""
        windows = await self.get_energy_windows(user_id)
        # Skill-specific energy biases
        skill_bias = {
            "analytical": lambda h: 1.0 if 8 <= h <= 12 else 0.7,
            "creative": lambda h: 1.0 if 9 <= h <= 13 else 0.6,
            "administrative": lambda h: 1.0 if 13 <= h <= 17 else 0.8,
            "communicative": lambda h: 1.0 if 10 <= h <= 16 else 0.7,
            "relational": lambda h: 1.0 if 9 <= h <= 15 else 0.6,
            "physical": lambda h: 1.0 if 7 <= h <= 10 or 17 <= h <= 19 else 0.5,
        }
        bias_fn = skill_bias.get(skill, lambda h: 1.0)
        slots_needed = int(duration_hours * 2)
        best_score = -1.0
        best_start = None
        for i in range(len(windows) - slots_needed + 1):
            block = windows[i:i + slots_needed]
            hour = datetime.fromisoformat(block[0]["start"]).hour
            avg = sum(w["energy_score"] for w in block) / slots_needed * bias_fn(hour)
            if avg > best_score:
                best_score = avg
                best_start = block[0]["start"]
        return {
            "start": best_start,
            "energy_score": round(best_score, 2),
            "skill": skill,
        }


def _energy_label(score: float) -> str:
    if score >= 0.85:
        return "peak"
    if score >= 0.65:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"
