// Monstro: visual do MapleStory, atributos e comportamento do RO.
import Phaser from 'phaser';
import { MobMeta } from '../data/types';
import { MobRules, MOBS } from '../ro/rules';
import { Foothold, Footholds } from '../world/footholds';
import { depthFor, MapView } from '../world/MapView';

type State = 'stand' | 'move' | 'hit' | 'die' | 'dead';

const RESPAWN_MS = 7000;
const AGGRO_TIMEOUT = 12000;

export class Mob {
  readonly sprite: Phaser.GameObjects.Sprite;
  readonly rules: MobRules;
  readonly meta: MobMeta;
  private hpBar: Phaser.GameObjects.Graphics;
  x: number;
  y: number;
  fh: Foothold | null;
  dir: -1 | 1 = -1;
  hp: number;
  state: State = 'stand';
  aggroUntil = 0;
  nextAttackAt = 0;
  private stateUntil = 0;
  private speed: number;

  constructor(
    private scene: Phaser.Scene,
    private map: MapView,
    readonly id: number,
    private spawnX: number,
    private spawnY: number,
    private spawnFh: number,
  ) {
    this.meta = scene.cache.json.get(`mob${id}`);
    this.rules = MOBS[id];
    this.hp = this.rules.hp;
    // Velocidade do Maple: speed é um percentual relativo (-100..+100).
    this.speed = Math.max(15, 70 * (1 + this.meta.speed / 100));
    this.sprite = scene.add.sprite(spawnX, spawnY, `mob${id}`);
    this.sprite.setOrigin(this.meta.originX / this.meta.frameWidth, this.meta.originY / this.meta.frameHeight);
    this.hpBar = scene.add.graphics();
    this.x = spawnX;
    this.y = spawnY;
    this.fh = null;
    this.spawn();
  }

  get alive() {
    return this.state !== 'die' && this.state !== 'dead';
  }

  get name() {
    return this.meta.name;
  }

  /** Caixa de colisão (a partir do tamanho do quadro e da origem). */
  get bodyRect() {
    const w = Math.min(this.meta.frameWidth, 70) * 0.7;
    const h = Math.min(this.meta.originY, 70);
    return new Phaser.Geom.Rectangle(this.x - w / 2, this.y - h, w, h);
  }

  private spawn() {
    this.hp = this.rules.hp;
    this.x = this.spawnX;
    this.fh = this.map.fh.get(this.spawnFh) ?? this.map.fh.below(this.spawnX, this.spawnY - 20, 500);
    this.y = this.fh ? Footholds.yAt(this.fh, this.x) : this.spawnY;
    this.state = 'stand';
    this.aggroUntil = 0;
    this.dir = Math.random() < 0.5 ? -1 : 1;
    this.sprite.setVisible(true).setAlpha(0);
    this.scene.tweens.add({ targets: this.sprite, alpha: 1, duration: 400 });
    this.play('stand');
  }

  private play(anim: string, once = false) {
    const key = `mob${this.id}:${anim in this.meta.anims ? anim : 'stand'}`;
    if (once) this.sprite.play({ key, repeat: 0 });
    else if (this.sprite.anims.currentAnim?.key !== key) this.sprite.play(key);
  }

  update(dt: number, now: number, target: { x: number; y: number; dead: boolean }) {
    if (this.state === 'dead') return;
    if (this.state === 'die') {
      this.draw();
      return;
    }
    const aggro = now < this.aggroUntil && !target.dead;

    if (this.state === 'hit') {
      if (now >= this.stateUntil) this.state = 'stand';
    } else if (aggro && Math.abs(target.y - this.y) < 80) {
      const dx = target.x - this.x;
      if (Math.abs(dx) > 18) {
        this.dir = dx > 0 ? 1 : -1;
        this.state = 'move';
      } else {
        this.state = 'stand';
      }
    } else if (now >= this.stateUntil) {
      // Vaga pelo mapa como no MapleStory.
      this.state = Math.random() < 0.55 ? 'move' : 'stand';
      if (Math.random() < 0.5) this.dir = this.dir === 1 ? -1 : 1;
      this.stateUntil = now + Phaser.Math.Between(1200, 3500);
    }

    if (this.state === 'move' && this.fh) {
      const sp = aggro ? this.speed * 1.5 : this.speed;
      const m = this.map.fh.walk(this.fh, this.x + this.dir * sp * dt);
      if (!m.fh || m.blocked) {
        this.dir = this.dir === 1 ? -1 : 1;
        if (!aggro) this.state = 'stand';
      } else {
        this.x = m.x;
        this.y = m.y;
        this.fh = m.fh;
      }
    }

    if (this.state !== 'hit') this.play(this.state === 'move' ? 'move' : 'stand');
    this.draw();
  }

  private draw() {
    this.sprite.setPosition(Math.round(this.x), Math.round(this.y));
    this.sprite.setFlipX(this.dir === 1);
    const depth = depthFor(this.fh?.layer ?? 0);
    this.sprite.setDepth(depth);
    this.hpBar.clear();
    if (this.alive && this.hp < this.rules.hp) {
      const w = 40;
      const x = Math.round(this.x - w / 2);
      const y = Math.round(this.y + 4);
      this.hpBar.fillStyle(0x10131c, 0.9).fillRect(x - 1, y - 1, w + 2, 6);
      this.hpBar.fillStyle(0x3ccf4e).fillRect(x, y, Math.ceil((w * this.hp) / this.rules.hp), 4);
      this.hpBar.setDepth(depth + 1);
    }
  }

  /** Recebe dano. Retorna true se morreu. */
  takeHit(damage: number, fromX: number, now: number): boolean {
    if (!this.alive) return false;
    this.aggroUntil = now + AGGRO_TIMEOUT;
    this.nextAttackAt = Math.max(this.nextAttackAt, now + 400);
    this.hp -= damage;
    if (this.hp <= 0) {
      this.hp = 0;
      this.die();
      return true;
    }
    this.scene.sound.play(`mob${this.id}-hit`, { volume: 0.4 });
    this.dir = fromX > this.x ? 1 : -1;
    this.state = 'hit';
    this.stateUntil = now + 450;
    this.play('hit1', true);
    if (this.fh) {
      const m = this.map.fh.walk(this.fh, this.x - this.dir * 12);
      if (m.fh && !m.blocked) {
        this.x = m.x;
        this.y = m.y;
        this.fh = m.fh;
      }
    }
    return false;
  }

  private die() {
    this.state = 'die';
    this.hpBar.clear();
    this.scene.sound.play(`mob${this.id}-die`, { volume: 0.4 });
    this.play('die1', true);
    this.sprite.once('animationcomplete', () => {
      this.scene.tweens.add({
        targets: this.sprite,
        alpha: 0,
        duration: 300,
        onComplete: () => {
          this.state = 'dead';
          this.sprite.setVisible(false);
          this.scene.time.delayedCall(RESPAWN_MS, () => this.spawn());
        },
      });
    });
  }

  /** Pode atacar quem está encostado nele? (só se provocado, como no RO) */
  canAttack(now: number) {
    return this.alive && this.state !== 'hit' && now < this.aggroUntil && now >= this.nextAttackAt;
  }

  didAttack(now: number) {
    this.nextAttackAt = now + this.rules.attackDelay;
  }
}
