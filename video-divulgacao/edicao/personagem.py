"""Personagem "Sensei" da AOI em SVG — estilo fofo (chibi), traço limpo, compatível com a identidade AOI.

Referência: cabelo longo, ondulado, risca no meio; olhos grandes e redondos com brilho;
sorriso aberto; bochechas rosadas; blusa creme com estampa de cruzinhas; brincos dourados;
cordão preto com pingente dourado oval.

personagem_svg(boca, olhos, sobrancelha) -> str
  boca:        "fechada" | "media" | "aberta" | "o"
  olhos:       "abertos" | "fechados" | "surpresa" | "felizes"
  sobrancelha: "normal" | "alta"
"""
import math

LINHA = "#2e2224"
PELE = "#f7d6c1"
PELE_SOMBRA = "#ecbfa6"
CABELO = "#1c171b"
CABELO_LUZ = "#3b3440"
BLUSA = "#fbf3ea"
BLUSA_SOMBRA = "#e9dccd"
ESTAMPA = "#8b8597"
BLUSH = "#f2948a"
OURO = "#e0a63c"
OURO_CLARO = "#f6d27a"
BOCA_DENTRO = "#8a2f33"
LINGUA = "#ec8a80"
IRIS = "#2b1a14"
IRIS_LUZ = "#6a4330"

SW = 5


def _onda(x0, y0, x1, y1, amp, n):
    """Pontos de uma linha ondulada entre (x0,y0) e (x1,y1)."""
    pts = []
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t + amp * math.sin(t * n * math.pi)
        y = y0 + (y1 - y0) * t
        pts.append((x, y))
    return pts


def _olho(cx, cy, estado, lado):
    if estado == "fechados":
        return f'<path d="M{cx - 38},{cy - 2} Q{cx},{cy + 22} {cx + 38},{cy - 2}" stroke="{LINHA}" stroke-width="8" fill="none" stroke-linecap="round"/>'
    if estado == "felizes":
        return f'<path d="M{cx - 38},{cy + 8} Q{cx},{cy - 30} {cx + 38},{cy + 8}" stroke="{LINHA}" stroke-width="9" fill="none" stroke-linecap="round"/>'
    rx, ry = (36, 41) if estado == "surpresa" else (34, 38)
    flick = f'<path d="M{cx + lado * 40},{cy - 18} q{lado * 10},-4 {lado * 16},-14" stroke="{LINHA}" stroke-width="6" fill="none" stroke-linecap="round"/>'
    return f'''
    <ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{IRIS}"/>
    <ellipse cx="{cx}" cy="{cy + ry * 0.35}" rx="{rx * 0.72}" ry="{ry * 0.5}" fill="{IRIS_LUZ}" opacity="0.75"/>
    <ellipse cx="{cx}" cy="{cy + 2}" rx="{rx * 0.42}" ry="{ry * 0.45}" fill="#120b0b"/>
    <circle cx="{cx + 11}" cy="{cy - 13}" r="10" fill="#ffffff"/>
    <circle cx="{cx - 12}" cy="{cy + 14}" r="4.5" fill="#ffffff" opacity="0.9"/>
    <path d="M{cx - rx - 8},{cy - 4} Q{cx - 4},{cy - ry - 22} {cx + rx + 8},{cy - 8}" stroke="{LINHA}" stroke-width="9" fill="none" stroke-linecap="round"/>
    {flick}
    '''


def _boca(estado):
    cx, cy = 500, 618
    if estado == "fechada":
        return (f'<path d="M{cx - 34},{cy - 4} Q{cx},{cy + 24} {cx + 34},{cy - 4}" stroke="{LINHA}" stroke-width="6" fill="none" stroke-linecap="round"/>')
    if estado == "o":
        return (f'<ellipse cx="{cx}" cy="{cy + 8}" rx="18" ry="22" fill="{BOCA_DENTRO}" stroke="{LINHA}" stroke-width="5"/>'
                f'<ellipse cx="{cx}" cy="{cy + 20}" rx="10" ry="7" fill="{LINGUA}"/>')
    w, h = (30, 22) if estado == "media" else (46, 46)
    return f'''
    <clipPath id="boca{estado}"><path d="M{cx - w},{cy - 6} Q{cx},{cy + 2} {cx + w},{cy - 6} Q{cx + w * 0.85},{cy + h} {cx},{cy + h + 4} Q{cx - w * 0.85},{cy + h} {cx - w},{cy - 6} Z"/></clipPath>
    <path d="M{cx - w},{cy - 6} Q{cx},{cy + 2} {cx + w},{cy - 6} Q{cx + w * 0.85},{cy + h} {cx},{cy + h + 4} Q{cx - w * 0.85},{cy + h} {cx - w},{cy - 6} Z" fill="{BOCA_DENTRO}"/>
    <g clip-path="url(#boca{estado})">
      <rect x="{cx - w}" y="{cy - 10}" width="{2 * w}" height="{h * 0.32 + 6}" fill="#ffffff"/>
      <ellipse cx="{cx}" cy="{cy + h + 2}" rx="{w * 0.62}" ry="{h * 0.42}" fill="{LINGUA}"/>
    </g>
    <path d="M{cx - w},{cy - 6} Q{cx},{cy + 2} {cx + w},{cy - 6} Q{cx + w * 0.85},{cy + h} {cx},{cy + h + 4} Q{cx - w * 0.85},{cy + h} {cx - w},{cy - 6} Z" fill="none" stroke="{LINHA}" stroke-width="5" stroke-linejoin="round"/>
    '''


def _estampa():
    """Cruzinhas da blusa (como na referência)."""
    out = []
    for row in range(9):
        for col in range(12):
            x = 150 + col * 62 + (31 if row % 2 else 0)
            y = 880 + row * 44
            out.append(f'<path d="M{x - 7},{y} h14 M{x},{y - 7} v14" stroke="{ESTAMPA}" stroke-width="4" stroke-linecap="round"/>')
    return "".join(out)


def _brinco(x, y):
    return (f'<circle cx="{x}" cy="{y}" r="7" fill="{OURO}" stroke="{LINHA}" stroke-width="2.5"/>'
            f'<path d="M{x},{y + 7} q-9,14 0,24 q9,-10 0,-24 Z" fill="{OURO}" stroke="{LINHA}" stroke-width="2.5"/>'
            f'<circle cx="{x - 2}" cy="{y - 2}" r="2.2" fill="{OURO_CLARO}"/>')


def personagem_svg(boca="fechada", olhos="abertos", sobrancelha="normal", w=1000, h=1200):
    dy = -16 if sobrancelha == "alta" else 0
    corpo = "M190,1200 C200,1010 250,912 352,880 Q420,860 454,770 L500,872 L546,770 Q580,860 648,880 C750,912 800,1010 810,1200 Z"
    # cabelo de trás, ondulado e longo
    esq = _onda(236, 470, 226, 1070, 24, 7)
    dir_ = _onda(764, 470, 774, 1070, -24, 7)
    p = "M500,200 C322,200 232,330 236,470 "
    for (x, y) in esq[1:]:
        p += f"L{x:.1f},{y:.1f} "
    p += "C320,1120 680,1120 774,1070 "
    for (x, y) in reversed(dir_[:-1]):
        p += f"L{x:.1f},{y:.1f} "
    p += "C768,330 678,200 500,200 Z"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 1000 1200">
  <defs><clipPath id="corpo"><path d="{corpo}"/></clipPath></defs>
  <path d="{p}" fill="{CABELO}" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
  <!-- pescoço -->
  <path d="M452,650 L452,770 Q500,800 548,770 L548,650 Z" fill="{PELE_SOMBRA}" stroke="{LINHA}" stroke-width="{SW}"/>
  <!-- blusa creme com cruzinhas e decote em V -->
  <path d="{corpo}" fill="{BLUSA}" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
  <g clip-path="url(#corpo)">{_estampa()}
    <path d="M300,1200 C300,1060 292,990 276,940" stroke="{BLUSA_SOMBRA}" stroke-width="10" fill="none" stroke-linecap="round"/>
    <path d="M700,1200 C700,1060 708,990 724,940" stroke="{BLUSA_SOMBRA}" stroke-width="10" fill="none" stroke-linecap="round"/>
  </g>
  <path d="M454,770 L500,872 L546,770 Q500,800 454,770 Z" fill="{PELE_SOMBRA}" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
  <path d="M440,790 L500,900 L560,790" stroke="{BLUSA_SOMBRA}" stroke-width="6" fill="none"/>
  <!-- cordão preto + pingente dourado -->
  <path d="M458,772 Q470,880 500,950 Q530,880 542,772" stroke="#141014" stroke-width="5" fill="none"/>
  <ellipse cx="500" cy="978" rx="22" ry="30" fill="{OURO}" stroke="{LINHA}" stroke-width="4"/>
  <ellipse cx="500" cy="978" rx="12" ry="18" fill="none" stroke="{OURO_CLARO}" stroke-width="3.5"/>
  <!-- rosto redondinho -->
  <path d="M500,252 C642,252 712,352 712,480 C712,608 638,706 500,720 C362,706 288,608 288,480 C288,352 358,252 500,252 Z"
        fill="{PELE}" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
  <!-- bochechas -->
  <ellipse cx="380" cy="594" rx="40" ry="24" fill="{BLUSH}" opacity="0.5"/>
  <ellipse cx="620" cy="594" rx="40" ry="24" fill="{BLUSH}" opacity="0.5"/>
  <!-- olhos grandes -->
  {_olho(408, 516, olhos, -1)}
  {_olho(592, 516, olhos, 1)}
  <!-- sobrancelhas finas -->
  <path d="M372,{432 + dy} Q412,{410 + dy} 452,{424 + dy}" stroke="{CABELO}" stroke-width="8" fill="none" stroke-linecap="round"/>
  <path d="M548,{424 + dy} Q588,{410 + dy} 628,{432 + dy}" stroke="{CABELO}" stroke-width="8" fill="none" stroke-linecap="round"/>
  <!-- nariz -->
  <path d="M496,566 Q502,574 508,566" stroke="{LINHA}" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.7"/>
  {_boca(boca)}
  <!-- cabelo da frente: risca no meio, cortinas onduladas emoldurando o rosto -->
  <path d="M500,252 C428,254 356,292 326,372 C300,440 292,520 296,600 C290,660 268,704 274,764 C280,824 256,866 262,926 C268,986 292,1020 326,1040 C342,1008 330,968 342,926 C354,876 334,836 344,786 C352,736 326,694 332,644 C338,566 326,476 356,396 C380,330 438,282 500,266 Z"
        fill="{CABELO}" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
  <path d="M500,252 C572,254 644,292 674,372 C700,440 708,520 704,600 C710,660 732,704 726,764 C720,824 744,866 738,926 C732,986 708,1020 674,1040 C658,1008 670,968 658,926 C646,876 666,836 656,786 C648,736 674,694 668,644 C662,566 674,476 644,396 C620,330 562,282 500,266 Z"
        fill="{CABELO}" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
  <!-- fios ondulados e brilho -->
  <path d="M470,268 C416,294 374,346 352,420" stroke="{CABELO_LUZ}" stroke-width="7" fill="none" stroke-linecap="round"/>
  <path d="M530,268 C584,294 626,346 648,420" stroke="{CABELO_LUZ}" stroke-width="7" fill="none" stroke-linecap="round"/>
  <path d="M310,660 C292,710 312,750 300,800 C290,850 312,890 300,950" stroke="{CABELO_LUZ}" stroke-width="5" fill="none" stroke-linecap="round"/>
  <path d="M690,660 C708,710 688,750 700,800 C710,850 688,890 700,950" stroke="{CABELO_LUZ}" stroke-width="5" fill="none" stroke-linecap="round"/>
  <path d="M258,600 C240,660 262,720 248,790 C236,850 258,910 250,980" stroke="{CABELO_LUZ}" stroke-width="5" fill="none" stroke-linecap="round"/>
  <path d="M742,600 C760,660 738,720 752,790 C764,850 742,910 750,980" stroke="{CABELO_LUZ}" stroke-width="5" fill="none" stroke-linecap="round"/>
  <!-- brincos dourados -->
  {_brinco(312, 640)}
  {_brinco(688, 640)}
</svg>'''


if __name__ == "__main__":
    import sys
    import cairosvg
    cairosvg.svg2png(bytestring=personagem_svg().encode(), write_to=sys.argv[1], output_width=600)
