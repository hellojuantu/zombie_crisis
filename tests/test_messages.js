const assert = require('assert');
const { stageFailedMessage } = require('../static/js/game/messages.js');

assert.strictEqual(stageFailedMessage(3, 'abandon'), '第 3 关已放弃，重新部署');
assert.strictEqual(stageFailedMessage(4, 'extraction_failed'), '第 4 关撤离失败，重新部署');
assert.strictEqual(stageFailedMessage(5, 'wipe'), '第 5 关失败，重新部署');
assert.strictEqual(stageFailedMessage(null, 'abandon'), '第 1 关已放弃，重新部署');

console.log('message tests ok');
