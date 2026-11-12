#!/usr/bin/env python3
"""Reels "A palavra que salva sua viagem ao Japão" — vídeo gerado a partir do áudio da professora.

Uso:
  AUDIO=voz.m4a WORDS=transcricao.json WORK=/tmp/work FONTS=/fonts/ttf python3 reels_audio.py

Pipeline:
  1. limpa o áudio (redução de ruído, EQ, compressão) e corta silêncios > 0,3 s
  2. remapeia o tempo de cada palavra (transcrição Whisper) para o áudio cortado
  3. anima a personagem (boca sincronizada pela energia da voz, piscadas, expressões)
  4. legenda palavra a palavra + cartões com destaque para o japonês
  5. trilha de koto bem baixa por baixo da voz
"""
import io, json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import cairosvg

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ["WORK"]
os.environ.setdefault("BRUTOS", WORK)
sys.path.insert(0, HERE)
import render as R                      # reaproveita fontes, cartões e trilha do primeiro Reels
from personagem import personagem_svg

AUDIO = os.environ["AUDIO"]
WORDS = os.environ["WORDS"]
W, H, FPS, SR = R.W, R.H, R.FPS, 48000
C, TEXT = R.C, R.TEXT
os.makedirs(f"{WORK}/ra", exist_ok=True)


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


# ======================================================== 1. áudio
def decode(path, filters=None):
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR)]
    if filters:
        cmd += ["-af", filters]
    cmd += ["-f", "f32le", "-"]
    return np.frombuffer(sh(cmd, capture_output=True).stdout, dtype="<f4").copy()


def silences(x, thr_db=-35, min_d=0.30):
    hop = int(0.01 * SR)
    n = len(x) // hop
    rms = np.sqrt(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    quiet = 20 * np.log10(rms) < thr_db
    out, start = [], None
    for i, q in enumerate(quiet):
        if q and start is None:
            start = i
        if not q and start is not None:
            if (i - start) * 0.01 >= min_d:
                out.append((start * 0.01, i * 0.01))
            start = None
    if start is not None and (n - start) * 0.01 >= min_d:
        out.append((start * 0.01, n * 0.01))
    return out


def build_audio():
    clean = decode(AUDIO, "highpass=f=85,afftdn=nf=-28:nr=12,lowpass=f=12000")
    sil = silences(clean)
    keep_pad = 0.11
    # intervalos mantidos
    cuts = []
    for s, e in sil:
        if s <= 0.01:                       # silêncio inicial
            cuts.append((0.0, max(0.0, e - 0.12)))
        elif e >= len(clean) / SR - 0.02:   # silêncio final
            cuts.append((s + 0.35, len(clean) / SR))
        else:
            cuts.append((s + keep_pad, e - keep_pad))
    cuts = [(a, b) for a, b in cuts if b - a > 0.02]
    keeps, t = [], 0.0
    for a, b in cuts:
        if a > t:
            keeps.append((t, a))
        t = b
    if t < len(clean) / SR:
        keeps.append((t, len(clean) / SR))
    fade = int(0.012 * SR)
    parts = []
    for a, b in keeps:
        seg = clean[int(a * SR): int(b * SR)].copy()
        if len(seg) > 2 * fade:
            seg[:fade] *= np.linspace(0, 1, fade)
            seg[-fade:] *= np.linspace(1, 0, fade)
        parts.append(seg)
    voice = np.concatenate(parts)
    raw = f"{WORK}/ra/voz_cortada.f32"
    voice.astype("<f4").tofile(raw)
    out = f"{WORK}/ra/voz.wav"
    sh(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", raw,
        "-af", "equalizer=f=200:t=q:w=1:g=-2,equalizer=f=3500:t=q:w=1.2:g=3,"
               "acompressor=threshold=-22dB:ratio=3:attack=8:release=120:makeup=4,"
               "loudnorm=I=-16:TP=-1.5:LRA=9,aresample=48000",
        "-ac", "1", out])

    def remap(t):
        removed = 0.0
        for a, b in cuts:
            if t >= b:
                removed += b - a
            elif t > a:
                return a - removed
        return t - removed
    return out, remap, len(voice) / SR, sum(b - a for a, b in cuts)


# ======================================================== 2. palavras
JP = {  # romaji -> (kana, significado)
    "sumimasen": ("すみません", "com licença · desculpa · obrigado"),
    "kore kudasai": ("これください", "isso, por favor"),
    "daijoubu desu": ("だいじょうぶです", "tá tudo bem"),
}


def load_words(remap):
    d = json.load(open(WORDS))
    ws = [dict(w=w["w"].strip(), s=remap(w["s"]), e=remap(w["e"])) for seg in d for w in seg["words"]]
    # correções da transcrição (texto do roteiro)
    def merge(i, j, text):
        ws[i:j + 1] = [dict(w=text, s=ws[i]["s"], e=ws[j]["e"])]
    txt = [w["w"].lower().strip(",.") for w in ws]
    # "arroba e o espaço ao oi" -> @espacoaoi
    for i in range(len(txt) - 5):
        if txt[i:i + 6] == ["arroba", "e", "o", "espaço", "ao", "oi"]:
            merge(i, i + 5, "@espacoaoi,")
            break
    txt = [w["w"].lower().strip(",.") for w in ws]
    for i in range(len(txt) - 1):
        if txt[i] == "a" and txt[i + 1] == "perto":
            merge(i, i + 1, "aperto.")
            break
    out = []
    i = 0
    while i < len(ws):
        w = ws[i]
        low = w["w"].lower().strip(",.")
        nxt = ws[i + 1]["w"].lower().strip(",.") if i + 1 < len(ws) else ""
        if low in ("kore", "daijoubu") and nxt in ("kudasai", "desu"):
            out.append(dict(w=f"{low} {nxt}", s=w["s"], e=ws[i + 1]["e"], jp=f"{low} {nxt}",
                            punct=ws[i + 1]["w"][-1] in ",." ))
            i += 2
            continue
        if low == "sumimasen":
            out.append(dict(w=low, s=w["s"], e=w["e"], jp="sumimasen", punct=w["w"][-1] in ",."))
        else:
            out.append(dict(w=w["w"].strip(",."), s=w["s"], e=w["e"], jp=None, punct=w["w"][-1] in ",."))
        i += 1
    # a 3ª ocorrência de sumimasen é a dica de pronúncia
    n = 0
    for w in out:
        if w["jp"] == "sumimasen":
            n += 1
            if n == 3:
                w["w"] = "s'mimasen"
    return out


def chunks(words, maxc=20):
    res, cur = [], []
    for w in words:
        if w["jp"]:
            if cur:
                res.append(cur); cur = []
            res.append([w])
            continue
        if cur and (len(" ".join(x["w"] for x in cur + [w])) > maxc):
            res.append(cur); cur = []
        cur.append(w)
        if w["punct"] or len(cur) >= 4:
            res.append(cur); cur = []
    if cur:
        res.append(cur)
    return res


# ======================================================== 3. elementos visuais
def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def back(x):  # ease-out com leve "pulo"
    x = min(max(x, 0.0), 1.0)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"


def emoji(ch, size):
    f = ImageFont.truetype(EMOJI, 109)
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((80, 80), ch, font=f, embedded_color=True, anchor="mm")
    im = im.crop(im.getbbox())
    return im.resize((round(im.width * size / im.height), size), Image.LANCZOS)


def background():
    bg = Image.new("RGBA", (W, H), C["creme_fundo"])
    pat = Image.open(os.path.join(R.MARCA, "canva", "padroes-seigaiha-asanoha.png")).convert("RGBA")
    s = pat.width / 335
    asa = pat.crop((int(105 * s), int(125 * s), int(232 * s), int(228 * s)))
    asa.putalpha(asa.getchannel("A").point(lambda a: int(a * 0.45)))
    a1 = asa.resize((int(asa.width * 1.2), int(asa.height * 1.2)), Image.LANCZOS)
    bg.alpha_composite(a1, (W - a1.width + 140, -40))
    sei = pat.crop((0, 0, int(160 * s), int(120 * s)))            # onda seigaiha vermelha (canto)
    sei = sei.resize((int(sei.width * 1.5), int(sei.height * 1.5)), Image.LANCZOS)
    sei.putalpha(sei.getchannel("A").point(lambda a: int(a * 0.9)))
    bg.alpha_composite(sei.transpose(Image.FLIP_TOP_BOTTOM), (-60, H - sei.height + 40))
    orn = Image.open(os.path.join(R.MARCA, "canva", "ornamentos.png")).convert("RGBA")
    so = orn.width / 335
    nuvem = orn.crop((int(10 * so), int(15 * so), int(110 * so), int(80 * so)))
    nuvem.putalpha(nuvem.getchannel("A").point(lambda a: int(a * 0.55)))
    bg.alpha_composite(nuvem, (-30, 300))
    return bg


def tag():
    im = Image.new("RGBA", (W, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    leaf = R.fit(Image.open(os.path.join(R.MARCA, "logos", "aoi-folha-cor.png")).convert("RGBA"), 54)
    f = R.jfont(600, 40)
    t = "@espacoaoi"
    tw = f.getlength(t)
    x = (W - tw - leaf.width - 14) / 2
    im.alpha_composite(leaf, (int(x), 20))
    d.text((x + leaf.width + 14, 50), t, font=f, fill=C["verde_aoi"], anchor="lm")
    return im


def jp_card(romaji, sub=None, warn=False):
    kana, meaning = JP[romaji]
    sub = sub or meaning
    ks = 150 if len(kana) <= 5 else (104 if len(kana) <= 6 else 96)
    kw = R.jp_width(kana, ks)
    fr = R.jfont(700, 70)
    fm = R.jfont(600, 50)
    cw = int(max(kw, fr.getlength(romaji), fm.getlength(sub)) + 140)
    ch = ks + 70 + 60 + 120
    c, pad = R.card(cw, ch, seed=len(romaji) + (7 if warn else 0), alpha=250)
    d = ImageDraw.Draw(c)
    R.draw_jp(d, pad + (cw - kw) / 2, pad + 38, kana, ks, C["verde_aoi"])
    d.text((c.width / 2, pad + 38 + ks + 52), romaji, font=fr, fill=C["vermelho_ume"], anchor="mm")
    col = C["vermelho_ume"] if warn else TEXT
    if warn:
        sub = "= " + sub
    d.text((c.width / 2, pad + 38 + ks + 128), sub, font=fm, fill=col, anchor="mm")
    flower = R.fit(R.UME, 70)
    c.alpha_composite(flower, (pad + 10, pad - 12))
    return c


def text_card(lines, size=64, color=None, seed=1, icon=None, weight=700):
    f = R.jfont(weight, size)
    tw = max(f.getlength(s) for s in lines)
    iw = icon.width + 24 if icon else 0
    cw = int(tw + iw + 120)
    ch = int(len(lines) * size * 1.25 + 80)
    c, pad = R.card(cw, ch, seed=seed, alpha=248)
    d = ImageDraw.Draw(c)
    if icon:
        c.alpha_composite(icon, (pad + 50, pad + (ch - icon.height) // 2))
    for i, s in enumerate(lines):
        d.text((pad + 60 + iw + (tw - f.getlength(s)) / 2 if not icon else pad + 60 + iw,
                pad + 40 + size * 1.25 * i + size * 0.62), s, font=f, fill=color or TEXT, anchor="lm")
    return c


def pill(text, n, active=True):
    f = R.jfont(600, 46)
    w = int(f.getlength(text) + 150)
    h = 92
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=C["creme_fundo"], outline=C["salvia"], width=4)
    d.ellipse((12, 12, h - 12, h - 12), fill=C["vermelho_ume"])
    d.text((h / 2, h / 2 + 2), str(n), font=R.jfont(700, 40), fill=C["creme_fundo"], anchor="mm")
    d.text((h + 8, h / 2 + 3), text, font=f, fill=TEXT, anchor="lm")
    return im


def pronuncia_card():
    f = R.jfont(700, 84)
    fs = R.jfont(600, 44)
    a, b = "sumimasen", "s'mimasen"
    wa, wb = f.getlength(a), f.getlength(b)
    cw = int(max(wa, wb) + 200)
    ch = 380
    c, pad = R.card(cw, ch, seed=13, alpha=250)
    d = ImageDraw.Draw(c)
    d.text((c.width / 2, pad + 60), "dica de pronúncia", font=fs, fill=C["verde_aoi"], anchor="mm")
    x0 = c.width / 2 - wa / 2
    y0 = pad + 150
    d.text((x0, y0), a, font=f, fill=(42, 42, 40, 120), anchor="lm")
    # risca o "u" de "su"
    ux0 = x0 + f.getlength("s")
    ux1 = x0 + f.getlength("su")
    d.line((ux0 - 4, y0 + 8, ux1 + 4, y0 - 14), fill=C["vermelho_ume"], width=8)
    d.text((c.width / 2, y0 + 70), "↓", font=R.jfont(400, 56), fill=TEXT, anchor="mm")
    d.text((c.width / 2, y0 + 150), b, font=f, fill=C["vermelho_ume"], anchor="mm")
    return c


def cta_button(text, scale=1.0):
    f = R.jfont(700, int(60 * scale))
    bw, bh = int(f.getlength(text) + 120 * scale), int(124 * scale)
    btn = Image.new("RGBA", (bw, bh + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(btn)
    d.rounded_rectangle((0, 8, bw - 1, bh + 8), radius=bh // 2, fill="#9e3a35")
    d.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=bh // 2, fill=C["vermelho_ume"])
    d.text((bw / 2, bh / 2 + 2), text, font=f, fill=C["creme_fundo"], anchor="mm")
    return btn


# ======================================================== 4. legenda
FCAP = R.jfont(700, 76)
FCAP_JP = R.jfont(700, 92)


def caption_img(chunk, active_idx, t, chunk_t0):
    widths, fonts = [], []
    for w in chunk:
        f = FCAP_JP if w["jp"] else FCAP
        fonts.append(f)
        widths.append(f.getlength(w["w"]))
    space = 22
    tw = sum(widths) + space * (len(chunk) - 1)
    scale = min(1.0, 980 / tw)
    im = Image.new("RGBA", (W, 170), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = (W - tw * scale) / 2
    for i, w in enumerate(chunk):
        f = fonts[i] if scale == 1 else R.jfont(700, int(fonts[i].size * scale))
        ww = f.getlength(w["w"])
        act = i == active_idx
        if w["jp"]:
            # destaque fixo para japonês: faixa coral atrás
            d.rounded_rectangle((x - 16, 22, x + ww + 16, 148), radius=26, fill=C["vermelho_ume"])
            d.text((x, 85), w["w"], font=f, fill=C["creme_fundo"], anchor="lm")
        else:
            col = C["verde_aoi"] if act else TEXT
            # contorno creme para leitura sobre qualquer fundo
            d.text((x, 85), w["w"], font=f, fill=col, anchor="lm", stroke_width=7, stroke_fill=C["creme_fundo"])
        x += (ww + space * scale)
    return im


# ======================================================== 5. personagem
PSIZE = 900


def character_cache():
    cache = {}
    for boca in ("fechada", "media", "aberta", "o"):
        for olhos in ("abertos", "fechados", "surpresa"):
            for sob in ("normal", "alta"):
                png = cairosvg.svg2png(bytestring=personagem_svg(boca, olhos, sob).encode(), output_width=PSIZE)
                cache[(boca, olhos, sob)] = Image.open(io.BytesIO(png)).convert("RGBA")
    return cache


def mouth_track(voice_wav, nframes):
    x = decode(voice_wav)
    hop = SR // FPS
    x = np.pad(x, (0, max(0, nframes * hop - len(x))))
    env = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(nframes)])
    env = np.convolve(env, [0.25, 0.5, 0.25], "same")
    ref = np.percentile(env[env > 1e-4], 90) if np.any(env > 1e-4) else 1
    lv = env / ref
    states, hold = [], 0
    cur = "fechada"
    for v in lv:
        want = "fechada" if v < 0.18 else ("media" if v < 0.55 else "aberta")
        if want != cur and hold <= 0:
            cur, hold = want, 2
        hold -= 1
        states.append(cur)
    return states, lv


# ======================================================== 6. montagem
def main():
    voice_wav, remap, vdur, removed = build_audio()
    print(f"voz: {vdur:.2f}s (cortados {removed:.2f}s de silêncio)")
    words = load_words(remap)
    json.dump(words, open(f"{WORK}/ra/palavras.json", "w"), ensure_ascii=False, indent=1)
    caps = chunks(words)
    TAIL = 1.6
    total = vdur + TAIL
    nframes = int(math.ceil(total * FPS))

    def wt(i):  # início da palavra i (índice na lista corrigida)
        return words[i]["s"]

    def find(text, nth=1, start=0):
        k = 0
        for i in range(start, len(words)):
            if words[i]["w"].lower().startswith(text):
                k += 1
                if k == nth:
                    return i
        raise KeyError(text)

    iS1 = find("sumimasen")
    iEla = find("ela")
    iPara2 = find("para", start=find("sumimasen", 2))
    iAte = find("até")
    iTres = find("três")
    iDica = find("dica")
    iAgora = find("agora")
    iKore = find("kore kudasai")
    iE_cuid = find("cuidado") - 1
    iCuid = find("cuidado")
    iDai = find("daijoubu desu")
    iEle = find("ele")
    iAi = find("aí")
    iSalva = find("salva")
    iComenta = find("comenta")
    iSegue = find("segue") - 1
    end_voice = words[-1]["e"]

    # cartões: (img, t0, t1, posição y do centro)
    pills_y = 760
    cards = [
        (text_card(["1 palavra que salva", "sua viagem ao Japão"], size=70, seed=3), 0.0, wt(iS1) - 0.05, 560),
        (jp_card("sumimasen"), wt(iS1), wt(iTres) - 0.05, 470),
        (pill("chamar o garçom", 1), wt(iEla), wt(iTres) - 0.05, pills_y),
        (pill("pedir desculpa", 2), wt(iPara2), wt(iTres) - 0.05, pills_y + 108),
        (pill("agradecer", 3), wt(iAte), wt(iTres) - 0.05, pills_y + 216),
        (text_card(["3 situações", "= 1 palavra só"], size=78, color=C["verde_aoi"], seed=5), wt(iTres), wt(iDica) - 0.05, 560),
        (pronuncia_card(), wt(iDica), wt(iAgora) - 0.05, 560),
        (jp_card("kore kudasai"), wt(iKore), wt(iE_cuid) - 0.05, 470),
        (text_card(["cuidado com essa!"], size=70, color=C["vermelho_ume"], seed=9,
                   icon=emoji("⚠", 70)), wt(iE_cuid), wt(iDai) - 0.05, 560),
        (jp_card("daijoubu desu"), wt(iDai), wt(iEle) - 0.05, 470),
        (jp_card("daijoubu desu", sub="não, obrigado", warn=True), wt(iEle), wt(iSalva) - 0.05, 470),
        (text_card(["sem sacola"], size=60, seed=11, icon=emoji("🛍", 64)), wt(iAi), wt(iSalva) - 0.05, 840),
        (text_card(["salva pra sua viagem"], size=60, seed=15, icon=emoji("📌", 64)), wt(iSalva), wt(iSegue) - 0.05, 440),
        (text_card(["comenta “parte 2”"], size=60, seed=17, icon=emoji("💬", 64)), wt(iComenta), wt(iSegue) - 0.05, 640),
    ]
    # kore kudasai: dedinho apontando
    point = emoji("👉", 110)

    bg = background()
    tg = tag()
    bg.alpha_composite(tg, (0, 150))
    chars = character_cache()
    mouth, energy = mouth_track(voice_wav, nframes)
    logo = R.fit(Image.open(os.path.join(R.MARCA, "logos", "aoi-horizontal-kanji-cor.png")).convert("RGBA"), 190)

    rng = np.random.default_rng(3)
    blinks = set()
    t = 1.2
    while t < total:
        f0 = int(t * FPS)
        blinks.update({f0, f0 + 1, f0 + 2})
        t += rng.uniform(2.6, 4.4)

    surprise = [(wt(iCuid) - 0.1, wt(iCuid) + 1.0), (wt(iEle), wt(iEle) + 1.3)]
    cap_cache = {}

    out = f"{WORK}/ra/video.mp4"
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                             "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for fi in range(nframes):
        t = fi / FPS
        fr = bg.copy()

        # ---- personagem
        sur = any(a <= t <= b for a, b in surprise)
        boca = mouth[fi] if t < end_voice + 0.1 else "fechada"
        if sur and boca == "fechada":
            boca = "o"
        olhos = "fechados" if fi in blinks and not sur else ("surpresa" if sur else "abertos")
        im = chars[(boca, olhos, "alta" if sur else "normal")]
        e = float(energy[fi]) if fi < len(energy) else 0
        bob = 6 * math.sin(t * 2 * math.pi * 0.55) + 4 * min(e, 1.5)
        ang = 1.4 * math.sin(t * 2 * math.pi * 0.31) + (0.8 * math.sin(t * 9) * min(e, 1) if e > 0.3 else 0)
        ch_im = im.rotate(ang, resample=Image.BICUBIC, center=(PSIZE / 2, PSIZE * 0.55))
        # entrada da personagem (sobe do rodapé)
        rise = (1 - ease(t / 0.6)) * 500
        fr.alpha_composite(ch_im, ((W - PSIZE) // 2, int(H - PSIZE * 1.2 + 110 + bob + rise)))

        # ---- cartões
        for img, t0, t1, cy in cards:
            if not (t0 <= t <= t1 + 0.2):
                continue
            pin = back((t - t0) / 0.35)
            pout = 1 - ease((t - t1) / 0.2) if t > t1 else 1
            a = max(0.0, min(1.0, ease((t - t0) / 0.18))) * pout
            sc = 0.82 + 0.18 * pin
            ci = img.resize((max(1, int(img.width * sc)), max(1, int(img.height * sc))), Image.BILINEAR)
            if a < 1:
                ci.putalpha(ci.getchannel("A").point(lambda v: int(v * a)))
            fr.alpha_composite(ci, ((W - ci.width) // 2, int(cy - ci.height / 2)))
        # dedinho no kore kudasai
        if wt(iKore) <= t <= wt(iE_cuid) - 0.05:
            wig = 14 * math.sin((t - wt(iKore)) * 2 * math.pi * 1.4)
            a = ease((t - wt(iKore) - 0.2) / 0.2)
            if a > 0:
                p = point.copy()
                p.putalpha(p.getchannel("A").point(lambda v: int(v * a)))
                fr.alpha_composite(p, (int(80 + wig), 420))

        # ---- final: botão Siga + logo + matrículas
        if t >= wt(iSegue):
            q = back((t - wt(iSegue)) / 0.4)
            pulse = 1 + 0.035 * math.sin((t - wt(iSegue)) * 2 * math.pi / (2 * R.BEAT))
            btn = cta_button("Siga @espacoaoi", scale=max(0.3, q * pulse))
            fr.alpha_composite(btn, ((W - btn.width) // 2, 680 - btn.height // 2))
            a2 = ease((t - wt(iSegue) - 0.6) / 0.4)
            if a2 > 0:
                lay = Image.new("RGBA", (W, 140), (0, 0, 0, 0))
                ImageDraw.Draw(lay).text((W / 2, 70), "matrículas em breve", font=R.jfont(700, 58),
                                         fill=C["verde_aoi"], anchor="mm", stroke_width=6, stroke_fill=C["creme_fundo"])
                lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a2)))
                fr.alpha_composite(lay, (0, 790))
                lg = logo.copy()
                lg.putalpha(lg.getchannel("A").point(lambda v: int(v * a2)))
                fr.alpha_composite(lg, ((W - lg.width) // 2, 330))

        # ---- legenda
        if t <= end_voice + 0.3:
            for ci, chunk in enumerate(caps):
                c0 = chunk[0]["s"] - 0.05
                c1 = caps[ci + 1][0]["s"] - 0.05 if ci + 1 < len(caps) else end_voice + 0.3
                if c0 <= t < c1:
                    act = 0
                    for k, w in enumerate(chunk):
                        if t >= w["s"] - 0.03:
                            act = k
                    key = (ci, act)
                    if key not in cap_cache:
                        cap_cache = {key: caption_img(chunk, act, t, c0)}
                    cimg = cap_cache[key]
                    pop = 1 - ease((t - c0) / 0.12)
                    fr.alpha_composite(cimg, (0, int(1015 + 18 * pop)))
                    break
        proc.stdin.write(fr.tobytes())
        if fi % 300 == 0:
            print(f"  quadro {fi}/{nframes}")
    proc.stdin.close()
    proc.wait()

    # trilha bem baixa, com ducking pela voz
    mpath = f"{WORK}/ra/musica.wav"
    R.music(mpath, total)
    final = f"{WORK}/ra/aoi-reels-sumimasen.mp4"
    sh(["ffmpeg", "-v", "error", "-y", "-i", out, "-i", voice_wav, "-i", mpath, "-filter_complex",
        f"[1:a]apad=whole_dur={total},asplit=2[v1][v2];"
        "[2:a]volume=0.22[m];[m][v2]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=400[md];"
        "[v1][md]amix=inputs=2:normalize=0,aresample=48000,"
        "loudnorm=I=-14:TP=-1.5:LRA=9,alimiter=limit=0.84:attack=0.5:release=40:level=disabled[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ac", "2",
        "-movflags", "+faststart", "-shortest", final])
    print("ok:", final)


if __name__ == "__main__":
    main()
