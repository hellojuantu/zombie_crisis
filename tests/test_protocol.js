const assert = require('assert');
const protocol = require('../static/js/protocol.js');

assert.strictEqual(protocol.PROTOCOL_VERSION, 16);

const player = protocol.decodePlayer('p1', [
  10,
  20,
  88,
  150,
  false,
  true,
  0.75,
  true,
  '#abcdef',
  '测试幸存者',
  3,
  4,
  0.12,
  55,
  42,
  123.4,
  -56.7,
  17,
  322,
  19,
  true,
  110,
  7,
  22,
  80,
  5,
  2,
  4,
  0.8,
  'rifle',
  '步枪',
  'pistol,rifle',
  true,
  6.4,
  '机房',
  '供电已恢复',
]);

assert.deepStrictEqual(
  {
    id: player.id,
    x: player.x,
    y: player.y,
    hp: player.hp,
    maxHp: player.maxHp,
    score: player.score,
    rapid: player.rapid,
    aim: player.aim,
    prot: player.prot,
    level: player.level,
    combo: player.combo,
    fireCd: player.fireCd,
    xp: player.xp,
    ack: player.ack,
    vx: player.vx,
    vy: player.vy,
    radius: player.radius,
    speed: player.speed,
    kills: player.kills,
    spread: player.spread,
    ammo: player.ammo,
    magSize: player.magSize,
    reserveAmmo: player.reserveAmmo,
    materials: player.materials,
    lore: player.lore,
    weaponLevel: player.weaponLevel,
    reloadCd: player.reloadCd,
    weapon: player.weapon,
    weaponName: player.weaponName,
    weapons: player.weapons,
    vehicle: player.vehicle,
    vehicleCd: player.vehicleCd,
    facility: player.facility,
    facilityStatus: player.facilityStatus,
  },
  {
    id: 'p1',
    x: 10,
    y: 20,
    hp: 88,
    maxHp: 110,
    score: 150,
    rapid: true,
    aim: 0.75,
    prot: true,
    level: 3,
    combo: 4,
    fireCd: 0.12,
    xp: 55,
    ack: 42,
    vx: 123.4,
    vy: -56.7,
    radius: 17,
    speed: 322,
    kills: 19,
    spread: true,
    ammo: 7,
    magSize: 22,
    reserveAmmo: 80,
    materials: 5,
    lore: 2,
    weaponLevel: 4,
    reloadCd: 0.8,
    weapon: 'rifle',
    weaponName: '步枪',
    weapons: ['pistol', 'rifle'],
    vehicle: true,
    vehicleCd: 6.4,
    facility: '机房',
    facilityStatus: '供电已恢复',
  },
);

const zombie = protocol.decodeZombie([7, 8, 31, 'runner', '#9dff7a', 13, 'p1', 10, -2, 32]);
assert.strictEqual(zombie.x, 7);
assert.strictEqual(zombie.hp, 31);
assert.strictEqual(zombie.type, 'runner');
assert.strictEqual(zombie.radius, 13);
assert.strictEqual(zombie.maxHp, 32);

const bullet = protocol.decodeBullet([5, 6, 760, 0, '#fff', 4, 'p1', 0.8, 'launcher', 150, 78, 1, 2, 3, 4, 42]);
assert.strictEqual(bullet.vx, 760);
assert.strictEqual(bullet.owner, 'p1');
assert.strictEqual(bullet.weapon, 'launcher');
assert.strictEqual(bullet.explosionRadius, 150);
assert.strictEqual(bullet.spawnX, 1);
assert.strictEqual(bullet.spawnY, 2);
assert.strictEqual(bullet.prevX, 3);
assert.strictEqual(bullet.prevY, 4);
assert.strictEqual(bullet.shotSeq, 42);

const oldBullet = protocol.decodeBullet([5, 6, 760, 0, '#fff', 4, 'p1', 0.8, 'launcher', 150, 78]);
assert.strictEqual(oldBullet.spawnX, 5);
assert.strictEqual(oldBullet.spawnY, 6);
assert.strictEqual(oldBullet.prevX, 5);
assert.strictEqual(oldBullet.prevY, 6);
assert.strictEqual(oldBullet.shotSeq, 0);

const item = protocol.decodeItem([5, 6, 'rapid', '#44ffaa', 'R', '速射', 15]);
assert.strictEqual(item.type, 'rapid');
assert.strictEqual(item.icon, 'R');
assert.strictEqual(item.name, '速射');

const fallback = protocol.decodePlayer('bad', []);
assert.strictEqual(fallback.hp, 100);
assert.strictEqual(fallback.color, '#ffffff');
assert.strictEqual(protocol.decodeCitizen, undefined);
assert.strictEqual(protocol.decodeTreasure, undefined);

console.log('protocol tests ok');
