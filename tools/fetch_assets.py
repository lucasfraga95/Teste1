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

# Mapas do protótipo. "links" conecta portais que o v83 não liga entre si.
MAPS = [100000000, 100010000]

# Visual do personagem (pele, rosto, cabelo, camisa, calça, sapato, arma).
SKIN = 2000
CHAR_ITEMS = [20000, 30030, 1040002, 1060002, 1072001]
WEAPON = 1302000
CHAR_ANIMS = ["stand1", "walk1", "jump", "alert", "swingO1", "swingO2",
              "swingO3", "stabO1", "prone", "proneStab", "ladder", "rope"]

MOB_ANIMS = ["stand", "move", "hit1", "die1"]
TILE = 1024  # tamanho máximo de cada pedaço de camada de mapa


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
    """anims: {nome: [(img, ox, oy, delay)]} -> uma folha com uma linha por
    animação, todas com a mesma célula e origem."""
    allf = [f for fs in anims.values() for f in fs]
    left = max(f[1] for f in allf)
    up = max(f[2] for f in allf)
    right = max(f[0].width - f[1] for f in allf)
    down = max(f[0].height - f[2] for f in allf)
    w, h = left + right, up + down
    cols = max(len(fs) for fs in anims.values())
    sheet = Image.new("RGBA", (w * cols, h * len(anims)))
    meta = {}
    for row, (name, fs) in enumerate(anims.items()):
        for i, (im, ox, oy, _) in enumerate(fs):
            sheet.paste(im, (i * w + left - ox, row * h + up - oy), im)
        meta[name] = {"start": row * cols, "count": len(fs),
                      "delays": [f[3] for f in fs]}
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
    # Ids 93xxxxx são monstros de evento; ficam de fora.
    mobs = [l for l in lifes if l["type"] == "m" and not l["hide"]
            and l["id"] // 100000 != 93]
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

    probe = None
    for n in range(16):
        data = fetch(layer_url(n), binary=True)
        if data:
            probe = n
            nat = Image.open(io.BytesIO(data))
            break
    zero = Image.open(io.BytesIO(fetch(layer_url(probe, "?minX=0&minY=0"),
                                       binary=True)))
    min_x = zero.width - nat.width
    min_y = zero.height - nat.height

    pieces = []
    for n in range(16):
        data = fetch(layer_url(n), binary=True)
        if not data:
            continue
        im = Image.open(io.BytesIO(data)).convert("RGBA")
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
        "bounds": {"left": min_x, "top": min_y, "right": zero.width,
                   "bottom": zero.height},
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


def fetch_character():
    print("[personagem]")
    armed = char_frames(CHAR_ITEMS + [WEAPON])
    unarmed = char_frames(CHAR_ITEMS)
    anims = {}
    for a in CHAR_ANIMS:
        src = armed if a in armed else unarmed
        if a not in src:
            print("  sem animação", a)
            continue
        fs = []
        for i in sorted(src[a]):
            im = src[a][i]
            delay = wz_val(f"Character/{SKIN:08d}.img/{a}/{i}/delay", 150)
            # renderMode FeetCenter: os pés ficam no centro da imagem.
            fs.append((im, im.width // 2, im.height // 2, abs(delay or 150)))
        anims[a] = fs
    sheet, meta = pack_anims(anims)
    save_png("char/novice.png", sheet)
    save_json("char/novice.json", meta)


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
    fetch_character()
    fetch_effects()
    save_json("index.json", {"maps": MAPS, "mobs": sorted(mob_ids)})
    print("ok")


if __name__ == "__main__":
    sys.exit(main())
