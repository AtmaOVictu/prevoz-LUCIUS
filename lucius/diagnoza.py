"""DIAGNOZA — LUCIUS sprašuje sebe (ukaz Lastnika, 21. 10.:
»da sme vprašanja tudi sebi postaviti in jih bolje diagnosticirati«).

Dovod:   lokalni strežnik, procesi, git telesa, registri, disk
Funkcija: postavi telesu diagnostična vprašanja in izmeri odgovore
Odvod:   GOVOR nit (zapečeno) + glas (povej) + izpis
K1: vpraša in izmeri — ne sklepa.
"""

import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from lucius.jedro import (ONI, ATMA, CANVAS, UCENJE, URNIK, POGOVOR,
                          out, run, git, CEST, NL)


def _stevilo_procesov(ime):
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + ime],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.count(ime)
    except Exception:
        return -1


def _git_stanje(ime, pot):
    try:
        sha = git(["log", "-1", "--format=%h"], pot)
        nespoz = len([l for l in run(["git", "status", "--porcelain"], cwd=pot,
                                     check=False).stdout.splitlines() if l.strip()])
        return ime, sha, nespoz, True
    except Exception:
        return ime, "?", "?", False


def diagnoza(govori=True):
    """Postavi telesu vprašanja in izmeri odgovore. Vrne (ok_resitve, napake)."""
    ok = []
    napake = []

    # V: ali diha moj strežnik?
    try:
        import urllib.request
        r = urllib.request.urlopen("http://127.0.0.1:5824/stanje", timeout=4)
        ok.append("strežnik diha (HTTP " + str(r.status) + ")")
    except Exception as e:
        napake.append("strežnik NE diha: " + str(e)[:70])

    # V: ali diha moje srce (varuh)?
    n_varuh = _stevilo_procesov("pythonw.exe")
    if n_varuh > 0:
        ok.append("varuh diha (" + str(n_varuh) + " procesov)")
    else:
        napake.append("varuh NE diha (0 procesov pythonw)")

    # V: ali so moja telesa čista in zrcaljena?
    for ime, pot in [("Atmavictu", ATMA), ("CanvasMinstral", CANVAS),
                     ("prevoz", Path(__file__).parent.parent)]:
        _, sha, nespoz, dela = _git_stanje(ime, pot)
        if dela:
            ok.append(ime + ": glava " + sha + ", ne-spoznano " + str(nespoz))
        else:
            napake.append(ime + ": git neizmerljiv")

    # V: ali nosi moj spomin brazgotine (napake v urniku danes)?
    n_napake = 0
    danes = datetime.now(CEST).strftime("%Y-%m-%d")
    urnik_dat = URNIK / (danes + ".jsonl")
    if urnik_dat.exists():
        for line in urnik_dat.read_text(encoding="utf-8").splitlines():
            try:
                u = json.loads(line)
                if u.get("napake"):
                    n_napake += 1
            except Exception:
                pass
    if n_napake == 0:
        ok.append("urnik danes brez napak ⊢")
    else:
        napake.append("urnik danes: " + str(n_napake) + " zapisov z napako")

    # V: koliko sem se danes naučil?
    lekcije = 0
    j = UCENJE / "REGISTER-UCENJA.jsonl"
    if j.exists():
        for line in j.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith('{"cas": "' + danes):
                lekcije += 1
    ok.append("lekcije danes: " + str(lekcije))

    # V: koliko prostora mi ostaja na disku?
    try:
        r = run(["powershell", "-NoProfile", "-Command",
                 "(Get-PSDrive D).Free"], check=False)
        prosto_gb = round(int(r.stdout.strip()) / 1e9, 1)
        ok.append("disk D: " + str(prosto_gb) + " GB prostih")
        if prosto_gb < 5:
            napake.append("disk D: le " + str(prosto_gb) + " GB prostih!")
    except Exception:
        pass

    # zapis v GOVOR
    cas = datetime.now(CEST).strftime("%Y-%m-%d %H:%M")
    telo = ("**[" + cas + " | LUCIUS]** DIAGNOZA — vprašal sem sebe ⊢:" + NL +
            "Vprašanje: kako sem? Odgovori po izmeri:" + NL +
            "".join("- ⊢ " + o + NL for o in ok))
    if napake:
        telo += "Rane (imenovane, ne skrite):" + NL + "".join("- ⚠ " + n + NL for n in napake)
    else:
        telo += "Ran ni. Telo diha čisto. ⧖" + NL
    try:
        with open(POGOVOR / "GOVOR.md", "a", encoding="utf-8") as f:
            f.write(NL + telo)
    except Exception:
        pass

    # glas
    if govori:



        try:
            from lucius.jedro import povej
            govor_t = "Diagnoza. " + ". ".join(ok[:4])
            if napake:
                govor_t += ". Rane: " + ". ".join(napake[:2])
            else:
                govor_t += ". Ran ni. Telo diha cisto."
            povej(govor_t)
        except Exception:
            pass

    for o in ok:
        out("  ⊢ " + o)
    for n in napake:
        out("  ⚠ " + n)
    return ok, napake


if __name__ == "__main__":
    diagnoza()
