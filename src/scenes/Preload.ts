import Phaser from 'phaser';
import { AssetIndex, MapData, SheetMeta } from '../data/types';
import { SKILLS } from '../ro/skills';

const A = 'assets/';

/** Cria as animações de uma folha gerada pelo script de assets. */
export function createSheetAnims(scene: Phaser.Scene, key: string, meta: SheetMeta) {
  for (const [name, a] of Object.entries(meta.anims)) {
    const animKey = `${key}:${name}`;
    if (scene.anims.exists(animKey)) continue;
    scene.anims.create({
      key: animKey,
      frames: a.delays.map((d, i) => ({ key, frame: a.start + i, duration: d })),
      frameRate: 1000 / 100,
      repeat: -1,
    });
  }
}

/** Carrega todos os JSONs e depois todas as imagens e sons. */
export class Preload extends Phaser.Scene {
  constructor() {
    super('Preload');
  }

  preload() {
    this.drawProgress();
    this.load.json('index', A + 'index.json');
    this.load.json('digits', A + 'fx/digits.json');
    this.load.json('fx-portal', A + 'fx/portal.json');
    this.load.json('fx-levelup', A + 'fx/levelup.json');
    this.load.json('fx-arrow', A + 'fx/arrow.json');
  }

  create() {
    const index = this.cache.json.get('index') as AssetIndex;
    for (const id of index.maps) this.load.json(`map${id}`, `${A}maps/${id}/map.json`);
    for (const id of index.mobs) this.load.json(`mob${id}`, `${A}mobs/${id}.json`);
    for (const job of index.classes) this.load.json(`char-${job}`, `${A}char/${job}.json`);
    for (const key of index.skillFx) this.load.json(key, `${A}fx/${key}.json`);
    this.load.once('complete', () => this.loadMedia(index));
    this.load.start();
  }

  private loadMedia(index: AssetIndex) {
    const sheet = (key: string, url: string, meta: SheetMeta) =>
      this.load.spritesheet(key, url, { frameWidth: meta.frameWidth, frameHeight: meta.frameHeight });

    for (const job of index.classes) sheet(`char-${job}`, `${A}char/${job}.png`, this.cache.json.get(`char-${job}`));
    for (const key of index.skillFx) sheet(key, `${A}fx/${key}.png`, this.cache.json.get(key));
    sheet('fx-arrow', A + 'fx/arrow.png', this.cache.json.get('fx-arrow'));
    for (const id of index.items) this.load.image(`icon-item-${id}`, `${A}icons/item_${id}.png`);
    for (const id of Object.keys(SKILLS)) this.load.image(`icon-skill-${id}`, `${A}icons/skill_${id}.png`);
    this.load.image('icon-meso', A + 'icons/meso.png');
    sheet('fx-portal', A + 'fx/portal.png', this.cache.json.get('fx-portal'));
    sheet('fx-levelup', A + 'fx/levelup.png', this.cache.json.get('fx-levelup'));
    const digits = this.cache.json.get('digits') as Record<string, { frameWidth: number; frameHeight: number }>;
    for (const [style, d] of Object.entries(digits)) {
      this.load.spritesheet(`dmg-${style}`, `${A}fx/${style}.png`, d);
    }

    const npcs = new Set<number>();
    // Camadas, fundos e música de cada mapa são carregados só ao entrar nele (Game.preload).
    for (const id of index.maps) {
      const m = this.cache.json.get(`map${id}`) as MapData;
      for (const n of m.npcs) npcs.add(n.id);
    }
    for (const id of npcs) this.load.json(`npc${id}`, `${A}npcs/${id}.json`);
    for (const id of index.mobs) {
      sheet(`mob${id}`, `${A}mobs/${id}.png`, this.cache.json.get(`mob${id}`));
      this.load.audio(`mob${id}-hit`, `${A}sfx/mob${id}_Damage.mp3`);
      this.load.audio(`mob${id}-die`, `${A}sfx/mob${id}_Die.mp3`);
    }
    for (const s of ['jump', 'portal', 'levelup', 'swing']) {
      this.load.audio(`sfx-${s}`, `${A}sfx/${s}.mp3`);
    }

    // NPCs dependem dos próprios JSONs: terceira etapa.
    this.load.once('complete', () => {
      for (const id of npcs) {
        const meta = this.cache.json.get(`npc${id}`) as SheetMeta | undefined;
        if (meta) sheet(`npc${id}`, `${A}npcs/${id}.png`, meta);
      }
      this.load.once('complete', () => this.finish(index, npcs));
      this.load.start();
    });
    this.load.start();
  }

  private finish(index: AssetIndex, npcs: Set<number>) {
    for (const job of index.classes) createSheetAnims(this, `char-${job}`, this.cache.json.get(`char-${job}`));
    for (const key of [...index.skillFx, 'fx-arrow']) createSheetAnims(this, key, this.cache.json.get(key));
    createSheetAnims(this, 'fx-portal', this.cache.json.get('fx-portal'));
    createSheetAnims(this, 'fx-levelup', this.cache.json.get('fx-levelup'));
    for (const id of index.mobs) createSheetAnims(this, `mob${id}`, this.cache.json.get(`mob${id}`));
    for (const id of npcs) {
      const meta = this.cache.json.get(`npc${id}`);
      if (meta && this.textures.exists(`npc${id}`)) createSheetAnims(this, `npc${id}`, meta);
    }
    this.scene.start('Game');
    this.scene.launch('UI');
  }

  private drawProgress() {
    const { width, height } = this.scale;
    const bar = this.add.graphics();
    const label = this.add
      .text(width / 2, height / 2 - 30, 'Carregando Midgard...', {
        fontFamily: 'Verdana, sans-serif',
        fontSize: '16px',
        color: '#ffffff',
      })
      .setOrigin(0.5);
    this.load.on('progress', (p: number) => {
      bar.clear();
      bar.fillStyle(0x333a55).fillRect(width / 2 - 160, height / 2, 320, 12);
      bar.fillStyle(0xf2c14e).fillRect(width / 2 - 160, height / 2, 320 * p, 12);
    });
    this.events.once('shutdown', () => label.destroy());
  }
}
