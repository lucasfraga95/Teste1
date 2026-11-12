#!/usr/bin/env python3
"""Reels PARTE 2 — "Como pedir comida no Japão" — montado a partir de 2 áudios brutos.

Os áudios têm erros e repetições. O script escolhe os melhores trechos de cada um:
  a1 (áudio longo, bruto) .... corpo da aula + 3ª tentativa do convite final + despedida
  a2 (regravação curta) ...... "para não esquecer dessas cinco frases... salva... manda..."
e corta: respiração, o "desu" que escapou em "eu quero dois desu", tentativas travadas e pausas longas.

Uso:
  A1=bruto.m4a A2=regravacao.m4a WORK=/tmp/p2 FONTS=/fonts/ttf python3 reels_parte2.py [frames t1 t2 ...]
Precisa de $WORK/a1.json e $WORK/a2.json (transcrição Whisper com tempo por palavra).
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
A1, A2, WORK = os.environ["A1"], os.environ["A2"], os.environ["WORK"]
os.environ.setdefault("AUDIO", A1)
os.environ.setdefault("WORDS", f"{WORK}/a1.json")
import reels_tipografia as RT

RA, R, IL = RT.RA, RT.R, RT.IL
C, TEXTO, OURO = RT.C, RT.TEXTO, RT.OURO
W, H, FPS, SR = R.W, R.H, R.FPS, RA.SR
ease, back = RT.ease, RT.back
OUT = f"{WORK}/p2out"
os.makedirs(OUT, exist_ok=True)


def lerp(a, b, p):
    return a + (b - a) * p


# ======================================================================= ÁUDIO
PIECES = [  # (fonte, 1ª palavra, última palavra, opções)  — índices das transcrições
    ("a1", 0, 14, {}),                      # "Cinco frases em japonês e você já consegue se virar..."
    ("a1", 15, 30, {}),                     # irasshaimase
    ("a1", 31, 46, {}),                     # sem resposta, só um sorriso
    ("a1", 47, 61, {}),                     # nanmei-sama desu ka
    ("a1", 62, 69, {"hold": 0.35}),         # futari desu
    ("a1", 70, 83, {}),                     # kore o onegaishimasu
    ("a1", 84, 100, {"b": 39.045}),         # kore o futatsu onegaishimasu, eu quero dois   (corta o "desu")
    ("a1", 102, 103, {"a": 39.50}),         # ..., por favor
    ("a1", 104, 121, {}),                   # okaikei onegaishimasu
    ("a2", 1, 23, {"a": 0.50}),             # regravação: "para não esquecer... salva... manda..." (sem a respiração do "E")
    ("a1", 153, 168, {}),                   # 3ª tentativa: "E não esquece de seguir a página do espaço Aoi..."
    ("a1", 169, 170, {}),                   # "Jane, mata" (despedida)
]
JPG = [("a1", 25, 25, "irasshaimase"), ("a1", 52, 55, "nanmei-sama desu ka"), ("a1", 68, 69, "futari desu"),
       ("a1", 81, 83, "kore o onegaishimasu"), ("a1", 92, 95, "kore o futatsu onegaishimasu"),
       ("a1", 114, 115, "okaikei onegaishimasu"), ("a1", 169, 170, "jane mata")]
# palavras que já aparecem em destaque no topo da tela -> sem legenda embaixo (src, 1ª, última)
KIN = [("a1", 0, 14), ("a1", 25, 30), ("a1", 35, 38), ("a1", 42, 46), ("a1", 52, 61), ("a1", 68, 69),
       ("a1", 81, 83), ("a1", 92, 95), ("a1", 96, 103), ("a1", 114, 121), ("a2", 9, 23), ("a1", 153, 170)]


def env_db(x, hop=None):
    hop = hop or int(0.01 * SR)
    n = len(x) // hop
    return 20 * np.log10(np.sqrt(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1)) + 1e-9)


def silence_runs(E, thr=-45, min_len=7):
    runs, st = [], None
    for i, v in enumerate(E):
        if v < thr and st is None:
            st = i
        if v >= thr and st is not None:
            if i - st >= min_len:
                runs.append((st * 0.01, i * 0.01))
            st = None
    return runs


def load_words(name):
    d = json.load(open(f"{WORK}/{name}.json"))
    return [dict(raw=x["w"].strip(), s=x["s"], e=x["e"]) for seg in d for x in seg["words"]]


def refine(ws, runs):
    """Ajusta início/fim das palavras que vêm depois/antes de uma pausa real (Whisper erra até ~0,3 s)."""
    ends = np.array([r[1] for r in runs]); starts = np.array([r[0] for r in runs])
    out = []
    for i, w in enumerate(ws):
        s, e = w["s"], w["e"]
        gap_b = s - ws[i - 1]["e"] if i > 0 else 1
        gap_a = ws[i + 1]["s"] - e if i + 1 < len(ws) else 1
        if gap_b >= 0.10 and len(ends):
            j = int(np.argmin(abs(ends - s)))
            if abs(ends[j] - s) <= 0.35:
                s = ends[j]
        if gap_a >= 0.10 and len(starts):
            k = int(np.argmin(abs(starts - e)))
            if abs(starts[k] - e) <= 0.35:
                e = starts[k]
        if e <= s:
            s, e = w["s"], w["e"]
        out.append(dict(w, s=s, e=e))
    return out


def build_audio():
    filt = "highpass=f=85,afftdn=nf=-28:nr=12,lowpass=f=12000"
    paths = {"a1": A1, "a2": A2}
    X = {n: RA.decode(p, filt) for n, p in paths.items()}
    RAW = {n: RA.decode(p, None) for n, p in paths.items()}
    E = {n: env_db(RAW[n]) for n in paths}
    RUNS = {n: silence_runs(E[n]) for n in paths}
    WS = {n: refine(load_words(n), RUNS[n]) for n in paths}
    fade = int(0.012 * SR)
    prev_b = {"a1": 0.0, "a2": 0.0}
    t_out, ys, info, allw = 0.0, [], [], []
    for (src, i0, i1, o) in PIECES:
        ws, Es = WS[src], E[src]
        s0, e1 = ws[i0]["s"], ws[i1]["e"]
        # início real da fala: 1º quadro acima de -26 dB (ignora respiração, que fica ~-32 dB)
        if "a" in o:
            a = o["a"]
        else:
            a = None
            for k in range(int(max(s0 - 0.30, prev_b[src]) * 100), min(len(Es), int((s0 + 1.4) * 100))):
                if Es[k] > -26:
                    a = k / 100 - 0.10
                    break
            a = max(a if a is not None else s0 - 0.05, prev_b[src])
        # fim real da fala: último quadro acima de -30 dB
        if "b" in o:
            b = o["b"]
        else:
            # fim real da fala = início da primeira pausa (< -45 dB por >= 70 ms) depois da última palavra
            b = None
            for rs, _re in RUNS[src]:
                if e1 - 0.40 <= rs <= e1 + 0.60 and rs > a:
                    b = rs + 0.11
                    break
            b = b if b is not None else e1 + 0.1
        prev_b[src] = b
        x = X[src][int(a * SR): int(b * SR)].copy()
        sub = RAW[src][int(a * SR): int(b * SR)]
        L = len(x) / SR
        cuts = [(s + 0.09, e - 0.09) for s, e in RA.silences(sub, thr_db=-45, min_d=0.28) if s > 0.02 and e < L - 0.02]
        keeps, t = [], 0.0
        for cs, ce in cuts:
            keeps.append((t, cs)); t = ce
        keeps.append((t, L))
        segs = []
        for ks, ke in keeps:
            seg = x[int(ks * SR): int(ke * SR)].copy()
            if len(seg) > 2 * fade:
                seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
            segs.append(seg)
        y = np.concatenate(segs)
        hold = o.get("hold", 0.0)
        if hold:
            y = np.concatenate([y, np.zeros(int(hold * SR), dtype=y.dtype)])

        def remap(ts, a=a, cuts=cuts, t0=t_out):
            loc = ts - a
            rem = 0.0
            for cs, ce in cuts:
                if loc >= ce:
                    rem += ce - cs
                elif loc > cs:
                    return t0 + cs - rem
            return t0 + max(0.0, loc - rem)

        for i in range(i0, i1 + 1):
            w = ws[i]
            s_ = w["s"] if i != i0 else a + 0.10
            e_ = w["e"] if i != i1 else b - 0.11
            allw.append(dict(src=src, i=i, raw=w["raw"], s=remap(s_), e=remap(max(e_, s_ + 0.05))))
        info.append((src, i0, i1, round(a, 2), round(b, 2), round(t_out, 2), round(len(y) / SR, 2)))
        ys.append((src, y))
        t_out += len(y) / SR
    # iguala o nível das duas gravações
    def level(src):
        v = np.concatenate([y for s, y in ys if s == src])
        r = env_db(v)
        sp = v[: len(r) * int(0.01 * SR)].reshape(len(r), -1)[r > -35]
        return float(np.mean(sp ** 2)) if len(sp) else 1e-6
    g2 = float(np.clip(math.sqrt(level("a1") / level("a2")), 0.7, 1.4))
    print(f"ganho a2 -> a1: {g2:.2f}")
    voice = np.concatenate([y * (g2 if s == "a2" else 1.0) for s, y in ys])
    raw = f"{OUT}/voz.f32"
    voice.astype("<f4").tofile(raw)
    out = f"{OUT}/voz.wav"
    RA.sh(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", raw, "-af",
           "equalizer=f=200:t=q:w=1:g=-2,equalizer=f=3500:t=q:w=1.2:g=3,"
           "acompressor=threshold=-22dB:ratio=3:attack=8:release=120:makeup=4,"
           "loudnorm=I=-16:TP=-1.5:LRA=9,aresample=48000", "-ac", "1", out])
    for r_ in info:
        print("  trecho", r_)
    return out, allw, len(voice) / SR


def display_words(allw):
    by = {(w["src"], w["i"]): w for w in allw}
    groups = {(s, i0): (i1, t) for s, i0, i1, t in JPG}
    skip, out = set(), []
    for w in allw:
        key = (w["src"], w["i"])
        if key in skip:
            continue
        if key in groups:
            i1, txt = groups[key]
            last = by[(w["src"], i1)]
            for k in range(w["i"], i1 + 1):
                skip.add((w["src"], k))
            out.append(dict(w=txt, s=w["s"], e=last["e"], jp=True, punct=last["raw"][-1:] in ",.?!…",
                            src=w["src"], i0=w["i"], i1=i1))
        else:
            out.append(dict(w=w["raw"].strip(",.?!…").replace("…", ""), s=w["s"], e=w["e"], jp=False,
                            punct=w["raw"][-1:] in ",.?!…", src=w["src"], i0=w["i"], i1=w["i"]))
    return out


# ======================================================================= ELEMENTOS
def pill(text, size, fg, bg, padx=52, pady=24, weight=700, track=0.04):
    t_ = RT.timg(text, size, fg, weight, track)
    w, h = t_.width + 2 * padx, t_.height + 2 * pady
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=bg)
    im.alpha_composite(t_, (padx, pady))
    return im


def chip(text, size=58):
    while True:
        eq = RT.timg("=", size, C["vermelho_ume"], 700)
        tx = RT.timg(text, size, C["verde_aoi"], 700, 0.03)
        w = eq.width + tx.width + 30 + 120
        if w + 60 <= 960 or size <= 30:
            break
        size -= 4
    h = max(eq.height, tx.height) + 56
    im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((30, 40, 30 + w, 40 + h), radius=h // 2, fill=(60, 40, 30, 60))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
    ImageDraw.Draw(im).rounded_rectangle((30, 30, 30 + w, 30 + h), radius=h // 2, fill="#ffffff")
    im.alpha_composite(eq, (30 + 60, 30 + (h - eq.height) // 2))
    im.alpha_composite(tx, (30 + 60 + eq.width + 30, 30 + (h - tx.height) // 2))
    return im


def appear(fr, im, cx, cy, t, t0, a=1.0, sc=1.0, dur=0.35, start=0.55):
    if t < t0:
        return
    p = (t - t0) / dur
    RT.put(fr, im, cx, cy, a=ease(p * 2) * a, sc=(start + (1 - start) * back(p)) * sc)


SMALL = set("ゃゅょっゎャュョッ")


def unit_w(text, size):
    return sum((0.72 if c in SMALL else 1.0) * size for c in text)


def kana_unit(text, size, color):
    """Uma 'mora' (ex.: し, しゃ, っ) com linha de base fixa: kana pequenos ficam pequenos e embaixo."""
    w, h = int(unit_w(text, size) + size * 0.3), int(size * 1.5)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = size * 0.15
    for c in text:
        f = R.kfont(c, size)
        if c in SMALL:
            d.text((x - 0.10 * size, size * 0.12), c, font=f, fill=color)
            x += 0.72 * size
        else:
            d.text((x + (size - f.getlength(c)) / 2, size * 0.12), c, font=f, fill=color)
            x += size
    return im


class Block:
    """Frase em hiragana (1 ou 2 linhas) + faixa vermelha com a leitura em sílabas (SU.MI.MA.SE.N)."""

    def __init__(self, lines, ks, cell, linegap, band_lines, hi=(), col=None):
        col = col or C["verde_aoi"]
        self.imgs, self.pos = [], []
        n, k = len(lines), 0
        gap = 0.10 * ks
        for i, line in enumerate(lines):
            ws_ = [unit_w(u, ks) for u in line]
            x = -(sum(ws_) + gap * (len(line) - 1)) / 2
            for j, kn in enumerate(line):
                self.imgs.append(kana_unit(kn, ks, C["vermelho_ume"] if k in hi else col))
                self.pos.append((x + ws_[j] / 2, (i - (n - 1) / 2) * linegap))
                x += ws_[j] + gap
                k += 1
        fs = 58
        txts = [RT.timg(s, fs, C["creme_fundo"], 700, 0.07) for s in band_lines]
        bw = max(max(x.width for x in txts) + 120, 640)
        lh = int(fs * 1.55)
        bh = int(lh * len(txts) + 44)
        band = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        ImageDraw.Draw(band).rounded_rectangle((0, 0, bw - 1, bh - 1), radius=min(40, bh // 2), fill=C["vermelho_ume"])
        for i, x in enumerate(txts):
            band.alpha_composite(x, ((bw - x.width) // 2, 22 + i * lh + (lh - x.height) // 2))
        self.band = band
        self.band_y = (n - 1) / 2 * linegap + ks * 0.5 + 60 + bh / 2

    def draw(self, fr, t, times, cx, cy, sc=1.0, a=1.0, override=None):
        for k, img in enumerate(self.imgs):
            tk = times[k]
            if tk is None or t < tk:
                continue
            pp = (t - tk) / 0.3
            lx, ly = (override or {}).get(k, self.pos[k])
            RT.put(fr, img, cx + lx * sc, cy + ly * sc, a=ease(pp * 2.5) * a, sc=(1.5 - 0.5 * back(pp)) * sc)

    def draw_band(self, fr, t, band_t, cx, cy, sc=1.0, a=1.0, img=None):
        if t < band_t:
            return
        pp = ease((t - band_t) / 0.35)
        RT.put(fr, img or self.band, cx - 300 * (1 - pp) * sc, cy + self.band_y * sc, a=pp * a, sc=sc)


def steps(t0, n, step):
    return [t0 + k * step for k in range(n)]


# ======================================================================= VÍDEO
def main():
    frames_mode = len(sys.argv) > 1 and sys.argv[1] == "frames"
    voice_wav, allw, vdur = build_audio()
    json.dump(allw, open(f"{OUT}/palavras.json", "w"), ensure_ascii=False, indent=1)
    by = {(w["src"], w["i"]): w for w in allw}
    T = lambda s, i: by[(s, i)]["s"]
    Ee = lambda s, i: by[(s, i)]["e"]
    dw = display_words(allw)
    kin = set()
    for w in dw:
        for (s, i0, i1) in KIN:
            if w["src"] == s and w["i0"] >= i0 and w["i1"] <= i1:
                kin.add(id(w))
    kin = frozenset(kin)
    caps = RA.chunks(dw, maxc=24)
    voice_end = dw[-1]["e"] + 0.15
    END = voice_end + 0.85
    nframes = int(END * FPS)
    print(f"voz {vdur:.1f}s | vídeo {END:.1f}s | {len(dw)} palavras")

    BG_CREME = RT.BG_CREME
    BG_SALVIA = Image.new("RGBA", (W, H), C["salvia"])
    _a = BG_CREME.copy(); _a.putalpha(70); BG_SALVIA.alpha_composite(_a)

    def badge(text):
        return pill(text, 38, C["creme_fundo"], C["verde_aoi"], padx=34, pady=15, track=0.06)

    # ---------------- GANCHO (verde)
    n11 = T("a1", 11)
    hook = [
        (RT.timg("5", 330, OURO), 470, T("a1", 0), "pop"),
        (RT.timg("FRASES EM JAPONÊS", 80, C["creme_fundo"]), 705, T("a1", 1), "up"),
        (RT.timg("E VOCÊ SE VIRA", 70, C["creme_fundo"]), 820, T("a1", 4), "up"),
        (RT.timg("EM QUALQUER", 90, C["creme_fundo"]), 940, T("a1", 10), "up"),
        (RT.timg("RESTAURANTE", 118, OURO), 1065, n11, "pop"),
        (RT.timg("NO JAPÃO", 110, C["creme_fundo"]), 1190, T("a1", 13), "pop"),
    ]
    ilu_rest_s = IL.png(IL.restaurante(), 300)

    def scene_hook(t):
        fr = RT.drift(RT.BG_VERDE, t).copy()
        RT.tag(fr, True)
        for im, y, t0, mode in hook:
            if mode == "pop":
                appear(fr, im, W / 2, y, t, t0 + 0.02)
            elif t >= t0:
                RT.reveal_up(fr, im, W / 2, y, (t - t0) / 0.3)
        if t >= n11 - 0.1:
            p = ease((t - n11 + 0.1) / 0.6)
            RT.put(fr, ilu_rest_s, W / 2, 1400 + 300 * (1 - p), a=p)
        return fr

    # ---------------- 1: IRASSHAIMASE + sorriso (creme)
    ilu_rest = IL.png(IL.restaurante(), 560)
    ilu_smile = IL.png(IL.sorriso(), 420)
    blkI = Block([["い", "ら", "っ", "しゃ", "い", "ま", "せ"]], 124, 136, 0, ["I.RAS.SHAI.MA.SE"])
    badge1, chip_bv = badge("FRASE 1/5"), chip("BEM-VINDO!")
    pill_nao = pill("NÃO PRECISA RESPONDER", 54, C["creme_fundo"], C["vermelho_ume"])
    pill_sor = pill("SÓ UM SORRISO!", 72, C["creme_fundo"], C["verde_aoi"])
    s1 = T("a1", 15) + 0.14
    t25, t29, t31, t35, t42 = T("a1", 25), T("a1", 29), T("a1", 31), T("a1", 35), T("a1", 42)
    timesI = steps(t25, 7, 0.11)

    def scene_irasshai(t):
        fr = BG_CREME.copy()
        RT.tag(fr, False)
        if t >= s1:
            if t < t25:
                appear(fr, ilu_rest, W / 2, 900 + 7 * math.sin(t * 4), t, s1)
            else:
                p = ease((t - t25) / 0.45)
                fade = 1 - ease((t - t31) / 0.3) if t > t31 else 1
                RT.put(fr, ilu_rest, W / 2, lerp(900, 1340, p), a=fade, sc=lerp(1, 0.55, p))
        if t >= t25:
            m = ease((t - (t31 - 0.1)) / 0.45) if t > t31 - 0.1 else 0
            blkI.draw(fr, t, timesI, W / 2, lerp(620, 380, m), lerp(1, 0.62, m))
            blkI.draw_band(fr, t, t25 + 0.85, W / 2, lerp(620, 380, m), lerp(1, 0.62, m))
            appear(fr, badge1, W / 2, 275, t, t25)
        if t >= t29:
            a = 1 - ease((t - (t31 - 0.1)) / 0.25) if t > t31 - 0.1 else 1
            appear(fr, chip_bv, W / 2, 970, t, t29, a=a)
        if t >= t35:
            if t < t42:
                RT.reveal_up(fr, pill_nao, W / 2, 800, (t - t35) / 0.3)
            else:
                RT.reveal_up(fr, pill_sor, W / 2, 800, (t - t42) / 0.3)
                appear(fr, ilu_smile, W / 2, 1150 + 8 * math.sin(t * 3), t, t42)
        return fr

    # ---------------- 2: NANMEI-SAMA DESU KA (sálvia)
    ilu_att = IL.png(IL.atendente(), 540)
    blkN = Block([["な", "ん", "め", "い", "さ", "ま"], ["で", "す", "か"]], 120, 140, 150, ["NAN.MEI.SA.MA", "DE.SU.KA"])
    badge2, chip_pq = badge("FRASE 2/5"), chip("SÃO QUANTAS PESSOAS?")
    s2 = T("a1", 47) + 0.14
    t52, t59 = T("a1", 52), T("a1", 59)
    timesN = steps(t52, 6, 0.12) + steps(t52 + 0.75, 3, 0.12)

    def scene_nanmei(t):
        fr = BG_SALVIA.copy()
        RT.tag(fr, False)
        if t >= s2:
            if t < t52:
                appear(fr, ilu_att, W / 2, 900 + 7 * math.sin(t * 4), t, s2)
            else:
                p = ease((t - t52) / 0.45)
                RT.put(fr, ilu_att, W / 2, lerp(900, 1345, p), sc=lerp(1, 0.58, p))
        if t >= t52:
            blkN.draw(fr, t, timesN, W / 2, 600)
            blkN.draw_band(fr, t, t52 + 1.0, W / 2, 600)
            appear(fr, badge2, W / 2, 275, t, t52)
        if t >= t59:
            appear(fr, chip_pq, W / 2, 1075, t, t59)
        return fr

    # ---------------- 3: FUTARI DESU (creme)
    ilu_two = IL.png(IL.duas_pessoas(), 540)
    num2 = RT.timg("2", 300, C["vermelho_ume"])
    blkF = Block([["ふ", "た", "り", "で", "す"]], 160, 170, 0, ["FU.TA.RI  DE.SU"])
    badge3, chip_dp = badge("FRASE 3/5"), chip("SÃO DUAS PESSOAS")
    s3 = T("a1", 62) + 0.14
    t64, t68, t69 = T("a1", 64), T("a1", 68), T("a1", 69)
    timesF = steps(t68, 5, 0.12)

    def scene_futari(t):
        fr = BG_CREME.copy()
        RT.tag(fr, False)
        if t >= s3:
            if t < t68:
                appear(fr, ilu_two, W / 2, 960 + 7 * math.sin(t * 4), t, s3)
            else:
                p = ease((t - t68) / 0.45)
                RT.put(fr, ilu_two, W / 2, lerp(960, 1320, p), sc=lerp(1, 0.6, p))
        if t64 <= t < t68 + 0.25:
            a = 1 - ease((t - t68) / 0.25) if t > t68 else 1
            appear(fr, num2, W / 2, 640, t, t64, a=a)
        if t >= t68:
            blkF.draw(fr, t, timesF, W / 2, 640)
            blkF.draw_band(fr, t, t68 + 0.55, W / 2, 640)
            appear(fr, badge3, W / 2, 275, t, t68)
        if t >= t69 + 0.15:
            appear(fr, chip_dp, W / 2, 1090, t, t69 + 0.15)
        return fr

    # ---------------- 4: KORE O (FUTATSU) ONEGAISHIMASU (sálvia)
    menu = IL.png(IL.cardapio(), 600)
    dedo = IL.png(IL.dedo(), 330)
    pratos = IL.png(IL.dois_pratos(), 600)
    K1 = Block([["こ", "れ", "を"], ["お", "ね", "が", "い", "し", "ま", "す"]], 118, 132, 150,
               ["KO.RE.O", "O.NE.GA.I.SHI.MA.SU"])
    K2 = Block([["こ", "れ", "を", "ふ", "た", "つ"], ["お", "ね", "が", "い", "し", "ま", "す"]], 118, 132, 150,
               ["KO.RE.O  FU.TA.TSU", "O.NE.GA.I.SHI.MA.SU"], hi={3, 4, 5})
    badge4, badge4b = badge("FRASE 4/5"), badge("FRASE 4/5 · VARIAÇÃO")
    chip_isso, chip_dois = chip("ISSO, POR FAVOR"), chip("EU QUERO DOIS, POR FAVOR")
    pill_ft = pill("FU.TA.TSU = 2", 52, C["creme_fundo"], C["vermelho_ume"])
    s4 = T("a1", 70) + 0.14
    tB, tC, tD, tE = T("a1", 81), T("a1", 88), T("a1", 94), T("a1", 98)
    tTap = T("a1", 76)
    times1 = steps(tB, 3, 0.15) + steps(T("a1", 83), 7, 0.11)
    bandK = T("a1", 83) + 0.9
    tI = bandK + 0.35
    map21 = {0: 0, 1: 1, 2: 2, 6: 3, 7: 4, 8: 5, 9: 6, 10: 7, 11: 8, 12: 9}
    times2 = [None] * 13
    for k in range(13):
        times2[k] = times1[map21[k]] if k in map21 else tD + (k - 3) * 0.12

    def scene_pedir(t):
        fr = BG_SALVIA.copy()
        RT.tag(fr, False)
        fade_menu = 1 - ease((t - (tC - 0.05)) / 0.25) if t > tC - 0.05 else 1
        if t >= s4:
            p = ease((t - tB) / 0.45) if t >= tB else 0
            my, msc = lerp(880, 1250, p), lerp(1, 0.52, p)
            if t < tB:
                appear(fr, menu, W / 2, 880 + 6 * math.sin(t * 4), t, s4)
            else:
                RT.put(fr, menu, W / 2, my, a=fade_menu, sc=msc)
            if t >= tTap:
                q = ease((t - tTap) / 0.35)
                tap = 14 * abs(math.sin((t - tTap) * 7))
                dx = lerp(W / 2 + 150, W / 2 + 110, p)
                dy = lerp(800, 1130, p)
                RT.put(fr, dedo, dx + 360 * (1 - q) + tap * msc, dy, a=q * fade_menu, sc=msc)
        if t >= tC:
            appear(fr, pratos, W / 2, 1265, t, tC, sc=0.55)
        if t >= tB:
            if t < tD:
                K1.draw(fr, t, times1, W / 2, 560)
                K1.draw_band(fr, t, bandK, W / 2, 560)
            else:
                q = ease((t - tD) / 0.3)
                ov = {k: (lerp(K1.pos[map21[k]][0], K2.pos[k][0], q), lerp(K1.pos[map21[k]][1], K2.pos[k][1], q))
                      for k in map21}
                K2.draw(fr, t, times2, W / 2, 560, override=ov)
                qb = ease((t - tD - 0.1) / 0.3)
                K1.draw_band(fr, t, bandK, W / 2, 560, a=1 - qb)
                K2.draw_band(fr, t, tD + 0.1, W / 2, 560, a=qb)
            appear(fr, badge4 if t < tC else badge4b, W / 2, 275, t, tB if t < tC else tC)
        if tI <= t < tD + 0.15:
            appear(fr, chip_isso, W / 2, 1060, t, tI, a=1 - ease((t - (tD - 0.05)) / 0.2) if t > tD - 0.05 else 1)
        if tD + 0.15 <= t < tE + 0.15:
            appear(fr, pill_ft, W / 2, 1050, t, tD + 0.15, a=1 - ease((t - tE) / 0.15) if t > tE else 1)
        if t >= tE:
            appear(fr, chip_dois, W / 2, 1060, t, tE)
        return fr

    # ---------------- 5: OKAIKEI ONEGAISHIMASU (creme)
    ilu_rec = IL.png(IL.recibo(), 540)
    blkO = Block([["お", "か", "い", "け", "い"], ["お", "ね", "が", "い", "し", "ま", "す"]], 118, 132, 150,
                 ["O.KAI.KEI", "O.NE.GA.I.SHI.MA.SU"])
    badge5, chip_conta = badge("FRASE 5/5"), chip("A CONTA, POR FAVOR")
    s5 = T("a1", 104) + 0.14
    t114, t115, t118 = T("a1", 114), T("a1", 115), T("a1", 118)
    timesO = steps(t114, 5, 0.16) + steps(t115, 7, 0.11)

    def scene_okaikei(t):
        fr = BG_CREME.copy()
        RT.tag(fr, False)
        if t >= s5:
            if t < t114:
                appear(fr, ilu_rec, W / 2, 900 + 7 * math.sin(t * 4), t, s5)
            else:
                p = ease((t - t114) / 0.45)
                RT.put(fr, ilu_rec, W / 2, lerp(900, 1320, p), sc=lerp(1, 0.6, p))
        if t >= t114:
            blkO.draw(fr, t, timesO, W / 2, 560)
            blkO.draw_band(fr, t, t115 + 0.9, W / 2, 560)
            appear(fr, badge5, W / 2, 275, t, t114)
        if t >= t118:
            appear(fr, chip_conta, W / 2, 1090, t, t118)
        return fr

    # ---------------- 6: RECAPITULAÇÃO + SALVA / MANDA (verde)
    rows = [("いらっしゃいませ", "irasshaimase"), ("なんめいさまですか", "nanmei-sama desu ka"),
            ("ふたりです", "futari desu"), ("これをおねがいします", "kore o onegaishimasu"),
            ("おかいけいおねがいします", "okaikei onegaishimasu")]

    def row_img(n, kana, romaji):
        w, h = 880, 140
        im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((30, 40, 30 + w, 40 + h), radius=44, fill=(20, 40, 30, 70))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((30, 30, 30 + w, 30 + h), radius=44, fill=C["creme_fundo"])
        d.ellipse((52, 30 + h / 2 - 38, 128, 30 + h / 2 + 38), fill=C["vermelho_ume"])
        nt = RT.timg(str(n), 52, C["creme_fundo"])
        im.alpha_composite(nt, (90 - nt.width // 2, int(30 + h / 2 - nt.height / 2)))
        kt = RT.kimg(kana, 56, C["verde_aoi"])
        rt = RT.timg(romaji, 34, TEXTO, 600, 0.02)
        im.alpha_composite(kt, (160, 30 + 20))
        im.alpha_composite(rt, (160, 30 + h - 20 - rt.height))
        return im

    row_imgs = [row_img(i + 1, k, r) for i, (k, r) in enumerate(rows)]
    mark = IL.png(IL.marcador(), 200)
    plane = IL.png(IL.aviao(), 300)
    l_salva = RT.timg("SALVA", 190, OURO)
    l_esse = RT.timg("ESSE VÍDEO", 96, C["creme_fundo"])
    l_manda = RT.timg("MANDA", 170, OURO)
    l_quem = RT.timg("PRA QUEM VAI VIAJAR", 76, C["creme_fundo"])
    l_voce = RT.timg("COM VOCÊ", 104, OURO)
    s6 = T("a2", 1) + 0.14
    ta0, tSalva, tEsse = s6, T("a2", 10), T("a2", 11)
    tManda, tQuem, tVia, tVoce = T("a2", 14), T("a2", 16), T("a2", 18), T("a2", 22)
    row_t = [ta0 + 0.1 + i * 0.4 for i in range(5)]

    def scene_cta(t):
        fr = RT.drift(RT.BG_VERDE, t).copy()
        RT.tag(fr, True)
        if t < tManda + 0.1:
            out_p = ease((t - (tSalva - 0.1)) / 0.3) if t > tSalva - 0.1 else 0
            for i, im in enumerate(row_imgs):
                if t >= row_t[i]:
                    p = ease((t - row_t[i]) / 0.3)
                    RT.put(fr, im, W / 2 + (1 - p) * 500 - out_p * 700, 520 + i * 160, a=p * (1 - out_p))
            appear(fr, mark, W / 2, 500, t, tSalva)
            appear(fr, l_salva, W / 2, 740, t, tSalva + 0.02)
            if t >= tEsse:
                RT.reveal_up(fr, l_esse, W / 2, 900, (t - tEsse) / 0.3, 1 - ease((t - tManda + 0.2) / 0.25) if t > tManda - 0.2 else 1)
        if t >= tManda - 0.05:
            po = 1 - ease((t - tManda - 0.1) / 0.25) if t < tManda + 0.1 else 1
            # troca de grupo: SALVA sai e MANDA entra
            appear(fr, l_manda, W / 2, 640, t, tManda)
            if t >= tQuem:
                RT.reveal_up(fr, l_quem, W / 2, 800, (t - tQuem) / 0.3)
            if t >= tVoce:
                RT.reveal_up(fr, l_voce, W / 2, 940, (t - tVoce) / 0.3)
            if t >= tVia - 0.1:
                fly = (t - tVia + 0.1) / 2.4
                fly = min(1.0, max(0.0, fly))
                RT.put(fr, plane, -250 + fly * 1580, 1340 - fly * 170 + 10 * math.sin(t * 5))
        return fr

    # ---------------- 7: FINAL (creme)
    logo = R.fit(Image.open(os.path.join(R.MARCA, "logos", "aoi-vertical-cor.png")).convert("RGBA"), 470)
    matri, breve = RT.timg("MATRÍCULAS", 128, C["verde_aoi"]), RT.timg("EM BREVE", 128, C["vermelho_ume"])
    out_k = RT.kimg("じゃあね、また！", 118, C["verde_aoi"])
    out_r = RT.timg("JAA NE, MATA!", 62, C["vermelho_ume"], 700, 0.06)
    out_t = RT.timg("tchau, até mais!", 52, TEXTO, 600, 0.02)
    s7 = T("a1", 153) + 0.14
    tSeg, tMat, tBre, tTch = T("a1", 157), T("a1", 165), T("a1", 166), T("a1", 169)

    def scene_final(t):
        fr = BG_CREME.copy()
        appear(fr, logo, W / 2, 520, t, s7)
        if t >= tSeg:
            q = back((t - tSeg) / 0.4)
            pulse = 1 + 0.04 * math.sin((t - tSeg) * 2 * math.pi / (2 * R.BEAT))
            btn = RA.cta_button("SIGA @espacoaoi", scale=max(0.3, 1.25 * q * pulse))
            RT.put(fr, btn, W / 2, 900)
        gone = 1 - ease((t - (tTch - 0.1)) / 0.25) if t > tTch - 0.1 else 1
        if t >= tMat and gone > 0:
            RT.reveal_up(fr, matri, W / 2, 1130, (t - tMat) / 0.3, gone)
        if t >= tBre - 0.1 and gone > 0:
            appear(fr, RT.with_alpha(breve, gone), W / 2, 1285, t, tBre - 0.1)
        if t >= tTch:
            RT.reveal_up(fr, out_k, W / 2, 1110, (t - tTch) / 0.35)
            if t >= tTch + 0.25:
                appear(fr, out_r, W / 2, 1240, t, tTch + 0.25)
                RT.reveal_up(fr, out_t, W / 2, 1340, (t - tTch - 0.45) / 0.3)
        return fr

    # ---------------- sequência de cenas + transições
    seq = [
        (0.0, scene_hook, None),
        (T("a1", 15) + 0.14, scene_irasshai, ("ume", 0.45)),
        (T("a1", 47) + 0.14, scene_nanmei, ("push", 0.35)),
        (T("a1", 62) + 0.14, scene_futari, ("wipe", 0.32, C["laranja"])),
        (T("a1", 70) + 0.14, scene_pedir, ("push", 0.32)),
        (T("a1", 104) + 0.14, scene_okaikei, ("wipe", 0.32, C["vermelho_ume"])),
        (T("a2", 1) + 0.14, scene_cta, ("wipe", 0.32, C["laranja"])),
        (T("a1", 153) + 0.14, scene_final, ("ume", 0.45)),
    ]

    def frame(t):
        k = max(i for i, x in enumerate(seq) if t >= x[0] - (x[2][1] if x[2] else 0))
        st, fn, tr = seq[k]
        if tr and t < st:
            d = tr[1]
            p = (t - (st - d)) / d
            old, new = seq[k - 1][1](t), fn(t)
            if tr[0] == "ume":
                fr = RT.ume_reveal(old, new, p)
            elif tr[0] == "wipe":
                fr = RT.diag_wipe(old, new, p, tr[2])
            else:
                fr = RT.push(old, new, p)
        else:
            fr = fn(t)
        RT.caption(fr, caps, t, voice_end, kin)
        return fr

    if frames_mode:
        ts = [float(a) for a in sys.argv[2:]]
        for t in ts:
            frame(t).convert("RGB").save(f"{OUT}/fr_{t:06.2f}.png")
        print("frames ok:", ts)
        return

    # ---------------- renderização
    vid = f"{OUT}/video.mp4"
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                             "-pix_fmt", "yuv420p", vid], stdin=subprocess.PIPE)
    for fi in range(nframes):
        proc.stdin.write(frame(fi / FPS).tobytes())
        if fi % 150 == 0:
            print(f"  quadro {fi}/{nframes}", flush=True)
    proc.stdin.close(); proc.wait()

    # ---------------- efeitos sonoros
    tr_t = [x[0] - x[2][1] for x in seq[1:]]
    pop, whoosh, ding, carimbo, alerta = RA.sfx_pop, RA.sfx_whoosh, RA.sfx_ding, RA.sfx_carimbo, RA.sfx_alerta
    evs = [(T("a1", 0), carimbo()), (n11, pop()), (T("a1", 13), pop())]
    evs += [(t_ - 0.03, whoosh(0.4)) for t_ in tr_t]
    evs += [(s1, pop()), (t25 + 0.85, ding()), (t29, pop()), (t35, pop()), (t42, pop()),
            (s2, pop()), (t52 + 1.0, ding()), (t59, pop()),
            (s3, pop()), (t64, carimbo()), (t68 + 0.55, ding()), (t69 + 0.15, pop()),
            (s4, pop()), (tTap + 0.1, pop()), (bandK, ding()), (tI, pop()), (tC, pop()), (tD + 0.1, ding()),
            (tD + 0.15, pop()), (tE, pop()),
            (s5, pop()), (t115 + 0.9, ding()), (t118, pop()),
            (ta0 + 0.1, pop()), (tSalva, pop()), (tManda, carimbo()), (tVia, whoosh(0.5)), (tVoce, pop()),
            (s7, pop()), (tSeg, ding()), (tMat, pop()), (tBre, pop()), (tTch, pop())]
    evs.sort(key=lambda e: e[0])
    kept, last = [], -9
    for tt, snd in evs:
        if tt >= 0 and tt - last >= 0.6:
            kept.append((tt, snd)); last = tt
    sfx = np.zeros(int((END + 2) * SR))
    for tt, snd in kept:
        i = int(tt * SR); sfx[i:i + len(snd)] += snd[: len(sfx) - i]
    ticks = timesI + timesN + timesF + times1 + times2[3:6] + timesO + row_t
    for k, kt in enumerate(ticks):
        snd = RA.sfx_tecla(k % 40) * 1.6; i = int(kt * SR); sfx[i:i + len(snd)] += snd[: len(sfx) - i]
    sfx_path = f"{OUT}/sfx.wav"
    with wave.open(sfx_path, "wb") as wv:
        wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR)
        wv.writeframes((np.clip(sfx, -1, 1) * 32767).astype("<i2").tobytes())
    mpath = f"{OUT}/musica.wav"
    R.music(mpath, END)
    final = f"{OUT}/aoi-reels-parte2.mp4"
    RA.sh(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", voice_wav, "-i", mpath, "-i", sfx_path, "-filter_complex",
           f"[1:a]apad=whole_dur={END},asplit=2[v1][v2];"
           "[2:a]volume=0.22[m];[m][v2]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=400[md];"
           f"[3:a]atrim=0:{END},volume=0.9[fx];"
           "[v1][md][fx]amix=inputs=3:normalize=0,aresample=48000,"
           "loudnorm=I=-14:TP=-1.5:LRA=9,alimiter=limit=0.84:attack=0.5:release=40:level=disabled[a]",
           "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ac", "2",
           "-movflags", "+faststart", "-shortest", final])
    print(f"sons: {len(kept)} + {len(ticks)} tiques")
    print("ok:", final)


if __name__ == "__main__":
    main()
