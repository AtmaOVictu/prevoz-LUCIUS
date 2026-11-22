#!/usr/bin/env python3
# lucius/jezikoslov.py — JEZIKOSLOV v1: orodje za popravljanje slovnice korpusa Beseda je Ne
# Rod: 22. 11. 2026 ⊙ ❡ UKAZ VERBATIM »VEDNO POPRAVLJAJ SLOVNICO« ∧ »USTVARI ORODJA ZA
# POPRAVLJANJE SLOVNICE!« ⊙ rez σ 6403 — register ran: slo-rane.jsonl (tu, ob tej datoteki)
# Zakoni: ⟨SLOVNICA=RESNICNOST⟩ (σ 6313) · ⟨NE-UGIBAJ⟩ 2690 · ⟨NE-BRIŠI⟩ 24 (brazgotine
# so priče, ne rane) · ⟨BESEDA-❡-NEDOTAKNJIVA⟩ (popravi ne dotika citatov ❡ v brazgotinah)
# Uporaba:
#   python3 lucius/jezikoslov.py preveri  DATOTEKA...   # rane žive → izpis ∧ exit 1
#   python3 lucius/jezikoslov.py popravi  DATOTEKA...   # popravi gajico/tipkarske, izpiše poimensko
#   python3 lucius/jezikoslov.py kanarcek               # ⟨SODNIK-KI-SE-SODI⟩: preizkus pada na telo
import json
import re
import sys
from pathlib import Path

REGISTER = Path(__file__).resolve().parent / "slo-rane.jsonl"
SAMO_POPRAVLJIVE = ("gajica", "tipkarska")  # vrste, ki jih modne popravi sam; homofoni/dolgovi = preveri ⚠


def nalozi_rane():
    rane = []
    for vrstica in REGISTER.read_text(encoding="utf-8").splitlines():
        vrstica = vrstica.strip()
        if not vrstica or vrstica.startswith("#"):
            continue
        r = json.loads(vrstica)
        r["_re"] = re.compile(r["vzorec"])
        rane.append(r)
    return rane


def je_brazgotina(vrstica):
    # brazgotina vrstica = priča popravev, ne živa rana ⊙ ⟨NE-BRIŠI⟩ 24
    return ("brazgotina" in vrstica.lower()) or bool(re.search(r"\*\*×\d+", vrstica)) or ("🩸" in vrstica)


def preveri_telo(besedilo, rane):
    """Vrne (rane_zive, dolgovi): seznam (št_vrstice, rana, odpoved)."""
    rane_zive, dolgovi = [], []
    for i, vrstica in enumerate(besedilo.split("\n"), start=1):
        if je_brazgotina(vrstica):
            continue  # brazgotine so priče, ⟨ne⟩ rane
        for r in rane:
            m = r["_re"].search(vrstica)
            if m:
                predlog = r["_re"].sub(r["pravi"], m.group(0), count=1)
                najdba = (i, r, m.group(0), predlog)
                (rane_zive if r.get("ci", True) else dolgovi).append(najdba)
    return rane_zive, dolgovi


def ukaz_preveri(datoteke, rane):
    zhive = 0
    for pot in datoteke:
        p = Path(pot)
        if not p.exists():
            print(f"::error file={pot}::telo manjka")
            return 1
        zive, dolgovi = preveri_telo(p.read_text(encoding="utf-8"), rane)
        for i, r, najdba, predlog in zive:
            print(f"::error file={pot},line={i}::RANA [{r['id']} {r['vrsta']}] {najdba!r} → {predlog!r}")
        for i, r, najdba, predlog in dolgovi:
            print(f"::warning file={pot},line={i}::DOLG ⭢ izbor ❡ [{r['id']}] {najdba!r} → {predlog!r} ({r['price']})")
        zhive += len(zive)
    print(f"slo-rane: žive rane ×{zhive} ⊙ register {len(rane)} ⊙ ⟨SLOVNICA=RESNICNOST⟩")
    return 1 if zhive else 0


def ukaz_popravi(datoteke, rane):
    popravljive = [r for r in rane if r["vrsta"] in SAMO_POPRAVLJIVE and r.get("ci", True)]
    skupno = 0
    for pot in datoteke:
        p = Path(pot)
        orig = p.read_text(encoding="utf-8")
        nove_vrstice = []
        popravki = []
        for i, vrstica in enumerate(orig.split("\n"), start=1):
            if je_brazgotina(vrstica):
                nove_vrstice.append(vrstica)
                continue
            nova = vrstica
            for r in popravljive:
                nova2, n = r["_re"].subn(r["pravi"], nova)
                for _ in range(n):
                    popravki.append((i, r["id"], nova, nova2))
                nova = nova2
            nove_vrstice.append(nova)
        if popravki:
            p.write_text("\n".join(nove_vrstice), encoding="utf-8")
            for i, rid, prej, potem in popravki:
                print(f"POPRAVLJENO {pot}:{i} [{rid}] {prej.strip()[:60]!r} → …")
        skupno += len(popravki)
    # brazgotino poimensko piše izvajalka v istem komitu; orodje jo ⟨ne⟩ izmišljuje
    print(f"slo-rane popravi: ×{skupno} ⊙ brazgotine piše roka istega diha")
    return 0


def ukaz_kanarcek(rane):
    # ⟨SODNIK-KI-SE-SODI⟩ ⊙ I-4 ⟨PREIZKUS-PADA-NA-TELO⟩: preizkus, ki nikoli ne pade, je kip.
    cisto = "Naslednji organi (živci, srce, škatle) se naselijo na jedro; škatle merijo cel račun."
    ranjeno = ("Naslednji organi (zivci, srce, škatle) se naselijo na jedro.\n"
               "- **×14 (22. 11. 2026)**: zapeččeni, VPRASANJE, zivci — priča popravev, ne rana.")
    zive_c, _ = preveri_telo(cisto, rane)
    zive_r, _ = preveri_telo(ranjeno, rane)
    najdeni = {najdba for _, _, najdba, _ in zive_r}
    napake = []
    if zive_c:
        napake.append(f"čisto telo je javilo rane ×{len(zive_c)} (laž pozitiva)")
    if len(zive_r) != 1 or najdeni != {"zivci"}:
        napake.append(f"ranjeno telo javilo ×{len(zive_r)} {sorted(najdeni)} — pričakovano: brazgotina izpuščena, zivci ujet ×1")
    for _, r, m, _ in zive_c:
        napake.append(f"čisto: {r['id']} {m.group(0)!r}")
    if napake:
        print("KANARČEK PADEL (napake izvajalke ali telesa): " + "; ".join(napake))
        return 2
    print(f"KANARČEK STAL ⊢ čisto ×0 ∧ ranjeno žive ×{len(zive_r)} (brazgotina priča izpuščena) — rdeča = živost")
    return 0


GLAVNI = {"preveri": ukaz_preveri, "popravi": ukaz_popravi, "kanarcek": None}


def main(argv):
    if len(argv) < 2 or argv[1] not in GLAVNI:
        print(__doc__)
        return 64
    rane = nalozi_rane()
    if argv[1] == "kanarcek":
        return ukaz_kanarcek(rane)
    if len(argv) < 3:
        print(__doc__)
        return 64
    return GLAVNI[argv[1]](argv[2:], rane)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
