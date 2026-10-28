// Plataformas do MapleStory ("footholds"): segmentos ligados por prev/next.
// Segmentos verticais (x1 == x2) são paredes.

export interface Foothold {
  id: number;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  prev: number;
  next: number;
  layer: number;
}

export interface GroundMove {
  fh: Foothold | null;
  x: number;
  y: number;
  blocked: boolean;
}

const EPS = 1;

export class Footholds {
  readonly list: Foothold[];
  readonly floors: Foothold[];
  readonly walls: Foothold[];
  private byId = new Map<number, Foothold>();
  readonly left: number;
  readonly right: number;
  readonly top: number;
  readonly bottom: number;

  constructor(list: Foothold[]) {
    this.list = list;
    for (const f of list) this.byId.set(f.id, f);
    this.floors = list.filter((f) => f.x1 !== f.x2);
    this.walls = list.filter((f) => f.x1 === f.x2);
    const xs = list.flatMap((f) => [f.x1, f.x2]);
    const ys = list.flatMap((f) => [f.y1, f.y2]);
    this.left = Math.min(...xs);
    this.right = Math.max(...xs);
    this.top = Math.min(...ys);
    this.bottom = Math.max(...ys);
  }

  get(id: number) {
    return this.byId.get(id);
  }

  static yAt(f: Foothold, x: number) {
    if (f.x1 === f.x2) return Math.min(f.y1, f.y2);
    return f.y1 + ((f.y2 - f.y1) * (x - f.x1)) / (f.x2 - f.x1);
  }

  static covers(f: Foothold, x: number) {
    return x >= Math.min(f.x1, f.x2) && x <= Math.max(f.x1, f.x2);
  }

  /** Plataforma mais alta abaixo de (x, y), dentro de `maxDrop`. */
  below(x: number, y: number, maxDrop = Infinity, ignore?: Foothold | null): Foothold | null {
    let best: Foothold | null = null;
    let bestY = Infinity;
    for (const f of this.floors) {
      if (f === ignore || !Footholds.covers(f, x)) continue;
      const fy = Footholds.yAt(f, x);
      if (fy >= y - EPS && fy - y <= maxDrop && fy < bestY) {
        best = f;
        bestY = fy;
      }
    }
    return best;
  }

  /** Pouso durante a queda: cruzou alguma plataforma entre y0 e y1? */
  landing(x: number, y0: number, y1: number, ignore?: Foothold | null): Foothold | null {
    let best: Foothold | null = null;
    let bestY = Infinity;
    for (const f of this.floors) {
      if (f === ignore || !Footholds.covers(f, x)) continue;
      const fy = Footholds.yAt(f, x);
      if (y0 <= fy + EPS && y1 >= fy && fy < bestY) {
        best = f;
        bestY = fy;
      }
    }
    return best;
  }

  /** Paredes que bloqueiam um deslocamento horizontal no ar. */
  wallBlock(x0: number, x1: number, y: number): number | null {
    if (x0 === x1) return null;
    for (const w of this.walls) {
      const top = Math.min(w.y1, w.y2);
      const bottom = Math.max(w.y1, w.y2);
      if (y <= top + EPS || y > bottom + EPS) continue;
      if (x1 > x0 && w.x1 >= x0 && w.x1 <= x1) return w.x1 - 1;
      if (x1 < x0 && w.x1 <= x0 && w.x1 >= x1) return w.x1 + 1;
    }
    return null;
  }

  /** Anda sobre a cadeia de plataformas de `fh` até `tx`. */
  walk(fh: Foothold, tx: number): GroundMove {
    let cur = fh;
    for (let guard = 0; guard < 32; guard++) {
      const lo = Math.min(cur.x1, cur.x2);
      const hi = Math.max(cur.x1, cur.x2);
      if (tx >= lo && tx <= hi) return { fh: cur, x: tx, y: Footholds.yAt(cur, tx), blocked: false };
      const right = tx > hi;
      const bx = right ? hi : lo;
      const by = Footholds.yAt(cur, bx);
      const nb = [this.byId.get(cur.prev), this.byId.get(cur.next)].find(
        (n) =>
          n &&
          n !== cur &&
          ((Math.abs(n.x1 - bx) <= EPS && Math.abs(n.y1 - by) <= EPS) ||
            (Math.abs(n.x2 - bx) <= EPS && Math.abs(n.y2 - by) <= EPS)),
      );
      if (!nb) return { fh: null, x: tx, y: by, blocked: false };
      if (nb.x1 === nb.x2) {
        const wallTop = Math.min(nb.y1, nb.y2);
        if (wallTop < by - EPS) {
          return { fh: cur, x: right ? bx - 0.01 : bx + 0.01, y: by, blocked: true };
        }
        return { fh: null, x: tx, y: by, blocked: false };
      }
      cur = nb;
    }
    return { fh: cur, x: tx, y: Footholds.yAt(cur, tx), blocked: true };
  }
}
