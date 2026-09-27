import os
import sqlite3
from datetime import datetime, timezone

import requests
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware

import cyrus_public_chat


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "cyrus_users.db")

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3:4b-instruct"

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise RuntimeError(
        "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET missing."
    )


app = FastAPI(
    title="Cyrus Public",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


SESSION_SECRET = os.getenv("CYRUS_SESSION_SECRET")

if not SESSION_SECRET:
    SESSION_SECRET = os.urandom(32).hex()


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
    server_metadata_url=(
        "https://accounts.google.com/.well-known/"
        "openid-configuration"
    ),
    client_kwargs={
        "scope": "openid email profile"
    },
)


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute(
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

    conn.commit()
    conn.close()

    cyrus_public_chat.init_chat_db()


def current_user(request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    conn = get_db()

    user = conn.execute(
        """
        SELECT id, google_id, email, name, picture
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    conn.close()

    return user


# -----------------------------
# AUTOMATIC MEMORY
# -----------------------------

def extract_memory(user_id, message):
    prompt = f"""
You are Cyrus's memory detector.

Read the user's message and decide whether it contains a useful
long-term personal fact that Cyrus should remember.

Useful memories can include:
- Name
- City or general location
- Hobbies
- Interests
- Skills being learned
- Long-term preferences
- Long-term goals
- Other useful non-sensitive personal preferences

Do NOT save:
- Temporary questions
- Greetings
- Random facts
- One-time requests
- Passwords
- API keys
- OAuth secrets
- Login credentials
- Financial information
- Highly sensitive personal information

If there is a useful memory, return ONLY one short sentence describing it.

If there is no useful memory, return exactly:
NONE

User message:
{message}
"""

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "think": False,
        "keep_alive": "15m",
        "options": {
            "num_predict": 80
        }
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        memory = (
            data.get("message", {})
            .get("content", "")
            .strip()
        )

        if not memory:
            return

        if memory.upper() == "NONE":
            return

        if len(memory) > 300:
            return

        cyrus_public_chat.add_memory(
            user_id,
            memory
        )

        print("MEMORY SAVED:", memory)

    except Exception as e:
        print("MEMORY ERROR:", e)


# -----------------------------
# AI
# -----------------------------

def ai_reply(user_id, conversation_id, message):

    context = cyrus_public_chat.build_user_context(
        user_id,
        conversation_id
    )

    system_prompt = """
You are Cyrus, a friendly personal AI assistant.

You communicate naturally in English and Roman Urdu.

You are serving a public user through a web application.

IMPORTANT:
- Never reveal passwords, API keys, OAuth secrets,
  session secrets, server configuration or private database data.
- Never access or reveal another user's memory or conversations.
- Only use the current user's supplied context.
- Do not control the user's computer.
- Keep answers helpful, natural and concise.
"""

    prompt_parts = [system_prompt]

    if context:
        prompt_parts.append(
            "\nUSER-SPECIFIC CONTEXT:\n" + context
        )

    prompt_parts.append(
        "\nCURRENT USER MESSAGE:\n" + message
    )

    prompt = "\n".join(prompt_parts)

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "think": False,
        "keep_alive": "15m",
        "options": {
            "num_predict": 260
        }
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=180
    )

    response.raise_for_status()

    data = response.json()

    answer = (
        data.get("message", {})
        .get("content", "")
        .strip()
    )

    if not answer:
        return "Sorry, mujhe is waqt jawab generate nahi ho saka."

    return answer


# -----------------------------
# STARTUP
# -----------------------------

@app.on_event("startup")
def startup():
    init_db()


# -----------------------------
# HOME
# -----------------------------

@app.get("/")
async def home():
    return FileResponse(
        os.path.join(BASE_DIR, "public.html")
    )


# -----------------------------
# GOOGLE LOGIN
# -----------------------------

@app.get("/login")
async def login(request: Request):

    redirect_uri = request.url_for(
        "auth_callback"
    )

    return await oauth.google.authorize_redirect(
        request,
        redirect_uri
    )


@app.get("/auth/callback")
async def auth_callback(request: Request):

    token = await oauth.google.authorize_access_token(
        request
    )

    userinfo = token.get("userinfo")

    if not userinfo:
        userinfo = await oauth.google.parse_id_token(
            request,
            token
        )

    google_id = userinfo["sub"]

    email = userinfo.get(
        "email",
        ""
    )

    name = userinfo.get(
        "name",
        ""
    )

    picture = userinfo.get(
        "picture",
        ""
    )

    conn = get_db()

    existing = conn.execute(
        """
        SELECT id
        FROM users
        WHERE google_id = ?
        """,
        (google_id,)
    ).fetchone()

    now = datetime.now(
        timezone.utc
    ).isoformat()

    if existing:

        conn.execute(
            """
            UPDATE users
            SET email = ?,
                name = ?,
                picture = ?,
                last_login = ?
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

        cursor = conn.execute(
            """
            INSERT INTO users
            (
                google_id,
                email,
                name,
                picture,
                created_at,
                last_login
            )
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

    conn.commit()
    conn.close()

    request.session["user_id"] = user_id

    return RedirectResponse("/")


# -----------------------------
# USER
# -----------------------------

@app.get("/me")
async def me(request: Request):

    user = current_user(request)

    if not user:

        return JSONResponse(
            {
                "logged_in": False
            },
            status_code=401
        )

    return {
        "logged_in": True,
        "user_id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user["picture"]
    }


@app.get("/logout")
async def logout(request: Request):

    request.session.clear()

    return RedirectResponse("/")


# -----------------------------
# CONVERSATIONS
# -----------------------------

@app.get("/conversations")
async def conversations(request: Request):

    user = current_user(request)

    if not user:

        return JSONResponse(
            {
                "error": "login_required"
            },
            status_code=401
        )

    return {
        "conversations":
            cyrus_public_chat.get_conversations(
                user["id"]
            )
    }


@app.post("/conversations")
async def create_conversation(
    request: Request
):

    user = current_user(request)

    if not user:

        return JSONResponse(
            {
                "error": "login_required"
            },
            status_code=401
        )

    try:
        body = await request.json()

    except Exception:
        body = {}

    title = str(
        body.get(
            "title",
            "New Chat"
        )
    ).strip()

    if not title:
        title = "New Chat"

    conversation_id = (
        cyrus_public_chat.create_conversation(
            user["id"],
            title[:100]
        )
    )

    return {
        "conversation_id":
            conversation_id,

        "title":
            title[:100]
    }


@app.patch(
    "/conversations/{conversation_id}"
)
async def rename_conversation(
    conversation_id: int,
    request: Request
):

    user = current_user(request)

    if not user:

        return JSONResponse(
            {
                "error": "login_required"
            },
            status_code=401
        )

    if not cyrus_public_chat.conversation_belongs_to_user(
        user["id"],
        conversation_id
    ):

        return JSONResponse(
            {
                "error":
                    "conversation_not_found"
            },
            status_code=404
        )

    try:
        body = await request.json()

    except Exception:
        body = {}

    title = str(
        body.get(
            "title",
            "New Chat"
        )
    ).strip()

    cyrus_public_chat.rename_conversation(
        user["id"],
        conversation_id,
        title
    )

    return {
        "success": True
    }


@app.delete(
    "/conversations/{conversation_id}"
)
async def delete_conversation(
    conversation_id: int,
    request: Request
):

    user = current_user(request)

    if not user:

        return JSONResponse(
            {
                "error": "login_required"
            },
            status_code=401
        )

    if not cyrus_public_chat.conversation_belongs_to_user(
        user["id"],
        conversation_id
    ):

        return JSONResponse(
            {
                "error":
                    "conversation_not_found"
            },
            status_code=404
        )

    cyrus_public_chat.delete_conversation(
        user["id"],
        conversation_id
    )

    return {
        "success": True
    }


# -----------------------------
# CHAT
# -----------------------------

@app.post("/chat")
async def chat(request: Request):

    user = current_user(request)

    if not user:

        return JSONResponse(
            {
                "error": "login_required"
            },
            status_code=401
        )

    try:

        body = await request.json()

    except Exception:

        return JSONResponse(
            {
                "error": "invalid_json"
            },
            status_code=400
        )

    message = str(
        body.get(
            "message",
            ""
        )
    ).strip()

    conversation_id = body.get(
        "conversation_id"
    )

    if conversation_id is not None:

        try:

            conversation_id = int(
                conversation_id
            )

        except (
            TypeError,
            ValueError
        ):

            return JSONResponse(
                {
                    "error":
                        "invalid_conversation"
                },
                status_code=400
            )

    if not message:

        return JSONResponse(
            {
                "error":
                    "message_required"
            },
            status_code=400
        )

    if len(message) > 4000:

        return JSONResponse(
            {
                "error":
                    "message_too_long"
            },
            status_code=400
        )

    user_id = user["id"]

    # Create conversation automatically
    if conversation_id is None:

        conversation_id = (
            cyrus_public_chat.create_conversation(
                user_id,
                "New Chat"
            )
        )

    # Security check
    if not cyrus_public_chat.conversation_belongs_to_user(
        user_id,
        conversation_id
    ):

        return JSONResponse(
            {
                "error":
                    "conversation_not_found"
            },
            status_code=404
        )

    # Save user message
    cyrus_public_chat.add_message(
        user_id,
        "user",
        message,
        conversation_id
    )

    # Automatic memory detection
    extract_memory(
        user_id,
        message
    )

    # First message becomes chat title
    messages = (
        cyrus_public_chat.get_recent_messages(
            user_id,
            conversation_id,
            limit=2
        )
    )

    if len(messages) == 1:

        title = message[:50]

        cyrus_public_chat.rename_conversation(
            user_id,
            conversation_id,
            title
        )

    try:

        answer = ai_reply(
            user_id,
            conversation_id,
            message
        )

    except Exception as e:

        print(
            "AI ERROR:",
            e
        )

        return JSONResponse(
            {
                "error":
                    "ai_unavailable"
            },
            status_code=503
        )

    # Save Cyrus response
    cyrus_public_chat.add_message(
        user_id,
        "assistant",
        answer,
        conversation_id
    )

    return {
        "answer":
            answer,

        "conversation_id":
            conversation_id
    }


# -----------------------------
# HISTORY
# -----------------------------

@app.get("/history")
async def history(
    request: Request,
    conversation_id: int | None = None
):

    user = current_user(request)

    if not user:

        return JSONResponse(
            {
                "error":
                    "login_required"
            },
            status_code=401
        )

    if conversation_id is not None:

        if not cyrus_public_chat.conversation_belongs_to_user(
            user["id"],
            conversation_id
        ):

            return JSONResponse(
                {
                    "error":
                        "conversation_not_found"
                },
                status_code=404
            )

    return {
        "history":
            cyrus_public_chat.get_recent_messages(
                user["id"],
                conversation_id,
                limit=50
            )
    }


@app.delete("/history")
async def delete_history(
    request: Request
):

    user = current_user(request)

    if not user:

        return JSONResponse(
            {
                "error":
                    "login_required"
            },
            status_code=401
        )

    cyrus_public_chat.clear_chat(
        user["id"]
    )

    return {
        "success": True
    }


# -----------------------------
# MEMORY
# -----------------------------

@app.get("/memory")
async def memory(
    request: Request
):

    user = current_user(request)

    if not user:

        return JSONResponse(
            {
                "error":
                    "login_required"
            },
            status_code=401
        )

    return {
        "memory":
            cyrus_public_chat.get_memories(
                user["id"]
            )
    }


@app.delete("/memory")
async def delete_memory(
    request: Request
):

    user = current_user(request)

    if not user:

        return JSONResponse(
            {
                "error":
                    "login_required"
            },
            status_code=401
        )

    cyrus_public_chat.clear_memory(
        user["id"]
    )

    return {
        "success": True
    }


# -----------------------------
# STATUS
# -----------------------------

@app.get("/status")
async def status(
    request: Request
):

    user = current_user(request)

    return {
        "cyrus": "online",
        "model": MODEL,
        "logged_in": bool(user)
    }