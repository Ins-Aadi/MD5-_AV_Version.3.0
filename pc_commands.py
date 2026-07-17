"""
pc_commands.py - Voice-controlled PC actions: open apps, create/delete folders.

Recognized phrases (case-insensitive):
    "open <app name>"                       e.g. "open chrome", "open notepad"
    "close <app name>"                      e.g. "close chrome", "close notepad"
    "create folder <name>" / "make folder <name>"
    "delete folder <name>" / "remove folder <name>"
    "shutdown" / "shut down" / "turn off the pc" / "power off"
    "restart" / "reboot"
    "sleep" / "go to sleep"
    "cancel shutdown" / "cancel restart"    aborts a pending shutdown/restart

SAFETY NOTES
    - Folder create/delete only operate inside WORKSPACE_DIR (a dedicated
      folder on your Desktop) — a misheard folder name can't touch anything
      outside it.
    - Deletes go to the Recycle Bin via send2trash (recoverable), not a
      permanent delete, and require a spoken "yes" to confirm first.
    - Shutdown/restart require a spoken "yes" to confirm, then wait
      POWER_ACTION_DELAY seconds before actually happening — say
      "cancel shutdown" in that window to stop it. Sleep is instant and
      harmless (nothing closes, just wakes back up), so it skips confirmation.
    - AppOpener (the "open"/"close" commands) is Windows-only. Shutdown,
      restart, and sleep also use Windows-specific commands.
"""

import os
import re
import subprocess
import ctypes
import statss
from AppOpener import open as app_open, close as app_close
from send2trash import send2trash

WORKSPACE_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "VoiceAssistant")
os.makedirs(WORKSPACE_DIR, exist_ok=True)
print(f"[pc_commands] Folder commands operate inside: {WORKSPACE_DIR}")
OPEN_RE = re.compile(r"^open (.+)$")
CLOSE_RE = re.compile(r"^close (.+)$")
CREATE_FOLDER_RE = re.compile(r"^(?:create|make)(?: a)? folder(?: named| called)? (.+)$")
DELETE_FOLDER_RE = re.compile(r"^(?:delete|remove)(?: the)? folder(?: named| called)? (.+)$")
TRAILING_LOCATION_RE = re.compile(r"\s+on (?:my|the) desktop$")
SYSTEM = re.compile(r"^system (.+)$")
DEVICE = r"(?:the|my) ?(?:pc|laptop|computer)?"
SHUTDOWN_RE = re.compile(rf"^(?:shut ?down|turn off|power off)(?: {DEVICE})?$")
RESTART_RE = re.compile(rf"^(?:restart|reboot)(?: {DEVICE})?$")
SLEEP_RE = re.compile(rf"^(?:go to sleep|sleep)(?: {DEVICE})?$")
CANCEL_POWER_RE = re.compile(r"^cancel (?:shutdown|restart)$")

POWER_ACTION_DELAY = 15  # seconds of warning before shutdown/restart actually happens


def _clean_name(raw):
    name = raw.strip().strip('"').strip("'")
    name = TRAILING_LOCATION_RE.sub("", name)
    return name.strip()


def _safe_path(raw_name):
    """Resolve a folder name to a path inside WORKSPACE_DIR. Returns None if
    the resolved path would escape WORKSPACE_DIR (blocks things like
    '../../Windows' from a misheard command)."""
    name = _clean_name(raw_name)
    if not name:
        return None
    target = os.path.abspath(os.path.join(WORKSPACE_DIR, name))
    root = os.path.abspath(WORKSPACE_DIR) + os.sep
    if not target.startswith(root):
        return None
    return target


def _handle_power_action(kind, speak, confirm):
    speak(f"Are you sure you want to {kind} the PC? Say yes to confirm.")
    if not confirm():
        speak("Okay, cancelled.")
        return

    flag = "/s" if kind == "shutdown" else "/r"
    subprocess.run(["shutdown", flag, "/t", str(POWER_ACTION_DELAY)])
    speak(f"{kind.capitalize()} in {POWER_ACTION_DELAY} seconds. Say 'cancel shutdown' to stop it.")

def try_handle(text, speak, confirm):
    """
    If `text` matches a known PC-control command, execute it and speak the
    result, then return True. Returns False if `text` isn't a recognized
    command, so the caller can fall through to normal chat.

    speak(text)   -> speaks/prints a response
    confirm()     -> asks a yes/no question by voice, returns bool
    """
    t = text.strip().lower()

    m = OPEN_RE.match(t)
    if m:
        app_name = m.group(1).strip()
        try:
            app_open(app_name, match_closest=True, throw_error=True)
            speak(f"Opening {app_name}.")
        except Exception:
            speak(f"I couldn't find an app called {app_name}.")
        return True

    m = CLOSE_RE.match(t)
    if m:
        app_name = m.group(1).strip()
        try:
            app_close(app_name, match_closest=True, throw_error=True)
            speak(f"Closing {app_name}.")
        except Exception:
            speak(f"I couldn't close {app_name}. It might not be running.")
        return True

    m = CREATE_FOLDER_RE.match(t)
    if m:
        path = _safe_path(m.group(1))
        if path is None:
            speak("I can only create folders inside your voice assistant workspace.")
        elif os.path.isdir(path):
            print(f"Already exists: {path}")
            speak(f"A folder called {os.path.basename(path)} already exists.")
        else:
            os.makedirs(path)
            print(f"Created: {path}")
            speak(f"Created folder {os.path.basename(path)}.")
        return True

    m = DELETE_FOLDER_RE.match(t)
    if m:
        path = _safe_path(m.group(1))
        if path is None or not os.path.isdir(path):
            speak("I can't find that folder in your voice assistant workspace.")
            return True
        name = os.path.basename(path)
        speak(f"Are you sure you want to delete the folder {name}? Say yes to confirm.")
        if confirm():
            send2trash(path)
            print(f"🗑️  Sent to Recycle Bin: {path}")
            speak(f"Deleted {name}. You can still restore it from the Recycle Bin.")
        else:
            speak("Okay, I left it alone.")
        return True

    if CANCEL_POWER_RE.match(t):
        subprocess.run(["shutdown", "/a"])
        speak("Cancelled.")
        return True

    if SHUTDOWN_RE.match(t):
        _handle_power_action("shutdown", speak, confirm)
        return True

    if RESTART_RE.match(t):
        _handle_power_action("restart", speak, confirm)
        return True

    if SLEEP_RE.match(t):
        speak("Going to sleep now.")
        ctypes.windll.powrprof.SetSuspendState(False, True, False)
        return True
    if SYSTEM.match(t):
        status = statss.get_system_status()
        print(status)
    return False