// Classes jogáveis nesta versão: Aprendiz e as quatro primeiras classes do RO.
import { Weapon } from './rules';

export type JobId = 'Novice' | 'Swordman' | 'Mage' | 'Archer' | 'Thief';

export interface ClassDef {
  id: JobId;
  name: string;
  desc: string;
  weapon: Weapon;
  /** Animações de ataque básico (sorteadas). */
  attackAnims: string[];
  /** Ataque básico à distância (flechas). */
  ranged: boolean;
  /** Habilidades da classe, na ordem da janela. */
  skills: string[];
}

export const CLASSES: Record<JobId, ClassDef> = {
  Novice: {
    id: 'Novice',
    name: 'Aprendiz',
    desc: 'Todo aventureiro começa aqui.',
    weapon: { name: 'Faca', atk: 17, level: 1, type: 'Dagger' },
    attackAnims: ['swingO1', 'swingO2', 'swingO3', 'stabO1'],
    ranged: false,
    skills: ['basic'],
  },
  Swordman: {
    id: 'Swordman',
    name: 'Espadachim',
    desc: 'Combate corpo a corpo, muito HP e golpes poderosos.',
    weapon: { name: 'Espada', atk: 25, level: 1, type: '1hSword' },
    attackAnims: ['swingO1', 'swingO2', 'swingO3', 'stabO1'],
    ranged: false,
    skills: ['bash', 'magnum', 'hprecovery', 'swordmastery'],
  },
  Mage: {
    id: 'Mage',
    name: 'Mago',
    desc: 'Magias elementais de longe. Pouco HP, muito dano.',
    weapon: { name: 'Cajado', atk: 15, level: 1, type: 'Staff', matkPct: 15 },
    attackAnims: ['swingO1', 'swingO2', 'swingO3'],
    ranged: false,
    skills: ['firebolt', 'coldbolt', 'lightning', 'sprecovery'],
  },
  Archer: {
    id: 'Archer',
    name: 'Arqueiro',
    desc: 'Ataca à distância com arco. Usa DEX como força.',
    weapon: { name: 'Arco', atk: 15, level: 1, type: 'Bow' },
    attackAnims: ['shoot1'],
    ranged: true,
    skills: ['doublestrafe', 'arrowshower', 'owlseye', 'vultureseye'],
  },
  Thief: {
    id: 'Thief',
    name: 'Gatuno',
    desc: 'Ágil, esquiva muito e ataca duas vezes com adagas.',
    weapon: { name: 'Adaga', atk: 30, level: 1, type: 'Dagger' },
    attackAnims: ['stabO1', 'stabO2', 'swingO1'],
    ranged: false,
    skills: ['doubleattack', 'envenom', 'improvedodge'],
  },
};

export const FIRST_CLASSES: JobId[] = ['Swordman', 'Mage', 'Archer', 'Thief'];
