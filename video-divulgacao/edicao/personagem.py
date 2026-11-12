"""Personagem "Sensei" da AOI em SVG — estilo fofo (chibi/anime), traço limpo, compatível com a identidade AOI.

Referência aprovada: cabelo longo e ondulado com risca no meio, olhos grandes e brilhantes,
sorriso aberto, bochechas rosadas, blusa creme com cruzinhas, brincos dourados,
cordão preto com pingente dourado oval.

personagem_svg(boca, olhos, sobrancelha, pose, aceno) -> str
  boca:        "fechada" | "media" | "aberta" | "o"
  olhos:       "abertos" | "fechados" | "surpresa" | "felizes"
  sobrancelha: "normal" | "alta"
  pose:        "neutra" | "acenando"
  aceno:       ângulo da mão (graus) quando acenando
"""

LINHA = "#3a2526"        # contorno externo (marrom-escuro quente)
LINHA_FINA = "#5a3a36"   # traços internos
PELE = "#fadbc8"
PELE_SOMBRA = "#efc0a8"
PELE_SOMBRA2 = "#e6ac93"
CABELO_A = "#2c2532"     # topo
CABELO_B = "#141017"     # pontas
CABELO_DENTRO = "#0d0a0e"
CABELO_LUZ = "#5b5470"
BLUSA = "#fcf5ec"
BLUSA_SOMBRA = "#eadbc9"
ESTAMPA = "#8e88a0"
BLUSH = "#f4938a"
OURO = "#e3a83c"
OURO_ESC = "#b9802a"
OURO_CLARO = "#f8dc8e"
BOCA_DENTRO = "#8c2e35"
LINGUA = "#ef8c84"

SW = 6      # contorno externo
SWI = 4     # contorno interno


DEFS = f'''
<defs>
  <linearGradient id="gCabelo" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{CABELO_A}"/><stop offset="1" stop-color="{CABELO_B}"/>
  </linearGradient>
  <radialGradient id="gIris" cx="0.5" cy="0.72" r="0.7">
    <stop offset="0" stop-color="#9a6243"/><stop offset="0.55" stop-color="#4a2c20"/><stop offset="1" stop-color="#1a0f0d"/>
  </radialGradient>
  <linearGradient id="gOuro" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{OURO_CLARO}"/><stop offset="0.5" stop-color="{OURO}"/><stop offset="1" stop-color="{OURO_ESC}"/>
  </linearGradient>
  <radialGradient id="gBlush" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="{BLUSH}" stop-opacity="0.75"/><stop offset="1" stop-color="{BLUSH}" stop-opacity="0"/>
  </radialGradient>
  <clipPath id="cRosto"><path d="{{ROSTO}}"/></clipPath>
  <clipPath id="cCorpo"><path d="{{CORPO}}"/></clipPath>
</defs>'''

ROSTO = ("M500,264 C640,264 704,362 702,478 C700,592 652,676 566,708 C542,716 520,720 500,720 "
         "C480,720 458,716 434,708 C348,676 300,592 298,478 C296,362 360,264 500,264 Z")
CORPO = ("M206,1200 C210,1040 248,944 330,904 C382,880 430,862 456,792 L500,884 L544,792 "
         "C570,862 618,880 670,904 C752,944 790,1040 794,1200 Z")


def _olho(cx, cy, estado, lado):
    if estado == "fechados":
        return (f'<path d="M{cx - 40},{cy + 2} Q{cx},{cy + 24} {cx + 40},{cy + 2}" stroke="{LINHA}" stroke-width="9" fill="none" stroke-linecap="round"/>'
                f'<path d="M{cx + lado * 40},{cy + 2} l{lado * 12},-6" stroke="{LINHA}" stroke-width="6" stroke-linecap="round"/>')
    if estado == "felizes":
        return f'<path d="M{cx - 40},{cy + 10} Q{cx},{cy - 32} {cx + 40},{cy + 10}" stroke="{LINHA}" stroke-width="10" fill="none" stroke-linecap="round"/>'
    big = estado == "surpresa"
    rx, ry = (40, 40) if big else (40, 36)
    irx, iry = (30, 37) if big else (29, 35)
    clip = f"cOlho{lado}{estado}"
    branco = f"M{cx - rx},{cy + 4} C{cx - rx},{cy - ry} {cx + rx},{cy - ry - 6} {cx + rx},{cy} C{cx + rx},{cy + ry * 0.9} {cx - rx},{cy + ry * 0.95} {cx - rx},{cy + 4} Z"
    return f'''
    <clipPath id="{clip}"><path d="{branco}"/></clipPath>
    <path d="{branco}" fill="#ffffff"/>
    <g clip-path="url(#{clip})">
      <ellipse cx="{cx + lado * 2}" cy="{cy + 3}" rx="{irx}" ry="{iry}" fill="url(#gIris)"/>
      <ellipse cx="{cx + lado * 2}" cy="{cy + 4}" rx="{irx * 0.42}" ry="{iry * 0.48}" fill="#120a0a"/>
      <path d="M{cx - rx},{cy - ry * 0.5} C{cx - 10},{cy - ry - 4} {cx + 20},{cy - ry - 6} {cx + rx},{cy - ry * 0.4} L{cx + rx},{cy - ry * 0.1} C{cx + 10},{cy - ry * 0.55} {cx - 10},{cy - ry * 0.5} {cx - rx},{cy - ry * 0.2} Z" fill="#2a1a18" opacity="0.35"/>
      <ellipse cx="{cx + 12}" cy="{cy - 12}" rx="11" ry="12" fill="#ffffff"/>
      <circle cx="{cx - 13}" cy="{cy + 17}" r="5" fill="#ffffff" opacity="0.95"/>
      <circle cx="{cx + 16}" cy="{cy + 14}" r="2.6" fill="#ffffff" opacity="0.8"/>
    </g>
    <path d="M{cx - rx - 6},{cy + 2} C{cx - rx + 2},{cy - ry - 4} {cx + rx - 4},{cy - ry - 10} {cx + rx + 8},{cy - 6}" stroke="{LINHA}" stroke-width="10" fill="none" stroke-linecap="round"/>
    <path d="M{cx + lado * (rx + 4)},{cy - 8 if lado > 0 else cy - 2} q{lado * 10},-4 {lado * 18},-16 M{cx + lado * (rx - 6)},{cy - ry * 0.55} q{lado * 8},-6 {lado * 12},-18" stroke="{LINHA}" stroke-width="6" fill="none" stroke-linecap="round"/>
    <path d="M{cx - rx + 8},{cy - ry - 14} C{cx - 6},{cy - ry - 26} {cx + 18},{cy - ry - 26} {cx + rx - 4},{cy - ry - 12}" stroke="{LINHA_FINA}" stroke-width="3" fill="none" stroke-linecap="round" opacity="0.6"/>
    <path d="M{cx - rx * 0.35},{cy + ry * 0.92} Q{cx + rx * 0.2},{cy + ry} {cx + rx * 0.7},{cy + ry * 0.7}" stroke="{LINHA_FINA}" stroke-width="3" fill="none" stroke-linecap="round" opacity="0.55"/>
    '''


def _boca(estado):
    cx, cy = 500, 624
    if estado == "fechada":
        return (f'<path d="M{cx - 30},{cy - 4} Q{cx - 15},{cy + 14} {cx},{cy + 4} Q{cx + 15},{cy + 14} {cx + 30},{cy - 4}" stroke="{LINHA}" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    if estado == "o":
        return (f'<ellipse cx="{cx}" cy="{cy + 8}" rx="17" ry="21" fill="{BOCA_DENTRO}" stroke="{LINHA}" stroke-width="5"/>'
                f'<ellipse cx="{cx}" cy="{cy + 19}" rx="9" ry="6" fill="{LINGUA}"/>')
    w, h = (28, 22) if estado == "media" else (42, 44)
    forma = f"M{cx - w},{cy - 6} Q{cx},{cy + 2} {cx + w},{cy - 6} Q{cx + w * 0.86},{cy + h} {cx},{cy + h + 4} Q{cx - w * 0.86},{cy + h} {cx - w},{cy - 6} Z"
    return f'''
    <clipPath id="cBoca{estado}"><path d="{forma}"/></clipPath>
    <path d="{forma}" fill="{BOCA_DENTRO}"/>
    <g clip-path="url(#cBoca{estado})">
      <rect x="{cx - w}" y="{cy - 10}" width="{2 * w}" height="{h * 0.3 + 6}" fill="#ffffff"/>
      <ellipse cx="{cx}" cy="{cy + h + 4}" rx="{w * 0.62}" ry="{h * 0.45}" fill="{LINGUA}"/>
    </g>
    <path d="{forma}" fill="none" stroke="{LINHA}" stroke-width="5" stroke-linejoin="round"/>
    '''


def _estampa():
    out = []
    for row in range(8):
        for col in range(11):
            x = 170 + col * 64 + (32 if row % 2 else 0)
            y = 916 + row * 42
            out.append(f'<path d="M{x - 6},{y} h12 M{x},{y - 6} v12" stroke="{ESTAMPA}" stroke-width="3.6" stroke-linecap="round"/>')
    return "".join(out)


def _brinco(x, y):
    return (f'<circle cx="{x}" cy="{y}" r="7" fill="url(#gOuro)" stroke="{LINHA}" stroke-width="2.5"/>'
            f'<path d="M{x},{y + 7} C{x - 10},{y + 18} {x - 7},{y + 30} {x},{y + 32} C{x + 7},{y + 30} {x + 10},{y + 18} {x},{y + 7} Z" fill="url(#gOuro)" stroke="{LINHA}" stroke-width="2.5"/>'
            f'<circle cx="{x - 2}" cy="{y + 20}" r="2.4" fill="#fff6d8"/>')


def _cabelo_tras():
    # silhueta com volume e mechas onduladas terminando em pontas
    return f'''<path d="M500,206 C340,206 240,318 238,458
        C236,540 222,600 232,666 C242,730 208,780 214,852 C220,918 188,964 200,1024
        C208,1066 238,1090 276,1100 C262,1072 270,1046 290,1040 C300,1070 330,1086 360,1086
        C352,1070 356,1060 372,1060 L628,1060 C644,1060 648,1070 640,1086
        C670,1086 700,1070 710,1040 C730,1046 738,1072 724,1100
        C762,1090 792,1066 800,1024 C812,964 780,918 786,852 C792,780 758,730 768,666
        C778,600 764,540 762,458 C760,318 660,206 500,206 Z"
        fill="url(#gCabelo)" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
      <path d="M300,500 C292,600 300,700 290,800 M710,500 C718,600 700,700 712,800" stroke="{CABELO_DENTRO}" stroke-width="40" fill="none" stroke-linecap="round" opacity="0.55"/>'''


def _cabelo_frente():
    esq = ("M500,262 C452,266 402,290 370,336 C338,380 316,444 312,512 C306,582 314,640 300,702 "
           "C288,760 302,812 290,872 C282,924 292,972 318,1008 C324,974 334,944 338,912 "
           "C346,862 330,822 340,772 C350,722 334,682 340,632 C346,560 340,480 364,420 "
           "C386,362 432,308 500,282 Z")
    dir_ = ("M500,262 C548,266 598,290 630,336 C662,380 684,444 688,512 C694,582 686,640 700,702 "
            "C712,760 698,812 710,872 C718,924 708,972 682,1008 C676,974 666,944 662,912 "
            "C654,862 670,822 660,772 C650,722 666,682 660,632 C654,560 660,480 636,420 "
            "C614,362 568,308 500,282 Z")
    return f'''
    <path d="{esq}" fill="url(#gCabelo)" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
    <path d="{dir_}" fill="url(#gCabelo)" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
    <!-- mechas internas -->
    <path d="M470,286 C420,320 384,380 370,460 M330,560 C322,640 330,720 318,800 C310,860 318,920 316,970"
          stroke="{CABELO_DENTRO}" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.9"/>
    <path d="M530,286 C580,320 616,380 630,460 M670,560 C678,640 670,720 682,800 C690,860 682,920 684,970"
          stroke="{CABELO_DENTRO}" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.9"/>
    <!-- brilho "anel" -->
    <path d="M408,300 C430,282 458,272 484,270" stroke="{CABELO_LUZ}" stroke-width="12" fill="none" stroke-linecap="round"/>
    <path d="M592,300 C570,282 542,272 516,270" stroke="{CABELO_LUZ}" stroke-width="12" fill="none" stroke-linecap="round"/>
    <path d="M300,330 C290,350 282,372 278,392 M700,330 C710,350 718,372 722,392" stroke="{CABELO_LUZ}" stroke-width="9" fill="none" stroke-linecap="round"/>
    <path d="M306,720 C298,760 302,790 296,820 M694,720 C702,760 698,790 704,820" stroke="{CABELO_LUZ}" stroke-width="6" fill="none" stroke-linecap="round" opacity="0.8"/>
    <!-- risca -->
    <path d="M500,256 L500,290" stroke="{CABELO_DENTRO}" stroke-width="4" stroke-linecap="round"/>
    '''


def _braco_acenando(ang):
    """Manga larga + mão grande acenando (lado esquerdo do observador). ang gira a mão no pulso."""
    px, py = 222, 690
    manga = (f'<path d="M232,1200 C246,1010 232,860 176,744 C196,700 262,684 292,706 C350,800 392,960 388,1200 Z" '
             f'fill="{BLUSA}" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>'
             f'<path d="M186,742 C214,712 262,702 290,716" stroke="{BLUSA_SOMBRA}" stroke-width="10" fill="none" stroke-linecap="round"/>'
             f'<path d="M260,820 C300,860 330,900 350,950" stroke="{BLUSA_SOMBRA}" stroke-width="8" fill="none" stroke-linecap="round"/>')
    dedos = ""
    for k, (dx, l) in enumerate([(-36, 60), (-13, 74), (11, 72), (33, 58)]):
        dedos += (f'<rect x="{dx - 12}" y="{-64 - l}" width="24" height="{l + 30}" rx="12" fill="{PELE}" '
                  f'stroke="{LINHA}" stroke-width="5" transform="rotate({(k - 1.5) * 8}, {dx}, -54)"/>')
    mao = f'''
    <g transform="translate({px},{py}) rotate({ang}) scale(1.45)">
      {dedos}
      <path d="M30,-52 C66,-74 80,-44 50,-24" fill="{PELE}" stroke="{LINHA}" stroke-width="5" stroke-linecap="round"/>
      <ellipse cx="0" cy="-40" rx="47" ry="42" fill="{PELE}" stroke="{LINHA}" stroke-width="5"/>
      <path d="M-32,-64 h64" stroke="{PELE}" stroke-width="14" stroke-linecap="round"/>
      <path d="M-18,-22 q18,10 36,0" stroke="{PELE_SOMBRA2}" stroke-width="4" fill="none" stroke-linecap="round"/>
    </g>'''
    return mao + manga


def personagem_svg(boca="fechada", olhos="abertos", sobrancelha="normal", pose="neutra", aceno=0, w=1000, h=1200):
    dy = -16 if sobrancelha == "alta" else 0
    defs = DEFS.replace("{ROSTO}", ROSTO).replace("{CORPO}", CORPO)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 1000 1200">
  {defs}
  {_cabelo_tras()}
  <!-- pescoço com sombra do queixo -->
  <path d="M454,660 L454,786 Q500,814 546,786 L546,660 Z" fill="{PELE}" stroke="{LINHA}" stroke-width="{SW}"/>
  <path d="M454,690 Q500,744 546,690 L546,660 L454,660 Z" fill="{PELE_SOMBRA2}"/>
  <!-- blusa -->
  <path d="{CORPO}" fill="{BLUSA}" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
  <g clip-path="url(#cCorpo)">
    {_estampa()}
    <path d="M206,1200 C210,1040 248,944 330,904 C300,980 286,1080 290,1200 Z" fill="{BLUSA_SOMBRA}" opacity="0.8"/>
    <path d="M794,1200 C790,1040 752,944 670,904 C700,980 714,1080 710,1200 Z" fill="{BLUSA_SOMBRA}" opacity="0.8"/>
    <path d="M500,884 L500,1200" stroke="{BLUSA_SOMBRA}" stroke-width="5"/>
  </g>
  <path d="M456,792 L500,884 L544,792 Q500,822 456,792 Z" fill="{PELE}" stroke="{LINHA}" stroke-width="{SWI}" stroke-linejoin="round"/>
  <path d="M440,800 L500,912 L560,800" stroke="{LINHA_FINA}" stroke-width="{SWI}" fill="none" stroke-linejoin="round" opacity="0.7"/>
  <circle cx="500" cy="1040" r="6" fill="{BLUSA}" stroke="{LINHA_FINA}" stroke-width="3"/>
  <circle cx="500" cy="1110" r="6" fill="{BLUSA}" stroke="{LINHA_FINA}" stroke-width="3"/>
  <!-- cordão + pingente -->
  <path d="M460,790 Q470,890 500,956 Q530,890 540,790" stroke="#141014" stroke-width="5" fill="none"/>
  <ellipse cx="500" cy="984" rx="23" ry="31" fill="url(#gOuro)" stroke="{LINHA}" stroke-width="4"/>
  <ellipse cx="500" cy="984" rx="13" ry="19" fill="none" stroke="#fff1c4" stroke-width="3" opacity="0.8"/>
  <!-- rosto -->
  <path d="{ROSTO}" fill="{PELE}" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
  <g clip-path="url(#cRosto)">
    <path d="M330,640 C380,700 440,724 500,724 C560,724 620,700 670,640 C640,700 580,740 500,740 C420,740 360,700 330,640 Z" fill="{PELE_SOMBRA}" opacity="0.6"/>
  </g>
  <!-- bochechas com tracinhos -->
  <ellipse cx="378" cy="598" rx="50" ry="30" fill="url(#gBlush)"/>
  <ellipse cx="622" cy="598" rx="50" ry="30" fill="url(#gBlush)"/>
  <path d="M362,596 l10,-12 M380,598 l10,-12 M398,600 l10,-12 M604,600 l10,-12 M622,598 l10,-12 M640,596 l10,-12"
        stroke="{BLUSH}" stroke-width="3.5" stroke-linecap="round" opacity="0.9"/>
  {_olho(410, 520, olhos, -1)}
  {_olho(590, 520, olhos, 1)}
  <path d="M368,{440 + dy} Q410,{418 + dy} 452,{432 + dy}" stroke="{CABELO_B}" stroke-width="7" fill="none" stroke-linecap="round"/>
  <path d="M548,{432 + dy} Q590,{418 + dy} 632,{440 + dy}" stroke="{CABELO_B}" stroke-width="7" fill="none" stroke-linecap="round"/>
  <path d="M494,574 Q501,582 508,574" stroke="{LINHA_FINA}" stroke-width="4" fill="none" stroke-linecap="round"/>
  {_boca(boca)}
  {_cabelo_frente()}
  {_brinco(326, 650)}
  {_brinco(674, 650)}
  {_braco_acenando(aceno) if pose == "acenando" else ""}
</svg>'''


if __name__ == "__main__":
    import sys
    import cairosvg
    cairosvg.svg2png(bytestring=personagem_svg().encode(), write_to=sys.argv[1], output_width=600)
