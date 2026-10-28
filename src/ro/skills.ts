// Habilidades das primeiras classes, com números do RO Pré-Renewal.
// Tempos de conjuração foram encurtados para combinar com o ritmo de ação.
import { JobId } from './classes';

export type SkillKind =
  | 'passive'
  | 'melee' // golpe em um alvo à frente
  | 'aoeSelf' // explosão ao redor do personagem
  | 'bolt' // magia em um alvo à distância, N acertos
  | 'ranged' // disparo à distância em um alvo
  | 'aoeTarget'; // área em volta do alvo

export interface SkillDef {
  id: string;
  name: string;
  job: JobId;
  maxLevel: number;
  kind: SkillKind;
  desc: (lv: number) => string;
  req?: { skill: string; level: number }[];
  sp?: (lv: number) => number;
  castMs?: (lv: number) => number;
  cooldownMs?: number;
  /** Multiplicador de dano em % por acerto. */
  pct?: (lv: number) => number;
  hits?: (lv: number) => number;
  element?: string;
  range?: number;
  radius?: number;
  /** Efeitos visuais (chaves de fx/skill_*). */
  fx?: { cast?: string; hit?: string; ball?: string };
}

const list: SkillDef[] = [
  {
    id: 'basic',
    name: 'Habilidades Básicas',
    job: 'Novice',
    maxLevel: 9,
    kind: 'passive',
    desc: () => 'Necessária no nível 9 para mudar de classe.',
  },
  // ------------------------------------------------------------ Espadachim
  {
    id: 'bash',
    name: 'Golpe Fulminante',
    job: 'Swordman',
    maxLevel: 10,
    kind: 'melee',
    sp: (lv) => (lv <= 5 ? 8 : 15),
    pct: (lv) => 100 + 30 * lv,
    cooldownMs: 300,
    desc: (lv) => `Golpe de ${100 + 30 * lv}% de dano, +${5 * lv}% de precisão.`,
    fx: { cast: 'skill_bash_effect', hit: 'skill_bash_hit' },
  },
  {
    id: 'magnum',
    name: 'Impacto Explosivo',
    job: 'Swordman',
    maxLevel: 10,
    kind: 'aoeSelf',
    req: [{ skill: 'bash', level: 5 }],
    sp: () => 30,
    pct: (lv) => 100 + 20 * lv,
    element: 'Fire',
    radius: 130,
    cooldownMs: 2000,
    desc: (lv) => `Explosão de fogo ao redor: ${100 + 20 * lv}% em todos os inimigos próximos.`,
    fx: { cast: 'skill_magnum_effect', hit: 'skill_magnum_hit' },
  },
  {
    id: 'hprecovery',
    name: 'Recuperação de HP',
    job: 'Swordman',
    maxLevel: 10,
    kind: 'passive',
    desc: (lv) => `Recupera ${5 * lv} HP + ${(0.2 * lv).toFixed(1)}% do HP máximo a cada 10s.`,
  },
  {
    id: 'swordmastery',
    name: 'Perícia com Espada',
    job: 'Swordman',
    maxLevel: 10,
    kind: 'passive',
    desc: (lv) => `+${4 * lv} de ATK com espadas e adagas.`,
  },
  // ------------------------------------------------------------ Mago
  ...(
    [
      ['firebolt', 'Lanças de Fogo', 'Fire', 'skill_firebolt_ball', 'skill_firebolt_hit'],
      ['coldbolt', 'Lanças de Gelo', 'Water', undefined, 'skill_coldbolt_hit'],
      ['lightning', 'Relâmpago', 'Wind', undefined, 'skill_lightning_hit'],
    ] as const
  ).map(
    ([id, name, element, ball, hit]): SkillDef => ({
      id,
      name,
      job: 'Mage',
      maxLevel: 10,
      kind: 'bolt',
      sp: (lv) => 10 + 2 * lv,
      castMs: (lv) => 250 + 120 * lv,
      cooldownMs: 600,
      pct: () => 100,
      hits: (lv) => lv,
      element,
      range: 420,
      desc: (lv) => `${lv} raio(s) de ${element === 'Fire' ? 'fogo' : element === 'Water' ? 'água' : 'vento'}, cada um com 100% do MATK.`,
      fx: { ball, hit },
    }),
  ),
  {
    id: 'sprecovery',
    name: 'Recuperação de SP',
    job: 'Mage',
    maxLevel: 10,
    kind: 'passive',
    desc: (lv) => `Recupera ${3 * lv} SP + ${(0.2 * lv).toFixed(1)}% do SP máximo a cada 10s.`,
  },
  // ------------------------------------------------------------ Arqueiro
  {
    id: 'doublestrafe',
    name: 'Rajada de Flechas',
    job: 'Archer',
    maxLevel: 10,
    kind: 'ranged',
    sp: () => 12,
    pct: (lv) => 100 + 10 * lv,
    hits: () => 2,
    range: 420,
    cooldownMs: 300,
    desc: (lv) => `Dispara 2 flechas de ${100 + 10 * lv}% de dano cada.`,
    fx: { hit: 'skill_doublestrafe_hit' },
  },
  {
    id: 'arrowshower',
    name: 'Chuva de Flechas',
    job: 'Archer',
    maxLevel: 10,
    kind: 'aoeTarget',
    req: [{ skill: 'doublestrafe', level: 5 }],
    sp: () => 15,
    pct: (lv) => 80 + 5 * lv,
    range: 420,
    radius: 110,
    cooldownMs: 1000,
    desc: (lv) => `Flechas em área: ${80 + 5 * lv}% em todos perto do alvo.`,
    fx: { cast: 'skill_arrowshower_effect', hit: 'skill_arrowshower_hit' },
  },
  {
    id: 'owlseye',
    name: 'Olhos de Coruja',
    job: 'Archer',
    maxLevel: 10,
    kind: 'passive',
    desc: (lv) => `+${lv} de DEX.`,
  },
  {
    id: 'vultureseye',
    name: 'Olhos de Águia',
    job: 'Archer',
    maxLevel: 10,
    kind: 'passive',
    req: [{ skill: 'owlseye', level: 3 }],
    desc: (lv) => `+${lv} de precisão e +${25 * lv} de alcance com arco.`,
  },
  // ------------------------------------------------------------ Gatuno
  {
    id: 'doubleattack',
    name: 'Ataque Duplo',
    job: 'Thief',
    maxLevel: 10,
    kind: 'passive',
    desc: (lv) => `${5 * lv}% de chance de acertar duas vezes com adagas.`,
  },
  {
    id: 'envenom',
    name: 'Envenenar',
    job: 'Thief',
    maxLevel: 10,
    kind: 'melee',
    sp: () => 12,
    pct: () => 100,
    element: 'Poison',
    cooldownMs: 300,
    desc: (lv) => `Ataque venenoso (+${15 * lv} de dano), ${10 + 4 * lv}% de chance de envenenar.`,
    fx: { cast: 'skill_envenom_effect', hit: 'skill_envenom_hit' },
  },
  {
    id: 'improvedodge',
    name: 'Perícia em Esquiva',
    job: 'Thief',
    maxLevel: 10,
    kind: 'passive',
    desc: (lv) => `+${3 * lv} de esquiva (FLEE).`,
  },
];

export const SKILLS: Record<string, SkillDef> = Object.fromEntries(list.map((s) => [s.id, s]));
