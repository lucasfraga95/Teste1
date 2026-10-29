// Estado e progressão do personagem no estilo RO.
import { CLASSES, ClassDef, JobId } from './classes';
import { ITEMS } from './items';
import {
  baseExpToNext, derive, Derived, emptyStats, INITIAL_STAT_POINTS, jobBonus, jobExpToNext,
  JOBS, MAX_STAT, PassiveBonus, RATES, statCost, StatName, statPointsGained, Stats, STAT_NAMES,
} from './rules';
import { SKILLS } from './skills';

const SAVE_KEY = 'ro-maple-save-v1';
const SAVE_VERSION = 2;

export interface SaveData {
  version: number;
  name: string;
  job: JobId;
  baseLevel: number;
  baseExp: number;
  jobLevel: number;
  jobExp: number;
  statPoints: number;
  skillPoints: number;
  stats: Stats;
  skills: Record<string, number>;
  inventory: Record<number, number>;
  zeny: number;
  hp: number;
  sp: number;
  mapId: number;
}

export interface ExpEvents {
  baseLevelUps: number;
  jobLevelUps: number;
}

function newSave(): SaveData {
  return {
    version: SAVE_VERSION,
    name: 'Aventureiro',
    job: 'Novice',
    baseLevel: 1,
    baseExp: 0,
    jobLevel: 1,
    jobExp: 0,
    statPoints: INITIAL_STAT_POINTS,
    skillPoints: 0,
    stats: { str: 1, agi: 1, vit: 1, int: 1, dex: 1, luk: 1 },
    skills: {},
    // Kit inicial: algumas poções e um pouco de zeny.
    inventory: { 2000000: 5, 2010000: 5 },
    zeny: 200,
    hp: 0,
    sp: 0,
    mapId: 100000000,
  };
}

/** Pesos da distribuição automática de atributos por classe. */
const AUTO_BUILDS: Record<JobId, Stats> = {
  Novice: { str: 3, agi: 1, vit: 2, int: 0, dex: 2, luk: 0 },
  Swordman: { str: 3, agi: 1, vit: 2, int: 0, dex: 2, luk: 0 },
  Mage: { str: 0, agi: 0, vit: 1, int: 4, dex: 2, luk: 0 },
  Archer: { str: 1, agi: 2, vit: 1, int: 0, dex: 4, luk: 0 },
  Thief: { str: 2, agi: 4, vit: 1, int: 0, dex: 2, luk: 0 },
};

export class Character {
  data: SaveData;
  derived!: Derived;
  totalStats!: Stats;

  constructor(data?: Partial<SaveData>) {
    const fresh = !data;
    this.data = { ...newSave(), ...data, version: SAVE_VERSION };
    if (!CLASSES[this.data.job]) this.data.job = 'Novice';
    this.recalc();
    if (fresh) this.fullHeal();
  }

  get cls(): ClassDef {
    return CLASSES[this.data.job];
  }

  skillLevel(id: string) {
    return this.data.skills[id] ?? 0;
  }

  bonusOf(stat: StatName): number {
    return this.totalStats[stat] - this.data.stats[stat];
  }

  recalc() {
    const d = this.data;
    const b = jobBonus(d.job, d.jobLevel);
    const t = emptyStats();
    for (const s of STAT_NAMES) t[s] = d.stats[s] + b[s];
    t.dex += this.skillLevel('owlseye');
    this.totalStats = t;

    const w = this.cls.weapon;
    const p: PassiveBonus = { atk: 0, hit: 0, flee: 0 };
    if (w.type === '1hSword' || w.type === 'Dagger') p.atk += 4 * this.skillLevel('swordmastery');
    if (w.type === 'Bow') p.hit += this.skillLevel('vultureseye');
    p.flee += 3 * this.skillLevel('improvedodge');
    this.derived = derive(d.job, d.baseLevel, t, w, p);
    d.hp = Math.min(d.hp, this.derived.maxHp);
    d.sp = Math.min(d.sp, this.derived.maxSp);
  }

  fullHeal() {
    this.data.hp = this.derived.maxHp;
    this.data.sp = this.derived.maxSp;
  }

  get baseExpNext() {
    return baseExpToNext(this.data.baseLevel);
  }

  get jobExpNext() {
    return jobExpToNext(this.data.job, this.data.jobLevel);
  }

  get jobMaxed() {
    return this.data.jobLevel >= JOBS[this.data.job].maxJobLevel;
  }

  // ------------------------------------------------------------ atributos

  canRaise(stat: StatName) {
    const v = this.data.stats[stat];
    return v < MAX_STAT && this.data.statPoints >= statCost(v);
  }

  raise(stat: StatName): boolean {
    if (!this.canRaise(stat)) return false;
    this.data.statPoints -= statCost(this.data.stats[stat]);
    this.data.stats[stat]++;
    this.recalc();
    return true;
  }

  /**
   * Gasta os pontos livres numa distribuição sugerida para a classe atual.
   * Cada atributo tem um peso; sobe sempre o que está mais abaixo da sua meta.
   */
  autoDistribute(): number {
    const weights = AUTO_BUILDS[this.data.job];
    let spent = 0;
    for (;;) {
      const options = STAT_NAMES.filter((s) => weights[s] > 0 && this.canRaise(s));
      if (!options.length) break;
      const next = options.reduce((a, b) => (this.data.stats[a] / weights[a] <= this.data.stats[b] / weights[b] ? a : b));
      this.raise(next);
      spent++;
    }
    return spent;
  }

  // ------------------------------------------------------------ habilidades

  /** Habilidades visíveis na janela (a classe atual). */
  get skillList(): string[] {
    return this.cls.skills;
  }

  canLearn(id: string) {
    const s = SKILLS[id];
    if (!s || this.data.skillPoints <= 0 || this.skillLevel(id) >= s.maxLevel) return false;
    return (s.req ?? []).every((r) => this.skillLevel(r.skill) >= r.level);
  }

  learn(id: string): boolean {
    if (!this.canLearn(id)) return false;
    this.data.skills[id] = this.skillLevel(id) + 1;
    this.data.skillPoints--;
    this.recalc();
    return true;
  }

  /** Habilidades ativas aprendidas (para a barra de atalhos). */
  get activeSkills(): string[] {
    return this.skillList.filter((id) => SKILLS[id].kind !== 'passive' && this.skillLevel(id) > 0);
  }

  get canChangeJob() {
    return this.data.job === 'Novice' && this.data.jobLevel >= 10 && this.skillLevel('basic') >= 9;
  }

  changeJob(job: JobId) {
    const d = this.data;
    d.job = job;
    d.jobLevel = 1;
    d.jobExp = 0;
    d.skillPoints = 0;
    this.recalc();
  }

  // ------------------------------------------------------------ itens

  count(id: number) {
    return this.data.inventory[id] ?? 0;
  }

  addItem(id: number, n = 1) {
    this.data.inventory[id] = this.count(id) + n;
  }

  removeItem(id: number, n = 1): boolean {
    if (this.count(id) < n) return false;
    this.data.inventory[id] = this.count(id) - n;
    if (!this.data.inventory[id]) delete this.data.inventory[id];
    return true;
  }

  /** Usa um consumível. Retorna o quanto curou, ou null se não pôde usar. */
  useItem(id: number): { hp: number; sp: number } | null {
    const it = ITEMS[id];
    if (!it || it.type !== 'consume' || this.count(id) <= 0) return null;
    const d = this.data;
    if ((it.hp && d.hp >= this.derived.maxHp && !it.sp) || (it.sp && d.sp >= this.derived.maxSp && !it.hp)) return null;
    this.removeItem(id);
    const hp = Math.min(it.hp ?? 0, this.derived.maxHp - d.hp);
    const sp = Math.min(it.sp ?? 0, this.derived.maxSp - d.sp);
    d.hp += hp;
    d.sp += sp;
    return { hp, sp };
  }

  buy(id: number, n = 1): boolean {
    const price = (ITEMS[id]?.price ?? 0) * n;
    if (!price || this.data.zeny < price) return false;
    this.data.zeny -= price;
    this.addItem(id, n);
    return true;
  }

  /** Vende todos os saques (itens etc). Retorna o zeny ganho. */
  sellLoot(): number {
    let total = 0;
    for (const [k, n] of Object.entries(this.data.inventory)) {
      const it = ITEMS[Number(k)];
      if (it?.type !== 'etc') continue;
      total += it.sell * n;
      delete this.data.inventory[Number(k)];
    }
    this.data.zeny += total;
    return total;
  }

  // ------------------------------------------------------------ experiência

  gainExp(base: number, job: number): ExpEvents {
    const ev: ExpEvents = { baseLevelUps: 0, jobLevelUps: 0 };
    const d = this.data;
    d.baseExp += Math.round(base * RATES.baseExp);
    // Como no RO, só sobe um nível por vez por monstro; o excesso fica até 1 abaixo.
    let next = this.baseExpNext;
    while (next > 0 && d.baseExp >= next) {
      d.baseExp -= next;
      d.baseLevel++;
      d.statPoints += statPointsGained(d.baseLevel);
      ev.baseLevelUps++;
      next = this.baseExpNext;
      if (next > 0 && d.baseExp >= next) d.baseExp = next - 1;
    }
    if (next === 0) d.baseExp = 0;

    d.jobExp += Math.round(job * RATES.jobExp);
    let jnext = this.jobExpNext;
    while (jnext > 0 && d.jobExp >= jnext) {
      d.jobExp -= jnext;
      d.jobLevel++;
      d.skillPoints++;
      ev.jobLevelUps++;
      jnext = this.jobExpNext;
      if (jnext > 0 && d.jobExp >= jnext) d.jobExp = jnext - 1;
    }
    if (jnext === 0) d.jobExp = 0;

    this.recalc();
    if (ev.baseLevelUps) this.fullHeal();
    return ev;
  }

  /** Penalidade de morte Pré-Renewal: perde 1% da EXP de base do nível. */
  deathPenalty() {
    const loss = Math.floor(this.baseExpNext * 0.01);
    this.data.baseExp = Math.max(0, this.data.baseExp - loss);
  }

  save() {
    try {
      localStorage.setItem(SAVE_KEY, JSON.stringify(this.data));
    } catch {
      /* armazenamento indisponível */
    }
  }

  static load(): Character {
    try {
      const raw = localStorage.getItem(SAVE_KEY);
      if (raw) return new Character(JSON.parse(raw));
    } catch {
      /* save corrompido ou indisponível: começa do zero */
    }
    return new Character();
  }

  static reset() {
    try {
      localStorage.removeItem(SAVE_KEY);
    } catch {
      /* ignora */
    }
  }
}
