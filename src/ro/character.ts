// Estado e progressão do personagem no estilo RO.
import {
  baseExpToNext, derive, Derived, INITIAL_STAT_POINTS, jobBonus, jobExpToNext,
  JOBS, MAX_STAT, RATES, statCost, StatName, statPointsGained, Stats, STAT_NAMES,
} from './rules';

const SAVE_KEY = 'ro-maple-save-v1';

export interface SaveData {
  name: string;
  job: string;
  baseLevel: number;
  baseExp: number;
  jobLevel: number;
  jobExp: number;
  statPoints: number;
  skillPoints: number;
  stats: Stats;
  hp: number;
  sp: number;
  mapId: number;
}

export interface ExpEvents {
  baseLevelUps: number;
  jobLevelUps: number;
}

export class Character {
  data: SaveData;
  derived!: Derived;

  constructor(data?: SaveData) {
    this.data = data ?? {
      name: 'Aprendiz',
      job: 'Novice',
      baseLevel: 1,
      baseExp: 0,
      jobLevel: 1,
      jobExp: 0,
      statPoints: INITIAL_STAT_POINTS,
      skillPoints: 0,
      stats: { str: 1, agi: 1, vit: 1, int: 1, dex: 1, luk: 1 },
      hp: 0,
      sp: 0,
      mapId: 100000000,
    };
    this.recalc();
    if (!data) this.fullHeal();
  }

  /** Atributos com bônus de classe. */
  get totalStats(): Stats {
    const b = jobBonus(this.data.job, this.data.jobLevel);
    const t = { ...this.data.stats };
    for (const s of STAT_NAMES) t[s] += b[s];
    return t;
  }

  bonusOf(stat: StatName): number {
    return jobBonus(this.data.job, this.data.jobLevel)[stat];
  }

  recalc() {
    this.derived = derive(this.data.job, this.data.baseLevel, this.totalStats);
    this.data.hp = Math.min(this.data.hp, this.derived.maxHp);
    this.data.sp = Math.min(this.data.sp, this.derived.maxSp);
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

export const JOB_NAMES: Record<string, string> = {
  Novice: 'Aprendiz',
  Swordman: 'Espadachim',
  Mage: 'Mago',
  Archer: 'Arqueiro',
  Acolyte: 'Noviço',
  Merchant: 'Mercador',
  Thief: 'Gatuno',
};
