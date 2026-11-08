#!/usr/bin/env python3
"""Gera os banners e os selos de ferramentas em assets/.

Os selos ficam no repositório para não depender de serviço externo: edite SELOS
e rode o script de novo.

O ruído vira sinal: glifos hexadecimais caem ao fundo e pulsos de luz percorrem
a placa de circuito do portfólio. O texto sai em curvas, porque um SVG aberto
em <img> não carrega fonte externa. Cores, fontes e placa vêm do portfólio,
então nada disso é copiado para cá.

Dependências: pip install fonttools brotli uharfbuzz
Uso: python scripts/gerar_banner.py [caminho do portfólio]
"""
import io
import json
import random
import re
import sys
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

RAIZ = Path(__file__).resolve().parent.parent
PORTFOLIO = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ.parent / "portfolio"

NOME = ("Warley Ferraz", "Almeida")
CARGO = "Analista de Redes N2 em NOC"
DOMINIO = "warley.ferzion.com.br"
DESCRICAO = f"{' '.join(NOME)}, {CARGO}"

LARGURA, ALTURA = 1280, 400
PASSO_COLUNA, PASSO_LINHA, CORPO_GLIFO = 26, 20, 16
GLIFOS = "0123456789ABCDEF"

# Tokens de portfolio/docs/05-design-system.md.
TEMAS = {
    "rubro": {
        "fundo": "#050203", "tinta": "#F2E7E5", "tinta2": "#B49896", "sinal": "#FF3646",
        "forma": "#C40F2C", "chuva": "#E01E30", "cabeca": "#FFE2DC",
        "chuva_texto": 0.16, "chuva_cena": 0.5, "placa": 0.55,
    },
    "claro": {
        "fundo": "#F5F0EF", "tinta": "#14080A", "tinta2": "#5A3F41", "sinal": "#A0001A",
        "forma": "#C40F2C", "chuva": "#14080A", "cabeca": "#A0001A",
        "chuva_texto": 0.05, "chuva_cena": 0.14, "placa": 0.5,
    },
}


# O tom indica a origem do conhecimento, do trabalho ao estudo.
SELOS = {
    "#C40F2C": ["GPON/FTTH", "ONU e ONT", "OLTs", "Zabbix", "Grafana", "Plataformas ACS", "IXC Provedor"],
    "#5E0712": [
        "Ubuntu Server", "Bash", "systemd", "Nginx", "Docker Compose", "UFW", "Let's Encrypt",
        "PostgreSQL", "GitHub Actions", "Python", "Django", "Celery", "Redis",
    ],
    "#1C0A0E": ["Kali Linux", "Nmap", "Wireshark", "Burp Suite", "Hack The Box", "TryHackMe", "PortSwigger Academy"],
}


def numero(v, casas=1):
    return f"{v:.{casas}f}".rstrip("0").rstrip(".")


class Fonte:
    def __init__(self, arquivo, **eixos):
        original = TTFont(arquivo)
        fixos = {a.axisTag: eixos.get(a.axisTag, a.defaultValue) for a in original["fvar"].axes}
        self.tt = instancer.instantiateVariableFont(original, fixos)
        self.tt.flavor = None
        dados = io.BytesIO()
        self.tt.save(dados)
        self.hb = hb.Font(hb.Face(dados.getvalue()))
        self.glifos = self.tt.getGlyphSet()
        self.ordem = self.tt.getGlyphOrder()
        self.emq = self.tt["head"].unitsPerEm

    def curva(self, texto, corpo, x, y, tracking=0.0, casas=1):
        """Devolve o atributo d do texto, com kerning, e a largura final."""
        buf = hb.Buffer()
        buf.add_str(texto)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {"calt": False, "liga": False})
        escala = corpo / self.emq
        caneta = SVGPathPen(self.glifos, ntos=lambda v: numero(v, casas))
        cx = x
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            if info.codepoint == 0:
                raise ValueError(f"A fonte não tem um dos caracteres de {texto!r}")
            transforma = TransformPen(caneta, (escala, 0, 0, -escala, cx + pos.x_offset * escala, y - pos.y_offset * escala))
            self.glifos[self.ordem[info.codepoint]].draw(transforma)
            cx += pos.x_advance * escala + tracking * corpo
        return caneta.getCommands(), cx - x


def ler_placa():
    fonte = (PORTFOLIO / "src/componentes/graficos/trilhas.gerado.ts").read_text(encoding="utf-8")
    return json.loads(re.search(r"TRILHAS: Record<string, Placa> = (\{.*\});", fonte, re.S).group(1))["inicio"]


def chuva(tema, glifos_mono):
    sorteio = random.Random(1110)
    colunas = []
    for i in range(LARGURA // PASSO_COLUNA + 1):
        x = i * PASSO_COLUNA + 6
        # A chuva respeita um teto de luz atrás do texto e sobe na área da cena.
        ramo = min(1.0, max(0.0, (x - 620) / 320))
        opacidade = tema["chuva_texto"] + (tema["chuva_cena"] - tema["chuva_texto"]) * ramo
        comprimento = sorteio.randint(9, 16)
        usos = []
        for n in range(comprimento):
            glifo = sorteio.randrange(len(GLIFOS))
            cor = f' fill="{tema["cabeca"]}"' if n == 0 else ""
            alfa = "" if n == 0 else f' opacity="{1 - n / comprimento:.2f}"'
            usos.append(f'<use href="#g{glifo}" y="{-n * PASSO_LINHA}"{cor}{alfa}/>')
        duracao = sorteio.uniform(7, 15)
        atraso = -sorteio.uniform(0, duracao)
        repouso = sorteio.randint(40, ALTURA + 120)
        colunas.append(
            f'<g transform="translate({x})" opacity="{opacidade:.2f}">'
            f'<g class="c" style="--d:{duracao:.1f}s;--a:{atraso:.1f}s;--y:{repouso}px">{"".join(usos)}</g></g>'
        )
    return "".join(colunas)


def placa_svg(tema, p):
    corpos = "".join(f'<rect x="{x}" y="{y}" width="{w}" height="{h}"/>' for x, y, w, h in p["corpos"])
    pads = "".join(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="currentColor" stroke="none"/>' for x, y, w, h in p["pads"])
    vias = "".join(f'<circle cx="{x}" cy="{y}" r="3"/>' for x, y in p["vias"])
    trechos = ["M" + t for t in p["d"].split("M") if t]
    # Pulsos só em trilhas longas e dentro do recorte do banner.
    visiveis = [t for t in trechos if len(t) > 24 and 80 < int(re.search(r"M\d+ (\d+)", t).group(1)) < 600]
    sorteio = random.Random(27)
    pulsos = []
    for t in sorteio.sample(visiveis, min(9, len(visiveis))):
        duracao = sorteio.uniform(3.2, 6.5)
        atraso = -sorteio.uniform(0, duracao)
        pulsos.append(f'<path class="p" d="{t}" pathLength="100" style="--d:{duracao:.1f}s;--a:{atraso:.1f}s"/>')
    return (
        f'<g transform="translate(380 -70) scale(.75)" fill="none" stroke-linecap="round" stroke-linejoin="round">'
        f'<g mask="url(#m)" color="{tema["forma"]}" stroke="currentColor" stroke-width="1.5" opacity="{tema["placa"]}">'
        f'<path d="{p["d"]}"/>{corpos}{pads}{vias}</g>'
        f'<g stroke="{tema["sinal"]}" stroke-width="2.4">{"".join(pulsos)}</g></g>'
    )


def banner(nome_tema, mona_titulo, mona_texto, mono, placa_dados):
    tema = TEMAS[nome_tema]
    glifos = []
    for i, letra in enumerate(GLIFOS):
        d, largura = mono.curva(letra, CORPO_GLIFO, 0, 0)
        glifos.append(f'<path id="g{i}" d="{d}"/>')
    dominio, _ = mono.curva(DOMINIO, 21, 64, 84, tracking=0.02)
    linha1, _ = mona_titulo.curva(NOME[0], 80, 62, 206, tracking=-0.02)
    linha2, _ = mona_titulo.curva(NOME[1], 80, 62, 284, tracking=-0.02)
    cargo, _ = mona_texto.curva(CARGO, 29, 64, 342)
    estilo = (
        ".c{transform:translateY(var(--y))}.p{stroke-dasharray:7 93;stroke-dashoffset:100;opacity:0}"
        "@media (prefers-reduced-motion:no-preference){"
        ".c{animation:cair var(--d) linear var(--a) infinite}"
        ".p{opacity:1;animation:luz var(--d) linear var(--a) infinite}}"
        f"@keyframes cair{{from{{transform:translateY(-20px)}}to{{transform:translateY({ALTURA + 340}px)}}}}"
        "@keyframes luz{from{stroke-dashoffset:100}to{stroke-dashoffset:-7}}"
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {LARGURA} {ALTURA}" role="img" aria-label="{DESCRICAO}">'
        f"<title>{DESCRICAO}</title><style>{estilo}</style><defs>{''.join(glifos)}"
        '<linearGradient id="f" x1="0" x2="1" y1="0" y2="0">'
        '<stop offset=".5" stop-color="#000"/><stop offset=".72" stop-color="#fff"/></linearGradient>'
        '<mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="1200" height="800">'
        '<rect width="1200" height="800" fill="url(#f)"/></mask></defs>'
        f'<rect width="{LARGURA}" height="{ALTURA}" fill="{tema["fundo"]}"/>'
        f'<g fill="{tema["chuva"]}">{chuva(tema, mono)}</g>'
        f"{placa_svg(tema, placa_dados)}"
        f'<path d="{dominio}" fill="{tema["sinal"]}"/>'
        f'<path d="{linha1}{linha2}" fill="{tema["tinta"]}"/>'
        f'<path d="{cargo}" fill="{tema["tinta2"]}"/></svg>\n'
    )


def selo(rotulo, cor, fonte):
    corpo, altura, folga = 13, 26, 10
    _, largura = fonte.curva(rotulo, corpo, 0, 0)
    total = round(largura + 2 * folga)
    d, _ = fonte.curva(rotulo, corpo, folga, altura / 2 + corpo * 0.35, casas=2)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="{altura}" viewBox="0 0 {total} {altura}" '
        f'role="img" aria-label="{rotulo}"><title>{rotulo}</title>'
        f'<rect x=".5" y=".5" width="{total - 1}" height="{altura - 1}" rx="2" fill="{cor}" stroke="#FF3646" stroke-opacity=".35"/>'
        f'<path d="{d}" fill="#F2E7E5"/></svg>\n'
    )


def gerar_selos(fonte):
    destino = RAIZ / "assets/selos"
    destino.mkdir(parents=True, exist_ok=True)
    total = 0
    for cor, rotulos in SELOS.items():
        for rotulo in rotulos:
            slug = re.sub(r"[^a-z0-9]+", "-", rotulo.lower()).strip("-")
            (destino / f"{slug}.svg").write_text(selo(rotulo, cor, fonte), encoding="utf-8")
            total += 1
    print(f"assets/selos: {total} selos")


def main():
    fontes = PORTFOLIO / "src/fontes"
    mona_titulo = Fonte(fontes / "mona-sans.woff2", wdth=112, wght=640)
    mona_texto = Fonte(fontes / "mona-sans.woff2", wdth=100, wght=450)
    mono = Fonte(fontes / "jetbrains-mono.woff2", wght=400)
    placa_dados = ler_placa()
    destino = RAIZ / "assets"
    destino.mkdir(exist_ok=True)
    for nome_tema in TEMAS:
        svg = banner(nome_tema, mona_titulo, mona_texto, mono, placa_dados)
        arquivo = destino / f"banner-{nome_tema}.svg"
        arquivo.write_text(svg, encoding="utf-8")
        print(f"{arquivo.relative_to(RAIZ)}: {len(svg.encode()) / 1024:.0f} KB")
    gerar_selos(Fonte(fontes / "mona-sans.woff2", wdth=100, wght=550))


if __name__ == "__main__":
    main()
