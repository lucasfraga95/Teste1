// Jogador: movimento estilo MapleStory sobre as plataformas do mapa.
import Phaser from 'phaser';
import { SheetMeta, Ladder } from '../data/types';
import { Foothold, Footholds } from '../world/footholds';
import { depthFor, MapView } from '../world/MapView';

const WALK_SPEED = 125;
const JUMP_SPEED = 555;
const GRAVITY = 2000;
const MAX_FALL = 670;
const CLIMB_SPEED = 100;
const AIR_ACCEL = 350;

export interface Controls {
  left: boolean;
  right: boolean;
  up: boolean;
  down: boolean;
  jump: boolean; // apertou agora
  attack: boolean; // segurando
}

const ATTACK_ANIMS = ['swingO1', 'swingO2', 'swingO3', 'stabO1'];

export class Player {
  readonly sprite: Phaser.GameObjects.Sprite;
  x: number;
  y: number;
  vx = 0;
  vy = 0;
  fh: Foothold | null = null;
  facing: -1 | 1 = -1;
  ladder: Ladder | null = null;
  dead = false;
  invincibleUntil = 0;
  private attackUntil = 0;
  private nextAttackAt = 0;
  private alertUntil = 0;
  private dropIgnore: Foothold | null = null;
  private dropUntil = 0;
  private meta: SheetMeta;
  private layer = 0;

  /** Chamado no meio do golpe para resolver o acerto. */
  onAttackHit?: () => void;

  constructor(private scene: Phaser.Scene, private map: MapView, x: number, y: number) {
    this.meta = scene.cache.json.get('char');
    this.sprite = scene.add.sprite(x, y, 'char');
    this.sprite.setOrigin(this.meta.originX / this.meta.frameWidth, this.meta.originY / this.meta.frameHeight);
    this.x = x;
    this.y = y;
    const below = map.fh.below(x, y - 20, 2000);
    if (below) {
      this.fh = below;
      this.y = Footholds.yAt(below, x);
    }
    this.play('stand1');
  }

  get grounded() {
    return this.fh !== null;
  }

  get attacking() {
    return this.scene.time.now < this.attackUntil;
  }

  /** Caixa usada para ser atingido por monstros. */
  get bodyRect() {
    return new Phaser.Geom.Rectangle(this.x - 14, this.y - 60, 28, 60);
  }

  private play(anim: string, once = false) {
    const key = `char:${anim}`;
    if (once) {
      this.sprite.play({ key, repeat: 0 });
    } else if (this.sprite.anims.currentAnim?.key !== key || !this.sprite.anims.isPlaying) {
      this.sprite.play(key);
    }
  }

  private animDuration(anim: string) {
    return this.meta.anims[anim].delays.reduce((a, b) => a + b, 0);
  }

  /** Inicia um ataque básico se possível. `delay` vem do ASPD do RO. */
  tryAttack(aspdDelay: number): boolean {
    const now = this.scene.time.now;
    if (this.dead || this.ladder || now < this.nextAttackAt) return false;
    const anim = this.fh && this.isProne ? 'proneStab' : Phaser.Utils.Array.GetRandom(ATTACK_ANIMS);
    const dur = this.animDuration(anim);
    this.attackUntil = now + dur;
    this.nextAttackAt = now + Math.max(dur, aspdDelay);
    this.alertUntil = now + 2500;
    this.play(anim, true);
    this.scene.time.delayedCall(Math.min(dur * 0.45, 250), () => this.onAttackHit?.());
    return true;
  }

  private isProne = false;

  update(dt: number, c: Controls) {
    const now = this.scene.time.now;
    if (this.dead) return;
    const fh = this.map.fh;

    if (this.ladder) {
      this.updateLadder(dt, c);
    } else if (this.fh) {
      this.isProne = c.down && !this.attacking;
      let dir = 0;
      if (!this.attacking && !this.isProne) dir = (c.right ? 1 : 0) - (c.left ? 1 : 0);
      if (dir) this.facing = dir as -1 | 1;
      this.vx = dir * WALK_SPEED;

      if (c.down && this.tryGrabLadder(true)) {
        // desceu para a escada
      } else if (c.up && this.tryGrabLadder(false)) {
        // subiu na escada
      } else if (c.jump && !this.attacking) {
        if (c.down && fh.below(this.x, this.y + 4, 1500, this.fh)) {
          this.dropIgnore = this.fh;
          this.dropUntil = now + 350;
          this.fh = null;
          this.vy = 0;
        } else {
          this.fh = null;
          this.vy = -JUMP_SPEED;
          this.scene.sound.play('sfx-jump', { volume: 0.4 });
        }
        this.isProne = false;
      }
      if (this.fh) {
        const m = fh.walk(this.fh, this.x + this.vx * dt);
        this.x = m.x;
        this.y = m.y;
        this.fh = m.fh;
        if (!this.fh) this.vy = 0;
      }
    } else {
      this.isProne = false;
      const dir = (c.right ? 1 : 0) - (c.left ? 1 : 0);
      if (dir) {
        this.vx = Phaser.Math.Clamp(this.vx + dir * AIR_ACCEL * dt, -WALK_SPEED, WALK_SPEED);
        if (!this.attacking) this.facing = dir as -1 | 1;
      }
      if (c.up) this.tryGrabLadder(false);
    }

    if (!this.fh && !this.ladder) this.updateAir(dt, now);

    // Limites horizontais do mapa.
    this.x = Phaser.Math.Clamp(this.x, fh.left + 10, fh.right - 10);
    this.updateSprite(now);
  }

  private updateAir(dt: number, now: number) {
    const fh = this.map.fh;
    this.vy = Math.min(this.vy + GRAVITY * dt, MAX_FALL);
    let nx = this.x + this.vx * dt;
    const block = fh.wallBlock(this.x, nx, this.y);
    if (block !== null) {
      nx = block;
      this.vx = 0;
    }
    const ny = this.y + this.vy * dt;
    const ignore = now < this.dropUntil ? this.dropIgnore : null;
    const land = this.vy >= 0 ? fh.landing(nx, this.y, ny, ignore) : null;
    this.x = nx;
    if (land) {
      this.fh = land;
      this.y = Footholds.yAt(land, nx);
      this.vy = 0;
      this.vx = 0;
    } else {
      this.y = ny;
    }
  }

  private tryGrabLadder(fromTop: boolean): boolean {
    for (const l of this.map.data.ladders) {
      if (Math.abs(this.x - l.x) > 14) continue;
      const ok = fromTop
        ? this.fh && Math.abs(this.y - l.y1) < 14
        : this.y > l.y1 + 6 && this.y - 60 <= l.y2;
      if (!ok) continue;
      this.ladder = l;
      this.fh = null;
      this.x = l.x;
      this.vx = 0;
      this.vy = 0;
      if (fromTop) this.y = l.y1 + 8;
      this.y = Math.min(this.y, l.y2);
      return true;
    }
    return false;
  }

  private updateLadder(dt: number, c: Controls) {
    const l = this.ladder!;
    const dir = (c.down ? 1 : 0) - (c.up ? 1 : 0);
    this.y += dir * CLIMB_SPEED * dt;
    const anim = l.ladder ? 'ladder' : 'rope';
    this.play(anim);
    if (dir) this.sprite.anims.resume();
    else this.sprite.anims.pause();

    if (c.jump && (c.left || c.right)) {
      this.ladder = null;
      this.facing = c.right ? 1 : -1;
      this.vx = this.facing * WALK_SPEED * 0.8;
      this.vy = -JUMP_SPEED * 0.55;
      this.sprite.anims.resume();
      return;
    }
    if (this.y < l.y1) {
      const top = this.map.fh.below(this.x, l.y1 - 10, 40);
      this.ladder = null;
      this.sprite.anims.resume();
      if (top) {
        this.fh = top;
        this.y = Footholds.yAt(top, this.x);
      }
    } else if (this.y > l.y2) {
      this.ladder = null;
      this.sprite.anims.resume();
      this.vy = 0;
    }
  }

  private updateSprite(now: number) {
    this.sprite.setPosition(Math.round(this.x), Math.round(this.y));
    this.sprite.setFlipX(this.facing === 1);
    const layer = this.fh?.layer ?? this.layer;
    this.layer = layer;
    // Em escadas e cordas fica na frente de todas as camadas.
    this.sprite.setDepth(this.ladder ? depthFor(7) + 5 : depthFor(layer) + 5);
    const blink = now < this.invincibleUntil && Math.floor(now / 80) % 2 === 0;
    this.sprite.setAlpha(blink ? 0.4 : 1);

    if (this.ladder || this.attacking) return;
    if (!this.fh) this.play('jump');
    else if (this.isProne) this.play('prone');
    else if (this.vx !== 0) this.play('walk1');
    else this.play(now < this.alertUntil ? 'alert' : 'stand1');
  }

  /** Empurrão ao levar dano. */
  knockback(fromX: number) {
    if (this.ladder) return;
    const dir = this.x < fromX ? -1 : 1;
    this.fh = null;
    this.vx = dir * 140;
    this.vy = -260;
  }

  die() {
    this.dead = true;
    this.ladder = null;
    this.sprite.play('char:prone');
    this.sprite.anims.pause();
    this.sprite.setTint(0x777777);
  }

  setLayerFrom(map: MapView) {
    this.layer = map.layerAt(this.x, this.y);
  }
}
