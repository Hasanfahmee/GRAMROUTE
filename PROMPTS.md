# Prompt log and iteration history

Technique used throughout: role-split prompts, priority tiers (P0 to P3), non-negotiable rules, exact acceptance numbers, and a "test it, fix it, don't claim what isn't true" instruction.

## Iteration 1: master autonomous build prompt
**Goal:** a complete offline rural transport system with three engines (Bus Rescue, Route Rescue, Capacity), kiosk, admin, 22 languages, voice.
**Key prompt ideas:** act as a team of engineers; build don't plan; seed realistic data; never exceed capacity; never fake AI; if time is short, follow P0 > P1 > P2 > P3.
**Result:** working Python and SQLite backend with the three engines, 3 simulation buttons, 8 automated tests.
**Problem:** scope too large for one pass, and the UI was a plain dashboard, not a kiosk.

## Iteration 2: convert a reference kiosk
**Prompt:** study a medical kiosk (language grid, form with virtual keyboard, review table, spoken instructions) and transfer the same interaction pattern to transport. Full text: `docs/BUILD_PROMPT.md`.
**Why rewritten:** the first prompt asked for React/Vite while the reference was multi-page HTML, so the stack conflicted. The new prompt says "use the stack already in the folder", maps each medical page to a transport page, and adds a grep check that no medical text remains.

## Iteration 3: voice
**Prompt:** add voice input and output, then make the system read what is on the screen like the reference does.
**Bug:** first version only spoke with locally installed voices, so it was silent on most machines. **Fix:** match the reference's behaviour (speak every screen automatically with the best available voice for the language), add Read screen, Slow and Mute, plus a tap-to-speak microphone using browser speech recognition. The UI states honestly that this is not offline.

## Iteration 4: surprise hurdle, Exam Day Crisis
**Prompt:** 2 government buses fail, demand +40%, a road floods, exams within 2 hours. Reallocate buses, find alternatives, prioritise exam students.
**Built:** a combined engine that runs all three engines on shared state, orders students by exam time, plans a second batch and flags late arrivals.
**Bug found by tests:** the demand-surge test showed 0 unallocated because the added vehicles raised capacity above demand. **Fix:** adjusted scenario sizes and kept the check that allocated + unallocated = demand.

## Iteration 5: one unified product
**Prompt:** put everything in the kiosk, show full solutions (vehicle, pickup, departure, arrival, second batch), add keyboards for all 22 languages, add voice commands.
**Built:** departure schedules, arrival estimates, second-batch times, 22 native keyboard layouts, map and emergency screens, voice navigation.

## Debugging log
- Foreground server command hung the session; fixed by running servers in the background with a timeout.
- A file copy to the outputs folder silently failed; fixed by verifying with `ls` before claiming delivery.
- Front-end JavaScript was syntax-checked with `node --check`; the backend is covered by 10 unit tests (capacity limits, closed roads never used, booking, persistence, exam crisis, intents).

*(Add your own exact chat prompts below if judges want the raw text.)*
