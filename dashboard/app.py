import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Load env — bot/.env holds shared vars; dashboard/.env holds dashboard-specific ones
_root = Path(__file__).parent.parent
load_dotenv(_root / "bot" / ".env")
load_dotenv(Path(__file__).parent / ".env")

from auth import verify_password, create_token, verify_token
from parser import compute_stats, parse_workouts

WORKOUTS_DIR = _root / "workouts"
DASHBOARD_USERNAME = os.environ.get("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD_HASH = os.environ["DASHBOARD_PASSWORD_HASH"]

app = FastAPI(docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def _get_user(session: Optional[str]) -> Optional[str]:
    return verify_token(session) if session else None


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

    workouts = parse_workouts(WORKOUTS_DIR)
    stats = compute_stats(workouts)
    workouts_json = json.dumps(workouts[:150]).replace("</", "<\\/")

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "workouts": workouts[:25],
        "stats": stats,
        "workouts_json": workouts_json,
    })
