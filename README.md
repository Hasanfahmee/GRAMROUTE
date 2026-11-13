# GRAMROUTE (prototype)
Run: `python3 server.py` → http://localhost:8000 (kiosk / Admin / Demo tabs). Tests: `python3 tests.py`. Python 3 stdlib only, no internet.
Implemented: SQLite data, Bus Rescue, Route Rescue (Dijkstra, blocked edges removed), Capacity engine (priority exam>access>none), booking with capacity checks, weekday-mean forecast (illustrative, seeded history), typed keyword intents, 3 demo simulations + reset, audit log.
NOT implemented: voice (ASR/TTS), 19 of 22 languages (en/hi/kn labels only, not RTL-tested), LLM, Leaflet maps, PWA/service worker, operator terminal, React/FastAPI, ride matching, student ticket/journey screens, auth.
Data is fictional. Routes are not verified safe.

## Voice (added)
Kiosk 🎤 Speak: uses the BROWSER speech recognition (Chrome; needs HTTPS or localhost). Audio may go to the browser vendor's service, so it is NOT offline. Answer comes from the local DB via keyword intent matching, spoken with the device's speech voices (local voice preferred). Languages with no installed voice show text only.
## Deploy
`Procfile` + `PORT` env var supported: push to public GitHub, deploy on any Python host (Render/Railway). Data resets with the host disk.
