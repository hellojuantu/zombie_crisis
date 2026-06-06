const assert = require('assert');
const interpolation = require('../static/js/interpolation.js');

const entity = interpolation.seedSamples({ x: 0, y: 0 }, 0);
assert.deepStrictEqual(entity.samples, [{ t: 0, x: 0, y: 0 }]);

assert.strictEqual(interpolation.pushSample(entity, 100, 0, { t: 100, snapDistance: 120, maxSamples: 8 }), 'sample');
interpolation.interpolateObject(entity, 50);
assert.strictEqual(entity.x, 50);
assert.strictEqual(entity.y, 0);

assert.strictEqual(interpolation.pushSample(entity, 500, 0, { t: 200, snapDistance: 120, maxSamples: 8 }), 'snap');
assert.strictEqual(entity.x, 500);
assert.strictEqual(entity.samples.length, 1);

const capped = interpolation.seedSamples({ x: 0, y: 0 }, 0);
for (let i = 1; i <= 10; i += 1) {
  interpolation.pushSample(capped, i, 0, { t: i, snapDistance: 120, maxSamples: 4 });
}
assert.strictEqual(capped.samples.length, 4);
assert.deepStrictEqual(
  capped.samples.map((s) => s.x),
  [7, 8, 9, 10],
);

const players = {
  me: interpolation.seedSamples({ x: 0, y: 0 }, 0),
  other: interpolation.seedSamples({ x: 0, y: 0 }, 0),
};
interpolation.pushSample(players.me, 100, 0, { t: 100, snapDistance: 120, maxSamples: 8 });
interpolation.pushSample(players.other, 100, 0, { t: 100, snapDistance: 120, maxSamples: 8 });
interpolation.interpolateEntities(players, {}, 'me', 150, 100);
assert.strictEqual(players.me.x, 0);
assert.strictEqual(players.other.x, 50);

console.log('interpolation tests ok');
