// Interface: barras, atalhos, janelas (atributos, habilidades, itens) e NPCs.
import { Capacitor } from '@capacitor/core';
import Phaser from 'phaser';
import { MapData } from '../data/types';
import { Character } from '../ro/character';
import { CLASSES, FIRST_CLASSES } from '../ro/classes';
import { ITEMS, POTION_SLOTS, SHOP_ITEMS } from '../ro/items';
import { statCost, StatName, STAT_NAMES } from '../ro/rules';
import { SKILLS } from '../ro/skills';
import { MAP_NAMES } from '../world/names';
import { NpcRole, TAXI_DESTINATIONS } from '../world/npcs';
import { isTouchDevice, TouchControls } from '../ui/TouchControls';
import type { Game } from './Game';

const FONT = 'Verdana, Tahoma, sans-serif';
const RES = Math.min(2, window.devicePixelRatio || 1);
const HELP_KEY = 'ro-maple-help-seen';
const BAR_H = 62;
const PANEL = 0xf4f1e8;
const HEADER = 0x5a6fa8;
const INK = '#1b1f33';

type Style = Phaser.Types.GameObjects.Text.TextStyle;

interface NpcTalk {
  id: number;
  name: string;
  role: NpcRole;
  title: string;
}

export class UI extends Phaser.Scene {
  private bars!: Phaser.GameObjects.Graphics;
  private lvText!: Phaser.GameObjects.Text;
  private jobText!: Phaser.GameObjects.Text;
  private expText!: Phaser.GameObjects.Text;
  private hpText!: Phaser.GameObjects.Text;
  private spText!: Phaser.GameObjects.Text;
  private statBadge!: Phaser.GameObjects.Text;
  private skillBadge!: Phaser.GameObjects.Text;
  private slots: { icon: Phaser.GameObjects.Image; count: Phaser.GameObjects.Text; cd: Phaser.GameObjects.Graphics }[] = [];
  private logLines: { t: Phaser.GameObjects.Text; until: number }[] = [];
  private notice!: Phaser.GameObjects.Text;
  private banner!: Phaser.GameObjects.Container;
  private castBar!: Phaser.GameObjects.Graphics;
  private deathBox!: Phaser.GameObjects.Container;
  private help!: Phaser.GameObjects.Container;
  private windows: Record<'stats' | 'skills' | 'items' | 'npc', Phaser.GameObjects.Container | null> = {
    stats: null,
    skills: null,
    items: null,
    npc: null,
  };
  private npcTalk: NpcTalk | null = null;
  private lastSig = '';

  constructor() {
    super('UI');
  }

  private get char(): Character {
    return this.registry.get('char');
  }

  private get game_(): Game {
    return this.scene.get('Game') as Game;
  }

  // ------------------------------------------------------------ helpers

  private txt(x: number, y: number, s: string, size = 12, color = '#ffffff', extra: Style = {}) {
    return this.add.text(x, y, s, { fontFamily: FONT, fontSize: `${size}px`, color, resolution: RES, ...extra });
  }

  private button(x: number, y: number, label: string, cb: () => void, enabled = true, color = '#3c4a78') {
    const b = this.txt(x, y, label, 12, '#ffffff', { backgroundColor: enabled ? color : '#8a8fa3', padding: { x: 7, y: 3 } });
    if (enabled) b.setInteractive({ useHandCursor: true }).on('pointerdown', (p: Phaser.Input.Pointer, lx: number, ly: number, e: Phaser.Types.Input.EventData) => {
      e.stopPropagation();
      cb();
    });
    return b;
  }

  /** Painel com título e botão de fechar. */
  private panel(name: keyof UI['windows'], x: number, y: number, w: number, h: number, title: string) {
    this.windows[name]?.destroy();
    const c = this.add.container(x, y);
    const g = this.add.graphics();
    g.fillStyle(PANEL, 0.97).fillRoundedRect(0, 0, w, h, 6);
    g.fillStyle(HEADER, 1).fillRoundedRect(0, 0, w, 24, { tl: 6, tr: 6, bl: 0, br: 0 });
    g.lineStyle(1, 0x3c4a78).strokeRoundedRect(0, 0, w, h, 6);
    c.add(g);
    // Bloqueia cliques que atravessariam o painel.
    c.add(this.add.zone(0, 0, w, h).setOrigin(0).setInteractive());
    c.add(this.txt(10, 5, title, 12, '#ffffff', { fontStyle: 'bold' }));
    c.add(
      this.txt(w - 20, 4, 'x', 13, '#ffffff', { fontStyle: 'bold' })
        .setInteractive({ useHandCursor: true })
        .on('pointerdown', () => this.close(name)),
    );
    this.windows[name] = c;
    return c;
  }

  private close(name: keyof UI['windows']) {
    this.windows[name]?.destroy();
    this.windows[name] = null;
    if (name === 'npc') {
      this.npcTalk = null;
      this.game_.closeDialog();
    }
  }

  private toggle(name: 'stats' | 'skills' | 'items') {
    if (this.windows[name]) this.close(name);
    else this.render(name);
  }

  private render(name: keyof UI['windows']) {
    if (name === 'stats') this.renderStats();
    else if (name === 'skills') this.renderSkills();
    else if (name === 'items') this.renderItems();
    else if (name === 'npc' && this.npcTalk) this.renderNpc(this.npcTalk);
  }

  // ------------------------------------------------------------ ciclo

  create() {
    const { width, height } = this.scale;
    this.buildBottomBar(width, height);
    this.castBar = this.add.graphics();
    this.notice = this.txt(width / 2, 90, '', 18, '#ffe680', { stroke: '#2a1a00', strokeThickness: 4, fontStyle: 'bold' })
      .setOrigin(0.5)
      .setAlpha(0);
    this.banner = this.add.container(width / 2, 40).setAlpha(0);
    if (isTouchDevice()) {
      this.registry.set('touch', new TouchControls(this));
      // No app Android ele já abre em tela cheia.
      if (!Capacitor.isNativePlatform()) this.buildFullscreenButton(width);
    }
    this.buildDeathBox(width, height);
    this.buildHelp(width, height);

    const ev = this.game.events;
    const handlers: [string, (...a: never[]) => void][] = [
      ['log', this.log],
      ['notice', this.showNotice],
      ['map-enter', this.showBanner],
      ['dead', () => this.deathBox.setVisible(true)],
      ['revived', () => this.deathBox.setVisible(false)],
      ['npc-talk', (t: NpcTalk) => this.openNpc(t)],
    ];
    for (const [e, h] of handlers) ev.on(e, h, this);
    this.events.once('shutdown', () => handlers.forEach(([e, h]) => ev.off(e, h, this)));

    const kb = this.input.keyboard!;
    kb.on('keydown-S', () => this.toggle('stats'));
    kb.on('keydown-K', () => this.toggle('skills'));
    kb.on('keydown-I', () => this.toggle('items'));
    kb.on('keydown-H', () => this.help.setVisible(!this.help.visible));
    kb.on('keydown-M', () => {
      this.sound.mute = !this.sound.mute;
      this.showNotice(this.sound.mute ? 'Som desligado (M)' : 'Som ligado (M)');
    });
    kb.on('keydown-ESC', () => {
      (Object.keys(this.windows) as (keyof UI['windows'])[]).forEach((n) => this.close(n));
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

  update(time: number) {
    const c = this.char;
    if (!c) return;
    this.updateBottomBar();
    this.updateCastBar();
    for (const l of this.logLines) if (time > l.until) l.t.setAlpha(Math.max(0, l.t.alpha - 0.02));

    // Redesenha janelas abertas quando os dados mudam.
    const d = c.data;
    const sig = JSON.stringify([d.stats, d.statPoints, d.skillPoints, d.skills, d.inventory, d.zeny, d.job, d.jobLevel, d.baseLevel]);
    if (sig !== this.lastSig) {
      this.lastSig = sig;
      (Object.keys(this.windows) as (keyof UI['windows'])[]).forEach((n) => this.windows[n] && this.render(n));
    }
  }

  // ------------------------------------------------------------ barra inferior

  private buildBottomBar(width: number, height: number) {
    const y = height - BAR_H;
    const bg = this.add.graphics();
    bg.fillGradientStyle(0x2a3350, 0x2a3350, 0x161b2b, 0x161b2b, 0.95).fillRect(0, y, width, BAR_H);
    bg.lineStyle(1, 0x6b7bb0, 0.8).lineBetween(0, y, width, y);
    this.bars = this.add.graphics();
    this.lvText = this.txt(12, y + 3, '', 19, '#ffe680', { fontStyle: 'bold', stroke: '#000', strokeThickness: 3 });
    this.jobText = this.txt(12, y + 27, '', 11, '#c9d3f5');
    this.expText = this.txt(12, y + 41, '', 10, '#f2d27a');
    this.txt(150, y + 6, 'HP', 11, '#ff9a9a', { fontStyle: 'bold' });
    this.txt(150, y + 24, 'SP', 11, '#9ac4ff', { fontStyle: 'bold' });
    this.txt(146, y + 40, 'JOB', 9, '#bfe8ff', { fontStyle: 'bold' });
    this.hpText = this.txt(290, y + 6, '', 11).setOrigin(0.5, 0);
    this.spText = this.txt(290, y + 24, '', 11).setOrigin(0.5, 0);

    // Atalhos: Q W E R (habilidades) e 1 2 3 4 (poções). Também funcionam com toque.
    const keys = ['Q', 'W', 'E', 'R', '1', '2', '3', '4'];
    keys.forEach((k, i) => {
      const sx = 422 + i * 40 + (i >= 4 ? 8 : 0);
      const sy = y + 8;
      const g = this.add.graphics();
      g.fillStyle(0x0f1322, 0.9).fillRoundedRect(sx, sy, 36, 36, 4);
      g.lineStyle(1, i < 4 ? 0x8a7bd8 : 0xd87b7b, 0.9).strokeRoundedRect(sx, sy, 36, 36, 4);
      const icon = this.add.image(sx + 18, sy + 18, '__DEFAULT').setVisible(false);
      const cd = this.add.graphics();
      const count = this.txt(sx + 34, sy + 35, '', 10, '#ffffff', { stroke: '#000', strokeThickness: 3 }).setOrigin(1, 1);
      this.txt(sx + 2, sy, k, 9, '#ffe680', { stroke: '#000', strokeThickness: 2 });
      const hit = this.add.zone(sx, sy, 36, 36).setOrigin(0).setInteractive({ useHandCursor: true });
      hit.on('pointerdown', () => (i < 4 ? this.game_.useSkillSlot(i) : this.game_.usePotionSlot(i - 4)));
      this.slots.push({ icon, count, cd });
    });

    const bx = width - 262;
    const statBtn = this.button(bx, y + 6, 'Atributos (S)', () => this.toggle('stats'));
    const skillBtn = this.button(bx + 128, y + 6, 'Habilidades (K)', () => this.toggle('skills'));
    this.button(bx, y + 33, 'Itens (I)', () => this.toggle('items'));
    this.button(bx + 128, y + 33, 'Ajuda (H)', () => this.help.setVisible(!this.help.visible));
    const badge: Style = { backgroundColor: '#ffd24a', padding: { x: 3, y: 0 }, fontStyle: 'bold' };
    this.statBadge = this.txt(statBtn.x + statBtn.width + 4, y - 8, '', 10, '#1a1200', badge).setOrigin(1, 0);
    this.skillBadge = this.txt(skillBtn.x + skillBtn.width + 4, y - 8, '', 10, '#1a1200', badge).setOrigin(1, 0);
  }

  private updateBottomBar() {
    const c = this.char;
    const d = c.data;
    const { width, height } = this.scale;
    const y = height - BAR_H;
    this.lvText.setText(`Lv. ${d.baseLevel}`);
    this.jobText.setText(`${c.cls.name} · Classe ${d.jobLevel}`);
    const bNext = c.baseExpNext;
    const bPct = bNext ? d.baseExp / bNext : 1;
    this.expText.setText(bNext ? `EXP ${(bPct * 100).toFixed(1)}%` : 'EXP MÁX');
    this.hpText.setText(`${d.hp} / ${c.derived.maxHp}`);
    this.spText.setText(`${d.sp} / ${c.derived.maxSp}`);

    const g = this.bars.clear();
    const bar = (x: number, by: number, w: number, h: number, pct: number, color: number) => {
      g.fillStyle(0x0b0e18, 1).fillRect(x - 1, by - 1, w + 2, h + 2);
      g.fillStyle(color, 1).fillRect(x, by, Math.round(w * Phaser.Math.Clamp(pct, 0, 1)), h);
    };
    const hpPct = d.hp / c.derived.maxHp;
    bar(175, y + 6, 230, 13, hpPct, hpPct < 0.25 ? 0xff3b3b : 0xd94848);
    bar(175, y + 24, 230, 13, d.sp / c.derived.maxSp, 0x3f7fe0);
    const jNext = c.jobExpNext;
    bar(175, y + 43, 230, 5, jNext ? d.jobExp / jNext : 1, 0x7fd3ff);
    bar(0, y + 56, width, 6, bPct, 0xf2c14e);

    const skills = c.activeSkills;
    const combat = this.game_.combat;
    this.slots.forEach((s, i) => {
      s.cd.clear();
      if (i < 4) {
        const id = skills[i];
        s.icon.setVisible(!!id);
        s.count.setText('');
        if (!id) return;
        s.icon.setTexture(`icon-skill-${id}`).setDisplaySize(32, 32);
        const def = SKILLS[id];
        const lacksSp = d.sp < (def.sp?.(c.skillLevel(id)) ?? 0);
        s.icon.setAlpha(lacksSp ? 0.4 : 1);
        const left = combat?.cooldownLeft(id) ?? 0;
        if (left > 0) {
          const pct = left / Math.max(1, def.cooldownMs ?? 1);
          s.cd.fillStyle(0x000000, 0.6).fillRect(s.icon.x - 18, s.icon.y - 18, 36, 36 * Math.min(1, pct));
        }
      } else {
        const id = POTION_SLOTS[i - 4];
        const n = c.count(id);
        s.icon.setTexture(`icon-item-${id}`).setVisible(true).setScale(1).setAlpha(n ? 1 : 0.35);
        s.count.setText(String(n));
      }
    });
    this.statBadge.setText(d.statPoints ? String(d.statPoints) : '').setVisible(d.statPoints > 0);
    this.skillBadge.setText(d.skillPoints ? String(d.skillPoints) : '').setVisible(d.skillPoints > 0);
  }

  private updateCastBar() {
    const g = this.castBar.clear();
    const game = this.game_;
    const pr = game?.player?.castProgress;
    if (pr == null) return;
    const cam = game.cameras.main;
    const x = game.player.x - cam.worldView.x - 30;
    const y = game.player.y - cam.worldView.y - 92;
    g.fillStyle(0x10131c, 0.9).fillRect(x - 1, y - 1, 62, 8);
    g.fillStyle(0x9f7bff).fillRect(x, y, 60 * pr, 6);
  }

  // ------------------------------------------------------------ mensagens

  private log(msg: string) {
    const { height } = this.scale;
    const t = this.txt(12, 0, msg, 11, '#e8f0ff', { stroke: '#000', strokeThickness: 3 });
    this.logLines.push({ t, until: this.time.now + 6000 });
    while (this.logLines.length > 6) this.logLines.shift()!.t.destroy();
    this.logLines.forEach((l, i) => l.t.setY(height - BAR_H - 18 - (this.logLines.length - 1 - i) * 16));
  }

  private showNotice(msg: string) {
    this.notice.setText(msg).setAlpha(1);
    this.tweens.killTweensOf(this.notice);
    this.tweens.add({ targets: this.notice, alpha: 0, delay: 2200, duration: 600 });
  }

  private showBanner(data: MapData) {
    data = { ...data, ...MAP_NAMES[data.id] };
    this.banner.removeAll(true);
    const street = this.txt(0, 0, data.street, 12, '#cfe3ff', { stroke: '#000', strokeThickness: 3 }).setOrigin(0.5);
    const name = this.txt(0, 20, data.name, 20, '#ffffff', { stroke: '#000', strokeThickness: 4, fontStyle: 'bold' }).setOrigin(0.5);
    this.banner.add([street, name]).setAlpha(1);
    this.tweens.killTweensOf(this.banner);
    this.tweens.add({ targets: this.banner, alpha: 0, delay: 2500, duration: 800 });
  }

  // ------------------------------------------------------------ atributos

  private renderStats() {
    const c = this.char;
    const w = 330;
    const p = this.panel('stats', this.scale.width - w - 12, 40, w, 250, 'Atributos');
    STAT_NAMES.forEach((s: StatName, i) => {
      const y = 36 + i * 26;
      const bonus = c.bonusOf(s);
      p.add(this.txt(12, y, s.toUpperCase(), 12, '#2b3150', { fontStyle: 'bold' }));
      p.add(this.txt(52, y, `${c.data.stats[s]}${bonus ? ` + ${bonus}` : ''}`, 12, INK));
      p.add(
        this.button(112, y - 3, '+', () => c.raise(s) && c.save(), c.canRaise(s), '#5a6fa8'),
      );
      p.add(this.txt(140, y, `custo ${statCost(c.data.stats[s])}`, 10, '#7a7f95'));
    });
    const d = c.derived;
    const w_ = c.cls.weapon;
    p.add(
      this.txt(
        190,
        36,
        [
          `ATK    ${d.atk} + ${w_.atk}`,
          `MATK   ${d.matkMin} ~ ${d.matkMax}`,
          `DEF    ${d.def} + ${d.softDef}`,
          `MDEF   0 + ${d.mdef}`,
          `HIT    ${d.hit}`,
          `FLEE   ${d.flee} + ${d.perfectDodge}`,
          `CRIT   ${d.crit}`,
          `ASPD   ${d.aspd}`,
        ].join('\n'),
        12,
        INK,
        { lineSpacing: 7 },
      ),
    );
    p.add(this.txt(12, 200, `Pontos de atributo: ${c.data.statPoints}`, 12, '#2b3150', { fontStyle: 'bold' }));
    p.add(
      this.button(190, 196, 'Distribuir automaticamente', () => {
        if (c.autoDistribute()) c.save();
      }, c.data.statPoints >= 2, '#4a8a5a'),
    );
    p.add(this.txt(12, 222, `Arma: ${w_.name} (ATK ${w_.atk})`, 11, '#5b6075'));
  }

  // ------------------------------------------------------------ habilidades

  private renderSkills() {
    const c = this.char;
    const list = c.skillList;
    const w = 380;
    const h = 64 + list.length * 58;
    const p = this.panel('skills', 12, 40, w, h, `Habilidades · ${c.cls.name}`);
    p.add(this.txt(12, 32, `Pontos de habilidade: ${c.data.skillPoints}`, 12, '#2b3150', { fontStyle: 'bold' }));
    list.forEach((id, i) => {
      const s = SKILLS[id];
      const lv = c.skillLevel(id);
      const y = 56 + i * 58;
      p.add(this.add.image(28, y + 18, `icon-skill-${id}`).setDisplaySize(32, 32));
      p.add(this.txt(52, y, s.name, 12, INK, { fontStyle: 'bold' }));
      p.add(this.txt(w - 96, y, `Nv ${lv}/${s.maxLevel}`, 11, '#5a6fa8', { fontStyle: 'bold' }));
      const unmet = (s.req ?? []).filter((r) => c.skillLevel(r.skill) < r.level);
      const info = unmet.length
        ? `Requer ${unmet.map((r) => `${SKILLS[r.skill].name} ${r.level}`).join(', ')}`
        : s.desc(Math.max(1, lv)) + (s.sp ? `  SP ${s.sp(Math.max(1, lv))}` : '') + (s.kind === 'passive' ? '  (passiva)' : '');
      p.add(this.txt(52, y + 17, info, 10, unmet.length ? '#b04848' : '#4a4f63', { wordWrap: { width: w - 110 } }));
      p.add(this.button(w - 34, y + 2, '+', () => c.learn(id) && c.save(), c.canLearn(id), '#5a6fa8'));
    });
    if (c.data.job === 'Novice') {
      const ok = c.canChangeJob;
      p.add(
        this.txt(12, h - 22, ok ? 'Pronto para mudar de classe! Fale com Cody em Henesys.' : 'Nível de classe 10 + Habilidades Básicas 9 = mudança de classe.', 10, ok ? '#2d8a3a' : '#5b6075'),
      );
    }
  }

  // ------------------------------------------------------------ itens

  private renderItems() {
    const c = this.char;
    const entries = Object.entries(c.data.inventory)
      .map(([k, n]) => [Number(k), n] as const)
      .filter(([id]) => ITEMS[id])
      .sort((a, b) => a[0] - b[0]);
    const rows = Math.max(1, Math.ceil(entries.length / 2));
    const w = 400;
    const h = 70 + rows * 40;
    const p = this.panel('items', this.scale.width / 2 - w / 2, 40, w, h, 'Itens');
    p.add(this.add.image(20, 41, 'icon-meso').setDisplaySize(20, 20));
    p.add(this.txt(34, 34, `${c.data.zeny.toLocaleString('pt-BR')} zeny`, 12, INK, { fontStyle: 'bold' }));
    if (!entries.length) p.add(this.txt(12, 64, 'Inventário vazio.', 11, '#5b6075'));
    entries.forEach(([id, n], i) => {
      const it = ITEMS[id];
      const x = 10 + (i % 2) * 195;
      const y = 60 + Math.floor(i / 2) * 40;
      p.add(this.add.image(x + 16, y + 16, `icon-item-${id}`));
      p.add(this.txt(x + 36, y + 2, it.name, 11, INK, { wordWrap: { width: 110 } }));
      p.add(this.txt(x + 36, y + 17, `x${n}`, 10, '#5b6075'));
      if (it.type === 'consume') {
        p.add(this.button(x + 140, y + 4, 'Usar', () => this.game_.useItem(id), true, '#4a8a5a'));
      }
    });
  }

  // ------------------------------------------------------------ NPCs

  private openNpc(t: NpcTalk) {
    this.npcTalk = t;
    if (t.role === 'heal') this.game_.heal();
    this.renderNpc(t);
  }

  private renderNpc(t: NpcTalk) {
    const c = this.char;
    const w = 520;
    const lines: (string | [string, () => void, boolean?, string?])[] = [];
    let text = '';
    if (t.role === 'job') {
      if (c.data.job !== 'Novice') {
        text = `Você já é ${c.cls.name}. Continue treinando! Novas classes chegarão em breve.`;
      } else if (!c.canChangeJob) {
        text =
          'Para escolher uma classe você precisa de:\n' +
          `• Nível de classe 10 (você tem ${c.data.jobLevel})\n` +
          `• Habilidades Básicas nível 9 (você tem ${c.skillLevel('basic')}) — abra Habilidades (K) para aprender.`;
      } else {
        text = 'Você está pronto! Escolha seu caminho:';
        for (const id of FIRST_CLASSES) {
          const cls = CLASSES[id];
          lines.push([`${cls.name} — ${cls.desc}`, () => {
            this.game_.changeJob(id);
            this.close('npc');
          }]);
        }
      }
    } else if (t.role === 'heal') {
      text = 'Pronto! HP e SP totalmente restaurados. Volte sempre que precisar.';
    } else if (t.role === 'shop') {
      text = `Seu zeny: ${c.data.zeny.toLocaleString('pt-BR')}`;
      for (const id of SHOP_ITEMS) {
        const it = ITEMS[id];
        const desc = it.hp ? `+${it.hp} HP` : `+${it.sp} SP`;
        lines.push([`${it.name} (${desc}) — ${it.price} z`, () => c.buy(id) ? c.save() : this.showNotice('Zeny insuficiente.'), c.data.zeny >= it.price!, `icon-item-${id}`]);
      }
      const loot = Object.entries(c.data.inventory).reduce((sum, [k, n]) => sum + (ITEMS[Number(k)]?.type === 'etc' ? ITEMS[Number(k)].sell * n : 0), 0);
      lines.push([`Vender todos os saques (+${loot} z)`, () => {
        const got = c.sellLoot();
        c.save();
        this.showNotice(`Vendido por ${got} zeny.`);
      }, loot > 0]);
    } else if (t.role === 'taxi') {
      text = `Para onde vamos? Seu zeny: ${c.data.zeny.toLocaleString('pt-BR')}`;
      for (const dst of TAXI_DESTINATIONS) {
        lines.push([`${dst.name} (${dst.levels}) — ${dst.price} z`, () => {
          if (c.data.zeny < dst.price) return;
          c.data.zeny -= dst.price;
          this.close('npc');
          this.game_.changeMap(dst.map);
        }, c.data.zeny >= dst.price]);
      }
    }

    const textH = 18 * (text.split('\n').length + 1);
    const h = 70 + textH + lines.length * 30 + 10;
    const p = this.panel('npc', this.scale.width / 2 - w / 2, Math.max(20, this.scale.height - BAR_H - h - 20), w, h, `${t.name} · ${t.title}`);
    if (this.textures.exists(`npc${t.id}`)) {
      const portrait = this.add.sprite(w - 50, 70, `npc${t.id}`, 0).setScale(0.8);
      p.add(portrait);
    }
    p.add(this.txt(14, 34, text, 12, INK, { lineSpacing: 4, wordWrap: { width: w - 110 } }));
    lines.forEach((l, i) => {
      if (typeof l === 'string') return;
      const [label, cb, enabled = true, icon] = l;
      const y = 40 + textH + i * 30;
      if (icon) p.add(this.add.image(26, y + 10, icon).setDisplaySize(24, 24));
      p.add(this.button(icon ? 44 : 14, y, label, cb, enabled));
    });
    p.add(this.button(w - 70, h - 32, 'Sair', () => this.close('npc'), true, '#7a4a4a'));
  }

  /** Tela cheia e orientação horizontal (celular/tablet). */
  private buildFullscreenButton(width: number) {
    this.button(width - 96, 6, 'Tela cheia', () => {
      if (this.scale.isFullscreen) {
        this.scale.stopFullscreen();
        return;
      }
      this.scale.startFullscreen();
      const orientation = screen.orientation as ScreenOrientation & { lock?: (o: string) => Promise<void> };
      orientation.lock?.('landscape').catch(() => {
        /* nem todo navegador permite travar a orientação */
      });
    }).setAlpha(0.8);
  }

  // ------------------------------------------------------------ morte / ajuda

  private buildDeathBox(width: number, height: number) {
    const c = this.add.container(width / 2, height / 2 - 40).setVisible(false).setDepth(10);
    const g = this.add.graphics();
    g.fillStyle(0x10131f, 0.92).fillRoundedRect(-200, -50, 400, 110, 8);
    g.lineStyle(1, 0xb04848).strokeRoundedRect(-200, -50, 400, 110, 8);
    c.add(g);
    c.add(this.txt(0, -36, 'Você foi derrotado.', 16, '#ff8a8a', { fontStyle: 'bold' }).setOrigin(0.5, 0));
    c.add(this.txt(0, -8, 'Perde 1% da EXP de base, como no RO.', 12, '#dfe6ff').setOrigin(0.5, 0));
    c.add(this.button(0, 22, 'Voltar a Henesys (Enter)', () => this.game_.respawn()).setOrigin(0.5, 0));
    this.deathBox = c;
  }

  private buildHelp(width: number, height: number) {
    const c = this.add.container(width / 2, height / 2 - 30).setDepth(20);
    const g = this.add.graphics();
    g.fillStyle(0x10131f, 0.94).fillRoundedRect(-250, -175, 500, 350, 8);
    g.lineStyle(1, 0x6b7bb0).strokeRoundedRect(-250, -175, 500, 350, 8);
    c.add(g);
    c.add(this.txt(0, -162, 'Como jogar', 16, '#ffe680', { fontStyle: 'bold' }).setOrigin(0.5, 0));
    const touchLines = [
      ['Direcional', 'andar (toque no canto inferior esquerdo)'],
      ['Direcional ↑', 'entrar em portais, falar com NPCs, subir escadas'],
      ['Direcional ↓', 'descer escadas e cordas, deitar'],
      ['PULAR', 'pular  (↓ + PULAR desce de plataformas)'],
      ['ATACAR', 'atacar (segure para atacar sem parar)'],
      ['Q W E R', 'toque nos ícones para usar habilidades'],
      ['1 2 3 4', 'toque nas poções para usá-las'],
      ['Menus', 'Atributos, Habilidades, Itens na barra de baixo'],
      ['Tela cheia', 'botão no canto superior direito'],
      ['Ajuda', 'toque em Ajuda para ver esta tela de novo'],
    ];
    const keyLines = [
      ['← →', 'andar'],
      ['Espaço / Alt', 'pular  (↓ + Espaço desce de plataformas)'],
      ['↑ / ↓', 'subir/descer escadas e cordas'],
      ['↑', 'entrar em portais e falar com NPCs'],
      ['Z, X ou Ctrl', 'atacar (segure para atacar sem parar)'],
      ['Q W E R', 'usar habilidades'],
      ['1 2 3 4', 'usar poções'],
      ['S / K / I', 'atributos / habilidades / itens'],
      ['M', 'ligar/desligar o som'],
      ['H', 'mostrar/esconder esta ajuda'],
    ];
    const lines = isTouchDevice() ? touchLines : keyLines;
    lines.forEach(([k, v], i) => {
      c.add(this.txt(-225, -128 + i * 22, k, 12, '#9ac4ff', { fontStyle: 'bold' }));
      c.add(this.txt(-100, -128 + i * 22, v, 12, '#e8f0ff'));
    });
    c.add(
      this.txt(
        0,
        102,
        'Comece como Aprendiz. Com nível de classe 10 e Habilidades Básicas 9,\nfale com Cody em Henesys para virar Espadachim, Mago, Arqueiro ou Gatuno.\nMonstros passivos só atacam depois de provocados, como no RO.',
        11,
        '#c9d3f5',
        { align: 'center' },
      ).setOrigin(0.5, 0),
    );
    c.setInteractive(new Phaser.Geom.Rectangle(-250, -175, 500, 350), Phaser.Geom.Rectangle.Contains).on(
      'pointerdown',
      () => c.setVisible(false),
    );
    this.help = c;
  }
}
