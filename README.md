# GRAMROUTE
**Gram-Based Rural Accessibility, Mobility and Route Optimization Using Technology**
*No student left stranded. Every village connected to education.*

A touchscreen village kiosk that tells a rural student, in their own language, which vehicle to take, where to board, when it leaves and when it arrives, even when buses break down, roads flood and demand exceeds seats. Built for **ROUTELESS: The Last Mile**, including the **Exam Day Crisis** surprise hurdle.

**Live demo:** _paste your deployed link here_

## The problem
Rural students depend on a few government buses. When a bus fails, a road floods, or too many students show up, nobody re-plans, and students miss class or exams.

## What GRAMROUTE does
| Situation | What the system does |
|---|---|
| **Bus unavailable** | Finds the affected students, then re-seats them on other verified vehicles that can reach their village, never beyond a vehicle's seat capacity. |
| **Road blocked** | Removes the blocked road from the road graph and recalculates the route with Dijkstra's algorithm. A closed road is never used. |
| **Demand > seats** | Allocates seats by transparent priority (exam, then accessibility, then others), reports who is left without a seat, and schedules a second batch. |
| **Exam Day Crisis** | One button: 2 government buses down, demand +40%, flood closes a road, exams within 2 hours, and all three engines run together on the same data. |

### Exam Day Crisis result (reproducible, seeded data)
- 93 students need transport (66 + 27 surge) but only 56 seats remain after 2 buses fail.
- **All 36 exam students are seated first** (earliest exam first); 33 of 36 reach on time, and the system tells the exam centre the other 3 arrive up to 6 minutes late because of the flood detour.
- The other 37 students go in a **second batch at 09:25**, so all 93 are transported.
- Without any planning, 87 students would have had no ride.

## Why it stands out
1. **Real engines, not a mock-up.** Every number comes from the backend and SQLite database, computed on each request. Nothing is hard-coded.
2. **Safe by design.** Capacity can never be exceeded, unverified vehicles are never assigned, and blocked roads are never routed through (covered by automated tests).
3. **Works for people with low literacy or no smartphone.** A kiosk with big buttons, spoken instructions, and an on-screen keyboard in the script of **all 22 scheduled languages**.
4. **Talk to it.** Tap the microphone and ask about seats, routes, booking or exams. Saying "emergency" runs the exam-day plan.
5. **Offline-first core.** Python standard library only, with a local SQLite database, local road graph and local optimisation. No cloud API, no API keys.
6. **Honest about uncertainty.** Travel times are estimates, and the data is clearly fictional demo data.

## How it works
```
Student kiosk (static/kiosk.html)  <--HTTP-->  server.py  <-->  SQLite
  language -> service -> details -> review      Bus Rescue      vehicles, students,
  -> result, voice in/out, 22 keyboards         Route Rescue    road graph, schedules,
  map + exam-day emergency                      Capacity engine reports, audit log
                                                Exam Day engine, intent matcher
```
- **Bus Rescue**: reassigns students of a cancelled vehicle within capacity and reachability.
- **Route Rescue**: Dijkstra over open roads only; reports are logged.
- **Capacity engine**: priority allocation, unallocated report, extra-vehicle suggestion, demand forecast.
- **Exam Day engine**: combines the three engines, then plans a second batch and notifies of late arrivals.
- **Voice**: browser speech for input and output; a keyword matcher maps what you say to real database queries and actions.

## Run locally
```
python3 server.py        # then open http://localhost:8000
python3 tests.py         # 10 automated tests
```
Python 3.9+ only. No installs needed.

## Deploy
Push to a public GitHub repo, then create a **Render** Web Service from it: Build command `pip install -r requirements.txt`, Start command `python3 server.py`. The `PORT` variable is read automatically. Voice input needs the HTTPS link Render gives you, and Chrome or Edge.

## Language support (honest matrix)
| Capability | Status |
|---|---|
| On-screen keyboard in native script | All 22 languages plus English (Ol Chiki and Meitei Mayek need those fonts installed) |
| Interface translation | English, Hindi, Kannada complete; the other languages show English text |
| Voice input | Uses Chrome's speech recognition: Assamese, Bengali, Gujarati, Hindi, Kannada, Malayalam, Marathi, Nepali, Odia, Punjabi, Tamil, Telugu, Urdu, English. Other languages fall back to Hindi/Urdu/English recognition. **Not offline; audio may go to the browser vendor.** |
| Voice output | The device's installed voices (works for languages the device supports) |
| Understanding spoken requests | Keyword matching in several languages, not an LLM |

## Known limitations
No admin dashboard or operator terminal yet, no real GPS/SMS (messages are not sent), no offline speech model, and the data is simulated. These are the next steps.

## Files
`server.py` (engines + API) · `static/kiosk.html` (kiosk UI) · `tests.py` · `PROMPTS.md` (prompt log) · `docs/BUILD_PROMPT.md` (full build prompt)
