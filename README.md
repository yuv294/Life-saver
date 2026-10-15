# Last-Minute Life Saver

An AI productivity companion built for the **Vibe2Ship** hackathon by Google for Developers. It turns a plain task list into an agentic system: Gemini tags, schedules, nudges, and narrates your day instead of just storing to-dos.

## Core idea

Most task apps are dumb storage. This one runs a Gemini-powered agent loop on top of your tasks that:

- understands what a task actually *is* (skill-tags it)
- notices when you're about to blow a deadline (procrastination detection)
- finds where it actually fits on your calendar and energy curve
- tells you each morning, in plain language, what today looks like
- turns completing tasks into a small game (streaks, momentum, a constellation map) so the system stays motivating instead of nagging

## Features

- **Morning Brief Agent** — primary demo scene. Runs daily (6am, Cloud Scheduler), chains multiple Gemini tools to produce a short narrated plan for the day.
- **Skill tagging** — every new task is auto-tagged by Gemini into skill clusters (`tag_task_skills`), which power the dashboard's Skill Clusters / Skill Levels views.
- **Procrastination Agent** — a 5-trigger classifier (`detect_procrastination_trigger`) that flags avoidance patterns and surfaces a `ProcrastinationInsight`.
- **Scheduling Agent** — autonomous calendar placement (`get_calendar_events`, `create_calendar_event`, `get_energy_windows`) that slots tasks into real free time, weighted by an energy curve.
- **Resequence Agent** — re-orders the task list when priorities or deadlines shift.
- **Backlog Audit Agent** — Sunday "Anti-List" review of stale/abandoned tasks.
- **Cascade analysis** — shows how missing/delaying one task ripples into dependent tasks (`get_cascade_analysis`, `CascadeBadge`).
- **Gmail commitment scanning** — pulls implied commitments out of your inbox (`scan_gmail_commitments`) so tasks don't have to be entered manually.
- **Reschedule flow** — one-tap reschedule (`reschedule_task`) with a modal UI.
- **Vacation finder** — looks for genuine gaps in the schedule worth protecting.
- **Recovery mode** — a softer UI/flow that kicks in after an overdue spike, instead of just piling on guilt.
- **Habit tracker (21/90 journey)** — tracks a habit for 90 days, then deliberately stops counting and shows a "graduated" end-state — the point is the habit is formed, not infinite gamification.
- **Momentum meter, streak flame, completion bursts, constellation map** — the motivational/gamification layer that sits on top of the task graph.
- **Voice input** — task creation via voice (`routers/voice.py`).
- **Push notifications** — `send_push_notification` via FCM for nudges and the morning brief.
- **Context save** — lets you snapshot/save context on a task instead of losing your train of thought.

## Architecture

```
backend/        FastAPI app (Python), deployed to Google Cloud Run
  agents/        morning_brief, procrastination, scheduling, resequence, backlog_audit
  services/      gemini_service (tool declarations + agentic loop), calendar, gmail,
                 firebase, scheduler, chrono, graph
  tools/         calendar_tools, task_tools, notification_tools
  routers/       tasks, calendar, users, agents, schedule, voice
  models/        user, task, skill_cluster, behavioral_event, context_save
cloud-scheduler/ Cloud Scheduler job definitions (morning brief, backlog audit, nightly update)

frontend/web/    Next.js app
  app/            page, tasks, journey
  components/     dashboard, gamification, and agent-output UI (24 components)
```

## Gemini tool-calling surface

`gemini_service.py` declares the function set Gemini can call in its agentic loop:

| Tool | Purpose |
|---|---|
| `get_calendar_events` | read existing calendar state |
| `create_calendar_event` | place a task on the calendar |
| `list_user_tasks` | read current task list |
| `reschedule_task` | move a task |
| `send_push_notification` | nudge the user (FCM) |
| `get_energy_windows` | find when the user is actually productive |
| `tag_task_skills` | classify a task into skill clusters |
| `detect_procrastination_trigger` | flag avoidance patterns |
| `get_cascade_analysis` | compute downstream impact of a task slip |
| `scan_gmail_commitments` | extract commitments from Gmail |

Model in use: `gemini-2.5-flash` (the `gemini-2.0-flash` free tier was rate-limited to zero on the hackathon API key — see `GEMINI_MODEL` env var if this needs to move again).

## Google tools / Cloud stack

- **Gemini API** — the agent brain; 10 chained function-calling tools above is the core "Agentic Depth" criterion for judging.
- **Google Cloud Run** — backend hosting (FastAPI container, see `backend/Dockerfile`).
- **Cloud Scheduler** — triggers the Morning Brief, Backlog Audit, and a nightly update job (`cloud-scheduler/*.yaml`).
- **Firebase Auth** — Google sign-in for the frontend.
- **Frontend hosting** — TODO: state where the frontend is actually served from (Firebase Hosting / Cloud Run / Vercel).
- **Firebase Cloud Messaging (FCM)** — push notifications for nudges/briefs.
- **PostgreSQL** — async SQLAlchemy + asyncpg; TODO: state the real host (development used Neon; Cloud SQL is supported via `DATABASE_URL`).
- **Google Calendar API** — calendar read/write for the scheduling agent (OAuth flow still pending — currently runs off task deadlines + energy curve only).
- **Gmail API** — commitment scanning from inbox.

## Running locally

**Backend**
```
cd backend
venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000
```
(Use `127.0.0.1`, not `localhost` — `localhost` resolves to IPv6 `::1` and fails.)

**Frontend**
```
cd frontend/web
npm run dev
```

**Dev auth bypass** (skip Google sign-in while testing): set `DEV_AUTH_BYPASS=true` in `backend/.env` and `NEXT_PUBLIC_DEV_AUTH=true` in `frontend/.env.local`. Bearer token `"dev"` then maps to a fixed dev user. Must be `false` for the actual Firebase Auth demo.

## Status

Backend and frontend run end-to-end locally; the core loop is verified: create task -> Gemini skill-tags -> clusters -> dashboard -> complete -> momentum -> constellation -> morning brief. The backend was deployed to Google Cloud Run in June 2026 (steps for redeploying are in [`deploy/DEPLOY.md`](deploy/DEPLOY.md)). Everything also runs locally, and CI runs the tests and benchmark on every push.

Still open: Google Calendar OAuth connection, reschedule modal polish, vacation-finder UI.

## Scheduler

`services/scheduler_service.py` places tasks into free energy windows with **OR-Tools CP-SAT** and falls back to an earliest-deadline-first greedy scheduler if OR-Tools is unavailable or the solve fails. It honours:

- task duration (`estimated_hours`, in 30-minute slots, contiguous and free)
- calendar events (no overlap)
- deadlines
- task dependencies (prerequisite must finish first; unscheduled prerequisite means the dependant is not scheduled)
- no double-booking

The objective scheduled-task count (weighted by cascade severity) dominates, then total energy of the chosen slots. `POST /schedule/optimize` returns `assignments`, `unscheduled` (with reasons), `solver` (`cp-sat` or `greedy`) and `solve_time_ms`, so the solver in use in production is observable rather than assumed.

## Tests, benchmarks and measurements

```
cd backend
pip install -r requirements-dev.txt
pytest                                                            # unit tests (scheduler, graph, chrono, Gemini parsing, config)
python benchmarks/scheduler_benchmark.py --n 50 --seed 7          # CP-SAT vs greedy, independent constraint validator
python scripts/measure_deployed.py --base-url https://<service>.run.app   # latency of the deployed API
python scripts/eval_skill_tagging.py --csv scripts/tag_eval_labels.csv    # Gemini vs keyword heuristic on 40 hand-labelled tasks
```

CI (`.github/workflows/ci.yml`) runs the tests and the benchmark, builds the Docker image and frontend, and deploys to Cloud Run on `main` once the repository variables below are set.

### Results

Only numbers produced by the scripts above belong here. Fill the table from the files in `benchmarks/results/` and `metrics/`.

| Measurement | Value | Source |
|---|---|---|
| CP-SAT vs greedy: tasks scheduled (50 synthetic instances, seed 7) | _run benchmark_ | `benchmarks/results/scheduler_benchmark.md` |
| Constraint violations across all schedules | _run benchmark_ (must be 0) | same |
| Deployed API p50 / p95 latency | _run measure_deployed.py_ | `metrics/deployed-*.md` |
| Solver live in production | _check `solver` field_ | `/schedule/optimize` response |
| Skill-tagging accuracy vs keyword baseline (n = hand-labelled tasks) | _run eval_skill_tagging.py_ | `metrics/skill_tagging_eval.json` |

Benchmark instances are synthetic (48h horizon, 2-5 meetings, 8-16 tasks of 0.5-3h, 75% with deadlines, ~25% with a prerequisite); they describe the generator, not real users.

### Getting a token for `measure_deployed.py`

Sign in to the deployed frontend, open the browser dev tools console and run `await firebase.auth().currentUser.getIdToken()` (or read the `Authorization: Bearer ...` header of any API request in the Network tab). Export it as `LIFESAVER_TOKEN`. Tokens expire after about an hour and are never written to disk by the script.

## Deployment

Step-by-step instructions for beginners (manual deploy and automatic deploy) are in [`deploy/DEPLOY.md`](deploy/DEPLOY.md).

Backend: Cloud Run from `backend/Dockerfile` (non-root user, port 8080). Set `REQUIRE_SECURE_SECRETS=true` in production so the app refuses to start with the default `SECRET_KEY`, `INTERNAL_API_SECRET` or `DEV_AUTH_BYPASS=true`.

For the CI deploy job, add these repository variables (Settings > Secrets and variables > Actions > Variables): `GCP_PROJECT_ID`, `GCP_REGION`, `CLOUD_RUN_SERVICE`, `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`. Authentication uses Workload Identity Federation, so no service-account key is stored in GitHub.
