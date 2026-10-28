// Ataques básicos e habilidades do jogador.
import Phaser from 'phaser';
import { SheetMeta } from '../data/types';
import { Mob } from '../entities/Mob';
import { Player } from '../entities/Player';
import { Character } from '../ro/character';
import { HitResult, magicAttack, physicalAttack, PhysicalOpts } from '../ro/rules';
import { SKILLS, SkillDef } from '../ro/skills';

const MELEE_REACH = 95;
const BOW_RANGE = 360;
const FX_DEPTH = 7000;

export interface CombatHost {
  char: Character;
  player: Player;
  mobs: Mob[];
  /** Aplica um acerto já calculado; retorna true se o monstro morreu. */
  applyHit(mob: Mob, r: HitResult, push: number, stack: number): boolean;
  notice(msg: string): void;
}

export class Combat {
  private readyAt = new Map<string, number>();

  constructor(private scene: Phaser.Scene, private host: CombatHost) {}

  private get p() {
    return this.host.player;
  }

  private get c() {
    return this.host.char;
  }

  cooldownLeft(id: string) {
    return Math.max(0, (this.readyAt.get(id) ?? 0) - this.scene.time.now);
  }

  // ------------------------------------------------------------ alvos

  /** Monstro mais próximo à frente, dentro do alcance. */
  private frontTarget(range: number, maxDy = 90): Mob | null {
    let best: Mob | null = null;
    let bestDist = Infinity;
    for (const m of this.host.mobs) {
      if (!m.alive) continue;
      const dx = (m.x - this.p.x) * this.p.facing;
      if (dx < -15 || dx > range || Math.abs(m.y - this.p.y) > maxDy) continue;
      if (dx < bestDist) {
        best = m;
        bestDist = dx;
      }
    }
    return best;
  }

  private meleeTarget(): Mob | null {
    const p = this.p;
    const reach = new Phaser.Geom.Rectangle(p.facing === 1 ? p.x - 10 : p.x - MELEE_REACH + 10, p.y - 70, MELEE_REACH, 80);
    let best: Mob | null = null;
    let bestDist = Infinity;
    for (const m of this.host.mobs) {
      if (!m.alive || !Phaser.Geom.Intersects.RectangleToRectangle(reach, m.bodyRect)) continue;
      const d = Math.abs(m.x - p.x);
      if (d < bestDist) {
        best = m;
        bestDist = d;
      }
    }
    return best;
  }

  private mobsNear(x: number, y: number, r: number): Mob[] {
    return this.host.mobs.filter((m) => m.alive && Math.abs(m.x - x) <= r && Math.abs(m.y - y) <= 80);
  }

  private get bowRange() {
    return BOW_RANGE + 25 * this.c.skillLevel('vultureseye');
  }

  // ------------------------------------------------------------ efeitos

  playFx(key: string | undefined, x: number, y: number, flip = false) {
    if (!key || !this.scene.textures.exists(key)) return;
    const meta = this.scene.cache.json.get(key) as SheetMeta;
    const s = this.scene.add.sprite(x, y, key).setDepth(FX_DEPTH).setFlipX(flip);
    s.setOrigin(meta.originX / meta.frameWidth, meta.originY / meta.frameHeight);
    s.play({ key: `${key}:${Object.keys(meta.anims)[0]}`, repeat: 0 });
    s.once('animationcomplete', () => s.destroy());
  }

  /** Projétil do jogador até o monstro; `onArrive` resolve o acerto. */
  private projectile(key: string, target: Mob, onArrive: () => void) {
    const sx = this.p.x + this.p.facing * 20;
    const sy = this.p.y - 38;
    const tx = target.x;
    const ty = target.y - Math.min(30, target.bodyRect.height / 2);
    const meta = this.scene.cache.json.get(key) as SheetMeta | undefined;
    const s = this.scene.add.sprite(sx, sy, key).setDepth(FX_DEPTH);
    if (meta) {
      s.setOrigin(meta.originX / meta.frameWidth, meta.originY / meta.frameHeight);
      const anim = Object.keys(meta.anims)[0];
      s.play(`${key}:${anim}`);
    }
    // Os sprites do Maple apontam para a esquerda.
    s.setFlipX(tx > sx);
    s.setRotation(Math.atan2(ty - sy, tx - sx) - (tx > sx ? 0 : Math.PI));
    const dur = Math.max(80, Phaser.Math.Distance.Between(sx, sy, tx, ty) / 0.8);
    this.scene.tweens.add({
      targets: s,
      x: tx,
      y: ty,
      duration: dur,
      onComplete: () => {
        s.destroy();
        onArrive();
      },
    });
  }

  private hitPhysical(m: Mob, o: PhysicalOpts, push = 12, stack = 0) {
    if (!m.alive) return false;
    const r = physicalAttack(this.c.totalStats, this.c.derived, this.c.cls.weapon, m.rules, o);
    return this.host.applyHit(m, r, push, stack);
  }

  // ------------------------------------------------------------ ataque básico

  basicAttack() {
    const cls = this.c.cls;
    const p = this.p;
    if (!p.ready) return;
    if (cls.ranged) {
      const target = this.frontTarget(this.bowRange);
      p.act(cls.attackAnims, this.c.derived.attackDelay, () => {
        this.scene.sound.play('sfx-swing', { volume: 0.3 });
        if (target) this.projectile('fx-arrow', target, () => this.hitPhysical(target, {}));
      });
      return;
    }
    p.act(cls.attackAnims, this.c.derived.attackDelay, () => {
      this.scene.sound.play('sfx-swing', { volume: 0.35 });
      const target = this.meleeTarget();
      if (!target) return;
      const died = this.hitPhysical(target, {});
      // Ataque Duplo do Gatuno: chance de um segundo golpe com adagas.
      const da = this.c.skillLevel('doubleattack');
      if (!died && da && cls.weapon.type === 'Dagger' && Math.random() * 100 < 5 * da) {
        this.scene.time.delayedCall(90, () => this.hitPhysical(target, {}, 4, 1));
      }
    });
  }

  // ------------------------------------------------------------ habilidades

  useSkill(id: string | undefined) {
    if (!id) return;
    const s = SKILLS[id];
    const lv = this.c.skillLevel(id);
    if (!s || !lv || s.kind === 'passive' || !this.p.ready) return;
    if (this.cooldownLeft(id) > 0) return;
    const sp = s.sp?.(lv) ?? 0;
    if (this.c.data.sp < sp) {
      this.host.notice('SP insuficiente.');
      return;
    }

    const spend = () => {
      this.c.data.sp -= sp;
      this.readyAt.set(id, this.scene.time.now + (s.cooldownMs ?? 0));
    };

    switch (s.kind) {
      case 'melee':
        return this.skillMelee(s, lv, spend);
      case 'aoeSelf':
        return this.skillAoeSelf(s, lv, spend);
      case 'bolt':
        return this.skillBolt(s, lv, sp, spend);
      case 'ranged':
        return this.skillRanged(s, lv, spend);
      case 'aoeTarget':
        return this.skillAoeTarget(s, lv, spend);
    }
  }

  private noTarget() {
    this.host.notice('Nenhum alvo ao alcance.');
  }

  private skillMelee(s: SkillDef, lv: number, spend: () => void) {
    const target = this.meleeTarget();
    if (!target) return this.noTarget();
    const ok = this.p.act(this.c.cls.attackAnims, this.c.derived.attackDelay, () => {
      this.scene.sound.play('sfx-swing', { volume: 0.4 });
      this.playFx(s.fx?.cast, this.p.x, this.p.y, this.p.facing === 1);
      if (!target.alive) return;
      const o: PhysicalOpts = { skillPct: s.pct!(lv), element: s.element, noCrit: true };
      if (s.id === 'bash') o.hitBonus = 5 * lv;
      if (s.id === 'envenom') o.flat = 15 * lv;
      this.playFx(s.fx?.hit, target.x, target.y - 20);
      const died = this.hitPhysical(target, o, s.id === 'bash' ? 30 : 12);
      if (!died && s.id === 'envenom' && Math.random() * 100 < 10 + 4 * lv) target.poison(this.scene.time.now);
    });
    if (ok) spend();
  }

  private skillAoeSelf(s: SkillDef, lv: number, spend: () => void) {
    const ok = this.p.act(this.c.cls.attackAnims, 0, () => {
      this.playFx(s.fx?.cast, this.p.x, this.p.y, this.p.facing === 1);
      this.mobsNear(this.p.x, this.p.y, s.radius!).forEach((m) => {
        this.playFx(s.fx?.hit, m.x, m.y - 20);
        this.hitPhysical(m, { skillPct: s.pct!(lv), element: s.element, hitBonus: 10 * lv, noCrit: true }, 50);
      });
    });
    if (ok) spend();
  }

  private skillBolt(s: SkillDef, lv: number, sp: number, spend: () => void) {
    const target = this.frontTarget(s.range!);
    if (!target) return this.noTarget();
    this.p.cast(s.castMs!(lv), () => {
      if (this.c.data.sp < sp) return;
      const anims = this.c.cls.attackAnims;
      const ok = this.p.act(this.p.hasAnim('shoot1') ? ['shoot1'] : anims, 0, () => {
        const hits = s.hits!(lv);
        for (let i = 0; i < hits; i++) {
          this.scene.time.delayedCall(i * 140, () => {
            if (!target.alive) return;
            const land = () => {
              if (!target.alive) return;
              this.playFx(s.fx?.hit, target.x, target.y - 15);
              this.host.applyHit(target, magicAttack(this.c.derived, target.rules, s.pct!(lv), s.element!), 6, i);
            };
            if (s.fx?.ball) this.projectile(s.fx.ball, target, land);
            else land();
          });
        }
      });
      if (ok) spend();
    });
  }

  private skillRanged(s: SkillDef, lv: number, spend: () => void) {
    const target = this.frontTarget(this.bowRange);
    if (!target) return this.noTarget();
    const ok = this.p.act(['shoot1'], this.c.derived.attackDelay, () => {
      for (let i = 0; i < s.hits!(lv); i++) {
        this.scene.time.delayedCall(i * 110, () => {
          if (!target.alive) return;
          this.scene.sound.play('sfx-swing', { volume: 0.3 });
          this.projectile('fx-arrow', target, () => {
            this.playFx(s.fx?.hit, target.x, target.y - 20);
            this.hitPhysical(target, { skillPct: s.pct!(lv), noCrit: true }, 8, i);
          });
        });
      }
    });
    if (ok) spend();
  }

  private skillAoeTarget(s: SkillDef, lv: number, spend: () => void) {
    const target = this.frontTarget(this.bowRange);
    if (!target) return this.noTarget();
    const tx = target.x;
    const ty = target.y;
    const ok = this.p.act(['shoot1'], this.c.derived.attackDelay, () => {
      this.playFx(s.fx?.cast, tx, ty);
      this.scene.time.delayedCall(250, () => {
        this.mobsNear(tx, ty, s.radius!).forEach((m) => {
          this.playFx(s.fx?.hit, m.x, m.y - 20);
          this.hitPhysical(m, { skillPct: s.pct!(lv), noCrit: true }, 40);
        });
      });
    });
    if (ok) spend();
  }
}
