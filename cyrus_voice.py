import requests
import json
import re
import subprocess
import os
import webbrowser
import pyttsx3
from bs4 import BeautifulSoup


# =========================
# SETTINGS
# =========================

MODEL = "qwen3:4b-instruct"
OLLAMA_URL = "http://localhost:11434/api/chat"

engine = pyttsx3.init()
engine.setProperty("rate", 175)


# =========================
# VOICE
# =========================

def speak(text):
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception:
        pass


# =========================
# CLEAN ANSWER
# =========================

def clean_short_answer(answer):

    if not answer:
        return ""

    # Remove thinking blocks
    answer = re.sub(
        r"<think>.*?</think>",
        "",
        answer,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Remove common thinking/meta lines
    lines = answer.splitlines()
    cleaned = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        lower = line.lower()

        blocked = [
            "let me think",
            "i need to",
            "i should",
            "we need to",
            "thinking",
            "analysis:",
            "reasoning:",
            "let's analyze",
            "first, i",
            "the user asks",
            "i will answer",
            "i'll answer",
            "i need answer"
        ]

        if any(x in lower for x in blocked):
            continue

        cleaned.append(line)

    answer = " ".join(cleaned)

    # Remove markdown
    answer = re.sub(r"\*\*(.*?)\*\*", r"\1", answer)
    answer = re.sub(r"\*(.*?)\*", r"\1", answer)
    answer = re.sub(r"`(.*?)`", r"\1", answer)

    # Remove bullets / numbering
    answer = re.sub(r"^\s*[-•]\s*", "", answer)
    answer = re.sub(r"^\s*\d+[\.\)]\s*", "", answer)

    # Remove extra spaces
    answer = re.sub(r"\s+", " ", answer).strip()

    # Keep only first sentence
    parts = re.split(r"(?<=[.!?])\s+", answer)

    if parts:
        answer = parts[0].strip()

    return answer


# =========================
# OLLAMA VERSION
# =========================

def get_ollama_version():

    try:
        response = requests.get(
            "http://localhost:11434/api/version",
            timeout=5
        )

        if response.ok:
            data = response.json()
            return data.get("version", "unknown")

    except Exception:
        pass

    return None


# =========================
# ASK CYRUS
# =========================

def ask_cyrus(user_input):

    system_prompt = """
You are Cyrus, a personal AI assistant.

Answer directly and naturally.

Rules:
- Keep answers extremely short.
- For a simple question, answer in ONE short sentence.
- Do not use bullets.
- Do not use numbering.
- Do not use headings.
- Do not repeat the question.
- Do not explain your reasoning.
- Do not show thinking or analysis.
- Do not say what you are going to do.
- Give only the useful answer.
"""

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_input
                + "\n\nAnswer in one short sentence only. No points. No list. No explanation. /no_think"
            }
        ],
        "stream": True,
        "think": False,
        "keep_alive": "15m",
        "options": {
            "temperature": 0.1,
            "top_p": 0.7,
            "repeat_penalty": 1.2,
            "num_predict": 40
        }
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            stream=True,
            timeout=(10, 180)
        )

        response.raise_for_status()

        full_answer = ""

        for line in response.iter_lines():

            if not line:
                continue

            try:
                data = json.loads(line.decode("utf-8"))

                message = data.get("message", {})
                content = message.get("content", "")

                if content:
                    full_answer += content

                if data.get("done"):
                    break

            except Exception:
                continue

        answer = clean_short_answer(full_answer)

        if not answer:
            answer = "Sorry, mujhe iska answer nahi mila."

        print("\nCyrus:")
        print(answer)

        return answer

    except requests.exceptions.ConnectionError:

        print("\nCyrus:")
        print("Ollama is not running.")

        return "Ollama is not running."

    except requests.exceptions.Timeout:

        print("\nCyrus:")
        print("Response lene mein zyada time lag raha hai.")

        return "Response lene mein zyada time lag raha hai."

    except Exception as e:

        print("\nCyrus:")
        print("Error:", e)

        return "Mujhe ek error aa gaya."


# =========================
# PYTHON LATEST VERSION
# =========================

def python_latest():

    try:

        url = "https://www.python.org/downloads/"

        r = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        soup = BeautifulSoup(
            r.text,
            "html.parser"
        )

        text = soup.get_text(" ", strip=True)

        match = re.search(
            r"Latest Python 3 Release - Python (\d+\.\d+\.\d+)",
            text
        )

        if match:
            return match.group(1)

        match = re.search(
            r"Python (\d+\.\d+\.\d+)",
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

def bing_search(query, limit=5):

    try:

        url = "https://www.bing.com/search"

        params = {
            "q": query
        }

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        results = []

        for item in soup.select("li.b_algo"):

            title_tag = item.select_one("h2")
            link_tag = item.select_one("h2 a")

            if not title_tag or not link_tag:
                continue

            title = title_tag.get_text(
                " ",
                strip=True
            )

            link = link_tag.get("href")

            description_tag = item.select_one(
                ".b_caption p"
            )

            description = ""

            if description_tag:
                description = description_tag.get_text(
                    " ",
                    strip=True
                )

            results.append({
                "title": title,
                "url": link,
                "description": description
            })

            if len(results) >= limit:
                break

        return results

    except Exception:

        return []


# =========================
# WEB KEYWORDS
# =========================

WEB_WORDS = [
    "latest",
    "today",
    "current",
    "news",
    "weather",
    "price",
    "version",
    "recent",
    "update",
    "who is",
    "what happened",
    "search",
    "google",
    "internet",
    "online"
]


def needs_web_search(text):

    text_lower = text.lower()

    for word in WEB_WORDS:

        if word in text_lower:
            return True

    return False


# =========================
# SPECIAL WEB QUESTIONS
# =========================

def handle_special_web_query(user_input):

    text = user_input.lower()

    # Ollama version
    if "ollama version" in text or "ollama ka version" in text:

        version = get_ollama_version()

        if version:
            return f"Ollama ka installed version {version} hai."

        return "Ollama ka version check nahi ho saka."

    # Python latest version
    if (
        "latest python" in text
        or "python latest" in text
        or "latest python version" in text
        or "python ka latest version" in text
    ):

        version = python_latest()

        if version:
            return f"Python ka latest version {version} hai."

        return "Python ka latest version check nahi ho saka."

    return None


# =========================
# SUMMARIZE WEB RESULTS
# =========================

def summarize_web_results(
    question,
    results
):

    if not results:
        return "Mujhe web par relevant result nahi mila."

    text = ""

    for i, result in enumerate(results[:5], 1):

        text += f"""
Result {i}
Title: {result['title']}
Description: {result['description']}
URL: {result['url']}
"""

    prompt = f"""
Question:
{question}

Web search results:
{text}

Answer the question using only the useful information from these results.

Rules:
- Answer in ONE short sentence.
- No bullets.
- No numbering.
- No headings.
- No reasoning.
- No unnecessary details.
"""

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Give a short direct answer."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": True,
        "think": False,
        "keep_alive": "15m",
        "options": {
            "temperature": 0.1,
            "top_p": 0.7,
            "repeat_penalty": 1.2,
            "num_predict": 40
        }
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            stream=True,
            timeout=(10, 180)
        )

        response.raise_for_status()

        full_answer = ""

        for line in response.iter_lines():

            if not line:
                continue

            try:

                data = json.loads(
                    line.decode("utf-8")
                )

                content = data.get(
                    "message",
                    {}
                ).get(
                    "content",
                    ""
                )

                if content:
                    full_answer += content

                if data.get("done"):
                    break

            except Exception:
                continue

        return clean_short_answer(
            full_answer
        )

    except Exception:

        return "Web result mila lekin answer prepare nahi ho saka."


# =========================
# WEB QUERY HANDLER
# =========================

def handle_web_query(user_input):

    special = handle_special_web_query(
        user_input
    )

    if special:
        return special

    results = bing_search(
        user_input,
        limit=5
    )

    if not results:
        return None

    return summarize_web_results(
        user_input,
        results
    )


# =========================
# OPEN PROGRAMS
# =========================

def open_program(name):

    name = name.lower().strip()

    if name in [
        "calculator",
        "calc"
    ]:

        subprocess.Popen(
            "calc.exe"
        )

        return "Calculator khol diya."

    if name in [
        "notepad"
    ]:

        subprocess.Popen(
            "notepad.exe"
        )

        return "Notepad khol diya."

    if name in [
        "chrome",
        "google chrome"
    ]:

        possible_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]

        for path in possible_paths:

            if os.path.exists(path):

                subprocess.Popen(
                    path
                )

                return "Chrome khol diya."

        webbrowser.open(
            "https://www.google.com"
        )

        return "Google Chrome khol diya."

    return None


# =========================
# OPEN FOLDERS
# =========================

def open_folder(folder):

    folder = folder.lower().strip()

    if folder == "downloads":

        path = os.path.join(
            os.path.expanduser("~"),
            "Downloads"
        )

        os.startfile(path)

        return "Downloads folder khol diya."

    if folder == "desktop":

        path = os.path.join(
            os.path.expanduser("~"),
            "Desktop"
        )

        os.startfile(path)

        return "Desktop khol diya."

    if folder == "personalbot":

        path = r"C:\Users\Zartash\OneDrive\Desktop\PersonalBot"

        if os.path.exists(path):

            os.startfile(path)

            return "PersonalBot folder khol diya."

    return None


# =========================
# PC COMMANDS
# =========================

def handle_pc_command(user_input):

    text = user_input.lower().strip()

    # Calculator
    if (
        "calculator kholo" in text
        or "calculator open" in text
        or "calc kholo" in text
    ):

        return open_program(
            "calculator"
        )

    # Notepad
    if (
        "notepad kholo" in text
        or "notepad open" in text
    ):

        return open_program(
            "notepad"
        )

    # Chrome
    if (
        "chrome kholo" in text
        or "chrome open" in text
        or "google kholo" in text
    ):

        return open_program(
            "chrome"
        )

    # Downloads
    if (
        "downloads kholo" in text
        or "downloads open" in text
    ):

        return open_folder(
            "downloads"
        )

    # Desktop
    if (
        "desktop kholo" in text
        or "desktop open" in text
    ):

        return open_folder(
            "desktop"
        )

    # PersonalBot
    if (
        "personalbot kholo" in text
        or "personal bot kholo" in text
    ):

        return open_folder(
            "personalbot"
        )

    # Google search
    if text.startswith("google "):

        query = user_input[
            len("google "):
        ].strip()

        if query:

            webbrowser.open(
                "https://www.google.com/search?q="
                + requests.utils.quote(query)
            )

            return "Google par search kar raha hoon."

    return None


# =========================
# MAIN
# =========================

def main():

    print("=" * 45)
    print("Cyrus Personal AI Assistant")
    print("=" * 45)

    print(
        f"Model: {MODEL}"
    )

    print(
        "Type 'exit' to close Cyrus."
    )

    while True:

        try:

            user_input = input(
                "\nYou: "
            ).strip()

        except KeyboardInterrupt:

            print(
                "\nCyrus closed."
            )

            break

        except EOFError:

            break

        if not user_input:
            continue

        if user_input.lower() in [
            "exit",
            "quit",
            "bye"
        ]:

            print(
                "Cyrus: Bye!"
            )

            break

        # =====================
        # PC COMMANDS
        # =====================

        pc_result = handle_pc_command(
            user_input
        )

        if pc_result:

            print(
                "\nCyrus:"
            )

            print(
                pc_result
            )

            speak(
                pc_result
            )

            continue

        # =====================
        # WEB SEARCH
        # =====================

        if needs_web_search(
            user_input
        ):

            print(
                "\nCyrus web par search kar raha hai..."
            )

            web_answer = handle_web_query(
                user_input
            )

            if web_answer:

                print(
                    "\nCyrus:"
                )

                print(
                    web_answer
                )

                speak(
                    web_answer
                )

                continue

        # =====================
        # NORMAL AI
        # =====================

        answer = ask_cyrus(
            user_input
        )

        if answer:
            speak(
                answer
            )


# =========================
# START
# =========================

if __name__ == "__main__":
    main()