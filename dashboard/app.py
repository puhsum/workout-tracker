import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, Cookie, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

_root = Path(__file__).parent.parent
load_dotenv(_root / "bot" / ".env")
load_dotenv(Path(__file__).parent / ".env")

from auth import verify_password, create_token, verify_token
from parser import compute_stats, get_exercise_names, parse_workouts
import sessions as sess
from writer import write_workout

VAULT_DIR = _root / "workout-converted"
DASHBOARD_USERNAME = os.environ.get("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD_HASH = os.environ["DASHBOARD_PASSWORD_HASH"]

app = FastAPI(docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def _get_user(session: Optional[str]) -> Optional[str]:
    return verify_token(session) if session else None


def _require_user(session: Optional[str]) -> str:
    user = _get_user(session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request, session: Optional[str] = Cookie(default=None)):
    if _get_user(session):
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if username == DASHBOARD_USERNAME and verify_password(password, DASHBOARD_PASSWORD_HASH):
        resp = RedirectResponse("/dashboard", status_code=302)
        resp.set_cookie("session", create_token(username), httponly=True, samesite="lax", max_age=86400 * 7)
        return resp
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})


@app.get("/logout")
async def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("session")
    return resp


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(session: Optional[str] = Cookie(default=None)):
    return RedirectResponse("/dashboard" if _get_user(session) else "/login")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: Optional[str] = Cookie(default=None)):
    if not _get_user(session):
        return RedirectResponse("/login")

    workouts = parse_workouts(VAULT_DIR)
    stats = compute_stats(workouts)
    workouts_json = json.dumps(workouts[:150]).replace("</", "<\\/")

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "workouts": workouts[:25],
        "stats": stats,
        "workouts_json": workouts_json,
    })


# ── Log detail ────────────────────────────────────────────────────────────────

@app.get("/log/{date}", response_class=HTMLResponse)
async def log_detail(date: str, request: Request, session: Optional[str] = Cookie(default=None)):
    if not _get_user(session):
        return RedirectResponse("/login")
    workouts = parse_workouts(VAULT_DIR)
    day_workouts = [w for w in workouts if w["date"] == date]
    return templates.TemplateResponse("log.html", {
        "request": request,
        "date": date,
        "workouts": day_workouts,
    })


# ── Workout Logging ───────────────────────────────────────────────────────────

@app.get("/workout/new", response_class=HTMLResponse)
async def workout_new(request: Request, session: Optional[str] = Cookie(default=None)):
    if not _get_user(session):
        return RedirectResponse("/login")
    return templates.TemplateResponse("workout.html", {"request": request})


@app.post("/api/workout/start")
async def workout_start(session: Optional[str] = Cookie(default=None)):
    _require_user(session)
    s = sess.create_session()
    return {"session_id": s["id"], "start_time": s["start_time"]}


@app.get("/api/workout/{session_id}")
async def workout_get(session_id: str, session: Optional[str] = Cookie(default=None)):
    _require_user(session)
    s = sess.get_session(session_id)
    if s is None:
        raise HTTPException(404, "Session not found")
    return s


class ExerciseIn(BaseModel):
    name: str
    sets: list


class FinishIn(BaseModel):
    local_date: Optional[str] = None


@app.post("/api/workout/{session_id}/exercise")
async def workout_add_exercise(
    session_id: str,
    body: ExerciseIn,
    session: Optional[str] = Cookie(default=None),
):
    _require_user(session)
    s = sess.add_exercise(session_id, body.name.strip(), body.sets)
    if s is None:
        raise HTTPException(404, "Session not found")
    return s


@app.delete("/api/workout/{session_id}/exercise/{index}")
async def workout_remove_exercise(
    session_id: str,
    index: int,
    session: Optional[str] = Cookie(default=None),
):
    _require_user(session)
    s = sess.remove_exercise(session_id, index)
    if s is None:
        raise HTTPException(404, "Session not found")
    return s


@app.post("/api/workout/{session_id}/finish")
async def workout_finish(
    session_id: str,
    body: FinishIn = FinishIn(),
    session: Optional[str] = Cookie(default=None),
):
    _require_user(session)
    s = sess.finish_session(session_id)
    if s is None:
        raise HTTPException(404, "Session not found")
    filename = write_workout(s, VAULT_DIR, local_date=body.local_date)
    sess.delete_session(session_id)
    return {"file": filename}


@app.get("/api/exercises")
async def list_exercises(session: Optional[str] = Cookie(default=None)):
    _require_user(session)
    workouts = parse_workouts(VAULT_DIR)
    return {"exercises": get_exercise_names(workouts)}
