# Heat-Shield Backend

FastAPI service powering the Kavach heat-stress app: real weather lookups,
a NOAA heat-index + OSHA-tier risk score, worker/crew tracking, and alerts.

## Run it

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Server comes up at `http://localhost:8000`. Interactive API docs (test
endpoints without touching the frontend) are auto-generated at
`http://localhost:8000/docs`.

Uses SQLite (`heatshield.db`, created automatically on first run) — no DB
setup needed. Delete the file to reset all data.

## Weather source

Uses [Open-Meteo](https://open-meteo.com) — **no API key required**, so
nothing to configure and nothing that can fail from a missing/expired key
mid-demo. Results are cached in-memory for 3 minutes per location to avoid
hammering the API when the frontend re-submits readings on every slider drag.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/login` | `{name, role, job_role?}` → gets or creates a worker, returns `worker_id` |
| POST | `/api/readings` | Submit shift context + GPS → returns weather, heat index, risk score, recommendations. Auto-creates an alert if score ≥ 85 |
| GET | `/api/workers` | Crew roster with each worker's latest risk status — powers the supervisor table |
| GET | `/api/alerts` | Unacknowledged high-risk alerts |
| POST | `/api/alerts/{id}/ack` | Acknowledge an alert |
| GET | `/api/weather?lat=&lon=` | Raw weather passthrough (debugging) |

## Risk model

`heat_calc.py`:
1. **Heat index** — NOAA/Rothfusz regression from temperature + humidity
   (the actual formula the US National Weather Service uses for heat
   advisories).
2. **Base score** — heat index mapped to OSHA/NIOSH risk bands (Caution /
   Extreme Caution / Danger / Extreme Danger).
3. **Modifiers** — added for heavy work, heavy/PPE clothing, low hydration,
   overdue rest breaks, and reported cardiac/other health conditions.
4. Final score (0–100) maps to Low / Moderate / High risk, each with
   generated recommendations. Score ≥ 85 fires an alert.

## Connecting the frontend

`frontend/main.html` is already wired to call this API (see `API_BASE` near
the top of its `<script>` block — defaults to `http://localhost:8000`). If
you deploy the backend somewhere, set `window.HEATSHIELD_API_BASE` before
the script runs, or just edit that constant directly.

If the backend is unreachable, the frontend silently falls back to a local
JS copy of the same scoring formula (with a simulated weather reading) so
the demo never breaks on stage — it'll just say "OFFLINE MODE" in the
header instead of live weather.

## Files

```
backend/
  main.py         FastAPI app + routes
  models.py       SQLAlchemy models (Worker, Reading, Alert) + DB setup
  schemas.py      Pydantic request/response shapes
  heat_calc.py    Heat index + risk scoring engine
  weather.py      Open-Meteo client with caching
  requirements.txt
```
