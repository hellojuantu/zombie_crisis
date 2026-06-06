const assert = require('assert');
const prediction = require('../static/js/prediction.js');

assert.deepStrictEqual(
  prediction.inputVector({ right: true, down: true }).map((n) => Number(n.toFixed(3))),
  [0.707, 0.707],
);

let player = { x: 100, y: 100 };
const predictor = prediction.createPredictor({
  speed: 360,
  radius: 16,
  mapW: 3000,
  mapH: 3000,
  hardSnap: 20,
  softSnap: 5,
});

predictor.predict(player, { keys: { right: true } }, 1 / 30, 1, []);
assert.strictEqual(Number(player.x.toFixed(1)), 102);
assert.strictEqual(Number(player.vx.toFixed(1)), 60);
assert.strictEqual(predictor.pending.length, 1);

predictor.reconcile(player, { x: 102, y: 100, vx: 60, vy: 0 }, 1, []);
assert.strictEqual(predictor.pending.length, 0);

predictor.predict(player, { keys: { right: true } }, 1 / 30, 2, []);
predictor.predict(player, { keys: { right: true } }, 1 / 30, 3, []);
assert.strictEqual(Number(player.x.toFixed(1)), 112);
const result = predictor.reconcile(player, { x: 60, y: 100, vx: 0, vy: 0 }, 1, []);

assert.ok(result.error > 20);
assert.strictEqual(predictor.pending.length, 2);
assert.strictEqual(Number(player.x.toFixed(1)), 66);

const blocked = prediction.moveWithCollision(100, 100, 16, 40, 0, 3000, 3000, [{ x: 120, y: 80, w: 40, h: 40 }]);
assert.deepStrictEqual(blocked, [100, 100]);

const tunnelBlocked = prediction.moveWithCollision(100, 100, 16, 150, 0, 3000, 3000, [{ x: 170, y: 80, w: 42, h: 40 }]);
assert.ok(tunnelBlocked[0] < 170 - 16 + 1);
assert.ok(tunnelBlocked[0] > 130);

const softPlayer = { x: 100, y: 100, vx: 0, vy: 0 };
const softPredictor = prediction.createPredictor({
  softSnap: 5,
  hardSnap: 100,
  softFactor: 0.05,
});
const softResult = softPredictor.reconcile(softPlayer, { x: 120, y: 100, vx: 50, vy: 0 }, 0, []);
assert.strictEqual(softResult.error, 20);
assert.strictEqual(Number(softPlayer.x.toFixed(1)), 101);
assert.strictEqual(Number(softPlayer.vx.toFixed(1)), 10);

console.log('prediction tests ok');
