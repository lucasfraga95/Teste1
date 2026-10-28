// Números de dano com os dígitos do MapleStory.
import Phaser from 'phaser';

export type DamageStyle = 'NoRed1' | 'NoCri1' | 'NoViolet1' | 'heal' | 'sp';

const TEXT_COLORS: Partial<Record<DamageStyle, string>> = { heal: '#7dff8a', sp: '#8ac4ff' };

export function showDamage(
  scene: Phaser.Scene,
  x: number,
  y: number,
  value: number | 'MISS',
  style: DamageStyle,
  stack = 0,
) {
  const c = scene.add.container(x, y - stack * 28).setDepth(9000);
  if (TEXT_COLORS[style]) {
    c.add(
      scene.add
        .text(0, 0, `+${value}`, {
          fontFamily: 'Verdana, sans-serif',
          fontSize: '18px',
          fontStyle: 'bold',
          color: TEXT_COLORS[style],
          stroke: '#003010',
          strokeThickness: 4,
        })
        .setOrigin(0.5),
    );
  } else if (value === 'MISS') {
    c.add(
      scene.add
        .text(0, 0, 'MISS', {
          fontFamily: 'Verdana, sans-serif',
          fontSize: '18px',
          fontStyle: 'bold',
          color: style === 'NoViolet1' ? '#d7a6ff' : '#ffd36b',
          stroke: '#3a1d00',
          strokeThickness: 4,
        })
        .setOrigin(0.5),
    );
  } else {
    const digits = String(value).split('');
    const frame = scene.textures.get(`dmg-${style}`).get(0);
    const step = Math.round(frame.width * 0.7);
    const total = step * (digits.length - 1);
    digits.forEach((d, i) => {
      const img = scene.add.image(i * step - total / 2, i % 2 ? 2 : -2, `dmg-${style}`, Number(d));
      if (i === 0) img.setScale(1.15);
      c.add(img);
    });
  }
  scene.tweens.add({
    targets: c,
    y: c.y - 40,
    alpha: { from: 1, to: 0 },
    duration: 1100,
    ease: 'Cubic.easeIn',
    onComplete: () => c.destroy(),
  });
}
