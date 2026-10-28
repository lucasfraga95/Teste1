// Formato dos arquivos gerados por tools/fetch_assets.py.
import { Foothold } from '../world/footholds';

export interface SheetMeta {
  frameWidth: number;
  frameHeight: number;
  originX: number;
  originY: number;
  anims: Record<string, { start: number; count: number; delays: number[] }>;
}

export interface MobMeta extends SheetMeta {
  id: number;
  name: string;
  speed: number;
}

export interface NpcMeta extends SheetMeta {
  name: string;
}

export interface MapPiece {
  key: string;
  layer: number;
  x: number;
  y: number;
}

export interface MapBack {
  key: string;
  x: number;
  y: number;
  rx: number;
  ry: number;
  type: number;
  cx: number;
  cy: number;
  a: number;
  front: number;
  flip: number;
  ox: number;
  oy: number;
  w: number;
  h: number;
}

export interface Portal {
  name: string;
  type: number;
  x: number;
  y: number;
  toMap: number;
  toName: string;
}

export interface Ladder {
  x: number;
  y1: number;
  y2: number;
  ladder: boolean;
}

export interface LifeSpawn {
  id: number;
  x: number;
  y: number;
  fh: number;
  f: number;
}

export interface MapData {
  id: number;
  name: string;
  street: string;
  town: boolean;
  bgm: string | null;
  returnMap: number;
  bounds: { left: number; top: number; right: number; bottom: number };
  pieces: MapPiece[];
  backs: MapBack[];
  footholds: Foothold[];
  ladders: Ladder[];
  portals: Portal[];
  mobs: (LifeSpawn & { rx0: number; rx1: number })[];
  npcs: LifeSpawn[];
}

export interface AssetIndex {
  maps: number[];
  mobs: number[];
}
