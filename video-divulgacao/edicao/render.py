#!/usr/bin/env python3
"""Reels de divulgação do Espaço AOI — edição 100% em código.

Uso:
  BRUTOS=/caminho/brutos WORK=/caminho/work FONTS=/caminho/fonts/ttf python3 render.py

Gera em $WORK/saida/:
  aoi-reels-com-musica.mp4   trilha original (koto pentatônico) + som ambiente
  aoi-reels-sem-musica.mp4   só som ambiente, para usar um áudio do Instagram
"""
import glob, json, math, os, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
MARCA = os.path.join(HERE, "..", "marca")
BRUTOS = os.environ["BRUTOS"]
WORK = os.environ["WORK"]
FONTS = os.environ["FONTS"]
W, H, FPS = 1080, 1920, 30

ID = json.load(open(os.path.join(MARCA, "identidade.json")))
C = {k: v for k, v in ID["cores"].items()}
TEXT = "#2a2a28"

BPM = 96
BEAT = 60 / BPM            # 0.625 s
SCENE = 4 * BEAT           # 2.5 s por cena
XF = 0.25                  # duração do crossfade
END = 8 * BEAT             # 5 s de encerramento

# (clipe, início em s, texto)  — ordem aprovada no storyboard
CENAS = [
    ("IMG_8397", 0.6, {"kind": "hook", "lines": ["Como é estudar japonês", "no Espaço AOI?"]}),
    ("IMG_8405", 0.0, {"kind": "furi", "jp": [("日本語", "にほんご"), ("を", ""), ("学", "まな"), ("ぶ", "")], "pt": "aprender japonês"}),
    ("IMG_8399", 1.6, {"kind": "pill", "text": "conversa de verdade"}),
    ("IMG_8401", 0.5, {"kind": "pill", "text": "leitura em voz alta"}),
    ("IMG_8402", 12.6, {"kind": "furi", "jp": [("好奇心", "こうきしん")], "pt": "curiosidade", "big": True}),
    ("IMG_8395", 9.0, {"kind": "furi", "jp": [("規律", "きりつ")], "pt": "disciplina", "big": True}),
    ("IMG_8396", 2.0, {"kind": "furi", "jp": [("興味", "きょうみ")], "pt": "interesse", "big": True}),
    ("IMG_8400", 0.5, None),
    ("IMG_8398", 21.6, {"kind": "pill", "text": "e muitas risadas"}),
    ("IMG_8403", 3.0, None),
    ("IMG_8397", 5.9, {"kind": "pill", "text": "aprendendo juntos"}),
]

os.makedirs(f"{WORK}/seg", exist_ok=True)
os.makedirs(f"{WORK}/ov", exist_ok=True)
os.makedirs(f"{WORK}/saida", exist_ok=True)


def run(cmd):
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------- tipografia
def jfont(w, size):
    return ImageFont.truetype(f"{FONTS}/JosefinSans-{w}.ttf", size)


_KOSUGI = []
for p in sorted(glob.glob(f"{FONTS}/kosugi/*.ttf")):
    from fontTools.ttLib import TTFont
    _KOSUGI.append((p, set(TTFont(p).getBestCmap().keys())))
_kcache = {}


def kfont(ch, size):
    for p, cmap in _KOSUGI:
        if ord(ch) in cmap:
            key = (p, size)
            if key not in _kcache:
                _kcache[key] = ImageFont.truetype(p, size)
            return _kcache[key]
    raise ValueError(f"sem glifo para {ch!r}")


def jp_width(s, size):
    return sum(kfont(c, size).getlength(c) for c in s)


def draw_jp(d, x, y, s, size, fill):
    for c in s:
        f = kfont(c, size)
        d.text((x, y), c, font=f, fill=fill)
        x += f.getlength(c)


# ---------------------------------------------------------------- formas
def blob(w, h, seed=3, wobble=0.035):
    """Bolha orgânica creme, no espírito das caixas dos stories AOI."""
    rng = np.random.default_rng(seed)
    n = 240
    ph = rng.uniform(0, 2 * np.pi, 3)
    pts = []
    for i in range(n):
        a = 2 * np.pi * i / n
        r = 1 + wobble * (np.sin(2 * a + ph[0]) + 0.6 * np.sin(3 * a + ph[1]) + 0.4 * np.sin(5 * a + ph[2]))
        # superelipse (mais "quadradinha" que um círculo)
        ca, sa = np.cos(a), np.sin(a)
        e = 3.2
        sx = np.sign(ca) * abs(ca) ** (2 / e)
        sy = np.sign(sa) * abs(sa) ** (2 / e)
        pts.append((w / 2 + sx * r * w / 2 * 0.96, h / 2 + sy * r * h / 2 * 0.96))
    return pts


def card(w, h, seed=3, alpha=242):
    pad = 40
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).polygon([(x + pad, y + pad + 10) for x, y in blob(w, h, seed)], fill=(40, 30, 20, 70))
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    im.alpha_composite(sh)
    ImageDraw.Draw(im).polygon([(x + pad, y + pad) for x, y in blob(w, h, seed)], fill=C["creme_fundo"] + format(alpha, "02x"))
    return im, pad


UME = Image.open(os.path.join(MARCA, "logos", "flor-ume-cor.png")).convert("RGBA")
LOGO_V = Image.open(os.path.join(MARCA, "logos", "aoi-vertical-cor.png")).convert("RGBA")
FOLHA_B = Image.open(os.path.join(MARCA, "logos", "aoi-folha-branco.png")).convert("RGBA")


def fit(im, h):
    return im.resize((round(im.width * h / im.height), h), Image.LANCZOS)


# ---------------------------------------------------------------- overlays
def tag_overlay():
    """@espacoaoi pequeno no topo, como nos templates."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = jfont(400, 40)
    t = "@espacoaoi"
    tw = f.getlength(t) + 3 * len(t)
    leaf = fit(FOLHA_B, 54)
    x = (W - tw - leaf.width - 12) / 2
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    for dx in (0,):
        cx = x + leaf.width + 12
        for ch in t:
            sd.text((cx, 192), ch, font=f, fill=(0, 0, 0, 150))
            cx += f.getlength(ch) + 3
    sh = sh.filter(ImageFilter.GaussianBlur(5))
    im.alpha_composite(sh)
    im.alpha_composite(leaf, (int(x), 172))
    cx = x + leaf.width + 12
    for ch in t:
        d.text((cx, 190), ch, font=f, fill="#ffffff")
        cx += f.getlength(ch) + 3
    return im


def overlay(spec, idx):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    k = spec["kind"]
    if k == "hook":
        f = jfont(600, 74)
        lines = spec["lines"]
        tw = max(f.getlength(s) for s in lines)
        cw, ch = int(tw + 150), 320
        c, pad = card(cw, ch, seed=idx + 5)
        d = ImageDraw.Draw(c)
        flower = fit(UME, 70)
        c.alpha_composite(flower, ((c.width - flower.width) // 2, pad + 20))
        for i, s in enumerate(lines):
            d.text(((c.width - f.getlength(s)) / 2, pad + 108 + i * 88), s, font=f, fill=TEXT)
        im.alpha_composite(c, ((W - c.width) // 2, 1020))
    elif k == "pill":
        f = jfont(600, 54)
        s = spec["text"]
        flower = fit(UME, 54)
        cw, ch = int(f.getlength(s) + flower.width + 120), 130
        c, pad = card(cw, ch, seed=idx + 11, alpha=245)
        d = ImageDraw.Draw(c)
        x0 = pad + (cw - (f.getlength(s) + flower.width + 22)) / 2
        c.alpha_composite(flower, (int(x0), pad + (ch - flower.height) // 2))
        d.text((x0 + flower.width + 22, pad + ch / 2 + 4), s, font=f, fill=TEXT, anchor="lm")
        im.alpha_composite(c, ((W - c.width) // 2, 1240))
    elif k == "furi":
        big = spec.get("big", False)
        ks, rs = (170, 46) if big else (110, 36)
        parts = spec["jp"]
        widths = [jp_width(base, ks) for base, _ in parts]
        tw = sum(widths)
        fpt = jfont(600, 58 if big else 52)
        cw = int(max(tw, fpt.getlength(spec["pt"])) + 170)
        ch = (ks + rs + 150) if big else (ks + rs + 130)
        c, pad = card(cw, ch, seed=idx + 21)
        d = ImageDraw.Draw(c)
        x = pad + (cw - tw) / 2
        y = pad + 40 + rs
        color = C["verde_aoi"] if big else TEXT
        for (base, ruby), bw in zip(parts, widths):
            if ruby:
                rw = jp_width(ruby, rs)
                draw_jp(d, x + (bw - rw) / 2, y - rs - 6, ruby, rs, C["vermelho_ume"])
            draw_jp(d, x, y, base, ks, color)
            x += bw
        s = spec["pt"]
        d.text(((c.width - fpt.getlength(s)) / 2, y + ks + 22), s, font=fpt, fill=TEXT)
        im.alpha_composite(c, ((W - c.width) // 2, 1080 if big else 1140))
    return im


# ---------------------------------------------------------------- encerramento
def ease(x):
    x = min(max(x, 0), 1)
    return 1 - (1 - x) ** 3


def end_frames(path):
    """Cartão final animado (creme + asanoha + logo + chamada)."""
    pat = Image.open(os.path.join(MARCA, "canva", "padroes-seigaiha-asanoha.png")).convert("RGBA")
    s = pat.width / 335
    asa = pat.crop((int(105 * s), int(125 * s), int(232 * s), int(228 * s)))  # aglomerado asanoha laranja
    asa.putalpha(asa.getchannel("A").point(lambda a: int(a * 0.55)))
    bg = Image.new("RGBA", (W, H), C["creme_fundo"])
    a1 = asa.resize((int(asa.width * 1.25), int(asa.height * 1.25)), Image.LANCZOS)
    bg.alpha_composite(a1, (-120, -60))
    a2 = a1.rotate(180)
    bg.alpha_composite(a2, (W - a2.width + 120, H - a2.height + 40))

    f_big = jfont(700, 92)
    f_mid = jfont(400, 50)
    f_at = jfont(600, 60)
    logo = fit(LOGO_V, 470)
    n = round((END + XF) * FPS)
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS),
                             "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / FPS - XF  # t=0 quando o crossfade termina
        fr = bg.copy()
        # logo: escala + fade
        p = ease((t + 0.1) / 0.7)
        if p > 0:
            sc = 0.86 + 0.14 * p
            lg = logo.resize((int(logo.width * sc), int(logo.height * sc)), Image.LANCZOS)
            lg.putalpha(lg.getchannel("A").point(lambda a: int(a * p)))
            fr.alpha_composite(lg, ((W - lg.width) // 2, 300 + (logo.height - lg.height) // 2))
        d = ImageDraw.Draw(fr)

        def line(txt, font, y, t0, color):
            q = ease((t - t0) / 0.45)
            if q <= 0:
                return
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(layer).text(((W - font.getlength(txt)) / 2, y + 30 * (1 - q)), txt, font=font, fill=color)
            layer.putalpha(layer.getchannel("A").point(lambda a: int(a * q)))
            fr.alpha_composite(layer)

        line("Matrículas", f_big, 880, 0.55, C["verde_aoi"])
        line("em breve", f_big, 985, 0.75, C["verde_aoi"])
        line("Quer garantir sua vaga", f_mid, 1170, 1.35, TEXT)
        line("antes de todo mundo?", f_mid, 1232, 1.45, TEXT)
        # botão "Siga @espacoaoi"
        q = ease((t - 2.1) / 0.45)
        if q > 0:
            pulse = 1 + 0.03 * math.sin(max(t - 2.6, 0) * 2 * math.pi / (2 * BEAT)) if t > 2.6 else 1
            txt = "Siga @espacoaoi"
            bw, bh = int((f_at.getlength(txt) + 110) * pulse), int(124 * pulse)
            btn = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            bd = ImageDraw.Draw(btn)
            bd.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=bh // 2, fill=C["vermelho_ume"])
            bd.text((bw / 2, bh / 2 + 3), txt, font=jfont(600, int(60 * pulse)), fill=C["creme_fundo"], anchor="mm")
            btn.putalpha(btn.getchannel("A").point(lambda a: int(a * q)))
            fr.alpha_composite(btn, ((W - bw) // 2, int(1390 + 30 * (1 - q) - (bh - 124) / 2)))
        line("e ative as notificações", jfont(400, 42), 1560, 2.5, TEXT)
        proc.stdin.write(fr.tobytes())
    proc.stdin.close()
    proc.wait()


# ---------------------------------------------------------------- trilha original
def music(path, dur):
    """Trilha original: koto (Karplus-Strong) na escala miyako-bushi, 96 BPM, com batida lo-fi suave."""
    sr = 48000
    N = int(dur * sr) + sr
    out = np.zeros((N, 2))
    rng = np.random.default_rng(7)

    def pluck(freq, length=2.2, amp=0.25, bright=0.996):
        n = int(length * sr)
        p = max(2, int(sr / freq))
        buf = rng.uniform(-1, 1, p)
        y = np.zeros(n)
        for i in range(n):
            y[i] = buf[i % p]
            buf[i % p] = bright * 0.5 * (buf[i % p] + buf[(i + 1) % p])
        env = np.exp(-np.arange(n) / (sr * length * 0.35))
        return amp * y * env

    def add(sig, t, pan=0.0):
        i = int(t * sr)
        j = min(N, i + len(sig))
        out[i:j, 0] += sig[: j - i] * (1 - pan) / 1.4
        out[i:j, 1] += sig[: j - i] * (1 + pan) / 1.4

    # D miyako-bushi: D Eb G A Bb
    base = 293.66
    scale = [0, 1, 5, 7, 8, 12, 13, 17, 19, 20, 24]
    hz = lambda st: base * 2 ** (st / 12)
    cache = {}

    def note(st, **kw):
        key = (st, tuple(sorted(kw.items())))
        if key not in cache:
            cache[key] = pluck(hz(st), **kw)
        return cache[key]

    bars = int(math.ceil(dur / (4 * BEAT)))
    melody = [
        [7, None, 5, 8, 7, None, 5, 1],
        [0, None, None, 1, 5, None, 7, None],
        [12, None, 8, 7, 8, None, 7, 5],
        [7, None, None, None, 5, 1, 0, None],
    ]
    for b in range(bars):
        t0 = b * 4 * BEAT
        # baixo / drone
        add(note(-12, length=3.0, amp=0.22, bright=0.994), t0, -0.1)
        add(note(-5 if b % 2 else -7, length=2.0, amp=0.14, bright=0.994), t0 + 2 * BEAT, 0.1)
        # melodia em colcheias (entra no compasso 2)
        if b >= 1:
            for k, st in enumerate(melody[b % 4]):
                if st is not None:
                    add(note(st, length=1.6, amp=0.16), t0 + k * BEAT / 2, (k % 3 - 1) * 0.35)
        # arpejo em semicolcheias suaves
        if b >= 2:
            arp = [0, 5, 7, 12, 7, 5, 8, 7]
            for k, st in enumerate(arp):
                add(note(st + 12, length=0.8, amp=0.05, bright=0.99), t0 + k * BEAT / 2 + BEAT / 4, 0.5 - (k % 2))
        # batida lo-fi (entra no compasso 1)
        if b >= 1:
            for k in range(4):
                tt = t0 + k * BEAT
                if k in (0, 2):
                    n = int(0.25 * sr)
                    ts = np.arange(n) / sr
                    kick = 0.45 * np.sin(2 * np.pi * (55 + 90 * np.exp(-ts * 30)) * ts) * np.exp(-ts * 14)
                    add(kick, tt)
                else:
                    n = int(0.18 * sr)
                    sn = rng.normal(0, 1, n) * np.exp(-np.arange(n) / sr * 28) * 0.10
                    add(np.convolve(sn, np.ones(6) / 6, "same"), tt)
                n = int(0.05 * sr)
                hat = rng.normal(0, 1, n) * np.exp(-np.arange(n) / sr * 90) * 0.035
                hat = hat - np.convolve(hat, np.ones(4) / 4, "same")
                add(hat, tt + BEAT / 2, 0.3)
    # reverb simples (combs)
    wet = np.zeros_like(out)
    for dly, g in [(0.0297, 0.7), (0.0371, 0.68), (0.0411, 0.66), (0.0437, 0.64)]:
        d = int(dly * sr)
        for ch in range(2):
            x = out[:, ch]
            y = np.zeros_like(x)
            for i in range(d, len(x), d):
                y[i:i + d] = x[i - d:i - d + d][: len(y[i:i + d])] + g * y[i - d:i - d + d][: len(y[i:i + d])]
            wet[:, ch] += y * 0.12
    mix = out + wet
    mix = mix[: int(dur * sr)]
    fade = int(1.8 * sr)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    mix[: int(0.05 * sr)] *= np.linspace(0, 1, int(0.05 * sr))[:, None]
    mix /= np.abs(mix).max() / 0.8
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((mix * 32767).astype("<i2").tobytes())


# ---------------------------------------------------------------- montagem
def main():
    seglen = SCENE + XF
    tag = tag_overlay()
    tag.save(f"{WORK}/ov/tag.png")
    segs = []
    for i, (clip, ss, spec) in enumerate(CENAS):
        ov = overlay(spec, i) if spec else Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if i > 0:
            ov.alpha_composite(tag)
        ovp = f"{WORK}/ov/{i:02d}.png"
        ov.save(ovp)
        out = f"{WORK}/seg/{i:02d}.mkv"
        segs.append(out)
        # leve push-in (Ken Burns) + correção de cor quente
        z0, z1 = (1.0, 1.06) if i % 2 == 0 else (1.06, 1.0)
        vf = (
            f"[0:v]scale=w='trunc({W}*({z0}+({z1}-{z0})*t/{seglen})/2)*2':h=-2:eval=frame,"
            f"crop={W}:{H},setsar=1,fps={FPS},"
            "eq=contrast=1.05:saturation=1.10:gamma=1.02,"
            "colorbalance=rs=0.03:gs=0.0:bs=-0.04:rm=0.02:bm=-0.02,"
            "vignette=angle=PI/5[v];"
            "[1:v]format=rgba,"
            f"fade=in:st=0.15:d=0.35:alpha=1,fade=out:st={seglen - 0.45:.2f}:d=0.3:alpha=1[o];"
            "[v][o]overlay=x=0:y='if(lt(t,0.5),36*(1-t/0.5),0)':format=auto,format=yuv420p[out]"
        )
        af = f"[0:a]atrim=0:{seglen},asetpts=PTS-STARTPTS,highpass=f=90,lowpass=f=9000,aformat=sample_rates=48000:channel_layouts=stereo[a]"
        if not (os.environ.get("REUSE") and os.path.exists(out)):
          run(["ffmpeg", "-v", "error", "-y", "-ss", str(ss), "-t", f"{seglen}", "-i", f"{BRUTOS}/{clip}.mov",
             "-loop", "1", "-t", f"{seglen}", "-i", ovp,
             "-filter_complex", vf + ";" + af, "-map", "[out]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-r", str(FPS),
             "-c:a", "pcm_s16le", out])
        print("cena", i + 1, "ok")

    endp = f"{WORK}/seg/end.mp4"
    if not (os.environ.get("REUSE") and os.path.exists(endp)):
        end_frames(endp)
    print("encerramento ok")

    total = len(CENAS) * SCENE + END
    mpath = f"{WORK}/musica.wav"
    music(mpath, total)
    print("trilha ok")

    # cadeia de xfades
    inputs = []
    for s in segs:
        inputs += ["-i", s]
    inputs += ["-i", endp]
    fc = [f"[{k}:v]fps={FPS},settb=AVTB,setsar=1,format=yuv420p[n{k}]" for k in range(len(segs) + 1)]
    prev = "[n0]"
    off = 0.0
    for k in range(1, len(segs) + 1):
        off += SCENE
        trans = "fade" if k != len(segs) else "fadewhite"
        lab = f"[x{k}]"
        fc.append(f"{prev}[n{k}]xfade=transition={trans}:duration={XF}:offset={off:.4f}{lab}")
        prev = lab
    # áudio ambiente: crossfade das cenas, bem baixo
    aprev = "[0:a]"
    for k in range(1, len(segs)):
        lab = f"[ax{k}]"
        fc.append(f"{aprev}[{k}:a]acrossfade=d={XF}{lab}")
        aprev = lab
    fc.append(f"{aprev}apad=whole_dur={total},atrim=0:{total},afade=t=out:st={total - END - 0.3}:d=1.2[amb]")
    fc.append(f"{prev}trim=0:{total},setpts=PTS-STARTPTS,format=yuv420p[vout]")
    vcommon = ["-map", "[vout]", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high",
               "-pix_fmt", "yuv420p", "-r", str(FPS), "-movflags", "+faststart",
               "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]

    # versão com música
    fc_m = fc + [f"[amb]volume=0.22[ambl]",
                 f"[{len(segs) + 1}:a]volume=1.0[mus]",
                 "[mus][ambl]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,volume=4.5dB,alimiter=limit=0.84:attack=0.5:release=40:level=disabled,asoftclip=type=tanh:threshold=0.9[aout]"]
    run(["ffmpeg", "-v", "error", "-y"] + inputs + ["-i", mpath, "-filter_complex", ";".join(fc_m),
         "-map", "[aout]"] + vcommon + [f"{WORK}/saida/aoi-reels-com-musica.mp4"])
    print("versão com música ok")

    # versão sem música (som ambiente normalizado)
    fc_s = fc + ["[amb]loudnorm=I=-16:TP=-1.5:LRA=11[aout]"]
    run(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", ";".join(fc_s),
         "-map", "[aout]"] + vcommon + [f"{WORK}/saida/aoi-reels-sem-musica.mp4"])
    print("versão sem música ok")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        tag = tag_overlay()
        for i, (clip, ss, spec) in enumerate(CENAS):
            if not spec:
                continue
            ov = overlay(spec, i)
            if i > 0:
                ov.alpha_composite(tag)
            ov.save(f"{WORK}/ov/prev-{i:02d}.png")
        print("preview ok")
    else:
        main()
