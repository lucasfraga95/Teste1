import Phaser from 'phaser';
import { AssetIndex, MapData, Portal } from '../data/types';
import { Mob } from '../entities/Mob';
import { Controls, Player } from '../entities/Player';
import { Character } from '../ro/character';
import { hpRegen, mobAttack, playerAttack, spRegen } from '../ro/rules';
import { showDamage } from '../ui/damage';
import { Footholds } from '../world/footholds';
import { MapView } from '../world/MapView';

interface GameInit {
  mapId?: number;
  portal?: string;
}

const INVINCIBLE_MS = 1500;
const SAVE_EVERY_MS = 5000;

export class Game extends Phaser.Scene {
  char!: Character;
  map!: MapView;
  player!: Player;
  mobs: Mob[] = [];
  private keys!: Record<string, Phaser.Input.Keyboard.Key>;
  private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
  private target: GameInit = {};
  private changing = false;
  private nextHpRegen = 0;
  private nextSpRegen = 0;
  private nextSave = 0;

  constructor() {
    super('Game');
  }

  init(data: GameInit) {
    this.target = data ?? {};
    this.changing = false;
    this.mobs = [];
  }

  create() {
    if (!this.registry.get('char')) this.registry.set('char', Character.load());
    this.char = this.registry.get('char');

    const index = this.cache.json.get('index') as AssetIndex;
    let mapId = this.target.mapId ?? this.char.data.mapId;
    if (!index.maps.includes(mapId)) mapId = index.maps[0];
    this.char.data.mapId = mapId;
    const data = this.cache.json.get(`map${mapId}`) as MapData;
    this.map = new MapView(this, data);

    const spawn = this.findSpawn(data, this.target.portal);
    this.player = new Player(this, this.map, spawn.x, spawn.y - 10);
    this.player.onAttackHit = () => this.resolvePlayerAttack();

    for (const m of data.mobs) {
      if (this.cache.json.has(`mob${m.id}`)) this.mobs.push(new Mob(this, this.map, m.id, m.x, m.y, m.fh));
    }

    const cam = this.cameras.main;
    const b = this.map.bounds;
    cam.setBounds(b.x, b.y, b.width, b.height);
    cam.startFollow(this.player.sprite, true, 0.12, 0.12, 0, 60);
    cam.setBackgroundColor('#88c0f0');
    cam.fadeIn(300);

    this.setupInput();
    this.playBgm(data);
    this.game.events.emit('map-enter', data);
    if (this.char.data.statPoints > 0 && !this.target.mapId) {
      this.time.delayedCall(800, () =>
        this.game.events.emit('log', `Você tem ${this.char.data.statPoints} pontos de atributo. Aperte S para distribuí-los.`),
      );
    }
    this.char.save();
  }

  private setupInput() {
    const kb = this.input.keyboard!;
    this.cursors = kb.createCursorKeys();
    this.keys = kb.addKeys({
      alt: Phaser.Input.Keyboard.KeyCodes.ALT,
      z: Phaser.Input.Keyboard.KeyCodes.Z,
      x: Phaser.Input.Keyboard.KeyCodes.X,
      ctrl: Phaser.Input.Keyboard.KeyCodes.CTRL,
      enter: Phaser.Input.Keyboard.KeyCodes.ENTER,
    }) as Record<string, Phaser.Input.Keyboard.Key>;
  }

  private playBgm(data: MapData) {
    const key = data.bgm ? `bgm${data.bgm}` : null;
    const current = this.registry.get('bgm') as Phaser.Sound.BaseSound | undefined;
    if (current && current.key === key) return;
    current?.stop();
    current?.destroy();
    if (!key) return;
    const music = this.sound.add(key, { loop: true, volume: 0.3 });
    music.play();
    this.registry.set('bgm', music);
  }

  private findSpawn(data: MapData, name?: string): Portal {
    return (
      (name && data.portals.find((p) => p.name === name)) ||
      data.portals.find((p) => p.name === 'sp') ||
      data.portals[0]
    );
  }

  update(time: number, deltaMs: number) {
    const dt = Math.min(deltaMs, 50) / 1000;
    const c = this.readControls();

    if (this.player.dead) {
      if (Phaser.Input.Keyboard.JustDown(this.keys.enter)) this.respawn();
    } else if (!this.changing) {
      if (c.attack) this.player.tryAttack(this.char.derived.attackDelay);
      if (Phaser.Input.Keyboard.JustDown(this.cursors.up) && this.player.grounded) this.tryPortal();
      this.player.update(dt, c);
      if (this.player.y > this.map.bounds.bottom + 300) this.teleportToSpawn();
    }

    for (const m of this.mobs) m.update(dt, time, this.player);
    this.resolveMobAttacks(time);
    this.map.update(this.cameras.main, dt);
    this.tickRegen(time);
  }

  private readControls(): Controls {
    const k = this.keys;
    return {
      left: this.cursors.left.isDown,
      right: this.cursors.right.isDown,
      up: this.cursors.up.isDown,
      down: this.cursors.down.isDown,
      jump: Phaser.Input.Keyboard.JustDown(this.cursors.space) || Phaser.Input.Keyboard.JustDown(k.alt),
      attack: k.z.isDown || k.x.isDown || k.ctrl.isDown,
    };
  }

  // ------------------------------------------------------------- combate

  private resolvePlayerAttack() {
    const p = this.player;
    if (p.dead) return;
    const reach = new Phaser.Geom.Rectangle(p.facing === 1 ? p.x - 10 : p.x - 85, p.y - 70, 95, 80);
    let best: Mob | null = null;
    let bestDist = Infinity;
    for (const m of this.mobs) {
      if (!m.alive || !Phaser.Geom.Intersects.RectangleToRectangle(reach, m.bodyRect)) continue;
      const d = Math.abs(m.x - p.x);
      if (d < bestDist) {
        best = m;
        bestDist = d;
      }
    }
    this.sound.play('sfx-swing', { volume: 0.35 });
    if (!best) return;

    const r = playerAttack(this.char.data.baseLevel, this.char.totalStats, this.char.derived, best.rules);
    const top = best.y - best.bodyRect.height - 10;
    if (r.miss) {
      showDamage(this, best.x, top, 'MISS', 'NoRed1');
      best.takeHit(0, p.x, this.time.now);
      return;
    }
    showDamage(this, best.x, top, r.damage, r.crit ? 'NoCri1' : 'NoRed1');
    if (best.takeHit(r.damage, p.x, this.time.now)) this.onMobKilled(best);
  }

  private onMobKilled(m: Mob) {
    const ev = this.char.gainExp(m.rules.baseExp, m.rules.jobExp);
    this.game.events.emit('log', `${m.name} derrotado: +${m.rules.baseExp} EXP de base, +${m.rules.jobExp} EXP de classe`);
    const notices: string[] = [];
    if (ev.baseLevelUps) {
      notices.push(`Nível de base ${this.char.data.baseLevel}!`);
      this.game.events.emit('log', `Você recebeu pontos de atributo. Aperte S para distribuí-los.`);
    }
    if (ev.jobLevelUps) {
      notices.push(`Nível de classe ${this.char.data.jobLevel}!`);
      if (this.char.jobMaxed) this.game.events.emit('log', 'Nível de classe máximo! Mudança de classe chega na próxima versão.');
    }
    if (notices.length) {
      this.levelUpEffect();
      this.game.events.emit('notice', notices.join('   '));
    }
    if (ev.baseLevelUps || ev.jobLevelUps) this.char.save();
  }

  private levelUpEffect() {
    const meta = this.cache.json.get('fx-levelup');
    const s = this.add.sprite(this.player.x, this.player.y, 'fx-levelup');
    s.setOrigin(meta.originX / meta.frameWidth, meta.originY / meta.frameHeight).setDepth(8000);
    s.play({ key: 'fx-levelup:levelup', repeat: 0 });
    s.once('animationcomplete', () => s.destroy());
    this.sound.play('sfx-levelup', { volume: 0.5 });
  }

  private resolveMobAttacks(now: number) {
    const p = this.player;
    if (p.dead || this.changing) return;
    const body = p.bodyRect;
    for (const m of this.mobs) {
      if (!m.canAttack(now) || !Phaser.Geom.Intersects.RectangleToRectangle(body, m.bodyRect)) continue;
      m.didAttack(now);
      if (now < p.invincibleUntil) continue;
      const r = mobAttack(m.rules, this.char.derived, this.char.totalStats);
      if (r.miss) {
        showDamage(this, p.x, p.y - 75, 'MISS', 'NoViolet1');
        continue;
      }
      showDamage(this, p.x, p.y - 75, r.damage, 'NoViolet1');
      this.char.data.hp = Math.max(0, this.char.data.hp - r.damage);
      p.invincibleUntil = now + INVINCIBLE_MS;
      if (this.char.data.hp <= 0) {
        p.die();
        this.game.events.emit('dead');
        return;
      }
      p.knockback(m.x);
    }
  }

  private tickRegen(now: number) {
    if (this.player.dead) return;
    const d = this.char.derived;
    const s = this.char.totalStats;
    const data = this.char.data;
    if (now >= this.nextHpRegen) {
      this.nextHpRegen = now + 6000;
      data.hp = Math.min(d.maxHp, data.hp + hpRegen(d, s));
    }
    if (now >= this.nextSpRegen) {
      this.nextSpRegen = now + 8000;
      data.sp = Math.min(d.maxSp, data.sp + spRegen(d, s));
    }
    if (now >= this.nextSave) {
      this.nextSave = now + SAVE_EVERY_MS;
      this.char.save();
    }
  }

  // ------------------------------------------------------------- mapas

  private tryPortal() {
    const p = this.player;
    const portal = this.map.data.portals.find(
      (o) => (o.type === 2 || o.type === 10) && Math.abs(o.x - p.x) < 30 && Math.abs(o.y - p.y) < 60,
    );
    if (!portal) return;
    const index = this.cache.json.get('index') as AssetIndex;
    if (portal.toMap === this.map.data.id) {
      const dest = this.map.data.portals.find((o) => o.name === portal.toName);
      if (dest) this.moveTo(dest.x, dest.y);
      return;
    }
    if (!index.maps.includes(portal.toMap)) {
      this.game.events.emit('notice', 'Este caminho ainda não está disponível.');
      return;
    }
    this.sound.play('sfx-portal', { volume: 0.5 });
    this.changeMap(portal.toMap, portal.toName);
  }

  private moveTo(x: number, y: number) {
    this.sound.play('sfx-portal', { volume: 0.5 });
    const fh = this.map.fh.below(x, y - 20, 300);
    this.player.x = x;
    this.player.y = fh ? Footholds.yAt(fh, x) : y;
    this.player.fh = fh;
    this.player.ladder = null;
  }

  private teleportToSpawn() {
    const sp = this.findSpawn(this.map.data);
    this.moveTo(sp.x, sp.y);
  }

  changeMap(mapId: number, portal?: string) {
    if (this.changing) return;
    this.changing = true;
    this.char.data.mapId = mapId;
    this.char.save();
    this.cameras.main.fadeOut(250, 0, 0, 0);
    this.cameras.main.once('camerafadeoutcomplete', () => this.scene.restart({ mapId, portal }));
  }

  private respawn() {
    this.char.deathPenalty();
    this.char.data.hp = Math.floor(this.char.derived.maxHp / 2);
    this.game.events.emit('revived');
    const town = this.map.data.returnMap && this.map.data.returnMap !== 999999999 ? this.map.data.returnMap : 100000000;
    this.changeMap(town);
  }
}
