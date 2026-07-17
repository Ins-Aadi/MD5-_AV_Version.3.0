import asyncio
import os
import re
import sys
import tempfile
import speech_recognition as sr
import edge_tts
from playsound import playsound
from google import genai
from google.genai import types

from pc_commands import try_handle
import code_commands

MODEL = "gemini-3.1-flash-lite"
SYSTEM_PROMPT = (
    "You are a helpful, friendly voice assistant. Keep replies short and "
    "conversational (1-3 sentences) since they will be read aloud."
)

# Voice speed: "+0%" is normal, "+25%" is noticeably faster, "-25%" slower.
RATE = "+35%"
VOICE_EN = "hi-IN-SwaraNeural"
VOICE_HI = "hi-IN-SwaraNeural"
HINDI_SCRIPT_RE = re.compile(r"[\u0900-\u097F]")
CONFIRM_WORDS = ("yes", "yeah", "yep", "confirm", "sure", "haan", "ha","yess")
CODE_BLOCK_RE = re.compile(r"```(?P<lang>\w+)?\s*\n(?P<code>.*?)```", re.DOTALL)


def listen(recognizer, mic):
    """Capture one utterance from the microphone and return it as text (or None)."""
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.3)
        print("\n🎤 Listening... (speak now)")
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio)
        print(f"You said: {text}")
        return text
    except sr.UnknownValueError:
        print("Didn't catch that — try again.")
        return None
    except sr.RequestError as e:
        print(f"Speech recognition service error: {e}")
        return None

def speak(text):
    """Convert text to speech with edge-tts and play it. A new mp3 is
    generated and played each call, so there's no shared engine state
    to get stuck, and RATE controls how fast it talks."""
    print(f"Assistant: {text}")
    voice = VOICE_HI if HINDI_SCRIPT_RE.search(text) else VOICE_EN

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        temp_path = f.name

    try:
        asyncio.run(edge_tts.Communicate(text, voice, rate=RATE).save(temp_path))
        playsound(temp_path)
    except Exception as e:
        print(f"TTS playback error: {e}")
    finally:
        os.remove(temp_path)
def generate_code(client, request_text, hinted_lang=None):
    """Ask Gemini to write code for a spoken request. Returns (code, lang,
    error) - code/lang are None if error is set. This is a standalone
    generate_content call (not chat.send_message), so it doesn't get mixed
    into the conversation's chat history."""
    prompt = (
        "You are a code generator. The user asked (via voice): "
        f"\"{request_text}\"\n\n"
        "Write clean, working code that fulfills this request. "
        "Respond with ONLY a single fenced code block - no explanation, "
        "no preamble, no text outside the code block. Right after the "
        "opening triple backticks, write the programming language name "
        "(e.g. python, javascript, java, cpp, html)."
    )
    if hinted_lang:
        prompt += f"\nThe user specifically asked for {hinted_lang}."

    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        raw = response.text
    except Exception as e:
        print(f"Code generation error: {e}")
        return None, None, str(e)

    match = CODE_BLOCK_RE.search(raw)
    if not match:
        # No fenced block found - fall back to the raw text so the user
        # still gets something saved.
        return raw.strip(), hinted_lang or "text", None

    lang = (match.group("lang") or hinted_lang or "text").strip().lower()
    code = match.group("code")
    return code, lang, None

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY is not set. Set it and try again (see setup notes at top of file).")

    client = genai.Client(api_key=api_key)
    chat = client.chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )

    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    def confirm():
        reply = listen(recognizer, mic)
        return reply is not None and reply.strip().lower() in CONFIRM_WORDS

    print("Voice chatbot ready. Say 'quit', 'exit', 'bye', 'bye-bye', or 'stop' to end.")

    while True:
        user_text = listen(recognizer, mic)
        if user_text is None:
            continue

        if user_text.strip().lower() in ("quit", "exit", "stop","bye-bye","bye"):
            speak("Goodbye!")
            break

        if try_handle(user_text, speak, confirm):
            continue

        if code_commands.try_handle(
            user_text, speak, lambda t, lang: generate_code(client, t, lang)
        ):
            continue

        try:
            response = chat.send_message(user_text)
            reply = response.text
        except Exception as e:
            print(f"API error: {e}")
            continue

        speak(reply)


if __name__ == "__main__":
    main()