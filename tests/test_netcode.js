const assert = require('assert');
const netcode = require('../static/js/netcode.js');

const sigA = netcode.inputSignature({ up: true }, true, false, 0.01, 0.04);
const sigB = netcode.inputSignature({ up: true }, true, false, 0.015, 0.04);
assert.strictEqual(sigA, sigB);

const sigC = netcode.inputSignature({ up: true }, true, false, 0.09, 0.04);
assert.notStrictEqual(sigA, sigC);

assert.strictEqual(
  netcode.shouldSendInput({ force: true, now: 0, lastInputAt: 0, active: true, changed: false }),
  true,
);
assert.strictEqual(netcode.shouldSendInput({ now: 30, lastInputAt: 0, active: true, changed: true }), false);
assert.strictEqual(netcode.shouldSendInput({ now: 70, lastInputAt: 0, active: true, changed: false }), true);
assert.strictEqual(netcode.shouldSendInput({ now: 200, lastInputAt: 0, active: false, changed: false }), false);

console.log('netcode tests ok');
