"""
IRIS AI - Complete Automation Engine (Python Port)
All automation logic from the TypeScript IRIS-AI repository.
"""
import os, sys, json, shutil, base64, hashlib, math, random, time, platform, re
import subprocess, asyncio, webbrowser, mimetypes
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from io import BytesIO
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import pyautogui
import pyperclip
import mss
from PIL import Image
import httpx
from bs4 import BeautifulSoup
from pygments import highlight as pyg_highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

try:
    from google import genai
    from google.genai import types as genai_types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    HAS_VOLUME = True
except ImportError:
    HAS_VOLUME = False

try:
    import pygetwindow as gw
    HAS_WINMGR = True
except ImportError:
    HAS_WINMGR = False

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request as GAuthRequest
    from googleapiclient.discovery import build as gmail_build
    HAS_GMAIL = True
except ImportError:
    HAS_GMAIL = False

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.02

# ═══════════════════════════════════════════════════════════
#   CONFIG
# ═══════════════════════════════════════════════════════════
DATA_DIR = os.environ.get("IRIS_DATA_DIR", os.path.join(str(Path.home()), ".iris_ai"))
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")

router = APIRouter()


def _run(cmd, **kw):
    """Run a subprocess command and return stdout."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=kw.get("timeout", 30), **{k: v for k, v in kw.items() if k != "timeout"})
        return r.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


def _run_bytes(cmd, **kw):
    """Run a subprocess command and return raw bytes."""
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=kw.get("timeout", 30))
        return r.stdout
    except Exception:
        return b""


def _get_sys_path(name):
    home = str(Path.home())
    paths = {"desktop": "Desktop", "documents": "Documents", "downloads": "Downloads",
             "music": "Music", "pictures": "Pictures", "videos": "Videos"}
    return os.path.join(home, paths.get(name.lower(), ""))


# ═══════════════════════════════════════════════════════════
#   PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════
class AppReq(BaseModel):
    app_name: str

class FilePathReq(BaseModel):
    file_path: str

class FileWriteReq(BaseModel):
    file_name: str
    content: str

class FileOpsReq(BaseModel):
    operation: str
    source_path: str
    dest_path: Optional[str] = None

class DirReq(BaseModel):
    dir_path: str

class SearchReq(BaseModel):
    query: str
    groq_key: Optional[str] = None

class GhostSeqReq(BaseModel):
    actions: List[Dict[str, Any]]

class GhostClickReq(BaseModel):
    x: int
    y: int
    double_click: bool = False

class ScrollReq(BaseModel):
    direction: str = "down"
    amount: int = 500

class VolumeReq(BaseModel):
    level: int

class ShellReq(BaseModel):
    command: str
    cwd: Optional[str] = None

class AdbConnReq(BaseModel):
    ip: str
    port: str = "5555"

class AdbAppReq(BaseModel):
    package_name: str

class AdbTapReq(BaseModel):
    x_percent: float
    y_percent: float

class AdbSwipeReq(BaseModel):
    direction: str

class AdbActionReq(BaseModel):
    action: str

class AdbFileReq(BaseModel):
    source_path: str
    dest_path: str = "/sdcard/Download/"

class AdbHwReq(BaseModel):
    setting: str
    state: bool

class WebSearchReq(BaseModel):
    query: str

class NoteReq(BaseModel):
    title: str
    content: str

class NoteDelReq(BaseModel):
    filename: str

class GallSaveReq(BaseModel):
    title: str
    base64_data: str

class GallDelReq(BaseModel):
    filename: str

class MemMsgReq(BaseModel):
    role: str
    text: str

class MemFactReq(BaseModel):
    fact: str

class GmailReadReq(BaseModel):
    max_results: int = 5

class GmailSendReq(BaseModel):
    to: str
    subject: str
    body: str

class TelekinesisReq(BaseModel):
    commands: List[Dict[str, str]]

class AiCodeReq(BaseModel):
    prompt: str
    filename: str
    gemini_key: Optional[str] = None

class AiWebsiteReq(BaseModel):
    prompt: str
    gemini_key: Optional[str] = None

class PhantomReq(BaseModel):
    prompt: str
    gemini_key: Optional[str] = None

class ScreenPeelReq(BaseModel):
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    gemini_key: Optional[str] = None

class DragDropReq(BaseModel):
    start_x: int
    start_y: int
    end_x: int
    end_y: int

class MoveFileReq(BaseModel):
    source_path: str
    target_folder: str

class WorkflowSaveReq(BaseModel):
    name: str
    description: str = ""
    nodes: List[Any] = []
    edges: List[Any] = []

class WorkflowDelReq(BaseModel):
    name: str

class HackerReq(BaseModel):
    url: str
    mode: str = "emerald_theme"
    custom_text: Optional[str] = None

class WidgetReq(BaseModel):
    html_code: str
    width: int = 420
    height: int = 500


# ═══════════════════════════════════════════════════════════
#   1. SYSTEM INFO
# ═══════════════════════════════════════════════════════════
_cpu_last = None

@router.get("/system/stats")
def get_system_stats():
    import os as _os
    total = _os.sysconf("SC_PAGE_SIZE") * _os.sysconf("SC_PHYS_PAGES") if hasattr(_os, "sysconf") else 0
    if total == 0:
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            c_ulonglong = ctypes.c_ulonglong
            class MEMSTAT(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", c_ulonglong), ("ullAvailPhys", c_ulonglong),
                            ("ullTotalPageFile", c_ulonglong), ("ullAvailPageFile", c_ulonglong),
                            ("ullTotalVirtual", c_ulonglong), ("ullAvailVirtual", c_ulonglong),
                            ("ullAvailExtendedVirtual", c_ulonglong)]
            m = MEMSTAT()
            m.dwLength = ctypes.sizeof(m)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            total = m.ullTotalPhys
            free = m.ullAvailPhys
            mem_pct = f"{((total - free) / total * 100):.1f}" if total else "0"
            total_gb = f"{total / 1024**3:.1f} GB"
            free_gb = f"{free / 1024**3:.1f} GB"
        except Exception:
            total_gb, free_gb, mem_pct = "N/A", "N/A", "0"
    else:
        import resource
        free = _os.sysconf("SC_AVPHYS_PAGES") * _os.sysconf("SC_PAGE_SIZE")
        total_gb = f"{total / 1024**3:.1f} GB"
        free_gb = f"{free / 1024**3:.1f} GB"
        mem_pct = f"{((total - free) / total * 100):.1f}"

    cpu = _run(["powershell", "-Command",
                "Get-CimInstance Win32_Processor | Select -Expand LoadPercentage"]) if platform.system() == "Windows" else "0"
    return {"cpu": cpu, "memory": {"total": total_gb, "free": free_gb, "used_pct": mem_pct},
            "os": {"type": platform.system(), "release": platform.release()}}


@router.get("/system/installed-apps")
def get_installed_apps():
    if platform.system() != "Windows":
        return []
    out = _run(["powershell", "-Command",
                'Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Depth 1'])
    if not out or out.startswith("Error"):
        return []
    try:
        data = json.loads(out)
        arr = data if isinstance(data, list) else [data]
        return sorted([{"name": a["Name"].strip(), "id": a["AppID"].strip()}
                       for a in arr if a.get("Name") and a.get("AppID")], key=lambda x: x["name"])
    except Exception:
        return []


@router.get("/system/running-apps")
def get_running_apps():
    if platform.system() == "Windows":
        out = _run(["powershell", "-Command",
                    "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object -ExpandProperty ProcessName"])
        apps = list(set(a.strip() for a in out.split("\n") if a.strip()))
        return apps
    elif platform.system() == "Darwin":
        out = _run(["osascript", "-e",
                    'tell application "System Events" to get name of (processes where background only is false)'])
        return [s.strip() for s in out.split(", ")]
    return []


@router.get("/system/drives")
def get_drives():
    if platform.system() != "Windows":
        return []
    out = _run(["powershell", "-Command",
                "Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N='FreeGB';E={[math]::round($_.Free/1GB,2)}}, @{N='TotalGB';E={[math]::round(($_.Used+$_.Free)/1GB,2)}} | ConvertTo-Json"])
    try:
        return json.loads(out) if out and not out.startswith("Error") else []
    except Exception:
        return []


@router.get("/system/screen-size")
def get_screen_size():
    with mss.mss() as sct:
        m = sct.monitors[1]
        return {"width": m["width"], "height": m["height"]}


# ═══════════════════════════════════════════════════════════
#   2. APP LAUNCHER
# ═══════════════════════════════════════════════════════════
APP_ALIASES = {
    "vscode": "code", "code": "code", "visual studio code": "code",
    "terminal": "wt", "cmd": "start cmd", "git": "start git-bash",
    "mongo": "mongodbcompass", "mongodb": "mongodbcompass", "postman": "postman",
    "chrome": "start chrome", "google chrome": "start chrome", "edge": "start msedge",
    "brave": "start brave", "firefox": "start firefox",
    "whatsapp": "start whatsapp:", "discord": "Update.exe --processStart Discord.exe",
    "spotify": "start spotify:", "telegram": "start telegram:",
    "steam": "start steam:", "notepad": "notepad", "calculator": "calc",
    "settings": "start ms-settings:", "explorer": "explorer", "files": "explorer",
    "task manager": "taskmgr", "camera": "start microsoft.windows.camera:",
    "photos": "start microsoft.windows.photos:"
}

PROCESS_NAMES = {
    "vscode": "code.exe", "code": "code.exe", "visual studio code": "code.exe",
    "chrome": "chrome.exe", "google chrome": "chrome.exe", "edge": "msedge.exe",
    "brave": "brave.exe", "firefox": "firefox.exe", "notepad": "notepad.exe",
    "cmd": "cmd.exe", "terminal": "WindowsTerminal.exe",
    "whatsapp": "WhatsApp.exe", "discord": "Discord.exe",
    "spotify": "Spotify.exe", "telegram": "Telegram.exe",
    "steam": "steam.exe", "calculator": "CalculatorApp.exe",
    "settings": "SystemSettings.exe", "task manager": "Taskmgr.exe",
    "explorer": "explorer.exe", "files": "explorer.exe"
}

PROTECTED = {"explorer.exe", "dwm.exe", "svchost.exe", "lsass.exe", "csrss.exe",
             "wininit.exe", "winlogon.exe", "services.exe", "taskmgr.exe", "system", "registry"}


@router.post("/app/open")
def open_app(req: AppReq):
    name = req.app_name.lower().strip()
    cmd = APP_ALIASES.get(name)
    if cmd:
        r = subprocess.run(cmd, shell=True, capture_output=True)
        if r.returncode == 0:
            return {"success": True, "message": f"Opened {req.app_name}"}
    # Fallback: PowerShell search
    ps = f"Get-StartApps | Where-Object {{ $_.Name -like '*{req.app_name}*' }} | Select-Object -First 1 -ExpandProperty AppID"
    app_id = _run(["powershell", "-Command", ps])
    if app_id and not app_id.startswith("Error"):
        subprocess.run(f'start explorer "shell:AppsFolder\\{app_id}"', shell=True)
        return {"success": True, "message": f"Opened {req.app_name} via System Search"}
    return {"success": False, "error": f"Could not find '{req.app_name}' on this system."}


@router.post("/app/close")
def close_app(req: AppReq):
    name = req.app_name.lower().strip()
    proc = PROCESS_NAMES.get(name, req.app_name if req.app_name.endswith(".exe") else f"{req.app_name}.exe")
    if proc.lower() in PROTECTED:
        return {"success": False, "error": f"Cannot close '{req.app_name}' (System Critical Process)."}
    r = subprocess.run(f'taskkill /IM "{proc}" /F /T', shell=True, capture_output=True)
    if r.returncode == 0:
        return {"success": True, "message": f"Terminated {req.app_name}"}
    return {"success": False, "error": f"Could not close {req.app_name}. Is it running?"}


# ═══════════════════════════════════════════════════════════
#   3. FILE MANAGEMENT
# ═══════════════════════════════════════════════════════════
FILE_TYPES = {
    "text": {".txt",".md",".js",".ts",".jsx",".tsx",".json",".html",".css",".py",".java",".c",".cpp",".h",".csv",".env",".log",".xml",".yml",".yaml"},
    "image": {".png",".jpg",".jpeg",".gif",".bmp",".svg",".webp"},
    "video": {".mp4",".mkv",".avi",".mov",".webm"},
    "executable": {".exe",".msi",".bat",".sh",".app",".dmg"}
}

def _file_type(name, is_dir):
    if is_dir:
        return "directory"
    ext = os.path.splitext(name)[1].lower()
    for t, exts in FILE_TYPES.items():
        if ext in exts:
            return t
    return "unknown"


@router.post("/file/read")
def read_file(req: FilePathReq):
    try:
        with open(req.file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return content[:2000] + "\n...(Truncated)" if len(content) > 2000 else content
    except Exception as e:
        return f"Error reading file: {e}"


@router.post("/file/write")
def write_file(req: FileWriteReq):
    try:
        is_abs = "/" in req.file_name or "\\" in req.file_name
        target = req.file_name if is_abs else os.path.join(_get_sys_path("desktop"), req.file_name)
        with open(target, "w", encoding="utf-8") as f:
            f.write(req.content)
        return f"Success. File saved to: {target}"
    except Exception as e:
        return f"Error writing file: {e}"


@router.post("/file/open")
def file_open(req: FilePathReq):
    try:
        if platform.system() == "Windows":
            os.startfile(req.file_path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", req.file_path])
        else:
            subprocess.run(["xdg-open", req.file_path])
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/file/reveal")
def file_reveal(req: FilePathReq):
    try:
        if platform.system() == "Windows":
            subprocess.run(["explorer", "/select,", req.file_path])
        elif platform.system() == "Darwin":
            subprocess.run(["open", "-R", req.file_path])
        return {"success": True}
    except Exception:
        return {"success": False, "error": "Failed to reveal item"}


@router.post("/file/ops")
def file_ops(req: FileOpsReq):
    try:
        if req.operation == "copy":
            if not req.dest_path:
                return "Error: Destination path required for copy."
            if os.path.isdir(req.source_path):
                shutil.copytree(req.source_path, req.dest_path)
            else:
                shutil.copy2(req.source_path, req.dest_path)
            return f"Success: Copied to {req.dest_path}"
        elif req.operation == "move":
            if not req.dest_path:
                return "Error: Destination path required for move."
            shutil.move(req.source_path, req.dest_path)
            return f"Success: Moved to {req.dest_path}"
        elif req.operation == "delete":
            if os.path.isdir(req.source_path):
                shutil.rmtree(req.source_path, ignore_errors=True)
            else:
                os.remove(req.source_path)
            return f"Success: Deleted {req.source_path}"
        return f"Error: Unknown operation '{req.operation}'"
    except Exception as e:
        return f"System Error: {e}"


@router.post("/directory/read")
def read_directory(req: DirReq):
    try:
        raw = req.dir_path.strip()
        target = raw
        if platform.system() == "Windows" and re.match(r'^[a-zA-Z]:?$', raw):
            target = raw[0].upper() + ":\\"
        elif raw.lower() in ("desktop","documents","downloads","music","pictures","videos"):
            target = _get_sys_path(raw.lower())
        elif raw.lower() in ("home", "~"):
            target = str(Path.home())
        elif not os.path.isabs(target):
            target = os.path.join(str(Path.home()), raw)

        if not os.path.isdir(target):
            if os.path.isfile(target):
                return f"Error: '{target}' is a FILE. Use read_file to read it."
            return f"Error: Directory not found at '{target}'."

        items = []
        for entry in os.scandir(target):
            if entry.name.startswith("."):
                continue
            try:
                st = entry.stat()
                items.append({"name": entry.name, "path": entry.path,
                              "is_dir": entry.is_dir(), "ext": os.path.splitext(entry.name)[1].lower(),
                              "mtime": st.st_mtime, "size": st.st_size})
            except Exception:
                items.append({"name": entry.name, "path": entry.path,
                              "is_dir": entry.is_dir(), "ext": "", "mtime": 0, "size": 0})

        items.sort(key=lambda x: (-x["is_dir"], -x["mtime"]))
        items = items[:150]
        results = []
        for it in items:
            t = _file_type(it["name"], it["is_dir"])
            info = f"[DIR]" if it["is_dir"] else f"[{t.upper()} | {it['size']/1024:.1f}KB]"
            results.append({"name": it["name"], "type": t, "path": it["path"], "info": info})
        return {"directory": target, "items_found": len(results), "content": results}
    except Exception as e:
        return f"System Error: {e}"


IGNORE_FOLDERS = {"node_modules","appdata","program files","windows","system volume information",
                  "dist","build",".git","$recycle.bin"}

@router.post("/file/search")
def search_files(req: SearchReq):
    try:
        key = req.groq_key or GROQ_KEY
        if not key:
            return "Error: Missing Groq API Key."

        groq = Groq(api_key=key)
        prompt = f'''Extract search keywords from: "{req.query}".
Rules: 1. Extract file name, extension, folder names. 2. Never include "file","document","folder","find". 3. Fix spelling. 4. If user mentions root location (desktop,documents,downloads), put in root_target.
Output JSON: {{"keywords":["word1","word2"],"root_target":""}}'''

        chat = groq.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant", response_format={"type": "json_object"})
        try:
            parsed = json.loads(chat.choices[0].message.content or '{"keywords":[]}')
            keywords = [str(k).lower().strip() for k in (parsed.get("keywords") or []) if k]
            root_target = parsed.get("root_target", "").strip().lower()
        except Exception:
            keywords = []
            root_target = ""

        if not keywords:
            return "No searchable keywords extracted."

        roots = set()
        if root_target:
            if len(root_target) == 1 and root_target.isalpha():
                roots.add(f"{root_target.upper()}:\\")
            elif root_target in ("desktop","documents","downloads","music","pictures","videos"):
                roots.add(_get_sys_path(root_target))
            else:
                roots.add(os.path.join(str(Path.home()), root_target))
        else:
            roots.add(str(Path.home()))
            if platform.system() == "Windows":
                for c in range(65, 91):
                    d = chr(c) + ":\\"
                    if d[0] != "C" and os.path.exists(d):
                        roots.add(d)

        found = []
        visited = set()
        queue = list(roots)
        while queue and len(found) < 15:
            cur = queue.pop(0)
            if cur in visited:
                continue
            visited.add(cur)
            try:
                entries = list(os.scandir(cur))
            except Exception:
                continue
            for entry in entries:
                if len(found) >= 15:
                    break
                lname = entry.name.lower()
                if entry.is_dir(follow_symlinks=False):
                    if lname.startswith(".") or lname.startswith("$") or lname in IGNORE_FOLDERS:
                        continue
                    queue.append(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    lpath = entry.path.lower()
                    if all(kw in lpath for kw in keywords):
                        found.append(entry.path)

        if found:
            return "NATIVE DEEP SYSTEM MATCHES:\n" + "\n".join(found[:15])
        return f"No files found matching [{', '.join(keywords)}]"
    except Exception as e:
        return f"System Error: {e}"


# ═══════════════════════════════════════════════════════════
#   4. GHOST CONTROL (Keyboard / Mouse / Volume / Screenshot)
# ═══════════════════════════════════════════════════════════
KEY_MAP = {
    "enter": "enter", "return": "enter", "space": "space", "tab": "tab",
    "escape": "escape", "esc": "escape", "backspace": "backspace",
    "shift": "shift", "control": "ctrl", "ctrl": "ctrl", "alt": "alt",
    "command": "win", "win": "win", "up": "up", "down": "down",
    "left": "left", "right": "right", "pageup": "pageup", "pagedown": "pagedown",
    "f1": "f1", "f5": "f5", "f11": "f11", "f12": "f12",
}
for c in "abcdefghijklmnopqrstuvwxyz":
    KEY_MAP[c] = c


def _human_path(sx, sy, ex, ey, steps=25):
    dev = random.random() * 80 + 20
    dx = 1 if ex > sx else -1
    dy = 1 if ey > sy else -1
    cx = sx + (abs(ex-sx)/2)*dx + random.choice([-1,1])*dev
    cy = sy + (abs(ey-sy)/2)*dy + random.choice([-1,1])*dev
    pts = []
    for i in range(steps+1):
        t = i/steps
        x = (1-t)**2*sx + 2*(1-t)*t*cx + t**2*ex
        y = (1-t)**2*sy + 2*(1-t)*t*cy + t**2*ey
        pts.append((int(x), int(y)))
    return pts


@router.post("/ghost/sequence")
def ghost_sequence(req: GhostSeqReq):
    try:
        for action in req.actions:
            atype = action.get("type", "")
            if atype == "paste":
                pyperclip.copy(action.get("text", ""))
                time.sleep(0.2)
                pyautogui.hotkey("ctrl", "v")
            elif atype == "wait":
                time.sleep(action.get("ms", 500) / 1000)
            elif atype == "type":
                pyautogui.write(action.get("text", ""), interval=0.02)
            elif atype == "press":
                k = KEY_MAP.get(action.get("key", "").lower())
                if k:
                    mods = action.get("modifiers", [])
                    if mods:
                        mapped = [KEY_MAP.get(m.lower(), m.lower()) for m in mods]
                        pyautogui.hotkey(*mapped, k)
                    else:
                        pyautogui.press(k)
            elif atype == "click":
                pyautogui.click()
        return True
    except Exception:
        return False


@router.post("/ghost/click")
def ghost_click(req: GhostClickReq):
    try:
        cx, cy = pyautogui.position()
        for px, py in _human_path(cx, cy, req.x, req.y):
            pyautogui.moveTo(px, py, _pause=False)
            time.sleep(0.01)
        if req.double_click:
            pyautogui.doubleClick()
        else:
            pyautogui.click()
        return True
    except Exception:
        return False


@router.post("/ghost/scroll")
def ghost_scroll(req: ScrollReq):
    try:
        amt = req.amount // 50
        if req.direction == "up":
            pyautogui.scroll(amt)
        else:
            pyautogui.scroll(-amt)
        return True
    except Exception:
        return False


@router.post("/ghost/screenshot")
def take_screenshot():
    try:
        fname = f"IRIS_Capture_{int(time.time()*1000)}.png"
        pics = _get_sys_path("pictures")
        os.makedirs(pics, exist_ok=True)
        save_path = os.path.join(pics, fname)
        with mss.mss() as sct:
            img = sct.grab(sct.monitors[1])
            Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX").save(save_path)
        if platform.system() == "Windows":
            subprocess.run(["explorer", "/select,", save_path])
        return f"Screenshot saved to {save_path}"
    except Exception as e:
        return f"Error: {e}"


@router.post("/ghost/volume")
def set_volume(req: VolumeReq):
    if HAS_VOLUME:
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            vol = cast(interface, POINTER(IAudioEndpointVolume))
            vol.SetMasterVolumeLevelScalar(max(0.0, min(1.0, req.level / 100.0)), None)
            return f"Volume {req.level}%"
        except Exception as e:
            return f"Error: {e}"
    return "Volume control not available (install pycaw)"


@router.post("/ghost/clipboard")
def copy_file_to_clipboard(req: FilePathReq):
    if platform.system() == "Windows":
        r = subprocess.run(["powershell", "-command", f"Set-Clipboard -Path '{req.file_path}'"],
                           capture_output=True)
        return r.returncode == 0
    return False


# ═══════════════════════════════════════════════════════════
#   5. TERMINAL CONTROL
# ═══════════════════════════════════════════════════════════
@router.post("/terminal/run")
def run_shell_command(req: ShellReq):
    try:
        safe_cwd = os.path.normpath(req.cwd) if req.cwd else None
        r = subprocess.run(["powershell.exe", "-Command", req.command],
                           cwd=safe_cwd, capture_output=True, text=True, timeout=60)
        return {"success": r.returncode == 0,
                "stdout": r.stdout, "stderr": r.stderr, "code": r.returncode}
    except Exception as e:
        return {"success": False, "output": str(e)}


# ═══════════════════════════════════════════════════════════
#   6. ADB MANAGER (Android Debug Bridge)
# ═══════════════════════════════════════════════════════════
_active_device = None

def _adb_target():
    if not _active_device:
        return None
    return f"-s {_active_device['ip']}:{_active_device['port']}"

def _adb(args, binary=False, timeout=15):
    t = _adb_target()
    if not t:
        return None
    cmd = f"adb {t} {args}"
    if binary:
        return _run_bytes(cmd.split(), timeout=timeout)
    return _run(cmd.split(), timeout=timeout)


@router.post("/adb/connect")
def adb_connect(req: AdbConnReq):
    global _active_device
    try:
        out = _run(["adb", "connect", f"{req.ip}:{req.port}"])
        if "connected" in out.lower():
            _active_device = {"ip": req.ip, "port": req.port}
            model = _run(["adb", "-s", f"{req.ip}:{req.port}", "shell", "getprop", "ro.product.model"])
            hist_dir = os.path.join(DATA_DIR, "Connected_Devices")
            hist_path = os.path.join(hist_dir, "Connect-mobile.json")
            try:
                history = json.loads(open(hist_path).read()) if os.path.exists(hist_path) else []
                entry = {"ip": req.ip, "port": req.port, "model": model.strip().upper(), "lastConnected": datetime.now().isoformat()}
                idx = next((i for i, d in enumerate(history) if d.get("ip") == req.ip), -1)
                if idx >= 0:
                    history[idx] = entry
                else:
                    history.append(entry)
                open(hist_path, "w").write(json.dumps(history, indent=2))
            except Exception:
                pass
            return {"success": True}
        return {"success": False, "error": out}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/adb/disconnect")
def adb_disconnect():
    global _active_device
    if not _active_device:
        return {"success": True}
    _run(["adb", "disconnect", f"{_active_device['ip']}:{_active_device['port']}"])
    _active_device = None
    return {"success": True}


@router.get("/adb/history")
def adb_history():
    try:
        p = os.path.join(DATA_DIR, "Connected_Devices", "Connect-mobile.json")
        return json.loads(open(p).read()) if os.path.exists(p) else []
    except Exception:
        return []


@router.get("/adb/screenshot")
def adb_screenshot():
    if not _active_device:
        return {"success": False}
    data = _adb("exec-out screencap -p", binary=True, timeout=20)
    if data:
        b64 = f"data:image/png;base64,{base64.b64encode(data).decode()}"
        return {"success": True, "image": b64}
    return {"success": False}


@router.post("/adb/quick-action")
def adb_quick_action(req: AdbActionReq):
    if not _active_device:
        return {"success": False}
    cmds = {
        "camera": "shell am start -a android.media.action.STILL_IMAGE_CAMERA",
        "wake": "shell input keyevent KEYCODE_WAKEUP",
        "lock": "shell input keyevent KEYCODE_SLEEP",
        "home": "shell input keyevent KEYCODE_HOME"
    }
    c = cmds.get(req.action)
    if c:
        _adb(c)
        return {"success": True}
    return {"success": False, "error": "Unknown action"}


@router.get("/adb/telemetry")
def adb_telemetry():
    if not _active_device:
        return {"success": False, "error": "No device"}
    try:
        bat = _adb("shell dumpsys battery")
        level = int(re.search(r"level: (\d+)", bat).group(1)) if re.search(r"level: (\d+)", bat) else 0
        temp_m = re.search(r"temperature: (\d+)", bat)
        temp = f"{int(temp_m.group(1))/10:.1f}" if temp_m else "0"
        charging = "AC powered: true" in bat or "USB powered: true" in bat
        stor = _adb("shell df -h /data")
        lines = stor.strip().split("\n")
        s_used, s_total, s_pct = "0", "0", 0
        if len(lines) > 1:
            parts = lines[1].split()
            if len(parts) >= 5:
                s_total, s_used = parts[1], parts[2]
                s_pct = int(parts[4].replace("%", "")) if "%" in parts[4] else 0
        model = _adb("shell getprop ro.product.model").strip().upper()
        osv = _adb("shell getprop ro.build.version.release").strip()
        return {"success": True, "data": {"model": model, "os": f"ANDROID {osv}",
                "battery": {"level": level, "isCharging": charging, "temp": temp},
                "storage": {"used": s_used, "total": s_total, "percent": s_pct}}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/adb/mobile-info")
def adb_mobile_info():
    if not _active_device:
        return "Error: No mobile device connected."
    try:
        model = _adb("shell getprop ro.product.model").strip()
        bat = _adb("shell dumpsys battery")
        level = re.search(r"level: (\d+)", bat)
        return f"Connected to {model}. Battery at {level.group(1)}%." if level else f"Connected to {model}."
    except Exception:
        return "Connected but telemetry unavailable."


@router.post("/adb/open-app")
def adb_open_app(req: AdbAppReq):
    if not _active_device:
        return {"success": False, "error": "No phone connected."}
    if req.package_name == "android.media.action.STILL_IMAGE_CAMERA":
        _adb("shell am start -a android.media.action.STILL_IMAGE_CAMERA")
    else:
        _adb(f"shell monkey -p {req.package_name} -c android.intent.category.LAUNCHER 1")
    return {"success": True}


@router.post("/adb/close-app")
def adb_close_app(req: AdbAppReq):
    if not _active_device:
        return {"success": False, "error": "No phone connected."}
    pkg = "com.google.android.GoogleCamera" if req.package_name == "android.media.action.STILL_IMAGE_CAMERA" else req.package_name
    _adb(f"shell am force-stop {pkg}")
    return {"success": True}


@router.post("/adb/tap")
def adb_tap(req: AdbTapReq):
    if not _active_device:
        return {"success": False}
    sz = _adb("shell wm size")
    m = re.search(r"(\d+)x(\d+)", sz)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        x, y = round(req.x_percent/100*w), round(req.y_percent/100*h)
        _adb(f"shell input tap {x} {y}")
        return {"success": True}
    return {"success": False, "error": "Could not get screen size."}


@router.post("/adb/swipe")
def adb_swipe(req: AdbSwipeReq):
    if not _active_device:
        return {"success": False}
    sz = _adb("shell wm size")
    m = re.search(r"(\d+)x(\d+)", sz)
    if not m:
        return {"success": False}
    w, h = int(m.group(1)), int(m.group(2))
    cx, cy = w//2, h//2
    cmds = {"up": f"input swipe {cx} {int(h*0.7)} {cx} {int(h*0.3)} 300",
            "down": f"input swipe {cx} {int(h*0.3)} {cx} {int(h*0.7)} 300",
            "left": f"input swipe {int(w*0.8)} {cy} {int(w*0.2)} {cy} 300",
            "right": f"input swipe {int(w*0.2)} {cy} {int(w*0.8)} {cy} 300"}
    c = cmds.get(req.direction)
    if c:
        _adb(f"shell {c}")
        return {"success": True}
    return {"success": False, "error": "Invalid direction."}


@router.get("/adb/notifications")
def adb_notifications():
    if not _active_device:
        return {"success": False}
    try:
        out = _adb("shell dumpsys notification --noredact", timeout=20)
        notifs, title = [], ""
        for line in out.split("\n"):
            if "android.title=" in line:
                m = re.search(r"android\.title=(?:String|CharSequence) \((.*?)\)", line)
                if m:
                    title = m.group(1).strip()
            elif "android.text=" in line and title:
                m = re.search(r"android\.text=(?:String|CharSequence) \((.*?)\)", line)
                if m:
                    txt = m.group(1).strip()
                    if not any(w in title.lower() for w in ("running","sync")) and not "running" in txt.lower():
                        msg = f"From {title}: {txt}"
                        if msg not in notifs:
                            notifs.append(msg)
                    title = ""
        return {"success": True, "data": notifs}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/adb/push-file")
def adb_push_file(req: AdbFileReq):
    if not _active_device:
        return {"success": False, "error": "No phone connected."}
    _adb(f'push "{req.source_path}" "{req.dest_path}"', timeout=60)
    return {"success": True}


@router.post("/adb/pull-file")
def adb_pull_file(req: AdbFileReq):
    if not _active_device:
        return {"success": False, "error": "No phone connected."}
    dest = req.dest_path or _get_sys_path("downloads")
    _adb(f'pull "{req.source_path}" "{dest}"', timeout=60)
    return {"success": True, "saved_to": dest}


@router.post("/adb/hardware-toggle")
def adb_hardware_toggle(req: AdbHwReq):
    if not _active_device:
        return {"success": False}
    s = req.setting.lower().strip()
    act = "enable" if req.state else "disable"
    try:
        if s in ("bluetooth", "bt"):
            _adb(f"shell svc bluetooth {act}")
        elif s == "wifi":
            _adb(f"shell svc wifi {act}")
        elif s in ("data", "mobile data"):
            _adb(f"shell svc data {act}")
        elif s in ("airplane", "flight"):
            _adb(f"shell cmd connectivity airplane-mode {act}")
        elif s in ("location", "gps"):
            _adb(f"shell settings put secure location_mode {'3' if req.state else '0'}")
        elif s in ("flashlight", "torch"):
            _adb("shell input keyevent KEYCODE_WAKEUP")
            _adb("shell cmd statusbar expand-settings")
            return {"success": True, "warning": "Opened Quick Settings for flashlight toggle."}
        else:
            return {"success": False, "error": f"Unknown setting: {req.setting}"}
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
#   7. WEB AGENT
# ═══════════════════════════════════════════════════════════
USER_BOOKMARKS = {"instagram": "https://instagram.com", "reddit": "https://reddit.com",
                  "chatgpt": "https://chat.openai.com", "claude": "https://claude.ai",
                  "linkedin": "https://linkedin.com"}


@router.post("/web/search")
def web_search(req: WebSearchReq):
    q = req.query.lower()
    url = None
    skip_scrape = False

    for key, burl in USER_BOOKMARKS.items():
        if key in q:
            url = burl
            break
    if not url:
        if any(w in q for w in ("amazon", "buy", "shop for")):
            term = re.sub(r"(amazon|buy|price of|shop for)", "", q).strip()
            url = f"https://www.amazon.in/s?k={term}"
            skip_scrape = True
        elif any(w in q for w in ("youtube", "watch")):
            term = re.sub(r"(youtube|watch)", "", q).strip()
            url = f"https://www.youtube.com/results?search_query={term}"
            skip_scrape = True
        elif any(w in q for w in ("github", "repo")):
            m = re.search(r"github(?:\s+profile)?(?:\s+of)?\s+(\w+)", q)
            term = m.group(1) if m else q.replace("github", "").strip()
            url = f"https://github.com/{term}"

    final_url = url or f"https://www.google.com/search?q={req.query}"
    webbrowser.open(final_url)

    if skip_scrape:
        return "Opened the link for you."

    try:
        scrape_url = final_url if url else f"https://duckduckgo.com/?q={req.query}&ia=web"
        r = httpx.get(scrape_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, follow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
        paras = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 50][:3]
        summary = "\n\n".join(paras)
        if not summary or len(summary) < 20:
            return "Opened the browser for you."
        return f"Opened the link. Quick summary:\n{summary[:500]}..."
    except Exception:
        return "Opened the browser, but couldn't read the content."


# ═══════════════════════════════════════════════════════════
#   8. LIVE LOCATION
# ═══════════════════════════════════════════════════════════
@router.get("/location/live")
def get_live_location():
    try:
        if platform.system() == "Windows":
            ps = 'Add-Type -AssemblyName System.Device; $w = New-Object System.Device.Location.GeoCoordinateWatcher; $w.Start(); $t=0; while($w.Position.Location.IsUnknown -and $t -lt 15){Start-Sleep -Milliseconds 300;$t++}; if(!$w.Position.Location.IsUnknown){Write-Output "$($w.Position.Location.Latitude),$($w.Position.Location.Longitude)"}'
            loc = _run(["powershell", "-Command", ps], timeout=20)
            if loc and "," in loc and not loc.startswith("Error"):
                lat, lon = loc.split(",")[:2]
                try:
                    geo = httpx.get(f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lon}&localityLanguage=en", timeout=5).json()
                    return {"city": geo.get("city") or geo.get("locality"), "region": geo.get("principalSubdivision"),
                            "country": geo.get("countryName"), "lat": float(lat), "lon": float(lon),
                            "fullString": f"{geo.get('city','')}, {geo.get('principalSubdivision','')}, {geo.get('countryName','')}"}
                except Exception:
                    return {"lat": float(lat), "lon": float(lon)}

        ip_data = httpx.get("http://ip-api.com/json/", timeout=5).json()
        if ip_data.get("status") == "success":
            return {"city": ip_data["city"], "region": ip_data["regionName"], "country": ip_data["country"],
                    "lat": ip_data["lat"], "lon": ip_data["lon"], "timezone": ip_data.get("timezone"),
                    "fullString": f"{ip_data['city']}, {ip_data['regionName']}, {ip_data['country']}"}
        return None
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════
#   9. NOTES MANAGER
# ═══════════════════════════════════════════════════════════
@router.post("/notes/save")
def save_note(req: NoteReq):
    try:
        d = os.path.join(DATA_DIR, "Notes")
        safe = re.sub(r"[^a-z0-9]", "_", req.title.lower())[:50]
        fp = os.path.join(d, f"{safe}.md")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(f"# {req.title}\n\n{req.content}")
        return {"success": True, "path": fp}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/notes/list")
def get_notes():
    try:
        d = os.path.join(DATA_DIR, "Notes")
        notes = []
        for f in os.listdir(d):
            if f.endswith(".md"):
                fp = os.path.join(d, f)
                st = os.stat(fp)
                content = open(fp, "r", encoding="utf-8").read()
                notes.append({"filename": f, "title": f.replace(".md","").replace("_"," "),
                              "content": content, "createdAt": st.st_ctime, "path": fp})
        return sorted(notes, key=lambda x: -x["createdAt"])
    except Exception:
        return []


@router.post("/notes/delete")
def delete_note(req: NoteDelReq):
    fp = os.path.join(DATA_DIR, "Notes", req.filename)
    if os.path.exists(fp):
        os.remove(fp)
        return True
    return False


# ═══════════════════════════════════════════════════════════
#   10. GALLERY MANAGER
# ═══════════════════════════════════════════════════════════
@router.get("/gallery/list")
def get_gallery():
    try:
        d = os.path.join(DATA_DIR, "Gallery")
        imgs = []
        for f in os.listdir(d):
            if re.search(r"\.(png|jpg|jpeg|webp|gif)$", f, re.I):
                fp = os.path.join(d, f)
                st = os.stat(fp)
                imgs.append({"filename": f, "path": fp, "createdAt": st.st_ctime,
                             "displayName": re.sub(r"_\d+_Generated_by_IRIS\.png$","",f).replace("_"," ")})
        return sorted(imgs, key=lambda x: -x["createdAt"])
    except Exception:
        return []


@router.post("/gallery/save")
def save_gallery_image(req: GallSaveReq):
    try:
        d = os.path.join(DATA_DIR, "Gallery")
        safe = re.sub(r"[^a-z0-9]", "_", (req.title or "visual").lower())[:50]
        fname = f"{safe}_{int(time.time()*1000)}_Generated_by_IRIS.png"
        fp = os.path.join(d, fname)
        data = re.sub(r"^data:image/\w+;base64,", "", req.base64_data)
        with open(fp, "wb") as f:
            f.write(base64.b64decode(data))
        return {"success": True, "path": fp}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/gallery/delete")
def delete_gallery_image(req: GallDelReq):
    fp = os.path.join(DATA_DIR, "Gallery", req.filename)
    if os.path.exists(fp):
        os.remove(fp)
        return True
    return False


# ═══════════════════════════════════════════════════════════
#   11. MEMORY (Chat History + Permanent Facts)
# ═══════════════════════════════════════════════════════════
@router.post("/memory/add-message")
def add_message(req: MemMsgReq):
    try:
        fp = os.path.join(DATA_DIR, "Chat", "iris_memory.json")
        history = json.loads(open(fp).read()) if os.path.exists(fp) else []
        history.append({"role": req.role, "content": req.text, "timestamp": datetime.now().isoformat()})
        if len(history) > 20:
            history = history[-20:]
        with open(fp, "w") as f:
            json.dump(history, f, indent=2)
        return True
    except Exception:
        return False


@router.get("/memory/history")
def get_history():
    try:
        fp = os.path.join(DATA_DIR, "Chat", "iris_memory.json")
        if os.path.exists(fp):
            raw = json.loads(open(fp).read())
            return [{"role": "model" if m.get("role") == "iris" else m.get("role"),
                     "parts": [{"text": m.get("content")}]} for m in raw]
        return []
    except Exception:
        return []


@router.post("/memory/save-fact")
def save_core_memory(req: MemFactReq):
    try:
        fp = os.path.join(DATA_DIR, "Memory", "saved-user-memory.json")
        bank = json.loads(open(fp).read()) if os.path.exists(fp) else []
        bank.append({"fact": req.fact, "timestamp": datetime.now().isoformat()})
        with open(fp, "w") as f:
            json.dump(bank, f, indent=2)
        return True
    except Exception:
        return False


@router.get("/memory/facts")
def search_core_memory():
    try:
        fp = os.path.join(DATA_DIR, "Memory", "saved-user-memory.json")
        return json.loads(open(fp).read()) if os.path.exists(fp) else []
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════
#   12. GMAIL MANAGER
# ═══════════════════════════════════════════════════════════
GMAIL_SCOPES = ["https://mail.google.com/"]

def _gmail_service():
    if not HAS_GMAIL:
        raise Exception("Gmail libraries not installed.")
    token_path = os.path.join(DATA_DIR, "gmail_token.json")
    creds_path = os.path.join(os.getcwd(), "credentials.json")
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, GMAIL_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GAuthRequest())
        else:
            if not os.path.exists(creds_path):
                raise Exception("credentials.json not found. Place it in the project root.")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return gmail_build("gmail", "v1", credentials=creds)


def _make_email(to, subject, body):
    raw = f"To: {to}\nSubject: {subject}\n\n{body}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


@router.post("/gmail/read")
def gmail_read(req: GmailReadReq):
    try:
        svc = _gmail_service()
        res = svc.users().messages().list(userId="me", maxResults=req.max_results).execute()
        msgs = res.get("messages", [])
        if not msgs:
            return {"speechText": "Inbox is empty.", "uiData": []}
        emails, ui = [], []
        for msg in msgs:
            full = svc.users().messages().get(userId="me", id=msg["id"]).execute()
            headers = {h["name"]: h["value"] for h in full.get("payload", {}).get("headers", [])}
            subj = headers.get("Subject", "No Subject")
            frm = headers.get("From", "Unknown")
            date = headers.get("Date", "")
            snippet = full.get("snippet", "")
            emails.append(f"From: {frm}\nSubject: {subj}\nPreview: {snippet}\n")
            ui.append({"id": full["id"], "from": frm, "subject": subj, "date": date, "preview": snippet})
        return {"speechText": "\n---\n".join(emails), "uiData": ui}
    except Exception as e:
        return {"speechText": f"Gmail Error: {e}", "uiData": []}


@router.post("/gmail/send")
def gmail_send(req: GmailSendReq):
    try:
        svc = _gmail_service()
        raw = _make_email(req.to, req.subject, req.body)
        svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"Email sent to {req.to}."
    except Exception as e:
        return f"Send Error: {e}"


@router.post("/gmail/draft")
def gmail_draft(req: GmailSendReq):
    try:
        svc = _gmail_service()
        raw = _make_email(req.to, req.subject, req.body)
        svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        return f"Draft created for {req.to}."
    except Exception as e:
        return f"Draft Error: {e}"


# ═══════════════════════════════════════════════════════════
#   13. TELEKINESIS (Window Snapping)
# ═══════════════════════════════════════════════════════════
@router.post("/telekinesis/teleport")
def teleport_windows(req: TelekinesisReq):
    if not HAS_WINMGR:
        return {"success": False, "error": "pygetwindow not available."}
    try:
        with mss.mss() as sct:
            mon = sct.monitors[1]
            sw, sh = mon["width"], mon["height"]
            sx, sy = mon["left"], mon["top"]
        all_wins = gw.getAllWindows()
        for cmd in req.commands:
            name = cmd.get("appName", "").lower()
            pos = cmd.get("position", "maximize")
            target = next((w for w in all_wins if w.title and name in w.title.lower()), None)
            if not target:
                continue
            try:
                target.restore()
                target.activate()
            except Exception:
                pass
            hw, hh = sw // 2, sh // 2
            bounds = {
                "left": (sx, sy, hw, sh), "right": (sx+hw, sy, hw, sh),
                "top-left": (sx, sy, hw, hh), "top-right": (sx+hw, sy, hw, hh),
                "bottom-left": (sx, sy+hh, hw, hh), "bottom-right": (sx+hw, sy+hh, hw, hh),
            }
            if pos == "maximize":
                try:
                    target.maximize()
                except Exception:
                    pass
            elif pos in bounds:
                bx, by, bw, bh = bounds[pos]
                try:
                    target.moveTo(bx, by)
                    target.resizeTo(bw, bh)
                except Exception:
                    pass
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
#   14. AI SERVICES (Coder / Phantom / Website / ScreenPeeler)
# ═══════════════════════════════════════════════════════════
def _get_genai_client(key=None):
    k = key or GEMINI_KEY
    if not k:
        raise Exception("Missing Gemini API Key. Set GEMINI_API_KEY in .env")
    if not HAS_GENAI:
        raise Exception("google-genai not installed.")
    return genai.Client(api_key=k)


@router.post("/ai/code")
def start_live_coding(req: AiCodeReq):
    try:
        client = _get_genai_client(req.gemini_key)
        proj_dir = os.path.join(DATA_DIR, "Projects")
        fp = os.path.join(proj_dir, req.filename)
        prompt = f'You are an elite developer. Write the code for: "{req.prompt}". Output ONLY the raw code for the file {req.filename}. No markdown blockquotes.'
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        code = response.text or ""
        code = re.sub(r"^```\w*\n?", "", code)
        code = re.sub(r"```$", "", code).strip()
        with open(fp, "w", encoding="utf-8") as f:
            f.write(code)
        return {"success": True, "filePath": fp, "code": code}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/ai/phantom")
def phantom_execute(req: PhantomReq):
    try:
        client = _get_genai_client(req.gemini_key)
        prompt = f"You are Phantom, an inline code generator. Output ONLY the raw text or code requested. NO markdown formatting. NO conversational text.\n\nRequest: {req.prompt}"
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        text = response.text or ""
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"```$", "", text).strip()
        pyperclip.copy(text)
        time.sleep(0.15)
        pyautogui.hotkey("ctrl", "v")
        return {"success": True, "text": text}
    except Exception as e:
        return {"success": False, "error": str(e)}


WEB_BUILDER_PROMPT = """You are an elite, Awwwards-winning frontend developer. Build a stunning, animated website based on the user prompt.
RULES: 1. Single HTML file with CSS in <style> and JS in <script>. Start with <!DOCTYPE html>.
2. Use Tailwind CDN and GSAP CDN. 3. Use picsum.photos for images. 4. Premium hero with glowing orbs, magnetic buttons.
5. 5-6 sections: Hero, About, Features (grid), Gallery, CTA+Footer. 6. Rich realistic copy, no lorem ipsum.
OUTPUT ONLY RAW HTML."""


@router.post("/ai/website")
def build_website(req: AiWebsiteReq):
    try:
        client = _get_genai_client(req.gemini_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{WEB_BUILDER_PROMPT}\n\nUSER PROMPT: {req.prompt}")
        code = response.text or ""
        code = re.sub(r"^```html\n?", "", code)
        code = re.sub(r"```$", "", code).strip()
        web_dir = os.path.join(DATA_DIR, "Websites")
        fp = os.path.join(web_dir, f"website_{int(time.time()*1000)}.html")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(code)
        webbrowser.open(fp)
        return {"success": True, "filePath": fp}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/ai/screen-peeler")
def screen_peeler(req: ScreenPeelReq):
    try:
        client = _get_genai_client(req.gemini_key)
        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[1])
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        if req.width > 0 and req.height > 0:
            img = img.crop((req.x, req.y, req.x + req.width, req.y + req.height))
        buf = BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                "Extract text/code from this image. Output ONLY as JSON: {\"language\": \"python\", \"code\": \"extracted text\"}. No markdown blocks.",
                genai_types.Part.from_bytes(data=img_bytes, mime_type="image/png")
            ])
        ai_text = response.text or ""
        try:
            parsed = json.loads(re.sub(r"```json|```", "", ai_text).strip())
            lang = (parsed.get("language") or "text").lower()
            code = parsed.get("code", "")
        except Exception:
            lang, code = "text", ai_text
        pyperclip.copy(code)
        try:
            lexer = get_lexer_by_name(lang)
            highlighted = pyg_highlight(code, lexer, HtmlFormatter())
        except Exception:
            highlighted = code
        return {"success": True, "language": lang, "code": code,
                "highlighted": highlighted, "image_base64": base64.b64encode(img_bytes).decode()}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
#   15. WORKFLOW MANAGER
# ═══════════════════════════════════════════════════════════
@router.get("/workflow/load")
def load_workflows():
    try:
        fp = os.path.join(DATA_DIR, "Workflows", "iris_workflows.json")
        return {"success": True, "workflows": json.loads(open(fp).read()) if os.path.exists(fp) else []}
    except Exception:
        return {"success": True, "workflows": []}


@router.post("/workflow/save")
def save_workflow(req: WorkflowSaveReq):
    try:
        fp = os.path.join(DATA_DIR, "Workflows", "iris_workflows.json")
        wfs = json.loads(open(fp).read()) if os.path.exists(fp) else []
        idx = next((i for i, w in enumerate(wfs) if w.get("name") == req.name), -1)
        entry = {"name": req.name, "description": req.description,
                 "nodes": req.nodes, "edges": req.edges, "updatedAt": int(time.time()*1000)}
        if idx >= 0:
            wfs[idx] = entry
        else:
            wfs.append(entry)
        with open(fp, "w") as f:
            json.dump(wfs, f, indent=2)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/workflow/delete")
def delete_workflow(req: WorkflowDelReq):
    try:
        fp = os.path.join(DATA_DIR, "Workflows", "iris_workflows.json")
        wfs = json.loads(open(fp).read()) if os.path.exists(fp) else []
        wfs = [w for w in wfs if w.get("name") != req.name]
        with open(fp, "w") as f:
            json.dump(wfs, f, indent=2)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
#   16. SMART DROPZONE (Drag-Drop + File Move)
# ═══════════════════════════════════════════════════════════
@router.post("/dropzone/drag")
def ghost_drag_and_drop(req: DragDropReq):
    try:
        path_pts = _human_path(req.start_x, req.start_y, req.end_x, req.end_y)
        pyautogui.moveTo(req.start_x, req.start_y)
        time.sleep(0.2)
        pyautogui.mouseDown()
        time.sleep(0.1)
        for px, py in path_pts:
            pyautogui.moveTo(px, py, _pause=False)
            time.sleep(0.015)
        time.sleep(0.1)
        pyautogui.mouseUp()
        return True
    except Exception:
        return False


@router.post("/dropzone/move-file")
def move_file_to_category(req: MoveFileReq):
    try:
        fname = os.path.basename(req.source_path)
        dest = os.path.join(req.target_folder, fname)
        os.makedirs(req.target_folder, exist_ok=True)
        shutil.move(req.source_path, dest)
        return {"success": True, "destPath": dest}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
#   17. WIDGET MANAGER
# ═══════════════════════════════════════════════════════════
@router.post("/widget/create")
def create_widget(req: WidgetReq):
    try:
        d = os.path.join(DATA_DIR, "DynamicWidgets")
        fp = os.path.join(d, f"widget_{int(time.time()*1000)}.html")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(req.html_code)
        webbrowser.open(fp)
        return {"success": True, "filePath": fp}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/widget/close-all")
def close_widgets():
    try:
        d = os.path.join(DATA_DIR, "DynamicWidgets")
        count = 0
        for f in os.listdir(d):
            if f.startswith("widget_") and f.endswith(".html"):
                os.remove(os.path.join(d, f))
                count += 1
        return {"success": True, "message": f"Cleaned {count} widget file(s)."}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
#   18. REALITY HACKER (Open URL in browser)
# ═══════════════════════════════════════════════════════════
@router.post("/hacker/hack")
def hack_website(req: HackerReq):
    try:
        webbrowser.open(req.url)
        return {"success": True, "message": f"Opened {req.url}. Theme injection requires Electron/browser control."}
    except Exception as e:
        return {"success": False, "error": str(e)}


