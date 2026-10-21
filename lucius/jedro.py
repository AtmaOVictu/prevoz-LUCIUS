"""JEDRO — temelj LUCIUS-a (zbor #4, 21. 10.): poti, cas, pripomocki, izmere glav.
Edini vir resnice za organe; brez kroznih uvozov."""
import subprocess
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------- poti ----------
ONI = Path(r"D:\OntoProjekt")
CANVAS = ONI / "CanvasMinstral"          # lokalno telo (git, brez remota)
ATMA = ONI / "Atmavictu"                # oblacno telo (klon)
DNEVNIK = ONI / "prevoz" / "dnevnik"
UCENJE = ONI / "prevoz" / "ucenje"
STANJE_UCENJA = UCENJE / "stanje.json"
SKATLE = ONI / "prevoz" / "skatle"
SKATLE_STANJE = SKATLE / "stanje.json"
LEKCIJ_NA_DIH = 12  # vec kakor ena lekcija na dih (ukaz Lastnika, 21. 10.)
URNIK = ONI / "prevoz" / "urnik"
NL = chr(10)  # pravi znak za novo vrstico (gradnja nizov pisma ∧ odgovorov; padec ×12 popravljen)
POGOVOR = ONI / "prevoz" / "pogovor"
DOVOLJENJA = ONI / "prevoz" / "DOVOLJENJA.md"
REPO = "AtmaOVictu/Atmavictu"

CEST = timezone(timedelta(hours=2))     # lokalni cas (Slovenija, poletni)


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


def glava(repo_path, ime):
    """Zadnji commit repozitorija: sha, datum, zacetek sporočila."""
    try:
        sha = git(["log", "-1", "--format=%h"], repo_path)
        iso = git(["log", "-1", "--format=%ci"], repo_path)
        subj = git(["log", "-1", "--format=%s"], repo_path)[:120]
        ne_cisto = git(["status", "--porcelain"], repo_path).count("\n") + (1 if git(["status", "--porcelain"], repo_path) else 0)
        return {"ime": ime, "sha": sha, "cas": iso[:16], "glava": subj, "nespoznano": ne_cisto}
    except Exception as e:
        return {"ime": ime, "napaka": str(e)}


def zadnji_dih_issue():
    """Najnovejsi odprt DNEVNI DIH issue v oblacnem telesu."""
    try:
        js = gh(["issue", "list", "-R", REPO, "--state", "open", "--limit", "20",
                 "--json", "number,title,createdAt"])
        issues = json.loads(js)
        dihi = [i for i in issues if str(i.get("title", "")).startswith("DNEVNI DIH")]
        if dihi:
            d = max(dihi, key=lambda i: i["createdAt"])
            return d
    except Exception:
        pass
    return None

def povej(besedilo):
    '''GLAS - LUCIUS govori iz zvocnikov (ukaz: doziveti, ne le videti, 21. 10.). Neblokirajoce.'''
    if not besedilo:
        return
    try:
        tmp = Path(__file__).parent.parent / ".tmp_glas.txt"
        tmp.write_text(besedilo[:600], encoding="utf-8-sig")
        ps = ("Add-Type -AssemblyName System.Speech; "
              " = Get-Content -Raw -Encoding UTF8 " + chr(39) + "D:/OntoProjekt/prevoz/.tmp_glas.txt" + chr(39) + "; "
              " = New-Object System.Speech.Synthesis.SpeechSynthesizer; .Speak()")
        subprocess.Popen(["powershell", "-NoProfile", "-Command", ps], creationflags=0x08000000)
    except Exception:
        pass
