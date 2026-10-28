# RO Maple

Projeto pessoal: um jogo 2D de plataforma com a cara do **MapleStory** e as regras do
**Ragnarok Online (Pré-Renewal)**.

- **Visual, mapas e física de plataformas:** MapleStory GMS v83, extraídos via [maplestory.io](https://maplestory.io).
- **Regras (EXP, atributos, HP/SP, fórmulas de dano, bônus de classe):** banco de dados
  pré-renewal do [rAthena](https://github.com/rathena/rathena).
- **Motor:** [Phaser 3](https://phaser.io) + TypeScript + Vite.

> Os gráficos e sons pertencem à Nexon. Este repositório é privado e de uso pessoal; não publique os assets.

## Como jogar no seu computador

1. Instale o [Node.js](https://nodejs.org) (versão LTS).
2. Baixe este repositório (botão **Code → Download ZIP** no GitHub, ou `git clone`).
3. Na pasta do projeto, abra um terminal e rode:

   ```bash
   npm install
   npm run dev
   ```

4. Abra no navegador o endereço que aparecer (normalmente http://localhost:5173).

### Controles

| Tecla | Ação |
| --- | --- |
| ← → | andar |
| Espaço / Alt | pular |
| ↓ + Espaço | descer de uma plataforma |
| ↑ / ↓ | subir/descer escadas e cordas |
| ↑ em cima de um portal | trocar de mapa |
| Z, X ou Ctrl | atacar (segure para continuar atacando) |
| S | janela de atributos |
| M | ligar/desligar o som |
| H | ajuda |

O progresso é salvo automaticamente no navegador.

## O que já existe (versão 0.1)

- Henesys (cidade) e A Colina a Leste de Henesys (caça), ligadas por portal.
- Física de plataformas do Maple: rampas, paredes, escadas, cordas, descer de plataformas.
- Fundos com parallax, NPCs, música e efeitos sonoros originais.
- Aprendiz (Novice) com nível de base/classe, tabela de EXP do RO, 48 pontos iniciais,
  custo de atributo do RO, HP/SP por nível, bônus de classe, ASPD, HIT/FLEE, crítico.
- Monstros com visual do Maple e atributos do RO: Caracol Azul (Poring), Cogumelo (Fabre),
  Caracol Vermelho (Lunatic), Porco (Savage Babe). Só atacam depois de provocados, como no RO.
- Morte com penalidade de 1% da EXP e retorno à cidade.

## Estrutura

```
tools/fetch_assets.py   baixa e organiza os assets do MapleStory em public/assets
tools/build_ro_data.py  gera src/data/ro.json a partir do rAthena
src/ro/                 regras e progressão do RO
src/world/              mapa, plataformas (footholds) e fundos
src/entities/           jogador e monstros
src/scenes/             carregamento, jogo e interface
```

Para adicionar mapas ou monstros: edite `MAPS` em `tools/fetch_assets.py` e
`MOB_TEMPLATES` em `tools/build_ro_data.py`, depois rode `npm run assets` e `npm run ro-data`
(precisa de Python 3 com Pillow e PyYAML).
