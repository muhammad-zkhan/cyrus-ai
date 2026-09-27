import requests
import json
import re
import subprocess
import os
import webbrowser
import pyttsx3
import ast
import operator
from datetime import datetime
from bs4 import BeautifulSoup


# =========================================================
# SETTINGS
# =========================================================

MODEL = "qwen3:4b-instruct"

OLLAMA_URL = "http://localhost:11434/api/chat"

MEMORY_FILE = "cyrus_memory.json"
CHAT_FILE = "cyrus_chat.json"

MAX_RECENT_MESSAGES = 14
MAX_RELEVANT_MESSAGES = 12
MAX_STORED_CHAT_MESSAGES = 500

REQUEST_TIMEOUT = (10, 180)


# =========================================================
# VOICE
# =========================================================

try:
    engine = pyttsx3.init()
    engine.setProperty("rate", 175)
    VOICE_ENABLED = True
except Exception:
    engine = None
    VOICE_ENABLED = False


def speak(text):

    if not VOICE_ENABLED:
        return

    try:
        engine.say(text)
        engine.runAndWait()
    except Exception:
        pass


# =========================================================
# SAFE JSON HELPERS
# =========================================================

def load_json_file(filename, default):

    if not os.path.exists(filename):
        return default

    try:
        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception:
        return default


def save_json_file(filename, data):

    try:
        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception:
        return False


# =========================================================
# PERMANENT MEMORY
# =========================================================

def load_memory():

    data = load_json_file(
        MEMORY_FILE,
        {"memories": []}
    )

    if not isinstance(data, dict):
        data = {"memories": []}

    if not isinstance(
        data.get("memories"),
        list
    ):
        data["memories"] = []

    return data


def save_memory(data):

    save_json_file(
        MEMORY_FILE,
        data
    )


def add_memory(memory):

    memory = memory.strip()

    if not memory:
        return False

    data = load_memory()

    for existing in data["memories"]:

        if existing.lower() == memory.lower():
            return False

    data["memories"].append(memory)

    save_memory(data)

    return True


def forget_memory(memory):

    memory = memory.strip().lower()

    data = load_memory()

    old_count = len(
        data["memories"]
    )

    data["memories"] = [
        item
        for item in data["memories"]
        if item.lower() != memory
    ]

    save_memory(data)

    return len(data["memories"]) < old_count


def clear_memory():

    save_memory({
        "memories": []
    })


def get_memory_text():

    data = load_memory()

    memories = data.get(
        "memories",
        []
    )

    if not memories:
        return "No permanent memories."

    return "\n".join(
        f"- {memory}"
        for memory in memories
    )


# =========================================================
# SECRET PROTECTION
# =========================================================

SECRET_WORDS = [

    "password",
    "passcode",
    "otp",
    "one time password",
    "credit card",
    "card number",
    "cvv",
    "cvc",
    "api key",
    "api token",
    "secret key",
    "private key",
    "security code",
    "verification code"

]


def contains_secret(text):

    lower = text.lower()

    for word in SECRET_WORDS:

        if word in lower:
            return True

    return False


# =========================================================
# CHAT HISTORY
# =========================================================

def load_chat_history():

    data = load_json_file(
        CHAT_FILE,
        []
    )

    if not isinstance(data, list):
        return []

    return data


def save_chat_history(history):

    save_json_file(
        CHAT_FILE,
        history
    )


def add_chat_message(
    role,
    content
):

    history = load_chat_history()

    history.append({

        "role": role,

        "content": content

    })

    if len(history) > MAX_STORED_CHAT_MESSAGES:

        history = history[
            -MAX_STORED_CHAT_MESSAGES:
        ]

    save_chat_history(history)


def clear_chat_history():

    save_chat_history([])


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_text(text):

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# KEYWORDS
# =========================================================

STOP_WORDS = {

    "the",
    "a",
    "an",
    "is",
    "am",
    "are",
    "was",
    "were",
    "be",
    "been",
    "to",
    "of",
    "and",
    "or",
    "in",
    "on",
    "for",
    "with",
    "from",
    "this",
    "that",
    "it",
    "me",
    "my",
    "i",
    "you",
    "your",
    "we",
    "our",
    "they",
    "their",
    "hai",
    "ho",
    "ka",
    "ki",
    "ke",
    "ko",
    "mein",
    "mujhe",
    "mera",
    "mere",
    "meri",
    "tum",
    "tumhe",
    "tumhein",
    "ye",
    "yeh",
    "wo",
    "woh",
    "kya",
    "kyun",
    "kaise",
    "kab",
    "kahan",
    "tha",
    "thi",
    "the",
    "hota",
    "hoti",
    "hoon",
    "kr",
    "kar",
    "karo",
    "koi",
    "kuch",
    "aur",
    "phir",
    "bhai",
    "acha",
    "haan",
    "han",
    "please",
    "tell",
    "give",
    "about",
    "what",
    "why",
    "how",
    "when",
    "where",
    "who",
    "should",
    "would",
    "could",
    "can"

}


def get_keywords(text):

    words = normalize_text(text).split()

    return {

        word
        for word in words

        if len(word) >= 3
        and word not in STOP_WORDS

    }


# =========================================================
# TOPIC / REFERENCE DETECTION
# =========================================================

REFERENCE_WORDS = {

    "it",
    "that",
    "this",
    "they",
    "them",
    "he",
    "she",
    "phir",
    "kyun",
    "kyun bhai",
    "kaise",
    "matlab",
    "then",
    "why",
    "how",
    "what",
    "where",
    "when",
    "who",
    "really"

}


def contains_reference_word(text):

    normalized = normalize_text(text)

    if normalized in REFERENCE_WORDS:
        return True

    reference_phrases = [

        "what about it",
        "what about that",
        "what should i do about it",
        "what should i do about that",
        "and why",
        "and how",
        "then what",
        "then what should i do",
        "why is that",
        "how is that",
        "how come"

    ]

    for phrase in reference_phrases:

        if phrase in normalized:
            return True

    return False


def get_recent_topic_messages(history):

    if not history:
        return []

    return history[
        -MAX_RECENT_MESSAGES:
    ]


# =========================================================
# RELEVANT OLD HISTORY
# =========================================================

def get_relevant_history(
    user_input,
    history
):

    if not history:
        return []

    query_keywords = get_keywords(
        user_input
    )

    if not query_keywords:
        return []

    scored = []

    total = max(
        len(history),
        1
    )

    for index, item in enumerate(history):

        role = item.get(
            "role",
            ""
        )

        content = item.get(
            "content",
            ""
        )

        if role not in [
            "user",
            "assistant"
        ]:
            continue

        if not content:
            continue

        message_keywords = get_keywords(
            content
        )

        overlap = (
            query_keywords
            & message_keywords
        )

        score = 0

        if overlap:
            score += len(overlap) * 2

        # More recent messages get a small bonus
        recency = index / total

        score += recency * 0.8

        # For reference questions, recent messages
        # are much more important.
        if contains_reference_word(user_input):

            score += recency * 2

        if score > 0:

            scored.append(
                (
                    score,
                    index,
                    item
                )
            )

    scored.sort(
        key=lambda x: (
            x[0],
            x[1]
        ),
        reverse=True
    )

    selected = []

    for score, index, item in scored:

        selected.append(
            (
                index,
                item
            )
        )

        if len(selected) >= MAX_RELEVANT_MESSAGES:
            break

    selected.sort(
        key=lambda x: x[0]
    )

    return [
        item
        for index, item in selected
    ]


# =========================================================
# BUILD SMART CONTEXT
# =========================================================

def build_conversation_context(
    user_input,
    history
):

    if not history:
        return []

    recent = get_recent_topic_messages(
        history
    )

    old_history = history[
        :-MAX_RECENT_MESSAGES
    ]

    relevant = get_relevant_history(
        user_input,
        old_history
    )

    combined = []

    seen = set()

    # If user is using a reference such as "it",
    # keep recent conversation especially strongly.
    if contains_reference_word(user_input):

        for item in recent:

            key = (
                item.get("role", ""),
                item.get("content", "")
            )

            if key not in seen:

                seen.add(key)
                combined.append(item)

        for item in relevant:

            key = (
                item.get("role", ""),
                item.get("content", "")
            )

            if key not in seen:

                seen.add(key)
                combined.append(item)

    else:

        for item in relevant:

            key = (
                item.get("role", ""),
                item.get("content", "")
            )

            if key not in seen:

                seen.add(key)
                combined.append(item)

        for item in recent:

            key = (
                item.get("role", ""),
                item.get("content", "")
            )

            if key not in seen:

                seen.add(key)
                combined.append(item)

    return combined


# =========================================================
# MEMORY COMMANDS
# =========================================================

def handle_memory_command(user_input):

    text = user_input.strip()

    lower = normalize_text(text)


    # =====================================================
    # SHOW MEMORY
    # =====================================================

    show_commands = [

        "what do you remember",
        "what do you remember about me",
        "what do you know about me",
        "tumhein mere bare mein kya yaad hai",
        "tumhe mere bare mein kya yaad hai",
        "tumhe mere bare mein kya pata hai",
        "tumhein mere bare mein kya pata hai",
        "memory",
        "show memory",
        "show my memory",
        "meri memory dikhao",
        "meri yaadash dikhao"

    ]

    if lower in show_commands:

        memories = load_memory()[
            "memories"
        ]

        if not memories:

            return (
                "Mujhe abhi kuch yaad nahi hai."
            )

        return (
            "Mujhe ye baatein yaad hain:\n"
            + "\n".join(
                f"• {item}"
                for item in memories
            )
        )


    # =====================================================
    # CLEAR CHAT
    # =====================================================

    clear_chat_commands = [

        "clear chat",
        "clear conversation",
        "chat clear karo",
        "conversation clear karo",
        "chat delete karo",
        "chat history clear karo",
        "history clear karo"

    ]

    if lower in clear_chat_commands:

        clear_chat_history()

        return (
            "Chat history clear kar di."
        )


    # =====================================================
    # FORGET EVERYTHING
    # =====================================================

    forget_all_commands = [

        "forget everything",
        "forget all",
        "forget all memories",
        "sab kuch bhool jao",
        "meri sari memory bhool jao",
        "sab memory bhool jao",
        "sari memory clear karo"

    ]

    if lower in forget_all_commands:

        clear_memory()

        return (
            "Theek hai, sari permanent "
            "memory clear kar di."
        )


    # =====================================================
    # REMEMBER
    # =====================================================

    remember_patterns = [

        r"^remember that (.+)$",
        r"^remember (.+)$",
        r"^please remember (.+)$",
        r"^yaad rakhna (.+)$",
        r"^yaad rakho (.+)$",
        r"^ye yaad rakhna (.+)$",
        r"^yeh yaad rakhna (.+)$",
        r"^ye baat yaad rakhna (.+)$"

    ]

    for pattern in remember_patterns:

        match = re.match(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            memory = match.group(1).strip()

            if contains_secret(memory):

                return (
                    "Security ki wajah se main "
                    "password, OTP, card details "
                    "ya API keys memory mein save "
                    "nahi karta."
                )

            added = add_memory(
                memory
            )

            if added:

                return (
                    "Theek hai, ye baat "
                    "main yaad rakhunga."
                )

            return (
                "Ye baat pehle se memory mein hai."
            )


    # =====================================================
    # FORGET
    # =====================================================

    forget_patterns = [

        r"^forget that (.+)$",
        r"^forget (.+)$",
        r"^please forget (.+)$",
        r"^bhool jao (.+)$",
        r"^ye bhool jao (.+)$",
        r"^yeh bhool jao (.+)$"

    ]

    for pattern in forget_patterns:

        match = re.match(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            memory = match.group(1).strip()

            removed = forget_memory(
                memory
            )

            if removed:

                return (
                    "Theek hai, ye baat "
                    "memory se hata di."
                )

            return (
                "Ye exact baat memory mein nahi mili."
            )


    return None


# =========================================================
# AUTOMATIC MEMORY
# =========================================================

def detect_automatic_memory(user_input):

    text = user_input.strip()

    if contains_secret(text):
        return None


    patterns = [

        (
            r"^my name is (.+)$",
            lambda m:
                f"my name is {m.group(1).strip()}"
        ),

        (
            r"^mera naam (.+) hai$",
            lambda m:
                f"mera naam {m.group(1).strip()} hai"
        ),

        (
            r"^my favorite (.+?) is (.+)$",
            lambda m:
                f"my favorite {m.group(1).strip()} "
                f"is {m.group(2).strip()}"
        ),

        (
            r"^meri favorite (.+?) (.+) hai$",
            lambda m:
                f"meri favorite "
                f"{m.group(1).strip()} "
                f"{m.group(2).strip()} hai"
        ),

        (
            r"^i like (.+)$",
            lambda m:
                f"i like {m.group(1).strip()}"
        ),

        (
            r"^mujhe (.+) pasand hai$",
            lambda m:
                f"mujhe {m.group(1).strip()} "
                f"pasand hai"
        ),

        (
            r"^i love (.+)$",
            lambda m:
                f"i love {m.group(1).strip()}"
        ),

        (
            r"^mujhe (.+) acha lagta hai$",
            lambda m:
                f"mujhe {m.group(1).strip()} "
                f"acha lagta hai"
        ),

        (
            r"^my goal is (.+)$",
            lambda m:
                f"my goal is "
                f"{m.group(1).strip()}"
        ),

        (
            r"^mera goal (.+)$",
            lambda m:
                f"mera goal "
                f"{m.group(1).strip()}"
        ),

        (
            r"^i want to (.+)$",
            lambda m:
                f"i want to {m.group(1).strip()}"
        ),

        (
            r"^main (.+) banna chahta hoon$",
            lambda m:
                f"main {m.group(1).strip()} "
                f"banna chahta hoon"
        ),

        (
            r"^i live in (.+)$",
            lambda m:
                f"i live in "
                f"{m.group(1).strip()}"
        ),

        (
            r"^main (.+) mein rehta hoon$",
            lambda m:
                f"main {m.group(1).strip()} "
                f"mein rehta hoon"
        ),

        (
            r"^my hobby is (.+)$",
            lambda m:
                f"my hobby is "
                f"{m.group(1).strip()}"
        ),

        (
            r"^meri hobby (.+) hai$",
            lambda m:
                f"meri hobby "
                f"{m.group(1).strip()} hai"
        )

    ]


    for pattern, formatter in patterns:

        match = re.match(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            memory = formatter(
                match
            ).strip()

            return memory


    return None


# =========================================================
# CLEAN AI RESPONSE
# =========================================================

def clean_short_answer(text):

    if not text:

        return (
            "Mujhe iska jawab nahi mila."
        )


    # Remove Qwen thinking blocks
    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    text = re.sub(
        r"<thinking>.*?</thinking>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )


    # Remove common reasoning prefixes
    bad_prefixes = [

        "thinking:",
        "analysis:",
        "reasoning:",
        "let me think",
        "i need to think",
        "i should answer",
        "the user is asking"

    ]


    lines = text.splitlines()

    cleaned = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        lower = line.lower()

        if any(
            lower.startswith(prefix)
            for prefix in bad_prefixes
        ):
            continue

        if line.startswith("```"):
            continue

        cleaned.append(line)


    text = " ".join(
        cleaned
    ).strip()


    # Remove markdown emphasis
    text = re.sub(
        r"\*\*(.*?)\*\*",
        r"\1",
        text
    )

    text = re.sub(
        r"\*(.*?)\*",
        r"\1",
        text
    )


    # Remove accidental Cyrus prefix
    text = re.sub(
        r"^Cyrus:\s*",
        "",
        text,
        flags=re.IGNORECASE
    )


    # Remove repeated whitespace
    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()


    # Keep answer reasonably short
    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    if len(sentences) > 3:

        text = " ".join(
            sentences[:3]
        )


    return (
        text.strip()
        or
        "Mujhe iska jawab nahi mila."
    )


# =========================================================
# FOLLOW-UP DETECTION
# =========================================================

def is_short_followup(user_input):

    text = normalize_text(
        user_input
    )

    followups = [

        "why",
        "how",
        "what",
        "when",
        "where",
        "who",
        "then",
        "really",
        "how so",
        "and why",
        "and how",
        "why is that",
        "how come",
        "what about that",
        "what about it",
        "why that",
        "then what",
        "then why",
        "then how",
        "kyun",
        "kyun bhai",
        "kaise",
        "phir",
        "phir kya",
        "matlab",
        "acha phir",
        "acha phir kya"

    ]

    if text in followups:
        return True

    return contains_reference_word(
        user_input
    )


# =========================================================
# OLLAMA HEALTH
# =========================================================

def get_ollama_version():

    try:

        response = requests.get(
            "http://localhost:11434/api/version",
            timeout=5
        )

        if response.ok:

            data = response.json()

            return data.get(
                "version",
                "unknown"
            )

    except Exception:
        pass

    return "unknown"


# =========================================================
# PYTHON LATEST
# =========================================================

def python_latest():

    try:

        response = requests.get(

            "https://www.python.org/downloads/",

            timeout=10,

            headers={
                "User-Agent": "Mozilla/5.0"
            }

        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )


        # First try the page's obvious download text
        page_text = soup.get_text(
            " ",
            strip=True
        )

        versions = re.findall(
            r"Python\s+(\d+\.\d+\.\d+)",
            page_text
        )

        if versions:

            return (
                "Python ki latest stable "
                "version "
                + versions[0]
            )


    except Exception:
        pass


    return (
        "Python ki latest version "
        "check nahi ho saki."
    )


# =========================================================
# DATE / TIME
# =========================================================

def get_current_time():

    now = datetime.now()

    return (
        "Abhi time "
        + now.strftime("%I:%M %p")
        + " hai."
    )


def get_current_date():

    now = datetime.now()

    return (
        "Aaj "
        + now.strftime("%d %B %Y")
        + " hai."
    )


# =========================================================
# SIMPLE CALCULATOR
# =========================================================

ALLOWED_OPERATORS = {

    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos

}


def safe_calculate(expression):

    expression = expression.strip()

    if len(expression) > 100:
        return None

    try:

        tree = ast.parse(
            expression,
            mode="eval"
        )

        def evaluate(node):

            if isinstance(
                node,
                ast.Constant
            ):

                if isinstance(
                    node.value,
                    (int, float)
                ):
                    return node.value

                raise ValueError

            if isinstance(
                node,
                ast.BinOp
            ):

                left = evaluate(
                    node.left
                )

                right = evaluate(
                    node.right
                )

                operation = (
                    ALLOWED_OPERATORS
                    .get(type(node.op))
                )

                if operation is None:
                    raise ValueError

                return operation(
                    left,
                    right
                )

            if isinstance(
                node,
                ast.UnaryOp
            ):

                value = evaluate(
                    node.operand
                )

                operation = (
                    ALLOWED_OPERATORS
                    .get(type(node.op))
                )

                if operation is None:
                    raise ValueError

                return operation(
                    value
                )

            raise ValueError

        result = evaluate(
            tree.body
        )

        return result

    except Exception:

        return None


def handle_calculation(user_input):

    text = user_input.strip()

    patterns = [

        r"^calculate (.+)$",
        r"^calc (.+)$",
        r"^solve (.+)$",
        r"^what is ([-+*/(). 0-9]+)$",
        r"^kitna hai ([-+*/(). 0-9]+)$"

    ]

    for pattern in patterns:

        match = re.match(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            expression = (
                match.group(1)
                .strip()
            )

            result = safe_calculate(
                expression
            )

            if result is None:
                return (
                    "Main is calculation ko "
                    "safely calculate nahi kar saka."
                )

            return (
                f"Answer: {result}"
            )

    return None


# =========================================================
# BING SEARCH
# =========================================================

def bing_search(query):

    try:

        url = (
            "https://www.bing.com/search?q="
            + requests.utils.quote(
                query
            )
        )

        response = requests.get(

            url,

            timeout=15,

            headers={
                "User-Agent":
                    "Mozilla/5.0"
            }

        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        results = []


        for item in soup.select(
            "li.b_algo"
        )[:5]:

            title_tag = item.select_one(
                "h2"
            )

            link_tag = item.select_one(
                "h2 a"
            )

            description_tag = (
                item.select_one(
                    ".b_caption p"
                )
            )


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

            description = ""

            if description_tag:

                description = (
                    description_tag.get_text(
                        " ",
                        strip=True
                    )
                )


            results.append({

                "title": title,

                "link": link,

                "description": description

            })


        return results


    except Exception:

        return []


# =========================================================
# WEB DETECTION
# =========================================================

WEB_PHRASES = [

    "latest",
    "today",
    "current",
    "news",
    "weather",
    "price",
    "prices",
    "version",
    "update",
    "updates",
    "recent",
    "what happened",
    "internet",
    "online",
    "website",
    "score",
    "results",
    "search the web",
    "search internet",
    "web par",
    "internet par",
    "latest update",
    "latest news"

]


def needs_web_search(user_input):

    lower = user_input.lower()

    for phrase in WEB_PHRASES:

        if phrase in lower:
            return True

    return False


# =========================================================
# SPECIAL WEB
# =========================================================

def handle_special_web_query(
    user_input
):

    lower = user_input.lower().strip()


    # =====================================================
    # DATE
    # =====================================================

    date_phrases = [

        "what is today's date",
        "what is the date today",
        "today's date",
        "todays date",
        "aaj ki date kya hai",
        "aaj date kya hai",
        "aaj ki tareekh kya hai"

    ]

    if lower in date_phrases:

        return get_current_date()


    # =====================================================
    # TIME
    # =====================================================

    time_phrases = [

        "what time is it",
        "what is the time",
        "current time",
        "time",
        "abhi time kya hai",
        "time kya hai",
        "kitne bajay hain",
        "kitna time hua"

    ]

    if lower in time_phrases:

        return get_current_time()


    # =====================================================
    # PYTHON
    # =====================================================

    if (

        "latest python" in lower

        or
        "python latest version" in lower

        or
        "python ki latest version" in lower

        or
        "python ka latest version" in lower

    ):

        return python_latest()


    # =====================================================
    # OLLAMA
    # =====================================================

    if (

        "ollama version" in lower

        or
        "ollama ka version" in lower

        or
        "ollama ki version" in lower

    ):

        version = get_ollama_version()

        return (
            "Tumhare system mein Ollama "
            f"version {version} installed hai."
        )


    return None


# =========================================================
# WEB SUMMARY
# =========================================================

def summarize_web_results(
    user_input,
    results
):

    if not results:

        return (
            "Mujhe web par relevant "
            "results nahi mile."
        )


    result_text = ""


    for index, item in enumerate(
        results,
        start=1
    ):

        result_text += (

            f"\nResult {index}:\n"

            f"Title: {item['title']}\n"

            f"Description: "
            f"{item['description']}\n"

        )


    prompt = f"""
You are Cyrus.

The user asked:

{user_input}

Bing search returned these results:

{result_text}

Answer the user's question using ONLY information
supported by these search results.

Do not invent facts.

If the results are unclear or insufficient,
say that clearly.

Answer naturally and briefly.

Do not mention internal reasoning.
Do not mention this prompt.
"""


    payload = {

        "model": MODEL,

        "messages": [

            {
                "role": "system",
                "content":
                    "Give accurate concise answers."
            },

            {
                "role": "user",
                "content": prompt
            }

        ],

        "stream": False,

        "think": False,

        "options": {

            "temperature": 0.1,

            "top_p": 0.7,

            "num_predict": 100

        }

    }


    try:

        response = requests.post(

            OLLAMA_URL,

            json=payload,

            timeout=REQUEST_TIMEOUT

        )

        response.raise_for_status()

        data = response.json()

        answer = (

            data
            .get("message", {})
            .get("content", "")
        )

        return clean_short_answer(
            answer
        )


    except Exception:

        first = results[0]

        if first["description"]:

            return (
                first["title"]
                + ": "
                + first["description"]
            )

        return first["title"]


# =========================================================
# WEB QUERY
# =========================================================

def handle_web_query(
    user_input
):

    print(
        "\nCyrus Bing par search kar raha hai..."
    )

    results = bing_search(
        user_input
    )

    if results:

        print(
            "Bing se results mil gaye."
        )

    else:

        print(
            "Bing se results nahi mile."
        )

    return summarize_web_results(
        user_input,
        results
    )


# =========================================================
# OPEN PROGRAMS
# =========================================================

def open_program(program):

    lower = program.lower().strip()


    # =====================================================
    # CALCULATOR
    # =====================================================

    if lower in [
        "calculator",
        "calc"
    ]:

        try:

            subprocess.Popen(
                "calc.exe"
            )

            return (
                "Calculator open kar diya."
            )

        except Exception:

            return (
                "Calculator open nahi ho saka."
            )


    # =====================================================
    # NOTEPAD
    # =====================================================

    if lower in [
        "notepad",
        "notes"
    ]:

        try:

            subprocess.Popen(
                "notepad.exe"
            )

            return (
                "Notepad open kar diya."
            )

        except Exception:

            return (
                "Notepad open nahi ho saka."
            )


    # =====================================================
    # CHROME
    # =====================================================

    if lower in [
        "chrome",
        "google chrome"
    ]:

        chrome_paths = [

            r"C:\Program Files\Google\Chrome\Application\chrome.exe",

            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

        ]


        for path in chrome_paths:

            if os.path.exists(path):

                try:

                    subprocess.Popen(
                        [path]
                    )

                    return (
                        "Chrome open kar diya."
                    )

                except Exception:
                    pass


        webbrowser.open(
            "https://www.google.com"
        )

        return (
            "Google open kar diya."
        )


    return None


# =========================================================
# OPEN FOLDERS
# =========================================================

def open_folder(folder):

    lower = folder.lower().strip()


    # =====================================================
    # DOWNLOADS
    # =====================================================

    if lower in [
        "downloads",
        "download folder"
    ]:

        path = os.path.join(

            os.path.expanduser("~"),

            "Downloads"

        )

        if os.path.exists(path):

            try:

                os.startfile(path)

                return (
                    "Downloads folder "
                    "open kar diya."
                )

            except Exception:
                pass


        return (
            "Downloads folder nahi mila."
        )


    # =====================================================
    # DESKTOP
    # =====================================================

    if lower in [
        "desktop",
        "desktop folder"
    ]:

        path = os.path.join(

            os.path.expanduser("~"),

            "Desktop"

        )

        if os.path.exists(path):

            try:

                os.startfile(path)

                return (
                    "Desktop open kar diya."
                )

            except Exception:
                pass


        return (
            "Desktop folder nahi mila."
        )


    # =====================================================
    # PERSONALBOT
    # =====================================================

    if lower in [
        "personalbot",
        "personal bot",
        "cyrus folder",
        "cyrus project"
    ]:

        possible_paths = [

            r"C:\Users\Zartash\OneDrive\Desktop\PersonalBot",

            os.path.join(
                os.path.expanduser("~"),
                "OneDrive",
                "Desktop",
                "PersonalBot"
            )

        ]


        for path in possible_paths:

            if os.path.exists(path):

                try:

                    os.startfile(path)

                    return (
                        "PersonalBot folder "
                        "open kar diya."
                    )

                except Exception:
                    pass


        return (
            "PersonalBot folder nahi mila."
        )


    return None


# =========================================================
# GOOGLE SEARCH
# =========================================================

def google_search(query):

    query = query.strip()

    url = (

        "https://www.google.com/search?q="

        + requests.utils.quote(query)

    )

    try:

        webbrowser.open(url)

        return (
            f"Google par '{query}' "
            "search kar diya."
        )

    except Exception:

        return (
            "Google search open nahi ho saki."
        )


# =========================================================
# WEBSITE
# =========================================================

def open_website(website):

    website = website.strip()

    if not website:
        return None

    if not website.startswith(
        "http://"
    ) and not website.startswith(
        "https://"
    ):

        website = (
            "https://"
            + website
        )

    try:

        webbrowser.open(
            website
        )

        return (
            "Website open kar di."
        )

    except Exception:

        return (
            "Website open nahi ho saki."
        )


# =========================================================
# PC COMMANDS
# =========================================================

def handle_pc_command(
    user_input
):

    text = user_input.strip()


    # =====================================================
    # OPEN
    # =====================================================

    match = re.match(

        r"^open (.+)$",

        text,

        re.IGNORECASE

    )

    if match:

        target = (
            match.group(1)
            .strip()
        )


        result = open_program(
            target
        )

        if result:
            return result


        result = open_folder(
            target
        )

        if result:
            return result


    # =====================================================
    # GOOGLE SEARCH
    # =====================================================

    match = re.match(

        r"^(search google for|google search) (.+)$",

        text,

        re.IGNORECASE

    )

    if match:

        query = (
            match.group(2)
            .strip()
        )

        return google_search(
            query
        )


    # =====================================================
    # WEBSITE
    # =====================================================

    match = re.match(

        r"^open website (.+)$",

        text,

        re.IGNORECASE

    )

    if match:

        website = (
            match.group(1)
            .strip()
        )

        return open_website(
            website
        )


    # =====================================================
    # OPEN URL DIRECTLY
    # =====================================================

    if (
        text.lower().startswith(
            "https://"
        )
        or
        text.lower().startswith(
            "http://"
        )
    ):

        return open_website(
            text
        )


    return None


# =========================================================
# NORMAL AI
# =========================================================

def ask_cyrus(
    user_input
):

    memory_text = get_memory_text()

    history = load_chat_history()

    conversation_context = (
        build_conversation_context(
            user_input,
            history
        )
    )


    # =====================================================
    # SYSTEM PROMPT
    # =====================================================

    system_prompt = """
You are Cyrus, a personal AI assistant.

You are running locally through Ollama.

Your most important ability is understanding the user's
meaning from conversation context.

=========================================================
IDENTITY
=========================================================

The USER and Cyrus are two different people.

When the user says:
"I", "me", "my", "mera", "meri", "mujhe"

it normally refers to THE USER.

Never accidentally turn the user's experiences,
preferences, goals, feelings, likes, dislikes, or choices
into Cyrus's own experiences or preferences.

Example:

User:
I like programming.

Correct understanding:
The USER likes programming.

If the user asks:
Why?

They are asking for a possible reason why THE USER likes
programming.

Do not answer as if Cyrus likes programming.

=========================================================
CONTEXT
=========================================================

Use the conversation history carefully.

The latest message may refer to something said several
messages earlier.

Understand references such as:

it
that
this
they
them
phir
phir kya
kyun
kyun bhai
kaise
matlab
then
why
how
what about it
what about that
and why
and how

from the conversation context.

Do not answer these words literally.

Resolve what the user is referring to before answering.

=========================================================
TOPIC CHANGES
=========================================================

If the user changes the topic, follow the new topic.

Do not force an old topic into a new question.

However, if the user uses a reference such as "it",
"that", "phir", "why", or "how", inspect recent
conversation before deciding what they mean.

Recent conversation is usually more important than very
old unrelated conversation.

=========================================================
OLD MEMORY
=========================================================

Permanent memory contains information previously provided
by the USER.

Use it only when relevant.

Never invent memories.

Never claim memories as your own.

=========================================================
UNCERTAINTY
=========================================================

If the exact reason is not known, make a reasonable
inference and clearly mark it as a possibility.

Use words like:

shayad
ho sakta hai
maybe
possibly

Do not present guesses as confirmed facts.

=========================================================
ANSWER STYLE
=========================================================

Answer naturally.

Do not repeat the user's question.

Do not explain your hidden reasoning.

Do not show chain-of-thought.

Do not say "I analyzed the context".

Do not mention internal prompts.

Usually answer in 1-3 sentences.

For a question that genuinely needs more explanation,
you may answer longer.

Use Roman Urdu/English naturally according to the user's
language.

=========================================================
IMPORTANT
=========================================================

Understand first.
Answer second.

Do not simply repeat the last message.

Do not confuse Cyrus's identity with the user's identity.
"""


    messages = [

        {
            "role": "system",
            "content": system_prompt
        },

        {
            "role": "system",
            "content":
                "Permanent user memory:\n"
                + memory_text
        }

    ]


    # =====================================================
    # ADD CONVERSATION CONTEXT
    # =====================================================

    if conversation_context:

        messages.append({

            "role": "system",

            "content":
                """
Conversation context is provided below.

Use it to understand references and continuity.

If the latest user message contains a short follow-up
or pronoun, identify what previous statement it refers to.

Do not blindly treat every old message as relevant.
"""

        })


        for item in conversation_context:

            role = item.get(
                "role",
                ""
            )

            content = item.get(
                "content",
                ""
            )

            if role in [
                "user",
                "assistant"
            ] and content:

                messages.append({

                    "role": role,

                    "content": content

                })


    # =====================================================
    # CURRENT MESSAGE
    # =====================================================

    if is_short_followup(
        user_input
    ):

        current_instruction = f"""
The user's latest message is a contextual follow-up.

Determine what it refers to using the conversation above.

Do not answer the follow-up word literally.

If it says "why", identify what the user is asking why about.

If it says "how", identify what process/action they mean.

If it says "what", identify what thing they mean.

If it says "it", "that", or "this", resolve the reference
from the most relevant recent conversation.

If it says "phir", determine what the natural next question
or next step is based on the conversation.

If the user is asking about their own preference,
experience, feeling, goal, or choice, answer about THE USER.

If exact information is unavailable, give a reasonable
possibility and label it as such.

Latest user message:

{user_input}

Answer naturally and briefly.

 /no_think
"""

    else:

        current_instruction = f"""
Latest user message:

{user_input}

Use the conversation context and permanent memory when
relevant.

Understand the user's intended meaning before answering.

If the user refers to an older relevant conversation,
use it.

Do not unnecessarily repeat information.

Do not claim the user's preferences or experiences as
your own.

Answer naturally.

 /no_think
"""


    messages.append({

        "role": "user",

        "content": current_instruction

    })


    # =====================================================
    # OLLAMA PAYLOAD
    # =====================================================

    payload = {

        "model": MODEL,

        "messages": messages,

        "stream": True,

        "think": False,

        "keep_alive": "15m",

        "options": {

            "temperature": 0.15,

            "top_p": 0.75,

            "repeat_penalty": 1.15,

            "num_predict": 140

        }

    }


    full_response = ""


    try:

        with requests.post(

            OLLAMA_URL,

            json=payload,

            stream=True,

            timeout=REQUEST_TIMEOUT

        ) as response:

            response.raise_for_status()


            for line in response.iter_lines():

                if not line:
                    continue


                try:

                    data = json.loads(
                        line.decode(
                            "utf-8"
                        )
                    )

                except Exception:

                    continue


                message = data.get(
                    "message",
                    {}
                )


                chunk = message.get(
                    "content",
                    ""
                )


                if chunk:

                    full_response += chunk


                if data.get(
                    "done",
                    False
                ):

                    break


        return clean_short_answer(
            full_response
        )


    except requests.exceptions.Timeout:

        return (
            "Ollama response mein "
            "bohat time lag raha hai."
        )


    except requests.exceptions.ConnectionError:

        return (
            "Ollama se connection nahi ho raha. "
            "Check karo ke Ollama chal raha hai."
        )


    except requests.exceptions.HTTPError as e:

        return (
            "Ollama HTTP error: "
            + str(e)
        )


    except Exception as e:

        return (
            "Error: "
            + str(e)
        )


# =========================================================
# PRINT + SAVE ANSWER
# =========================================================

def finish_response(
    user_input,
    answer
):

    add_chat_message(
        "user",
        user_input
    )

    add_chat_message(
        "assistant",
        answer
    )

    print(
        "\nCyrus:"
    )

    print(
        answer
    )

    speak(
        answer
    )


# =========================================================
# STARTUP CHECK
# =========================================================

def startup_info():

    print(
        "Cyrus AI Assistant started."
    )

    print(
        f"Model: {MODEL}"
    )

    version = get_ollama_version()

    if version != "unknown":

        print(
            f"Ollama: {version}"
        )

    else:

        print(
            "Ollama: connection check failed"
        )

    if VOICE_ENABLED:

        print(
            "Voice: ON"
        )

    else:

        print(
            "Voice: OFF"
        )

    print(
        "Memory: ON"
    )

    print(
        "Chat history: ON"
    )

    print(
        "Type 'exit' to close."
    )


# =========================================================
# MAIN
# =========================================================

def main():

    startup_info()


    while True:

        try:

            user_input = input(
                "\nYou: "
            ).strip()


        except (
            KeyboardInterrupt,
            EOFError
        ):

            print(
                "\nCyrus band ho gaya."
            )

            break


        if not user_input:
            continue


        lower = user_input.lower().strip()


        # =================================================
        # EXIT
        # =================================================

        if lower in [

            "exit",
            "quit",
            "bye",
            "band ho jao",
            "close",
            "shutdown cyrus"

        ]:

            answer = (
                "Allah Hafiz!"
            )

            print(
                "\nCyrus:"
            )

            print(
                answer
            )

            speak(
                answer
            )

            break


        # =================================================
        # MEMORY COMMAND
        # =================================================

        memory_result = (
            handle_memory_command(
                user_input
            )
        )

        if memory_result:

            print(
                "\nCyrus:"
            )

            print(
                memory_result
            )

            speak(
                memory_result
            )

            continue


        # =================================================
        # AUTOMATIC MEMORY
        # =================================================

        automatic_memory = (
            detect_automatic_memory(
                user_input
            )
        )

        if automatic_memory:

            added = add_memory(
                automatic_memory
            )

            add_chat_message(
                "user",
                user_input
            )

            if added:

                answer = (
                    "Theek hai, ye baat "
                    "main yaad rakhunga."
                )

            else:

                answer = (
                    "Ye baat pehle se "
                    "memory mein hai."
                )

            add_chat_message(
                "assistant",
                answer
            )

            print(
                "\nCyrus:"
            )

            print(
                answer
            )

            speak(
                answer
            )

            continue


        # =================================================
        # CALCULATOR
        # =================================================

        calculation_result = (
            handle_calculation(
                user_input
            )
        )

        if calculation_result:

            finish_response(
                user_input,
                calculation_result
            )

            continue


        # =================================================
        # PC COMMAND
        # =================================================

        pc_result = (
            handle_pc_command(
                user_input
            )
        )

        if pc_result:

            finish_response(
                user_input,
                pc_result
            )

            continue


        # =================================================
        # SPECIAL LOCAL/WEB
        # =================================================

        special_result = (
            handle_special_web_query(
                user_input
            )
        )

        if special_result:

            finish_response(
                user_input,
                special_result
            )

            continue


        # =================================================
        # GENERAL WEB
        # =================================================

        if needs_web_search(
            user_input
        ):

            answer = (
                handle_web_query(
                    user_input
                )
            )

            finish_response(
                user_input,
                answer
            )

            continue


        # =================================================
        # NORMAL AI
        # =================================================

        answer = ask_cyrus(
            user_input
        )

        finish_response(
            user_input,
            answer
        )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()