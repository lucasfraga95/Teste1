// Monta um mapa do MapleStory: fundos com parallax, camadas, portais e NPCs.
import Phaser from 'phaser';
import { MapBack, MapData, NpcMeta, Portal } from '../data/types';
import { Footholds } from './footholds';

/**
 * Profundidade de personagens, monstros, NPCs e itens. No Maple eles ficam junto
 * da camada da plataforma (e árvores de camadas acima os cobrem); aqui ficam
 * sempre na frente do cenário, que é o que se espera num jogo 2D.
 */
const ENTITY_DEPTH = 8 * 100 + 50;
export const depthFor = (_layer?: number) => ENTITY_DEPTH;
const BACK_DEPTH = -1000;
const FRONT_DEPTH = 5000;
const HUD_HEIGHT = 62;

interface BackView {
  b: MapBack;
  obj: Phaser.GameObjects.Image | Phaser.GameObjects.TileSprite;
  htile: boolean;
  vtile: boolean;
  scrollX: number;
  scrollY: number;
}

export class MapView {
  readonly fh: Footholds;
  readonly bounds: Phaser.Geom.Rectangle;
  private backs: BackView[] = [];

  constructor(private scene: Phaser.Scene, readonly data: MapData) {
    this.fh = new Footholds(data.footholds);
    // Câmera: vai até onde o personagem pode andar (as plataformas), para ele
    // nunca sair da tela; embaixo deixa espaço para a barra inferior.
    const left = this.fh.left;
    const right = this.fh.right;
    const top = Math.min(data.bounds.top, this.fh.top - 300);
    const bottom = Math.max(this.fh.bottom + 80, Math.min(data.bounds.bottom, this.fh.bottom + 200)) + HUD_HEIGHT;
    this.bounds = new Phaser.Geom.Rectangle(left, top, right - left, bottom - top);

    data.backs.forEach((b, i) => this.addBack(b, i));
    for (const p of data.pieces) {
      scene.add.image(p.x, p.y, p.key).setOrigin(0, 0).setDepth(p.layer * 100 + 10);
    }
    for (const p of data.portals) if (p.type === 2) this.addPortal(p);
    for (const n of data.npcs) this.addNpc(n.id, n.x, n.y, n.fh, n.f);
  }

  /** Camada sobre a qual um ponto está (pela plataforma mais próxima abaixo). */
  layerAt(x: number, y: number) {
    return this.fh.below(x, y - 5, 400)?.layer ?? 0;
  }

  private addBack(b: MapBack, i: number) {
    const htile = [1, 3, 4, 6, 7].includes(b.type);
    const vtile = [2, 3, 5, 6, 7].includes(b.type);
    const { width, height } = this.scene.scale;
    const key = `back-${b.key}`;
    let obj: Phaser.GameObjects.Image | Phaser.GameObjects.TileSprite;
    if (htile || vtile) {
      obj = this.scene.add.tileSprite(0, 0, htile ? width + b.w * 2 : b.w, vtile ? height + b.h * 2 : b.h, key);
    } else {
      obj = this.scene.add.image(0, 0, key);
    }
    obj.setOrigin(0, 0).setScrollFactor(0).setAlpha(b.a / 255);
    obj.setDepth((b.front ? FRONT_DEPTH : BACK_DEPTH) + i);
    if (b.flip && obj instanceof Phaser.GameObjects.Image) obj.setFlipX(true);
    this.backs.push({ b, obj, htile, vtile, scrollX: 0, scrollY: 0 });
  }

  /** Posiciona os fundos (fórmula de parallax do cliente do MapleStory). */
  update(cam: Phaser.Cameras.Scene2D.Camera, dt: number) {
    const { width, height } = this.scene.scale;
    const cx = cam.scrollX + width / 2;
    const cy = cam.scrollY + height / 2;
    for (const v of this.backs) {
      const b = v.b;
      let x: number;
      let y: number;
      if (b.type === 4 || b.type === 6) {
        v.scrollX += b.rx * 8 * dt;
        x = b.x + v.scrollX - cx + width / 2;
      } else {
        x = b.x + (b.rx * cx) / 100 + width / 2;
      }
      if (b.type === 5 || b.type === 7) {
        v.scrollY += b.ry * 8 * dt;
        y = b.y + v.scrollY - cy + height / 2;
      } else {
        y = b.y + (b.ry * cy) / 100 + height / 2;
      }
      x -= b.ox;
      y -= b.oy;
      if (v.htile) {
        const w = b.cx > 0 ? b.cx : b.w;
        const off = ((x % w) + w) % w;
        v.obj.x = off - w;
        (v.obj as Phaser.GameObjects.TileSprite).tilePositionX = 0;
      } else {
        v.obj.x = x;
      }
      if (v.vtile) {
        const h = b.cy > 0 ? b.cy : b.h;
        const off = ((y % h) + h) % h;
        v.obj.y = off - h;
      } else {
        v.obj.y = y;
      }
    }
  }

  private addPortal(p: Portal) {
    const s = this.scene.add.sprite(p.x, p.y, 'fx-portal').play('fx-portal:portal');
    const meta = this.scene.cache.json.get('fx-portal');
    s.setOrigin(meta.originX / meta.frameWidth, meta.originY / meta.frameHeight);
    s.setDepth(depthFor(this.layerAt(p.x, p.y)) - 5);
  }

  private addNpc(id: number, x: number, y: number, fhId: number, flip: number) {
    const key = `npc${id}`;
    if (!this.scene.textures.exists(key)) return;
    const meta = this.scene.cache.json.get(key) as NpcMeta;
    const layer = this.fh.get(fhId)?.layer ?? this.layerAt(x, y);
    const s = this.scene.add.sprite(x, y, key).play(`${key}:stand`);
    s.setOrigin(meta.originX / meta.frameWidth, meta.originY / meta.frameHeight);
    s.setFlipX(!!flip).setDepth(depthFor(layer) - 2);
    if (meta.name) {
      this.scene.add
        .text(x, y + 4, meta.name, {
          fontFamily: 'Verdana, sans-serif',
          fontSize: '11px',
          color: '#ffe680',
          backgroundColor: '#000000aa',
          padding: { x: 4, y: 1 },
        })
        .setOrigin(0.5, 0)
        .setDepth(depthFor(layer) - 1);
    }
  }
}
