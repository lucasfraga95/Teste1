#!/usr/bin/env python3
"""Gera src/data/ro.json com as regras do RO Pré-Renewal a partir do
banco de dados do rAthena (github.com/rathena/rathena, db/pre-re).

Uso: python3 tools/build_ro_data.py
Requer: git e PyYAML. O rAthena é clonado em tools/.cache/rathena.
"""
import json
import os
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RA = os.path.join(ROOT, "tools", ".cache", "rathena")
DB = os.path.join(RA, "db", "pre-re")
OUT = os.path.join(ROOT, "src", "data", "ro.json")

JOBS = ["Novice", "Swordman", "Mage", "Archer", "Acolyte", "Merchant",
        "Thief"]

# Monstro do Maple -> monstro do RO cujos atributos ele usa.
MOB_TEMPLATES = {
    100101: "PORING",         # Blue Snail
    130101: "LUNATIC",        # Red Snail
    120100: "FABRE",          # Shroom
    210100: "DROPS",          # Slime
    1210100: "SAVAGE_BABE",   # Pig
    1210102: "ROCKER",        # Orange Mushroom
    1210101: "POPORING",      # Ribbon Pig
    1110100: "SPORE",         # Green Mushroom
    2220100: "POISON_SPORE",  # Blue Mushroom
    2110200: "HORN",          # Horny Mushroom
}

# Monstros agressivos no rAthena (atacam ao ver o jogador).
AGGRESSIVE_AI = {4, 5, 7, 9, 10, 13, 19, 20, 21, 24, 25, 26, 27}


def ensure_rathena():
    if os.path.isdir(DB):
        return
    os.makedirs(os.path.dirname(RA), exist_ok=True)
    subprocess.check_call(["git", "clone", "--depth", "1", "--filter=blob:none",
                           "--sparse", "https://github.com/rathena/rathena",
                           RA])
    subprocess.check_call(["git", "-C", RA, "sparse-checkout", "set",
                           "db/pre-re"])


def body(name):
    with open(os.path.join(DB, name)) as f:
        return yaml.safe_load(f)["Body"]


def entries_for(job, rows):
    return [r for r in rows if r.get("Jobs", {}).get(job)]


def main():
    ensure_rathena()
    exp = body("job_exp.yml")
    basepoints = body("job_basepoints.yml")
    stats = body("job_stats.yml")
    aspd = body("job_aspd.yml")

    base_exp = next(r for r in entries_for("Novice", exp) if "BaseExp" in r)
    out = {
        "baseExp": [e["Exp"] for e in base_exp["BaseExp"]],
        "statPoints": [e["Points"] for e in body("statpoint.yml")
                       if e["Level"] <= 99],
        "jobs": {},
        "mobs": {},
    }

    for job in JOBS:
        jexp = next(r for r in entries_for(job, exp) if "JobExp" in r)
        hp = sp = None
        for r in entries_for(job, basepoints):
            hp = hp or r.get("BaseHp")
            sp = sp or r.get("BaseSp")
        st = {}
        for r in entries_for(job, stats):
            st.update({k: v for k, v in r.items() if k != "Jobs"})
        bonus = [{k.lower(): v for k, v in b.items()}
                 for b in st.get("BonusStats", [])]
        sp_inc = st.get("SpIncrease", 100)
        out["jobs"][job] = {
            "jobExp": [e["Exp"] for e in jexp["JobExp"]],
            "maxJobLevel": jexp["MaxJobLevel"],
            "baseHp": [e["Hp"] for e in hp] if hp else None,
            # Sem tabela de SP no rAthena: fórmula 10 + nível * SpIncrease/100.
            "baseSp": [e["Sp"] for e in sp] if sp else
                      [10 + (lv * sp_inc) // 100 for lv in range(1, 100)],
            "bonus": bonus,
            "maxWeight": st.get("MaxWeight", 20000),
            "aspd": next((r["BaseASPD"] for r in entries_for(job, aspd)), {}),
        }

    by_name = {m["AegisName"]: m for m in body("mob_db.yml")}
    for maple_id, aegis in MOB_TEMPLATES.items():
        m = by_name[aegis]
        out["mobs"][maple_id] = {
            "ro": m["Name"], "level": m["Level"], "hp": m["Hp"],
            "baseExp": m.get("BaseExp", 0), "jobExp": m.get("JobExp", 0),
            "atk": [m.get("Attack", 0), m.get("Attack2", 0)],
            "def": m.get("Defense", 0), "mdef": m.get("MagicDefense", 0),
            "str": m.get("Str", 0), "agi": m.get("Agi", 0),
            "vit": m.get("Vit", 0), "int": m.get("Int", 0),
            "dex": m.get("Dex", 0), "luk": m.get("Luk", 0),
            "size": m.get("Size", "Small"), "race": m.get("Race", "Formless"),
            "element": m.get("Element", "Neutral"),
            "walkSpeed": m.get("WalkSpeed", 200),
            "attackDelay": m.get("AttackDelay", 1500),
            "elementLevel": m.get("ElementLevel", 1),
            "aggressive": int(m.get("Ai") or 6) in AGGRESSIVE_AI,
        }

    # Elementos: attr[nível][elemento do ataque][elemento do alvo] = %.
    out["attr"] = {str(e["Level"]): {k: v for k, v in e.items() if k != "Level"}
                   for e in body("attr_fix.yml")}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print("ok:", OUT)


if __name__ == "__main__":
    main()
