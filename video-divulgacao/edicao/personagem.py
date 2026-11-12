"""Personagem da professora AOI em SVG (estilo flat, traço fino, paleta da escola).

personagem_svg(boca, olhos, sobrancelha) -> str
  boca:        "fechada" | "media" | "aberta" | "o"
  olhos:       "abertos" | "fechados" | "surpresa"
  sobrancelha: "normal" | "alta"
"""

LINHA = "#3a2c2a"
PELE = "#f4d3bd"
PELE_SOMBRA = "#e8bba3"
CABELO = "#1e1b22"
CABELO_BRILHO = "#3a3646"
BLUSA = "#4f8370"       # verde AOI
BLUSA_SOMBRA = "#43705f"
CREME = "#fef7f1"
CORAL = "#f0876e"
VERMELHO = "#c94e48"
LARANJA = "#e89232"
OURO = "#d9a441"
LABIO = "#d4766b"
BOCA_DENTRO = "#7b2f30"
LINGUA = "#e2867c"

SW = 5  # espessura do traço


def _flor(cx, cy, r, rot=0):
    """Flor de ume da marca (5 pétalas vermelhas + miolo laranja + raios)."""
    import math
    petals = []
    for i in range(5):
        a = math.radians(rot + i * 72 - 90)
        px, py = cx + math.cos(a) * r * 0.55, cy + math.sin(a) * r * 0.55
        petals.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r * 0.5:.1f}" fill="{VERMELHO}"/>')
    rays = []
    for i in range(5):
        a = math.radians(rot + i * 72 - 54)
        x2, y2 = cx + math.cos(a) * r * 0.95, cy + math.sin(a) * r * 0.95
        rays.append(f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{LARANJA}" stroke-width="2.2" stroke-linecap="round"/>')
    return "".join(petals) + "".join(rays) + f'<circle cx="{cx}" cy="{cy}" r="{r * 0.2:.1f}" fill="{LARANJA}"/>'


def _olho(cx, cy, estado, lado):
    # lado: -1 esquerdo (do observador), +1 direito
    E = 48  # meia-largura do olho
    wing = f'<path d="M{cx + lado * (E - 2)},{cy - 6} q{lado * 12},-6 {lado * 20},-16" stroke="{LINHA}" stroke-width="{SW}" fill="none" stroke-linecap="round"/>'
    if estado == "fechados":
        return (f'<path d="M{cx - E},{cy - 2} Q{cx},{cy + 24} {cx + E},{cy - 2}" stroke="{LINHA}" stroke-width="{SW + 2}" fill="none" stroke-linecap="round"/>'
                + wing)
    abre = 34 if estado == "surpresa" else 27
    iris_r = 25 if estado == "surpresa" else 24
    clip = f"olho{lado}{estado}"
    forma = f"M{cx - E},{cy + 2} Q{cx - 6},{cy - abre * 1.9} {cx + E},{cy} Q{cx + 4},{cy + abre * 0.8} {cx - E},{cy + 2} Z"
    return f'''
    <clipPath id="{clip}"><path d="{forma}"/></clipPath>
    <path d="{forma}" fill="#ffffff"/>
    <g clip-path="url(#{clip})">
      <circle cx="{cx + lado * 2}" cy="{cy - 2}" r="{iris_r}" fill="#5a3d2b"/>
      <circle cx="{cx + lado * 2}" cy="{cy - 2}" r="{iris_r * 0.78}" fill="#3b261b"/>
      <circle cx="{cx + lado * 2}" cy="{cy - 2}" r="{iris_r * 0.45}" fill="#160f0f"/>
      <circle cx="{cx + lado * 2 + 9}" cy="{cy - 11}" r="7.5" fill="#ffffff"/>
      <circle cx="{cx + lado * 2 - 8}" cy="{cy + 7}" r="3.2" fill="#ffffff" opacity="0.85"/>
    </g>
    <path d="M{cx - E - 3},{cy + 4} Q{cx - 6},{cy - abre * 1.98} {cx + E + 2},{cy - 1}" stroke="{LINHA}" stroke-width="{SW + 3}" fill="none" stroke-linecap="round"/>
    {wing}
    <path d="M{cx - E * 0.7},{cy + abre * 0.55} Q{cx},{cy + abre * 0.9} {cx + E * 0.65},{cy + abre * 0.5}" stroke="{LINHA}" stroke-width="2.6" fill="none" stroke-linecap="round" opacity="0.5"/>
    '''


def _boca(estado):
    cx, cy = 500, 618
    if estado == "fechada":
        return (f'<path d="M{cx - 46},{cy - 6} Q{cx},{cy + 26} {cx + 46},{cy - 6}" stroke="{LINHA}" stroke-width="{SW}" fill="none" stroke-linecap="round"/>'
                f'<path d="M{cx - 22},{cy + 14} Q{cx},{cy + 20} {cx + 22},{cy + 14}" stroke="{LABIO}" stroke-width="5" fill="none" stroke-linecap="round" opacity="0.7"/>')
    if estado == "o":
        return (f'<ellipse cx="{cx}" cy="{cy + 6}" rx="20" ry="24" fill="{BOCA_DENTRO}" stroke="{LINHA}" stroke-width="{SW}"/>'
                f'<ellipse cx="{cx}" cy="{cy + 20}" rx="11" ry="7" fill="{LINGUA}"/>')
    h = 18 if estado == "media" else 34
    w = 44 if estado == "media" else 48
    return f'''
    <path d="M{cx - w},{cy - 6} Q{cx},{cy + 4} {cx + w},{cy - 6} Q{cx + w * 0.6},{cy + h + 14} {cx},{cy + h + 16} Q{cx - w * 0.6},{cy + h + 14} {cx - w},{cy - 6} Z" fill="{BOCA_DENTRO}" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
    <path d="M{cx - w * 0.8},{cy - 3} Q{cx},{cy + 6} {cx + w * 0.8},{cy - 3} L{cx + w * 0.7},{cy + 4} Q{cx},{cy + 12} {cx - w * 0.7},{cy + 4} Z" fill="#ffffff"/>
    <ellipse cx="{cx}" cy="{cy + h + 6}" rx="{w * 0.45}" ry="{h * 0.32 + 3}" fill="{LINGUA}"/>
    '''


def personagem_svg(boca="fechada", olhos="abertos", sobrancelha="normal", w=1000, h=1200):
    dy = -14 if sobrancelha == "alta" else 0
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 1000 1200">
  <!-- cabelo de trás -->
  <path d="M318,330 C300,470 292,640 292,770 C292,812 330,840 376,836 C400,834 416,826 424,812 L420,600 L600,600 L600,800 C612,826 640,836 666,830 C700,822 712,796 708,770 C704,640 698,470 684,330 C640,220 360,220 318,330 Z"
        fill="{CABELO}" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
  <path d="M640,640 C646,700 652,760 664,812" stroke="{CABELO_BRILHO}" stroke-width="5" fill="none" stroke-linecap="round"/>
  <!-- pescoço -->
  <path d="M440,640 L440,760 Q500,792 560,760 L560,640 Z" fill="{PELE_SOMBRA}" stroke="{LINHA}" stroke-width="{SW}"/>
  <!-- tronco / blusa -->
  <path d="M130,1200 C140,980 210,880 330,850 Q400,832 446,760 Q500,812 554,760 Q600,832 670,850 C790,880 860,980 870,1200 Z"
        fill="{BLUSA}" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
  <path d="M446,760 Q500,880 554,760 Q500,812 446,760 Z" fill="{PELE_SOMBRA}" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
  <path d="M300,1200 C300,1060 290,980 270,930" stroke="{BLUSA_SOMBRA}" stroke-width="8" fill="none" stroke-linecap="round"/>
  <path d="M700,1200 C700,1060 710,980 730,930" stroke="{BLUSA_SOMBRA}" stroke-width="8" fill="none" stroke-linecap="round"/>
  <!-- estampa de bolinhas creme -->
  <g fill="{CREME}" opacity="0.85">
    <circle cx="250" cy="980" r="5"/><circle cx="320" cy="1040" r="5"/><circle cx="210" cy="1100" r="5"/><circle cx="380" cy="960" r="5"/>
    <circle cx="420" cy="1080" r="5"/><circle cx="560" cy="1000" r="5"/><circle cx="620" cy="1090" r="5"/><circle cx="700" cy="990" r="5"/>
    <circle cx="760" cy="1070" r="5"/><circle cx="480" cy="1150" r="5"/><circle cx="660" cy="1170" r="5"/><circle cx="300" cy="1160" r="5"/>
    <circle cx="790" cy="1160" r="5"/><circle cx="190" cy="1020" r="5"/>
  </g>
  <!-- colar: cordão + pingente oval dourado -->
  <path d="M452,770 Q470,900 500,960 Q530,900 548,770" stroke="#4a3328" stroke-width="4" fill="none"/>
  <ellipse cx="500" cy="985" rx="20" ry="28" fill="{OURO}" stroke="{LINHA}" stroke-width="4"/>
  <ellipse cx="500" cy="985" rx="11" ry="17" fill="none" stroke="#f3d48a" stroke-width="3"/>
  <!-- orelha direita (do observador) com argola -->
  <path d="M660,470 C690,456 700,500 690,526 C684,542 670,548 658,540" fill="{PELE}" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
  <circle cx="684" cy="572" r="26" fill="none" stroke="{OURO}" stroke-width="7"/>
  <!-- rosto -->
  <path d="M500,262 C610,262 668,340 668,450 C668,560 640,640 590,676 C560,698 530,708 500,708 C470,708 440,698 410,676 C360,640 332,560 332,450 C332,340 390,262 500,262 Z"
        fill="{PELE}" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
  <path d="M360,430 C400,400 440,380 480,372 C440,400 405,430 380,470 Z" fill="{PELE_SOMBRA}" opacity="0.6"/>
  <!-- bochechas -->
  <ellipse cx="400" cy="575" rx="44" ry="24" fill="{CORAL}" opacity="0.32"/>
  <ellipse cx="600" cy="575" rx="44" ry="24" fill="{CORAL}" opacity="0.32"/>
  <!-- olhos -->
  {_olho(422, 494, olhos, -1)}
  {_olho(580, 494, olhos, 1)}
  <!-- sobrancelhas -->
  <path d="M370,{424 + dy} Q418,{396 + dy} 468,{414 + dy}" stroke="{CABELO}" stroke-width="10" fill="none" stroke-linecap="round"/>
  <path d="M534,{414 + dy} Q584,{396 + dy} 632,{424 + dy}" stroke="{CABELO}" stroke-width="10" fill="none" stroke-linecap="round"/>
  <!-- nariz -->
  <path d="M506,520 Q514,556 498,566 Q490,570 484,564" stroke="{LINHA}" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.75"/>
  <!-- boca -->
  {_boca(boca)}
  <!-- franja: risca à direita, mecha varrendo para a esquerda -->
  <path d="M580,250 C470,236 370,280 336,370 C322,410 318,460 326,520 C304,600 298,690 302,780 C304,820 330,846 366,842 C380,840 390,832 394,822 C374,800 366,760 364,720 C360,640 364,580 372,530 C390,468 428,420 474,392 C522,364 566,340 596,300 C610,330 640,360 668,380 C672,330 650,276 580,250 Z"
        fill="{CABELO}" stroke="{LINHA}" stroke-width="{SW}" stroke-linejoin="round"/>
  <path d="M470,300 C430,330 392,380 374,440" stroke="{CABELO_BRILHO}" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.8"/>
  <path d="M352,600 C346,670 348,740 360,800" stroke="{CABELO_BRILHO}" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.8"/>
  <!-- brilhos do cabelo -->
  <path d="M410,300 C450,280 500,276 540,282" stroke="{CABELO_BRILHO}" stroke-width="9" fill="none" stroke-linecap="round"/>
  <path d="M338,560 C334,630 334,700 338,770" stroke="{CABELO_BRILHO}" stroke-width="7" fill="none" stroke-linecap="round"/>
  <!-- presilha de flor de ume -->
  <g>{_flor(632, 318, 34, rot=12)}</g>
</svg>'''


if __name__ == "__main__":
    import sys
    import cairosvg
    out = sys.argv[1]
    cairosvg.svg2png(bytestring=personagem_svg().encode(), write_to=out, output_width=600)
