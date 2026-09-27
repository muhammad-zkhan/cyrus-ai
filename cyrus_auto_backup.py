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

        subprocess.Popen(
            "explorer.exe"
        )

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
            r"C:\Users\Zartash\OneDrive"
            r"\Desktop\PersonalBot"
        )

        os.startfile(path)

        return "PersonalBot folder khol diya."

    if command.startswith(
        "search google for "
    ):

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
                f"Google par {query} "
                "search kar diya."
            )

    return None


# =========================
# QUERY IMPROVER
# =========================

def improve_query(query):

    q = query.lower().strip()

    # Python
    if "python" in q and (
        "version" in q
        or "latest" in q
        or "newest" in q
    ):

        return (
            query
            + " site:python.org"
        )

    # OpenAI / ChatGPT
    if (
        "openai" in q
        or "chatgpt" in q
    ):

        if (
            "api" in q
            or "official" in q
            or "latest" in q
            or "version" in q
        ):

            return (
                query
                + " site:openai.com"
            )

    # Microsoft / Windows
    if (
        "windows" in q
        or "microsoft" in q
    ):

        if (
            "latest" in q
            or "version" in q
            or "update" in q
            or "official" in q
        ):

            return (
                query
                + " site:microsoft.com"
            )

    # Ollama
    if "ollama" in q:

        return (
            query
            + " site:ollama.com"
        )

    # Android
    if "android" in q:

        if (
            "latest" in q
            or "version" in q
            or "update" in q
        ):

            return (
                query
                + " site:android.com"
            )

    # GitHub
    if "github" in q:

        return (
            query
            + " site:github.com"
        )

    # General current/latest
    if (
        "latest" in q
        or "current" in q
        or "official" in q
    ):

        return (
            query
            + " official"
        )

    return query


# =========================
# OFFICIAL PYTHON SEARCH
# =========================

def official_python_search(query):

    print(
        "Python official website "
        "check kar raha hai..."
    )

    url = (
        "https://www.python.org/getit/"
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/153.0.0.0 "
            "Safari/537.36"
        )
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # Find the main release information
        version = None

        for text in soup.stripped_strings:

            if (
                "Latest Python 3 Release"
                in text
            ):

                # Look at nearby page text
                version = text
                break

        # Get clean page text
        page_text = soup.get_text(
            " ",
            strip=True
        )

        # Try to extract latest version
        import re

        matches = re.findall(
            r"Python\s+3\.\d+\.\d+",
            page_text
        )

        latest_version = None

        if matches:

            # Remove duplicates
            unique_versions = []

            for item in matches:

                if item not in unique_versions:
                    unique_versions.append(item)

            # Prefer 3.14 if present
            for item in unique_versions:

                if item.startswith(
                    "Python 3.14."
                ):

                    latest_version = item
                    break

            if not latest_version:
                latest_version = (
                    unique_versions[0]
                )

        if latest_version:

            return (
                "Python official website "
                "ke mutabiq latest Python 3 "
                f"release {latest_version} hai.\n\n"
                "Official source:\n"
                "https://www.python.org/getit/"
            )

        return (
            "Python official website "
            "se information mil gayi, "
            "lekin version automatically "
            "identify nahi ho saka.\n\n"
            "Official source:\n"
            "https://www.python.org/getit/"
        )

    except Exception as e:

        print(
            "Python official search error:",
            e
        )

        return (
            "Python official website "
            "read nahi ho saki. "
            "Bing search try kar raha hoon..."
        )


# =========================
# BING SEARCH
# =========================

def web_search(query):

    search_query = improve_query(
        query
    )

    print(
        f"Search query: {search_query}"
    )

    url = (
        "https://www.bing.com/search?q="
        + quote_plus(search_query)
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/153.0.0.0 "
            "Safari/537.36"
        ),
        "Accept-Language":
            "en-US,en;q=0.9"
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

            snippet_tag = (
                result.select_one(
                    ".b_caption p"
                )
            )

            snippet = ""

            if snippet_tag:

                snippet = (
                    snippet_tag.get_text(
                        " ",
                        strip=True
                    )
                )

            if title and link:

                results.append({
                    "title": title,
                    "url": link,
                    "snippet": snippet
                })

            if len(results) >= 5:
                break

        print(
            f"Bing results found: "
            f"{len(results)}"
        )

        return results

    except Exception as e:

        print(
            "Bing search error:",
            e
        )

        return []


# =========================
# RESULT FILTER
# =========================

def filter_results(
    results,
    query
):

    if not results:
        return []

    q_words = [
        word.lower()
        for word in query.split()
        if len(word) > 2
    ]

    scored = []

    for result in results:

        title = (
            result["title"]
            .lower()
        )

        snippet = (
            result["snippet"]
            .lower()
        )

        url = (
            result["url"]
            .lower()
        )

        score = 0

        # Query words
        for word in q_words:

            if word in title:
                score += 5

            if word in snippet:
                score += 2

            if word in url:
                score += 1

        # Official domains
        official_domains = [
            "python.org",
            "openai.com",
            "microsoft.com",
            "ollama.com",
            "android.com",
            "apple.com",
            "github.com"
        ]

        for domain in official_domains:

            if domain in url:
                score += 4

        scored.append(
            (
                score,
                result
            )
        )

    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return [
        item[1]
        for item in scored[:3]
    ]


# =========================
# WEB ANSWER
# =========================

def web_answer(query):

    print(
        "Cyrus Bing par search kar raha hai..."
    )

    q = query.lower()

    # Python official information
    if (
        "python" in q
        and (
            "version" in q
            or "latest" in q
            or "newest" in q
        )
    ):

        result = official_python_search(
            query
        )

        # If official search worked
        if "Official source:" in result:

            return result

        # Otherwise continue to Bing

    # Normal Bing search
    results = web_search(
        query
    )

    if not results:

        return (
            "Web search se "
            "results nahi mile."
        )

    results = filter_results(
        results,
        query
    )

    print(
        "Bing results filter ho gaye."
    )

    answer = (
        f"Web results for: "
        f"{query}\n\n"
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

print(
    "==================================="
)

print(
    "          CYRUS PERSONAL AI"
)

print(
    "==================================="
)

print(
    "Cyrus ready hai."
)

print(
    "Type 'exit' to close.\n"
)


while True:

    try:

        user_input = input(
            "You: "
        ).strip()

        if not user_input:
            continue

        # EXIT
        if (
            user_input.lower()
            == "exit"
        ):

            print(
                "Cyrus: Allah Hafiz!"
            )

            break

        # WEB SEARCH
        if (
            user_input.lower()
            .startswith(
                "search web for "
            )
        ):

            query = user_input[
                len(
                    "search web for "
                ):
            ].strip()

            if query:

                answer = web_answer(
                    query
                )

                print(
                    "\nCyrus:"
                )

                print(
                    answer
                )

            continue

        # PC COMMAND
        pc_result = pc_command(
            user_input
        )

        if pc_result:

            print(
                "\nCyrus:",
                pc_result
            )

            speak(
                pc_result
            )

            continue

        # NORMAL AI CHAT
        answer = ask_cyrus(
            user_input
        )

        print(
            "\nCyrus:",
            answer
        )

        speak(
            answer
        )

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