// Regras do RO Pré-Renewal. Tabelas vêm de src/data/ro.json (rAthena).
import ro from '../data/ro.json';

export type StatName = 'str' | 'agi' | 'vit' | 'int' | 'dex' | 'luk';
export const STAT_NAMES: StatName[] = ['str', 'agi', 'vit', 'int', 'dex', 'luk'];
export type Stats = Record<StatName, number>;

export interface JobData {
  jobExp: number[];
  maxJobLevel: number;
  baseHp: number[] | null;
  baseSp: number[];
  bonus: ({ level: number } & Partial<Stats>)[];
  maxWeight: number;
  aspd: Record<string, number>;
}

export interface MobRules {
  ro: string;
  level: number;
  hp: number;
  baseExp: number;
  jobExp: number;
  atk: [number, number];
  def: number;
  mdef: number;
  str: number;
  agi: number;
  vit: number;
  int: number;
  dex: number;
  luk: number;
  size: string;
  race: string;
  element: string;
  walkSpeed: number;
  attackDelay: number;
  aggressive: boolean;
}

export const RATES = { baseExp: 1, jobExp: 1 };
export const MAX_BASE_LEVEL = 99;
export const MAX_STAT = 99;

export const JOBS = ro.jobs as unknown as Record<string, JobData>;
export const MOBS = ro.mobs as unknown as Record<string, MobRules>;
const BASE_EXP: number[] = ro.baseExp;
const STAT_POINTS: number[] = ro.statPoints;

// Arma do protótipo: Sword do RO (ATK 25, nível de arma 1).
export const WEAPON = { name: 'Sword', atk: 25, level: 1, type: '1hSword' };

export function baseExpToNext(level: number): number {
  return level >= MAX_BASE_LEVEL ? 0 : BASE_EXP[level - 1];
}

export function jobExpToNext(job: string, level: number): number {
  const j = JOBS[job];
  return level >= j.maxJobLevel ? 0 : j.jobExp[level - 1];
}

/** Pontos de atributo ganhos ao passar de level-1 para level. */
export function statPointsGained(level: number): number {
  return STAT_POINTS[level - 1] - STAT_POINTS[level - 2];
}

export const INITIAL_STAT_POINTS = STAT_POINTS[0];

/** Custo para subir um atributo que está em `value`. */
export function statCost(value: number): number {
  return Math.floor((value - 1) / 10) + 2;
}

/** Bônus de atributo por nível de classe. */
export function jobBonus(job: string, jobLevel: number): Stats {
  const b: Stats = { str: 0, agi: 0, vit: 0, int: 0, dex: 0, luk: 0 };
  for (const e of JOBS[job].bonus) {
    if (e.level > jobLevel) continue;
    for (const s of STAT_NAMES) b[s] += e[s] ?? 0;
  }
  return b;
}

export interface Derived {
  maxHp: number;
  maxSp: number;
  atk: number;
  matkMin: number;
  matkMax: number;
  def: number;
  softDef: number;
  mdef: number;
  hit: number;
  flee: number;
  perfectDodge: number;
  crit: number;
  aspd: number;
  attackDelay: number;
}

/** Atributos derivados (fórmulas Pré-Renewal). `s` já inclui bônus. */
export function derive(job: string, baseLevel: number, s: Stats): Derived {
  const j = JOBS[job];
  const hpTable = j.baseHp ?? JOBS.Novice.baseHp!;
  const maxHp = Math.floor(hpTable[baseLevel - 1] * (1 + s.vit / 100));
  const maxSp = Math.floor(j.baseSp[baseLevel - 1] * (1 + s.int / 100));
  const atk =
    s.str + Math.floor(s.str / 10) ** 2 + Math.floor(s.dex / 5) + Math.floor(s.luk / 5);
  const baseAspd = j.aspd[WEAPON.type] ?? j.aspd.Fist ?? 500;
  const amotion = baseAspd - Math.floor((baseAspd * (4 * s.agi + s.dex)) / 1000);
  return {
    maxHp,
    maxSp,
    atk,
    matkMin: s.int + Math.floor(s.int / 7) ** 2,
    matkMax: s.int + Math.floor(s.int / 5) ** 2,
    def: 0,
    softDef: Math.floor(s.vit / 2),
    mdef: s.int,
    hit: baseLevel + s.dex,
    flee: baseLevel + s.agi,
    perfectDodge: 1 + Math.floor(s.luk / 10),
    crit: 1 + Math.floor(s.luk * 0.3),
    aspd: Math.floor(200 - amotion / 10),
    attackDelay: amotion * 2,
  };
}

const rand = (min: number, max: number) => min + Math.floor(Math.random() * (max - min + 1));
const chance = (pct: number) => Math.random() * 100 < pct;

export interface HitResult {
  damage: number;
  miss: boolean;
  crit: boolean;
}

/** Ataque físico básico do jogador contra um monstro. */
export function playerAttack(baseLevel: number, s: Stats, d: Derived, mob: MobRules): HitResult {
  const crit = chance(d.crit - Math.floor(mob.luk / 5));
  if (!crit) {
    const hitRate = Math.max(5, Math.min(95, 80 + d.hit - (mob.level + mob.agi)));
    if (!chance(hitRate)) return { damage: 0, miss: true, crit: false };
  }
  // Variação da arma depende de DEX; crítico usa o máximo e ignora DEF.
  const weaponMin = Math.min(Math.floor(s.dex * (0.8 + 0.2 * WEAPON.level)), WEAPON.atk);
  const weapon = crit ? WEAPON.atk : rand(weaponMin, WEAPON.atk);
  let damage = d.atk + weapon;
  if (!crit) {
    damage = Math.floor((damage * (100 - mob.def)) / 100) - mob.vit;
  }
  return { damage: Math.max(1, damage), miss: false, crit };
}

/** Ataque de um monstro contra o jogador. */
export function mobAttack(mob: MobRules, d: Derived, s: Stats): HitResult {
  if (chance(d.perfectDodge)) return { damage: 0, miss: true, crit: false };
  const hitRate = Math.max(5, Math.min(95, 80 + mob.level + mob.dex - d.flee));
  if (!chance(hitRate)) return { damage: 0, miss: true, crit: false };
  const raw = rand(mob.atk[0], mob.atk[1]);
  const soft = d.softDef + rand(0, Math.floor(s.vit * 0.3));
  const damage = Math.floor((raw * (100 - d.def)) / 100) - soft;
  return { damage: Math.max(1, damage), miss: false, crit: false };
}

/** Regeneração natural (a cada 6s HP, 8s SP). */
export function hpRegen(d: Derived, s: Stats): number {
  return Math.max(1, Math.floor(d.maxHp / 200)) + Math.floor(s.vit / 5);
}

export function spRegen(d: Derived, s: Stats): number {
  return 1 + Math.floor(d.maxSp / 100) + Math.floor(s.int / 6);
}
