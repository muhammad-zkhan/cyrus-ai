import json
import urllib.request

MODEL = "qwen3:4b"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

messages = [
    {
        "role": "system",
        "content": (
            "Your name is Cyrus. You are a helpful personal AI assistant. "
            "Answer naturally, clearly and concisely."
        )
    }
]

print("=" * 50)
print("        CYRUS AI — ONLINE")
print("=" * 50)
print("Type 'exit' to close Cyrus.\n")

while True:
    try:
        user = input("You: ").strip()

        if user.lower() in ("exit", "quit"):
            print("Cyrus: Goodbye!")
            break

        if not user:
            continue

        messages.append({
            "role": "user",
            "content": user
        })

        data = json.dumps({
            "model": MODEL,
            "messages": messages,
            "stream": False
        }).encode("utf-8")

        request = urllib.request.Request(
            OLLAMA_URL,
            data=data,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))

        reply = result["message"]["content"]

        print(f"\nCyrus: {reply}\n")

        messages.append({
            "role": "assistant",
            "content": reply
        })import json
import urllib.request
import pyttsx3

MODEL = "qwen3:4b"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

engine = pyttsx3.init()
engine.setProperty("rate", 165)
engine.setProperty("volume", 1.0)

messages = [
    {
        "role": "system",
        "content": (
            "Your name is Cyrus. You are a helpful personal AI assistant. "
            "Answer naturally, clearly and concisely."
        )
    }
]

print("=" * 50)
print("        CYRUS AI — VOICE MODE")
print("=" * 50)
print("Type your message. Type 'exit' to close.\n")

while True:
    try:
        user = input("You: ").strip()

        if user.lower() in ("exit", "quit"):
            print("Cyrus: Goodbye!")
            engine.say("Goodbye!")
            engine.runAndWait()
            break

        if not user:
            continue

        messages.append({
            "role": "user",
            "content": user
        })

        data = json.dumps({
            "model": MODEL,
            "messages": messages,
            "stream": False
        }).encode("utf-8")

        request = urllib.request.Request(
            OLLAMA_URL,
            data=data,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))

        reply = result["message"]["content"]

        print(f"\nCyrus: {reply}\n")

        messages.append({
            "role": "assistant",
            "content": reply
        })

        engine.say(reply)
        engine.runAndWait()

    except Exception as e:
        print(f"\nCyrus Error: {e}\n")

    except Exception as e:
        print(f"\nCyrus Error: {e}\n")