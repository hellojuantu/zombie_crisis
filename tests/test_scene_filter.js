const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { sceneMatches } = require('../static/js/game/scene_filter.js');

assert.strictEqual(sceneMatches('room:lab', 'room:lab', { sceneId: 'main' }), false);
assert.strictEqual(sceneMatches('room:lab', 'room:lab', { sceneId: 'room:lab' }), true);
assert.strictEqual(sceneMatches('room:lab', 'main', { sceneId: 'main', pid: 'me' }), true);
assert.strictEqual(sceneMatches('main', 'main', { sceneId: 'main' }), true);
assert.strictEqual(sceneMatches('main', 'main', {}), true);

const browserContext = { window: {} };
browserContext.globalThis = browserContext.window;
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../static/js/game/scene_filter.js'), 'utf8'), browserContext);

assert.strictEqual(typeof browserContext.window.ZCSceneFilter.sceneMatches, 'function');
assert.strictEqual(browserContext.window.ZCSceneFilter.sceneMatches('room:a', 'room:a', { sceneId: 'main' }), false);

console.log('scene filter tests ok');
