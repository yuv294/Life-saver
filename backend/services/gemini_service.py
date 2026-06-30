"""
Core Gemini 2.0 Flash client — google-genai SDK (current).

Provides:
  - AGENT_TOOLS: all 10 function declarations
  - execute_tool(): routes function calls to service implementations
  - run_agent(): autonomous multi-turn agentic loop
  - classify_skills(): one-shot skill tagging
  - compress_context(): brain dump -> 3-bullet context save
"""

from google import genai
from google.genai import types
from config import settings
from typing import Any
import asyncio
import logging
import json

logger = logging.getLogger(__name__)

MODEL = settings.gemini_model
# Cap one-shot calls so a throttled/slow API falls back fast instead of hanging the UI.
GEN_TIMEOUT = 12.0

_client: genai.Client | None = None


class GeminiDisabled(Exception):
    """Raised when GEMINI_ENABLED=false so callers fall back to heuristics."""


async def _generate(prompt: str) -> str:
    """One-shot text generation with a hard timeout. Raises on disabled/timeout/error."""
    if not settings.gemini_enabled:
        raise GeminiDisabled()
    client = get_client()
    response = await asyncio.wait_for(
        client.aio.models.generate_content(model=MODEL, contents=prompt),
        timeout=GEN_TIMEOUT,
    )
    return response.text


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


# ── Tool definitions ──────────────────────────────────────────────────────────

def _schema(**props) -> types.Schema:
    """Helper: build an OBJECT schema from keyword property schemas."""
    return types.Schema(type=types.Type.OBJECT, properties=props)


def _str(desc: str) -> types.Schema:
    return types.Schema(type=types.Type.STRING, description=desc)


def _int(desc: str) -> types.Schema:
    return types.Schema(type=types.Type.INTEGER, description=desc)


AGENT_TOOLS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_calendar_events",
            description="Get Google Calendar events for a date range. Call before scheduling.",
            parameters=_schema(
                start_date=_str("Start date ISO 8601 e.g. 2026-06-25"),
                end_date=_str("End date ISO 8601 e.g. 2026-06-28"),
            ),
        ),
        types.FunctionDeclaration(
            name="create_calendar_event",
            description="Block time on Google Calendar. Only call after confirming slot is free.",
            parameters=_schema(
                title=_str("Event title"),
                start_time=_str("ISO 8601 with timezone"),
                end_time=_str("ISO 8601 with timezone"),
                description=_str("Task details"),
            ),
        ),
        types.FunctionDeclaration(
            name="list_user_tasks",
            description="Get all pending/in_progress tasks with deadlines, skill_tags, cascade_severity.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={}),
        ),
        types.FunctionDeclaration(
            name="reschedule_task",
            description="Move a task to a new datetime. Updates calendar and increments reschedule_count.",
            parameters=_schema(
                task_id=_str("UUID of the task"),
                new_datetime=_str("New start ISO 8601"),
                reason=_str("Reason for rescheduling"),
            ),
        ),
        types.FunctionDeclaration(
            name="send_push_notification",
            description="Send a push notification via Firebase Cloud Messaging.",
            parameters=_schema(
                title=_str("Notification title (max 50 chars)"),
                body=_str("Notification body (max 200 chars)"),
                deep_link=_str("Optional app route e.g. /tasks/{id}"),
            ),
        ),
        types.FunctionDeclaration(
            name="get_energy_windows",
            description="Get predicted energy levels for next 48h. Returns 30-min blocks with energy 0.0-1.0.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={}),
        ),
        types.FunctionDeclaration(
            name="tag_task_skills",
            description="Analyze task, return skill tags from: analytical, creative, communicative, administrative, relational, physical.",
            parameters=_schema(
                task_title=_str("Task title"),
                task_description=_str("Task description"),
            ),
        ),
        types.FunctionDeclaration(
            name="detect_procrastination_trigger",
            description="Analyze why a task is being avoided and generate a targeted intervention.",
            parameters=_schema(task_id=_str("UUID of the avoided task")),
        ),
        types.FunctionDeclaration(
            name="get_cascade_analysis",
            description="Which tasks depend on this one and what is the cascade severity score.",
            parameters=_schema(task_id=_str("UUID of the task")),
        ),
        types.FunctionDeclaration(
            name="scan_gmail_commitments",
            description="Scan recent Gmail inbox for commitment-style emails and return candidate tasks.",
            parameters=_schema(
                lookback_days=_int("Days back to scan (default 3)"),
            ),
        ),
    ]
)


# ── Tool execution router ─────────────────────────────────────────────────────

async def execute_tool(
    function_name: str,
    function_args: dict,
    user_id: str,
    services: dict,
) -> Any:
    handlers = {
        "get_calendar_events": lambda: services["calendar"].get_events(**function_args),
        "create_calendar_event": lambda: services["calendar"].create_event(**function_args),
        "list_user_tasks": lambda: services["tasks"].list_tasks(user_id),
        "reschedule_task": lambda: services["tasks"].reschedule(user_id=user_id, **function_args),
        "send_push_notification": lambda: services["firebase"].send_push(**function_args),
        "get_energy_windows": lambda: services["chrono"].get_energy_windows(user_id),
        "tag_task_skills": lambda: classify_skills(**function_args),
        "detect_procrastination_trigger": lambda: services["procrastination"].detect(**function_args),
        "get_cascade_analysis": lambda: services["graph"].cascade_analysis(**function_args),
        "scan_gmail_commitments": lambda: services["gmail"].scan_commitments(**function_args),
    }
    handler = handlers.get(function_name)
    if not handler:
        raise ValueError(f"Unknown tool: {function_name}")
    try:
        return await handler()
    except Exception as exc:
        logger.error("Tool %s failed: %s", function_name, exc)
        return {"error": str(exc)}


# ── Agentic loop ──────────────────────────────────────────────────────────────

async def run_agent(
    system_prompt: str,
    user_message: str,
    user_id: str,
    services: dict,
    max_iterations: int = 10,
) -> str:
    """
    Multi-turn loop: Gemini calls tools, gets results, decides next tool or returns text.
    """
    if not settings.gemini_enabled:
        raise GeminiDisabled()
    client = get_client()
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[AGENT_TOOLS],
    )

    chat = client.aio.chats.create(model=MODEL, config=config)
    response = await chat.send_message(user_message)
    logger.info("Agent started for user %s", user_id)

    for iteration in range(max_iterations):
        if not response.candidates or not response.candidates[0].content.parts:
            break

        tool_calls = [
            p for p in response.candidates[0].content.parts
            if p.function_call and p.function_call.name
        ]

        if not tool_calls:
            break

        logger.info("Iteration %d: %d tool call(s)", iteration + 1, len(tool_calls))

        fn_responses = []
        for part in tool_calls:
            fc = part.function_call
            logger.info("  -> %s(%s)", fc.name, dict(fc.args))
            result = await execute_tool(fc.name, dict(fc.args), user_id, services)
            fn_responses.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"result": result},
                    )
                )
            )

        response = await chat.send_message(fn_responses)

    # Extract final text response
    for part in response.candidates[0].content.parts:
        if hasattr(part, "text") and part.text:
            return part.text

    return "Agent completed all actions."


# ── One-shot helpers ──────────────────────────────────────────────────────────

SKILL_KEYWORDS = {
    "analytical": ["analyze", "research", "data", "debug", "calculate", "review", "plan",
                   "study", "compare", "budget", "report", "code", "fix", "design system"],
    "creative": ["write", "design", "brainstorm", "draft", "create", "sketch", "compose",
                 "logo", "story", "content", "video", "blog", "ideate"],
    "communicative": ["email", "call", "message", "present", "pitch", "reply", "notify",
                      "announce", "post", "share", "demo", "talk"],
    "administrative": ["file", "submit", "schedule", "organize", "book", "pay", "renew",
                       "form", "register", "update", "sort", "expense", "invoice"],
    "relational": ["meet", "coffee", "catch up", "interview", "mentor", "thank",
                   "birthday", "visit", "network", "1:1", "sync"],
    "physical": ["gym", "run", "clean", "move", "build", "cook", "walk", "exercise",
                 "repair", "pack", "groceries"],
}


def _heuristic_skills(task_title: str, task_description: str = "") -> dict:
    """Keyword-based skill tagging used when Gemini is unavailable/rate-limited."""
    text = f"{task_title} {task_description}".lower()
    matched = [skill for skill, kws in SKILL_KEYWORDS.items()
               if any(kw in text for kw in kws)]
    if not matched:
        matched = ["administrative"]
    urgent_words = ["urgent", "asap", "today", "now", "deadline", "due", "tomorrow", "tonight"]
    urgency = "high" if any(w in text for w in urgent_words) else "medium"
    return {
        "skill_tags": matched[:3],
        "primary_skill": matched[0],
        "complexity": "high" if len(text) > 120 else "medium",
        "eisenhower_quadrant": 1 if urgency == "high" else 2,
        "importance": "medium",
        "urgency": urgency,
        "_source": "heuristic",
    }


async def classify_skills(task_title: str, task_description: str = "") -> dict:
    prompt = f"""Analyze this task and return ONLY a JSON object.

Task title: {task_title}
Description: {task_description or "N/A"}

Return exactly this JSON structure:
{{
  "skill_tags": ["<tag1>", "<tag2>"],
  "primary_skill": "<tag>",
  "complexity": "low|medium|high",
  "eisenhower_quadrant": 1,
  "importance": "low|medium|high",
  "urgency": "low|medium|high"
}}

skill_tags must be a subset of: analytical, creative, communicative, administrative, relational, physical
eisenhower_quadrant: 1=urgent+important 2=not urgent+important 3=urgent+not important 4=neither
Return JSON only, no markdown fences."""

    try:
        raw = await _generate(prompt)
        text = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("classify_skills parse failed, using heuristic")
        return _heuristic_skills(task_title, task_description)
    except Exception as exc:
        logger.warning("classify_skills API error (%s), using heuristic", type(exc).__name__)
        return _heuristic_skills(task_title, task_description)


async def compress_context(brain_dump: str, task_title: str) -> str:
    prompt = f"""Compress this brain dump into exactly 3 bullet points for "{task_title}".

Brain dump: {brain_dump}

Format:
* [DONE] What was just completed
* [THINKING] Current hypothesis or decision point
* [NEXT] The single clearest next action

Return only the 3 bullets, nothing else."""

    try:
        return (await _generate(prompt)).strip()
    except Exception as exc:
        logger.warning("compress_context API error (%s), using raw dump", type(exc).__name__)
        snippet = brain_dump.strip().replace("\n", " ")[:200]
        return (
            f"* [DONE] Captured notes on {task_title}\n"
            f"* [THINKING] {snippet}\n"
            f"* [NEXT] Resume where you left off"
        )


async def simple_generate(prompt: str) -> str:
    """Convenience wrapper for one-shot text generation. Returns '' on failure."""
    try:
        return (await _generate(prompt)).strip()
    except Exception as exc:
        logger.warning("simple_generate API error (%s)", type(exc).__name__)
        return ""
