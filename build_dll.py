
import os
import shutil
import subprocess
import sys
import tempfile

import phantom_elevator as pe


def _find_cc() -> str:
    for name in ("x86_64-w64-mingw32-gcc", "gcc"):
        p = shutil.which(name)
        if p:
            return p
    sys.exit("no x86_64 gcc on PATH — install mingw-w64")


def _build_one(cc: str, cfg: dict) -> bytes:
    tmp = tempfile.mkdtemp(prefix="bdll_")
    src = os.path.join(tmp, "ph.c")
    dll = os.path.join(tmp, "ph.dll")

    v2 = pe._V2_ATTEMPT if cfg.get("iid_v2") else ""
    iid_v2_c = (pe._guid_to_c(cfg["iid_v2"]) if cfg.get("iid_v2")
                else pe._guid_to_c(cfg["iid_v1"]))

    code = pe.ABE_TEMPLATE
    code = code.replace("@@CLSID@@", pe._guid_to_c(cfg["cls_id"]))
    code = code.replace("@@IID_V1@@", pe._guid_to_c(cfg["iid_v1"]))
    code = code.replace("@@IID_V2@@", iid_v2_c)
    code = code.replace("@@V2_ATTEMPT@@", v2)
    code = code.replace("@@VT_INDEX@@", str(cfg["vtable_offset"] // 8))

    with open(src, "w", encoding="utf-8") as f:
        f.write(code)

    r = subprocess.run(
        [cc, "-shared", "-O2", "-s", "-static", "-static-libgcc",
         "-o", dll, src,
         "-lole32", "-loleaut32", "-luser32"],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not os.path.isfile(dll):
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(f"{cfg['name']}: {r.stderr[:300]}")

    with open(dll, "rb") as f:
        blob = f.read()
    shutil.rmtree(tmp, ignore_errors=True)
    return blob


def main() -> int:
    cc = _find_cc()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dlls")
    os.makedirs(out, exist_ok=True)

    for cfg in pe.BROWSERS:
        if not cfg.get("abe"):
            continue
        blob = _build_one(cc, cfg)
        fn = cfg["name"].lower().replace(" ", "_") + ".dll"
        with open(os.path.join(out, fn), "wb") as f:
            f.write(blob)
        print(f"  {fn:<22} {len(blob):>6} bytes")

    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
