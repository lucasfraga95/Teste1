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
| ↑ | entrar em portais e falar com NPCs |
| Z, X ou Ctrl | atacar (segure para continuar atacando) |
| Q W E R | habilidades |
| 1 2 3 4 | poções |
| S / K / I | atributos / habilidades / itens |
| M | ligar/desligar o som |
| H | ajuda |

O progresso é salvo automaticamente no navegador.

## O que já existe (versão 0.2)

- **8 mapas:** Henesys e 7 campos de caça ao redor (níveis 1 a 20), ligados por portais.
- **Classes:** Aprendiz → Espadachim, Mago, Arqueiro ou Gatuno (nível de classe 10 +
  Habilidades Básicas 9, falando com Cody em Henesys). Cada classe tem visual e arma próprios.
- **Habilidades (números do RO Pré-Renewal):**
  - Espadachim: Golpe Fulminante, Impacto Explosivo, Recuperação de HP, Perícia com Espada
  - Mago: Lanças de Fogo, Lanças de Gelo, Relâmpago (com conjuração), Recuperação de SP
  - Arqueiro: Rajada de Flechas, Chuva de Flechas, Olhos de Coruja, Olhos de Águia
  - Gatuno: Ataque Duplo, Envenenar, Perícia em Esquiva
- **Regras do RO:** tabela de EXP, atributos, HP/SP por classe, ASPD, HIT/FLEE, crítico,
  tabela de elementos, tamanho do alvo, penalidade de morte.
- **10 monstros** com visual do Maple e atributos de monstros do RO (Poring, Fabre, Lunatic,
  Drops, Savage Babe, Rocker, Poporing, Spore, Poison Spore, Horn). O Cogumelo Azul é agressivo.
- **Itens:** saques e poções caem dos monstros; loja de poções (Rina), curandeira (Nana) e
  táxi para os campos de caça (Regular Cab) em Henesys.

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
