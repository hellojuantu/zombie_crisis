const assert = require('assert');
const timing = require('../static/js/timing.js');

const clock = timing.createClockSync({ smoothing: 0.1 });

assert.strictEqual(clock.sampleTime(10, 10000), 10000);

const jittered = clock.sampleTime(10.05, 10070);
assert.strictEqual(Number(jittered.toFixed(1)), 10052);
assert.ok(jittered < 10070);

const next = clock.sampleTime(10.1, 10100);
assert.ok(next > jittered);
assert.ok(next <= 10100);

clock.reset();
assert.strictEqual(clock.sampleTime(20, 25000), 25000);

console.log('timing tests ok');
