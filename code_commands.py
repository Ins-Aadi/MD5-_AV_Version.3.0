"""
code_commands.py - Voice-triggered code generation: "write code to ..." /
"generate a python script that ..." / "create code for ..." etc.

The actual generation call is made by the caller (Voice_chatbot.py) via a
callback, so this module never touches the Gemini client directly - it just
detects the trigger, saves the result to a file, and reports back.

Recognized phrases (case-insensitive), the important part is having one of
"write / generate / create / make" together with "code / program / script /
function" somewhere in the sentence:
    "write code to reverse a linked list"
    "generate a python script that sorts a list"
    "create code for a calculator"
    "make a javascript function that validates an email"

SAFETY NOTES
    - Generated files only ever get written inside CODE_DIR (a dedicated
      folder on your Desktop) - never anywhere else on disk.
    - Existing files are never overwritten; a numeric suffix is added
      instead (e.g. calculator_1.py).
    - This module does not execute any generated code - it only writes it
      to a file.
"""

import os
import re

CODE_DIR = os.path.join(
    os.path.expanduser("~"), "Desktop", "VoiceAssistant", "Generated"
)

TRIGGER_RE = re.compile(
    r"\b(?:write|generate|create|make)\b.*\b(?:code|program|script|function)\b",
    re.IGNORECASE,
)

LANG_HINT_RE = re.compile(
    r"\b(python|javascript|typescript|java|c\+\+|cpp|c#|csharp|html|css|"
    r"bash|shell|sql|ruby|go|rust|json|js|ts)\b",
    re.IGNORECASE,
)

TASK_RE = re.compile(r"\b(?:for|to|that|which)\s+(.+)$", re.IGNORECASE)

EXTENSION_MAP = {
    "python": "py", "py": "py",
    "javascript": "js", "js": "js",
    "typescript": "ts", "ts": "ts",
    "java": "java",
    "c++": "cpp", "cpp": "cpp",
    "c": "c",
    "c#": "cs", "csharp": "cs",
    "html": "html",
    "css": "css",
    "bash": "sh", "shell": "sh", "sh": "sh",
    "sql": "sql",
    "ruby": "rb",
    "go": "go",
    "rust": "rs",
    "json": "json",
    "text": "txt",
}


def _slugify(text, max_words=6):
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())[:max_words]
    return "_".join(words) or "generated"


def _build_filename(task_desc, lang):
    ext = EXTENSION_MAP.get((lang or "text").lower(), "txt")
    return f"{_slugify(task_desc)}.{ext}"


def _save_code(filename, code):
    os.makedirs(CODE_DIR, exist_ok=True)
    base, ext = os.path.splitext(filename)
    path = os.path.join(CODE_DIR, filename)
    counter = 1
    while os.path.exists(path):
        path = os.path.join(CODE_DIR, f"{base}_{counter}{ext}")
        counter += 1
    with open(path, "w", encoding="utf-8") as f:
        f.write(code.strip() + "\n")
    print(f"💾 Saved generated code: {path}")
    return path


def try_handle(text, speak, generate_code_fn):
    """
    If `text` looks like a code-generation request, generate the code via
    `generate_code_fn`, save it to CODE_DIR, speak the result, and return
    True. Returns False if `text` doesn't look like a code request, so the
    caller can fall through to normal chat.

    generate_code_fn(request_text, hinted_lang) -> (code, lang, error)
        code / lang are None if error is set.
    speak(text) -> speaks/prints a response
    """
    if not TRIGGER_RE.search(text):
        return False

    lang_match = LANG_HINT_RE.search(text)
    hinted_lang = lang_match.group(1).lower() if lang_match else None

    task_match = TASK_RE.search(text)
    task_desc = task_match.group(1).strip() if task_match else text.strip()

    speak("Sure, generating the code now.")
    code, lang, error = generate_code_fn(text, hinted_lang)

    if error or not code:
        speak("Sorry, I ran into a problem generating that code.")
        return True

    filename = _build_filename(task_desc, lang or hinted_lang)
    path = _save_code(filename, code)
    speak(f"Done! I saved it as {os.path.basename(path)} in your generated code folder.")
    return True
