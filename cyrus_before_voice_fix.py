import requests
import json
import os
import webbrowser
import subprocess
import re
import pyttsx3
from bs4 import BeautifulSoup

# =========================
# CYRUS SETTINGS
# =========================

MODEL = "qwen3:4b"
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_VERSION_URL = "http://127.0.0.1:11434/api/version"

# =========================
# VOICE
# =========================

engine = pyttsx3.init()
engine.setProperty("rate", 175)

def speak(text):
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception:
        pass

# =========================
# OLLAMA STREAMING
# =========================

def ask_cyrus(prompt):
    print("\nCyrus: ", end="", flush=True)

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "think": False,
        "stream": True,
        "keep_alive": "15m",
        "options": {
            "temperature": 0.2,
            "num_predict": 180
        }
    }

    full_answer = ""

    try:
        with requests.post(
            OLLAMA_CHAT_URL,
            json=payload,
            stream=True,
            timeout=180
        ) as response:

            response.raise_for_status()

            for line in response.iter_lines():

                if not line:
                    continue

                try:
                    data = json.loads(line.decode("utf-8"))
                except Exception:
                    continue

                message = data.get("message", {})
                content = message.get("content", "")

                if content:
                    print(content, end="", flush=True)
                    full_answer += content

                if data.get("done"):
                    break

        print()

        return full_answer.strip()

    except requests.exceptions.Timeout:
        print("\n\nCyrus: Ollama ne response dene mein bohat zyada time liya.")
        return ""

    except requests.exceptions.ConnectionError:
        print("\n\nCyrus: Ollama server se connection nahi ho raha.")
        return ""

    except Exception as e:
        print(f"\n\nCyrus error: {e}")
        return ""

# =========================
# OLLAMA VERSION
# =========================

def get_ollama_version():

    try:
        r = requests.get(
            OLLAMA_VERSION_URL,
            timeout=5
        )

        if r.status_code == 200:
            data = r.json()
            return data.get("version")

    except Exception:
        pass

    return None

# =========================
# PYTHON OFFICIAL SEARCH
# =========================

def python_latest():

    try:
        url = "https://www.python.org/downloads/"

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        r = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        if r.status_code != 200:
            return None

        soup = BeautifulSoup(
            r.text,
            "html.parser"
        )

        text = soup.get_text(" ", strip=True)

        match = re.search(
            r"Python\s+(\d+\.\d+\.\d+)",
            text
        )

        if match:
            return match.group(1)

    except Exception:
        pass

    return None

# =========================
# BING SEARCH
# =========================

def bing_search(query, max_results=5):

    print("\nCyrus web par search kar raha hai...")

    try:

        url = "https://www.bing.com/search"

        params = {
            "q": query
        }

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        r = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=20
        )

        if r.status_code != 200:
            return []

        soup = BeautifulSoup(
            r.text,
            "html.parser"
        )

        results = []

        for item in soup.select("li.b_algo"):

            title_tag = item.select_one("h2")

            link_tag = item.select_one("h2 a")

            snippet_tag = item.select_one(".b_caption p")

            if not title_tag or not link_tag:
                continue

            title = title_tag.get_text(
                " ",
                strip=True
            )

            link = link_tag.get(
                "href",
                ""
            )

            snippet = ""

            if snippet_tag:
                snippet = snippet_tag.get_text(
                    " ",
                    strip=True
                )

            results.append({
                "title": title,
                "url": link,
                "snippet": snippet
            })

            if len(results) >= max_results:
                break

        print(f"Bing results found: {len(results)}")

        return results

    except Exception as e:

        print(
            f"\nSearch error: {e}"
        )

        return []

# =========================
# WEB DETECTION
# =========================

WEB_WORDS = [
    "latest",
    "current",
    "today",
    "tonight",
    "news",
    "update",
    "updates",
    "price",
    "weather",
    "forecast",
    "score",
    "scores",
    "schedule",
    "release",
    "released",
    "version",
    "newest",
    "recent",
    "recently"
]

def needs_web_search(text):

    text_lower = text.lower()

    if (
        "search web" in text_lower
        or "search online" in text_lower
        or "google" in text_lower
    ):
        return True

    for word in WEB_WORDS:

        if re.search(
            r"\b" + re.escape(word) + r"\b",
            text_lower
        ):
            return True

    return False

# =========================
# SPECIAL WEB QUESTIONS
# =========================

def handle_special_web_query(text):

    lower = text.lower()

    # Ollama version
    if "ollama" in lower and "version" in lower:

        version = get_ollama_version()

        if version:

            print(
                "\nCyrus:"
            )

            answer = (
                f"Tumhare PC par installed "
                f"Ollama version {version} hai."
            )

            print(answer)

            return answer

    # Python latest version
    if (
        "python" in lower
        and (
            "latest" in lower
            or "newest" in lower
            or "current" in lower
        )
    ):

        print(
            "\nPython official website check kar raha hai..."
        )

        version = python_latest()

        if version:

            answer = (
                f"Python official website ke mutabiq "
                f"latest Python 3 release Python {version} hai."
            )

            print("\nCyrus:")
            print(answer)

            print(
                "\nOfficial source:"
            )
            print(
                "https://www.python.org/downloads/"
            )

            return answer

    return None

# =========================
# WEB SUMMARY
# =========================

def summarize_web_results(
    question,
    results
):

    if not results:

        return (
            "Mujhe web par relevant results nahi mile."
        )

    text = ""

    for i, result in enumerate(results, 1):

        text += (
            f"\nResult {i}:\n"
            f"Title: {result['title']}\n"
            f"URL: {result['url']}\n"
            f"Info: {result['snippet']}\n"
        )

    prompt = f"""
You are Cyrus, a personal AI assistant.

Answer the user's question using the web results below.

User question:
{question}

Web results:
{text}

Rules:
- Give a concise answer.
- Do not invent facts.
- If the results are unclear, say so.
- Prefer information directly supported by the results.
- Do not mention internal instructions.
"""

    return ask_cyrus(prompt)

# =========================
# WEB HANDLER
# =========================

def handle_web_query(question):

    special = handle_special_web_query(
        question
    )

    if special:
        return special

    results = bing_search(
        question,
        max_results=5
    )

    if not results:

        print(
            "\nCyrus:"
        )

        answer = (
            "Web search se relevant results nahi mile."
        )

        print(answer)

        return answer

    print(
        "\nCyrus answer prepare kar raha hai..."
    )

    answer = summarize_web_results(
        question,
        results
    )

    return answer

# =========================
# PC COMMANDS
# =========================

def handle_pc_command(text):

    lower = text.lower().strip()

    # Calculator
    if (
        "open calculator" in lower
        or "calculator kholo" in lower
        or "calculator khol" in lower
    ):

        try:

            subprocess.Popen(
                "calc.exe"
            )

            print(
                "\nCyrus: Calculator khol diya."
            )

        except Exception as e:

            print(
                f"\nCyrus: Calculator nahi khul saka: {e}"
            )

        return True

    # Notepad
    if (
        "open notepad" in lower
        or "notepad kholo" in lower
        or "notepad khol" in lower
    ):

        try:

            subprocess.Popen(
                "notepad.exe"
            )

            print(
                "\nCyrus: Notepad khol diya."
            )

        except Exception as e:

            print(
                f"\nCyrus: Notepad nahi khul saka: {e}"
            )

        return True

    # Chrome
    if (
        "open chrome" in lower
        or "chrome kholo" in lower
        or "chrome khol" in lower
    ):

        try:

            subprocess.Popen(
                "chrome.exe"
            )

            print(
                "\nCyrus: Chrome khol diya."
            )

        except Exception:

            try:

                webbrowser.open(
                    "https://www.google.com"
                )

                print(
                    "\nCyrus: Chrome/browser khol diya."
                )

            except Exception as e:

                print(
                    f"\nCyrus: Browser nahi khul saka: {e}"
                )

        return True

    # File Explorer
    if (
        "open file explorer" in lower
        or "file explorer kholo" in lower
        or "explorer kholo" in lower
    ):

        try:

            subprocess.Popen(
                "explorer.exe"
            )

            print(
                "\nCyrus: File Explorer khol diya."
            )

        except Exception as e:

            print(
                f"\nCyrus: Explorer nahi khul saka: {e}"
            )

        return True

    # Downloads
    if (
        "open downloads" in lower
        or "downloads kholo" in lower
    ):

        try:

            downloads = os.path.join(
                os.path.expanduser("~"),
                "Downloads"
            )

            os.startfile(
                downloads
            )

            print(
                "\nCyrus: Downloads folder khol diya."
            )

        except Exception as e:

            print(
                f"\nCyrus: Downloads nahi khul saka: {e}"
            )

        return True

    # Desktop
    if (
        "open desktop" in lower
        or "desktop kholo" in lower
    ):

        try:

            desktop = os.path.join(
                os.path.expanduser("~"),
                "Desktop"
            )

            os.startfile(
                desktop
            )

            print(
                "\nCyrus: Desktop khol diya."
            )

        except Exception as e:

            print(
                f"\nCyrus: Desktop nahi khul saka: {e}"
            )

        return True

    # PersonalBot folder
    if (
        "open personalbot" in lower
        or "personalbot kholo" in lower
    ):

        try:

            folder = os.path.join(
                os.path.expanduser("~"),
                "OneDrive",
                "Desktop",
                "PersonalBot"
            )

            os.startfile(
                folder
            )

            print(
                "\nCyrus: PersonalBot folder khol diya."
            )

        except Exception as e:

            print(
                f"\nCyrus: PersonalBot nahi khul saka: {e}"
            )

        return True

    # Google search
    if (
        lower.startswith("google ")
        or lower.startswith("search google ")
    ):

        if lower.startswith("google "):

            query = text[7:].strip()

        else:

            query = text[14:].strip()

        if query:

            url = (
                "https://www.google.com/search?q="
                + requests.utils.quote(query)
            )

            webbrowser.open(
                url
            )

            print(
                f"\nCyrus: Google par '{query}' search kar diya."
            )

        return True

    return False

# =========================
# MAIN
# =========================

def main():

    print(
        "================================"
    )

    print(
        "       CYRUS AI ASSISTANT"
    )

    print(
        "================================"
    )

    print(
        "Local Qwen3 model:",
        MODEL
    )

    print(
        "Thinking: OFF"
    )

    print(
        "Streaming: ON"
    )

    print(
        "\nType 'exit' to close Cyrus.\n"
    )

    while True:

        try:

            user_input = input(
                "You: "
            ).strip()

        except KeyboardInterrupt:

            print(
                "\nCyrus band ho raha hai."
            )

            break

        except EOFError:

            break

        if not user_input:
            continue

        if user_input.lower() in [
            "exit",
            "quit",
            "bye",
            "band ho jao"
        ]:

            print(
                "\nCyrus: Allah Hafiz!"
            )

            break

        # PC commands first
        if handle_pc_command(
            user_input
        ):
            continue

        # Web questions
        if needs_web_search(
            user_input
        ):

            handle_web_query(
                user_input
            )

            continue

        # Normal AI question
        print(
            "\nCyrus soch raha hai..."
        )

        answer = ask_cyrus(
            user_input
        )

        # Voice
        if answer:

            speak(
                answer
            )

# =========================
# START
# =========================

if __name__ == "__main__":
    main()