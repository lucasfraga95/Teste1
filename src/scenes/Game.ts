import Phaser from 'phaser';
import { Combat, CombatHost } from '../combat/Combat';
import { AssetIndex, MapData, Portal } from '../data/types';
import { Mob } from '../entities/Mob';
import { Controls, Player } from '../entities/Player';
import { Character } from '../ro/character';
import { CLASSES, JobId } from '../ro/classes';
import { ITEMS, POTION_SLOTS, rollDrops } from '../ro/items';
import { HitResult, hpRegen, mobAttack, MOBS, spRegen } from '../ro/rules';
import { showDamage } from '../ui/damage';
import { Drops } from '../world/Drops';
import { Footholds } from '../world/footholds';
import { MapView } from '../world/MapView';
import { NPC_ROLES } from '../world/npcs';

interface GameInit {
  mapId?: number;
  portal?: string;
}

const INVINCIBLE_MS = 1500;
const SAVE_EVERY_MS = 5000;
const SKILL_KEYS = ['Q', 'W', 'E', 'R'];
const POTION_KEYS = ['ONE', 'TWO', 'THREE', 'FOUR'];

export class Game extends Phaser.Scene implements CombatHost {
  char!: Character;
  map!: MapView;
  player!: Player;
  mobs: Mob[] = [];
  combat!: Combat;
  private drops!: Drops;
  private keys!: Record<string, Phaser.Input.Keyboard.Key>;
  private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
  private target: GameInit = {};
  private changing = false;
  private nextHpRegen = 0;
  private nextSpRegen = 0;
  private nextSkillRegen = 0;
  private nextSave = 0;
  /** Diálogo aberto: bloqueia os controles do personagem. */
  dialogOpen = false;

  constructor() {
    super('Game');
  }

  init(data: GameInit) {
    this.target = data ?? {};
    this.changing = false;
    this.dialogOpen = false;
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
    this.addNpcTitles(data);

    const spawn = this.findSpawn(data, this.target.portal);
    this.player = new Player(this, this.map, spawn.x, spawn.y - 10, this.char.data.job);
    this.combat = new Combat(this, this);
    this.drops = new Drops(this, this.map);

    for (const m of data.mobs) {
      if (!MOBS[m.id] || !this.cache.json.has(`mob${m.id}`)) continue;
      const mob = new Mob(this, this.map, m.id, m.x, m.y, m.fh);
      mob.onPoison = (target, dmg) => showDamage(this, target.x, target.y - target.bodyRect.height - 10, dmg, 'NoRed1');
      this.mobs.push(mob);
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
        this.notice(`Você tem ${this.char.data.statPoints} pontos de atributo. Aperte S para distribuí-los.`, true),
      );
    }
    this.char.save();
  }

  private addNpcTitles(data: MapData) {
    for (const n of data.npcs) {
      const r = NPC_ROLES[n.id];
      if (!r) continue;
      this.add
        .text(n.x, n.y + 22, `[${r.title}]`, {
          fontFamily: 'Verdana, sans-serif',
          fontSize: '11px',
          color: '#9ff0a0',
          stroke: '#000000',
          strokeThickness: 3,
        })
        .setOrigin(0.5, 0)
        .setDepth(900);
    }
  }

  private setupInput() {
    const kb = this.input.keyboard!;
    this.cursors = kb.createCursorKeys();
    const K = Phaser.Input.Keyboard.KeyCodes;
    const codes: Record<string, number> = { alt: K.ALT, z: K.Z, x: K.X, ctrl: K.CTRL, enter: K.ENTER };
    for (const k of [...SKILL_KEYS, ...POTION_KEYS]) codes[k] = K[k as keyof typeof K];
    this.keys = kb.addKeys(codes) as Record<string, Phaser.Input.Keyboard.Key>;
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

  notice(msg: string, log = false) {
    this.game.events.emit(log ? 'log' : 'notice', msg);
  }

  update(time: number, deltaMs: number) {
    const dt = Math.min(deltaMs, 50) / 1000;
    const JD = Phaser.Input.Keyboard.JustDown;
    const c = this.readControls();

    if (this.player.dead) {
      if (JD(this.keys.enter)) this.respawn();
    } else if (!this.changing) {
      if (!this.dialogOpen) {
        if (c.attack) this.combat.basicAttack();
        SKILL_KEYS.forEach((k, i) => JD(this.keys[k]) && this.useSkillSlot(i));
        POTION_KEYS.forEach((k, i) => JD(this.keys[k]) && this.usePotionSlot(i));
        if (JD(this.cursors.up) && this.player.grounded && !this.tryPortal()) this.tryNpc();
      }
      this.player.update(dt, this.dialogOpen ? { left: false, right: false, up: false, down: false, jump: false, attack: false } : c);
      if (this.player.y > this.map.bounds.bottom + 300) this.teleportToSpawn();
      for (const id of this.drops.update(this.player.x, this.player.y, time)) this.pickUp(id);
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

  // ------------------------------------------------------------- ações

  useSkillSlot(i: number) {
    if (this.player.dead || this.dialogOpen) return;
    this.combat.useSkill(this.char.activeSkills[i]);
  }

  usePotionSlot(i: number) {
    this.useItem(POTION_SLOTS[i]);
  }

  useItem(id: number) {
    if (this.player.dead) return;
    const r = this.char.useItem(id);
    if (!r) {
      if (!this.char.count(id)) this.notice(`Você não tem ${ITEMS[id].name}.`);
      return;
    }
    if (r.hp) showDamage(this, this.player.x, this.player.y - 80, r.hp, 'heal');
    if (r.sp) showDamage(this, this.player.x, this.player.y - 100, r.sp, 'sp');
  }

  // ------------------------------------------------------------- combate

  applyHit(mob: Mob, r: HitResult, push: number, stack: number): boolean {
    const top = mob.y - mob.bodyRect.height - 10;
    if (r.miss) {
      showDamage(this, mob.x, top, 'MISS', 'NoRed1', stack);
      mob.takeHit(0, this.player.x, this.time.now, 0);
      return false;
    }
    showDamage(this, mob.x, top, r.damage, r.crit ? 'NoCri1' : 'NoRed1', stack);
    const died = mob.takeHit(r.damage, this.player.x, this.time.now, push);
    if (died) this.onMobKilled(mob);
    return died;
  }

  private onMobKilled(m: Mob) {
    const ev = this.char.gainExp(m.rules.baseExp, m.rules.jobExp);
    this.notice(`${m.name}: +${m.rules.baseExp} EXP de base, +${m.rules.jobExp} EXP de classe`, true);
    this.drops.spawn(rollDrops(m.id), m.x, m.y);
    const notices: string[] = [];
    if (ev.baseLevelUps) {
      notices.push(`Nível de base ${this.char.data.baseLevel}!`);
      this.notice('Você recebeu pontos de atributo. Aperte S para distribuí-los.', true);
    }
    if (ev.jobLevelUps) {
      notices.push(`Nível de classe ${this.char.data.jobLevel}!`);
      this.notice('Você recebeu um ponto de habilidade. Aperte K para usá-lo.', true);
      if (this.char.canChangeJob) this.notice('Você já pode mudar de classe! Fale com Cody em Henesys.', true);
    }
    if (notices.length) {
      this.levelUpEffect();
      this.notice(notices.join('   '));
      this.char.save();
    }
  }

  private pickUp(id: number) {
    this.char.addItem(id);
    this.notice(`Você obteve: ${ITEMS[id]?.name ?? id}`, true);
  }

  levelUpEffect() {
    this.combat.playFx('fx-levelup', this.player.x, this.player.y);
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
      if (p.casting) {
        p.interruptCast();
        this.notice('Conjuração interrompida!');
      }
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
    const ch = this.char;
    const d = ch.derived;
    const s = ch.totalStats;
    const data = ch.data;
    if (now >= this.nextHpRegen) {
      this.nextHpRegen = now + 6000;
      data.hp = Math.min(d.maxHp, data.hp + hpRegen(d, s));
    }
    if (now >= this.nextSpRegen) {
      this.nextSpRegen = now + 8000;
      data.sp = Math.min(d.maxSp, data.sp + spRegen(d, s));
    }
    // Recuperação de HP/SP (Espadachim/Mago): a cada 10s.
    if (now >= this.nextSkillRegen) {
      this.nextSkillRegen = now + 10000;
      const hpLv = ch.skillLevel('hprecovery');
      const spLv = ch.skillLevel('sprecovery');
      if (hpLv) data.hp = Math.min(d.maxHp, data.hp + 5 * hpLv + Math.floor((d.maxHp * hpLv) / 500));
      if (spLv) data.sp = Math.min(d.maxSp, data.sp + 3 * spLv + Math.floor((d.maxSp * spLv) / 500));
    }
    if (now >= this.nextSave) {
      this.nextSave = now + SAVE_EVERY_MS;
      ch.save();
    }
  }

  // ------------------------------------------------------------- NPCs

  private tryNpc(): boolean {
    const p = this.player;
    const npc = this.map.data.npcs.find((n) => NPC_ROLES[n.id] && Math.abs(n.x - p.x) < 60 && Math.abs(n.y - p.y) < 70);
    if (!npc) return false;
    const meta = this.cache.json.get(`npc${npc.id}`);
    this.dialogOpen = true;
    this.game.events.emit('npc-talk', { id: npc.id, name: meta?.name ?? '', ...NPC_ROLES[npc.id] });
    return true;
  }

  closeDialog() {
    this.dialogOpen = false;
  }

  changeJob(job: JobId) {
    if (!this.char.canChangeJob) return;
    this.char.changeJob(job);
    this.player.setJob(job);
    this.char.fullHeal();
    this.levelUpEffect();
    this.notice(`Parabéns! Agora você é ${CLASSES[job].name}!`);
    this.notice('Aperte K para ver suas novas habilidades.', true);
    this.char.save();
  }

  heal() {
    this.char.fullHeal();
    this.levelUpEffect();
  }

  // ------------------------------------------------------------- mapas

  private tryPortal(): boolean {
    const p = this.player;
    const portal = this.map.data.portals.find(
      (o) => (o.type === 2 || o.type === 10) && Math.abs(o.x - p.x) < 30 && Math.abs(o.y - p.y) < 60,
    );
    if (!portal) return false;
    const index = this.cache.json.get('index') as AssetIndex;
    if (portal.toMap === this.map.data.id) {
      const dest = this.map.data.portals.find((o) => o.name === portal.toName);
      if (dest) this.moveTo(dest.x, dest.y);
      return true;
    }
    if (!index.maps.includes(portal.toMap)) {
      this.notice('Este caminho ainda não está disponível.');
      return true;
    }
    this.sound.play('sfx-portal', { volume: 0.5 });
    this.changeMap(portal.toMap, portal.toName);
    return true;
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

  respawn() {
    if (!this.player.dead) return;
    this.char.deathPenalty();
    this.char.data.hp = Math.floor(this.char.derived.maxHp / 2);
    this.game.events.emit('revived');
    this.changeMap(100000000);
  }
}
