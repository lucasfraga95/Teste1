// Itens no chão: caem do monstro e são coletados ao encostar.
import Phaser from 'phaser';
import { Footholds } from './footholds';
import { depthFor, MapView } from './MapView';

const LIFETIME_MS = 60000;
const PICKUP_DIST = 32;

/** Id usado para zeny no chão. */
export const ZENY = 0;

export interface Pickup {
  id: number;
  amount: number;
}

interface GroundItem {
  id: number;
  amount: number;
  sprite: Phaser.GameObjects.Image;
  x: number;
  y: number;
  expires: number;
  landed: boolean;
}

export class Drops {
  private items: GroundItem[] = [];

  constructor(private scene: Phaser.Scene, private map: MapView) {}

  /** Solta itens (e zeny, se `zeny` > 0) espalhados em volta de x. */
  spawn(ids: number[], x: number, y: number, zeny = 0) {
    const all = zeny > 0 ? [ZENY, ...ids] : ids;
    all.forEach((id, i) => {
      const dx = (i - (all.length - 1) / 2) * 26;
      const fh = this.map.fh.below(x + dx, y - 10, 200);
      const gy = fh ? Footholds.yAt(fh, x + dx) : y;
      const s = this.scene.add.image(x, y - 30, id === ZENY ? 'icon-meso' : `icon-item-${id}`).setOrigin(0.5, 1);
      s.setDepth(depthFor(fh?.layer ?? 0) + 3);
      const it: GroundItem = { id, amount: id === ZENY ? zeny : 1, sprite: s, x: x + dx, y: gy, expires: this.scene.time.now + LIFETIME_MS, landed: false };
      this.items.push(it);
      this.scene.tweens.add({ targets: s, x: it.x, duration: 450 });
      this.scene.tweens.add({
        targets: s,
        y: { from: y - 30, to: y - 70 },
        duration: 200,
        ease: 'Quad.easeOut',
        onComplete: () =>
          this.scene.tweens.add({
            targets: s,
            y: gy,
            duration: 250,
            ease: 'Quad.easeIn',
            onComplete: () => {
              it.landed = true;
              this.scene.tweens.add({ targets: s, y: gy - 4, yoyo: true, repeat: -1, duration: 700, ease: 'Sine.easeInOut' });
            },
          }),
      });
    });
  }

  /** Retorna o que foi coletado neste quadro. */
  update(px: number, py: number, now: number): Pickup[] {
    const got: Pickup[] = [];
    this.items = this.items.filter((it) => {
      if (now > it.expires) {
        it.sprite.destroy();
        return false;
      }
      if (it.landed && Math.abs(it.x - px) < PICKUP_DIST && Math.abs(it.y - py) < 40) {
        got.push({ id: it.id, amount: it.amount });
        this.scene.tweens.killTweensOf(it.sprite);
        this.scene.tweens.add({
          targets: it.sprite,
          y: it.sprite.y - 40,
          alpha: 0,
          duration: 300,
          onComplete: () => it.sprite.destroy(),
        });
        return false;
      }
      return true;
    });
    return got;
  }
}
