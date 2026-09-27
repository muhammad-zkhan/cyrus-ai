import os
import sqlite3
import secrets
from datetime import datetime, timezone

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "cyrus_users.db")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise RuntimeError(
        "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET environment variables missing."
    )

app = FastAPI(title="Cyrus Public")

# Random session secret. For this development session only.
SESSION_SECRET = secrets.token_urlsafe(32)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    https_only=False,
    same_site="lax",
)

oauth = OAuth()

oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile"
    },
)


def db():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = db()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_id TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            name TEXT,
            picture TEXT,
            created_at TEXT NOT NULL,
            last_login TEXT NOT NULL
        )
        """
    )

    connection.commit()
    connection.close()


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
async def home():
    return {
        "name": "Cyrus",
        "status": "online",
        "message": "Cyrus Public Server"
    }


@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")

    return await oauth.google.authorize_redirect(
        request,
        redirect_uri
    )


@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)

    userinfo = token.get("userinfo")

    if not userinfo:
        userinfo = await oauth.google.parse_id_token(
            request,
            token
        )

    google_id = userinfo["sub"]
    email = userinfo.get("email", "")
    name = userinfo.get("name", "")
    picture = userinfo.get("picture", "")

    connection = db()

    existing = connection.execute(
        "SELECT id FROM users WHERE google_id = ?",
        (google_id,)
    ).fetchone()

    now = datetime.now(timezone.utc).isoformat()

    if existing:
        connection.execute(
            """
            UPDATE users
            SET email = ?, name = ?, picture = ?, last_login = ?
            WHERE google_id = ?
            """,
            (
                email,
                name,
                picture,
                now,
                google_id
            )
        )
        user_id = existing["id"]

    else:
        cursor = connection.execute(
            """
            INSERT INTO users
            (google_id, email, name, picture, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                google_id,
                email,
                name,
                picture,
                now,
                now
            )
        )

        user_id = cursor.lastrowid

    connection.commit()
    connection.close()

    request.session["user_id"] = user_id
    request.session["google_id"] = google_id
    request.session["email"] = email
    request.session["name"] = name

    return RedirectResponse("/me")


@app.get("/me")
async def me(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse("/login")

    return {
        "logged_in": True,
        "user_id": request.session["user_id"],
        "email": request.session["email"],
        "name": request.session["name"]
    }


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


@app.get("/users/count")
async def users_count():
    connection = db()

    result = connection.execute(
        "SELECT COUNT(*) AS count FROM users"
    ).fetchone()

    connection.close()

    return {
        "users": result["count"]
    }