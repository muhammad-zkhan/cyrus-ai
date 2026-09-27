import json
import urllib.request
import subprocess
import os
import webbrowser
import pyttsx3
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus


# =========================
# SETTINGS
# =========================

MODEL = "qwen3:4b"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"


# =========================
# VOICE
# =========================

engine = pyttsx3.init()
engine.setProperty("rate", 175)
engine.setProperty("volume", 1.0)


def speak(text):
    try:
        engine.say(text)
        engine.runAndWait()
    except:
        pass


# =========================
# AI CHAT
# =========================

def ask_cyrus(prompt):

    data = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Cyrus, a helpful personal AI assistant. "
                    "Answer clearly, naturally and briefly."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "options": {
            "num_predict": 150
        }
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=60
    ) as response:

        result = json.loads(
            response.read().decode("utf-8")
        )

    return result["message"]["content"].strip()


# =========================
# PC COMMANDS
# =========================

def pc_command(text):

    command = text.lower().strip()

    if command == "open calculator":
        subprocess.Popen("calc.exe")
        return "Calculator khol diya."

    if command == "open notepad":
        subprocess.Popen("notepad.exe")
        return "Notepad khol diya."

    if command == "open chrome":
        subprocess.Popen(
            "cmd /c start chrome",
            shell=True
        )
        return "Chrome khol diya."

    if command == "open file explorer":
        subprocess.Popen("explorer.exe")
        return "File Explorer khol diya."

    if command == "open downloads":

        path = os.path.join(
            os.path.expanduser("~"),
            "Downloads"
        )

        os.startfile(path)

        return "Downloads folder khol diya."

    if command == "open desktop":

        path = os.path.join(
            os.path.expanduser("~"),
            "Desktop"
        )

        os.startfile(path)

        return "Desktop khol diya."

    if command == "open personalbot":

        path = (
            r"C:\Users\Zartash\OneDrive\Desktop"
            r"\PersonalBot"
        )

        os.startfile(path)

        return "PersonalBot folder khol diya."

    if command.startswith("search google for "):

        query = text[
            len("search google for "):
        ].strip()

        if query:

            url = (
                "https://www.google.com/search?q="
                + quote_plus(query)
            )

            webbrowser.open(url)

            return (
                f"Google par {query} search kar diya."
            )

    return None


# =========================
# BING SEARCH
# =========================

def web_search(query):

    url = (
        "https://www.bing.com/search?q="
        + quote_plus(query)
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        results = []

        for result in soup.select(
            "li.b_algo"
        ):

            title_tag = result.select_one(
                "h2 a"
            )

            if not title_tag:
                continue

            title = title_tag.get_text(
                " ",
                strip=True
            )

            link = title_tag.get(
                "href",
                ""
            )

            snippet_tag = result.select_one(
                ".b_caption p"
            )

            snippet = ""

            if snippet_tag:

                snippet = snippet_tag.get_text(
                    " ",
                    strip=True
                )

            if title and link:

                results.append({
                    "title": title,
                    "url": link,
                    "snippet": snippet
                })

            if len(results) >= 3:
                break

        print(
            f"Bing results found: {len(results)}"
        )

        return results

    except Exception as e:

        print(
            "Bing search error:",
            e
        )

        return []


# =========================
# WEB ANSWER
# =========================

def web_answer(query):

    print(
        "Cyrus Bing par search kar raha hai..."
    )

    results = web_search(query)

    if not results:

        return (
            "Web search se results nahi mile."
        )

    print(
        "Bing se results mil gaye."
    )

    answer = (
        f"Web results for: {query}\n\n"
    )

    for i, result in enumerate(
        results,
        1
    ):

        title = result["title"]
        snippet = result["snippet"]
        url = result["url"]

        answer += (
            f"{i}. {title}\n"
            f"{snippet}\n"
            f"{url}\n\n"
        )

    return answer


# =========================
# CYRUS START
# =========================

print("===================================")
print("          CYRUS PERSONAL AI")
print("===================================")
print("Cyrus ready hai.")
print("Type 'exit' to close.\n")


while True:

    try:

        user_input = input(
            "You: "
        ).strip()

        if not user_input:
            continue

        if user_input.lower() == "exit":

            print(
                "Cyrus: Allah Hafiz!"
            )

            break


        # =========================
        # WEB SEARCH
        # =========================

        if user_input.lower().startswith(
            "search web for "
        ):

            query = user_input[
                len("search web for "):
            ].strip()

            if query:

                answer = web_answer(
                    query
                )

                print(
                    "\nCyrus:"
                )

                print(answer)

            continue


        # =========================
        # PC COMMAND
        # =========================

        pc_result = pc_command(
            user_input
        )

        if pc_result:

            print(
                "\nCyrus:",
                pc_result
            )

            speak(pc_result)

            continue


        # =========================
        # NORMAL AI CHAT
        # =========================

        answer = ask_cyrus(
            user_input
        )

        print(
            "\nCyrus:",
            answer
        )

        speak(answer)


    except KeyboardInterrupt:

        print(
            "\nCyrus: Allah Hafiz!"
        )

        break


    except Exception as e:

        print(
            "\nError:",
            e
        )