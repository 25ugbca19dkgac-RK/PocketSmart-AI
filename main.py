"""
main.py – PocketSmart AI Backend
FastAPI application with user auth, session management,
and AI-powered budget recommendation endpoints.
"""

import os
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import (
    FastAPI, HTTPException, Depends, Request, Form, UploadFile, File, status
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv
from jose import JWTError, jwt
import bcrypt

from gemini_utils import (
    get_home_recommendations,
    get_party_recommendations,
    get_jewelry_recommendations,
)

# ─────────────── Configuration ───────────────

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "pocketsmart-ai-fallback-secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
USERS_FILE = DATA_DIR / "users.json"
HISTORY_FILE = DATA_DIR / "history.json"


# ─────────────── App Setup ───────────────

app = FastAPI(title="PocketSmart AI", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files & templates
STATIC_DIR = Path("static")
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Password hashing helpers
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


# ─────────────── Data Helpers (JSON File Store) ───────────────

def _read_json(path: Path) -> list:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def _write_json(path: Path, data: list):
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def get_users() -> list[dict]:
    return _read_json(USERS_FILE)


def save_users(users: list[dict]):
    _write_json(USERS_FILE, users)


def find_user(username: str) -> dict | None:
    for u in get_users():
        if u["username"] == username:
            return u
    return None


def get_history() -> list[dict]:
    return _read_json(HISTORY_FILE)


def save_history(history: list[dict]):
    _write_json(HISTORY_FILE, history)


def add_history_entry(username: str, category: str, inputs: dict, result: str):
    history = get_history()
    history.insert(0, {
        "id": str(uuid.uuid4()),
        "username": username,
        "category": category,
        "inputs": inputs,
        "result": result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    # Keep latest 100 per user
    save_history(history[:500])


# ─────────────── Auth Helpers ───────────────

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user_from_cookie(request: Request) -> dict | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            return None
        user = find_user(username)
        return user
    except JWTError:
        return None


def require_login(request: Request) -> dict:
    user = get_current_user_from_cookie(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


# ─────────────── Pydantic Models ───────────────

class UserRegister(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenData(BaseModel):
    access_token: str
    token_type: str


# ─────────────── Page Routes (HTML Templates) ───────────────

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    user = get_current_user_from_cookie(request)
    return templates.TemplateResponse(request, "index.html", {"user": user})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"error": None})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    history = [h for h in get_history() if h["username"] == user["username"]][:10]
    return templates.TemplateResponse(request, "dashboard.html", {"user": user, "history": history})


@app.get("/home-planner", response_class=HTMLResponse)
async def home_planner_page(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "home_planner.html", {"user": user})


@app.get("/party-planner", response_class=HTMLResponse)
async def party_planner_page(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "party_planner.html", {"user": user})


@app.get("/jewelry-planner", response_class=HTMLResponse)
async def jewelry_planner_page(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "jewelry_planner.html", {"user": user})


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    history = [h for h in get_history() if h["username"] == user["username"]]
    return templates.TemplateResponse(request, "history.html", {"user": user, "history": history})


# ─────────────── Auth Endpoints ───────────────

@app.post("/register")
async def register_user(request: Request):
    form = await request.form()
    username = form.get("username", "").strip()
    email = form.get("email", "").strip()
    password = form.get("password", "").strip()

    if not username or not email or not password:
        return templates.TemplateResponse(request, "register.html", {"error": "All fields are required."})

    if find_user(username):
        return templates.TemplateResponse(request, "register.html", {"error": "Username already exists."})

    users = get_users()
    users.append({
        "username": username,
        "email": email,
        "hashed_password": hash_password(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    save_users(users)
    return RedirectResponse(url="/login", status_code=303)


@app.post("/login")
async def login_user(request: Request):
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "").strip()

    user = find_user(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return templates.TemplateResponse(request, "login.html", {"error": "Invalid username or password."})

    token = create_access_token(
        data={"sub": username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="access_token", value=token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return response


@app.get("/logout")
async def logout_user():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response


@app.post("/token")
async def get_token(request: Request):
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "").strip()

    user = find_user(username)
    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        data={"sub": username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": token, "token_type": "bearer"}


# ─────────────── Session Info Endpoints ───────────────

@app.get("/session-info")
async def session_info(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return JSONResponse({"logged_in": False})
    return JSONResponse({
        "logged_in": True,
        "username": user["username"],
        "email": user["email"],
    })


@app.get("/session-data")
async def session_data(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return JSONResponse({"logged_in": False, "data": None})
    history = [h for h in get_history() if h["username"] == user["username"]][:5]
    return JSONResponse({
        "logged_in": True,
        "username": user["username"],
        "recent_history": history,
    })


# ─────────────── AI Recommendation Endpoints ───────────────

@app.post("/generate-home")
async def generate_home(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    body = await request.json()
    budget = float(body.get("budget", 0))
    family_size = int(body.get("family_size", 2))
    preferences = body.get("preferences", "modern")
    rooms = body.get("rooms", [])

    if budget <= 0:
        raise HTTPException(status_code=400, detail="Budget must be greater than 0")

    try:
        result = get_home_recommendations(budget, rooms, family_size, preferences)
        add_history_entry(
            user["username"], "home",
            {"budget": budget, "family_size": family_size, "preferences": preferences, "rooms": rooms},
            result["ai_recommendation"]
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-party")
async def generate_party(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    body = await request.json()
    event_type = body.get("event_type", "birthday")
    budget = float(body.get("budget", 0))
    guest_count = int(body.get("guest_count", 10))
    venue_details = body.get("venue_details", "")
    food_preference = body.get("food_preference", "mixed")
    theme = body.get("theme", "")

    if budget <= 0:
        raise HTTPException(status_code=400, detail="Budget must be greater than 0")

    try:
        result = get_party_recommendations(
            event_type, budget, guest_count, venue_details, food_preference, theme
        )
        add_history_entry(
            user["username"], "party",
            {"event_type": event_type, "budget": budget, "guest_count": guest_count},
            result["ai_recommendation"]
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-jewelry")
async def generate_jewelry(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    form = await request.form()
    budget = float(form.get("budget", 0))
    occasion = form.get("occasion", "wedding")
    style_preference = form.get("style_preference", "traditional")
    metal_preference = form.get("metal_preference", "gold")

    image_data = None
    image_mime = "image/jpeg"
    image_file = form.get("outfit_image")
    if image_file and hasattr(image_file, "read"):
        image_data = await image_file.read()
        image_mime = image_file.content_type or "image/jpeg"

    if budget <= 0:
        raise HTTPException(status_code=400, detail="Budget must be greater than 0")

    try:
        result = get_jewelry_recommendations(
            budget, occasion, style_preference, metal_preference, image_data, image_mime
        )
        add_history_entry(
            user["username"], "jewelry",
            {"budget": budget, "occasion": occasion, "style_preference": style_preference},
            result["ai_recommendation"]
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────── Recommendation Details & History API ───────────────

@app.get("/recommendation-details/{rec_id}")
async def recommendation_details(rec_id: str, request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    history = get_history()
    for entry in history:
        if entry["id"] == rec_id and entry["username"] == user["username"]:
            return entry
    raise HTTPException(status_code=404, detail="Recommendation not found")


@app.get("/api/history")
async def api_history(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    history = [h for h in get_history() if h["username"] == user["username"]]
    return {"history": history}


# ─────────────── Startup ───────────────

@app.on_event("startup")
async def startup():
    print("[*] PocketSmart AI is starting up...")
    DATA_DIR.mkdir(exist_ok=True)
    if not USERS_FILE.exists():
        _write_json(USERS_FILE, [])
    if not HISTORY_FILE.exists():
        _write_json(HISTORY_FILE, [])
    print("[+] PocketSmart AI is ready!")


# ─────────────── Entry Point ───────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)