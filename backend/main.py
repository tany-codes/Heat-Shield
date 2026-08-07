from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import models
import schemas
from weather import get_current_weather, WeatherError
from heat_calc import calculate_risk

models.init_db()

app = FastAPI(title="Heat-Shield API")

# Wide open for hackathon demo purposes — tighten before real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "heat-shield-api"}


# ---------------------------------------------------------------- auth ----
@app.post("/api/login", response_model=schemas.LoginResponse)
def login(req: schemas.LoginRequest, db: Session = Depends(models.get_db)):
    """No password — hackathon-simple. Looks up or creates a worker by name."""
    worker = db.query(models.Worker).filter(models.Worker.name == req.name).first()
    if not worker:
        worker = models.Worker(name=req.name, role=req.role, job_role=req.job_role or "General")
        db.add(worker)
        db.commit()
        db.refresh(worker)
    else:
        worker.role = req.role
        db.commit()
    return schemas.LoginResponse(worker_id=worker.id, name=worker.name, role=worker.role)


# ------------------------------------------------------------- readings ---
@app.post("/api/readings", response_model=schemas.ReadingResponse)
def submit_reading(req: schemas.ReadingRequest, db: Session = Depends(models.get_db)):
    worker = db.query(models.Worker).filter(models.Worker.id == req.worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="worker not found")

    try:
        weather = get_current_weather(req.lat, req.lon)
    except WeatherError:
        # Fallback so a demo never hard-fails if the weather API hiccups.
        weather = {"temp_c": 34.0, "humidity": 60.0, "source": "fallback"}

    result = calculate_risk(
        temp_c=weather["temp_c"],
        humidity=weather["humidity"],
        work_type=req.work_type,
        clothing=req.clothing,
        hydration_glasses=req.hydration_glasses,
        rest_minutes=req.rest_minutes,
        health=req.health,
    )

    reading = models.Reading(
        worker_id=worker.id,
        lat=req.lat,
        lon=req.lon,
        work_type=req.work_type,
        clothing=req.clothing,
        hydration_glasses=req.hydration_glasses,
        rest_minutes=req.rest_minutes,
        health=req.health,
        temp_c=weather["temp_c"],
        humidity=weather["humidity"],
        heat_index_c=result["heat_index_c"],
        score=result["score"],
        label=result["label"],
        level=result["level"],
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    if result["alert"]:
        db.add(models.Alert(worker_id=worker.id, reading_id=reading.id, score=result["score"]))
        db.commit()

    return schemas.ReadingResponse(
        temp_c=weather["temp_c"],
        humidity=weather["humidity"],
        heat_index_c=result["heat_index_c"],
        score=result["score"],
        label=result["label"],
        level=result["level"],
        description=result["description"],
        recommendations=result["recommendations"],
        alert=result["alert"],
    )


# --------------------------------------------------------------- workers --
@app.get("/api/workers", response_model=list[schemas.WorkerStatus])
def list_workers(db: Session = Depends(models.get_db)):
    """Crew roster with each worker's latest reading — powers the supervisor table."""
    workers = db.query(models.Worker).filter(models.Worker.role == "worker").all()
    out = []
    now = datetime.utcnow()
    for w in workers:
        latest = w.readings[0] if w.readings else None
        out.append(
            schemas.WorkerStatus(
                worker_id=w.id,
                name=w.name,
                job_role=w.job_role,
                score=latest.score if latest else None,
                label=latest.label if latest else None,
                level=latest.level if latest else None,
                last_reading_at=latest.created_at if latest else None,
                shift_minutes=int((now - w.shift_start).total_seconds() // 60),
                minutes_since_reading=(
                    int((now - latest.created_at).total_seconds() // 60) if latest else None
                ),
            )
        )
    return out


# --------------------------------------------------------------- alerts ---
@app.get("/api/alerts", response_model=list[schemas.AlertOut])
def list_alerts(db: Session = Depends(models.get_db)):
    alerts = (
        db.query(models.Alert)
        .filter(models.Alert.acknowledged == False)  # noqa: E712
        .order_by(models.Alert.created_at.desc())
        .all()
    )
    return [
        schemas.AlertOut(
            id=a.id,
            worker_id=a.worker_id,
            worker_name=a.worker.name,
            score=a.score,
            created_at=a.created_at,
            acknowledged=a.acknowledged,
        )
        for a in alerts
    ]


@app.post("/api/alerts/{alert_id}/ack")
def ack_alert(alert_id: int, db: Session = Depends(models.get_db)):
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="alert not found")
    alert.acknowledged = True
    db.commit()
    return {"ok": True}


# --------------------------------------------------------------- weather --
@app.get("/api/weather")
def weather_lookup(lat: float, lon: float):
    try:
        return get_current_weather(lat, lon)
    except WeatherError as e:
        raise HTTPException(status_code=502, detail=str(e))
