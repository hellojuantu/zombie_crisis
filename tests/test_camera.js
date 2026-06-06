const assert = require('assert');
const camera = require('../static/js/camera.js');

assert.deepStrictEqual(camera.targetTopLeft(100, 100, { viewportW: 200, viewportH: 200, mapW: 1000, mapH: 1000 }), {
  x: 0,
  y: 0,
});

assert.deepStrictEqual(camera.targetTopLeft(950, 950, { viewportW: 200, viewportH: 200, mapW: 1000, mapH: 1000 }), {
  x: 800,
  y: 800,
});

const cam = camera.createCamera({
  stiffness: 10,
  snapDistance: 500,
  viewportW: 100,
  viewportH: 100,
  mapW: 1000,
  mapH: 1000,
});

cam.snapTo(100, 100);
assert.deepStrictEqual(cam.view(1), { x: 50, y: 50 });

cam.follow(160, 100, 1 / 60);
assert.ok(cam.state.x > 50);
assert.ok(cam.state.x < 110);

cam.follow(900, 900, 1 / 60);
assert.deepStrictEqual(cam.view(1), { x: 850, y: 850 });

const aligned = camera.pixelAlign(10.26, 2);
assert.strictEqual(aligned, 10.5);

console.log('camera tests ok');
