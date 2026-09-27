import os
import sys
import threading

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# =========================================================
# CYRUS MOBILE / WEB SERVER
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Make sure Python can find cyrus_pc.py
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import cyrus_pc


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="Cyrus Personal AI",
    version="1.0.0"
)

# Local network mobile app ke liye CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# THREAD LOCK
# =========================================================

cyrus_lock = threading.Lock()


# =========================================================
# REQUEST MODELS
# =========================================================

class ChatRequest(BaseModel):
    message: str


# =========================================================
# HEALTH
# =========================================================

@app.get("/")
def root():
    return {
        "name": "Cyrus",
        "status": "online",
        "model": cyrus_pc.MODEL
    }


@app.get("/health")
def health():
    return {
        "status": "online",
        "ollama": cyrus_pc.ollama_available(),
        "model": cyrus_pc.MODEL
    }


# =========================================================
# CHAT
# =========================================================

@app.post("/chat")
def chat(request: ChatRequest):

    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message empty hai."
        )

    # Safety limit
    if len(message) > 4000:
        raise HTTPException(
            status_code=400,
            detail="Message bohat long hai."
        )

    try:

        with cyrus_lock:

            response = cyrus_pc.handle_user_input(
                message
            )

            if response == "__EXIT__":
                response = "Cyrus server ko exit command mobile se nahi di ja sakti."

            # Same chat history system as desktop Cyrus
            cyrus_pc.add_chat_message(
                "user",
                message
            )

            cyrus_pc.add_chat_message(
                "assistant",
                response
            )

        return {
            "success": True,
            "response": response
        }

    except Exception as e:

        print(
            f"[Server error] {type(e).__name__}: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Cyrus request process nahi kar saka."
        )


# =========================================================
# MEMORY
# =========================================================

@app.get("/memory")
def get_memory():

    try:

        with cyrus_lock:

            return {
                "success": True,
                "memory": list(cyrus_pc.memory)
            }

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Memory read nahi ho saki."
        )


@app.delete("/memory")
def delete_memory():

    try:

        with cyrus_lock:

            result = cyrus_pc.clear_memory()

            return {
                "success": True,
                "message": result
            }

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Memory clear nahi ho saki."
        )


# =========================================================
# CHAT HISTORY
# =========================================================

@app.get("/history")
def get_history():

    try:

        with cyrus_lock:

            return {
                "success": True,
                "history": list(cyrus_pc.chat_history)
            }

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Chat history read nahi ho saki."
        )


@app.delete("/history")
def delete_history():

    try:

        with cyrus_lock:

            cyrus_pc.chat_history = []

            cyrus_pc.save_chat_history()

            return {
                "success": True,
                "message": "Chat history clear kar di."
            }

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Chat history clear nahi ho saki."
        )


# =========================================================
# SYSTEM STATUS
# =========================================================

@app.get("/status")
def status():

    try:

        ollama_online = cyrus_pc.ollama_available()

        ollama_version = (
            cyrus_pc.get_ollama_version()
            if ollama_online
            else None
        )

        return {
            "success": True,
            "cyrus": "online",
            "ollama": ollama_online,
            "ollama_version": ollama_version,
            "model": cyrus_pc.MODEL,
            "memory_items": len(cyrus_pc.memory),
            "chat_messages": len(cyrus_pc.chat_history)
        }

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Status read nahi ho saka."
        )


# =========================================================
# SERVER START
# =========================================================

if __name__ == "__main__":

    import uvicorn

    print()
    print("=" * 60)
    print("CYRUS MOBILE SERVER")
    print("=" * 60)
    print()
    print("Cyrus backend start ho raha hai...")
    print()
    print("Local PC:")
    print("http://127.0.0.1:8000")
    print()
    print("Network:")
    print("http://0.0.0.0:8000")
    print()
    print("Mobile app isi server se connect hogi.")
    print()
    print("=" * 60)
    print()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )