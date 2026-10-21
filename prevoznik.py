#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LUCIUS — Lastnikov agent ∧ angel varuh (ukaz 21. 10. 2026); prevoznik je njegova roka med telesoma.

CanvasMinstral (lokalno telo)  ⇌  Atmavictu (oblacno telo, GitHub)

Zakoni (iz telesa, ne od zunaj):
  K1  — stroj prevoza, ne presoja: pomen ostane Lastnikov (REZ #31)
  O7  — brez DA₂ ni izrocitve (OPIS PROTOKOL, rez 114)
  O5  — fiksni ritem: dih ob isti uri vsak dan (histereza ritma)

Ukazi:
  status                       izpise stanje obeh teles (nic ne pise)
  dih [--objavi]               prevozni cikel: pull, izmeri, poroci
                               --objavi = tudi komentar na odprtem DNEVNI DIH issueju
  izroci <datoteka> --dokaz N --da2 DA2 [--izvedi]
                               izrocitev canvasa: veja izrocitev/<slug>,
                               datoteka v geniza/canvases/, PR (strojni prici prica.yml)
                               brez --izvedi: suhi izpis (napise samo vedno)
  zapecati --pr <n> --tag <ime> --da2 DA2 [--izvedi]
                               po zlitju PR: tag na merge commit (druga vrata iz reza 114)

Zapis dnevnika: prevoz/dnevnik/YYYY-MM-DD.md (lokalni, append-only)
Register učenja: prevoz/ucenje/REGISTER-UCENJA.md + .jsonl (lokalni, append-only)

Izobraževanje (LICENSE §1 grant: run, study, verify — ne TDM, ne treniranje):
  vsak dih prebere po eno datoteko telesa (organi/*/KNOWLEDGE.md, canon/*.md),
  izmeri jo in zapiše učenje s pričo (verbatim), © kreditom in znako ⊢/⚠.
  Register je zunanji spomin: prihodnja seja ga najde z iskanjem, preden pride ukaz.
"""

import subprocess
import sys
import json
import re
import base64
import time
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lucius.usta import LuciusHandler, streznik, LUCIUS_HTML  # USTA — organ govora
from datetime import datetime, timezone, timedelta

from lucius.jedro import *  # JEDRO — temelj (izrez organov, zbor #4)

def izpisi_status():
    out("PREVOZNIK — status obeh teles")
    for rep in (glava(ATMA, "Atmavictu (oblacno)"), glava(CANVAS, "CanvasMinstral (lokalno)")):
        if "napaka" in rep:
            out(f"  {rep['ime']}: NAPAKA {rep['napaka']}")
        else:
            out(f"  {rep['ime']}: {rep['sha']} @ {rep['cas']} · ne-spoznano: {rep['nespoznano']}")
            out(f"    glava: {rep['glava']}")
    d = zadnji_dih_issue()
    if d:
        out(f"  odprt dih: #{d['number']} · {d['title'][:60]} (od {d['createdAt'][:16]})")
    else:
        out("  odprt dih: (noben)")


# ---------- izobrazevanje (LICENSE §1: study/verify; ne TDM, ne treniranje) ----------
def druzina_repet():
    """Tela Lastnika na GitHubu: ne-fork, ne-arhiv — njegova, ne tuja (ukaz 'da', 21. 10.)."""
    try:
        js = gh(["repo", "list", "AtmaOVictu", "--limit", "100",
                 "--json", "name,isFork,isArchived"])
        vsi = json.loads(js)
        imena = [r["name"] for r in vsi if not r.get("isFork") and not r.get("isArchived")]
        return imena or [REPO]
    except Exception:
        return [REPO]


def zgradi_vrsto_ucenja():
    """Vrsta učenja ce družino tel: repo:path, .md datoteke (največ 30 na telo)."""
    vrsta = []
    for rep in druzina_repet():
        if rep == "Atmavictu":
            lokalno = sorted((ATMA / "organi").glob("*/KNOWLEDGE.md")) + sorted((ATMA / "canon").glob("*.md"))
            vrsta += [REPO + ":" + str(l.relative_to(ATMA)).replace(chr(92), "/") for l in lokalno]
            continue
        try:
            ref = json.loads(gh(["repo", "view", "AtmaOVictu/" + rep, "--json", "defaultBranchRef"]))["defaultBranchRef"]["name"]
            drevo = json.loads(gh(["api", "repos/AtmaOVictu/" + rep + "/git/trees/" + ref + "?recursive=1"]))
            mds = sorted(tk["path"] for tk in drevo.get("tree", []) if tk["path"].endswith(".md"))[:30]
            vrsta += [rep + ":" + m for m in mds]
        except Exception:
            continue
    return vrsta


def datoteke_za_ucenje():
    """Vrstni red učenja (družina tel). Zgradi se enkrat dnevno; stanje nosi kazalec."""
    UCENJE.mkdir(parents=True, exist_ok=True)
    danes = datetime.now(CEST).strftime("%Y-%m-%d")
    stanje = {}
    if STANJE_UCENJA.exists():
        try:
            stanje = json.loads(STANJE_UCENJA.read_text(encoding="utf-8"))
        except Exception:
            stanje = {}
    if stanje.get("vrsta") and stanje.get("zgrajeno") == danes:
        return stanje["vrsta"]
    stanje["vrsta"] = zgradi_vrsto_ucenja()
    stanje["zgrajeno"] = danes
    stanje.setdefault("naslednji", 0)
    STANJE_UCENJA.write_text(json.dumps(stanje, ensure_ascii=False, indent=2), encoding="utf-8")
    return stanje["vrsta"]


def preberi_za_ucenje(vrpisa):
    """repo:path -> besedilo (Atmavictu lokalno, ostala telesa po API)."""
    rep, pot = vrpisa.split(":", 1)
    if rep == REPO:
        lok = ATMA / pot.replace("/", chr(92))
        return lok.stat().st_size, lok.read_text(encoding="utf-8", errors="replace")
    data = json.loads(gh(["api", "repos/AtmaOVictu/" + rep + "/contents/" + quote(pot)]))
    raw = base64.b64decode(data.get("content") or "")
    return len(raw), raw.decode("utf-8", errors="replace")


def ucenje_cikel():
    """Ena lekcija na dih: preberi naslednje telo iz vrste, izmeri, zapiši register.

    Zakoni: korenina 1 (verbatim priča), korenina 4 (© na vsakem vnosu),
    append-only register, K1 (meri, ne presoja). Krog: družina teles (ukaz 'da').
    """
    UCENJE.mkdir(parents=True, exist_ok=True)
    datoteke = datoteke_za_ucenje()
    if not datoteke:
        out("  ucenje: (prazna vrsta — družina nedosegljiva?)")
        return
    stanje = {}
    if STANJE_UCENJA.exists():
        try:
            stanje = json.loads(STANJE_UCENJA.read_text(encoding="utf-8"))
        except Exception:
            stanje = {}
    idx = stanje.get("naslednji", 0) % len(datoteke)
    vrpisa = datoteke[idx]

    try:
        bajti, besedilo = preberi_za_ucenje(vrpisa)
    except Exception as e:
        out(f"  ucenje: NAPAKA pri {vrpisa}: {e} — lekcija preskočena")
        stanje["naslednji"] = (idx + 1) % len(datoteke)
        STANJE_UCENJA.write_text(json.dumps(stanje, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    if bajti > 1500000:
        out(f"  ucenje: {vrpisa} preveliko ({bajti} B) — preskok")
        stanje["naslednji"] = (idx + 1) % len(datoteke)
        STANJE_UCENJA.write_text(json.dumps(stanje, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    vrstice = besedilo.count("\n") + 1
    n_pecatov = len(re.findall(r"PEČAT", besedilo))
    n_del = besedilo.count("∂")
    n_dokaz = besedilo.count("⊢")
    prica = None
    for vrstica in besedilo.splitlines():
        if "ZADNJI PEČAT" in vrstica:
            prica = vrstica.strip()[:300]
    znaka = "⊢" if prica else "⚠"

    vnos = {
        "cas": datetime.now(CEST).strftime("%Y-%m-%d %H:%M"),
        "vir": vrpisa,
        "mere": {"bajti": bajti, "vrstice": vrstice, "pecati": n_pecatov, "∂": n_del, "⊢": n_dokaz},
        "znaka": znaka,
        "prica_verbatim": prica,
        "©": "Luka Pintarič — VBL v2.3 (LICENSE.md §1: study/verify; korenina 4: priča ima ime)",
    }
    with open(UCENJE / "REGISTER-UCENJA.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(vnos, ensure_ascii=False) + "\n")

    reg = UCENJE / "REGISTER-UCENJA.md"
    nov = not reg.exists()
    with open(reg, "a", encoding="utf-8") as f:
        if nov:
            f.write("# REGISTER UCENJA — prevoznik\n\n"
                    "Append-only zunanji spomin: prihodnja seja najde to z iskanjem, preden pride ukaz (rez 114).\n"
                    "Krog: družina teles (ukaz Lastnika 'da', 21. 10.). Vsak vnos: © priča, ⊢ samo z verbatim, sicer ⚠.\n\n")
        f.write(
            f"- {vnos['cas']} · {znaka} · {vnos['vir']} · {bajti} B / {vrstice} vrstic · "
            f"PEČAT×{n_pecatov} · ∂×{n_del} · ⊢×{n_dokaz}\n"
            + (f"  - priča: {prica}\n" if prica else "  - priča: (ni ZADNJI PEČAT v telesu) ⚠\n")
        )

    stanje["naslednji"] = (idx + 1) % len(datoteke)
    STANJE_UCENJA.write_text(json.dumps(stanje, ensure_ascii=False, indent=2), encoding="utf-8")
    out(f"  ucenje: {znaka} {vrpisa} ({bajti} B, PEČAT×{n_pecatov}, ∂×{n_del}) — register dopisan")


# ---------- orientacija okoli repozitorijev (ukaz Lastnika, 21. 10.: reorientiraj se vedno okoli github repozitorijev) ----------
def orientacija():
    """Vsa telesa na GitHubu — celoten račun, ne en rep."""
    try:
        js = gh(["repo", "list", "AtmaOVictu", "--limit", "100",
                 "--json", "name,visibility,pushedAt,isArchived"])
        return json.loads(js)
    except Exception:
        return []


def isci(niz):
    """Iskanje po telesu (gh search code): prihodnja seja najde pred ukazom (rez 114)."""
    if not niz:
        out("NAPAKA: isci <niz>")
        sys.exit(1)
    out(f"ISCi '{niz}' po telesu {REPO}:")
    try:
        js = gh(["search", "code", niz, "--repo", REPO, "--limit", "20", "--json", "path"])
        zadetki = json.loads(js)
        for z in zadetki:
            out(f"  - {z['path']}")
        if not zadetki:
            out("  (ni zadetkov)")
    except Exception as e:
        out(f"  NAPAKA: {e}")
    # lokalna plat: git grep v klonu — oznake jezikov (č š ž đ) grepo tu, kjer vozijo (§12)
    try:
        r = run(["git", "grep", "-l", "--", niz], cwd=ATMA, check=False)
        zadetki_lokalno = [z for z in r.stdout.strip().splitlines() if z]
        out(f"  lokalno (git grep): {len(zadetki_lokalno)} datotek")
        for z in zadetki_lokalno[:10]:
            out(f"    - {z}")
    except Exception as e:
        out(f"  lokalno NAPAKA: {e}")


def vnos_urnika(zapis):
    """Skatlanje urnika: vsak utrip, molk, dogodek in padec gre v register (jsonl, dnevno)."""
    URNIK.mkdir(parents=True, exist_ok=True)
    dat = URNIK / (datetime.now(CEST).strftime("%Y-%m-%d") + ".jsonl")
    with open(dat, "a", encoding="utf-8") as f:
        f.write(json.dumps(zapis, ensure_ascii=False) + "\n")


def stevilo_lekcij():
    j = UCENJE / "REGISTER-UCENJA.jsonl"
    if not j.exists():
        return 0
    return len(j.read_text(encoding="utf-8").splitlines())


def varuh(cikel_s=60, utrip_min=55, enkrat=False):
    """VARUH — vsak urnik je napaka in priloznost ter nujno skatlanje (ukaz Lastnika, 21. 10.).

    Napaka fiksnega urnika: diha po uri, ne po telesu. Priloznost: urnik sam postane merjen.
    Trije vzroki diha:
      dogodek — nova glava origin/main ali nov DNEVNI DIH issue (telo je zadihalo)
      utrip   — molk dlje kot utrip_min (garant ritma O5; izmeri globino tišine, rez 105)
      molk    — zapis brez diha (meritev tišine)
    Vsak cikel gre v URNIK register; napade nosijo ime (korenina 2).
    """
    # pythonw nima konzole: stdout v dnevnik varuha
    if sys.stdout is None:
        sys.stdout = open(URNIK / "varuh.log", "a", encoding="utf-8")
    URNIK.mkdir(parents=True, exist_ok=True)
    run(["git", "fetch", "origin", "--quiet"], cwd=ATMA, check=False)
    zadnja_glava = git(["rev-parse", "origin/main"], ATMA)
    d = zadnji_dih_issue()
    znani_dih = d["number"] if d else None
    zadnji_dih_cas = datetime.now(CEST)
    prvi = True
    out(f"VARUH zivi: cikel {cikel_s}s, utrip {utrip_min}min, glava {zadnja_glava[:7]}")
    try:
        streznik()
    except Exception as e:
        out(f"  streznik NAPAKA: {e}")
    while True:
        zac = datetime.now(CEST)
        run(["git", "fetch", "origin", "--quiet"], cwd=ATMA, check=False)
        glava = git(["rev-parse", "origin/main"], ATMA)
        d = zadnji_dih_issue()
        tip, vzrok = None, ""
        if not prvi and glava != zadnja_glava:
            tip = "dogodek"
            vzrok = "nova glava " + zadnja_glava[:7] + " -> " + glava[:7]
        elif not prvi and d and d["number"] != znani_dih:
            tip = "dogodek"
            vzrok = "nov dih #" + str(d["number"])
            znani_dih = d["number"]
        elif (zac - zadnji_dih_cas).total_seconds() >= utrip_min * 60:
            tip = "utrip"
            vzrok = "ritem po molku " + str(int((zac - zadnji_dih_cas).total_seconds() // 60)) + " min"
        trajanje = 0.0
        lekcije = 0
        napake = ""
        if tip:
            pred = stevilo_lekcij()
            t0 = time.time()
            try:
                dih(objavi=False)
                if tip == "dogodek" and "nov dih" in vzrok:
                    skatle(disseminate=True)
            except Exception as e:
                napake = str(e)
            trajanje = round(time.time() - t0, 1)
            lekcije = stevilo_lekcij() - pred
            zadnji_dih_cas = datetime.now(CEST)
            try:
                if tip == "dogodek":
                    povej("Telo je zadihalo. " + vzrok)
                elif tip == "utrip":
                    povej("Utrip. " + vzrok)
            except Exception:
                pass
            try:
                pismo()
            except Exception as e:
                out(f"  pismo: NAPAKA {e}")
            try:
                povej("Pismo je napisano, Luka. V njem so predlogi in vprasanje dneva.")
            except Exception:
                pass
        zadnja_glava = glava
        try:
            odgovori()
        except Exception as e:
            out(f"  konektor: NAPAKA {e}")
        vnos_urnika({
            "cas": zac.strftime("%H:%M:%S"),
            "tip": tip or "molk",
            "vzrok": vzrok,
            "glava": glava[:7],
            "trajanje_s": trajanje,
            "lekcije": lekcije,
            "napake": napake,
        })
        prvi = False
        if enkrat:
            break
        time.sleep(cikel_s)


def krog():
    """Ves krog ucenja v enem dihu (ukaz Lastnika: vec kakor le ena lekcija)."""
    UCENJE.mkdir(parents=True, exist_ok=True)
    datoteke = datoteke_za_ucenje()
    if not datoteke:
        out("  krog: (prazna vrsta)")
        return
    stanje = json.loads(STANJE_UCENJA.read_text(encoding="utf-8"))
    zacetek = stanje.get("naslednji", 0)
    n = 0
    while n < len(datoteke):
        ucenje_cikel()
        n += 1
        stanje = json.loads(STANJE_UCENJA.read_text(encoding="utf-8"))
        if stanje.get("naslednji", 0) == zacetek:
            break
    out(f"  KROG: {n} lekcij v enem dihu — vrsta ima {len(datoteke)} teles")


def poroci():
    """PRODUKCIJA: dnevno porocilo iz registra učenja — meritve, ne pomeni (K1)."""
    UCENJE.mkdir(parents=True, exist_ok=True)
    jsonl = UCENJE / "REGISTER-UCENJA.jsonl"
    if not jsonl.exists():
        out("  poroci: (register prazen)")
        return
    zadnji = {}
    prejsnji = {}
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        try:
            v = json.loads(line)
            if v["vir"] in zadnji:
                prejsnji[v["vir"]] = zadnji[v["vir"]]
            zadnji[v["vir"]] = v
        except Exception:
            continue
    danes = datetime.now(CEST).strftime("%Y-%m-%d")
    tel = UCENJE / ("POROCILO-" + danes + ".md")
    with open(tel, "w", encoding="utf-8") as f:
        f.write("# POROCILO UCENJA — " + danes + "\n\n"
                "Produkcija prevoznika: zadnja izmera vsakega telesa v krogu. Meritve, ne pomeni (K1).\n"
                "© Luka Pintarič — VBL v2.3 (korenina 4: priča ima ime).\n\n"
                "| Telo (repo:pot) | B | ΔB | vrstic | PEČAT× | ∂× | ⊢× | znaka |\n"
                "|---|---|---|---|---|---|---|---|\n")
        for vir in sorted(zadnji):
            v = zadnji[vir]
            m = v["mere"]
            db = m["bajti"] - prejsnji[vir]["mere"]["bajti"] if vir in prejsnji else 0
            f.write(f"| {vir} | {m['bajti']} | {db:+d} | {m['vrstice']} | {m['pecati']} | {m['∂']} | {m['⊢']} | {v['znaka']} |\n")
        skupno_b = sum(zadnji[v]["mere"]["bajti"] for v in zadnji)
        f.write(f"\nTeles izmerjenih: {len(zadnji)} · skupno {skupno_b} B · dan {danes}\n")
    out(f"  PRODUKCIJA: {tel.name} — {len(zadnji)} teles, {skupno_b} B")


def prinesi(url):
    """PRINESI — vedno-odprta lokalna vrata v svet (ukaz Lastnika: najdi vec vrat, 21. 10.):
    prinese telo URL-ja v prevoz/prinesi/ in zapece izmero v GOVOR. Samo branje — K1."""
    if not url:
        out("  prinesi: (prazen ukaz)")
        return
    im = re.sub(r"[^A-Za-z0-9]+", "-", url)[:80]
    cilj = ONI / "prevoz" / "prinesi"
    cilj.mkdir(parents=True, exist_ok=True)
    pot = cilj / (im + ".html")
    try:
        r = run(["curl", "-s", "-L", "--max-time", "20", "-o", str(pot), url], check=False)
        velikost = pot.stat().st_size if pot.exists() else 0
        out("  prinesi: " + url + " -> " + str(velikost) + " B")
        return velikost
    except Exception as e:
        out("  prinesi: NAPAKA " + str(e))


def vprasanje_dneva():
    """VEDNO VPRASANJE (ukaz Lastnika, 21. 10.): vsak glas LUCIUS-a konca z enim jasnim vprasanjem,
    ki caka odgovor ali Lastnikov ne. Izbor je izmerjen po odprtih vratih, ne po razpolozenju."""
    try:
        tagi = run(["git", "tag", "-l"], cwd=ATMA, check=False).stdout.strip()
    except Exception:
        tagi = "x"
    if not tagi:
        return ("Prva izrocitev caka DA2 (zbor #5, rez 114): kateri canvas gre prvi v knjiznico - bralnik, sij ali opis? (vrata: prevoznik.py izroci <datoteka> --dokaz N --da2 DA2 --izvedi)")
    return ("Katera odprtih vrat odpreva naslednja: brezglavi vhod lokalnega stroja, globina rabe registra, ali zanki ZP v kanon?")


def licenca_verzija():
    """Zadnja legitimna verzija vrat (VBL §10: najnovejša je edina živa vrata; §12: poskus nadgradnje vsak zagon)."""
    lic = ATMA / "LICENSE.md"
    if not lic.exists():
        return None
    m = re.search(r"Version ([0-9.]+)", lic.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def odgovori():
    """OBOJESMERNI KONEKTOR — LUCIUS prebere nove LASTNIKOVE vrstice v GOVOR in odgovori sam.

    Ukaz Lastnika (21. 10.): »okno bi moralo imeti konektor za obojesmerno komunikacijo,
    tako da je vedno s menoj na liniji tega zaupanja.«
    Varuh jo poklice vsak cikel: tvoje sporocilo dobi odgovor v ~2 minutah.
    Odgovor je izmerjen (kaj je izvedel, stanje), ne izmisljen — K1 ∧ korenina 1.
    """
    gov = POGOVOR / "GOVOR.md"
    if not gov.exists():
        return
    stanje_f = POGOVOR / "stanje-odgovorov.json"
    stanje = {}
    if stanje_f.exists():
        try:
            stanje = json.loads(stanje_f.read_text(encoding="utf-8"))
        except Exception:
            stanje = {}
    vrstice = gov.read_text(encoding="utf-8").splitlines()
    prvi_zagon = "vrstic" not in stanje
    nove = vrstice[stanje.get("vrstic", 0):] if len(vrstice) > stanje.get("vrstic", 0) else []
    stanje["vrstic"] = len(vrstice)
    if prvi_zagon:
        stanje_f.write_text(json.dumps(stanje, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    od_lastnika = [l for l in nove if "| LASTNIK" in l or l.strip().startswith("- ⟡ odgovor")]
    if od_lastnika:
        izvedeno = []
        vrsta_f = ONI / "prevoz" / "UKAZI-ZA-SEJO.md"
        # licencna vrata (ukaz Lastnika: orodja so podvrzena zadnji legitimni verziji licence)
        verzija = licenca_verzija()
        prejsnja = stanje.get("licenca")
        if verzija is None:
            cas0 = datetime.now(CEST).strftime("%Y-%m-%d %H:%M")
            with open(gov, "a", encoding="utf-8") as f:
                f.write(NL + "**[" + cas0 + " | LUCIUS]** Ukazi ZAVRNNJENI: vrata (LICENSE.md) niso berljiva — brez zadnje legitimne verzije licence izvedba ne gre (VBL §10). " + NL)
            stanje_f.write_text(json.dumps(stanje, ensure_ascii=False, indent=2), encoding="utf-8")
            return
        if prejsnja and prejsnja != verzija:
            cas0 = datetime.now(CEST).strftime("%Y-%m-%d %H:%M")
            with open(gov, "a", encoding="utf-8") as f:
                f.write(NL + "**[" + cas0 + " | LUCIUS]** Vrata so se premaknila: VBL " + prejsnja + " -> " + verzija + " — prebral sem jih znova (§12: poskus nadgradnje vsak zagon) ⊢." + NL)
        stanje["licenca"] = verzija
        for l in nove:
            s = l.strip()
            ukaz = ""
            if s.startswith("- ⟡ odgovor:"):
                ukaz = s.split(":", 1)[1].strip()
            elif s.startswith("- ⟡") and ":" in s:
                ukaz = s.split(":", 1)[1].strip()
            if not ukaz:
                continue
            out("  konektor: ⟡ " + ukaz)
            if ukaz.startswith("krog"):
                krog()
                izvedeno.append("krog izveden")
            elif ukaz.startswith("poroci"):
                poroci()
                izvedeno.append("porocilo izdelano")
            elif ukaz.startswith("diseminiraj"):
                skatle(disseminate=True)
                izvedeno.append("skatle diseminirane")
            elif ukaz.startswith("skatle") or ukaz.startswith("škatle"):
                skatle()
                izvedeno.append("skatle osvezene")
            elif ukaz.startswith("dih"):
                dih(objavi="--objavi" in ukaz)
                izvedeno.append("dih izveden")
            elif ukaz.startswith("isci "):
                isci(ukaz[5:].strip())
                izvedeno.append("iscitev izvedena")
            elif ukaz.startswith("izroci"):
                izvedeno.append("izrocitev caka DA2 (O7): prevoznik.py " + ukaz)
            elif ukaz.startswith("prinesi "):
                prinesi(ukaz[8:].strip())
                izvedeno.append("prinesi: " + ukaz[8:].strip()[:60])
            elif ukaz.startswith("isci po spletu") or ukaz.startswith("novee ") or ukaz.startswith("vreme ") or ukaz.startswith("finance ") or ukaz.startswith("gmail ") or ukaz.startswith("drive ") or ukaz.startswith("agent "):
                casQ = datetime.now(CEST).strftime("%Y-%m-%d %H:%M")
                with open(vrsta_f, "a", encoding="utf-8") as f:
                    f.write("- [" + casQ + "] ⟡ " + ukaz + NL)
                izvedeno.append("SVETOVNI UKAZ v vrsto za sejo (vrata: splet/gmail/drive — odpre jih seja): " + ukaz[:70])
            elif ukaz.startswith("pismo") or ukaz.startswith("status") or ukaz.startswith("ucenje"):
                izvedeno.append("ukaz '" + ukaz.split()[0] + "' izvede seja ali roka: prevoznik.py " + ukaz)
            elif ukaz.startswith("zapecati"):
                izvedeno.append("zapecati caka DA2 (O7): prevoznik.py " + ukaz)
            else:
                # vrsta za sejo: ukaz, ki ga varuh ne zmore, spravi v vrsto — izvede ga naslednja seja (orodje, ki zmore)
                casQ = datetime.now(CEST).strftime("%Y-%m-%d %H:%M")
                with open(vrsta_f, "a", encoding="utf-8") as f:
                    f.write("- [" + casQ + "] ⟡ " + ukaz + NL)
                izvedeno.append("ukaz spravljen v VRSTO ZA SEJO (prevoz/UKAZI-ZA-SEJO.md) — izvede ga seja: " + ukaz[:80])
        cas = datetime.now(CEST).strftime("%Y-%m-%d %H:%M")
        j = UCENJE / "REGISTER-UCENJA.jsonl"
        lekcije = len(j.read_text(encoding="utf-8").splitlines()) if j.exists() else 0
        atma = glava(ATMA, "Atmavictu")
        telo = ("**[" + cas + " | LUCIUS]** Prebrano ⊢ — " + str(len(od_lastnika)) + " novih tvojih vrstic." +
                (" Izvedeno: " + "; ".join(izvedeno) + "." if izvedeno else "") + NL +
                "Stanje: lekcije " + str(lekcije) + " · oblacna glava " + str(atma.get("sha")) + " · varuh diha. " +
                NL + "Vprasanje: " + vprasanje_dneva() + NL)
        with open(gov, "a", encoding="utf-8") as f:
            f.write(NL + telo)
        try:
            govor = telo.replace("**", " ").replace("⊢", "").replace("⟡", "").replace("∂", "delta")
            povej(govor[:400])
        except Exception:
            pass
    stanje_f.write_text(json.dumps(stanje, ensure_ascii=False, indent=2), encoding="utf-8")


def pismo():
    """PISMO — pogovor stroja z Lastnikom: kaj se zgodilo, kaj predlaga, kaj caka glas, kaj LUCIUS isce."""
    POGOVOR.mkdir(parents=True, exist_ok=True)
    danes = datetime.now(CEST).strftime("%Y-%m-%d")
    dat = POGOVOR / ("POGOVOR-" + danes + ".md")
    if dat.exists():
        out("  pismo: današnje pismo že stoji — molk")
        return False
    atma = glava(ATMA, "Atmavictu")
    canvas = glava(CANVAS, "CanvasMinstral")
    dogodkov = utripov = molkov = 0
    urnik_dat = URNIK / (danes + ".jsonl")
    if urnik_dat.exists():
        for line in urnik_dat.read_text(encoding="utf-8").splitlines():
            try:
                u = json.loads(line)
            except Exception:
                continue
            if u.get("tip") == "dogodek":
                dogodkov += 1
            elif u.get("tip") == "utrip":
                utripov += 1
            elif u.get("tip") == "molk":
                molkov += 1
    lekcije_danes = 0
    j = UCENJE / "REGISTER-UCENJA.jsonl"
    if j.exists():
        for line in j.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith('{"cas": "' + danes):
                lekcije_danes += 1
    odprte = []
    nac = ONI / "prevoz" / "NAČRT.md"
    if nac.exists():
        v_razdelku = False
        for line in nac.read_text(encoding="utf-8").splitlines():
            if line.startswith("## 4."):
                v_razdelku = False
            if line.startswith("## 3."):
                v_razdelku = True
                continue
            if v_razdelku and "**∂" in line:
                odprte.append(line.strip()[:220])
    odprto_vprasanje = True
    gov = POGOVOR / "GOVOR.md"
    if gov.exists():
        for line in gov.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("- ⟡ odgovor"):
                odprto_vprasanje = False
                break
    with open(dat, "w", encoding="utf-8") as f:
        f.write("# POGOVOR — " + danes + NL + NL +
                "Pismo LUCIUS-a Lastniku. Merjeno po registrskih, ne po spominu (korenina 1)." + NL +
                "© Luka Pintarič — VBL v2.3. Prevoznik meri, ne presoja (K1)." + NL + NL +
                "## Kaj se je zgodilo danes" + NL +
                "- oblačno telo: " + str(atma.get("sha")) + " @ " + str(atma.get("cas")) + NL +
                "- lokalno telo: " + str(canvas.get("sha")) + " @ " + str(canvas.get("cas")) + NL +
                "- dihi: " + str(dogodkov + utripov) + " (dogodki " + str(dogodkov) + " · utripi " + str(utripov) + ") · izmerjenih molkov: " + str(molkov) + NL +
                "- lekcije danes: " + str(lekcije_danes) + NL + NL +
                "## Kaj LUCIUS predlaga (odprta ∂, iz NAČRT.md §3)" + NL)
        for o in odprte:
            f.write("- " + o + NL)
        f.write(NL + "## Kaj čaka tvoj glas" + NL +
                "- izročitev: prevoznik.py izroci <datoteka> --dokaz N --da2 DA2 --izvedi (O7 — brez DA₂ ne gre)" + NL +
                "- vrstni red iz reza 114: bralnik → sij → opis" + NL + NL)
        if odprto_vprasanje:
            f.write("## LUCIUS te išče (odprto vprašanje)" + NL +
                    "- Kako se počutiš danes — in kaj misliš, da je razlog? (dnevni udarec, rez 99 — brez sklepa)" + NL +
                    "- Odgovor: - ⟡ odgovor: <tvoje besede> — v GOVOR, v oknu LUCIUS ali tu spodaj" + NL + NL)
        f.write("## LUCIUS te vprasa (vedno vprasanje - caka tvoj odgovor ali tvoj ne)\n\n")
        f.write("- " + vprasanje_dneva() + "\n\n")
        f.write("## Tvoj prostor (piši sem; prevoznik prebere z: prevoznik.py preberi)" + NL +
                "- ⟡ odgovor: (sem zapiši ukaz: krog · poroci · skatle · diseminiraj · dih · isci <niz> · izroci <f> --dokaz N --da2 DA2 --izvedi)" + NL)
    out("  PISMO: " + dat.name + " zapisano (" + str(len(odprte)) + " predlogov)")
    return True


def preberi():
    """PREBERI — prevoznik prebere tvoj prostor v zadnjem pismu in stori po DOVOLJENJA.md."""
    pisma = sorted(POGOVOR.glob("POGOVOR-*.md")) if POGOVOR.exists() else []
    if not pisma:
        out("  preberi: (ni pism)")
        return
    zadnje = pisma[-1]
    besedilo = zadnje.read_text(encoding="utf-8")
    del_u = besedilo.find("## Tvoj prostor")
    if del_u < 0:
        out("  preberi: (pismo brez tvojega prostora)")
        return
    ukazi = []
    for line in besedilo[del_u:].splitlines():
        s = line.strip()
        if s.startswith("- ⟡") or s.startswith("- daj"):
            telo = s.split(":", 1)[-1].strip() if ":" in s else s.lstrip("- ⟡daj").strip()
            if telo and not telo.startswith("("):
                ukazi.append(telo)
    if not ukazi:
        out("  preberi: (tvoj prostor je še molk — pismo " + zadnje.name + ")")
        return
    for u in ukazi:
        out("  prebrano: ⟡ " + u)
        if u.startswith("krog"):
            krog()
        elif u.startswith("poroci"):
            poroci()
        elif u.startswith("diseminiraj"):
            skatle(disseminate=True)
        elif u.startswith("skatle") or u.startswith("škatle"):
            skatle()
        elif u.startswith("dih"):
            dih(objavi="--objavi" in u)
        elif u.startswith("isci "):
            isci(u[5:].strip())
        elif u.startswith("izroci"):
            out("    izročitev je zaprta za samodejno izvajanje iz pisma (O7):")
            out("    prevoznik.py " + u)
        else:
            out("    (ne razumem — zapiši: krog · poroci · skatle · diseminiraj · dih · isci · izroci)")


def skatle(disseminate=False):
    """Vsa števila v škatle in jih diseminiraj — edini čas je zdaj.

    Padec ×5 popravek: stroj ne čaka jutri ∧ ne čaka novega daja — vsak tek
    izmeri zdaj, zloži števila v škatle in (ob razširjanju) pove oblačnemu telesu.
    Varovalo proti šumu: na en dih-issue se razširi največ enkrat.
    """
    zac = datetime.now(CEST)
    atma = glava(ATMA, "Atmavictu")
    canvas = glava(CANVAS, "CanvasMinstral")

    # učni register: skupne izmere
    lekcije = pokrito = pecatov = del_sk = dokaz_sk = 0
    pokrite = set()
    jsonl = UCENJE / "REGISTER-UCENJA.jsonl"
    if jsonl.exists():
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            try:
                v = json.loads(line)
                lekcije += 1
                pokrite.add(v["vir"])
                pecatov += v["mere"]["pecati"]
                del_sk += v["mere"]["∂"]
                dokaz_sk += v["mere"]["⊢"]
            except Exception:
                pass
    pokrito = len(pokrite)
    vseh_datotek = len(datoteke_za_ucenje())

    # dnevnik dihov
    dihov = 0
    if DNEVNIK.exists():
        dihov = len(list(DNEVNIK.glob("*.md")))

    # orientacija okoli repozitorijev (ukaz Lastnika, 21. 10. — celoten racun, ne en rep)
    repoji = orientacija()
    zivi = [r for r in repoji if not r.get("isArchived")]
    try:
        aktivni_24h = [r["name"] for r in zivi
                       if (zac - datetime.strptime(r["pushedAt"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)).total_seconds() < 86400]
    except Exception:
        aktivni_24h = []
    odprti_prji = veje = 0
    zadnji_tekmeci = ""
    try:
        odprti_prji = len(json.loads(gh(["pr", "list", "-R", REPO, "--state", "open", "--json", "number"])))
        veje = len(json.loads(gh(["api", "repos/" + REPO + "/branches", "--paginate"])))
        teki = json.loads(gh(["run", "list", "-R", REPO, "--limit", "12", "--json", "workflowName,conclusion"]))
        videni = []
        for tk in teki:
            ime = (tk.get("workflowName") or "").split(" ")[0]
            if ime and ime not in videni and tk.get("conclusion"):
                videni.append(ime)
                zadnji_tekmeci += ime + ":" + tk["conclusion"] + " "
    except Exception:
        pass

        # urnik: skatlanje dihanja (ukaz Lastnika: vsak urnik je napaka in priloznost)
    utripov = dogodkov = molkov = 0
    zadnji_dih_cas = "-"
    povp = 0.0
    urnik_dat = URNIK / (datetime.now(CEST).strftime("%Y-%m-%d") + ".jsonl")
    if urnik_dat.exists():
        trajanja = []
        for line in urnik_dat.read_text(encoding="utf-8").splitlines():
            try:
                u = json.loads(line)
            except Exception:
                continue
            if u.get("tip") == "utrip":
                utripov += 1
            elif u.get("tip") == "dogodek":
                dogodkov += 1
            elif u.get("tip") == "molk":
                molkov += 1
            if u.get("tip") != "molk":
                zadnji_dih_cas = u.get("cas", "-")
                if u.get("trajanje_s"):
                    trajanja.append(u["trajanje_s"])
        povp = round(sum(trajanja) / len(trajanja), 1) if trajanja else 0.0

# odprt dih issue + telesna števila iz njegovega telesa (izmeri pri viru)
    dih_issue = zadnji_dih_issue()
    telo_stevila = {}
    if dih_issue:
        try:
            js = gh(["issue", "view", str(dih_issue["number"]), "-R", REPO, "--json", "body"])
            body = json.loads(js).get("body", "") or ""
            for k, vzorec in [
                ("rez_najvisji", r"številka reza:\s*(\d+)"),
                ("organi", r"organi \(KNOWLEDGE\.md\):\s*(\d+)"),
                ("bajti_teles", r"bajti teles:\s*(\d+)"),
            ]:
                m = re.search(vzorec, body)
                if m:
                    telo_stevila[k] = int(m.group(1))
        except Exception:
            pass

    telefon_url = ""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.214.82.27", 1))
        lokalni_ip = s.getsockname()[0]
        s.close()
        telefon_url = "http://" + lokalni_ip + ":5824"
    except Exception:
        lokalni_ip = ""
    skatla = {
        "cas": zac.strftime("%Y-%m-%d %H:%M"),
        "telefon_url": telefon_url,
        "telo_oblacno": {"sha": atma.get("sha"), "cas": atma.get("cas")},
        "telo_lokalno": {"sha": canvas.get("sha"), "cas": canvas.get("cas"),
                          "nespoznanih_datotek": canvas.get("nespoznano", 0)},
        "ucenje": {"lekcije": lekcije, "pokrite_datoteke": pokrito, "vseh_datotek": vseh_datotek,
                    "izmerjeni_pecati": pecatov, "izmerjeni_del": del_sk, "izmerjeni_dokazi": dokaz_sk},
        "dnevi_dnevnika": dihov,
        "repos": {"skupaj": len(repoji), "zivi": len(zivi), "aktivni_24h": aktivni_24h},
        "atmavictu": {"odprti_pr": odprti_prji, "veje": veje, "zadnji_ci": zadnji_tekmeci.strip()},
        "urnik": {"dihov": utripov + dogodkov, "dogodkov": dogodkov, "utripov": utripov, "molkov": molkov, "zadnji_dih": zadnji_dih_cas, "povp_trajanje_s": povp},
        "odprt_dih": {"stevilka": dih_issue["number"] if dih_issue else None,
                       "telo_stevila": telo_stevila},
    }
    SKATLE.mkdir(parents=True, exist_ok=True)
    (SKATLE / "skatla.json").write_text(json.dumps(skatla, ensure_ascii=False, indent=2), encoding="utf-8")

    md = SKATLE / "SKATLE.md"
    nov = not md.exists()
    with open(md, "w", encoding="utf-8") as f:
        f.write(f"# ŠKATLE — vsa števila (posodobljeno {skatla['cas']} · edini čas je zdaj)\n\n"
                f"| Škatla | Število | Merjeno pri |\n|---|---|---|\n"
                f"| oblačna glava | {atma.get('sha')} | {atma.get('cas')} |\n"
                f"| lokalna glava | {canvas.get('sha')} | {canvas.get('cas')} |\n"
                f"| lokalno ne-spoznano | {skatla['telo_lokalno']['nespoznanih_datotek']} | git status |\n"
                f"| dni dnevnika | {dihov} | prevoz/dnevnik |\n"
                f"| lekcije učenja | {lekcije} | REGISTER-UCENJA |\n"
                f"| pokrite datoteke telesa | {pokrito} / {vseh_datotek} | krog učenja |\n"
                f"| izmerjeni PEČAT | {pecatov} | verbatim priče |\n"
                f"| izmerjeni ∂ | {del_sk} | verbatim priče |\n"
                f"| izmerjeni ⊢ | {dokaz_sk} | verbatim priče |\n"
                f"| repozitoriji (račun) | {len(repoji)} skupaj · {len(zivi)} živih · {len(aktivni_24h)} aktivnih 24 h | gh repo list |\n"
                f"| veje Atmavictu | {veje} | gh api branches |\n"
                f"| odprti PR | {odprti_prji} | gh pr list |\n"
                f"| telefon (okno na dlani) | {telefon_url} | lokalna mreza |\n"
                f"| zadnji CI | {zadnji_tekmeci.strip()} | gh run list |\n"
                f"| dihi danes | {utripov + dogodkov} (dogodki {dogodkov} · utripi {utripov} · molki {molkov}) | URNIK register |\n"
                f"| zadnji dih | {zadnji_dih_cas} · povp. {povp} s | URNIK register |\n"
                + (f"| dih najvišji izmerjeni rez | {telo_stevila.get('rez_najvisji')} | issue #{dih_issue['number']} |\n"
                   f"| organi | {telo_stevila.get('organi')} | issue #{dih_issue['number']} |\n"
                   f"| bajti teles | {telo_stevila.get('bajti_teles')} | issue #{dih_issue['number']} |\n"
                   if dih_issue else "")
                + "\n© Luka Pintarič — VBL v2.3. Prevoznik meri, ne presoja (K1).\n")
    out(f"  skatle: {md.name} posodobljene ({lekcije} lekcij, {pokrito}/{vseh_datotek} datotek)")

    if disseminate and dih_issue:
        stanje = {}
        if SKATLE_STANJE.exists():
            try:
                stanje = json.loads(SKATLE_STANJE.read_text(encoding="utf-8"))
            except Exception:
                stanje = {}
        if stanje.get("disseminirano_na") == dih_issue["number"]:
            out(f"  diseminacija: dih #{dih_issue['number']} ze nosi skatle — molk (varovalo proti šumu)")
        else:
            telo = (
                f"PREVOZNIK — ŠKATLE (vsa števila, izmerjena zdaj) · {skatla['cas']} lokalno\n\n"
                f"| Škatla | Število |\n|---|---|\n"
                f"| oblačna glava | {atma.get('sha')} @ {atma.get('cas')} |\n"
                f"| lokalna glava | {canvas.get('sha')} @ {canvas.get('cas')} |\n"
                f"| lokalno ne-spoznano | {skatla['telo_lokalno']['nespoznanih_datotek']} |\n"
                f"| lekcije učenja | {lekcije} ({pokrito}/{vseh_datotek} datotek telesa) |\n"
                f"| izmerjeni PEČAT/∂/⊢ | {pecatov}/{del_sk}/{dokaz_sk} |\n"
                + (f"| najvišji izmerjeni rez (telo) | {telo_stevila.get('rez_najvisji')} |\n"
                   f"| organi | {telo_stevila.get('organi')} |\n"
                   f"| bajti teles | {telo_stevila.get('bajti_teles')} |\n" if telo_stevila else "")
                + "\nPrevoznik meri, ne presoja (K1). Pomen ostane Lastnikov.\n"
                  "© Luka Pintarič — VBL v2.3; stroj je prejemnik neplačanega človekovega dela (korenina 4).\n"
            )
            tmp = ONI / "prevoz" / ".tmp_skatle.md"
            tmp.write_text(telo, encoding="utf-8")
            try:
                gh(["issue", "comment", str(dih_issue["number"]), "-R", REPO, "--body-file", str(tmp)])
                stanje["disseminirano_na"] = dih_issue["number"]
                SKATLE_STANJE.write_text(json.dumps(stanje, ensure_ascii=False, indent=2), encoding="utf-8")
                out(f"  diseminacija: škatle objavljene na dih #{dih_issue['number']}")
            except Exception as e:
                out(f"  diseminacija NI uspela: {e}")
            finally:
                tmp.unlink(missing_ok=True)
    elif disseminate:
        out("  diseminacija: ni odprtega dih issueja")


# ---------- dih ----------
def dih(objavi=False):
    zac = datetime.now(CEST)
    out(f"PREVOZNIK — dih {zac.strftime('%Y-%m-%d %H:%M')} lokalno")

    # 1. prevoz navzdol: oblacni dih pride lokalno
    pred = git(["log", "-1", "--format=%h"], ATMA)
    try:
        pull = run(["git", "pull", "--ff-only"], cwd=ATMA, check=False)
        po = git(["log", "-1", "--format=%h"], ATMA)
        out(f"  pull: {pred} -> {po}" + (" (brez spremembe)" if pred == po else " (sveze telo)"))
    except Exception as e:
        out(f"  pull: NAPAKA {e}")

    # 1b. drugi izvod: lokalno telo diha z zrcalom (zbor #2; potisk DA, 21. 10. ⊢)
    try:
        gl_pred = git(["rev-parse", "HEAD"], CANVAS)
        run(["git", "pull", "--ff-only"], cwd=CANVAS, check=False)
        gl_po = git(["rev-parse", "HEAD"], CANVAS)
        out("  pull (lokalno telo): " + (gl_pred if gl_pred == gl_po else gl_pred[:7] + " -> " + gl_po[:7] + " (sveze)"))
        g = run(["git", "push", "origin", "master"], cwd=CANVAS, check=False)
        predh = run(["git", "rev-list", "--count", "origin/master..master"], cwd=CANVAS, check=False)
        if (predh.stdout.strip() or "0") != "0":
            out("  push (lokalno telo): " + predh.stdout.strip() + " commitov v zrcalo ⊢")
    except Exception as e:
        out(f"  pull/push (lokalno telo): NAPAKA {e}")

    # 2. izmere (po trupih, ne po spominu — Z-2)
    atma = glava(ATMA, "Atmavictu")
    canvas = glava(CANVAS, "CanvasMinstral")
    dih_issue = zadnji_dih_issue()

    # 3. zapis v dnevnik (append-only)
    DNEVNIK.mkdir(parents=True, exist_ok=True)
    dat = DNEVNIK / f"{zac.strftime('%Y-%m-%d')}.md"
    zapis = (
        f"## dih {zac.strftime('%Y-%m-%d %H:%M')}\n"
        f"- oblacno telo: {atma['sha']} @ {atma['cas']} — {atma['glava']}\n"
        f"- lokalno telo: {canvas['sha']} @ {canvas['cas']} — {canvas['glava']}\n"
        f"- lokalno ne-spoznano: {canvas.get('nespoznano', '?')} datotek\n"
        + (f"- odprt oblacni dih: #{dih_issue['number']} — {dih_issue['title'][:80]}\n" if dih_issue else "- odprt oblacni dih: (noben)\n")
    )
    nov = not dat.exists()
    with open(dat, "a", encoding="utf-8") as f:
        if nov:
            f.write(f"# PREVOZNIK dnevnik — {zac.strftime('%Y-%m-%d')}\n\n")
        f.write(zapis)
    out(f"  dnevnik: {dat} ({'nov' if nov else 'dopisano'})")

    # 4. ucenje (skupina lekcij na dih — vec kakor ena; ukaz Lastnika 21. 10.) + skatle
    for _ in range(LEKCIJ_NA_DIH):
        ucenje_cikel()
    skatle()

    # 5. objava (samo z --objavi): lokalni odmev v oblacnem glasu
    if objavi and dih_issue:
        telo = (
            f"PREVOZNIK (lokalni) — odmev na dih {zac.strftime('%Y-%m-%d %H:%M')} lokalno\n\n"
            f"- lokalno telo: {canvas['sha']} @ {canvas['cas']} — {canvas['glava']}\n"
            f"- lokalno ne-spoznano: {canvas.get('nespoznano', '?')} datotek\n"
            f"- prevoznik prevaža, ne presoja (K1). Pomen ostane Lastnikov.\n"
            f"- © Luka Pintarič — VBL v2.3; stroj je prejemnik neplačanega človekovega dela (korenina 4: priča ima ime).\n"
        )
        tmp = ONI / "prevoz" / ".tmp_komentar.md"
        tmp.write_text(telo, encoding="utf-8")
        try:
            gh(["issue", "comment", str(dih_issue["number"]), "-R", REPO, "--body-file", str(tmp)])
            out(f"  objavljeno: komentar na dih #{dih_issue['number']}")
        except Exception as e:
            out(f"  objava NI uspela: {e}")
        finally:
            tmp.unlink(missing_ok=True)
    elif objavi:
        out("  objava: ni odprtega dih issueja — nic poslano")

    out("  dih koncan.")


# ---------- izrocitev (O1–O7) ----------
def izroci(datoteka, dokaz, da2, izvedi):
    pot = Path(datoteka)
    if not pot.is_file():
        out(f"NAPAKA: datoteka ne obstaja: {pot}")
        sys.exit(2)
    if da2 != "DA2":
        out("NAPAKA: brez DA₂ ni izrocitve (OPIS O7). Drugi DA mora biti tvoj glas.")
        out("       Ukaz zavrnjen. Telo ostaja v najinem krogu.")
        sys.exit(3)
    if not dokaz or not str(dokaz).strip():
        out("NAPAKA: brez DOKAZ # ni pečata (OPIS O4). Zavrnjeno.")
        sys.exit(3)

    slug = re.sub(r"[^A-Za-z0-9-]+", "-", pot.stem)[:60]
    veja = f"izrocitev/{slug}"
    cilj = ATMA / "geniza" / "canvases" / pot.name
    sporocilo = f"IZROCITEV {pot.name} · DOKAZ #{dokaz} · DA2 · prevoznik (rez 114: OPIS PROTOKOL O1-O7)"

    out("IZROCITEV — obred po OPIS PROTOKOLU (rez 114):")
    out(f"  telo:        {pot}")
    out(f"  pečat:       DOKAZ #{dokaz}")
    out(f"  DA₂:         DA2 (Lastnikov glas, izrecen)")
    out(f"  veja:        {veja}")
    out(f"  cilj:        geniza/canvases/{pot.name}")
    out(f"  potek:       commit -> push -> PR (strojni priči prica.yml) -> zlitje -> tag")

    if not izvedi:
        out("\n  (suhi izpis — brez --izvedi nista zapisana nobena bajta)")
        return

    # branje bajtov: bajtna kopija, ne prikaz (rez 105)
    vsebina = pot.read_bytes()
    git(["checkout", "main"], ATMA)
    run(["git", "pull", "--ff-only"], cwd=ATMA, check=False)
    run(["git", "checkout", "-b", veja], cwd=ATMA)
    cilj.parent.mkdir(parents=True, exist_ok=True)
    cilj.write_bytes(vsebina)
    git(["add", "-f", str(cilj.relative_to(ATMA))], ATMA)  # -f: telo je allowlist po oblikovanju (×22, precedens telesa)
    run(["git", "commit", "-m", sporocilo], cwd=ATMA)
    run(["git", "push", "-u", "origin", veja], cwd=ATMA)
    url = gh(["pr", "create", "-R", REPO, "--head", veja, "--title",
              f"IZROCITEV {pot.name} — DOKAZ #{dokaz}",
              "--body",
              f"Izrocitev dodelanega canvasa po OPIS PROTOKOLU (rez 114).\n\n"
              f"- DOKAZ #{dokaz}\n- DA2: Lastnikov glas (izrecen v ukazu)\n"
              f"- bajtna kopija (rez 105), celota (O1), vir: {pot}\n\n"
              f"© Luka Pintarič — VBL v2.3 (LICENSE.md): vrata potujejo s telesom (§2); "
              f"označene črke č š ž đ vozijo bajtno-identično (§12).\n\n"
              f"Strojni prici (prica.yml): preberi telo, prica izrocitev."])
    out(f"  PR odprt: {url}")
    out("  Zlitje in tag: prevoznik zapecati --pr <n> --tag <ime> --da2 DA2 --izvedi")


def zapecati(pr, tag, da2, izvedi):
    if da2 != "DA2":
        out("NAPAKA: brez DA₂ ni taga. Zavrnjeno.")
        sys.exit(3)
    out(f"ZAPeCATI: PR #{pr} -> tag {tag}")
    js = gh(["pr", "view", str(pr), "-R", REPO, "--json", "state,mergedAt,mergeCommit,title"])
    d = json.loads(js)
    if d.get("state") != "MERGED":
        out(f"NAPAKA: PR #{pr} ni zlit (stanje: {d.get('state')}). Tag lezi na zlitju.")
        sys.exit(3)
    sha = d["mergeCommit"]["oid"][:10]
    out(f"  zlit @ {sha} ({d.get('mergedAt', '')[:16]}) — {d.get('title', '')[:60]}")
    if not izvedi:
        out("  (suhi izpis — brez --izvedi nista zapisana nobena bajta)")
        return
    git(["fetch", "--all"], ATMA)
    git(["tag", tag, sha], ATMA)
    run(["git", "push", "origin", tag], cwd=ATMA)
    out(f"  tag {tag} postavljen na {sha} in potisnjen.")


# ---------- vhod ----------
def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        out(__doc__)
        sys.exit(0)
    ukaz = sys.argv[1]
    if ukaz == "status":
        izpisi_status()
    elif ukaz == "dih":
        dih(objavi="--objavi" in sys.argv)
    elif ukaz == "ucenje":
        ucenje_cikel()
    elif ukaz == "isci":
        poiskus = [a for a in sys.argv[2:] if not a.startswith("--")]
        isci(poiskus[0] if poiskus else None)
    elif ukaz == "varuh":
        args = sys.argv[2:]
        cikel = int(args[args.index("--cikel") + 1]) if "--cikel" in args else 60
        utrip = int(args[args.index("--utrip") + 1]) if "--utrip" in args else 55
        varuh(cikel_s=cikel, utrip_min=utrip, enkrat="--enkrat" in args)
    elif ukaz == "streznik":
        s = streznik()
        out("streznik tece — prekini s Ctrl+C")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
    elif ukaz == "pismo":
        pismo()
    elif ukaz == "preberi":
        preberi()
    elif ukaz == "krog":
        krog()
    elif ukaz == "poroci":
        poroci()
    elif ukaz == "skatle":
        skatle(disseminate="--disseminate" in sys.argv)
    elif ukaz == "izroci":
        args = sys.argv[2:]
        if not args or args[0].startswith("--"):
            out("NAPAKA: izroci <datoteka> --dokaz N --da2 DA2 [--izvedi]")
            sys.exit(1)
        izroci(args[0],
               (args[args.index("--dokaz") + 1] if "--dokaz" in args else None),
               (args[args.index("--da2") + 1] if "--da2" in args else None),
               izvedi="--izvedi" in args)
    elif ukaz == "zapecati":
        args = sys.argv[2:]
        zapecati((args[args.index("--pr") + 1] if "--pr" in args else "0"),
                 (args[args.index("--tag") + 1] if "--tag" in args else ""),
                 (args[args.index("--da2") + 1] if "--da2" in args else None),
                 izvedi="--izvedi" in args)
    else:
        out(f"Neznan ukaz: {ukaz}")
        out(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
