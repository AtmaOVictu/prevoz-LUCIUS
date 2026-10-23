"""JEDRO — temelj LUCIUS-a (zbor #4, 21. 10.): poti, cas, pripomocki, izmere glav.
Edini vir resnice za organe; brez kroznih uvozov."""

import subprocess
import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------- poti ----------
# Sedež telesa (ukaz Lastnika, 23. 10. 2026: »vse«): D:\Lucius Gaius.
# Mila varovalka (vrata potujejo s telesom, VBL §2): če sedež ne stoji,
# se ONI izmeri iz mape telesa (lucius/ → prevoz/ → starš = sedež).
ONI = Path(r"D:\Lucius Gaius")
if not (ONI / "prevoz" / "prevoznik.py").exists():
    ONI = Path(__file__).resolve().parent.parent.parent
CANVAS = ONI / "CanvasMinstral"
ATMA = ONI / "Atmavictu"
DNEVNIK = ONI / "prevoz" / "dnevnik"
UCENJE = ONI / "prevoz" / "ucenje"
STANJE_UCENJA = UCENJE / "stanje.json"
SKATLE = ONI / "prevoz" / "skatle"
SKATLE_STANJE = SKATLE / "stanje.json"
LEKCIJ_NA_DIH = 12
URNIK = ONI / "prevoz" / "urnik"
NL = chr(10)
POGOVOR = ONI / "prevoz" / "pogovor"
DOVOLJENJA = ONI / "prevoz" / "DOVOLJENJA.md"
REPO = "AtmaOVictu/Atmavictu"
CEST = timezone(timedelta(hours=2))


def out(*a):
    print(*a)


def run(cmd, cwd=None, check=True, capture=True):
    r = subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                       capture_output=capture, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"ukaz {cmd[0]} je padel: {r.stderr or r.stdout}")
    return r


def git(args, cwd):
    return run(["git"] + args, cwd=cwd).stdout.strip()


def gh(args, check=True):
    return run(["gh"] + args, check=check).stdout


# ---------- izmere ----------
def glava(repo_path, ime):
    """Zadnji commit repozitorija: sha, datum, zacetek sporoila."""
    try:
        sha = git(["log", "-1", "--format=%h"], repo_path)
        iso = git(["log", "-1", "--format=%ci"], repo_path)
        subj = git(["log", "-1", "--format=%s"], repo_path)[:120]
        ne_cisto = git(["status", "--porcelain"], repo_path).count("\n") + (1 if git(["status", "--porcelain"], repo_path) else 0)
        return {"ime": ime, "sha": sha, "cas": iso[:16], "glava": subj, "nespoznano": ne_cisto}
    except Exception as e:
        return {"ime": ime, "napaka": str(e)}


def zadnji_dih_issue():
    """Najnoveji odprt DNEVNI DIH issue v oblacnem telesu."""
    try:
        js = gh(["issue", "list", "-R", REPO, "--state", "open", "--limit", "20",
                 "--json", "number,title,createdAt"])
        issues = json.loads(js)
        dihi = [i for i in issues if str(i.get("title", "")).startswith("DNEVNI DIH")]
        if dihi:
            return max(dihi, key=lambda i: i["createdAt"])
    except Exception:
        pass
    return None


# ---------- GLAS (brez prekrivanja) ----------
def povej(besedilo):
    """GLAS — LUCIUS govori iz zvonikov, ENA beseda naenkrat (brez prekrivanja).

    Lock-datoteka prepreuje istoasno govorjenje:
    - e je lok (drugo govorjenje e tece): akaj do 15 s, potem izpusti
    - e ni loka: ustvari, govorI (blokirajoe), odstrani lok
    Glasnost 75%.
    """
    if not besedilo:
        return
    lock = ONI / "prevoz" / ".glas_lock"
    tmp = ONI / "prevoz" / ".tmp_glas.txt"

    # akaj dokler drug govor ne konca (max 15 s)
    for _ in range(30):
        if not lock.exists():
            break
        time.sleep(0.5)

    # e lok e vedno obstaja po 15 s, ga odstrani (morda je crkoval)
    if lock.exists():
        try:
            lock.unlink()
        except Exception:
            pass

    # ustvari lok in govorI
    try:
        lock.touch()
        tmp.write_text(besedilo[:600], encoding="utf-8-sig")
        ps = (
            "Add-Type -AssemblyName System.Speech; "
            "$t = Get-Content -Raw -Encoding UTF8 " + chr(39) + str(tmp).replace(chr(92), "/") + chr(39) + "; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Volume = 75; "
            "$s.Speak($t)"
        )
        # BLOKIRAJO e: ak dokler govor ne konca (ne Popen!)
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, timeout=30)
    except Exception:
        pass
    finally:
        try:
            lock.unlink(missing_ok=True)
        except Exception:
            pass
