"""Ilustrações flat em SVG na paleta AOI (sem contorno pesado, formas arredondadas)."""
import io
import cairosvg
from PIL import Image

CREME = "#fef7f1"
PESSEGO = "#fae8d4"
SALVIA = "#c6dac8"
VERDE = "#4f8370"
VERDE_ESC = "#3e6b5a"
LARANJA = "#e89232"
CORAL = "#f0876e"
VERMELHO = "#c94e48"
TEXTO = "#2a2a28"
PELE = "#f1c7a6"
PELE2 = "#d9a27e"
MADEIRA = "#7a4a2e"


def png(svg, width):
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(), output_width=width))).convert("RGBA")


def _wrap(body, vb="0 0 600 600"):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">{body}</svg>'


def japao():
    """Sol vermelho + Monte Fuji + nuvens."""
    return _wrap(f'''
    <circle cx="300" cy="250" r="150" fill="{VERMELHO}"/>
    <path d="M40,560 L250,250 Q300,205 350,250 L560,560 Z" fill="{SALVIA}"/>
    <path d="M250,250 Q300,205 350,250 L392,312 L362,298 L336,326 L306,296 L278,330 L246,300 L208,314 Z" fill="{CREME}"/>
    <path d="M40,560 L250,250 L232,290 L180,420 L120,560 Z" fill="#b3cbb6"/>
    <g fill="none" stroke="{CREME}" stroke-width="12" stroke-linecap="round">
      <path d="M20,90 h70 a26,26 0 0 1 26,-26 a26,26 0 0 1 26,26 h40"/>
      <path d="M440,60 h40 a22,22 0 0 1 22,-22 a22,22 0 0 1 22,22 h60"/>
    </g>''')


def ramen_mao():
    """Mão levantada chamando + tigela de ramen."""
    return _wrap(f'''
    <ellipse cx="320" cy="545" rx="210" ry="22" fill="#000" opacity="0.08"/>
    <path d="M120,360 h400 a200,170 0 0 1 -400,0 Z" fill="{VERMELHO}"/>
    <path d="M140,410 h360" stroke="{CREME}" stroke-width="16" stroke-dasharray="4 30" stroke-linecap="round"/>
    <rect x="250" y="520" width="140" height="24" rx="12" fill="#9e3a35"/>
    <ellipse cx="320" cy="360" rx="200" ry="38" fill="#f6d27a"/>
    <path d="M170,360 q30,-24 60,0 t60,0 t60,0 t60,0 t60,0" stroke="#e8b44e" stroke-width="10" fill="none"/>
    <circle cx="390" cy="348" r="30" fill="{CREME}"/><circle cx="390" cy="348" r="14" fill="{LARANJA}"/>
    <path d="M240,340 l40,-10 l-6,24 Z" fill="{CORAL}"/>
    <rect x="300" y="150" width="14" height="230" rx="7" fill="{MADEIRA}" transform="rotate(18 307 265)"/>
    <rect x="330" y="150" width="14" height="230" rx="7" fill="{MADEIRA}" transform="rotate(26 337 265)"/>
    <g stroke="{SALVIA}" stroke-width="12" fill="none" stroke-linecap="round">
      <path d="M220,300 q-20,-30 0,-60 t0,-60"/><path d="M420,300 q-20,-30 0,-60 t0,-60"/>
    </g>
    <!-- mão chamando -->
    <g transform="translate(70,40) rotate(-12 60 160)">
      <rect x="18" y="20" width="26" height="90" rx="13" fill="{PELE}"/>
      <rect x="48" y="4" width="26" height="104" rx="13" fill="{PELE}"/>
      <rect x="78" y="10" width="26" height="98" rx="13" fill="{PELE}"/>
      <rect x="106" y="30" width="24" height="80" rx="12" fill="{PELE}"/>
      <path d="M126,120 q40,-30 52,-6 q-14,30 -50,50 Z" fill="{PELE}"/>
      <rect x="14" y="80" width="120" height="110" rx="46" fill="{PELE}"/>
      <rect x="34" y="176" width="80" height="120" rx="20" fill="{VERDE}"/>
    </g>
    <g stroke="{LARANJA}" stroke-width="10" stroke-linecap="round">
      <path d="M40,70 l-26,-20"/><path d="M30,120 l-32,0"/><path d="M210,40 l22,-24"/>
    </g>''')


def pessoa(cx, cy, cor, inclina=0, rosto=True):
    return f'''<g transform="rotate({inclina} {cx} {cy + 160})">
      <rect x="{cx - 52}" y="{cy + 50}" width="104" height="170" rx="46" fill="{cor}"/>
      <circle cx="{cx}" cy="{cy}" r="48" fill="{PELE}"/>
      <path d="M{cx - 48},{cy - 4} a48,48 0 0 1 96,0 q-30,-26 -96,0 Z" fill="{TEXTO}"/>
      {f'<circle cx="{cx - 16}" cy="{cy + 6}" r="5" fill="{TEXTO}"/><circle cx="{cx + 16}" cy="{cy + 6}" r="5" fill="{TEXTO}"/>' if rosto else ''}
    </g>'''


def esbarrao():
    """Duas pessoas se esbarrando, uma se curvando pedindo desculpa."""
    return _wrap(f'''
    <ellipse cx="300" cy="560" rx="230" ry="20" fill="#000" opacity="0.08"/>
    {pessoa(190, 300, VERDE, inclina=-24)}
    {pessoa(420, 300, CORAL, inclina=8)}
    <path d="M300,170 l18,40 l44,-12 l-26,36 l34,30 l-44,4 l-4,44 l-26,-34 l-38,22 l14,-42 l-40,-20 l44,-8 Z" fill="{LARANJA}"/>
    <path d="M128,226 q-14,22 0,34 q14,-12 0,-34 Z" fill="#8fc1e8"/>
    <rect x="455" y="380" width="70" height="56" rx="8" fill="{PESSEGO}" stroke="{MADEIRA}" stroke-width="6" transform="rotate(14 490 408)"/>
    ''')


def porta():
    """Porta aberta, uma pessoa segura, outra passa; corações."""
    return _wrap(f'''
    <ellipse cx="300" cy="565" rx="250" ry="18" fill="#000" opacity="0.08"/>
    <rect x="200" y="80" width="230" height="480" rx="10" fill="{VERDE_ESC}"/>
    <rect x="216" y="96" width="198" height="464" fill="#fff3e3"/>
    <path d="M414,96 L520,140 L520,520 L414,560 Z" fill="{VERDE}"/>
    <circle cx="500" cy="340" r="10" fill="{LARANJA}"/>
    {pessoa(500, 250, CORAL, inclina=0)}
    {pessoa(300, 260, VERDE, inclina=-6)}
    <g fill="{VERMELHO}">
      <path d="M110,190 c0,-26 36,-26 36,0 c0,-26 36,-26 36,0 c0,26 -36,44 -36,56 c0,-12 -36,-30 -36,-56 Z"/>
      <path d="M60,300 c0,-17 24,-17 24,0 c0,-17 24,-17 24,0 c0,17 -24,29 -24,37 c0,-8 -24,-20 -24,-37 Z" opacity="0.8"/>
    </g>''')


def balao(texto_svg_w=420):
    """Balão de fala vazio (o texto é escrito por cima)."""
    w = texto_svg_w
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w + 40} 210"><path d="M30,20 h{w - 20} a30,30 0 0 1 30,30 v80 a30,30 0 0 1 -30,30 h-{w - 140} l-50,44 l6,-44 h-{70} a30,30 0 0 1 -30,-30 v-80 a30,30 0 0 1 30,-30 Z" fill="{CREME}" stroke="{TEXTO}" stroke-width="7"/></svg>'


def cardapio():
    """Cardápio japonês (sem preços) com 3 pratos."""
    return _wrap(f'''
    <rect x="70" y="40" width="460" height="520" rx="26" fill="#000" opacity="0.07" transform="translate(10,12)"/>
    <rect x="70" y="40" width="460" height="520" rx="26" fill="{CREME}" stroke="{MADEIRA}" stroke-width="10"/>
    <rect x="70" y="40" width="460" height="96" rx="26" fill="{VERMELHO}"/>
    <rect x="70" y="100" width="460" height="36" fill="{VERMELHO}"/>
    <g transform="translate(0,0)">
      <path d="M110,200 h90 a45,40 0 0 1 -90,0 Z" fill="{VERMELHO}"/><ellipse cx="155" cy="200" rx="45" ry="9" fill="#f6d27a"/>
      <rect x="230" y="186" width="250" height="16" rx="8" fill="{SALVIA}"/><rect x="230" y="216" width="170" height="14" rx="7" fill="{PESSEGO}"/>
      <path d="M155,300 l42,70 h-84 Z" fill="{CREME}" stroke="{TEXTO}" stroke-width="6" stroke-linejoin="round"/><rect x="128" y="338" width="54" height="32" fill="{TEXTO}"/>
      <rect x="230" y="318" width="250" height="16" rx="8" fill="{SALVIA}"/><rect x="230" y="348" width="190" height="14" rx="7" fill="{PESSEGO}"/>
      <rect x="152" y="420" width="6" height="110" rx="3" fill="{MADEIRA}"/>
      <circle cx="155" cy="440" r="20" fill="{CORAL}"/><circle cx="155" cy="476" r="20" fill="{CREME}" stroke="{TEXTO}" stroke-width="4"/><circle cx="155" cy="512" r="20" fill="{SALVIA}"/>
      <rect x="230" y="456" width="250" height="16" rx="8" fill="{SALVIA}"/><rect x="230" y="486" width="150" height="14" rx="7" fill="{PESSEGO}"/>
    </g>''')


def dedo():
    """Mão com indicador apontando para a esquerda."""
    return _wrap(f'''
    <rect x="70" y="40" width="150" height="34" rx="17" fill="{PELE}"/>
    <rect x="150" y="30" width="120" height="110" rx="44" fill="{PELE}"/>
    <rect x="160" y="90" width="80" height="26" rx="13" fill="{PELE2}" opacity="0.5"/>
    <rect x="250" y="44" width="90" height="84" rx="16" fill="{VERDE}"/>''', vb="0 0 360 170")


def sacola():
    return _wrap(f'''
    <path d="M180,180 q0,-110 120,-110 q120,0 120,110" fill="none" stroke="{VERDE_ESC}" stroke-width="26" stroke-linecap="round"/>
    <path d="M110,180 h380 l-30,360 h-320 Z" fill="{SALVIA}"/>
    <path d="M110,180 h380 l-6,70 h-368 Z" fill="#b3cbb6"/>
    <circle cx="300" cy="380" r="56" fill="{CREME}"/><circle cx="300" cy="380" r="30" fill="{VERMELHO}"/>''')


def itens_na_mao():
    """Compras equilibradas nos braços, sem sacola."""
    return _wrap(f'''
    <ellipse cx="300" cy="570" rx="220" ry="18" fill="#000" opacity="0.08"/>
    <rect x="160" y="300" width="280" height="190" rx="18" fill="{LARANJA}"/>
    <rect x="160" y="300" width="280" height="44" rx="18" fill="#cf7d22"/>
    <rect x="370" y="120" width="70" height="190" rx="22" fill="#8fc1e8"/><rect x="384" y="86" width="42" height="44" rx="10" fill="{VERMELHO}"/>
    <rect x="374" y="190" width="62" height="56" fill="{CREME}"/>
    <path d="M250,170 l70,120 h-140 Z" fill="{CREME}" stroke="{TEXTO}" stroke-width="7" stroke-linejoin="round"/><rect x="214" y="246" width="72" height="44" fill="{TEXTO}"/>
    <circle cx="130" cy="250" r="44" fill="{VERMELHO}"/><path d="M130,206 q6,-26 24,-30" stroke="{MADEIRA}" stroke-width="8" fill="none"/>
    <path d="M150,212 q24,-18 40,-4 q-20,16 -40,4 Z" fill="{VERDE}"/>
    <rect x="96" y="440" width="150" height="60" rx="30" fill="{PELE}"/><rect x="354" y="440" width="150" height="60" rx="30" fill="{PELE}"/>
    <g fill="#8fc1e8"><path d="M520,170 q-16,26 0,40 q16,-14 0,-40 Z"/><path d="M80,120 q-12,20 0,30 q12,-10 0,-30 Z"/></g>
    <g stroke="{LARANJA}" stroke-width="9" stroke-linecap="round"><path d="M70,330 l-30,-8"/><path d="M530,320 l30,-10"/></g>''')


def marcador():
    return _wrap(f'''<path d="M170,60 h260 a30,30 0 0 1 30,30 v450 l-160,-110 l-160,110 v-450 a30,30 0 0 1 30,-30 Z" fill="{OURO_IL}"/>
    <path d="M300,170 l26,54 l58,8 l-42,40 l10,58 l-52,-28 l-52,28 l10,-58 l-42,-40 l58,-8 Z" fill="{CREME}"/>''')


def aviao():
    return _wrap(f'''<g transform="rotate(-20 300 300)">
    <path d="M60,300 q0,-40 60,-40 h340 q90,0 90,40 q0,40 -90,40 h-340 q-60,0 -60,-40 Z" fill="{CREME}"/>
    <path d="M300,262 l-90,-170 h60 l130,170 Z" fill="{CREME}"/><path d="M300,338 l-90,170 h60 l130,-170 Z" fill="#e9dccd"/>
    <path d="M100,262 l-40,-90 h44 l60,90 Z" fill="{CREME}"/>
    <g fill="{VERMELHO}"><circle cx="380" cy="300" r="12"/><circle cx="330" cy="300" r="12"/><circle cx="280" cy="300" r="12"/></g></g>''')


OURO_IL = "#f6d27a"
