// Itens: consumíveis do RO com ícones do Maple e saques de cada monstro.

import type { WeaponType } from './rules';

export type EquipSlot = 'weapon' | 'body' | 'head' | 'shoes';

export interface ItemDef {
  id: number;
  name: string;
  type: 'consume' | 'etc' | 'equip';
  slot?: EquipSlot;
  weaponType?: WeaponType;
  atk?: number;
  def?: number;
  /** Bônus de MATK em % (cajados). */
  matkPct?: number;
  hp?: number;
  sp?: number;
  /** Preço de compra na loja. */
  price?: number;
  /** Preço de venda. */
  sell: number;
}

const items: ItemDef[] = [
  { id: 2000000, name: 'Poção Vermelha', type: 'consume', hp: 45, price: 50, sell: 25 },
  { id: 2000001, name: 'Poção Laranja', type: 'consume', hp: 105, price: 200, sell: 100 },
  { id: 2000002, name: 'Poção Branca', type: 'consume', hp: 325, price: 1200, sell: 600 },
  { id: 2000003, name: 'Poção Azul', type: 'consume', sp: 60, price: 800, sell: 400 },
  { id: 2010000, name: 'Maçã', type: 'consume', hp: 16, price: 15, sell: 7 },
  { id: 4000000, name: 'Concha de Caracol Azul', type: 'etc', sell: 5 },
  { id: 4000016, name: 'Concha de Caracol Vermelho', type: 'etc', sell: 8 },
  { id: 4000011, name: 'Esporo de Cogumelo', type: 'etc', sell: 10 },
  { id: 4000010, name: 'Bolha de Slime', type: 'etc', sell: 9 },
  { id: 4000017, name: 'Cabeça de Porco', type: 'etc', sell: 15 },
  { id: 4000001, name: 'Chapéu de Cogumelo Laranja', type: 'etc', sell: 20 },
  { id: 4000002, name: 'Laço de Porco', type: 'etc', sell: 30 },
  { id: 4000012, name: 'Chapéu de Cogumelo Verde', type: 'etc', sell: 40 },
  { id: 4000009, name: 'Chapéu de Cogumelo Azul', type: 'etc', sell: 60 },
  { id: 4000015, name: 'Chapéu de Cogumelo Chifrudo', type: 'etc', sell: 55 },
  // Armas (ATK no estilo do RO).
  { id: 1332005, name: 'Cutter', type: 'equip', slot: 'weapon', weaponType: 'Dagger', atk: 30, price: 1250, sell: 600 },
  { id: 1332006, name: 'Main Gauche', type: 'equip', slot: 'weapon', weaponType: 'Dagger', atk: 43, price: 2400, sell: 1200 },
  { id: 1332067, name: 'Adaga Afiada', type: 'equip', slot: 'weapon', weaponType: 'Dagger', atk: 60, price: 5000, sell: 2500 },
  { id: 1302007, name: 'Falchion', type: 'equip', slot: 'weapon', weaponType: '1hSword', atk: 49, price: 1500, sell: 750 },
  { id: 1302005, name: 'Blade', type: 'equip', slot: 'weapon', weaponType: '1hSword', atk: 53, price: 2900, sell: 1450 },
  { id: 1302001, name: 'Cimitarra', type: 'equip', slot: 'weapon', weaponType: '1hSword', atk: 70, price: 6000, sell: 3000 },
  { id: 1372005, name: 'Varinha', type: 'equip', slot: 'weapon', weaponType: 'Staff', atk: 25, matkPct: 15, price: 1200, sell: 600 },
  { id: 1382003, name: 'Cajado de Safira', type: 'equip', slot: 'weapon', weaponType: 'Staff', atk: 30, matkPct: 20, price: 3500, sell: 1750 },
  { id: 1382005, name: 'Cajado Arcano', type: 'equip', slot: 'weapon', weaponType: 'Staff', atk: 35, matkPct: 25, price: 7000, sell: 3500 },
  { id: 1452003, name: 'Arco Composto', type: 'equip', slot: 'weapon', weaponType: 'Bow', atk: 29, price: 2500, sell: 1250 },
  { id: 1452054, name: 'Arco Longo', type: 'equip', slot: 'weapon', weaponType: 'Bow', atk: 50, price: 5000, sell: 2500 },
  { id: 1452062, name: 'Arco de Caça', type: 'equip', slot: 'weapon', weaponType: 'Bow', atk: 60, price: 8000, sell: 4000 },
  // Armaduras, chapéus e calçados (DEF reduz o dano recebido em %).
  { id: 1040010, name: 'Camiseta', type: 'equip', slot: 'body', def: 1, price: 100, sell: 50 },
  { id: 1040013, name: 'Jaqueta', type: 'equip', slot: 'body', def: 3, price: 800, sell: 400 },
  { id: 1040014, name: 'Traje de Aventureiro', type: 'equip', slot: 'body', def: 5, price: 3000, sell: 1500 },
  { id: 1002014, name: 'Faixa Vermelha', type: 'equip', slot: 'head', def: 1, price: 300, sell: 150 },
  { id: 1002019, name: 'Bandana', type: 'equip', slot: 'head', def: 2, price: 900, sell: 450 },
  { id: 1002008, name: 'Gorro de Couro', type: 'equip', slot: 'head', def: 3, price: 2200, sell: 1100 },
  { id: 1072005, name: 'Sandálias', type: 'equip', slot: 'shoes', def: 1, price: 300, sell: 150 },
  { id: 1072004, name: 'Sapatos', type: 'equip', slot: 'shoes', def: 2, price: 900, sell: 450 },
  { id: 1072037, name: 'Botas', type: 'equip', slot: 'shoes', def: 3, price: 2200, sell: 1100 },
];

export const ITEMS: Record<number, ItemDef> = Object.fromEntries(items.map((i) => [i.id, i]));

/** Itens que a loja de Henesys vende. */
export const SHOP_ITEMS = [2000000, 2000001, 2000002, 2000003, 2010000];

/** Itens da loja de equipamentos (Jay), por categoria. */
export const EQUIP_SHOP: Record<EquipSlot, number[]> = {
  weapon: [1332005, 1332006, 1332067, 1302007, 1302005, 1302001, 1372005, 1382003, 1382005, 1452003, 1452054, 1452062],
  body: [1040010, 1040013, 1040014],
  head: [1002014, 1002019, 1002008],
  shoes: [1072005, 1072004, 1072037],
};

export const SLOT_NAMES: Record<EquipSlot, string> = {
  weapon: 'Arma',
  body: 'Armadura',
  head: 'Chapéu',
  shoes: 'Calçado',
};

/** Zeny que um monstro deixa cair (estilo MapleStory), pelo nível. */
export function rollZeny(level: number): number {
  return Math.max(1, Math.round(level * (2 + Math.random() * 4)));
}

/** Atalhos de consumíveis (teclas 1 a 4). */
export const POTION_SLOTS = [2000000, 2000001, 2000002, 2000003];

/** Tabela de saque: [item, chance em %]. O zeny vem à parte (rollZeny). */
export const DROPS: Record<number, [number, number][]> = {
  100101: [[4000000, 70], [2010000, 10], [2000000, 4]],
  130101: [[4000016, 60], [2010000, 10], [2000000, 5]],
  120100: [[4000011, 55], [2000000, 5]],
  210100: [[4000010, 60], [2000000, 5], [2000003, 0.5]],
  1210100: [[4000017, 55], [2000000, 6], [2000001, 1]],
  1210102: [[4000001, 55], [2000000, 6], [2000001, 3]],
  1210101: [[4000002, 55], [2000001, 4]],
  1110100: [[4000012, 55], [2000001, 5], [2000003, 1]],
  2220100: [[4000009, 55], [2000002, 2], [2000003, 1.5]],
  2110200: [[4000015, 55], [2000001, 6], [2000002, 2]],
};

export function rollDrops(mobId: number): number[] {
  return (DROPS[mobId] ?? []).filter(([, pct]) => Math.random() * 100 < pct).map(([id]) => id);
}
