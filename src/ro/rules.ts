// Regras do RO Pré-Renewal. Tabelas vêm de src/data/ro.json (rAthena).
import ro from '../data/ro.json';

export type StatName = 'str' | 'agi' | 'vit' | 'int' | 'dex' | 'luk';
export const STAT_NAMES: StatName[] = ['str', 'agi', 'vit', 'int', 'dex', 'luk'];
export type Stats = Record<StatName, number>;
export const emptyStats = (): Stats => ({ str: 0, agi: 0, vit: 0, int: 0, dex: 0, luk: 0 });

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
  size: 'Small' | 'Medium' | 'Large';
  race: string;
  element: string;
  elementLevel: number;
  walkSpeed: number;
  attackDelay: number;
  aggressive: boolean;
}

export type WeaponType = 'Dagger' | '1hSword' | 'Staff' | 'Bow';

export interface Weapon {
  name: string;
  atk: number;
  level: number;
  type: WeaponType;
  matkPct?: number;
}

// mobDamage: multiplicador do dano que os monstros causam (ajuste de equilíbrio).
export const RATES = { baseExp: 1, jobExp: 1, mobDamage: 0.5 };
export const MAX_BASE_LEVEL = 99;
export const MAX_STAT = 99;

export const JOBS = ro.jobs as unknown as Record<string, JobData>;
export const MOBS = ro.mobs as unknown as Record<string, MobRules>;
const ATTR = ro.attr as unknown as Record<string, Record<string, Record<string, number>>>;
const BASE_EXP: number[] = ro.baseExp;
const STAT_POINTS: number[] = ro.statPoints;

// Modificador de tamanho por tipo de arma (tabela clássica do RO).
const SIZE_FIX: Record<WeaponType | 'Fist', Record<MobRules['size'], number>> = {
  Fist: { Small: 100, Medium: 100, Large: 100 },
  Dagger: { Small: 100, Medium: 75, Large: 50 },
  '1hSword': { Small: 75, Medium: 100, Large: 75 },
  Staff: { Small: 100, Medium: 100, Large: 100 },
  Bow: { Small: 100, Medium: 100, Large: 75 },
};

export function elementMod(atk: string, mob: MobRules): number {
  return ATTR[String(mob.elementLevel || 1)]?.[atk]?.[mob.element] ?? 100;
}

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
  const b = emptyStats();
  for (const e of JOBS[job].bonus) {
    if (e.level > jobLevel) continue;
    for (const s of STAT_NAMES) b[s] += e[s] ?? 0;
  }
  return b;
}

/** Bônus vindos de habilidades passivas. */
export interface PassiveBonus {
  atk: number;
  hit: number;
  flee: number;
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
export function derive(job: string, baseLevel: number, s: Stats, weapon: Weapon, p: PassiveBonus): Derived {
  const j = JOBS[job];
  const hpTable = j.baseHp ?? JOBS.Novice.baseHp!;
  const maxHp = Math.floor(hpTable[baseLevel - 1] * (1 + s.vit / 100));
  const maxSp = Math.floor(j.baseSp[baseLevel - 1] * (1 + s.int / 100));
  // Arcos usam DEX como atributo principal; armas corpo a corpo usam STR.
  const [main, sub] = weapon.type === 'Bow' ? [s.dex, s.str] : [s.str, s.dex];
  const atk = main + Math.floor(main / 10) ** 2 + Math.floor(sub / 5) + Math.floor(s.luk / 5) + p.atk;
  const baseAspd = j.aspd[weapon.type] ?? j.aspd.Fist ?? 500;
  const amotion = baseAspd - Math.floor((baseAspd * (4 * s.agi + s.dex)) / 1000);
  const matkPct = 1 + (weapon.matkPct ?? 0) / 100;
  return {
    maxHp,
    maxSp,
    atk,
    matkMin: Math.floor((s.int + Math.floor(s.int / 7) ** 2) * matkPct),
    matkMax: Math.floor((s.int + Math.floor(s.int / 5) ** 2) * matkPct),
    def: 0,
    softDef: Math.floor(s.vit / 2),
    mdef: s.int,
    hit: baseLevel + s.dex + p.hit,
    flee: baseLevel + s.agi + p.flee,
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

export interface PhysicalOpts {
  /** Multiplicador da habilidade em % (100 = ataque normal). */
  skillPct?: number;
  /** Bônus de acerto da habilidade em %. */
  hitBonus?: number;
  /** Dano fixo somado antes da defesa (ex.: Envenenar). */
  flat?: number;
  element?: string;
  /** Habilidades não causam crítico no RO. */
  noCrit?: boolean;
}

/** Ataque físico do jogador contra um monstro. */
export function physicalAttack(s: Stats, d: Derived, weapon: Weapon, mob: MobRules, o: PhysicalOpts = {}): HitResult {
  const crit = !o.noCrit && chance(d.crit - Math.floor(mob.luk / 5));
  if (!crit) {
    const hitRate = Math.max(5, Math.min(95, 80 + d.hit - (mob.level + mob.agi)));
    if (!chance(hitRate * (1 + (o.hitBonus ?? 0) / 100))) return { damage: 0, miss: true, crit: false };
  }
  // Variação da arma depende de DEX; crítico usa o máximo e ignora DEF.
  const weaponMin = Math.min(Math.floor(s.dex * (0.8 + 0.2 * weapon.level)), weapon.atk);
  let wpn = crit ? weapon.atk : rand(weaponMin, weapon.atk);
  wpn = Math.floor((wpn * SIZE_FIX[weapon.type][mob.size]) / 100);
  let damage = Math.floor(((d.atk + wpn) * (o.skillPct ?? 100)) / 100) + (o.flat ?? 0);
  if (!crit) damage = Math.floor((damage * (100 - mob.def)) / 100) - mob.vit;
  damage = Math.floor((Math.max(1, damage) * elementMod(o.element ?? 'Neutral', mob)) / 100);
  return { damage: Math.max(damage > 0 ? 1 : 0, damage), miss: false, crit };
}

/** Ataque mágico (sempre acerta, reduzido por MDEF e INT/VIT do alvo). */
export function magicAttack(d: Derived, mob: MobRules, skillPct: number, element: string): HitResult {
  const matk = rand(d.matkMin, d.matkMax);
  let damage = Math.floor((matk * skillPct) / 100);
  damage = Math.floor((damage * (100 - mob.mdef)) / 100) - (mob.int + Math.floor(mob.vit / 2));
  damage = Math.floor((Math.max(1, damage) * elementMod(element, mob)) / 100);
  return { damage: Math.max(0, damage), miss: false, crit: false };
}

/** Ataque de um monstro contra o jogador. */
export function mobAttack(mob: MobRules, d: Derived, s: Stats): HitResult {
  if (chance(d.perfectDodge)) return { damage: 0, miss: true, crit: false };
  const hitRate = Math.max(5, Math.min(95, 80 + mob.level + mob.dex - d.flee));
  if (!chance(hitRate)) return { damage: 0, miss: true, crit: false };
  const raw = rand(mob.atk[0], mob.atk[1]);
  const soft = d.softDef + rand(0, Math.floor(s.vit * 0.3));
  const damage = Math.floor(((raw * (100 - d.def)) / 100 - soft) * RATES.mobDamage);
  return { damage: Math.max(1, damage), miss: false, crit: false };
}

/** Regeneração natural (a cada 6s HP, 8s SP). */
export function hpRegen(d: Derived, s: Stats): number {
  return Math.max(1, Math.floor(d.maxHp / 200)) + Math.floor(s.vit / 5);
}

export function spRegen(d: Derived, s: Stats): number {
  return 1 + Math.floor(d.maxSp / 100) + Math.floor(s.int / 6);
}
