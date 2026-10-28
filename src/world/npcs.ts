// Papéis dos NPCs de Henesys neste jogo.

export type NpcRole = 'job' | 'shop' | 'heal' | 'taxi';

export const NPC_ROLES: Record<number, { role: NpcRole; title: string }> = {
  9200000: { role: 'job', title: 'Instrutor de Classes' },
  1010100: { role: 'shop', title: 'Loja de Poções' },
  9201001: { role: 'heal', title: 'Curandeira' },
  1012000: { role: 'taxi', title: 'Transporte' },
};

/** Destinos do táxi (como o teleporte da Kafra no RO). */
export const TAXI_DESTINATIONS: { map: number; name: string; levels: string; price: number }[] = [
  { map: 100010000, name: 'Colina a Leste de Henesys', levels: 'Nv. 1-7', price: 50 },
  { map: 104040000, name: 'Campo de Caça de Henesys I', levels: 'Nv. 1-7', price: 50 },
  { map: 104030000, name: 'Colina a Oeste de Henesys', levels: 'Nv. 3-8', price: 100 },
  { map: 100020000, name: 'Floresta Tropical', levels: 'Nv. 7-10', price: 150 },
  { map: 104040001, name: 'Campo de Caça de Henesys II', levels: 'Nv. 7-16', price: 200 },
  { map: 104040002, name: 'Campo de Caça de Henesys III', levels: 'Nv. 9-16', price: 250 },
  { map: 106010000, name: 'Estrada para o Calabouço', levels: 'Nv. 18-20', price: 400 },
];
