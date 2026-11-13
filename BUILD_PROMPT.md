# GRAMROUTE: ONE-SHOT BUILD PROMPT

You are a senior full-stack engineer working inside the project folder that is currently open. It contains an existing, working **medical kiosk** (multi-page HTML + a backend). Your job is to **convert that kiosk into GRAMROUTE, a rural student transportation kiosk**, keeping exactly the way the medical kiosk works and replacing the medical content with transport content.

Do not ask me questions. Do not stop to present a plan. Build it, run it, test it, fix it, and finish with the report in section 12. If something is ambiguous, pick the simpler option and write the decision in `DECISIONS.md`.

---

## 0. THE CORE IDEA (read twice)

The medical kiosk flow is:

`index.html` (language) → `patient-details.html` (form + virtual keyboard) → `symptoms.html` (guided questions) → `summary.html` (review table) → submit to backend → back to start.

GRAMROUTE keeps the same **feel and mechanics** (large touch UI, language first, native-script buttons, custom on-screen keyboard that switches layout per language, numeric keypad, Back/Proceed footer, spoken instructions, review table before submit, backend save, auto-reset) but the **purpose** changes:

> A student walks up, picks a language, and tells the kiosk one of three things: **my bus is not available**, **my road is blocked**, or **there are not enough seats**. The local backend then actually computes a rescue: which verified vehicle, which pickup point, which route, which students are left without a seat. The student gets a reference number and instructions.

Tagline: *"No student left stranded. Every village connected to education."*
Full name: *Gram-Based Rural Accessibility, Mobility and Route Optimization Using Technology.*

**Zero medical content may remain.** At the end, `grep -ri -E "patient|medical|doctor|symptom|allerg|vital|triage|clinic"` over the served files and backend must return nothing (except the preserved copies in `_reference/`).

---

## 1. STEP 1: INSPECT BEFORE WRITING (10 minutes max)

1. List the folder. Identify: the backend language/framework, how static files are served, the DB, the run command, existing API routes (e.g. `/api/patients`, `/api/visits/...`), and any other pages (`symptoms.html`, etc.).
2. Read `index.html`, `patient-details.html`, `summary.html` fully. Note exactly how they do: `?lang=` passing, `sessionStorage`, `keyboardLayouts`, `renderDynamicKeyboard`, `translations`, `applyTranslations`, `playInstructionVoice` (browser `speechSynthesis`), fullscreen, and `fetch('/api/...')`.
3. Copy the three originals (and any other medical pages) to `_reference/` untouched.
4. **Use the stack that is already in this folder.** Do not migrate to React/TypeScript/Vite. Keep multi-page vanilla HTML/CSS/JS served by the existing backend. If the existing backend is Node, stay in Node; if Python, stay in Python. Add dependencies only if truly needed, and none that need internet at runtime.
5. If a previous GRAMROUTE engine exists in the folder (a `server.py` with Bus Rescue / Route Rescue / Capacity engines), reuse its logic; otherwise write the engines fresh in the folder's backend language.

---

## 2. SCREEN FLOW (one HTML page per step, same pattern as the reference)

Language travels in `?lang=xx`. Transaction state travels in `sessionStorage` under one key (`gr_session`) as JSON, so **Back never loses entered data**. Shared logic goes in shared files, not copy-pasted per page:

- `kiosk.css`: the reference look (bg `#F8FAFC`, primary `#1E56A0`, teal `#0D9488`, white cards, 16px radius, 3px soft borders, `:active` scale + blue border, 1.5rem+ text, 64px+ touch targets).
- `i18n.js`: translation dictionary + `t(key)` with fallback chain (selected language → Hindi/English fallback, never throws on a missing key) + RTL handling.
- `keyboard.js`: the virtual keyboard, extracted and generalized from the reference.
- `voice.js`: spoken instructions (section 7).
- `session.js`: session state, inactivity timer, API helper.

Pages:

| # | File | Purpose |
|---|------|---------|
| 1 | `index.html` | Welcome, tagline, **all 22 language buttons** (native script + English name), Help button, fullscreen on first touch, clears session on load |
| 2 | `services.html` | 8 large cards: Find My Bus, My Bus Is Not Available, My Route Is Blocked, I Need An Alternative Ride, Report A Problem, Check Seat Availability, Track My Journey, Get Help. Each routes to a real feature. |
| 3 | `student-details.html` | Mirrors `patient-details.html`: name, student ID, mobile (optional), village (list), institution (list), seats needed (numeric). Option "continue without saving a profile". Lookup by student ID. Virtual keyboard for text, numeric keypad for numbers. |
| 4 | `journey.html` | Village, destination, date, arrival time, pickup point, current bus (all **selectable lists**, minimal typing), normal vs emergency request |
| 5 | `problem.html` | Three big choices: **Bus not available / Road blocked / Not enough seats**, plus "normal journey search". Asks only the questions relevant to the choice (see section 4). |
| 6 | `summary.html` | Mirrors the reference review table: student, village, destination, date/time, route, seats, problem, pickup, accessibility. Buttons: **Back/Edit** and **Confirm and Find Transport**. Never auto-submits. |
| 7 | `processing.html` | Real progress: it shows steps as the backend call actually completes ("Checking available buses", "Checking alternative routes", "Finding seats", "Preparing instructions"). No fake timers: the steps map to real response stages or a single honest "Calculating…" state. |
| 8 | `result.html` | Outcome + reference number + vehicle, vehicle type, pickup point, departure time, seats allocated, route, warnings, **status badge: `RECOMMENDED` / `AWAITING OPERATOR CONFIRMATION` / `CONFIRMED` / `NO VEHICLE AVAILABLE`**. Print travel slip (`window.print()` with a print stylesheet; thermal printer is out of scope unless a device exists). SMS-ready text shown and queued, never claimed as sent. |
| 9 | `done.html` | "Your request has been recorded." + reference number + Print / Check another journey / Return to start |

Also: `track.html` (journey history by reference number or student ID), `help.html` (emergency/contact numbers loaded from config only; **never invent phone numbers**, show "Not configured" if empty), `seats.html` (live seat availability per vehicle from the DB).

Inactivity: after 90 s of no touch, show a 15 s warning modal ("Still there?"). If a transaction is in progress, keep the data until the warning expires, then clear session and return to `index.html`.

---

## 3. THE 22 LANGUAGES

Languages (code: native name): as, bn, brx, doi, gu, hi, kn, ks, kok, mai, ml, mni, mr, ne, or, pa, sa, sat, sd, ta, te, ur. All 22 appear on the welcome screen in correct native script (Bodo/Dogri/Konkani/Maithili/Sanskrit/Nepali/Marathi in Devanagari; Santali in Ol Chiki; Manipuri in Meitei Mayek or Bengali script, and state which; Kashmiri/Sindhi/Urdu in Perso-Arabic).

The reference has hand-written translations for 9 languages only. Do it like this:

- Put every string in **one** dictionary file keyed by stable keys (`svc.findBus`, `err.required`, …). Per-language packs live in `lang/<code>.json` so each can be tested independently.
- **Fully translate** the languages you can translate reliably: at minimum the 9 already in the reference (en, hi, kn, ta, te, ml, mr, bn, gu) plus as many of the remaining 13 as you can do accurately (Urdu, Punjabi, Odia, Nepali, Assamese are usually reliable).
- For languages whose pack is incomplete, **fall back per key** to Hindi (or English for non-Devanagari) and show a small visible badge `Partial translation`. Never present machine-garbled text as translated. Never leave an English-only button for a language.
- `lang/STATUS.md` + a `/api/languages` endpoint expose, per language: interface translation (full/partial/none), keyboard layout (native/English-fallback), TTS (tested or not), ASR (none unless truly integrated), and tested yes/no.
- RTL: set `dir="rtl"` for ur, ks (Perso-Arabic), sd (Perso-Arabic); fonts via locally bundled files or the OS stack (no Google Fonts CDN, because the kiosk is offline).

## 4. KEYBOARD (essential)

Extract the reference's `keyboardLayouts` / `renderDynamicKeyboard` / `setupKeyboard` into `keyboard.js`.

- English QWERTY; Devanagari, Bengali-Assamese, Gurmukhi, Gujarati, Odia, Tamil, Telugu, Kannada, Malayalam, Perso-Arabic (Urdu/Kashmiri/Sindhi) layouts; Ol Chiki and Meitei Mayek if you can do them correctly. Where a layout is not provided, use the English keyboard **and** show "Type in English or choose from the list". Do not pretend unsupported characters can be typed.
- Language switch button on the keyboard (native ⇄ English).
- Numeric keypad for phone, student ID digits, seat count.
- Keys: character, Space, Backspace, Clear, Done. Keyboard slides up and **scrolls the focused field into view so it is never hidden**.
- Validation: name ≥2 chars, phone 10 digits if given, seats 1 to the max available, with translated error messages.

## 5. DATA MODEL (use the existing DB, SQLite if none)

Tables with PK/FK/indexes: `villages`, `pickup_points`, `institutions`, `students`, `operators`, `vehicles` (type, reg no., capacity, `verified`, `available`, `operator_id`, `base_village`), `routes`, `road_segments` (a, b, km, minutes, `status` open/blocked, `verified` 0/1, reason), `schedules`, `journey_requests` (reference no., status, problem type, created_at), `seat_allocations` (**UNIQUE(vehicle, trip, seat_no)** so a seat can never be double-assigned), `disruptions` (type, segment, reporter, verified/unverified/rejected, resolved), `demand_history`, `notifications` (queued/sent, with `sent` only if a real gateway confirmed, otherwise `queued`), `incidents`, `audit_logs`, `users` (role admin/operator), `lang_config`.

Capacity is enforced both in code **and** by a DB check; an allocation that exceeds capacity must raise an error.

Public screens and logs never show student address or phone. Phone is stored only if given, never displayed back in full (mask it).

## 6. THE THREE ENGINES (deterministic, in the backend, unit-tested)

**A. Bus Rescue.** Input: cancelled/failed vehicle or trip. Steps: find assigned students → group by village/pickup → list verified, available vehicles with free seats that can reach the pickup via the *current open* road graph and still reach the institution → allocate (priority: exam day, accessibility need, then village/arrival deadline, with the rule order stored in config and shown to admin) → persist allocations → return per-vehicle assignments, **unallocated list**, suggested extra vehicle/batch, and a plain-language explanation. Never exceed capacity, never use an unverified vehicle, never say "all rescued" if anyone is left.

**B. Route Rescue.** Input: disruption report (segment, type, reporter, verified or not). Record it; mark the segment blocked in the routing graph (an unverified report blocks the route *as a precaution* but is labelled `UNVERIFIED`); find affected routes and students; Dijkstra (or A*) on remaining edges; return old vs new path, extra km/min, alternative pickup points, and `"estimated, not verified safe"` wording. Never route through a blocked edge. If no path exists, say so.

**C. Capacity Intelligence.** Input: demand set + available vehicles. Cluster by village + destination + departure window, allocate seats by the configured priority, return demand, capacity, allocated, unallocated, shortage, per-vehicle fill, recommended extra vehicles, staggered batch suggestion. Re-run when a vehicle is added. **Exact reproducible demo: 100 students, vehicles totalling exactly 60 seats → allocated 60, unallocated 40, shortage 40**, deterministic (fixed seed/order).

The engines must interact: a road closure can remove a vehicle's reachability, which triggers Bus Rescue, which can trigger a capacity shortage. The "Combined crisis" demo runs A → B → C in that order against shared state and shows the cumulative result.

Demand forecasting: from `demand_history`, compute weekday/exam-adjusted averages and flag likely shortages; label all demo forecasts **"Illustrative: based on simulated history"**.

Ride matching: group students by village, destination, time window, and seats; compute cost-per-student from the vehicle's configured cost / seats allocated; only verified vehicles.

## 7. VOICE (honest version)

- `voice.js` speaks the instruction for every screen in the selected language using the **local** `speechSynthesis` voices only. Check `voice.localService`; if the best voice for the language is not local or not present, do not speak and show "Voice not available for this language" plus the text. Never call an internet TTS URL.
- Controls: Repeat, Slow, Mute, always with the text on screen.
- Speech **input**: implement a pluggable `/api/asr` endpoint abstraction. Inspect hardware and whether a local model (AI4Bharat IndicConformer, Vosk, Whisper.cpp, etc.) can realistically be installed in this environment. If it can't, ship the abstraction + the text/touch fallback, mark ASR `none` in the language matrix, and say so. **Do not put a microphone icon over a text box. Do not use the browser Web Speech Recognition API, because on Chrome it sends audio to the cloud.**
- Do not download large model collections blindly.

## 8. OFFLINE

PWA with a service worker caching all kiosk pages, CSS, JS, language packs, and `manifest.json`; no CDN links anywhere (fonts, icons, libraries are local files or inline SVG). Header indicator shows `Offline / Local server` vs `Network detected`. Maps: no online tiles. Use an inline SVG schematic of the local road graph (villages, pickup points, blocked roads in red, alternative path highlighted) plus a text route list. Add `npm`/`pip` installs only for local use at build time.

## 9. ADMIN and OPERATOR (separate, not linked from kiosk screens)

Entry: `/admin` and `/operator`, with a login (demo credentials documented in README, e.g. admin / `gramroute-admin`, operator / `gramroute-op`, hashed in DB). Kiosk pages have **no** link to them.

**Admin:** overview metrics (all from DB: students, villages, institutions, vehicles, available vehicles, demand, seats, unallocated, active disruptions, pending reports, today's bookings); CRUD for students, vehicles, routes/segments/pickups; verify/reject/resolve disruptions; view/reallocate allocations; add a vehicle and re-run capacity; demand analytics + forecast; settings (emergency contacts, languages, backup/export DB); audit log.

**Operator:** sign in, own vehicle only (enforce server-side: an operator may not read or change another operator's records); set available/unavailable, update free seats, report breakdown/delay/road problem, accept/reject proposed assignments, confirm departure/arrival, boarding counts. Every action updates the DB and audit log.

## 10. DEMO MODE (`/demo`)

Fictional seed data, clearly labelled **SIMULATED**. Buttons: 1) Bus breakdown, 2) Road closure, 3) Demand surge (100/60), 4) Combined crisis, 5) Offline-mode check (a page that makes a request to an external host, shows it failing, then proves kiosk/engines still work), and **Reset demo** (restores seed exactly; repeatable from any state). Each button changes real DB state, calls the real engine, and shows the numbers plus a short explanation of *why* the engine decided that.

Seed must include: 3+ villages, 1+ college and 1 school, 100+ students, government buses, shared autos, vans, community vehicle (some unverified, to prove they are never assigned), connected roads, one pre-existing blocked road, one known alternative route, schedules, historical demand.

## 11. TESTING (you must run these, not just write them)

Automated tests for: the 100/60 scenario (60/40); bus rescue never exceeding capacity; unverified vehicle never assigned; double-seat prevented by the DB; closed segment never used; no-path case; operator isolation; booking decrements free seats; reset restores seed; language packs have no missing keys that crash; kiosk page set contains 22 language buttons; no medical strings (grep test).

If a headless browser is available (Playwright/Chromium), run a UI smoke test of the full flow Welcome → result and the keyboard. If not, say "browser verification not performed".

**Process rules:** start servers in the background with a log file and a timeout, never run a blocking command that can hang the session; after each milestone, run the app and a `curl` check before moving on; fix errors instead of reporting them.

## 12. DELIVERY

Work in this order and run after each: (1) inspect + reference copy, (2) DB + seed + 3 engines + tests, (3) shared JS/CSS + all kiosk pages end-to-end, (4) admin + operator, (5) i18n/keyboards/voice, (6) PWA/offline + demo mode, (7) docs.

Write `README.md` (install, start, URLs, logins, demo walkthrough, architecture, language capability matrix, test results, known limitations), `DECISIONS.md`, and a requirements/package file.

**Final message must contain:** exact project folder path; exact install command; exact start command; local URLs (kiosk, admin, operator, demo); logins; test output summary (pass/fail counts); what is genuinely complete; what is not; known bugs. Verify the files exist in the folder with `ls` before claiming delivery. Never claim SMS was sent, GPS exists, offline speech works, or a language is fully translated unless it is true and tested.

## NON-NEGOTIABLE

Real backend, no fake AI, no dead buttons, no invented vehicles/seats/phone numbers, never exceed capacity, never assign unverified vehicles, never call a route "safe" unless verified, no internet dependency for any core flow, reference files preserved, medical content fully removed, every unfinished feature documented honestly.
