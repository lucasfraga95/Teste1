#!/usr/bin/env python3
"""Baixa os assets do MapleStory (GMS v83) via maplestory.io e gera
os arquivos que o jogo usa em public/assets.

Uso: python3 tools/fetch_assets.py
Requer: Pillow. As respostas da API ficam em cache em tools/.cache.
"""
import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "public", "assets")
CACHE = os.path.join(ROOT, "tools", ".cache")
API = "https://maplestory.io/api"
REGION, VERSION = "GMS", "83"
UA = "Mozilla/5.0 (RO-Maple fan project)"

# Mapas do jogo: Henesys e os campos de caça ao redor.
MAPS = [
    100000000,  # Henesys
    100010000,  # Colina a Leste de Henesys
    100020000,  # Floresta Tropical a Leste de Henesys
    104040000,  # Campo de Caça de Henesys I
    104040001,  # Campo de Caça de Henesys II
    104040002,  # Campo de Caça de Henesys III
    104030000,  # Colina a Oeste de Henesys
    106010000,  # Estrada para o Calabouço
]

# Visual de cada classe: rosto, cabelo, roupas e, por último, a arma.
SKIN = 2000
HEAD = [20000, 30921]  # rosto e cabelo ruivo arrepiado (Short Top Tail)
CLASS_LOOKS = {
    # Aprendiz: blusa clara, calça bege larga, botas avermelhadas e luvas marrons.
    "Novice": [1040017, 1060013, 1072069, 1082149, 1332005],
    "Swordman": [1002002, 1040015, 1060008, 1072009, 1092005, 1302005],
    "Mage": [1002017, 1050009, 1072006, 1382000],
    "Archer": [1002010, 1040008, 1060006, 1072015, 1082012, 1452002],
    "Thief": [1002019, 1040031, 1060021, 1072030, 1082030, 1332000],
}
CHAR_ANIMS = ["stand1", "walk1", "jump", "alert", "swingO1", "swingO2",
              "swingO3", "stabO1", "stabO2", "swingT1", "shoot1", "prone",
              "proneStab", "ladder", "rope"]

# Efeitos visuais do Maple usados nas habilidades do RO: (id da skill, partes).
SKILL_FX = {
    "bash": (1001004, ["effect", "hit/0"]),
    "magnum": (1001005, ["effect", "hit/0"]),
    "firebolt": (2101004, ["ball", "hit/0"]),
    "coldbolt": (2201004, ["effect", "hit/0"]),
    "lightning": (2201005, ["effect", "hit/0"]),
    "doublestrafe": (3001005, ["hit/0"]),
    "arrowshower": (3111004, ["effect", "hit/0"]),
    "envenom": (4201005, ["effect", "hit/0"]),
}
# Ícones do Maple para as habilidades do RO.
SKILL_ICONS = {
    "basic": 1000, "bash": 1001004, "magnum": 1001005, "hprecovery": 1000000,
    "swordmastery": 1100000, "firebolt": 2101004, "coldbolt": 2201004,
    "lightning": 2201005, "sprecovery": 2000000, "doublestrafe": 3001005,
    "arrowshower": 3111004, "owlseye": 3000000, "vultureseye": 3000002,
    "doubleattack": 4001334, "envenom": 4201005, "improvedodge": 4000000,
}
# Equipamentos vendidos no jogo (só o ícone; o visual do personagem é o da classe).
EQUIP_ITEMS = [1332005, 1332006, 1332067, 1302007, 1302005, 1302001,
               1372005, 1382003, 1382005, 1452003, 1452054, 1452062,
               1040010, 1040013, 1040014, 1002014, 1002019, 1002008,
               1072005, 1072004, 1072037]
ITEMS = [2000000, 2000001, 2000002, 2000003, 2010000,
         4000000, 4000001, 4000002, 4000009, 4000010, 4000011, 4000012,
         4000015, 4000016, 4000017]

MOB_ANIMS = ["stand", "move", "hit1", "die1"]
TILE = 1024  # tamanho máximo de cada pedaço de camada de mapa
MAX_SHEET_W = 2048  # largura máxima das folhas de animação


# ---------------------------------------------------------------- HTTP / cache

def fetch(url, binary=False, retries=4):
    key = hashlib.sha1(url.encode()).hexdigest()
    path = os.path.join(CACHE, key)
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = f.read()
    else:
        data = None
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=180) as r:
                    data = r.read()
                break
            except urllib.error.HTTPError as e:
                if e.code == 404 or e.code == 500:
                    data = b""
                    break
                time.sleep(2 ** attempt)
            except Exception:
                time.sleep(2 ** attempt)
        if data is None:
            raise RuntimeError("falhou: " + url)
        os.makedirs(CACHE, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
    if not data:
        return None
    return data if binary else json.loads(data)


def q(path):
    return urllib.parse.quote(path, safe="/")


def wz(path):
    """Nó cru do WZ: {children, type, value?}."""
    return fetch(f"{API}/wz/{REGION}/{VERSION}/{q(path)}")


def wz_children(path):
    n = wz(path)
    return n["children"] if n else []


def wz_val(path, default=None):
    n = wz(path)
    if not n or "value" not in n:
        return default
    return n["value"]


def wz_img(path):
    data = fetch(f"{API}/wz/img/{REGION}/{VERSION}/{q(path)}", binary=True)
    if not data:
        return None
    return Image.open(io.BytesIO(data)).convert("RGBA")


def wz_vec(path):
    v = wz_val(path)
    if isinstance(v, dict):
        return int(v.get("x", 0)), int(v.get("y", 0))
    return 0, 0


def wz_audio(path, dest):
    data = fetch(f"{API}/wz/export/{REGION}/{VERSION}/{q(path)}", binary=True)
    if not data:
        return False
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(data))
    names = [n for n in z.namelist() if n.endswith(".mp3")]
    if not names:
        return False
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(z.read(names[0]))
    return True


def pmap(fn, items, workers=12):
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(fn, items))


def save_json(rel, obj):
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, separators=(",", ":"))


def save_png(rel, img):
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, optimize=True)


# ------------------------------------------------------------- sprite sheets

def pack_frames(frames):
    """frames: lista de (img, ox, oy). Retorna (sheet, w, h, ox, oy) com todos
    os quadros em células iguais e alinhados pela mesma origem."""
    left = max(ox for _, ox, _ in frames)
    up = max(oy for _, _, oy in frames)
    right = max(im.width - ox for im, ox, _ in frames)
    down = max(im.height - oy for im, _, oy in frames)
    w, h = left + right, up + down
    sheet = Image.new("RGBA", (w * len(frames), h))
    for i, (im, ox, oy) in enumerate(frames):
        sheet.paste(im, (i * w + left - ox, up - oy), im)
    return sheet, w, h, left, up


def pack_anims(anims):
    """anims: {nome: [(img, ox, oy, delay)]} -> uma folha em grade, todas as
    células do mesmo tamanho e com a mesma origem. Os quadros seguem em ordem
    (esquerda para a direita, de cima para baixo), como o Phaser numera."""
    allf = [f for fs in anims.values() for f in fs]
    # A célula é simétrica em volta da origem: ao espelhar o sprite (virar
    # para o outro lado) o Phaser espelha em torno do centro da célula.
    left = right = max(max(f[1] for f in allf),
                       max(f[0].width - f[1] for f in allf))
    up = max(f[2] for f in allf)
    down = max(f[0].height - f[2] for f in allf)
    w, h = left + right, up + down
    cols = max(1, min(len(allf), MAX_SHEET_W // w))
    rows = (len(allf) + cols - 1) // cols
    sheet = Image.new("RGBA", (w * cols, h * rows))
    meta = {}
    i = 0
    for name, fs in anims.items():
        meta[name] = {"start": i, "count": len(fs),
                      "delays": [f[3] for f in fs]}
        for im, ox, oy, _ in fs:
            x, y = (i % cols) * w, (i // cols) * h
            sheet.paste(im, (x + left - ox, y + up - oy), im)
            i += 1
    return sheet, {"frameWidth": w, "frameHeight": h, "originX": left,
                   "originY": up, "anims": meta}


# ---------------------------------------------------------------------- mapas

def map_img_path(mid):
    return f"Map/Map/Map{mid // 100000000}/{mid:09d}.img"


def fetch_map(mid):
    print(f"[mapa {mid}]")
    base = map_img_path(mid)
    info = fetch(f"{API}/{REGION}/{VERSION}/map/{mid}")

    # Portais lidos do WZ cru (a API resumida omite alguns).
    def portal(i):
        p = f"{base}/portal/{i}"
        return {"name": wz_val(p + "/pn", ""), "type": wz_val(p + "/pt", 0),
                "x": wz_val(p + "/x", 0), "y": wz_val(p + "/y", 0),
                "toMap": wz_val(p + "/tm", 999999999),
                "toName": wz_val(p + "/tn", "")}
    portals = pmap(portal, wz_children(base + "/portal"))

    # Monstros (life tipo m) com faixa de patrulha.
    def life(i):
        p = f"{base}/life/{i}"
        return {"type": wz_val(p + "/type"), "id": int(wz_val(p + "/id", "0")),
                "x": wz_val(p + "/x", 0), "y": wz_val(p + "/cy", 0),
                "fh": wz_val(p + "/fh", 0), "rx0": wz_val(p + "/rx0", 0),
                "rx1": wz_val(p + "/rx1", 0), "f": wz_val(p + "/f", 0),
                "hide": wz_val(p + "/hide", 0)}
    lifes = pmap(life, wz_children(base + "/life"))
    # Ids 9xxxxxx são monstros de evento; ficam de fora.
    mobs = [l for l in lifes if l["type"] == "m" and not l["hide"]
            and l["id"] < 9000000]
    npcs = [l for l in lifes if l["type"] == "n" and not l["hide"]]

    # Fundos (parallax).
    def back(i):
        p = f"{base}/back/{i}"
        b = {k: wz_val(f"{p}/{k}", 0) for k in
             ("no", "x", "y", "rx", "ry", "type", "cx", "cy", "a", "front",
              "ani", "f")}
        b["bS"] = wz_val(p + "/bS", "")
        b["i"] = int(i)
        return b
    backs = [b for b in pmap(back, wz_children(base + "/back")) if b["bS"]]
    back_out = []
    for b in backs:
        if b["ani"]:
            ip = f"Map/Back/{b['bS']}.img/ani/{b['no']}/0"
        else:
            ip = f"Map/Back/{b['bS']}.img/back/{b['no']}"
        im = wz_img(ip)
        if im is None or im.width <= 1 and im.height <= 1:
            continue
        ox, oy = wz_vec(ip + "/origin")
        key = f"{b['bS']}_{'a' if b['ani'] else 'b'}{b['no']}"
        save_png(f"backs/{key}.png", im)
        back_out.append({"key": key, "x": b["x"], "y": b["y"], "rx": b["rx"],
                         "ry": b["ry"], "type": b["type"], "cx": b["cx"],
                         "cy": b["cy"], "a": b["a"] if b["a"] else 255,
                         "front": b["front"], "flip": b["f"], "ox": ox,
                         "oy": oy, "w": im.width, "h": im.height})

    # Camadas de tiles/objetos renderizadas pela API, recortadas em pedaços.
    def layer_url(n, extra=""):
        return f"{API}/{REGION}/{VERSION}/map/{mid}/render/layer/{n}{extra}"

    # Todas as camadas são pedidas com a mesma origem (minX/minY), escolhida
    # com folga a partir das plataformas; assim a posição de cada pixel é exata.
    fhs = list(info["footholds"].values())
    min_x = min(min(f["x1"], f["x2"]) for f in fhs) - 1500
    min_y = min(min(f["y1"], f["y2"]) for f in fhs) - 1500
    extra = f"?minX={min_x}&minY={min_y}"
    max_x, max_y = min_x, min_y

    pieces = []
    for n in range(16):
        data = fetch(layer_url(n, extra), binary=True)
        if not data:
            continue
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        box = im.getbbox()
        if box:
            max_x = max(max_x, min_x + box[2])
            max_y = max(max_y, min_y + box[3])
        for ty in range(0, im.height, TILE):
            for tx in range(0, im.width, TILE):
                part = im.crop((tx, ty, min(tx + TILE, im.width),
                                min(ty + TILE, im.height)))
                bbox = part.getbbox()
                if not bbox:
                    continue
                part = part.crop(bbox)
                key = f"m{mid}_l{n}_{tx}_{ty}"
                save_png(f"maps/{mid}/{key}.png", part)
                pieces.append({"key": key, "layer": n // 2,
                               "x": min_x + tx + bbox[0],
                               "y": min_y + ty + bbox[1]})

    footholds = [{"id": f["id"], "x1": f["x1"], "y1": f["y1"], "x2": f["x2"],
                  "y2": f["y2"], "prev": f["prev"], "next": f["next"],
                  "layer": f["layerId"]} for f in info["footholds"].values()]
    ladders = [{"x": l["x"], "y1": l["y1"], "y2": l["y2"],
                "ladder": l["isLadder"]} for l in info["ladderRopes"] or []]

    for n in npcs:
        fetch_npc(n["id"])

    bgm = info.get("backgroundMusic") or ""
    if bgm and not os.path.exists(os.path.join(OUT, "bgm", f"{mid}.mp3")):
        data = fetch(f"{API}/{REGION}/{VERSION}/map/{mid}/bgm", binary=True)
        if data:
            os.makedirs(os.path.join(OUT, "bgm"), exist_ok=True)
            with open(os.path.join(OUT, "bgm", f"{mid}.mp3"), "wb") as f:
                f.write(data)

    save_json(f"maps/{mid}/map.json", {
        "id": mid, "name": info["name"], "street": info["streetName"],
        "town": bool(info.get("isTown")), "bgm": f"{mid}" if bgm else None,
        "returnMap": info.get("returnMap"),
        "bounds": {"left": min(p["x"] for p in pieces),
                   "top": min(p["y"] for p in pieces), "right": max_x,
                   "bottom": max_y},
        "pieces": pieces, "backs": back_out, "footholds": footholds,
        "ladders": ladders, "portals": portals,
        "mobs": [{k: m[k] for k in ("id", "x", "y", "fh", "rx0", "rx1", "f")}
                 for m in mobs],
        "npcs": [{k: n[k] for k in ("id", "x", "y", "fh", "f")}
                 for n in npcs],
    })
    return {m["id"] for m in mobs}


# ------------------------------------------------------------ monstros / npcs

def anim_frames(base, anim):
    out = []
    for i in sorted((c for c in wz_children(f"{base}/{anim}") if c.isdigit()),
                    key=int):
        p = f"{base}/{anim}/{i}"
        im = wz_img(p)
        if im is None:
            continue
        ox, oy = wz_vec(p + "/origin")
        out.append((im, ox, oy, wz_val(p + "/delay", 100) or 100))
    return out


def fetch_mob(mid):
    if os.path.exists(os.path.join(OUT, "mobs", f"{mid}.json")):
        return
    print(f"[monstro {mid}]")
    meta = fetch(f"{API}/{REGION}/{VERSION}/mob/{mid}")
    src = mid
    link = wz_val(f"Mob/{mid:07d}.img/info/link")
    if link:
        src = int(link)
    base = f"Mob/{src:07d}.img"
    anims = {}
    for a in MOB_ANIMS:
        fs = anim_frames(base, a)
        if fs:
            anims[a] = fs
    if "move" not in anims and "stand" in anims:
        anims["move"] = anims["stand"]
    sheet, sm = pack_anims(anims)
    save_png(f"mobs/{mid}.png", sheet)
    for snd in ("Damage", "Die"):
        wz_audio(f"Sound/Mob.img/{src:07d}/{snd}",
                 os.path.join(OUT, "sfx", f"mob{mid}_{snd}.mp3"))
    m = meta["meta"]
    sm.update({"id": mid, "name": meta["name"], "speed": m.get("speed", 0),
               "maple": {"level": m.get("level"), "hp": m.get("maxHP"),
                         "exp": m.get("exp")}})
    save_json(f"mobs/{mid}.json", sm)


def fetch_npc(nid):
    if os.path.exists(os.path.join(OUT, "npcs", f"{nid}.json")):
        return
    print(f"[npc {nid}]")
    base = f"Npc/{nid:07d}.img"
    link = wz_val(base + "/info/link")
    if link:
        base = f"Npc/{int(link):07d}.img"
    fs = anim_frames(base, "stand")
    if not fs:
        return
    sheet, sm = pack_anims({"stand": fs})
    name = fetch(f"{API}/{REGION}/{VERSION}/npc/{nid}") or {}
    sm["name"] = name.get("name", "")
    save_png(f"npcs/{nid}.png", sheet)
    save_json(f"npcs/{nid}.json", sm)


# ------------------------------------------------------------------ personagem

def char_frames(items):
    """Baixa a folha do personagem (quadros centralizados nos pés)."""
    import zipfile
    ids = ",".join(str(i) for i in items)
    url = (f"{API}/{REGION}/{VERSION}/Character/download/{SKIN}/{ids}"
           f"?format=2&renderMode=4")
    z = zipfile.ZipFile(io.BytesIO(fetch(url, binary=True)))
    frames = {}
    for n in z.namelist():
        # O pacote traz uma pasta por expressão; usamos só a padrão.
        if "/" in n and not n.startswith("default/0/"):
            continue
        name = os.path.basename(n)[:-4]
        anim, idx = name.rsplit("_", 1)
        im = Image.open(io.BytesIO(z.read(n))).convert("RGBA")
        frames.setdefault(anim, {})[int(idx)] = im
    return frames


def fetch_character(job, items):
    if os.path.exists(os.path.join(OUT, "char", f"{job}.json")):
        return
    print(f"[personagem {job}]")
    armed = char_frames(HEAD + items)
    unarmed = char_frames(HEAD + items[:-1])
    anims = {}
    for a in CHAR_ANIMS:
        src = armed if a in armed else unarmed
        if a not in src:
            continue
        fs = []
        for i in sorted(src[a]):
            im = src[a][i]
            delay = wz_val(f"Character/{SKIN:08d}.img/{a}/{i}/delay", 150)
            # renderMode FeetCenter: os pés ficam no centro da imagem.
            fs.append((im, im.width // 2, im.height // 2, abs(delay or 150)))
        anims[a] = fs
    sheet, meta = pack_anims(anims)
    save_png(f"char/{job}.png", sheet)
    save_json(f"char/{job}.json", meta)


def fetch_skills():
    print("[habilidades]")
    for name, (sid, parts) in SKILL_FX.items():
        base = f"Skill/{sid // 10000:03d}.img/skill/{sid:07d}"
        for part in parts:
            parent, leaf = f"{base}/{part}".rsplit("/", 1)
            fs = anim_frames(parent, leaf)
            if not fs:
                print("  sem efeito", name, part)
                continue
            sheet, meta = pack_anims({"play": fs})
            key = f"skill_{name}_{part.split('/')[0]}"
            save_png(f"fx/{key}.png", sheet)
            save_json(f"fx/{key}.json", meta)
    for name, sid in SKILL_ICONS.items():
        im = wz_img(f"Skill/{sid // 10000:03d}.img/skill/{sid:07d}/icon")
        if im is None:
            print("  sem ícone", name)
            continue
        save_png(f"icons/skill_{name}.png", im)


def item_path(iid):
    if iid // 1000000 == 1:
        kind = {100: "Cap", 104: "Coat", 105: "Longcoat", 107: "Shoes"}.get(
            iid // 10000, "Weapon")
        return f"Character/{kind}/{iid:08d}.img"
    group = {2: "Consume", 4: "Etc"}[iid // 1000000]
    return f"Item/{group}/{iid // 10000:04d}.img/{iid:08d}"


def fetch_items():
    print("[itens]")
    names = {}
    for iid in ITEMS + EQUIP_ITEMS:
        im = wz_img(item_path(iid) + "/info/icon")
        if im is not None:
            save_png(f"icons/item_{iid}.png", im)
        n = fetch(f"{API}/{REGION}/{VERSION}/item/{iid}/name") or {}
        names[iid] = n.get("name", str(iid))
    save_json("icons/items.json", names)
    meso = wz_img("Item/Special/0900.img/09000000/iconRaw/0")
    if meso is not None:
        save_png("icons/meso.png", meso)
    fs = anim_frames("Item/Consume/0206.img/02060000", "bullet")
    if fs:
        sheet, meta = pack_anims({"fly": fs})
        save_png("fx/arrow.png", sheet)
        save_json("fx/arrow.json", meta)


# --------------------------------------------------------------------- efeitos

def fetch_effects():
    print("[efeitos]")
    digits = {}
    for style in ("NoRed1", "NoCri1", "NoViolet1"):
        fs = []
        for d in range(10):
            p = f"Effect/BasicEff.img/{style}/{d}"
            im = wz_img(p)
            ox, oy = wz_vec(p + "/origin")
            fs.append((im, ox, oy))
        sheet, w, h, ox, oy = pack_frames(fs)
        save_png(f"fx/{style}.png", sheet)
        digits[style] = {"frameWidth": w, "frameHeight": h}
    save_json("fx/digits.json", digits)

    for name, path in (("portal", "Map/MapHelper.img/portal/game/pv"),
                       ("levelup", "Effect/BasicEff.img/LevelUp")):
        fs = anim_frames(path.rsplit("/", 1)[0], path.rsplit("/", 1)[1])
        sheet, meta = pack_anims({name: fs})
        save_png(f"fx/{name}.png", sheet)
        save_json(f"fx/{name}.json", meta)

    for name, path in (("jump", "Sound/Game.img/Jump"),
                       ("portal", "Sound/Game.img/Portal"),
                       ("levelup", "Sound/Game.img/LevelUp"),
                       ("swing", "Sound/Weapon.img/swordL/Attack")):
        wz_audio(path, os.path.join(OUT, "sfx", f"{name}.mp3"))


def main():
    os.makedirs(OUT, exist_ok=True)
    mob_ids = set()
    for mid in MAPS:
        mob_ids |= fetch_map(mid)
    for m in sorted(mob_ids):
        fetch_mob(m)
    for job, items in CLASS_LOOKS.items():
        fetch_character(job, items)
    fetch_effects()
    fetch_skills()
    fetch_items()
    save_json("index.json", {"maps": MAPS, "mobs": sorted(mob_ids),
                             "classes": list(CLASS_LOOKS),
                             "skillFx": [f"skill_{n}_{p.split('/')[0]}"
                                         for n, (_, ps) in SKILL_FX.items()
                                         for p in ps],
                             "items": ITEMS + EQUIP_ITEMS})
    print("ok")


if __name__ == "__main__":
    sys.exit(main())
