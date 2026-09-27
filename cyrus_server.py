import os
import json
import re
import sqlite3
import io
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

import requests
import edge_tts

from fastapi import FastAPI, Request
from fastapi.responses import (
    RedirectResponse,
    JSONResponse,
    FileResponse,
    StreamingResponse,
)

from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware

import cyrus_public_chat


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "cyrus_users.db")

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3:4b-instruct"

GOOGLE_JSON_FILE = os.path.join(
    BASE_DIR,
    "google_client_secret.json"
)

with open(GOOGLE_JSON_FILE, "r", encoding="utf-8") as f:
    google_config = json.load(f)

google_web = google_config["web"]

GOOGLE_CLIENT_ID = google_web["client_id"]
GOOGLE_CLIENT_SECRET = google_web["client_secret"]

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise RuntimeError(
        "Google OAuth credentials missing from JSON file."
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
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
    },
)



# -----------------------------
# DATABASE
# -----------------------------

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


# -----------------------------
# CURRENT USER
# -----------------------------

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
# TEXT NORMALIZATION
# -----------------------------

def normalize_text(text):
    """
    Roman Urdu / casual typing ko normalize karta hai.
    """

    text = text.lower().strip()

    replacements = {
        "mujhy": "mujhe",
        "mujhe": "mujhe",
        "mjhy": "mujhe",
        "mjhe": "mujhe",

        "kia": "kya",
        "kiya": "kya",
        "kya": "kya",

        "yad": "yaad",
        "yaad": "yaad",

        "ha": "hai",
        "h": "hai",

        "me": "mein",
        "mai": "mein",
        "mein": "mein",

        "bare": "baare",
        "baare": "baare",

        "sari": "saari",
        "saare": "saari",
        "saari": "saari",

        "bhul": "bhool",
        "bhool": "bhool",

        "jao": "jao",
    }

    words = re.findall(r"\S+", text)

    normalized = []

    for word in words:

        clean = re.sub(
            r"[^\w\u0600-\u06FF]+",
            "",
            word
        )

        if clean in replacements:
            normalized.append(
                replacements[clean]
            )
        else:
            normalized.append(
                clean
            )

    return " ".join(normalized)


# -----------------------------
# MEMORY COMMAND DETECTION
# -----------------------------

def is_memory_question(text):

    normalized = normalize_text(text)

    english_patterns = [
        "what do you remember about me",
        "what do you remember",
        "what do you know about me",
        "show my memories",
        "show me my memories",
        "my memories",
        "remember about me",
    ]

    for pattern in english_patterns:

        if pattern in normalized:
            return True


    roman_patterns = [
        "mujhe kya yaad hai",
        "mujhe yaad kya hai",
        "mujhe kya kya yaad hai",

        "mere baare mein kya yaad hai",
        "mere baare me kya yaad hai",

        "mere bare mein kya yaad hai",
        "mere bare me kya yaad hai",

        "mere baare mein kya kya yaad hai",
        "mere bare mein kya kya yaad hai",

        "meri memory kya hai",
        "meri memories kya hain",

        "meri kya kya memory hai",
        "meri kya kya memories hain",
    ]

    for pattern in roman_patterns:

        if pattern in normalized:
            return True


    words = normalized.split()

    has_memory_word = (
        "yaad" in words
        or "memory" in words
        or "memories" in words
    )

    has_question_word = (
        "kya" in words
        or "what" in words
    )

    if has_memory_word and has_question_word:
        return True


    return False


def is_forget_all_command(text):

    normalized = normalize_text(text)

    patterns = [

        "forget everything",
        "forget all memories",
        "forget all my memories",
        "delete all memories",
        "delete my memories",
        "clear all memories",
        "clear my memories",
        "remove all memories",

        "sab kuch bhool jao",
        "sab kuch bhul jao",

        "sab memories bhool jao",
        "sab memories bhul jao",

        "meri sari memories bhool jao",
        "meri saari memories bhool jao",

        "meri sari memory bhool jao",
        "meri saari memory bhool jao",

        "meri sab memories bhool jao",
        "meri sab memory bhool jao",

        "meri memories delete karo",
        "meri sari memories delete karo",

        "sab memory delete karo",
        "sab memories delete karo",

        "sab kuch delete karo",
        "meri sari memory delete karo",
    ]

    for pattern in patterns:

        if pattern in normalized:
            return True


    words = normalized.split()

    has_forget = (
        "bhool" in words
        or "forget" in words
        or "delete" in words
        or "clear" in words
        or "remove" in words
    )

    has_all = (
        "sab" in words
        or "sari" in words
        or "saari" in words
        or "everything" in words
        or "all" in words
    )

    has_memory = (
        "memory" in words
        or "memories" in words
    )

    if has_forget and has_all and has_memory:
        return True

    if has_forget and has_all:
        return True

    return False


def extract_specific_memory_keyword(text):

    normalized = normalize_text(text)

    command_words = [
        "mujhe",
        "meri",
        "mera",
        "mere",
        "wali",
        "wala",
        "wale",
        "ki",
        "ka",
        "ke",
        "memory",
        "memories",
        "bhool",
        "bhul",
        "jao",
        "karo",
        "kar",
        "do",
        "delete",
        "forget",
        "remove",
        "clear",
        "please",
    ]

    words = normalized.split()

    remaining = []

    for word in words:

        if word not in command_words:
            remaining.append(word)

    if not remaining:
        return None

    keyword = " ".join(remaining).strip()

    if len(keyword) < 2:
        return None

    return keyword


def is_specific_forget_command(text):

    if is_forget_all_command(text):
        return False

    normalized = normalize_text(text)
    words = normalized.split()

    has_forget = (
        "bhool" in words
        or "forget" in words
        or "delete" in words
        or "remove" in words
        or "clear" in words
    )

    has_memory = (
        "memory" in words
        or "memories" in words
    )

    if has_forget and has_memory:

        keyword = extract_specific_memory_keyword(
            text
        )

        if keyword:
            return True

    return False


# -----------------------------
# MEMORY COMMAND HANDLER
# -----------------------------

def handle_memory_command(user_id, message):

    if is_memory_question(message):

        memories = cyrus_public_chat.get_memories(
            user_id
        )

        if not memories:

            return (
                "Mujhe abhi tumhare baare mein "
                "koi saved memory nahi hai."
            )

        lines = [
            "Mujhe tumhare baare mein ye yaad hai:"
        ]

        for memory in memories:

            lines.append(
                f"• {memory}"
            )

        return "\n".join(lines)


    if is_forget_all_command(message):

        cyrus_public_chat.clear_memory(
            user_id
        )

        return (
            "Theek hai, maine tumhari saari "
            "saved memories bhula di hain."
        )


    if is_specific_forget_command(message):

        keyword = (
            extract_specific_memory_keyword(
                message
            )
        )

        deleted = (
            cyrus_public_chat.forget_memory(
                user_id,
                keyword
            )
        )

        if deleted > 0:

            return (
                f"Theek hai, maine "
                f"'{keyword}' se related "
                f"saved memory delete kar di."
            )

        return (
            f"Mujhe '{keyword}' se related "
            f"koi saved memory nahi mili."
        )


    return None


# -----------------------------
# AUTOMATIC MEMORY
# -----------------------------

def extract_memory(user_id, message):

    prompt = f"""
You are Cyrus's memory detector.

Read the user's message and decide whether it contains
a useful long-term personal fact that Cyrus should remember.

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
- Memory commands such as "forget this", "delete my memory",
  "what do you remember", etc.

If there is a useful memory, return ONLY one short sentence
describing it.

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

        print(
            "MEMORY SAVED:",
            memory
        )

    except Exception as e:

        print(
            "MEMORY ERROR:",
            e
        )


# -----------------------------
# AI REPLY
# -----------------------------

def ai_reply(
    user_id,
    conversation_id,
    message
):

    context = (
        cyrus_public_chat.build_user_context(
            user_id,
            conversation_id
        )
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

    prompt_parts = [
        system_prompt
    ]

    if context:

        prompt_parts.append(
            "\nUSER-SPECIFIC CONTEXT:\n"
            + context
        )

    prompt_parts.append(
        "\nCURRENT USER MESSAGE:\n"
        + message
    )

    prompt = "\n".join(
        prompt_parts
    )

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

        return (
            "Sorry, mujhe is waqt jawab "
            "generate nahi ho saka."
        )

    return answer


# -----------------------------
# TTS HELPERS
# -----------------------------

def clean_speech_text(text):
    """
    TTS ke liye emojis aur unnecessary markdown remove karta hai.
    """

    text = str(text)

    # URLs
    text = re.sub(
        r"https?://\S+",
        "",
        text
    )

    # Markdown
    text = re.sub(
        r"[*_`#~]+",
        "",
        text
    )

    # Bullet characters
    text = re.sub(
        r"[•●▪◾▶►]",
        "",
        text
    )

    # Common emoji / symbol ranges
    text = re.sub(
        r"[\U0001F300-\U0001FAFF"
        r"\U00002700-\U000027BF"
        r"\U00002600-\U000026FF"
        r"\U0001F1E6-\U0001F1FF]+",
        "",
        text
    )

    # Extra spaces
    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


def detect_tts_voice(text):

    # Urdu script present
    if re.search(
        r"[\u0600-\u06FF]",
        text
    ):
        return "ur-PK-AsadNeural"


    normalized = text.lower()

    # Roman Urdu indicators
    roman_urdu_words = {
        "main",
        "mein",
        "mujhe",
        "mujhy",
        "aap",
        "ap",
        "tum",
        "tumhe",
        "tumhein",
        "hai",
        "hain",
        "hoon",
        "hun",
        "kya",
        "kia",
        "kaise",
        "kaisa",
        "kyun",
        "kyu",
        "mera",
        "meri",
        "mere",
        "aapki",
        "aapka",
        "baare",
        "bare",
        "yaad",
        "bhool",
        "kar",
        "karo",
        "kr",
        "nahi",
        "nahin",
        "acha",
        "achha",
        "theek",
        "thik",
        "haan",
        "han",
        "wala",
        "wali",
        "liye",
        "lagta",
        "sakta",
        "sakti",
        "raha",
        "rahi",
        "rahe",
    }

    words = re.findall(
        r"[a-zA-Z']+",
        normalized
    )

    if not words:
        return "en-US-AndrewMultilingualNeural"

    roman_urdu_count = sum(
        1
        for word in words
        if word in roman_urdu_words
    )

    # Agar Roman Urdu indicators zyada hain
    if roman_urdu_count >= 1:
        return "ur-PK-AsadNeural"

    return "en-US-AndrewMultilingualNeural"


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
        os.path.join(
            BASE_DIR,
            "public.html"
        )
    )


# -----------------------------
# GOOGLE LOGIN
# -----------------------------

@app.get("/login")
async def login(
    request: Request
):

    redirect_uri = request.url_for(
        "auth_callback"
    )

    return await oauth.google.authorize_redirect(
        request,
        redirect_uri
    )


@app.get("/auth/callback")
async def auth_callback(
    request: Request
):

    token = await oauth.google.authorize_access_token(
        request
    )

    userinfo = token.get(
        "userinfo"
    )

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
async def me(
    request: Request
):

    user = current_user(
        request
    )

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
async def logout(
    request: Request
):

    request.session.clear()

    return RedirectResponse("/")


# -----------------------------
# CONVERSATIONS
# -----------------------------

@app.get("/conversations")
async def conversations(
    request: Request
):

    user = current_user(
        request
    )

    if not user:

        return JSONResponse(
            {
                "error":
                    "login_required"
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

    user = current_user(
        request
    )

    if not user:

        return JSONResponse(
            {
                "error":
                    "login_required"
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

    user = current_user(
        request
    )

    if not user:

        return JSONResponse(
            {
                "error":
                    "login_required"
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

    user = current_user(
        request
    )

    if not user:

        return JSONResponse(
            {
                "error":
                    "login_required"
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
async def chat(
    request: Request
):

    user = current_user(
        request
    )

    if not user:

        return JSONResponse(
            {
                "error":
                    "login_required"
            },
            status_code=401
        )

    try:

        body = await request.json()

    except Exception:

        return JSONResponse(
            {
                "error":
                    "invalid_json"
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


    # -------------------------
    # MEMORY COMMANDS
    # -------------------------

    memory_command = (
        handle_memory_command(
            user_id,
            message
        )
    )

    if memory_command:

        if conversation_id is None:

            conversation_id = (
                cyrus_public_chat.create_conversation(
                    user_id,
                    "New Chat"
                )
            )

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

        cyrus_public_chat.add_message(
            user_id,
            "user",
            message,
            conversation_id
        )

        cyrus_public_chat.add_message(
            user_id,
            "assistant",
            memory_command,
            conversation_id
        )

        return {
            "answer":
                memory_command,

            "conversation_id":
                conversation_id
        }


    # -------------------------
    # CREATE CONVERSATION
    # -------------------------

    if conversation_id is None:

        conversation_id = (
            cyrus_public_chat.create_conversation(
                user_id,
                "New Chat"
            )
        )


    # -------------------------
    # SECURITY CHECK
    # -------------------------

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


    # -------------------------
    # SAVE USER MESSAGE
    # -------------------------

    cyrus_public_chat.add_message(
        user_id,
        "user",
        message,
        conversation_id
    )


    # -------------------------
    # AUTOMATIC MEMORY
    # -------------------------

    extract_memory(
        user_id,
        message
    )


    # -------------------------
    # CHAT TITLE
    # -------------------------

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


    # -------------------------
    # AI
    # -------------------------

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


    # -------------------------
    # SAVE AI RESPONSE
    # -------------------------

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
# TTS
# -----------------------------

@app.post("/tts")
async def tts(
    request: Request
):

    user = current_user(
        request
    )

    if not user:

        return JSONResponse(
            {
                "error":
                    "login_required"
            },
            status_code=401
        )

    try:

        body = await request.json()

    except Exception:

        return JSONResponse(
            {
                "error":
                    "invalid_json"
            },
            status_code=400
        )

    text = str(
        body.get(
            "text",
            ""
        )
    ).strip()

    if not text:

        return JSONResponse(
            {
                "error":
                    "text_required"
            },
            status_code=400
        )

    text = clean_speech_text(
        text
    )

    if not text:

        return JSONResponse(
            {
                "error":
                    "no_speakable_text"
            },
            status_code=400
        )

    text = text[:3000]

    voice = detect_tts_voice(
        text
    )

    print(
        "TTS VOICE:",
        voice
    )

    try:

        communicate = edge_tts.Communicate(
            text,
            voice
        )

        audio = bytearray()

        async for chunk in communicate.stream():

            if chunk["type"] == "audio":

                audio.extend(
                    chunk["data"]
                )

        if not audio:

            return JSONResponse(
                {
                    "error":
                        "tts_audio_empty"
                },
                status_code=500
            )

        return StreamingResponse(
            io.BytesIO(
                bytes(audio)
            ),
            media_type="audio/mpeg",
            headers={
                "Cache-Control":
                    "no-store"
            }
        )

    except Exception as e:

        print(
            "TTS ERROR:",
            e
        )

        return JSONResponse(
            {
                "error":
                    "tts_failed"
            },
            status_code=500
        )


# -----------------------------
# HISTORY
# -----------------------------

@app.get("/history")
async def history(
    request: Request,
    conversation_id: int | None = None
):

    user = current_user(
        request
    )

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

    user = current_user(
        request
    )

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
# MEMORY API
# -----------------------------

@app.get("/memory")
async def memory(
    request: Request
):

    user = current_user(
        request
    )

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

    user = current_user(
        request
    )

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

    user = current_user(
        request
    )

    return {
        "cyrus": "online",
        "model": MODEL,
        "logged_in": bool(user)
    }