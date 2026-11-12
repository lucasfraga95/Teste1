#!/usr/bin/env python3
"""Reels "Sumimasen" — versão tipográfica (sem personagem): textos animados, ilustrações e transições AOI.

Uso:
  AUDIO=voz.m4a WORDS=transcricao.json WORK=/tmp/work FONTS=/fonts/ttf python3 reels_tipografia.py [amostra]
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reels_audio as RA
import ilustracoes as IL

R = RA.R
W, H, FPS, SR = R.W, R.H, R.FPS, RA.SR
C = R.C
TEXTO = "#2a2a28"
OURO = "#f6d27a"
WORK = RA.WORK
OUT = f"{WORK}/tipo"
os.makedirs(OUT, exist_ok=True)
ease, back = RA.ease, RA.back


def hexrgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ------------------------------------------------------------------ texto
_tcache = {}


def timg(text, size, color, weight=700, track=0.04):
    key = (text, size, color, weight, track)
    if key in _tcache:
        return _tcache[key]
    f = R.jfont(weight, size)
    sp = size * track
    w = int(sum(f.getlength(c) for c in text) + sp * (len(text) - 1)) + 8
    asc, desc = f.getmetrics()
    top = int(size * 0.45)          # espaço para acentos das maiúsculas (Ê, Ã, Ó, Ç)
    im = Image.new("RGBA", (w, asc + desc + top + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 4
    for c in text:
        d.text((x, top), c, font=f, fill=color)
        x += f.getlength(c) + sp
    im = im.crop(im.getbbox())
    _tcache[key] = im
    return im


def kimg(text, size, color):
    key = ("k", text, size, color)
    if key in _tcache:
        return _tcache[key]
    w = int(R.jp_width(text, size)) + 10
    im = Image.new("RGBA", (w, int(size * 1.4)), (0, 0, 0, 0))
    R.draw_jp(ImageDraw.Draw(im), 5, 0, text, size, color)
    im = im.crop(im.getbbox())
    _tcache[key] = im
    return im


def with_alpha(im, a):
    if a >= 0.999:
        return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * max(0, a))))
    return im


def put(fr, im, cx, cy, a=1.0, sc=1.0):
    if a <= 0 or sc <= 0.01:
        return
    if abs(sc - 1) > 0.002:
        im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BICUBIC)
    fr.alpha_composite(with_alpha(im, a), (int(cx - im.width / 2), int(cy - im.height / 2)))


def reveal_up(fr, im, cx, cy, p, a=1.0):
    """Texto sobe de dentro de uma máscara (efeito 'linha nascendo')."""
    if p <= 0:
        return
    e = ease(p)
    off = int((1 - e) * im.height * 0.9)
    crop = im.crop((0, 0, im.width, im.height - off)) if off < im.height else None
    if crop is None or crop.height <= 0:
        return
    fr.alpha_composite(with_alpha(crop, a * min(1, e * 1.6)),
                       (int(cx - im.width / 2), int(cy - im.height / 2 + off)))


def pop_in(fr, im, cx, cy, t, t0, dur=0.35, start=0.55):
    if t < t0:
        return
    p = (t - t0) / dur
    sc = start + (1 - start) * back(p)
    put(fr, im, cx, cy, a=ease(p * 2), sc=sc)


# ------------------------------------------------------------------ fundos
def seigaiha(w, h, base, line, step=90, alpha=0.35):
    im = Image.new("RGBA", (w, h), base)
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    col = hexrgb(line) + (int(255 * alpha),)
    r = step // 2
    for row in range(-1, h // (r // 2) + 2):
        y = row * r // 2
        off = 0 if row % 2 == 0 else r
        for x in range(-step, w + step, step):
            cx = x + off
            for k in (r, r * 0.72, r * 0.44):
                d.arc((cx - k, y - k, cx + k, y + k), 180, 360, fill=col, width=4)
    im.alpha_composite(lay)
    return im


BG_VERDE = seigaiha(W, H + 200, C["verde_aoi"], "#3f6d5b", alpha=0.55)
BG_VERMELHO = seigaiha(W, H + 200, C["vermelho_ume"], "#a83d38", alpha=0.6)


def bg_creme():
    bg = Image.new("RGBA", (W, H), C["creme_fundo"])
    pat = Image.open(os.path.join(R.MARCA, "canva", "padroes-seigaiha-asanoha.png")).convert("RGBA")
    s = pat.width / 335
    asa = pat.crop((int(105 * s), int(125 * s), int(232 * s), int(228 * s)))
    asa = with_alpha(asa.resize((int(asa.width * 1.3), int(asa.height * 1.3)), Image.LANCZOS), 0.35)
    bg.alpha_composite(asa, (W - asa.width + 160, -60))
    bg.alpha_composite(asa.rotate(180), (-160, H - asa.height + 60))
    return bg


BG_CREME = bg_creme()


def drift(bg, t, speed=14):
    off = int(t * speed) % 200
    return bg.crop((0, off, W, off + H))


def tag(fr, dark_bg):
    col = C["creme_fundo"] if dark_bg else C["verde_aoi"]
    put(fr, timg("@espacoaoi", 38, col, 600, 0.06), W / 2, 150)


# ------------------------------------------------------------------ transições
def ume_reveal(old, new, p, center=(540, 760)):
    """Círculo que abre a partir da flor de ume."""
    e = ease(p)
    r = int(e * 1400)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).ellipse((center[0] - r, center[1] - r, center[0] + r, center[1] + r), fill=255)
    out = Image.composite(new, old, mask)
    fl = R.UME.rotate(-200 * e, resample=Image.BICUBIC, expand=True)
    size = int(120 + 900 * e)
    fl = fl.resize((size, int(size * fl.height / fl.width)), Image.BICUBIC)
    put(out, fl, center[0], center[1], a=1 - ease((p - 0.45) / 0.55))
    return out


def diag_wipe(old, new, p, color):
    """Faixa diagonal colorida varre a tela e revela a nova cena."""
    out = old.copy()
    e = ease(p)
    band = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(band)
    x = -900 + e * (W + 1800)
    d.polygon([(x - 700, H), (x, 0), (x + 700, 0), (x, H)], fill=255)
    rev = Image.new("L", (W, H), 0)
    xr = x - 350
    ImageDraw.Draw(rev).polygon([(-2000, 0), (xr, 0), (xr - 700, H), (-2000, H)], fill=255)
    out = Image.composite(new, out, rev)
    col = Image.new("RGBA", (W, H), color)
    edge = Image.new("L", (W, H), 0)
    ImageDraw.Draw(edge).polygon([(xr, 0), (x + 700, 0), (x, H), (xr - 700, H)], fill=255)
    out = Image.composite(col, out, edge)
    return out


def push(old, new, p):
    e = ease(p)
    dx = int(e * W)
    out = Image.new("RGBA", (W, H))
    out.alpha_composite(old.crop((dx, 0, W, H)), (0, 0)) if dx < W else None
    out.alpha_composite(new.crop((0, 0, dx, H)), (W - dx, 0)) if dx > 0 else None
    return out


# ------------------------------------------------------------------ legenda
FCAP = 54


def caption(fr, caps, t, end_voice, kin=frozenset()):
    if t > end_voice + 0.25:
        return
    for ci, chunk in enumerate(caps):
        c0 = chunk[0]["s"] - 0.05
        c1 = caps[ci + 1][0]["s"] - 0.05 if ci + 1 < len(caps) else end_voice + 0.25
        if not (c0 <= t < c1):
            continue
        if any(id(w) in kin for w in chunk):      # já está em destaque no topo
            return
        act = max([k for k, w in enumerate(chunk) if t >= w["s"] - 0.03] or [0])
        parts = []
        for k, w in enumerate(chunk):
            txt = w["w"].upper() if w["jp"] else w["w"]
            col = C["vermelho_ume"] if (w["jp"] or k == act) else TEXTO
            parts.append(timg(txt, FCAP, col, 700, 0.02))
        gap = 18
        tw = sum(p.width for p in parts) + gap * (len(parts) - 1)
        ph = max(p.height for p in parts)
        pill = Image.new("RGBA", (tw + 70, ph + 46), (0, 0, 0, 0))
        ImageDraw.Draw(pill).rounded_rectangle((0, 0, pill.width - 1, pill.height - 1), radius=(ph + 46) // 2,
                                               fill=hexrgb(C["creme_fundo"]) + (240,))
        x = 35
        for p in parts:
            pill.alpha_composite(p, (x, 23 + (ph - p.height) // 2 + (ph - p.height) // 2 * 0))
            x += p.width + gap
        pop = ease((t - c0) / 0.12)
        put(fr, pill, W / 2, 1440 + 14 * (1 - pop), a=pop)
        return


# ------------------------------------------------------------------ cenas
def main():
    amostra = len(sys.argv) > 1 and sys.argv[1] == "amostra"
    voice_wav, remap, vdur, removed = RA.build_audio()
    words = RA.load_words(remap)
    caps = RA.chunks(words, maxc=22)

    def find(text, nth=1, start=0):
        k = 0
        for i in range(start, len(words)):
            if words[i]["w"].lower().startswith(text):
                k += 1
                if k == nth:
                    return i
        raise KeyError(text)

    T = lambda i: words[i]["s"]
    t_puder, t_aprender, t_uma, t_palavra = T(find("puder")), T(find("aprender")), T(find("uma")), T(find("palavra"))
    t_antes, t_japao, t_aprenda = T(find("antes")), T(find("japão")), T(find("aprenda"))
    t_sumi = T(find("sumimasen"))
    t_ela, t_chamar, t_sumi2 = T(find("ela")), T(find("chamar")), T(find("sumimasen", 2))
    i_para2 = find("para", start=find("sumimasen", 2))
    t_para2, t_pedir, t_esbarra = T(i_para2), T(find("pedir")), T(find("esbarra"))
    t_ate, t_agradecer, t_porta = T(find("até")), T(find("agradecer")), T(find("porta"))
    t_tres, t_uma2, t_dica = T(find("três")), T(find("uma", 2)), T(find("dica"))

    END = t_dica + 0.55 if amostra else vdur + 1.6
    voice_end = t_dica - 0.04 if amostra else vdur
    nframes = int(END * FPS)

    # --- elementos pré-renderizados
    hook_lines = [
        (timg("SE VOCÊ SÓ PUDER", 72, C["creme_fundo"]), 520, 0.0, "up"),
        (timg("APRENDER", 124, C["creme_fundo"]), 650, t_aprender, "up"),
        (timg("1 PALAVRA", 156, OURO), 820, t_uma, "pop"),
        (timg("ANTES DE IR PRO", 72, C["creme_fundo"]), 985, t_antes, "up"),
        (timg("JAPÃO", 168, C["creme_fundo"]), 1120, t_japao - 0.05, "pop"),
    ]
    ilu_jp = IL.png(IL.japao(), 430)
    aprenda = timg("APRENDA ESSA", 132, OURO)
    seta = timg("↓", 150, C["creme_fundo"], 400)

    kana = ["す", "み", "ま", "せ", "ん"]
    sil = ["SU", "MI", "MA", "SE", "N"]
    KS = 184
    kana_imgs = [kimg(k, KS, C["verde_aoi"]) for k in kana]
    sil_imgs = [timg(s, 62, C["vermelho_ume"]) for s in sil]
    cell = 196
    row_x0 = W / 2 - cell * 2
    kana_t = [t_sumi + i * 0.11 for i in range(5)]
    band_t = t_sumi + 0.55
    band = Image.new("RGBA", (900, 150), (0, 0, 0, 0))
    ImageDraw.Draw(band).rounded_rectangle((0, 0, 899, 149), radius=36, fill=C["vermelho_ume"])
    bt = timg("SU.MI.MA.SE.N", 96, C["creme_fundo"], 700, 0.08)
    band.alpha_composite(bt, ((900 - bt.width) // 2, (150 - bt.height) // 2))
    significado = timg("com licença · desculpa · obrigado", 46, TEXTO, 600, 0.01)

    # bloco "cabeçalho" (kana + faixa) para o morph
    block = Image.new("RGBA", (W, 560), (0, 0, 0, 0))
    for i, im in enumerate(kana_imgs):
        block.alpha_composite(im, (int(row_x0 + i * cell - im.width / 2), int(130 - im.height / 2)))
    block.alpha_composite(band, ((W - 900) // 2, 300))
    block = block.crop(block.getbbox())
    morph0, morph1 = max(t_ela + 0.35, band_t + 0.6), max(t_ela + 0.35, band_t + 0.6) + 0.45
    HEAD_Y, HEAD_SC = 330, 0.42

    usos = [
        dict(t0=morph1 - 0.1, label="CHAMAR O GARÇOM", lt=t_chamar, ilu=IL.png(IL.ramen_mao(), 540), n=1),
        dict(t0=t_para2, label="PEDIR DESCULPA", lt=t_pedir, ilu=IL.png(IL.esbarrao(), 540), n=2),
        dict(t0=t_ate, label="AGRADECER", lt=t_agradecer, ilu=IL.png(IL.porta(), 540), n=3),
    ]
    bal = IL.png(IL.balao(420), 360)
    bal.alpha_composite(kimg("すみません!", 58, TEXTO), (40, 38))
    card_bg = Image.new("RGBA", (900, 820), (0, 0, 0, 0))
    sh = Image.new("RGBA", (940, 860), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((20, 34, 920, 846), radius=56, fill=(60, 40, 30, 60))
    sh = sh.filter(ImageFilter.GaussianBlur(16))
    ImageDraw.Draw(card_bg).rounded_rectangle((0, 0, 899, 819), radius=56, fill="#ffffff")

    def card_img(u, t):
        c = Image.new("RGBA", (940, 860), (0, 0, 0, 0))
        c.alpha_composite(sh)
        c.alpha_composite(card_bg, (20, 20))
        shake = 0
        if u["n"] == 2 and t_esbarra <= t <= t_esbarra + 0.25:
            shake = int(10 * math.sin((t - t_esbarra) * 80))
        c.alpha_composite(u["ilu"], (470 - 270 + shake, 60))
        d = ImageDraw.Draw(c)
        d.ellipse((50, 50, 150, 150), fill=C["vermelho_ume"])
        num = timg(str(u["n"]), 64, C["creme_fundo"])
        c.alpha_composite(num, (100 - num.width // 2, 100 - num.height // 2))
        dd = ImageDraw.Draw(c)
        for j in range(3):
            col = C["vermelho_ume"] if j <= u["n"] - 1 else C["salvia"]
            x = 470 + (j - 1) * 46
            dd.ellipse((x - 12, 790 - 12, x + 12, 790 + 12), fill=col)
        if t >= u["lt"]:
            lab = timg(u["label"], 74, C["verde_aoi"])
            tmp = Image.new("RGBA", (940, 160), (0, 0, 0, 0))
            reveal_up(tmp, lab, 470, 80, (t - u["lt"]) / 0.3)
            c.alpha_composite(tmp, (0, 620))
        if u["n"] == 1 and t >= t_sumi2 - 0.05:
            p = (t - t_sumi2 + 0.05) / 0.35
            b2 = bal.resize((max(1, int(bal.width * (0.5 + 0.5 * back(p)))), max(1, int(bal.height * (0.5 + 0.5 * back(p))))))
            c.alpha_composite(with_alpha(b2, ease(p * 2)), (560 - b2.width // 2 + 120, 120 - b2.height // 2 + 40))
        if u["n"] == 3 and t >= t_porta:
            p = (t - t_porta) / 0.4
            hs = kimg("♥", 70, C["vermelho_ume"]) if False else timg("♥", 90, C["vermelho_ume"], 400)
            for k, (hx, hy) in enumerate([(760, 200), (820, 300), (700, 120)]):
                q = ease((p - k * 0.2) * 1.5)
                if q > 0:
                    c.alpha_composite(with_alpha(hs, q), (hx, int(hy - 40 * q)))
        return c

    # ---------------- renderização de cada cena (quadro inteiro)
    def scene_hook(t):
        fr = drift(BG_VERDE, t).copy()
        tag(fr, True)
        out_p = ease((t - t_aprenda + 0.05) / 0.25)
        lift = 270 * ease((t - t_japao + 0.35) / 0.45)     # bloco sobe para a ilustração entrar
        for im, y, t0, mode in hook_lines:
            yy = y - lift - 300 * out_p
            a = 1 - out_p
            if mode == "up":
                tmp_p = (t - t0) / 0.3
                if tmp_p > 0:
                    reveal_up(fr, im, W / 2, yy, tmp_p, a)
            else:
                if t >= t0:
                    p = (t - t0) / 0.35
                    put(fr, im, W / 2, yy, a=ease(p * 2) * a, sc=0.55 + 0.45 * back(p))
        if t >= t_japao - 0.3:
            p = ease((t - t_japao + 0.3) / 0.6)
            put(fr, ilu_jp, W / 2, 1150 + 400 * (1 - p) - 200 * out_p, a=p * (1 - out_p))
        if t >= t_aprenda:
            p = (t - t_aprenda) / 0.35
            put(fr, aprenda, W / 2, 700, a=ease(p * 2), sc=0.6 + 0.4 * back(p))
            bounce = 18 * abs(math.sin((t - t_aprenda) * 6))
            put(fr, seta, W / 2, 880 + bounce, a=ease((p - 0.4) * 2))
        return fr

    def scene_main(t):
        fr = BG_CREME.copy()
        tag(fr, False)
        # --- kana grandes / morph para cabeçalho
        if t < morph0:
            for i in range(5):
                if t >= kana_t[i]:
                    p = (t - kana_t[i]) / 0.3
                    cx = row_x0 + i * cell
                    put(fr, kana_imgs[i], cx, 660, a=ease(p * 2.5), sc=1.5 - 0.5 * back(p))
                    if t >= kana_t[i] + 0.05:
                        q = (t - kana_t[i] - 0.05) / 0.25
                        put(fr, sil_imgs[i], cx, 815 + 20 * (1 - ease(q)), a=ease(q))
            if t >= band_t:
                p = ease((t - band_t) / 0.35)
                fr.alpha_composite(with_alpha(band, p), (int((W - 900) / 2 - 300 * (1 - p)), 930))
                put(fr, significado, W / 2, 1150, a=ease((t - band_t - 0.25) / 0.3))
        else:
            p = ease((t - morph0) / (morph1 - morph0))
            sc = 1 + (HEAD_SC - 1) * p
            cy = (660 - 130 + block.height / 2) * (1 - p) + HEAD_Y * p
            put(fr, block, W / 2, cy, sc=sc)
        # --- cartões dos usos
        if t >= usos[0]["t0"]:
            k = max(i for i, u in enumerate(usos) if t >= u["t0"])
            u = usos[k]
            ci = card_img(u, t)
            cy = 960
            if k == 0:
                p = ease((t - u["t0"]) / 0.4)
                put(fr, ci, W / 2, cy + 500 * (1 - p), a=p)
            else:
                p = (t - u["t0"]) / 0.4
                if p < 1:
                    e = ease(p)
                    prev = card_img(usos[k - 1], t)
                    put(fr, prev, W / 2 - e * W, cy)
                    put(fr, ci, W / 2 + (1 - e) * W, cy)
                else:
                    put(fr, ci, W / 2, cy)
        return fr

    tres = timg("3", 440, C["creme_fundo"])
    situ = timg("SITUAÇÕES", 120, C["creme_fundo"])
    igual = timg("=", 150, OURO)
    umap = timg("1 PALAVRA SÓ", 124, OURO)
    kana_head = kimg("すみません", 120, C["creme_fundo"])

    def scene_tres(t):
        fr = drift(BG_VERMELHO, t).copy()
        tag(fr, True)
        pop_in(fr, kana_head, W / 2, 330, t, t_tres)
        pop_in(fr, tres, W / 2, 640, t, t_tres + 0.02)
        if t >= t_tres + 0.2:
            reveal_up(fr, situ, W / 2, 900, (t - t_tres - 0.2) / 0.3)
        pop_in(fr, igual, W / 2, 1050, t, t_uma2 - 0.15)
        pop_in(fr, umap, W / 2, 1200, t, t_uma2)
        return fr

    # ================= segunda metade =================
    t_O, t_U, t_some, t_fala = T(find("o", start=find("dica"))), T(find("u", start=find("dica"))), T(find("some")), T(find("fala"))
    t_agora, t_kore = T(find("agora")), T(find("kore kudasai"))
    t_isso, t_apontou, t_kore2, t_pronto = T(find("isso")), T(find("apontou")), T(find("kore kudasai", 2)), T(find("pronto"))
    i_E = find("cuidado") - 1
    t_E, t_cuidado, t_com = T(i_E), T(find("cuidado")), T(find("com", start=find("cuidado")))
    t_dai, t_quer, t_ta = T(find("daijoubu desu")), T(find("quer")), T(find("tá"))
    t_mas, t_pergunta, t_sacola = T(find("mas")), T(find("pergunta")), T(find("sacola"))
    t_responde, t_entende, t_nao, t_ai = T(find("responde")), T(find("entende")), T(find("não")), T(find("aí"))
    t_salva, t_viagem, t_comenta = T(find("salva")), T(find("viagem")), T(find("comenta"))
    t_ensino, t_pedir_c, t_sem = T(find("ensino")), T(find("pedir", start=find("ensino"))), T(find("sem", start=find("ensino")))
    i_E2 = find("segue") - 1
    t_E2, t_segue, t_matri, t_abrem = T(i_E2), T(find("segue")), T(find("matrículas")), T(find("abrem"))

    # palavras que já aparecem em destaque no topo -> sem legenda embaixo
    def rng_(a, b):
        return {id(words[i]) for i in range(a, b + 1)}
    kin = set()
    kin |= rng_(0, find("sumimasen"))
    kin |= rng_(find("chamar"), find("sumimasen", 2))
    kin |= rng_(find("pedir"), find("pedir") + 1)
    kin |= rng_(find("agradecer"), find("agradecer"))
    kin |= rng_(find("três"), find("dica") - 1)
    kin |= rng_(find("dica"), find("cardápio"))
    kin |= rng_(find("kore kudasai", 2), find("bem"))
    kin |= rng_(find("quer", 2), find("sacola"))
    kin |= rng_(find("não"), find("obrigado"))
    kin |= rng_(find("salva"), find("viagem"))
    kin |= rng_(find("comenta"), find("comenta") + 2)
    kin |= rng_(find("pedir", start=find("ensino")), len(words) - 1)
    kin = frozenset(kin)

    # ---------- utilidades de kana grande + cabeçalho
    def kana_bloco(kanas, sils, band_txt, ks, cell, kcol, band_bg, band_fg, sil_col):
        kimgs = [kimg(k, ks, kcol) for k in kanas]
        simgs = [timg(x, 54, sil_col) for x in sils] if sils else []
        bt_ = timg(band_txt, 84, band_fg, 700, 0.06)
        bw = max(bt_.width + 120, 700)
        bd = Image.new("RGBA", (bw, 136), (0, 0, 0, 0))
        ImageDraw.Draw(bd).rounded_rectangle((0, 0, bw - 1, 135), radius=34, fill=band_bg)
        bd.alpha_composite(bt_, ((bw - bt_.width) // 2, (136 - bt_.height) // 2))
        blk = Image.new("RGBA", (W, 520), (0, 0, 0, 0))
        x0 = W / 2 - cell * (len(kanas) - 1) / 2
        for i, im in enumerate(kimgs):
            blk.alpha_composite(im, (int(x0 + i * cell - im.width / 2), int(110 - im.height / 2)))
        blk.alpha_composite(bd, ((W - bw) // 2, 290))
        blk = blk.crop(blk.getbbox())
        return dict(k=kimgs, s=simgs, band=bd, blk=blk, cell=cell, x0=x0, n=len(kanas))

    def kana_reveal(fr, b, t, t0, step, y, band_t_, morph=None):
        if morph and t >= morph[0]:
            p = ease((t - morph[0]) / (morph[1] - morph[0]))
            sc = 1 + (HEAD_SC - 1) * p
            cy = (y - 110 + b["blk"].height / 2) * (1 - p) + HEAD_Y * p
            put(fr, b["blk"], W / 2, cy, sc=sc)
            return
        for i in range(b["n"]):
            ti = t0 + i * step
            if t >= ti:
                pp = (t - ti) / 0.3
                cx = b["x0"] + i * b["cell"]
                put(fr, b["k"][i], cx, y, a=ease(pp * 2.5), sc=1.5 - 0.5 * back(pp))
                if b["s"] and t >= ti + 0.05:
                    q = (t - ti - 0.05) / 0.25
                    put(fr, b["s"][i], cx, y + 150 + 20 * (1 - ease(q)), a=ease(q))
        if t >= band_t_:
            pp = ease((t - band_t_) / 0.35)
            bw = b["band"].width
            fr.alpha_composite(with_alpha(b["band"], pp), (int((W - bw) / 2 - 300 * (1 - pp)), int(y + 250)))

    def check(size, col):
        im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(im).line([(size * 0.15, size * 0.55), (size * 0.42, size * 0.8), (size * 0.88, size * 0.2)],
                                fill=col, width=int(size * 0.14), joint="curve")
        return im

    def xis(size, col):
        im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(im); wd = int(size * 0.16)
        d.line([(size * 0.15, size * 0.15), (size * 0.85, size * 0.85)], fill=col, width=wd)
        d.line([(size * 0.85, size * 0.15), (size * 0.15, size * 0.85)], fill=col, width=wd)
        return im

    BG_SALVIA = Image.new("RGBA", (W, H), C["salvia"])
    _a = BG_CREME.copy(); _a.putalpha(70)
    BG_SALVIA.alpha_composite(_a)

    # ---------- E: dica de pronúncia
    _dt = timg("DICA DE PRONÚNCIA", 58, C["creme_fundo"])
    _pw = _dt.width + 110
    dica_pill = Image.new("RGBA", (_pw, 120), (0, 0, 0, 0))
    ImageDraw.Draw(dica_pill).rounded_rectangle((0, 0, _pw - 1, 119), radius=60, fill=C["verde_aoi"])
    dica_pill.alpha_composite(_dt, ((_pw - _dt.width) // 2, (120 - _dt.height) // 2))
    letras = list("SUMIMASEN")
    LS = 150
    let_imgs = [timg(ch, LS, TEXTO) for ch in letras]
    u_red = timg("U", LS, C["vermelho_ume"])
    apos = timg("’", LS, C["vermelho_ume"])
    fala_lbl = timg("FALA ASSIM:", 64, C["verde_aoi"])
    som_lbl = timg("o “u” quase some", 56, TEXTO, 600, 0.02)
    ouvido = kimg("すみません", 96, C["verde_aoi"])

    def scene_dica(t):
        fr = BG_SALVIA.copy()
        tag(fr, False)
        pop_in(fr, dica_pill, W / 2, 400, t, t_dica)
        if t >= t_O - 0.1:
            pu = ease((t - t_some) / 0.45) if t >= t_some else 0          # u some
            pa = ease((t - t_fala) / 0.35) if t >= t_fala else 0          # apóstrofo + vermelho
            gap = 6
            ws = [im.width for im in let_imgs]
            ws[1] = ws[1] * (1 - pu) + apos.width * pa
            tot = sum(ws) + gap * (len(ws) - 1)
            x = W / 2 - tot / 2
            app = ease((t - t_O + 0.1) / 0.3)
            for i, im in enumerate(let_imgs):
                cx = x + ws[i] / 2
                if i == 1:
                    if pu < 1:
                        img_u = u_red if t >= t_U else im
                        bob = -30 * math.sin(min(1, (t - t_U) / 0.3) * math.pi) if t_U <= t < t_U + 0.3 else 0
                        put(fr, img_u, cx, 760 + bob - 80 * pu, a=app * (1 - pu), sc=1 - 0.6 * pu)
                    if pa > 0:
                        put(fr, apos, cx, 730, a=pa)
                else:
                    col_im = timg(letras[i], LS, C["vermelho_ume"]) if pa > 0.5 else im
                    put(fr, col_im, cx, 760, a=app)
                x += ws[i] + gap
            if t >= t_some:
                put(fr, som_lbl, W / 2, 930, a=ease((t - t_some) / 0.3) * (1 - ease((t - t_fala) / 0.2)))
            if t >= t_fala:
                pop_in(fr, fala_lbl, W / 2, 600, t, t_fala)
                pop_in(fr, ouvido, W / 2, 960, t, t_fala + 0.15)
        return fr

    # ---------- F: kore kudasai + cardápio
    kb = kana_bloco(["こ", "れ", "く", "だ", "さ", "い"], ["KO", "RE", "KU", "DA", "SA", "I"], "KO.RE  KU.DA.SA.I",
                    150, 160, C["verde_aoi"], C["vermelho_ume"], C["creme_fundo"], C["vermelho_ume"])
    agora1, agora2 = timg("AGORA JUNTA", 110, TEXTO), timg("COM ESSA", 110, C["verde_aoi"])
    isso_lbl = timg("= ISSO, POR FAVOR", 70, C["verde_aoi"])
    menu = IL.png(IL.cardapio(), 640)
    dedo = IL.png(IL.dedo(), 330)
    aponta = timg("APONTOU NO CARDÁPIO…", 60, C["verde_aoi"])
    bal_kore = IL.png(IL.balao(440), 380)
    bal_kore.alpha_composite(kimg("これください!", 52, TEXTO), (36, 40))
    k_morph = (t_apontou - 0.25, t_apontou + 0.2)

    def scene_kore(t):
        fr = BG_CREME.copy()
        tag(fr, False)
        if t < t_kore:
            po = ease((t - t_kore + 0.25) / 0.2)
            reveal_up(fr, agora1, W / 2, 640 - 200 * po, (t - t_agora) / 0.3, 1 - po)
            reveal_up(fr, agora2, W / 2, 790 - 200 * po, (t - t_agora - 0.35) / 0.3, 1 - po)
        kana_reveal(fr, kb, t, t_kore, 0.09, 640, t_kore + 0.55, morph=k_morph)
        if t_isso <= t < k_morph[0] + 0.2:
            a = 1 - ease((t - k_morph[0]) / 0.2)
            pop_in(fr, with_alpha(isso_lbl, a), W / 2, 1150, t, t_isso)
        if t >= t_apontou - 0.05:
            p = ease((t - t_apontou + 0.05) / 0.4)
            put(fr, menu, W / 2, 900 + 500 * (1 - p), a=p)
            if t >= t_apontou + 0.25:
                q = ease((t - t_apontou - 0.25) / 0.35)
                tap = 14 * abs(math.sin((t - t_apontou) * 7))
                put(fr, dedo, W / 2 + 260 + 300 * (1 - q) + tap, 830, a=q)
            reveal_up(fr, aponta, W / 2, 1290, (t - t_apontou) / 0.3)
        if t >= t_kore2 - 0.05:
            pop_in(fr, bal_kore, W / 2 + 150, 560, t, t_kore2 - 0.05)
        if t >= t_pronto:
            pp = (t - t_pronto) / 0.18
            sc = 1.6 - 0.65 * ease(pp) if pp < 1 else 0.95 + 0.05 * ease((t - t_pronto - 0.18) / 0.1)
            put(fr, stamp_pf, W / 2, 900, sc=sc)
        return fr

    stamp_pf = RA.carimbo("PEDIDO FEITO!")

    # ---------- G1: cuidado + daijoubu desu
    db = kana_bloco(["だ", "い", "じょ", "う", "ぶ", "で", "す"], ["DA", "I", "JO", "U", "BU", "DE", "SU"], "DAI.JO.U.BU  DE.SU",
                    116, 140, C["creme_fundo"], C["creme_fundo"], C["vermelho_ume"], OURO)
    cuid = timg("CUIDADO", 170, C["creme_fundo"])
    com_essa = timg("COM ESSA!", 100, OURO)
    alerta = Image.new("RGBA", (190, 170), (0, 0, 0, 0))
    ImageDraw.Draw(alerta).polygon([(95, 6), (184, 164), (6, 164)], fill=OURO)
    _ex = timg("!", 110, C["vermelho_ume"]); alerta.alpha_composite(_ex, (95 - _ex.width // 2, 100 - _ex.height // 2 + 6))
    quer_d = timg("QUER DIZER", 64, C["creme_fundo"])
    ok_pill = Image.new("RGBA", (680, 150), (0, 0, 0, 0))
    ImageDraw.Draw(ok_pill).rounded_rectangle((0, 0, 679, 149), radius=75, fill=C["creme_fundo"])
    ok_pill.alpha_composite(check(90, C["verde_aoi"]), (50, 30))
    _ot = timg("TÁ TUDO BEM", 74, C["verde_aoi"]); ok_pill.alpha_composite(_ot, (160 + (500 - _ot.width) // 2, (150 - _ot.height) // 2))

    def scene_dai(t):
        fr = drift(BG_VERMELHO, t).copy()
        tag(fr, True)
        if t < t_dai + 0.1:
            po = ease((t - t_dai + 0.2) / 0.25)
            shake = int(8 * math.sin((t - t_cuidado) * 60)) if t_cuidado <= t <= t_cuidado + 0.3 else 0
            pop_in(fr, with_alpha(alerta, 1 - po), W / 2 + shake, 520 - 200 * po, t, t_E)
            pop_in(fr, with_alpha(cuid, 1 - po), W / 2 + shake, 730 - 200 * po, t, t_cuidado)
            pop_in(fr, with_alpha(com_essa, 1 - po), W / 2, 880 - 200 * po, t, t_com)
        if t >= t_dai:
            kana_reveal(fr, db, t, t_dai, 0.08, 620, t_dai + 0.6)
        if t >= t_quer:
            reveal_up(fr, quer_d, W / 2, 1110, (t - t_quer) / 0.3)
        if t >= t_ta:
            pop_in(fr, ok_pill, W / 2, 1250, t, t_ta)
        return fr

    # ---------- G2: o caixa pergunta
    head_dai = kimg("だいじょうぶです", 74, TEXTO)
    def _pess(cor):
        im = IL.png(IL._wrap(IL.pessoa(300, 250, cor)), 900)
        im = im.crop(im.getbbox())
        return im.resize((int(im.width * 330 / im.height), 330), Image.LANCZOS)
    caixa = _pess(C["verde_aoi"])
    voce = _pess(C["coral"])
    lbl_caixa, lbl_voce = timg("CAIXA", 46, C["verde_aoi"]), timg("VOCÊ", 46, C["coral"])
    b_caixa = IL.png(IL.balao(470), 420)
    b_caixa.alpha_composite(kimg("袋いりますか？", 54, TEXTO), (34, 36))
    tr_caixa = timg("“quer sacola?”", 54, TEXTO, 600, 0.01)
    _bv = IL.png(IL.balao(560), 560).transpose(Image.FLIP_LEFT_RIGHT)
    _kt = kimg("だいじょうぶです", 52, TEXTO)
    _bv.alpha_composite(_kt, ((_bv.width - _kt.width) // 2 + 6, 44)); b_voce = _bv
    nao_stamp = RA.carimbo("NÃO, OBRIGADO")
    bag = IL.png(IL.sacola(), 260)

    def scene_caixa(t):
        fr = BG_CREME.copy()
        tag(fr, False)
        put(fr, head_dai, W / 2, 330)
        p = ease((t - t_mas + 0.2) / 0.4)
        put(fr, caixa, 230 - 300 * (1 - p), 1150, a=p)
        put(fr, voce, 850 + 300 * (1 - p), 1150, a=p)
        put(fr, lbl_caixa, 230, 1350, a=p); put(fr, lbl_voce, 850, 1350, a=p)
        fade_b = 1 - ease((t - t_nao + 0.25) / 0.2)       # balões saem quando entra o carimbo
        if t >= t_pergunta:
            pop_in(fr, with_alpha(b_caixa, fade_b), 330, 560, t, t_pergunta)
        if t >= t_sacola:
            reveal_up(fr, tr_caixa, 330, 720, (t - t_sacola) / 0.3, fade_b)
            pop_in(fr, bag, 540, 1080, t, t_sacola)
        if t >= t_responde:
            pop_in(fr, with_alpha(b_voce, fade_b), 690, 830, t, t_responde)
        if t >= t_entende + 0.15:
            put(fr, xis(260, C["vermelho_ume"]), 540, 1080, a=ease((t - t_entende - 0.15) / 0.2))
        if t >= t_nao - 0.1:
            pp = (t - t_nao + 0.1) / 0.18
            sc = 1.6 - 0.65 * ease(pp) if pp < 1 else 0.95 + 0.05 * ease((t - t_nao + 0.1 - 0.18) / 0.1)
            put(fr, nao_stamp, W / 2, 680, sc=sc * 1.15)
        return fr

    # ---------- G3: sem sacola
    pilha = IL.png(IL.itens_na_mao(), 640)
    sem_sac = timg("SEM SACOLA!", 132, C["vermelho_ume"])
    na_mao = timg("tudo na mão", 66, TEXTO, 600, 0.02)

    def scene_semsacola(t):
        fr = BG_CREME.copy()
        tag(fr, False)
        wob = 5 * math.sin(t * 9)
        il = pilha.rotate(wob, resample=Image.BICUBIC)
        pop_in(fr, il, W / 2, 1000, t, t_ai)
        pop_in(fr, sem_sac, W / 2, 470, t, t_ai + 0.1)
        if t >= T(find("carregando")):
            reveal_up(fr, na_mao, W / 2, 610, (t - T(find("carregando"))) / 0.3)
        return fr

    # ---------- H: CTA
    salva = timg("SALVA", 190, OURO)
    esse_v = timg("ESSE VÍDEO", 96, C["creme_fundo"])
    pra_v = timg("PRA SUA VIAGEM", 86, C["creme_fundo"])
    mark = IL.png(IL.marcador(), 200)
    plane = IL.png(IL.aviao(), 300)
    coment = timg("COMENTA", 140, OURO)
    p2a, p2b, p2c = timg("NA PARTE 2:", 70, C["creme_fundo"]), timg("COMO PEDIR COMIDA", 84, OURO), timg("SEM APERTO", 84, C["creme_fundo"])

    def scene_cta(t):
        fr = drift(BG_VERDE, t).copy()
        tag(fr, True)
        if t < t_comenta + 0.1:
            po = ease((t - t_comenta + 0.25) / 0.25)
            pop_in(fr, with_alpha(mark, 1 - po), W / 2, 470 - 200 * po, t, t_salva - 0.05)
            pop_in(fr, with_alpha(salva, 1 - po), W / 2, 720 - 200 * po, t, t_salva)
            if t >= T(find("esse")):
                reveal_up(fr, esse_v, W / 2, 880 - 200 * po, (t - T(find("esse"))) / 0.3, 1 - po)
            if t >= t_viagem - 0.1:
                reveal_up(fr, pra_v, W / 2, 1010 - 200 * po, (t - t_viagem + 0.1) / 0.3, 1 - po)
                fly = ease((t - t_viagem) / 0.9)
                put(fr, plane, -200 + fly * 1480, 1240 - fly * 160, a=(1 - po))
        else:
            pop_in(fr, coment, W / 2, 470, t, t_comenta)
            n = int(max(0, (t - t_comenta - 0.25) / 0.05)) if t >= t_comenta + 0.25 else 0
            txt = "parte 2!!"[:n]
            done = (t - (t_comenta + 0.25 + 9 * 0.05)) if n >= 9 else None
            cb = RA.comentario(txt, done)
            pop_in(fr, cb, W / 2, 700, t, t_comenta + 0.05)
            if t >= t_ensino - 0.2:
                reveal_up(fr, p2a, W / 2, 930, (t - t_ensino + 0.2) / 0.3)
            if t >= t_pedir_c:
                reveal_up(fr, p2b, W / 2, 1060, (t - t_pedir_c) / 0.3)
            if t >= t_sem:
                reveal_up(fr, p2c, W / 2, 1180, (t - t_sem) / 0.3)
        return fr

    # ---------- I: final
    logo = R.fit(Image.open(os.path.join(R.MARCA, "logos", "aoi-vertical-cor.png")).convert("RGBA"), 470)
    matri = timg("MATRÍCULAS", 128, C["verde_aoi"])
    breve = timg("EM BREVE", 128, C["vermelho_ume"])

    def scene_fim(t):
        fr = BG_CREME.copy()
        pop_in(fr, logo, W / 2, 520, t, t_E2 - 0.1)
        if t >= t_segue:
            q = back((t - t_segue) / 0.4)
            pulse = 1 + 0.04 * math.sin((t - t_segue) * 2 * math.pi / (2 * R.BEAT))
            btn = RA.cta_button("SIGA @espacoaoi", scale=max(0.3, 1.25 * q * pulse))
            put(fr, btn, W / 2, 900)
        if t >= t_matri:
            reveal_up(fr, matri, W / 2, 1130, (t - t_matri) / 0.3)
        if t >= t_abrem - 0.1:
            pop_in(fr, breve, W / 2, 1285, t, t_abrem - 0.1)
        return fr

    # ---------- linha do tempo (cena, início) + transições
    TR1 = (t_aprenda + 0.4, t_sumi - 0.02)
    TR2 = (t_tres - 0.3, t_tres + 0.02)
    seq = [
        (0.0, scene_hook, None),
        (TR1[1], scene_main, ("ume", TR1[1] - TR1[0])),
        (TR2[1], scene_tres, ("wipe", TR2[1] - TR2[0], C["laranja"])),
        (t_dica - 0.05, scene_dica, ("push", 0.35)),
        (t_agora - 0.05, scene_kore, ("push", 0.35)),
        (t_E - 0.02, scene_dai, ("wipe", 0.32, C["laranja"])),
        (t_mas - 0.05, scene_caixa, ("push", 0.35)),
        (t_ai - 0.05, scene_semsacola, ("push", 0.3)),
        (t_salva - 0.05, scene_cta, ("wipe", 0.32, C["salvia"])),
        (t_E2 - 0.05, scene_fim, ("ume", 0.4)),
    ]
    if amostra:
        seq = [x for x in seq if x[0] < END]

    def frame(t):
        k = max(i for i, x in enumerate(seq) if t >= x[0] - (x[2][1] if x[2] else 0))
        st, fn, tr = seq[k]
        if tr and t < st:
            d = tr[1]
            p = (t - (st - d)) / d
            old = seq[k - 1][1](t)
            new = fn(t)
            if tr[0] == "ume":
                fr = ume_reveal(old, new, p)
            elif tr[0] == "wipe":
                fr = diag_wipe(old, new, p, tr[2])
            else:
                fr = push(old, new, p)
        else:
            fr = fn(t)
        caption(fr, caps, t, voice_end, kin)
        return fr

    # ---------------- vídeo
    vid = f"{OUT}/video.mp4"
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                             "-pix_fmt", "yuv420p", vid], stdin=subprocess.PIPE)
    for fi in range(nframes):
        proc.stdin.write(frame(fi / FPS).tobytes())
        if fi % 150 == 0:
            print(f"  quadro {fi}/{nframes}", flush=True)
    proc.stdin.close(); proc.wait()

    # ---------------- sons
    evs = [(t_uma, RA.sfx_carimbo()), (t_japao - 0.05, RA.sfx_pop()), (TR1[0], RA.sfx_whoosh()),
           (band_t, RA.sfx_ding()), (morph0, RA.sfx_whoosh(0.3)), (t_sumi2, RA.sfx_pop()),
           (usos[1]["t0"], RA.sfx_whoosh(0.32)), (t_esbarra, RA.sfx_carimbo()), (usos[2]["t0"], RA.sfx_whoosh(0.32)),
           (t_porta, RA.sfx_pop()), (TR2[0], RA.sfx_whoosh()), (t_tres + 0.02, RA.sfx_carimbo()), (t_uma2, RA.sfx_pop()),
           (t_dica - 0.4, RA.sfx_whoosh(0.32)), (t_U, RA.sfx_pop()), (t_some, RA.sfx_whoosh(0.3)), (t_fala, RA.sfx_ding()),
           (t_agora - 0.4, RA.sfx_whoosh(0.32)), (t_kore + 0.5, RA.sfx_ding()), (t_apontou, RA.sfx_whoosh(0.3)),
           (t_kore2, RA.sfx_pop()), (t_pronto, RA.sfx_carimbo()), (t_E - 0.34, RA.sfx_whoosh()), (t_cuidado, RA.sfx_alerta()),
           (t_dai + 0.6, RA.sfx_ding()), (t_ta, RA.sfx_pop()), (t_mas - 0.4, RA.sfx_whoosh(0.32)), (t_pergunta, RA.sfx_pop()),
           (t_sacola, RA.sfx_pop()), (t_responde, RA.sfx_pop()), (t_nao - 0.1, RA.sfx_carimbo()), (t_ai, RA.sfx_alerta()),
           (t_salva - 0.37, RA.sfx_whoosh()), (t_salva + 0.1, RA.sfx_pop()), (t_viagem, RA.sfx_whoosh(0.5)),
           (t_comenta, RA.sfx_pop()), (t_comenta + 0.25 + 9 * 0.05 + 0.05, RA.sfx_clique()), (t_pedir_c, RA.sfx_pop()),
           (t_E2 - 0.45, RA.sfx_whoosh()), (t_segue, RA.sfx_ding()), (t_abrem, RA.sfx_pop())]
    evs = [e for e in evs if e[0] < END]
    evs.sort(key=lambda e: e[0])
    kept, last = [], -9
    for tt, snd in evs:
        if tt - last >= 0.6:
            kept.append((tt, snd)); last = tt
    sfx = np.zeros(int((END + 2) * SR))
    for tt, snd in kept:
        i = int(tt * SR); sfx[i:i + len(snd)] += snd[: len(sfx) - i]
    ticks = list(kana_t) + [t_kore + i * 0.09 for i in range(6)] + [t_dai + i * 0.08 for i in range(7)] \
        + [t_comenta + 0.25 + i * 0.05 for i in range(9)]
    for k, kt in enumerate(ticks):                      # "tique" a cada kana / tecla
        if kt < END:
            snd = RA.sfx_tecla(k) * 1.6; i = int(kt * SR); sfx[i:i + len(snd)] += snd
    sfx_path = f"{OUT}/sfx.wav"
    with wave.open(sfx_path, "wb") as wv:
        wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR)
        wv.writeframes((np.clip(sfx, -1, 1) * 32767).astype("<i2").tobytes())
    mpath = f"{OUT}/musica.wav"
    R.music(mpath, END)
    final = f"{OUT}/aoi-reels-sumimasen-{'amostra' if amostra else 'completo'}.mp4"
    RA.sh(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", voice_wav, "-i", mpath, "-i", sfx_path, "-filter_complex",
           f"[1:a]atrim=0:{voice_end},afade=t=out:st={voice_end - 0.08}:d=0.08,apad=whole_dur={END},asplit=2[v1][v2];"
           "[2:a]volume=0.22[m];[m][v2]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=400[md];"
           f"[3:a]atrim=0:{END},volume=0.9[fx];"
           "[v1][md][fx]amix=inputs=3:normalize=0,aresample=48000,"
           "loudnorm=I=-14:TP=-1.5:LRA=9,alimiter=limit=0.84:attack=0.5:release=40:level=disabled[a]",
           "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ac", "2",
           "-movflags", "+faststart", "-shortest", final])
    print(f"sons: {len(kept)} + 5 tiques")
    print("ok:", final)


if __name__ == "__main__":
    main()
