// Interface: barras, janela de atributos (estilo RO), mensagens e ajuda.
import Phaser from 'phaser';
import { MapData } from '../data/types';
import { Character, JOB_NAMES } from '../ro/character';
import { statCost, StatName, STAT_NAMES } from '../ro/rules';

const FONT = 'Verdana, Tahoma, sans-serif';
const RES = Math.min(2, window.devicePixelRatio || 1);
const HELP_KEY = 'ro-maple-help-seen';

const txt = (
  scene: Phaser.Scene,
  x: number,
  y: number,
  s: string,
  size = 12,
  color = '#ffffff',
  extra: Phaser.Types.GameObjects.Text.TextStyle = {},
) =>
  scene.add
    .text(x, y, s, { fontFamily: FONT, fontSize: `${size}px`, color, resolution: RES, ...extra })
    .setScrollFactor(0);

export class UI extends Phaser.Scene {
  private bars!: Phaser.GameObjects.Graphics;
  private lvText!: Phaser.GameObjects.Text;
  private jobText!: Phaser.GameObjects.Text;
  private hpText!: Phaser.GameObjects.Text;
  private spText!: Phaser.GameObjects.Text;
  private expText!: Phaser.GameObjects.Text;
  private jexpText!: Phaser.GameObjects.Text;
  private pointsBadge!: Phaser.GameObjects.Text;
  private logLines: { t: Phaser.GameObjects.Text; until: number }[] = [];
  private notice!: Phaser.GameObjects.Text;
  private banner!: Phaser.GameObjects.Container;
  private stats!: Phaser.GameObjects.Container;
  private statRows: Partial<Record<StatName, { val: Phaser.GameObjects.Text; plus: Phaser.GameObjects.Text; cost: Phaser.GameObjects.Text }>> = {};
  private derivedText!: Phaser.GameObjects.Text;
  private pointsText!: Phaser.GameObjects.Text;
  private deathBox!: Phaser.GameObjects.Container;
  private help!: Phaser.GameObjects.Container;

  constructor() {
    super('UI');
  }

  private get char(): Character {
    return this.registry.get('char');
  }

  create() {
    const { width, height } = this.scale;
    this.buildBottomBar(width, height);
    this.notice = txt(this, width / 2, 90, '', 18, '#ffe680', { stroke: '#2a1a00', strokeThickness: 4, fontStyle: 'bold' })
      .setOrigin(0.5)
      .setAlpha(0);
    this.banner = this.add.container(width / 2, 40).setAlpha(0);
    this.buildStatsWindow(width);
    this.buildDeathBox(width, height);
    this.buildHelp(width, height);

    const ev = this.game.events;
    ev.on('log', this.log, this);
    ev.on('notice', this.showNotice, this);
    ev.on('map-enter', this.showBanner, this);
    ev.on('dead', () => this.deathBox.setVisible(true));
    ev.on('revived', () => this.deathBox.setVisible(false));
    this.events.once('shutdown', () => ev.off('log').off('notice').off('map-enter').off('dead').off('revived'));

    const kb = this.input.keyboard!;
    kb.on('keydown-S', () => this.toggleStats());
    kb.on('keydown-H', () => this.help.setVisible(!this.help.visible));
    kb.on('keydown-M', () => {
      this.sound.mute = !this.sound.mute;
      this.showNotice(this.sound.mute ? 'Som desligado (M)' : 'Som ligado (M)');
    });
    kb.on('keydown-ESC', () => {
      this.stats.setVisible(false);
      this.help.setVisible(false);
    });

    let seen = false;
    try {
      seen = localStorage.getItem(HELP_KEY) === '1';
      localStorage.setItem(HELP_KEY, '1');
    } catch {
      /* ignora */
    }
    this.help.setVisible(!seen);
  }

  // ------------------------------------------------------------ barra inferior

  private buildBottomBar(width: number, height: number) {
    const y = height - 62;
    const bg = this.add.graphics();
    bg.fillGradientStyle(0x2a3350, 0x2a3350, 0x161b2b, 0x161b2b, 0.95).fillRect(0, y, width, 62);
    bg.lineStyle(1, 0x6b7bb0, 0.8).lineBetween(0, y, width, y);
    this.bars = this.add.graphics();
    this.lvText = txt(this, 14, y + 6, '', 20, '#ffe680', { fontStyle: 'bold', stroke: '#000', strokeThickness: 3 });
    this.jobText = txt(this, 14, y + 32, '', 11, '#c9d3f5');
    txt(this, 150, y + 8, 'HP', 11, '#ff9a9a', { fontStyle: 'bold' });
    txt(this, 150, y + 26, 'SP', 11, '#9ac4ff', { fontStyle: 'bold' });
    this.hpText = txt(this, 290, y + 7, '', 11).setOrigin(0.5, 0);
    this.spText = txt(this, 290, y + 25, '', 11).setOrigin(0.5, 0);
    this.expText = txt(this, width / 2, y + 44, '', 10).setOrigin(0.5, 0);
    this.jexpText = txt(this, width - 14, y + 26, '', 10, '#d8f0ff').setOrigin(1, 0);

    const btn = (x: number, label: string, cb: () => void) => {
      const b = txt(this, x, y + 6, label, 12, '#ffffff', {
        backgroundColor: '#3c4a78',
        padding: { x: 8, y: 3 },
      })
        .setInteractive({ useHandCursor: true })
        .on('pointerdown', cb);
      return b;
    };
    btn(width - 210, 'Atributos (S)', () => this.toggleStats());
    btn(width - 92, 'Ajuda (H)', () => this.help.setVisible(!this.help.visible));
    this.pointsBadge = txt(this, width - 216, y + 2, '', 10, '#1a1200', {
      backgroundColor: '#ffd24a',
      padding: { x: 4, y: 1 },
    }).setOrigin(1, 0);
  }

  update(time: number) {
    const c = this.char;
    if (!c) return;
    const { width, height } = this.scale;
    const d = c.data;
    const y = height - 62;
    this.lvText.setText(`Lv. ${d.baseLevel}`);
    this.jobText.setText(`${JOB_NAMES[d.job] ?? d.job}  ·  Classe ${d.jobLevel}`);
    this.hpText.setText(`${d.hp} / ${c.derived.maxHp}`);
    this.spText.setText(`${d.sp} / ${c.derived.maxSp}`);

    const g = this.bars.clear();
    const bar = (x: number, by: number, w: number, h: number, pct: number, color: number) => {
      g.fillStyle(0x0b0e18, 1).fillRect(x - 1, by - 1, w + 2, h + 2);
      g.fillStyle(color, 1).fillRect(x, by, Math.round(w * Phaser.Math.Clamp(pct, 0, 1)), h);
    };
    const hpPct = d.hp / c.derived.maxHp;
    bar(175, y + 8, 230, 13, hpPct, hpPct < 0.25 ? 0xff3b3b : 0xd94848);
    bar(175, y + 26, 230, 13, d.sp / c.derived.maxSp, 0x3f7fe0);

    const bNext = c.baseExpNext;
    const bPct = bNext ? d.baseExp / bNext : 1;
    bar(0, y + 56, width, 6, bPct, 0xf2c14e);
    this.expText.setText(bNext ? `EXP de base  ${d.baseExp} / ${bNext}  (${(bPct * 100).toFixed(1)}%)` : 'EXP de base  MÁX');
    const jNext = c.jobExpNext;
    const jPct = jNext ? d.jobExp / jNext : 1;
    bar(width - 330, y + 42, 316, 6, jPct, 0x7fd3ff);
    this.jexpText.setText(jNext ? `EXP de classe ${(jPct * 100).toFixed(1)}%` : 'EXP de classe MÁX');

    this.pointsBadge.setText(d.statPoints > 0 ? `${d.statPoints} pts` : '').setVisible(d.statPoints > 0);
    if (this.stats.visible) this.refreshStats();

    for (const l of this.logLines) if (time > l.until) l.t.setAlpha(Math.max(0, l.t.alpha - 0.02));
  }

  // ------------------------------------------------------------ mensagens

  private log(msg: string) {
    const { height } = this.scale;
    const t = txt(this, 12, 0, msg, 11, '#e8f0ff', { stroke: '#000', strokeThickness: 3 });
    this.logLines.push({ t, until: this.time.now + 6000 });
    while (this.logLines.length > 6) this.logLines.shift()!.t.destroy();
    this.logLines.forEach((l, i) => l.t.setY(height - 80 - (this.logLines.length - 1 - i) * 16));
  }

  private showNotice(msg: string) {
    this.notice.setText(msg).setAlpha(1);
    this.tweens.killTweensOf(this.notice);
    this.tweens.add({ targets: this.notice, alpha: 0, delay: 2200, duration: 600 });
  }

  private showBanner(data: MapData) {
    this.banner.removeAll(true);
    const street = txt(this, 0, 0, data.street, 12, '#cfe3ff', { stroke: '#000', strokeThickness: 3 }).setOrigin(0.5);
    const name = txt(this, 0, 20, data.name, 20, '#ffffff', { stroke: '#000', strokeThickness: 4, fontStyle: 'bold' }).setOrigin(0.5);
    this.banner.add([street, name]).setAlpha(1);
    this.tweens.killTweensOf(this.banner);
    this.tweens.add({ targets: this.banner, alpha: 0, delay: 2500, duration: 800 });
  }

  // ------------------------------------------------------------ atributos

  private buildStatsWindow(width: number) {
    const w = 330;
    const h = 236;
    const c = this.add.container(width - w - 16, 60).setVisible(false);
    const g = this.add.graphics();
    g.fillStyle(0xf4f1e8, 0.97).fillRoundedRect(0, 0, w, h, 6);
    g.fillStyle(0x5a6fa8, 1).fillRoundedRect(0, 0, w, 24, { tl: 6, tr: 6, bl: 0, br: 0 });
    g.lineStyle(1, 0x3c4a78).strokeRoundedRect(0, 0, w, h, 6);
    c.add(g);
    c.add(txt(this, 10, 5, 'Atributos', 12, '#ffffff', { fontStyle: 'bold' }));
    const close = txt(this, w - 20, 4, 'x', 13, '#ffffff', { fontStyle: 'bold' })
      .setInteractive({ useHandCursor: true })
      .on('pointerdown', () => c.setVisible(false));
    c.add(close);

    STAT_NAMES.forEach((s, i) => {
      const y = 36 + i * 24;
      c.add(txt(this, 12, y, s.toUpperCase(), 12, '#2b3150', { fontStyle: 'bold' }));
      const val = txt(this, 52, y, '', 12, '#1b1f33');
      const plus = txt(this, 112, y - 2, '+', 13, '#ffffff', {
        backgroundColor: '#5a6fa8',
        padding: { x: 5, y: 0 },
        fontStyle: 'bold',
      })
        .setInteractive({ useHandCursor: true })
        .on('pointerdown', () => {
          if (this.char.raise(s)) this.char.save();
        });
      const cost = txt(this, 136, y, '', 10, '#7a7f95');
      c.add([val, plus, cost]);
      this.statRows[s] = { val, plus, cost };
    });
    this.pointsText = txt(this, 12, h - 26, '', 12, '#2b3150', { fontStyle: 'bold' });
    this.derivedText = txt(this, 186, 36, '', 12, '#1b1f33', { lineSpacing: 6 });
    c.add([this.pointsText, this.derivedText]);
    this.stats = c;
  }

  private toggleStats() {
    this.stats.setVisible(!this.stats.visible);
    if (this.stats.visible) this.refreshStats();
  }

  private refreshStats() {
    const c = this.char;
    for (const s of STAT_NAMES) {
      const row = this.statRows[s]!;
      const bonus = c.bonusOf(s);
      row.val.setText(`${c.data.stats[s]}${bonus ? ` + ${bonus}` : ''}`);
      const can = c.canRaise(s);
      row.plus.setAlpha(can ? 1 : 0.35);
      row.cost.setText(`custo ${statCost(c.data.stats[s])}`);
    }
    const d = c.derived;
    this.derivedText.setText(
      [
        `ATK     ${d.atk} + 25`,
        `MATK    ${d.matkMin} ~ ${d.matkMax}`,
        `DEF     ${d.def} + ${d.softDef}`,
        `MDEF    0 + ${d.mdef}`,
        `HIT     ${d.hit}`,
        `FLEE    ${d.flee} + ${d.perfectDodge}`,
        `CRIT    ${d.crit}`,
        `ASPD    ${d.aspd}`,
      ].join('\n'),
    );
    this.pointsText.setText(`Pontos de atributo: ${c.data.statPoints}`);
  }

  // ------------------------------------------------------------ morte / ajuda

  private buildDeathBox(width: number, height: number) {
    const c = this.add.container(width / 2, height / 2 - 40).setVisible(false);
    const g = this.add.graphics();
    g.fillStyle(0x10131f, 0.92).fillRoundedRect(-200, -50, 400, 100, 8);
    g.lineStyle(1, 0xb04848).strokeRoundedRect(-200, -50, 400, 100, 8);
    c.add(g);
    c.add(txt(this, 0, -30, 'Você foi derrotado.', 16, '#ff8a8a', { fontStyle: 'bold' }).setOrigin(0.5, 0));
    c.add(txt(this, 0, 2, 'Aperte Enter para voltar à cidade\n(perde 1% da EXP de base, como no RO)', 12, '#dfe6ff', { align: 'center' }).setOrigin(0.5, 0));
    this.deathBox = c;
  }

  private buildHelp(width: number, height: number) {
    const c = this.add.container(width / 2, height / 2 - 30);
    const g = this.add.graphics();
    g.fillStyle(0x10131f, 0.93).fillRoundedRect(-230, -150, 460, 300, 8);
    g.lineStyle(1, 0x6b7bb0).strokeRoundedRect(-230, -150, 460, 300, 8);
    c.add(g);
    c.add(txt(this, 0, -136, 'Como jogar', 16, '#ffe680', { fontStyle: 'bold' }).setOrigin(0.5, 0));
    const lines = [
      ['← →', 'andar'],
      ['Espaço / Alt', 'pular'],
      ['↓ + Espaço', 'descer de uma plataforma'],
      ['↑ / ↓', 'subir/descer escadas e cordas'],
      ['↑ no portal', 'trocar de mapa'],
      ['Z, X ou Ctrl', 'atacar (segure para atacar sem parar)'],
      ['↓', 'deitar'],
      ['S', 'janela de atributos (STR, AGI, VIT, INT, DEX, LUK)'],
      ['M', 'ligar/desligar o som'],
      ['H', 'mostrar/esconder esta ajuda'],
    ];
    lines.forEach(([k, v], i) => {
      c.add(txt(this, -205, -100 + i * 22, k, 12, '#9ac4ff', { fontStyle: 'bold' }));
      c.add(txt(this, -75, -100 + i * 22, v, 12, '#e8f0ff'));
    });
    c.add(
      txt(this, 0, 128, 'Os monstros só atacam depois de provocados, como no RO.', 11, '#c9d3f5').setOrigin(0.5, 0),
    );
    c.setInteractive(new Phaser.Geom.Rectangle(-230, -150, 460, 300), Phaser.Geom.Rectangle.Contains).on(
      'pointerdown',
      () => c.setVisible(false),
    );
    this.help = c;
  }
}
