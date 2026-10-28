// Controles de toque: direcional à esquerda, ataque e pulo à direita.
import Phaser from 'phaser';

const BAR_H = 62;
const STICK_R = 62;
const DEADZONE = 0.35;

/** Tela de toque? (ou forçado com ?touch=1 na URL, para testar no PC) */
export function isTouchDevice(): boolean {
  const q = new URLSearchParams(window.location.search).get('touch');
  if (q !== null) return q !== '0';
  return window.matchMedia?.('(pointer: coarse)').matches || 'ontouchstart' in window;
}

export class TouchControls {
  left = false;
  right = false;
  up = false;
  down = false;
  attack = false;
  private jumpQueued = false;
  private upQueued = false;

  private stickId: number | null = null;
  private stickBase: Phaser.GameObjects.Arc;
  private stickThumb: Phaser.GameObjects.Arc;
  private baseX: number;
  private baseY: number;
  private buttons: { circle: Phaser.GameObjects.Arc; ids: Set<number>; onDown: () => void; onUp?: () => void }[] = [];

  constructor(private scene: Phaser.Scene) {
    const { width, height } = scene.scale;
    scene.input.addPointer(3);
    this.baseX = 105;
    this.baseY = height - BAR_H - 95;

    this.stickBase = scene.add.circle(this.baseX, this.baseY, STICK_R, 0x0b1020, 0.35).setStrokeStyle(2, 0xffffff, 0.35);
    this.stickThumb = scene.add.circle(this.baseX, this.baseY, 26, 0xffffff, 0.35);

    const by = height - BAR_H - 70;
    this.addButton(width - 80, by - 10, 46, 'ATACAR', 0xd94848, () => (this.attack = true), () => (this.attack = false));
    this.addButton(width - 190, by + 20, 36, 'PULAR', 0x3f7fe0, () => (this.jumpQueued = true));

    scene.input.on('pointerdown', this.onDown, this);
    scene.input.on('pointermove', this.onMove, this);
    scene.input.on('pointerup', this.onUp, this);
    scene.input.on('pointerupoutside', this.onUp, this);
  }

  private addButton(x: number, y: number, r: number, label: string, color: number, onDown: () => void, onUp?: () => void) {
    const circle = this.scene.add.circle(x, y, r, color, 0.45).setStrokeStyle(2, 0xffffff, 0.5);
    this.scene.add
      .text(x, y, label, { fontFamily: 'Verdana, sans-serif', fontSize: '12px', fontStyle: 'bold', color: '#ffffff' })
      .setOrigin(0.5)
      .setAlpha(0.9);
    this.buttons.push({ circle, ids: new Set(), onDown, onUp });
  }

  /** Pulo apertado desde a última leitura. */
  consumeJump() {
    const j = this.jumpQueued;
    this.jumpQueued = false;
    return j;
  }

  /** Direcional empurrado para cima desde a última leitura (portais, NPCs). */
  consumeUp() {
    const u = this.upQueued;
    this.upQueued = false;
    return u;
  }

  private onDown(p: Phaser.Input.Pointer, over: Phaser.GameObjects.GameObject[]) {
    for (const b of this.buttons) {
      if (Phaser.Math.Distance.Between(p.x, p.y, b.circle.x, b.circle.y) <= b.circle.radius + 10) {
        b.ids.add(p.id);
        b.circle.setFillStyle(b.circle.fillColor, 0.8);
        b.onDown();
        return;
      }
    }
    // Direcional: qualquer toque no canto inferior esquerdo, fora de janelas e botões.
    if (over.length || this.stickId !== null) return;
    const { width, height } = this.scene.scale;
    if (p.x < width * 0.4 && p.y > height * 0.35 && p.y < height - BAR_H) {
      this.stickId = p.id;
      this.moveStick(p);
    }
  }

  private onMove(p: Phaser.Input.Pointer) {
    if (p.id === this.stickId) this.moveStick(p);
  }

  private onUp(p: Phaser.Input.Pointer) {
    for (const b of this.buttons) {
      if (b.ids.delete(p.id) && b.ids.size === 0) {
        b.circle.setFillStyle(b.circle.fillColor, 0.45);
        b.onUp?.();
      }
    }
    if (p.id === this.stickId) {
      this.stickId = null;
      this.left = this.right = this.up = this.down = false;
      this.stickThumb.setPosition(this.baseX, this.baseY);
    }
  }

  private moveStick(p: Phaser.Input.Pointer) {
    let dx = p.x - this.baseX;
    let dy = p.y - this.baseY;
    const len = Math.hypot(dx, dy);
    if (len > STICK_R) {
      dx = (dx / len) * STICK_R;
      dy = (dy / len) * STICK_R;
    }
    this.stickThumb.setPosition(this.baseX + dx, this.baseY + dy);
    const nx = dx / STICK_R;
    const ny = dy / STICK_R;
    this.left = nx < -DEADZONE;
    this.right = nx > DEADZONE;
    const wasUp = this.up;
    // Para cima/baixo exige um empurrão mais claro, para não atrapalhar o andar.
    this.up = ny < -0.55;
    this.down = ny > 0.55;
    if (this.up && !wasUp) this.upQueued = true;
  }
}
