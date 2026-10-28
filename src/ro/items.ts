// Itens: consumíveis do RO com ícones do Maple e saques de cada monstro.

export interface ItemDef {
  id: number;
  name: string;
  type: 'consume' | 'etc';
  hp?: number;
  sp?: number;
  /** Preço de compra na loja (consumíveis). */
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
];

export const ITEMS: Record<number, ItemDef> = Object.fromEntries(items.map((i) => [i.id, i]));

/** Itens que a loja de Henesys vende. */
export const SHOP_ITEMS = [2000000, 2000001, 2000002, 2000003, 2010000];

/** Atalhos de consumíveis (teclas 1 a 4). */
export const POTION_SLOTS = [2000000, 2000001, 2000002, 2000003];

/** Tabela de saque: [item, chance em %]. Como no RO, monstros não soltam zeny. */
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
