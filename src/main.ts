import Phaser from 'phaser';
import { Game } from './scenes/Game';
import { Preload } from './scenes/Preload';
import { UI } from './scenes/UI';

const game = new Phaser.Game({
  type: Phaser.AUTO,
  parent: 'game',
  width: 1024,
  height: 576,
  backgroundColor: '#0b0d14',
  roundPixels: true,
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  scene: [Preload, Game, UI],
});

// Exposto para testes automatizados.
(window as unknown as { game: Phaser.Game }).game = game;
