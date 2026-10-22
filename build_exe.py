
import os
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True,
                           errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True,
                           errors="replace")
except Exception:
    pass

from pathlib import Path

ABE_DLLS = ("chrome", "chrome_beta", "brave", "edge", "avast")


def _say(msg: str = "") -> None:
    print(msg, flush=True)


def _have_nuitka() -> str:
    try:
        from importlib.metadata import version, PackageNotFoundError
        try:
            return f"nuitka {version('nuitka')}"
        except PackageNotFoundError:
            pass
    except Exception:
        pass
    exe = shutil.which("nuitka")
    if exe:
        return f"nuitka (on PATH: {exe})"
    return ""


def _install_nuitka() -> str:
    _say("        installing nuitka via pip - this can take a minute...")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade",
         "--disable-pip-version-check",
         "nuitka", "ordered-set", "zstandard"],
    )
    if r.returncode != 0:
        raise RuntimeError(f"pip install nuitka failed (rc={r.returncode})")
    v = _have_nuitka()
    if not v:
        raise RuntimeError("nuitka installed but metadata not visible")
    return v


def _clean_input(raw: str) -> str:
    s = raw.strip()
    s = s.strip('"').strip("'").strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1].strip()
    elif s.startswith("["):
        s = s[1:].strip()
    elif s.endswith("]"):
        s = s[:-1].strip()
    return s


def _ask(prompt: str, default: Path, kind: str) -> Path:
    label = "file" if kind == "file" else "folder"
    _say(f"  {prompt}")
    if default.exists():
        _say(f"    default: {default}")
    _say("    (press enter for default, or paste a path)")

    for attempt in range(3):
        try:
            raw = input("  > ")
        except EOFError:
            raw = ""
        s = _clean_input(raw)
        p = (Path(s) if s else default).expanduser().resolve()

        ok = p.is_file() if kind == "file" else p.is_dir()
        if ok:
            _say(f"    ok: {p}")
            return p

        _say(f"    not a {label}: {p}")
        if attempt < 2:
            _say("    try again")
    raise RuntimeError(f"no valid {label} after 3 attempts")


def main() -> int:
    here = Path(__file__).resolve().parent

    _say()
    _say("  ============================================")
    _say("  Phantom Elevator - Nuitka build")
    _say("  ============================================")
    _say()

    _say("  [1/5] checking nuitka...")
    v = _have_nuitka()
    if v:
        _say(f"        ok: {v}")
    else:
        _say("        not found")
        v = _install_nuitka()
        _say(f"        installed: {v}")
    _say()

    _say("  [2/5] locating files...")
    src = _ask("  phantom_elevator.py path",
               here / "phantom_elevator.py", "file")
    _say()
    dlls = _ask("  dlls folder path",
                here / "dlls", "dir")
    _say()

    _say("  [3/5] validating dlls...")
    missing = [n for n in ABE_DLLS if not (dlls / f"{n}.dll").is_file()]
    if missing:
        _say(f"        missing in {dlls}:")
        for m in missing:
            _say(f"          {m}.dll")
        _say()
        _say("        run build_dlls.py first to generate them")
        return 1
    _say(f"        ok: {len(ABE_DLLS)} dlls present")
    for n in ABE_DLLS:
        size = (dlls / f"{n}.dll").stat().st_size
        _say(f"          {n}.dll  {size} bytes")
    _say()

    _say("  [4/5] building (first run can take 3-5 minutes)...")
    _say(f"        source  {src}")
    _say(f"        dlls    {dlls}")
    _say()

    out_dir = here / "dist"
    out_dir.mkdir(exist_ok=True)

 
    cmd = [
        sys.executable, "-m", "nuitka",
        "--onefile",
        "--windows-console-mode=force",
        "--assume-yes-for-downloads",
        "--include-package=Crypto",
        "--include-package=snappy",
        f"--include-data-files={dlls}\\*.dll=dlls/",
        "--nofollow-import-to=tkinter",
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=pydoc",
        "--nofollow-import-to=doctest",
        "--nofollow-import-to=distutils",
        "--nofollow-import-to=setuptools",
        f"--output-dir={out_dir}",
        "--output-filename=phantom_elevator",
        "--remove-output",
        str(src),
    ]

    _say("  $ " + " ".join(cmd))
    _say()
    r = subprocess.run(cmd, cwd=str(src.parent))
    _say()

    if r.returncode != 0:
        _say(f"  [5/5] build failed (rc={r.returncode})")
        return r.returncode

    _say("  [5/5] done")
    exe = out_dir / "phantom_elevator.exe"
    if not exe.is_file():
        found = list(out_dir.rglob("phantom_elevator*.exe"))
        if found:
            exe = found[0]
    if not exe.is_file():
        _say(f"        build exited 0 but no exe in {out_dir}")
        return 1

    size_mb = exe.stat().st_size / (1024 * 1024)
    _say(f"        exe:  {exe}")
    _say(f"        size: {size_mb:.1f} MB")
    _say()
    _say("  ship this one file. no python, no gcc, no dlls beside it.")
    _say()
    return 0


def _pause() -> None:
    if os.environ.get("PE_NO_PAUSE"):
        return
    if "--no-pause" in sys.argv:
        return
    try:
        input("  press enter to close...")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    rc = 1
    try:
        rc = main()
    except KeyboardInterrupt:
        _say()
        _say("  interrupted")
        rc = 130
    except RuntimeError as e:
        _say()
        _say(f"  error: {e}")
        rc = 1
    except Exception:
        import traceback
        traceback.print_exc()
        rc = 1
    finally:
        _pause()
    sys.exit(rc)
