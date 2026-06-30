# Last-Minute Life Saver — Implementation Checklist

> Status legend: ☐ = not started · ◐ = backend done, frontend pending · ☑ = fully working (backend + UI + tested)

---

## ✅ Current status — updated 2026-06-27 (this session)

**The app now runs end-to-end locally.** Verified:
- Backend boots, Neon DB connects, Firebase Admin inits, `/health` OK. **16/16 core endpoints pass** an automated smoke test with real Gemini calls.
- **Critical fix:** `gemini-2.0-flash` free tier is dead on this key (429 `limit:0`). Switched to `gemini-2.5-flash` (env `GEMINI_MODEL`). This unblocked every AI feature. All Gemini helpers now degrade gracefully so a 429 never 500s task creation.
- Frontend builds clean (`next build` ✓) and serves. **Fixed pervasive data-shape mismatches** (status `done`→`completed`; eisenhower int 1-4 not strings; `skill_tags[]` not `skill_cluster`; next-session object; energy-window shape).
- Morning brief agent chains 3 tools → real 4-sentence narrative, returned synchronously for the card (+ fallback).
- New: `POST /tasks/{id}/complete`, `POST /agents/me/tasks/{id}/procrastination`. Fixed an `ARRAY.contains()` crash (generic→postgresql ARRAY).
- New UI: "Why am I avoiding this?" panel + "Pause & save context" breadcrumb on task cards.

**Local dev:** run backend with host `127.0.0.1` (NOT localhost — IPv6 ::1 fails). Set `DEV_AUTH_BYPASS=true` (backend `.env`) + `NEXT_PUBLIC_DEV_AUTH=true` (frontend `.env.local`) to skip Google sign-in with Bearer token `dev`; **set both false for the Firebase Auth demo.**

**⚙️ Gemini key / rate limits:** AI calls now respect `GEMINI_ENABLED` (backend `.env`). It's currently `false` (instant heuristic fallbacks, **zero quota burn**) so the app is fully usable without burning the key. **For the demo: set `GEMINI_ENABLED=true` and use a billing-enabled key** (free tier = ~10 req/min, ~250/day; the morning brief alone is ~5 calls). Best demo hygiene: enable billing OR pre-create your demo tasks so tagging/clustering is already stored, then pace AI actions.

**✅ Integration verified (Sec 13):** automated full-journey pass = **14/14 checks** (create→tag→cluster→complete→brief→procrastination→cascade→reschedule→planning→vacation→audit→streak), **zero backend exceptions**. All 3 frontend routes serve 200, `next build` clean.

**✅ Done across sessions:** Feat 1 cluster cards, Feat 4 Cascade Map, Feat 6 anti-list actions, Feat 7 planning-fallacy hint (1.5×), Feat 8 Vacation Finder, Feat 10 Reschedule modal, Feat 11 (completion burst + streak flame + skill levels + 21/90 tracker + wins wall), Gemini timeout + `GEMINI_ENABLED` flag.

**Polish done (2026-06-30):** energy-match + micro-break (EnergyNow), planning-accuracy card, recovery-day shield, **theme toggle fixed** (glass-card was undefined + navy now theme-aware), **Recovery Mode** (1-task calm view), **missed-task re-sequencing agent + Overdue card**. Decided: **keep Speech-to-Text (voice), drop Gmail**. Integration still 14/14.

**Still TODO:** real Google sign-in popup (needs browser) + enable Speech-to-Text API for voice, "save context?" auto-pause prompt (Feat 5), single-mission "Start Session" CTA (Feat 11), browser console click-through, **deployment (Sec 14)**.

---

## 🐞 UI/UX issues to fix (user review — 2026-06-30, smallest-first)

> From a live click-through. Status: ☐ todo · ◐ in progress · ☑ done

1. ☑ **Badge contrast — FIXED.** Darkened skill/quadrant/trigger badge text to deep same-hue ink + bumped `.skill-badge` weight to 700. Files: [lib/types.ts](frontend/web/lib/types.ts), [ProcrastinationInsight.tsx](frontend/web/components/ProcrastinationInsight.tsx), `.skill-badge` in [globals.css](frontend/web/app/globals.css).
2. ☑ **Low-contrast tint-box text — FIXED (main offenders).** Root cause: making `navy` theme-aware turned text light in dark mode, so it vanished on hardcoded-light tint boxes. Set explicit dark ink on: ProcrastinationInsight first-step box, ContextSave breadcrumb, CreateTaskModal planning hint, VacationFinder cards, RescheduleModal energy badge. *(Still audit for any remaining tint boxes elsewhere.)*
3. ☑ **Reschedule (and Create) modal bleed-through — FIXED.** Added opaque `.modal-panel` class (solid `--bg2`) + darker overlay (rgba 0.72) + blur. Both modals now use it instead of translucent `.glass-card`. Files: [globals.css](frontend/web/app/globals.css), [RescheduleModal.tsx](frontend/web/components/RescheduleModal.tsx), [CreateTaskModal.tsx](frontend/web/components/CreateTaskModal.tsx).
4. ☑ **Create-Task "Hours" input — FIXED.** Root cause: no field labels (the "Hours" placeholder vanished once it defaulted to "1", so it looked like a bare number), cramped 1/3 width, and `step="0.25"` made the browser nag on non-multiples. Now: labelled Deadline / Est. hours / Difficulty fields, 2-col layout with room, `step="any"` + `inputMode="decimal"` for smooth entry. File: [CreateTaskModal.tsx](frontend/web/components/CreateTaskModal.tsx).
5. ☑ **Skill Constellation clarity — FIXED.** Root bug: colour map was keyed by `writing/design/code` but real tags are `analytical/creative/…`, so every cluster rendered the same blue. Re-keyed to real skills (distinct bright glows) + added a **colour→skill legend** under the canvas + clearer title ("Your skill sky") and explainer. *(Could still add on-canvas per-cluster text labels.)* File: [ConstellationMap.tsx](frontend/web/components/ConstellationMap.tsx).
6. ☑ **Gamification terms — FIXED.** "Stars lit→Wins (done)", "In orbit→In motion", "Skill clusters→Skill areas"; constellation legend now "✦ done / ○ to do" + plain-English explainer. Files: [journey/page.tsx](frontend/web/app/journey/page.tsx), ConstellationMap.tsx.
7. ☑ **Constellation now responsive + bigger — FIXED.** ConstellationMap measures its container via ResizeObserver and fills the available width (grows with the layout); height raised 320→380. Cluster cards already scroll horizontally and skill levels list grows vertically, so they scale fine. File: ConstellationMap.tsx.
8. ☑ **Typography — DONE (first pass).** Body font switched Space Grotesk → **Spectral** (calm, readable serif in the realm of the user's examples); kept **Fraunces** for display headings; Space Grotesk retained only for tiny badge chips. Files: [globals.css](frontend/web/app/globals.css) import + `font-family`, [tailwind.config.ts](frontend/web/tailwind.config.ts) `fontFamily.body`. *(Requires dev-server restart to apply. May still want a per-size weight/letter-spacing audit.)*
9. ☑ **Breathing Room (VacationFinder) text invisible — already FIXED** in issue #2 pass (dark ink on the light cards); earlier screenshot was pre-refresh.
10. ☑ **"Audit backlog" button more visible — DONE.** Was a faint outlined text link; now a filled gradient button. File: [tasks/page.tsx](frontend/web/app/tasks/page.tsx).

### 🔁 Round 2 review fixes (2026-06-30)
- ☑ **Removed badge pill backgrounds entirely** — user said the tinted-pill look is "very AI generated." Badges are now plain **coloured text** (bright skill hues, readable on dark) in **Spectral** serif, no background. `.skill-badge` has `background: transparent !important` so all inline pill bg's are killed in one place. Files: globals.css, types.ts, ProcrastinationInsight.tsx, RescheduleModal.tsx.
- ☑ **Modal overlay near-opaque** (was still bleeding the page through) — overlay now rgba(6,9,20,0.94) + blur(10) on Reschedule + Create modals.

### ❓ Status of optional Google features (answered to user)
- **Speech-to-Text: coded but NOT working yet.** Needs (a) **Cloud Speech-to-Text API enabled** + a real `GOOGLE_SPEECH_API_KEY` (the Gemini key does NOT work for the speech endpoint), and (b) `GEMINI_ENABLED=true` to parse the transcript. Currently **English-only** (`languageCode: "en-US"` hardcoded in voice.py) — would need a language param / auto-detect for multilingual.
- **Gemini key: confirmed live and working (2026-06-30).** `GEMINI_ENABLED=true` flipped in `backend/.env`; direct + async smoke tests against the real key both returned `SUCCESS` in ~1.2s. Key is never hardcoded anywhere in source — only read via `settings.gemini_api_key` from `.env` (gitignored). For GitHub: added root `.gitignore` (excludes `.env`, `.env.local`, `venv/`, service-account JSON). For Cloud Run deploy: key must go into **Secret Manager**, not `--set-env-vars`, so it never appears in deploy logs or the image. ⚠️ Observed: task creation through the running FastAPI app takes 10-15s end-to-end (vs 1.2s for an isolated Gemini call) — likely Neon DB round-trip latency from this network, not a Gemini issue; worth re-measuring once deployed to Cloud Run (same region as DB).
- **Google Calendar OAuth — code now wired (2026-06-30), needs a manual browser test.** Added a "Connect Calendar" button (Nav.tsx) that re-prompts Google sign-in with the `calendar` scope via a second `GoogleAuthProvider` (`lib/firebase.ts` → `calendarProvider`), extracts the OAuth access token from the popup result, and POSTs it to the already-existing `POST /users/me/oauth-tokens` endpoint. **Limitation:** Firebase's client-side popup flow never returns a refresh token, so the access token is only valid ~1 hour — user reconnects when it goes stale. This is fine for in-session use (vacation finder, reschedule, live calendar reads while the user is in the app) but NOT enough for the 6am unattended Cloud Scheduler morning-brief job, which will keep using deadline+energy-curve fallback as before. Still needs: (1) enable the Calendar API on the `life-saver-c2207` GCP project, (2) test the real popup in a browser with `NEXT_PUBLIC_DEV_AUTH=false` + `DEV_AUTH_BYPASS=false` (currently both `true` for dev bypass, so the button is inert in current local config).
- **Constellation IS live + data-driven** — it twinkles continuously and renders from the task list; new skills appear as new stars when the Journey page (re)loads. Not real-time across pages (refetch-on-focus is a possible enhancement).

### 📌 Product notes (from user, keep in mind)
- **21/90 journey stops at 90 days. ☑ DONE** — at ≥90 days HabitTracker now shows a 🎉 "You made it — 90 days … we'll stop the counter here; the habit is yours to keep" graduated success card. Everything else keeps working as normal.
- **Constellation realism ☑ DONE** — ConstellationMap rewritten as an animated canvas: twinkling colored stars (per-skill bloom + white-hot core + diffraction spikes on completed) on a night-sky backdrop with faint dust, matching the StarField background. Still open (#7): make the box bigger/responsive as clusters grow.
- **Google Calendar is NOT connected yet.** Calendar code exists but there's no stored OAuth token, so vacation-finder / scheduling / reschedule run purely off **task deadlines + the energy curve**, not real calendar events. Connecting it = the Google OAuth flow (a setup/deploy step). Same for FCM push.

---

## 0. Foundation (must work before anything else)

- [x] Backend runs locally (`uvicorn main:app --port 8000` — use host 127.0.0.1) — no startup errors
- [x] Neon Postgres connection stable (channel_binding fixed)
- [x] `/docs` loads and `/health` returns `{"status":"healthy"}`
- [◐] Firebase Auth — Admin SDK inits + token verification coded; dev bypass added. Real Google popup not yet tested.
- [x] Frontend runs (`npm run dev` → http://localhost:3000) — builds clean, serves 200
- [x] Frontend can call an authenticated endpoint end-to-end (verified via dev token: GET /tasks → render)
- [x] CORS allows http://localhost:3000
- [x] Dark/Light theme toggle works — fixed: `.glass-card` was undefined (cards had no styling) + `navy` text is now theme-aware (rgb var), inputs use `--field-bg`

---

## 1. Skill Graph Engine + Cognitive Session Batching

**Backend**
- [x] `POST /tasks` auto-tags skills via Gemini (verified: returns analytical/creative/communicative/… + complexity + eisenhower)
- [x] NetworkX graph: nodes = tasks, edges weighted by Jaccard similarity of skill tags
- [x] Louvain community detection → task clusters (networkx `louvain_communities`, greedy fallback)
- [x] Each cluster gets estimated total duration (suggested time slot via /schedule)
- [x] `GET /tasks/clusters` returns clusters with total hours
- [x] `GET /tasks/next-session` returns highest-priority cluster for now

**Frontend**
- [x] Skill badges render on every task card (colored per skill)
- [x] Skill Cluster cards — horizontal scrollable row on dashboard (SkillClusters.tsx)
- [x] "Next session" surfaced on Today page

---

## 2. Chronotype-Aware Energy Scheduling

**Backend**
- [x] Log `task_started` + `task_completed` events with timestamps in behavioral_events
- [x] After 14+ events: `chrono_service.infer_chronotype()` (statsmodels) — coded, default curve until enough data
- [x] Produce daily energy curve: `[{hour, energy_score 0.0–1.0}]` (verified via endpoint)
- [x] Scheduler (greedy fallback — OR-Tools not installed) assigns tasks→timeslots (verified /schedule/optimize)
- [x] Gemini function-calling version: get_energy_windows / get_calendar_events / create_calendar_event declared
- [x] `GET /schedule/energy-windows` returns the curve (verified)

**Frontend**
- [x] Energy forecast bars on Journey page (fixed to use energy_score)
- [x] Energy match indicator on dashboard (EnergyNow.tsx — current energy + work-fit guidance)

---

## 3. Procrastination Fingerprinter

**Backend**
- [x] `procrastination_agent.py` classifies 5 triggers: ambiguity, fear, overwhelm, boredom, resentment
- [x] Returns: trigger, trigger_explanation, intervention, first_step, estimated_start_minutes (verified)
- [x] `POST /agents/me/procrastination-check` + new `POST /agents/me/tasks/{id}/procrastination` (per-task) working
- [x] Detection signals wired: reschedule_count, days_old, open_without_progress_count, similar_completion_rate

**Frontend**
- [x] "Why am I avoiding this?" button on task cards (ProcrastinationInsight.tsx)
- [x] Procrastination panel shows trigger + intervention + "first step" CTA
- [x] First Step Injector — "Start →" sets task in_progress

---

## 4. Dependency Cascade Map

**Backend**
- [x] `build_dependency_dag()` from task.depends_on (now recomputed on create + update)
- [x] `get_critical_path()` (longest path by estimated_hours)
- [x] `get_cascade_severity()` — descendants downstream, returns severity + at_risk_titles + critical_path_affected (verified A→3, B→1)
- [x] `GET /tasks/{id}/cascade` endpoint; cascade_severity stored on each task
- [x] Missed-task re-sequencing — `resequence_agent.py` + `POST /agents/me/resequence` (Gemini plan + deterministic fallback; verified at-risk downstream)

**Frontend**
- [x] Cascade severity badge on task cards ("Delays N other tasks") — now has real data
- [x] Visual dependency view — badge expands to list blocked tasks (CascadeBadge.tsx)
- [x] Critical-path highlight (badge when on critical path)
- [x] Dependency picker in Create Task modal (so cascades can actually be created)
- [x] Overdue recovery card on dashboard (OverdueRecovery.tsx — expandable re-sequence plan)

---

## 5. Context Save State

**Backend**
- [x] `POST /tasks/{id}/context-save` — Gemini compresses brain dump → 3 bullets (verified output)
- [x] Stored in context_saves table
- [x] On task open: `GET /tasks/{id}/context-save` returns most recent context_save
- [ ] Auto-detect pause from behavioral_events (task_opened → app_closed within 30s, no completion)

**Frontend**
- [x] "Pause & save context" button → 10-second text prompt (ContextSave.tsx)
- [x] Breadcrumb (3 bullets) shown FIRST when reopening (panel loads latest breadcrumb)
- [ ] "Save your context?" prompt on detected pause

---

## 6. Anti-List Engine

**Backend**
- [x] Candidate criteria wired (not opened 30+ days · cascade=0 · reschedule>=5 · low urgency+importance · resentment)
- [x] `POST /agents/me/backlog-audit` — returns candidates + recommendation + reason (verified, health_score=95 on clean backlog)
- [x] Health score returned

**Frontend**
- [x] "Audit backlog" button on Tasks page
- [x] Anti-List review UI — per-task recommendation chips + reason
- [x] Quick abandon / delegate / defer actions (wired: abandon/delegate→abandoned, defer→+2 weeks)

---

## 7. Planning Fallacy Corrector

**Backend**
- [x] On completion: log actual_hours (via `/complete` + update; defaults to estimate, accepts real value)
- [x] Per-category inflation_factor = actual / estimated
- [x] `GET /users/me/planning-accuracy` (per-skill) + new `GET /users/me/planning-summary` (overall + per-skill)
- [x] Auto-correction suggestion powered by planning-summary (verified 1.5× on real data)

**Frontend**
- [x] Auto-correction hint in Create Task modal ("You estimated 2h. Your tasks run 1.5× longer → ~3h") — verified
- [x] Planning accuracy stats card on /journey (overall ×inflation + per-skill bars, PlanningAccuracyCard.tsx)

---

## 8. Vacation Finder + Break Window Calculator

**Backend**
- [x] Query tasks with deadlines in next 90 days
- [x] Continuous daily pressure map (free days included — fixed: was only scanning deadline-days)
- [x] Find low-pressure valleys below threshold, grouped into windows
- [x] Per-window blast_radius + tasks_at_risk + recommendation (verified: ranks clear runways first)
- [x] `GET /calendar/vacation-finder` returns ranked windows (verified 3 windows)
- [ ] Micro-breaks: same logic for 30-min windows today

**Frontend**
- [x] Vacation Finder view — ranked break windows with blast radius (VacationFinder.tsx on /journey)
- [x] Micro-break suggestion chip (in EnergyNow.tsx — suggests next energy-dip window today)

---

## 9. Morning Brief Agent (Primary Agentic Demo)

**Backend**
- [x] Autonomous Gemini function-calling chain verified (chained list_user_tasks → get_calendar_events → get_energy_windows → reasoned → narrative; tries send_push)
- [x] 4-sentence warm narrative brief verified (capacity / mission / skill session / watch-out) + deterministic fallback
- [x] `POST /agents/me/morning-brief` (now returns narrative synchronously) + `POST /agents/morning-brief/{user_id}` (scheduler)
- [ ] Daily 6am Cloud Scheduler trigger (deploy step)

**Frontend**
- [x] Daily Brief card at top of dashboard — narrative text (DailyBrief.tsx)
- [x] "Ask Gemini" button with loading state

---

## 10. Smart Rescheduling with Friction

**Backend**
- [x] Two-phase flow: `GET /tasks/{id}/reschedule-options` (preview, no mutation) + `PATCH /tasks/{id}/reschedule` (commit exact window)
- [x] Up to 3 viable windows, spread across 48h, high-energy free slots (verified)
- [x] Each window: energy score, tasks displaced, cascade impact count
- [x] 0 windows → no_options state with 4 alternatives
- [x] Friction: reschedule_count>=2 require reason (verified 422→200); >=3 auto-flagged in event metadata

**Frontend**
- [x] Full-screen Reschedule modal — "N viable windows" or "⚠ No viable windows" (RescheduleModal.tsx)
- [x] Window cards with energy bar + displaced count + cascade badge
- [x] Reason selector after 2 reschedules
- [x] Reschedule count badge on task cards (↺ N) + modal header

---

## 11. UX / Gamification (cross-cutting)

- [◐] Today's Mission card — "Start here" do-first tasks + next-session card shown; single-mission "Start Session" CTA TODO
- [x] Momentum Meter — circular gauge, reflects completion ratio (now correct after status fix)
- [x] Task completion micro-celebration — teal #00E5CC comet/particle burst (CompletionBurst.tsx)
- [x] Constellation Map (/journey) — task = star, cluster = skill, completed = bright glow (fixed to skill_tags/completed)
- [x] 21/90 tracker — progress path with milestones at 7/14/21/30/60/90 (HabitTracker.tsx on /journey)
- [x] Streak flame (StreakFlame.tsx in Nav) + Recovery Day Shield (RecoveryShield.tsx on /journey — verified 4→3)
- [x] Recovery Mode — simplified 1-task UI, softer colors (RecoveryMode.tsx; toggle on dashboard, persists)
- [x] Skill levels — 2 completions/category = +1 level → "Writing Level 4" (SkillLevels.tsx)
- [x] Wins Wall — end-of-day completions on /journey (framed positively)

---

## 12. Google Technologies — TRIMMED to essentials

**KEEP (core to the features above):**
- [x] Gemini **2.5 Flash** — LLM, function calling, all AI features *(2.0-flash free tier is dead; use 2.5 via `GEMINI_MODEL`)*
- [◐] Firebase Authentication — Admin SDK + token verify coded; real Google sign-in popup untested
- [◐] Google Calendar API — service coded; needs user OAuth tokens stored (returns empty without them)
- [◐] Firebase Cloud Messaging (FCM) — service coded; needs `fcm_token` on user (skips send without it)
- [x] Neon Postgres — database connected & stable (Cloud SQL on deploy)
- [ ] Google Cloud Run — backend hosting (deploy step)
- [ ] Google Cloud Scheduler — morning brief 6am, backlog audit Sunday 9am

**OPTIONAL / DROP — DECIDED 2026-06-30:**
- [x] ✅ **KEEP Google Speech-to-Text** — voice task entry. Backend (voice.py) + mic UI both code-complete & route verified. **Just enable the Speech-to-Text API on the GCP project** (uses GOOGLE_SPEECH_API_KEY, falls back to Gemini key). Self-contained, no OAuth.
- [ ] ❌ **DROP Gmail API** — code-complete but needs sensitive `gmail.readonly` OAuth scope + inbox access + the un-connected OAuth flow. Heavier/riskier to demo; skip per plan.
- [ ] ~~Google Firestore~~ — **DROP**. Postgres already handles state; real-time sync not needed for single-user demo.
- [ ] ~~Google Cloud Storage~~ — **DROP**. Data exports/file attachments not core to any demo feature.

> **Minimum viable Google stack for the demo:** Gemini + Firebase Auth + FCM + Calendar + Cloud SQL/Neon + Cloud Run + Cloud Scheduler. That's 7 technologies — enough to be impressive without over-scoping.

---

## 13. Make Everything Actually Work (integration pass)

- [x] Every backend endpoint exercised (automated dev-token integration pass: **14/14 checks**)
- [◐] Every frontend page renders — all 3 routes serve 200, no compile errors (client render not browser-verified)
- [◐] Loading + empty + error states — present on most components; not audited page-by-page
- [x] Create task → skills auto-tagged → appears in cluster → shows on dashboard (full loop verified)
- [x] Complete task → status=completed (momentum + constellation derive from this) — verified
- [x] Morning brief button → narrative returned (357 chars; real Gemini path verified earlier)
- [x] No unhandled exceptions in backend logs during the full integration pass
- [ ] No red errors in browser console (needs a real browser click-through)

---

## 14. Deployment (last)

- [ ] Dockerfile for backend
- [ ] Deploy backend to Cloud Run
- [ ] Migrate Neon → Cloud SQL (or keep Neon)
- [ ] Set up Cloud Scheduler jobs (morning brief, backlog audit)
- [ ] Deploy frontend (Vercel or Cloud Run)
- [ ] Update CORS + env vars for production URLs
- [ ] Final end-to-end test on deployed URLs
