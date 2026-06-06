(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.ZCProtocol = api;
})(typeof globalThis !== 'undefined' ? globalThis : window, function () {
  const PROTOCOL_VERSION = 16;

  const PLAYER = Object.freeze({
    X: 0,
    Y: 1,
    HP: 2,
    SCORE: 3,
    DEAD: 4,
    RAPID: 5,
    AIM: 6,
    PROTECTED: 7,
    COLOR: 8,
    NAME: 9,
    LEVEL: 10,
    COMBO: 11,
    FIRE_CD: 12,
    XP: 13,
    ACK: 14,
    VX: 15,
    VY: 16,
    RADIUS: 17,
    SPEED: 18,
    KILLS: 19,
    SPREAD: 20,
    MAX_HP: 21,
    AMMO: 22,
    MAG_SIZE: 23,
    RESERVE_AMMO: 24,
    MATERIALS: 25,
    LORE: 26,
    WEAPON_LEVEL: 27,
    RELOAD_CD: 28,
    WEAPON_ID: 29,
    WEAPON_NAME: 30,
    WEAPONS: 31,
    VEHICLE: 32,
    VEHICLE_CD: 33,
    FACILITY: 34,
    FACILITY_STATUS: 35,
    LENGTH: 36,
  });

  const ZOMBIE = Object.freeze({
    X: 0,
    Y: 1,
    HP: 2,
    TYPE: 3,
    COLOR: 4,
    RADIUS: 5,
    TARGET: 6,
    VX: 7,
    VY: 8,
    MAX_HP: 9,
    LENGTH: 10,
  });

  const BULLET = Object.freeze({
    X: 0,
    Y: 1,
    VX: 2,
    VY: 3,
    COLOR: 4,
    RADIUS: 5,
    OWNER: 6,
    LIFE: 7,
    WEAPON: 8,
    EXPLOSION_RADIUS: 9,
    DAMAGE: 10,
    SPAWN_X: 11,
    SPAWN_Y: 12,
    PREV_X: 13,
    PREV_Y: 14,
    SHOT_SEQ: 15,
    LENGTH: 16,
  });

  const ITEM = Object.freeze({
    X: 0,
    Y: 1,
    TYPE: 2,
    COLOR: 3,
    ICON: 4,
    NAME: 5,
    RADIUS: 6,
    LENGTH: 7,
  });

  function numberAt(tuple, index, fallback) {
    const value = Number(tuple[index]);
    return Number.isFinite(value) ? value : fallback;
  }

  function decodePlayer(pid, tuple) {
    return {
      id: pid,
      x: numberAt(tuple, PLAYER.X, 0),
      y: numberAt(tuple, PLAYER.Y, 0),
      tx: numberAt(tuple, PLAYER.X, 0),
      ty: numberAt(tuple, PLAYER.Y, 0),
      hp: numberAt(tuple, PLAYER.HP, 100),
      maxHp: numberAt(tuple, PLAYER.MAX_HP, 100),
      score: numberAt(tuple, PLAYER.SCORE, 0),
      dead: Boolean(tuple[PLAYER.DEAD]),
      rapid: Boolean(tuple[PLAYER.RAPID]),
      aim: numberAt(tuple, PLAYER.AIM, 0),
      prot: Boolean(tuple[PLAYER.PROTECTED]),
      color: tuple[PLAYER.COLOR] || '#ffffff',
      name: tuple[PLAYER.NAME] || '幸存者',
      level: numberAt(tuple, PLAYER.LEVEL, 1),
      combo: numberAt(tuple, PLAYER.COMBO, 0),
      fireCd: numberAt(tuple, PLAYER.FIRE_CD, 0),
      xp: numberAt(tuple, PLAYER.XP, 0),
      ack: numberAt(tuple, PLAYER.ACK, 0),
      vx: numberAt(tuple, PLAYER.VX, 0),
      vy: numberAt(tuple, PLAYER.VY, 0),
      radius: numberAt(tuple, PLAYER.RADIUS, 17),
      speed: numberAt(tuple, PLAYER.SPEED, 315),
      kills: numberAt(tuple, PLAYER.KILLS, 0),
      spread: Boolean(tuple[PLAYER.SPREAD]),
      ammo: numberAt(tuple, PLAYER.AMMO, 24),
      magSize: numberAt(tuple, PLAYER.MAG_SIZE, 24),
      reserveAmmo: numberAt(tuple, PLAYER.RESERVE_AMMO, 0),
      materials: numberAt(tuple, PLAYER.MATERIALS, 0),
      lore: numberAt(tuple, PLAYER.LORE, 0),
      weaponLevel: numberAt(tuple, PLAYER.WEAPON_LEVEL, 1),
      reloadCd: numberAt(tuple, PLAYER.RELOAD_CD, 0),
      weapon: tuple[PLAYER.WEAPON_ID] || 'pistol',
      weaponName: tuple[PLAYER.WEAPON_NAME] || '手枪',
      weapons: String(tuple[PLAYER.WEAPONS] || 'pistol')
        .split(',')
        .filter(Boolean),
      vehicle: Boolean(tuple[PLAYER.VEHICLE]),
      vehicleCd: numberAt(tuple, PLAYER.VEHICLE_CD, 0),
      facility: tuple[PLAYER.FACILITY] || '',
      facilityStatus: tuple[PLAYER.FACILITY_STATUS] || '',
    };
  }

  function decodeZombie(tuple) {
    return {
      x: numberAt(tuple, ZOMBIE.X, 0),
      y: numberAt(tuple, ZOMBIE.Y, 0),
      tx: numberAt(tuple, ZOMBIE.X, 0),
      ty: numberAt(tuple, ZOMBIE.Y, 0),
      hp: numberAt(tuple, ZOMBIE.HP, 1),
      type: tuple[ZOMBIE.TYPE] || 'walker',
      color: tuple[ZOMBIE.COLOR] || '#6bd36b',
      radius: numberAt(tuple, ZOMBIE.RADIUS, 16),
      target: tuple[ZOMBIE.TARGET] || null,
      vx: numberAt(tuple, ZOMBIE.VX, 0),
      vy: numberAt(tuple, ZOMBIE.VY, 0),
      maxHp: numberAt(tuple, ZOMBIE.MAX_HP, numberAt(tuple, ZOMBIE.HP, 1)),
    };
  }

  function decodeBullet(tuple) {
    return {
      x: numberAt(tuple, BULLET.X, 0),
      y: numberAt(tuple, BULLET.Y, 0),
      vx: numberAt(tuple, BULLET.VX, 0),
      vy: numberAt(tuple, BULLET.VY, 0),
      color: tuple[BULLET.COLOR] || '#ffffff',
      radius: numberAt(tuple, BULLET.RADIUS, 4),
      owner: tuple[BULLET.OWNER] || null,
      life: numberAt(tuple, BULLET.LIFE, 0),
      weapon: tuple[BULLET.WEAPON] || 'pistol',
      explosionRadius: numberAt(tuple, BULLET.EXPLOSION_RADIUS, 0),
      damage: numberAt(tuple, BULLET.DAMAGE, 0),
      spawnX: numberAt(tuple, BULLET.SPAWN_X, numberAt(tuple, BULLET.X, 0)),
      spawnY: numberAt(tuple, BULLET.SPAWN_Y, numberAt(tuple, BULLET.Y, 0)),
      prevX: numberAt(tuple, BULLET.PREV_X, numberAt(tuple, BULLET.SPAWN_X, numberAt(tuple, BULLET.X, 0))),
      prevY: numberAt(tuple, BULLET.PREV_Y, numberAt(tuple, BULLET.SPAWN_Y, numberAt(tuple, BULLET.Y, 0))),
      shotSeq: numberAt(tuple, BULLET.SHOT_SEQ, 0),
    };
  }

  function decodeItem(tuple) {
    return {
      x: numberAt(tuple, ITEM.X, 0),
      y: numberAt(tuple, ITEM.Y, 0),
      type: tuple[ITEM.TYPE] || 'item',
      color: tuple[ITEM.COLOR] || '#ffffff',
      icon: tuple[ITEM.ICON] || '?',
      name: tuple[ITEM.NAME] || '道具',
      radius: numberAt(tuple, ITEM.RADIUS, 14),
    };
  }

  return {
    PROTOCOL_VERSION,
    PLAYER,
    ZOMBIE,
    BULLET,
    ITEM,
    decodePlayer,
    decodeZombie,
    decodeBullet,
    decodeItem,
  };
});
