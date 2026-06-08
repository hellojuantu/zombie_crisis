import { createAudio } from './audio.js?v=62';
import { createEffects } from './effects.js?v=62';
import { createRenderer } from './render.js?v=64';
import { createUI } from './ui.js?v=64';

const { ZCProtocol, ZCPrediction, ZCInterpolation, ZCCamera, ZCTiming, ZCNetcode } = window;
const { stageFailedMessage } = window.ZCMessages;
const { sceneMatches: sceneMatchesPayload } = window.ZCSceneFilter;

let playerSpeed = 315;
let playerRadius = 17;
let dashDist = 112;
let dashCd = 1.15;
let fireInterval = 0.145;
let muzzleForward = 34;
let mapW = 3400;
let mapH = 3400;
let moveCollisionStep = 14;
let dynamicAoiMain = 980;
let dynamicAoiRoom = 520;
let vehicleSpeedMult = 1.52;
let weaponOrder = ['pistol', 'rifle', 'shotgun', 'smg', 'launcher'];
let weaponTypes = {
  pistol: {
    name: '手枪',
    mag_size: 24,
    fire_interval: 0.145,
    bullet_speed: 760,
    bullet_life: 0.9,
    pellets: 1,
    spread: 0,
    ammo_cost: 1,
    muzzle: 34,
    color: '#dce7f1',
  },
};

const BASE_INTERP_DELAY = 105;
const SNAP_DIST = 170;
const SELF_VISUAL_SMOOTHING = 30;
const SELF_VISUAL_SNAP = 120;
const MAX_SAMPLES = 10;
const INPUT_ACTIVE_MS = 33;
const INPUT_IDLE_MS = 170;
const AIM_EPS = 0.045;
const SOCKET_OPTIONS = {
  transports: ['websocket'],
  upgrade: false,
  reconnection: true,
  reconnectionDelay: 400,
  reconnectionDelayMax: 2000,
  timeout: 4000,
};

const canvas = document.getElementById('gameCanvas');
const renderer = createRenderer(canvas, document.getElementById('minimap'));
const effects = createEffects();
const audio = createAudio();
const ui = createUI();
const predictor = ZCPrediction.createPredictor({
  speed: playerSpeed,
  radius: playerRadius,
  mapW,
  mapH,
  softSnap: 22,
  hardSnap: 110,
  softFactor: 0.16,
});
const camera = ZCCamera.createCamera({
  stiffness: 18,
  snapDistance: 310,
  mapW,
  mapH,
});
const clockSync = ZCTiming.createClockSync({ smoothing: 0.08 });

let sock = null;
let socketReady = false;
let joining = false;
let joined = false;
let myId = null;
let myCol = '#ffffff';
let myNm = '幸存者';
let keys = {};
let pointerX = window.innerWidth / 2;
let pointerY = window.innerHeight / 2;
let shooting = false;
let dashReq = false;
let interactReq = false;
let reloadReq = false;
let fireReq = false;
let weaponReq = '';
let inventoryOpen = false;
let inputDirty = false;
let inputSeq = 0;
let lastInputAt = 0;
let lastInputSig = '';
let localDashReady = 0;
let localShotReady = 0;
let localMeleeReady = 0;
let lastFireRequestAt = 0;
const pendingShotAnchors = new Map();
let pingSeq = 0;
let pingSent = {};
let pingMs = null;
let lastPingAt = 0;
let interpDelay = BASE_INTERP_DELAY;
let lastHUD = 0;
let lastMinimap = 0;
let camView = { x: 0, y: 0 };
let training = { move: false, aim: false, shoot: false, objective: false };
let scenePayloadReady = true;
let sceneRefreshRequestedAt = 0;
let lastReconcile = { error: 0, pending: 0 };

const state = {
  scene: 'main',
  sceneName: '设施楼层',
  mw: mapW,
  mh: mapH,
  dynamicAoi: dynamicAoiMain,
  obs: [],
  features: [],
  pl: {},
  z: {},
  b: {},
  items: {},
  wave: 1,
  wr: 0,
  zt: 0,
  bt: 0,
  it: 0,
  lb: [],
  obj: {},
  fog: null,
  mission: null,
  exits: [],
  intermission: null,
  perf: {},
};
let collisionObstacles = ZCPrediction.prepareObstacles(state.obs);

const me = {
  x: 0,
  y: 0,
  vx: 0,
  vy: 0,
  aim: 0,
  hp: 100,
  maxHp: 100,
  score: 0,
  kills: 0,
  dead: false,
  rapid: false,
  spread: false,
  prot: false,
  level: 1,
  combo: 0,
  fireCd: 0,
  ammo: 24,
  magSize: 24,
  currentReserve: 108,
  ammoPools: { pistol: 108, rifle: 0, smg: 0, shell: 0, explosive: 0 },
  ammoType: 'pistol',
  ammoTypeName: '手枪弹',
  lives: 3,
  maxLives: 3,
  materials: 0,
  lore: 0,
  weaponLevel: 1,
  weapon: 'pistol',
  weaponName: '手枪',
  weapons: ['pistol'],
  vehicle: false,
  vehicleCd: 0,
  facility: '',
  facilityStatus: '',
  sceneId: 'main',
  sceneName: '设施楼层',
  reloadCd: 0,
  xp: 0,
  radius: playerRadius,
  speed: playerSpeed,
};
const visualMe = { x: 0, y: 0, ready: false };

function resetVisualMe(x = me.x, y = me.y) {
  visualMe.x = x;
  visualMe.y = y;
  visualMe.ready = true;
}

function updateVisualMe(dt) {
  if (!joined || !Number.isFinite(me.x) || !Number.isFinite(me.y)) return;
  if (!visualMe.ready) {
    resetVisualMe();
    return;
  }
  const dx = me.x - visualMe.x;
  const dy = me.y - visualMe.y;
  const dist = Math.hypot(dx, dy);
  if (dist > SELF_VISUAL_SNAP || me.dead || !scenePayloadReady) {
    resetVisualMe();
    return;
  }
  const t = 1 - Math.exp(-SELF_VISUAL_SMOOTHING * Math.min(0.05, dt));
  visualMe.x += dx * t;
  visualMe.y += dy * t;
}

function hpMaxForLevel(level) {
  return 100 + Math.min(45, Math.max(0, level - 1) * 5);
}

function currentWeaponMeta() {
  return weaponTypes[me.weapon] || weaponTypes.pistol || {};
}

const QUIET_PICKUP_TYPES = new Set([
  'ammo',
  'ammo_pistol',
  'ammo_rifle',
  'ammo_smg',
  'ammo_shell',
  'ammo_explosive',
  'parts',
  'medkit',
]);

function shouldNotifyPickup(data) {
  const type = data?.type || '';
  const sceneId = data?.sceneId || state.scene || 'main';
  const inRoom = sceneId !== 'main';
  if (!type) return false;
  if (inRoom && type !== 'lore') return true;
  if (QUIET_PICKUP_TYPES.has(type) || type.startsWith('weapon_')) return false;
  if (type === 'lore') return false;
  return true;
}

function unlockedWeapons() {
  const owned = new Set(me.weapons || ['pistol']);
  const ordered = weaponOrder.filter((id) => owned.has(id));
  return ordered.length ? ordered : ['pistol'];
}

function requestWeaponStep(step) {
  const owned = unlockedWeapons();
  if (owned.length <= 1) {
    ui.notify('还没有其他武器', '#aeb7c2');
    return;
  }
  const current = Math.max(0, owned.indexOf(me.weapon));
  const next = owned[(current + step + owned.length) % owned.length];
  if (!next || next === me.weapon) return;
  weaponReq = next;
  inputDirty = true;
  sendInput(true);
}

function mkP(pid, tuple) {
  return ZCProtocol.decodePlayer(pid, tuple);
}

function mkZ(tuple) {
  return ZCProtocol.decodeZombie(tuple);
}

function mkB(tuple) {
  return ZCProtocol.decodeBullet(tuple);
}

function mkI(tuple) {
  return ZCProtocol.decodeItem(tuple);
}

function seedSamples(entity, t = performance.now()) {
  return ZCInterpolation.seedSamples(entity, t);
}

function pushSample(entity, x, y, t = performance.now()) {
  return ZCInterpolation.pushSample(entity, x, y, { t, snapDistance: SNAP_DIST, maxSamples: MAX_SAMPLES });
}

function snapObject(entity, x, y) {
  return ZCInterpolation.snapObject(entity, x, y, performance.now());
}

function applyPlayer(target, next) {
  target.hp = next.hp;
  target.maxHp = next.maxHp || hpMaxForLevel(next.level);
  target.score = next.score;
  target.dead = next.dead;
  target.rapid = next.rapid;
  target.aim = next.aim;
  target.prot = next.prot;
  target.color = next.color;
  target.name = next.name;
  target.level = next.level;
  target.combo = next.combo;
  target.fireCd = next.fireCd;
  target.ammo = next.ammo;
  target.magSize = next.magSize;
  target.currentReserve = next.currentReserve;
  target.ammoPools = next.ammoPools || {};
  target.ammoType = next.ammoType || 'pistol';
  target.ammoTypeName = next.ammoTypeName || '手枪弹';
  target.lives = next.lives;
  target.maxLives = next.maxLives;
  target.materials = next.materials;
  target.lore = next.lore;
  target.weaponLevel = next.weaponLevel;
  target.weapon = next.weapon;
  target.weaponName = next.weaponName;
  target.weapons = next.weapons;
  target.vehicle = next.vehicle;
  target.vehicleCd = next.vehicleCd;
  target.facility = next.facility;
  target.facilityStatus = next.facilityStatus;
  target.sceneId = next.sceneId || 'main';
  target.sceneName = next.sceneName || '设施楼层';
  target.reloadCd = next.reloadCd;
  target.xp = next.xp;
  target.ack = next.ack;
  target.vx = next.vx || 0;
  target.vy = next.vy || 0;
  target.radius = next.radius;
  target.speed = next.speed;
  target.kills = next.kills;
  target.spread = next.spread;
}

function syncOwnPlayerRenderState() {
  const p = state.pl[myId];
  if (!p) return;
  p.x = visualMe.ready ? visualMe.x : me.x;
  p.y = visualMe.ready ? visualMe.y : me.y;
  applyPlayer(
    p,
    Object.assign({}, p, me, {
      color: p.color || myCol,
      name: p.name || myNm,
      maxHp: me.maxHp || hpMaxForLevel(me.level),
      radius: me.radius || playerRadius,
      speed: me.speed || playerSpeed,
    }),
  );
}

function resetState() {
  state.scene = 'main';
  state.sceneName = '设施楼层';
  state.obs = [];
  collisionObstacles = ZCPrediction.prepareObstacles(state.obs);
  scenePayloadReady = true;
  sceneRefreshRequestedAt = 0;
  state.features = [];
  state.pl = {};
  state.z = {};
  state.b = {};
  state.items = {};
  state.wave = 1;
  state.wr = 0;
  state.zt = 0;
  state.bt = 0;
  state.it = 0;
  state.lb = [];
  state.obj = {};
  state.fog = null;
  state.mission = null;
  state.exits = [];
  state.intermission = null;
  state.perf = {};
  effects.clear();
}

function sceneMatches(data = {}) {
  return sceneMatchesPayload(state.scene, me.sceneId, data);
}

function applyScenePayload(data = {}, clearEntities = true) {
  scenePayloadReady = true;
  sceneRefreshRequestedAt = 0;
  state.scene = data.scene || 'main';
  state.sceneName = data.sceneName || (state.scene === 'main' ? '设施楼层' : '设施内部');
  me.sceneId = state.scene;
  me.sceneName = state.sceneName;
  mapW = data.mw || mapW;
  mapH = data.mh || mapH;
  state.mw = mapW;
  state.mh = mapH;
  predictor.config.mapW = mapW;
  predictor.config.mapH = mapH;
  state.dynamicAoi = Number.isFinite(data.dynamicAoi)
    ? data.dynamicAoi
    : state.scene === 'main'
      ? dynamicAoiMain
      : dynamicAoiRoom;
  if (data.obs) {
    state.obs = data.obs;
    collisionObstacles = ZCPrediction.prepareObstacles(state.obs);
  }
  if (data.features) state.features = data.features;
  if ('mission' in data) state.mission = data.mission || null;
  if (data.exits) state.exits = data.exits;
  if (data.obj) state.obj = Object.assign({}, state.obj || {}, data.obj);
  if (clearEntities) {
    const mine = state.pl[myId];
    state.z = {};
    state.b = {};
    state.items = {};
    state.pl = mine ? { [myId]: mine } : {};
    state.zt = 0;
    state.bt = 0;
    state.it = 0;
    effects.clear();
    predictor.clear();
  }
}

function requestSceneRefresh() {
  const now = performance.now();
  if (!sock || !sock.connected || now - sceneRefreshRequestedAt < 280) return;
  sceneRefreshRequestedAt = now;
  sock.emit('request_scene', {});
}

function resetTraining() {
  training = { move: false, aim: false, shoot: false, objective: false };
}

function markTraining(key) {
  if (training[key]) return;
  training = Object.assign({}, training, { [key]: true });
}

function nearbyDanger() {
  if (!joined) return 0;
  let danger = me.hp < 45 ? 0.8 : 0;
  for (const z of Object.values(state.z)) {
    const dx = (z.x || z.tx || 0) - me.x;
    const dy = (z.y || z.ty || 0) - me.y;
    const dist = Math.hypot(dx, dy);
    if (dist < 280) danger += 0.45;
    else if (dist < 520) danger += 0.18;
  }
  return Math.min(1.6, danger);
}

function visiblePlayerCenter() {
  return visualMe.ready ? visualMe : me;
}

function worldAimTarget() {
  return {
    x: pointerX + camView.x,
    y: pointerY + camView.y,
  };
}

function updateAim() {
  const origin = visiblePlayerCenter();
  const target = worldAimTarget();
  me.aim = Math.atan2(target.y - origin.y, target.x - origin.x);
}

function currentMuzzlePoint(angle = me.aim) {
  const meta = currentWeaponMeta();
  const muzzle = meta.muzzle || muzzleForward;
  const origin = visiblePlayerCenter();
  return {
    x: origin.x + Math.cos(angle) * muzzle,
    y: origin.y + Math.sin(angle) * muzzle,
  };
}

function pruneShotAnchors(now = performance.now()) {
  for (const [seq, anchor] of pendingShotAnchors) {
    if (now - anchor.t > 900) pendingShotAnchors.delete(seq);
  }
}

function rememberShotAnchor(seq, now = performance.now()) {
  if (!seq) return;
  pruneShotAnchors(now);
  const muzzle = currentMuzzlePoint(me.aim);
  pendingShotAnchors.set(seq, {
    x: muzzle.x,
    y: muzzle.y,
    t: now,
  });
}

function shotAnchor(seq) {
  if (!seq) return null;
  const anchor = pendingShotAnchors.get(seq);
  if (!anchor || performance.now() - anchor.t > 900) return null;
  return anchor;
}

function withLocalBulletAnchor(next, existing) {
  if (!next || next.owner !== myId) return next;
  let visualDx = existing?.visualDx;
  let visualDy = existing?.visualDy;
  if (!Number.isFinite(visualDx) || !Number.isFinite(visualDy)) {
    const anchor = shotAnchor(next.shotSeq);
    visualDx = 0;
    visualDy = 0;
    if (anchor) {
      visualDx = anchor.x - next.spawnX;
      visualDy = anchor.y - next.spawnY;
      if (Math.hypot(visualDx, visualDy) > 220) {
        visualDx = 0;
        visualDy = 0;
      }
    }
  }
  if (!visualDx && !visualDy) return Object.assign(next, { visualDx: 0, visualDy: 0 });
  return Object.assign({}, next, {
    x: next.x + visualDx,
    y: next.y + visualDy,
    spawnX: next.spawnX + visualDx,
    spawnY: next.spawnY + visualDy,
    prevX: next.prevX + visualDx,
    prevY: next.prevY + visualDy,
    visualDx,
    visualDy,
  });
}

function inputDir() {
  let dx = (keys.d || keys.arrowright ? 1 : 0) - (keys.a || keys.arrowleft ? 1 : 0);
  let dy = (keys.s || keys.arrowdown ? 1 : 0) - (keys.w || keys.arrowup ? 1 : 0);
  if (dx && dy) {
    dx *= Math.SQRT1_2;
    dy *= Math.SQRT1_2;
  }
  return [dx, dy];
}

function moveLocal(x, y, radius, dx, dy) {
  return ZCPrediction.moveWithCollision(x, y, radius, dx, dy, mapW, mapH, collisionObstacles, moveCollisionStep);
}

function snapCamera() {
  const size = renderer.size();
  camera.snapTo(visualMe.x, visualMe.y, { mapW, mapH, viewportW: size.width, viewportH: size.height });
  camView = camera.view(size.dpr);
}

function followCamera(dt) {
  const size = renderer.size();
  camera.follow(visualMe.x, visualMe.y, dt, { mapW, mapH, viewportW: size.width, viewportH: size.height });
  camView = camera.view(size.dpr);
}

function localDash(nowSeconds) {
  if (!dashReq || me.dead || nowSeconds < localDashReady) return;
  let [dx, dy] = inputDir();
  if (!dx && !dy) {
    dx = Math.cos(me.aim);
    dy = Math.sin(me.aim);
  }
  const origin = visiblePlayerCenter();
  const sx = origin.x;
  const sy = origin.y;
  const nx = sx + dx * dashDist;
  const ny = sy + dy * dashDist;
  localDashReady = nowSeconds + dashCd;
  effects.tracer(sx, sy, nx, ny, myCol);
  effects.ring(nx, ny, 34, myCol, 0.18, 2);
}

function localShotFx(nowSeconds, force = false) {
  if ((!shooting && !force) || me.dead || nowSeconds < localShotReady) return;
  if ((me.reloadCd || 0) > 0 || (me.ammo || 0) <= 0) return;
  const meta = currentWeaponMeta();
  const interval = (meta.fire_interval || meta.fireInterval || fireInterval) * (me.rapid ? 0.58 : 1);
  const ammoCost = Math.max(1, Math.round(meta.ammo_cost || meta.ammoCost || 1));
  localShotReady = nowSeconds + interval;
  me.ammo = Math.max(0, (me.ammo || 0) - ammoCost);
  const pellets = Math.max(1, Math.round(meta.pellets || 1));
  const spread = Number(meta.spread || 0);
  let angles;
  if (pellets <= 1) {
    angles = [me.aim];
  } else {
    angles = Array.from(
      { length: pellets },
      (_, i) => me.aim + (-spread / 2 + (spread * i) / Math.max(1, pellets - 1)),
    );
  }
  if (me.spread) angles = angles.flatMap((angle) => [angle - 0.16, angle, angle + 0.16]);
  const muzzle = meta.muzzle || muzzleForward;
  const speed = meta.bullet_speed || meta.bulletSpeed || 760;
  const life = meta.bullet_life || meta.bulletLife || 0.7;
  const range = Math.max(82, Math.min(230, speed * Math.min(life, 0.24)));
  const col = meta.color || myCol;
  const origin = currentMuzzlePoint(me.aim);
  for (const angle of angles) {
    const x1 = origin.x;
    const y1 = origin.y;
    const x2 = origin.x + Math.cos(angle) * range;
    const y2 = origin.y + Math.sin(angle) * range;
    effects.line(x1, y1, x2, y2, col, 0.055, me.weapon === 'launcher' ? 4 : 2);
  }
}

function hasCloseZombie(range = 88) {
  const limit = range + (me.radius || playerRadius);
  for (const z of Object.values(state.z)) {
    const zr = z.radius || 16;
    if (Math.hypot((z.x || z.tx || 0) - me.x, (z.y || z.ty || 0) - me.y) <= limit + zr) return true;
  }
  return false;
}

function localMeleeFx(nowSeconds) {
  if (me.dead || nowSeconds < localMeleeReady) return;
  localMeleeReady = nowSeconds + 0.32;
  const angle = me.aim;
  const sx = me.x + Math.cos(angle) * 10;
  const sy = me.y + Math.sin(angle) * 10;
  effects.slash(sx, sy, angle, 72, '#dce7f1', 0.15);
}

function requestFire(nowMs, hold = false) {
  if (inventoryOpen) return;
  audio.unlock();
  markTraining('shoot');
  updateAim();
  if (hold) shooting = true;
  fireReq = true;
  inputDirty = true;
  const nowSeconds = nowMs / 1000;
  if (hasCloseZombie() || (me.ammo || 0) <= 0) localMeleeFx(nowSeconds);
  else localShotFx(nowSeconds, true);
  lastFireRequestAt = nowMs;
  sendInput(true);
}

function applyWeaponEvent(data) {
  if (!data) return;
  if (data.weapon) me.weapon = data.weapon;
  if (data.weaponName) me.weaponName = data.weaponName;
  if (Array.isArray(data.weapons)) me.weapons = data.weapons;
  if (Number.isFinite(data.magSize)) me.magSize = data.magSize;
  if (Number.isFinite(data.ammo)) me.ammo = data.ammo;
  if (Number.isFinite(data.currentReserve)) me.currentReserve = data.currentReserve;
  if (data.ammoPools)
    me.ammoPools = typeof data.ammoPools === 'string' ? parseAmmoPools(data.ammoPools) : data.ammoPools;
  if (data.ammoType) me.ammoType = data.ammoType;
  if (data.ammoTypeName) me.ammoTypeName = data.ammoTypeName;
  if (state.pl[myId]) {
    state.pl[myId].weapon = me.weapon;
    state.pl[myId].weaponName = me.weaponName;
    state.pl[myId].weapons = me.weapons;
    state.pl[myId].magSize = me.magSize;
    state.pl[myId].ammo = me.ammo;
    state.pl[myId].currentReserve = me.currentReserve;
    state.pl[myId].ammoPools = me.ammoPools;
    state.pl[myId].ammoType = me.ammoType;
    state.pl[myId].ammoTypeName = me.ammoTypeName;
  }
}

function parseAmmoPools(value) {
  const pools = {};
  String(value || '')
    .split(',')
    .filter(Boolean)
    .forEach((entry) => {
      const [key, raw] = entry.split(':');
      const amount = Number(raw);
      if (key && Number.isFinite(amount)) pools[key] = amount;
    });
  return pools;
}

function updateLatency(rtt) {
  pingMs = pingMs == null ? rtt : pingMs * 0.8 + rtt * 0.2;
  interpDelay = Math.max(BASE_INTERP_DELAY, Math.min(190, BASE_INTERP_DELAY + Math.max(0, pingMs - 25) * 0.6));
  ui.setPing(pingMs);
}

function sendPing(ts) {
  if (!sock || !sock.connected || ts - lastPingAt < 1000) return;
  lastPingAt = ts;
  pingSeq += 1;
  pingSent[pingSeq] = ts;
  sock.emit('client_ping', { seq: pingSeq, t: ts });
  for (const seq of Object.keys(pingSent)) {
    if (ts - pingSent[seq] > 5000) delete pingSent[seq];
  }
}

function sendInput(force = false) {
  if (!sock || !joined) return;
  const paused = inventoryOpen || Boolean(state.intermission?.active);
  const locallyMoving = Math.hypot(me.vx || 0, me.vy || 0) > 2;
  const ik = {
    up: !paused && (keys.w || keys.arrowup),
    down: !paused && (keys.s || keys.arrowdown),
    left: !paused && (keys.a || keys.arrowleft),
    right: !paused && (keys.d || keys.arrowright),
  };
  const now = performance.now();
  const dash = paused ? false : dashReq;
  const interact = paused ? false : interactReq;
  const reload = paused ? false : reloadReq;
  const fire = paused ? false : fireReq;
  const weapon = paused ? '' : weaponReq;
  const aimTarget = worldAimTarget();
  const active =
    paused ||
    locallyMoving ||
    ik.up ||
    ik.down ||
    ik.left ||
    ik.right ||
    shooting ||
    dash ||
    interact ||
    reload ||
    fire ||
    weapon;
  const sig = `${ZCNetcode.inputSignature(ik, paused ? false : shooting, dash, me.aim, AIM_EPS)}|${interact ? 1 : 0}|${reload ? 1 : 0}|${fire ? 1 : 0}|${weapon}|${paused ? 1 : 0}`;
  const changed = sig !== lastInputSig;
  if (
    !ZCNetcode.shouldSendInput({
      force,
      now,
      lastInputAt,
      active,
      changed,
      activeMs: INPUT_ACTIVE_MS,
      idleMs: INPUT_IDLE_MS,
    })
  )
    return;
  lastInputAt = now;
  lastInputSig = sig;
  inputSeq += 1;
  if (!paused && (fire || shooting)) rememberShotAnchor(inputSeq, now);
  sock.emit('player_input', {
    seq: inputSeq,
    keys: ik,
    aim_angle: me.aim,
    aim_x: aimTarget.x,
    aim_y: aimTarget.y,
    shooting: paused ? false : shooting,
    dash,
    interact,
    reload,
    fire,
    weapon,
    paused,
  });
  inputDirty = false;
  if (dash) dashReq = false;
  if (interact) interactReq = false;
  if (reload) reloadReq = false;
  if (fire) fireReq = false;
  if (weapon) weaponReq = '';
}

function createSocket() {
  if (typeof window.io !== 'function') {
    ui.setJoinLoading(false);
    ui.notify('Socket.IO 脚本加载失败', '#ff6666');
    return null;
  }
  return window.io(SOCKET_OPTIONS);
}

function ensureSocket() {
  if (sock) return sock;
  sock = createSocket();
  if (!sock) return null;
  setupSocket();
  return sock;
}

function loadPlayers(players, syncT) {
  for (const pid of Object.keys(players || {})) {
    state.pl[pid] = seedSamples(mkP(pid, players[pid]), syncT);
  }
}

function loadZombies(zombies, syncT) {
  for (const zid of Object.keys(zombies || {})) {
    const z = mkZ(zombies[zid]);
    z.lastHp = z.hp;
    state.z[zid] = seedSamples(z, syncT);
  }
}

function loadBullets(bullets) {
  for (const bid of Object.keys(bullets || {})) state.b[bid] = mkB(bullets[bid]);
}

function loadItems(items) {
  for (const iid of Object.keys(items || {})) state.items[iid] = mkI(items[iid]);
}

function setupSocket() {
  if (socketReady) return;
  socketReady = true;
  sock.on('server_pong', (data) => {
    const sent = pingSent[data.seq];
    if (!sent) return;
    delete pingSent[data.seq];
    updateLatency(performance.now() - sent);
  });
  sock.on('init', (data) => {
    myId = data.id;
    myCol = data.col;
    myNm = data.nm;
    mapW = data.mw;
    mapH = data.mh;
    if (data.cfg) {
      playerSpeed = data.cfg.playerSpeed || playerSpeed;
      playerRadius = data.cfg.playerRadius || playerRadius;
      dashDist = data.cfg.dashDist || dashDist;
      dashCd = data.cfg.dashCd || dashCd;
      fireInterval = data.cfg.fireInterval || fireInterval;
      muzzleForward = data.cfg.muzzleForward || muzzleForward;
      vehicleSpeedMult = data.cfg.vehicleSpeedMult || vehicleSpeedMult;
      dynamicAoiMain = data.cfg.dynamicAoiMain || dynamicAoiMain;
      dynamicAoiRoom = data.cfg.dynamicAoiRoom || dynamicAoiRoom;
      weaponOrder = data.cfg.weaponOrder || weaponOrder;
      weaponTypes = data.cfg.weaponTypes || weaponTypes;
      predictor.config.accel = data.cfg.moveAccel || predictor.config.accel;
      predictor.config.decel = data.cfg.moveDecel || predictor.config.decel;
      predictor.config.collisionStep = data.cfg.moveCollisionStep || predictor.config.collisionStep;
      moveCollisionStep = data.cfg.moveCollisionStep || moveCollisionStep;
    }
    predictor.config.mapW = mapW;
    predictor.config.mapH = mapH;
    predictor.config.speed = playerSpeed;
    predictor.config.radius = playerRadius;
    clockSync.reset();
    predictor.clear();
    const syncT = clockSync.sampleTime(data.time, performance.now());
    resetState();
    resetTraining();
    applyScenePayload(data, false);
    state.wave = data.w || 1;
    state.wr = data.wr || 0;
    state.lb = data.lb || [];
    state.obj = data.obj || {};
    state.mission = data.mission || null;
    state.exits = data.exits || [];
    state.intermission = data.intermission || null;
    loadPlayers(data.pl, syncT);
    loadZombies(data.z, syncT);
    loadBullets(data.b);
    loadItems(data.i);
    state.zt = Object.keys(state.z).length;
    state.bt = Object.keys(state.b).length;
    state.it = Object.keys(state.items).length;

    const p = state.pl[myId];
    Object.assign(me, p);
    me.sceneId = p.sceneId || state.scene;
    me.sceneName = p.sceneName || state.sceneName;
    me.maxHp = p.maxHp || hpMaxForLevel(me.level);
    resetVisualMe();
    joined = true;
    joining = false;
    inputSeq = 0;
    inputDirty = true;
    lastInputSig = '';
    dashReq = false;
    interactReq = false;
    reloadReq = false;
    fireReq = false;
    weaponReq = '';
    localDashReady = 0;
    localShotReady = 0;
    localMeleeReady = 0;
    lastFireRequestAt = 0;
    pingMs = null;
    pingSent = {};
    lastPingAt = 0;
    interpDelay = BASE_INTERP_DELAY;
    snapCamera();
    updateAim();
    ui.showGame(myNm, myCol);
    ui.setAudioOn(audio.enabled);
  });

  sock.on('sync', (data) => {
    const syncT = clockSync.sampleTime(data.time, performance.now());
    if (data.scene && data.scene !== state.scene) {
      state.scene = data.scene;
      state.sceneName = data.sceneName || state.sceneName;
      me.sceneId = state.scene;
      me.sceneName = state.sceneName;
      mapW = data.mw || mapW;
      mapH = data.mh || mapH;
      state.mw = mapW;
      state.mh = mapH;
      predictor.config.mapW = mapW;
      predictor.config.mapH = mapH;
      scenePayloadReady = false;
      collisionObstacles = ZCPrediction.prepareObstacles([]);
      predictor.clear();
      requestSceneRefresh();
    }
    if (Number.isFinite(data.dynamicAoi)) state.dynamicAoi = data.dynamicAoi;
    if (data.perf) state.perf = data.perf;
    for (const pid of Object.keys(data.p || {})) {
      const next = mkP(pid, data.p[pid]);
      if (!state.pl[pid]) state.pl[pid] = seedSamples(next, syncT);
      const p = state.pl[pid];
      if (pid === myId) {
        Object.assign(me, {
          aim: next.aim,
          hp: next.hp,
          maxHp: next.maxHp || hpMaxForLevel(next.level),
          score: next.score,
          dead: next.dead,
          rapid: next.rapid,
          prot: next.prot,
          level: next.level,
          combo: next.combo,
          fireCd: next.fireCd,
          ammo: next.ammo,
          magSize: next.magSize,
          currentReserve: next.currentReserve,
          ammoPools: next.ammoPools || {},
          ammoType: next.ammoType || 'pistol',
          ammoTypeName: next.ammoTypeName || '手枪弹',
          lives: next.lives,
          maxLives: next.maxLives,
          materials: next.materials,
          lore: next.lore,
          weaponLevel: next.weaponLevel,
          weapon: next.weapon,
          weaponName: next.weaponName,
          weapons: next.weapons,
          vehicle: next.vehicle,
          vehicleCd: next.vehicleCd,
          facility: next.facility,
          facilityStatus: next.facilityStatus,
          sceneId: next.sceneId || 'main',
          sceneName: next.sceneName || '设施楼层',
          reloadCd: next.reloadCd,
          xp: next.xp,
          ack: next.ack,
          radius: next.radius,
          speed: next.speed,
          kills: next.kills,
          spread: next.spread,
        });
        predictor.config.radius = me.radius;
        predictor.config.speed = me.speed;
        lastReconcile = predictor.reconcile(me, next, next.ack, collisionObstacles);
        syncOwnPlayerRenderState();
      } else {
        pushSample(p, next.x, next.y, syncT);
        applyPlayer(p, next);
      }
    }
    for (const pid of Object.keys(state.pl)) {
      if (!(pid in (data.p || {})) && pid !== myId) delete state.pl[pid];
    }

    const zdata = data.z || {};
    for (const zid of Object.keys(zdata)) {
      const next = mkZ(zdata[zid]);
      if (state.z[zid]) {
        const z = state.z[zid];
        if (next.hp < z.hp - 0.5) effects.particlesAt(next.x, next.y, '#d8ff8a', 5, 90, 0.22, 2.2);
        pushSample(z, next.x, next.y, syncT);
        Object.assign(z, next);
      } else {
        next.lastHp = next.hp;
        state.z[zid] = seedSamples(next, syncT);
      }
    }
    for (const zid of Object.keys(state.z)) {
      if (!(zid in zdata)) delete state.z[zid];
    }
    state.zt = data.zt ?? Object.keys(state.z).length;

    const bdata = data.b || {};
    for (const bid of Object.keys(bdata)) {
      const rawNext = mkB(bdata[bid]);
      const next = withLocalBulletAnchor(rawNext, state.b[bid]);
      if (state.b[bid]) {
        const b = state.b[bid];
        b.x += (next.x - b.x) * 0.35;
        b.y += (next.y - b.y) * 0.35;
        Object.assign(b, {
          vx: next.vx,
          vy: next.vy,
          color: next.color,
          radius: next.radius,
          owner: next.owner,
          life: next.life,
          weapon: next.weapon,
          explosionRadius: next.explosionRadius,
          damage: next.damage,
          spawnX: next.spawnX,
          spawnY: next.spawnY,
          prevX: next.prevX,
          prevY: next.prevY,
          shotSeq: next.shotSeq,
          visualDx: next.visualDx,
          visualDy: next.visualDy,
        });
      } else {
        state.b[bid] = next;
      }
    }
    for (const bid of Object.keys(state.b)) {
      if (!(bid in bdata)) delete state.b[bid];
    }
    state.bt = data.bt ?? Object.keys(state.b).length;

    const idata = data.i || {};
    state.items = {};
    for (const iid of Object.keys(idata)) state.items[iid] = mkI(idata[iid]);
    state.it = data.it ?? Object.keys(state.items).length;
    state.wave = data.w || state.wave;
    state.wr = data.wr ?? state.wr;
    state.lb = data.lb || state.lb;
    state.obj = data.obj ? Object.assign({}, state.obj || {}, data.obj) : state.obj;
    state.mission = data.mission ? Object.assign({}, state.mission || {}, data.mission) : state.mission;
    if (data.exits) state.exits = data.exits;
    state.intermission = data.intermission || null;
  });

  sock.on('scene_change', (data) => {
    if (data.pid && data.pid !== myId) return;
    applyScenePayload(data, true);
    me.x = Number.isFinite(data.x) ? data.x : me.x;
    me.y = Number.isFinite(data.y) ? data.y : me.y;
    resetVisualMe();
    if (!state.pl[myId]) state.pl[myId] = seedSamples(Object.assign({ id: myId }, me));
    state.pl[myId].x = me.x;
    state.pl[myId].y = me.y;
    state.pl[myId].sceneId = state.scene;
    state.pl[myId].sceneName = state.sceneName;
    snapCamera();
    ui.notify(
      data.reason === 'leave_room' ? '返回设施走廊' : `进入${state.sceneName}`,
      data.reason === 'leave_room' ? '#aee6ff' : '#ffcc66',
    );
    audio.facility(data.reason === 'leave_room' ? '' : 'lab');
  });

  sock.on('p_join', (data) => {
    if (data.pid === myId) return;
    state.pl[data.pid] = seedSamples({
      id: data.pid,
      x: data.x,
      y: data.y,
      tx: data.x,
      ty: data.y,
      hp: 100,
      maxHp: 100,
      score: 0,
      kills: 0,
      dead: false,
      rapid: false,
      spread: false,
      aim: 0,
      prot: true,
      color: data.col,
      name: data.nm,
      level: 1,
      combo: 0,
      fireCd: 0,
      ammo: 24,
      magSize: 24,
      currentReserve: 108,
      ammoPools: { pistol: 108, rifle: 0, smg: 0, shell: 0, explosive: 0 },
      ammoType: 'pistol',
      ammoTypeName: '手枪弹',
      lives: 3,
      maxLives: 3,
      materials: 0,
      lore: 0,
      weaponLevel: 1,
      weapon: 'pistol',
      weaponName: '手枪',
      weapons: ['pistol'],
      vehicle: false,
      vehicleCd: 0,
      facility: '',
      facilityStatus: '',
      sceneId: 'main',
      sceneName: '设施楼层',
      reloadCd: 0,
      xp: 0,
      ack: 0,
      vx: 0,
      vy: 0,
      radius: playerRadius,
      speed: playerSpeed,
    });
  });
  sock.on('p_leave', (data) => delete state.pl[data.pid]);
  sock.on('z_spawn', (data) => {
    if (!sceneMatches(data)) return;
    const z = {
      x: data.x,
      y: data.y,
      tx: data.x,
      ty: data.y,
      hp: data.hp,
      maxHp: data.maxHp,
      type: data.type,
      color: data.color,
      radius: data.radius,
      vx: 0,
      vy: 0,
    };
    state.z[data.id] = seedSamples(z);
    if (data.type === 'boss') {
      effects.ring(data.x, data.y, 120, data.color || '#ff4d7a', 0.55, 5);
    }
  });
  sock.on('boss_spawn', (data) => {
    if (!sceneMatches(data)) return;
    ui.notify(`${data.name || 'Boss'} 出现`, data.color || '#ff4d7a');
    effects.ring(data.x, data.y, 150, data.color || '#ff4d7a', 0.68, 5);
    effects.particlesAt(data.x, data.y, data.color || '#ff4d7a', 36, 230, 0.58, 4.4);
    audio.boss();
  });
  sock.on('boss_phase', (data) => {
    if (!sceneMatches(data)) return;
    ui.notify(data.text || `Boss 进入第 ${data.phase || 1} 阶段`, data.col || '#ff4d7a');
    effects.ring(data.x, data.y, 210 + (data.phase || 1) * 42, data.col || '#ff4d7a', 0.8, 6);
    effects.particlesAt(data.x, data.y, data.col || '#ff4d7a', 52, 280, 0.72, 5);
    audio.boss();
  });
  sock.on('fog_wave', (data) => {
    if (!sceneMatches(data)) return;
    const duration = data.duration || 4.8;
    state.fog = {
      until: performance.now() + duration * 1000,
      duration,
      reason: data.reason || 'silence',
      scene: data.scene || '',
      color: data.col || '#d6eceb',
      x: data.x,
      y: data.y,
      spawnX: data.spawnX,
      spawnY: data.spawnY,
    };
    const reasonText =
      data.scene ||
      {
        armory: '仓库警报',
        medbay: '病房惊醒',
        generator: '供电警报',
        lab: '样本共振',
        terminal: '终端雾袭',
        extraction: '撤离警报',
        silence: '雾里有东西',
        director: '雾袭',
      }[data.reason] ||
      '雾袭';
    const sourceText = data.sourceCount ? ` · 感染源 ${data.sourceCount}` : '';
    ui.notify(`${reasonText}：${data.count || 0} 只感染体靠近${sourceText}`, data.col || '#d6eceb');
    effects.ring(data.x, data.y, 132, data.col || '#d6eceb', 0.48, 4);
    effects.particlesAt(data.x, data.y, data.col || '#d6eceb', 16, 150, 0.42, 3.4);
    audio.fogWave(data.reason || 'director');
  });
  sock.on('z_leap', (data) => {
    if (!sceneMatches(data)) return;
    effects.tracer(data.sx, data.sy, data.x, data.y, data.col || '#ffb347');
    effects.ring(data.sx, data.sy, 46, data.col || '#ffb347', 0.24, 3);
    audio.leaper();
  });
  sock.on('z_scream', (data) => {
    if (!sceneMatches(data)) return;
    effects.ring(data.x, data.y, data.r || 260, data.col || '#d88cff', 0.38, 4);
    effects.particlesAt(data.x, data.y, data.col || '#d88cff', Math.min(28, 8 + (data.buffed || 0)), 140, 0.32, 2.6);
    audio.screamer();
  });
  sock.on('boss_slam', (data) => {
    if (!sceneMatches(data)) return;
    effects.ring(data.x, data.y, data.r || 210, data.col || '#ff4d7a', 0.52, 6);
    effects.particlesAt(data.x, data.y, data.col || '#ff4d7a', 34, 220, 0.46, 4);
    audio.explosion();
  });
  sock.on('z_explode', (data) => {
    if (!sceneMatches(data)) return;
    effects.ring(data.x, data.y, data.r || 150, data.col || '#ff8f52', 0.58, 5);
    effects.particlesAt(data.x, data.y, data.col || '#ff8f52', 34, 230, 0.5, 4.1);
    audio.explosion();
  });
  sock.on('grenade_explode', (data) => {
    if (!sceneMatches(data)) return;
    effects.ring(data.x, data.y, data.r || 150, data.col || '#ff8844', 0.58, 5);
    effects.particlesAt(data.x, data.y, data.col || '#ff8844', 36, 240, 0.5, 4.2);
    audio.explosion();
    if (data.pid === myId) audio.hit();
  });
  sock.on('z_die', (data) => {
    if (!sceneMatches(data)) return;
    const old = state.z[data.zid];
    const x = data.x ?? old?.x ?? 0;
    const y = data.y ?? old?.y ?? 0;
    delete state.z[data.zid];
    effects.blood(x, y);
    effects.particlesAt(x, y, data.col || '#6bd36b', 18, 150, 0.34, 3);
    audio.zombieDeath();
    if (data.pid === myId) effects.ring(x, y, 30, myCol, 0.22, 2);
    if (data.pid === myId) {
      markTraining('shoot');
      audio.hit();
    }
  });
  sock.on('score_gain', (data) => {
    if (data.pid !== myId) return;
    me.score = data.score;
    me.kills = data.kills;
    me.combo = data.combo;
    me.level = data.level;
    if (data.combo > 1 && data.combo % 5 === 0) ui.notify(`连杀 x${data.combo}`, data.col || '#ffc247');
  });
  sock.on('combo_bonus', (data) => {
    if (data.pid !== myId) return;
    if (data.type === 'rapid') me.rapid = true;
    if (data.type === 'spread') me.spread = true;
    if (data.type === 'shield') me.prot = true;
    ui.notify(`${data.name} x${data.combo}`, data.col || '#ffc247');
    effects.ring(data.x, data.y, 78, data.col || '#ffc247', 0.48, 4);
    effects.particlesAt(data.x, data.y, data.col || '#ffc247', 24, 170, 0.42, 3.2);
    audio.reward();
  });
  sock.on('task_update', (data) => {
    if (!sceneMatches(data)) return;
    state.obj = Object.assign({}, state.obj || {}, { task: data.task || {} });
    markTraining('objective');
    ui.notify(`取得 ${data.name} x${data.count}`, data.col || '#dce7f1');
    audio.pickup();
    effects.ring(data.x, data.y, 58, data.col || '#dce7f1', 0.42, 3);
    effects.particlesAt(data.x, data.y, data.col || '#dce7f1', 18, 130, 0.38, 3);
  });
  sock.on('i_spawn', (data) => {
    if (!sceneMatches(data)) return;
    state.items[data.id] = {
      x: data.x,
      y: data.y,
      type: data.type,
      color: data.color,
      icon: data.icon,
      name: data.name,
      radius: data.radius,
    };
  });
  sock.on('item_pick', (data) => {
    if (!sceneMatches(data)) return;
    delete state.items[data.iid];
    effects.ring(data.x, data.y, 46, data.col || '#fff', 0.38, 3);
    effects.particlesAt(data.x, data.y, data.col || '#fff', 16, 120, 0.38, 3);
    if (data.pid === myId) {
      if (Number.isFinite(data.ammo)) me.ammo = data.ammo;
      if (Number.isFinite(data.materials)) me.materials = data.materials;
      if (Number.isFinite(data.lore)) me.lore = data.lore;
      if (Number.isFinite(data.weaponLevel)) me.weaponLevel = data.weaponLevel;
      applyWeaponEvent(data);
      me.vehicle = Boolean(data.vehicle);
      const suffix = data.amount && data.amount > 1 ? ` +${data.amount}` : '';
      markTraining('objective');
      if (shouldNotifyPickup(data)) ui.notify(`获得 ${data.name}${suffix}`, data.col || '#fff');
      audio.pickup();
    }
  });
  sock.on('ammo_empty', (data) => {
    if (data.pid !== myId) return;
    me.ammo = data.ammo || 0;
    applyWeaponEvent(data);
    ui.notify(
      me.currentReserve > 0 ? '换弹中' : `${me.ammoTypeName || '弹药'}耗尽`,
      me.currentReserve > 0 ? '#dce7f1' : '#ff6666',
    );
    audio.empty();
  });
  sock.on('shot_fired', (data) => {
    if (data.pid !== myId) return;
    applyWeaponEvent(data);
    markTraining('shoot');
    audio.shot();
  });
  sock.on('reload_start', (data) => {
    if (data.pid !== myId) return;
    me.reloadCd = data.duration || 1;
    me.ammo = data.ammo || 0;
    applyWeaponEvent(data);
    shooting = false;
    ui.notify('换弹', '#dce7f1');
    audio.reload();
  });
  sock.on('reload_done', (data) => {
    if (data.pid !== myId) return;
    me.reloadCd = 0;
    applyWeaponEvent(data);
    ui.notify('上膛完成', '#48f0a0');
    audio.reload();
  });
  sock.on('talent_upgrade', (data) => {
    if (data.pid !== myId) return;
    me.weaponLevel = data.weaponLevel || me.weaponLevel;
    me.magSize = data.magSize || me.magSize;
    me.maxHp = data.maxHp || me.maxHp;
    me.hp = data.hp || me.hp;
    me.speed = data.speed || me.speed;
    me.materials = Number.isFinite(data.materials) ? data.materials : 0;
    applyWeaponEvent(data);
    state.intermission = data.intermission || state.intermission;
    ui.setIntermission(state.intermission, me);
    ui.notify(`${data.name || '天赋'} Lv.${data.level}`, data.col || '#48f0a0');
    ui.setIntermissionFeedback(`${data.name || '天赋'} 已升级到 Lv.${data.level}`, data.col || '#48f0a0');
    effects.ring(data.x, data.y, 82, data.col || '#48f0a0', 0.5, 4);
    audio.reward();
  });
  sock.on('talent_denied', (data) => {
    if (data.pid !== myId) return;
    ui.notify(data.reason || '无法升级', data.col || '#ffc247');
    ui.setIntermissionFeedback(data.reason || '无法升级', data.col || '#ffc247');
    ui.setIntermission(state.intermission, me);
  });
  sock.on('weapon_unlock', (data) => {
    if (data.pid !== myId) return;
    applyWeaponEvent(data);
    effects.ring(data.x, data.y, 72, data.col || '#8fd0ff', 0.48, 4);
    audio.reward();
  });
  sock.on('weapon_switch', (data) => {
    if (data.pid !== myId) return;
    applyWeaponEvent(data);
    localShotReady = 0;
  });
  sock.on('vehicle_start', (data) => {
    if (data.pid !== myId) return;
    me.vehicle = true;
    me.vehicleCd = data.duration || 10;
    me.speed = Math.max(me.speed || playerSpeed, playerSpeed * (data.speedMult || vehicleSpeedMult));
    ui.notify('维修推车启动：可以撞开近身感染体', data.col || '#ffc247');
    audio.facility('armory');
  });
  sock.on('vehicle_end', (data) => {
    if (data.pid !== myId) return;
    me.vehicle = false;
    me.vehicleCd = 0;
    ui.notify('载具失效', '#aeb7c2');
  });
  sock.on('vehicle_hit', (data) => {
    if (!sceneMatches(data)) return;
    effects.ring(data.x, data.y, 44, data.col || '#ffc247', 0.24, 4);
    effects.particlesAt(data.x, data.y, data.col || '#ffc247', 14, 150, 0.24, 3.2);
    if (data.pid === myId) audio.explosion();
  });
  sock.on('facility_pulse', (data) => {
    if (data.pid !== myId) return;
    if (data.noticeKey === 'enter_prompt') return;
    ui.notify(data.text || '设施响应', data.col || '#aee6ff');
    effects.ring(data.x, data.y, 54, data.col || '#aee6ff', 0.34, 3);
    audio.facility(data.facility || '');
  });
  sock.on('lab_reactor', (data) => {
    if (data.pid !== myId) return;
    ui.notify(data.text || '样本库共振：样本掉落提升', data.col || '#b7ff47');
    effects.ring(data.x, data.y, 118, data.col || '#b7ff47', 0.72, 5);
    effects.particlesAt(data.x, data.y, data.col || '#b7ff47', 36, 210, 0.55, 4);
    audio.facility('lab');
    audio.fogWave('lab');
  });
  sock.on('facility_used', (data) => {
    if (!sceneMatches(data)) return;
    if (data.pid === myId && !data.quiet) ui.notify(data.text || '设施已使用', data.col || '#aee6ff');
    effects.ring(data.x, data.y, 76, data.col || '#aee6ff', 0.46, 4);
    audio.facility(data.facility || '');
  });
  sock.on('lore_found', (data) => {
    if (!sceneMatches(data)) return;
    if (data.pid !== myId) return;
    me.lore = data.count || me.lore;
    ui.notify(data.text || `档案碎片 ${me.lore}`, data.col || '#aee6ff');
    audio.facility('lab');
  });
  sock.on('item_end', (data) => {
    if (data.pid !== myId) return;
    if (data.type === 'rapid') me.rapid = false;
    if (data.type === 'spread') me.spread = false;
    if (data.type === 'shield') me.prot = false;
  });
  sock.on('nuke', (data) => {
    if (!sceneMatches(data)) return;
    effects.ring(data.x, data.y, data.r, '#ff8844', 0.62, 5);
    effects.particlesAt(data.x, data.y, '#ffcc66', 42, 260, 0.55, 4);
    if (data.pid === myId) ui.notify(`清场 ${data.kills}`, '#ffcc66');
  });
  sock.on('mission_revealed', (data) => {
    if (!sceneMatches(data)) return;
    state.exits = state.exits.map((exit) =>
      exit.id === data.id ? Object.assign({}, exit, data, { visible: true }) : exit,
    );
    markTraining('objective');
    ui.notify(`${data.name} 已发现`, data.col || '#ff4d5f');
    audio.extract();
    effects.ring(data.x, data.y, 118, data.col || '#ff4d5f', 0.52, 5);
    effects.particlesAt(data.x, data.y, data.col || '#ff4d5f', 22, 150, 0.42, 3.4);
  });
  sock.on('exit_ready', (data) => {
    if (!sceneMatches(data)) return;
    state.exits = state.exits.map((exit) =>
      exit.id === data.id ? Object.assign({}, exit, data, { visible: true, ready: true }) : exit,
    );
    markTraining('objective');
    ui.notify(`${data.name} 可以撤离`, '#48f0a0');
    audio.extract();
    effects.ring(data.x, data.y, 138, '#48f0a0', 0.72, 5);
    effects.particlesAt(data.x, data.y, '#48f0a0', 26, 180, 0.5, 3.6);
  });
  sock.on('mission_complete', (data) => {
    if (!sceneMatches(data)) return;
    if (state.mission) {
      state.mission.done = true;
      state.mission.charge = 1;
    }
    ui.notify(
      data.ending ? '主线结局已揭露' : `${data.name || '撤离点'} 撤离成功`,
      data.ending ? '#ffb1bd' : '#48f0a0',
    );
    if (data.rewardTitle)
      setTimeout(() => ui.notify(`${data.rewardTitle}: ${data.rewardText || '路线收益已生效'}`, '#aee6ff'), 320);
    if (data.ending) audio.stage(true);
    else audio.extract();
    effects.ring(data.x, data.y, 122, '#44ffaa', 0.62, 5);
    effects.particlesAt(data.x, data.y, '#44ffaa', 32, 180, 0.5, 3.6);
  });
  sock.on('intermission_start', (data) => {
    state.intermission = data || null;
    keys = {};
    shooting = false;
    dashReq = false;
    interactReq = false;
    reloadReq = false;
    fireReq = false;
    weaponReq = '';
    inputDirty = true;
    inventoryOpen = false;
    ui.setInventoryOpen(false);
    ui.setIntermission(state.intermission, me);
    if (data?.ending) audio.stage(true);
  });
  sock.on('p_dash', (data) => {
    if (!sceneMatches(data)) return;
    if (data.pid === myId) {
      me.x = data.x;
      me.y = data.y;
      me.vx = 0;
      me.vy = 0;
      predictor.clear();
      resetVisualMe(data.x, data.y);
      syncOwnPlayerRenderState();
    } else if (state.pl[data.pid]) {
      snapObject(state.pl[data.pid], data.x, data.y);
    }
    effects.tracer(data.sx, data.sy, data.x, data.y, data.col || '#fff');
  });
  sock.on('melee_swing', (data) => {
    if (!sceneMatches(data)) return;
    const col = data.col || '#dce7f1';
    effects.slash(data.x, data.y, data.angle || 0, 72, col, 0.16);
    if (data.hit) effects.particlesAt(data.tx, data.ty, '#dce7f1', 10, 120, 0.22, 2.4);
    if (data.pid === myId) {
      markTraining('shoot');
      audio.melee();
    }
  });
  sock.on('p_die', (data) => {
    if (!sceneMatches(data)) return;
    if (data.pid === myId) {
      me.dead = true;
      me.lives = Number.isFinite(data.lives) ? data.lives : me.lives;
      me.maxLives = Number.isFinite(data.maxLives) ? data.maxLives : me.maxLives;
      shooting = false;
      audio.playerDeath();
    }
    if (state.pl[data.pid]) state.pl[data.pid].dead = true;
    effects.ring(data.x, data.y, 72, data.col || '#ff6666', 0.5, 4);
    effects.particlesAt(data.x, data.y, '#ff5b61', 26, 150, 0.45, 4);
  });
  sock.on('p_resp', (data) => {
    if (data.pid !== myId && !sceneMatches(data)) return;
    if (data.pid === myId) {
      me.x = data.x;
      me.y = data.y;
      me.hp = data.hp || me.maxHp;
      me.lives = Number.isFinite(data.lives) ? data.lives : me.lives;
      me.maxLives = Number.isFinite(data.maxLives) ? data.maxLives : me.maxLives;
      me.dead = false;
      resetVisualMe(data.x, data.y);
      snapCamera();
    }
    if (state.pl[data.pid]) {
      snapObject(state.pl[data.pid], data.x, data.y);
      state.pl[data.pid].dead = false;
      state.pl[data.pid].hp = data.hp || 100;
      state.pl[data.pid].lives = Number.isFinite(data.lives) ? data.lives : state.pl[data.pid].lives;
      state.pl[data.pid].maxLives = Number.isFinite(data.maxLives) ? data.maxLives : state.pl[data.pid].maxLives;
    }
    effects.ring(data.x, data.y, 54, '#ffffff', 0.38, 3);
  });
  sock.on('level_up', (data) => {
    if (!sceneMatches(data)) return;
    if (data.pid === myId) {
      me.level = data.level;
      me.maxHp = hpMaxForLevel(data.level);
      ui.notify(`升级 Lv.${data.level}`, data.col || '#44ffaa');
    }
    effects.ring(data.x, data.y, 90, data.col || '#44ffaa', 0.7, 4);
  });
  sock.on('wave_start', (data) => {
    state.intermission = null;
    ui.setIntermission(null);
    state.wave = data.wave;
    state.wr = data.remaining;
    if (data.obs) {
      applyScenePayload(data, true);
    } else {
      state.obj = data.obj || state.obj;
      state.mission = data.mission || state.mission;
      state.exits = data.exits || state.exits;
    }
    const stageTitle = data.stage?.title || data.obj?.stageTitle;
    ui.notify(
      data.boss ? `第 ${data.wave} 关：重型反应` : `第 ${data.wave} 关：${stageTitle || '未知设施'}`,
      data.boss ? '#ff4d7a' : '#ffcc66',
    );
    audio.stage(Boolean(data.boss));
    if (data.story) setTimeout(() => ui.notify(data.story, data.boss ? '#ff9bb6' : '#aee6ff'), 420);
    if (data.routeReward?.routeHook) setTimeout(() => ui.notify(data.routeReward.routeHook, '#aee6ff'), 760);
  });
  sock.on('wave_clear', (data) => {
    if (!sceneMatches(data)) return;
    ui.notify(`第 ${data.wave} 关撤离`, '#48f0a0');
    audio.extract();
  });
  sock.on('wave_reward', (data) => {
    if (data.pid !== myId) return;
    me.hp = data.hp;
    me.prot = true;
    ui.notify('波次奖励', data.col || '#48f0a0');
    effects.ring(data.x, data.y, 62, data.col || '#48f0a0', 0.46, 3);
    audio.reward();
  });
  sock.on('stage_failed', (data) => {
    ui.notify(stageFailedMessage(data.wave || state.wave, data.reason), '#ff6666');
    if (data.obs) {
      applyScenePayload(data, true);
    } else {
      state.obj = data.obj || state.obj;
      state.mission = data.mission || state.mission;
      state.exits = data.exits || state.exits;
    }
    audio.playerDeath();
  });
  sock.on('stage_restart_denied', (data) => {
    ui.notify(data.reason || '当前不能重开本关', data.col || '#ffc247');
  });
  sock.on('game_restart', () => {
    inventoryOpen = false;
    ui.setInventoryOpen(false);
    ui.setIntermission(null);
    predictor.clear();
    resetState();
    resetTraining();
  });
  sock.on('connect_error', () => {
    joining = false;
    ui.setJoinLoading(false);
    ui.notify('连接失败，请刷新后重试', '#ff6666');
  });
  sock.on('disconnect', () => {
    joined = false;
    joining = false;
    inventoryOpen = false;
    ui.setInventoryOpen(false);
    ui.setIntermission(null);
    predictor.clear();
    ui.showJoin();
    ui.setPing(null);
  });
}

function joinGame() {
  if (joining) return;
  inventoryOpen = false;
  ui.setInventoryOpen(false);
  audio.unlock();
  ui.setAudioOn(audio.enabled);
  joining = true;
  ui.setJoinLoading(true);
  const s = ensureSocket();
  if (!s) {
    joining = false;
    return;
  }
  s.emit('join_game', {});
}

function restartGame() {
  const s = ensureSocket();
  if (!s) return;
  s.emit('restart_game', {});
}

function restartStage() {
  if (!joined) return;
  if (state.intermission?.active) {
    ui.notify('整备中不能重开本关', '#ffc247');
    return;
  }
  const s = ensureSocket();
  if (!s) return;
  inventoryOpen = false;
  ui.setInventoryOpen(false);
  clearInput();
  ui.notify('放弃本关，重新部署...', '#ffb1bd');
  s.emit('restart_stage', {});
}

function continueStage() {
  const s = ensureSocket();
  if (!s || !state.intermission?.active) return;
  s.emit('continue_stage', {});
}

function buyTalent(talent) {
  const s = ensureSocket();
  if (!s || !state.intermission?.active || !talent) return;
  ui.setIntermissionFeedback('改装中...');
  audio.reward();
  s.emit('buy_talent', { talent });
}

function clearInput() {
  keys = {};
  shooting = false;
  dashReq = false;
  interactReq = false;
  reloadReq = false;
  fireReq = false;
  weaponReq = '';
  inputDirty = true;
  sendInput(true);
}

function setInventoryOpen(open) {
  if (!joined || inventoryOpen === open) return;
  inventoryOpen = open;
  keys = {};
  shooting = false;
  dashReq = false;
  interactReq = false;
  reloadReq = false;
  fireReq = false;
  weaponReq = '';
  me.vx = 0;
  me.vy = 0;
  inputDirty = true;
  ui.setInventoryOpen(open);
  if (open) ui.updateInventory(me, state, weaponTypes, weaponOrder);
  sendInput(true);
}

function debugSnapshot() {
  return {
    scene: state.scene,
    scenePayloadReady,
    inputSeq,
    pending: predictor.pending.length,
    reconcile: Object.assign({}, lastReconcile),
    perf: Object.assign({}, state.perf || {}),
    x: Math.round(me.x * 10) / 10,
    y: Math.round(me.y * 10) / 10,
    vx: Math.round((me.vx || 0) * 10) / 10,
    vy: Math.round((me.vy || 0) * 10) / 10,
  };
}

function publishDebugSnapshot() {
  document.documentElement.dataset.zcDebug = JSON.stringify(debugSnapshot());
}

ui.bindActions(joinGame, restartGame, restartStage);
ui.bindAudioToggle(() => {
  audio.setEnabled(!audio.enabled);
  ui.setAudioOn(audio.enabled);
  if (audio.enabled) audio.unlock();
});
ui.bindIntroStart(() => {
  audio.unlock();
  ui.setAudioOn(audio.enabled);
});
ui.bindInventory(
  () => setInventoryOpen(true),
  () => setInventoryOpen(false),
);
ui.bindIntermission(continueStage, buyTalent);

window.addEventListener('keydown', (event) => {
  const key = event.code === 'Space' ? ' ' : event.key.toLowerCase();
  if (
    [
      'w',
      'a',
      's',
      'd',
      'arrowup',
      'arrowdown',
      'arrowleft',
      'arrowright',
      ' ',
      'shift',
      'r',
      'q',
      'e',
      'f',
      'b',
      'escape',
      '1',
      '2',
      '3',
      '4',
      '5',
    ].includes(key)
  )
    event.preventDefault();
  if (key === 'b') {
    if (!keys[key]) setInventoryOpen(!inventoryOpen);
    keys[key] = true;
    return;
  }
  if (key === 'escape' && inventoryOpen) {
    setInventoryOpen(false);
    keys[key] = true;
    return;
  }
  if (inventoryOpen) {
    keys[key] = true;
    return;
  }
  if ((key === 'q' || key === 'e') && !keys[key]) {
    requestWeaponStep(key === 'q' ? -1 : 1);
    keys[key] = true;
    return;
  }
  if (key === 'f' && !keys[key]) {
    interactReq = true;
    inputDirty = true;
    sendInput(true);
    keys[key] = true;
    return;
  }
  if (/^[1-5]$/.test(key)) {
    const weapon = weaponOrder[Number(key) - 1];
    if (weapon && (me.weapons || []).includes(weapon) && weapon !== me.weapon) {
      weaponReq = weapon;
      inputDirty = true;
      sendInput(true);
    }
    keys[key] = true;
    return;
  }
  if (['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(key)) markTraining('move');
  if ((key === ' ' || key === 'shift') && !keys[key]) dashReq = true;
  if (key === 'r' && !keys[key]) reloadReq = true;
  if (!keys[key]) inputDirty = true;
  keys[key] = true;
});
window.addEventListener('keyup', (event) => {
  const key = event.code === 'Space' ? ' ' : event.key.toLowerCase();
  if (keys[key]) inputDirty = true;
  keys[key] = false;
});
canvas.addEventListener('mousemove', (event) => {
  pointerX = event.clientX;
  pointerY = event.clientY;
  markTraining('aim');
});
window.addEventListener(
  'mousemove',
  (event) => {
    pointerX = event.clientX;
    pointerY = event.clientY;
    if (joined) markTraining('aim');
  },
  { passive: true },
);

function ignoreAttackEvent(event) {
  if (!joined || event.button !== 0) return true;
  const target = event.target;
  return (
    inventoryOpen ||
    Boolean(
      target?.closest?.(
        '#join-screen, #hud, #wave-info, #scoreboard, #audioBtn, #inventory-overlay, button, input, textarea, select',
      ),
    )
  );
}

window.addEventListener(
  'mousedown',
  (event) => {
    if (event.button === 2) {
      if (
        !joined ||
        inventoryOpen ||
        event.target?.closest?.(
          '#join-screen, #hud, #wave-info, #scoreboard, #audioBtn, #inventory-overlay, button, input, textarea, select',
        )
      )
        return;
      event.preventDefault();
      pointerX = event.clientX;
      pointerY = event.clientY;
      requestWeaponStep(1);
      return;
    }
    if (ignoreAttackEvent(event)) return;
    pointerX = event.clientX;
    pointerY = event.clientY;
    requestFire(performance.now(), false);
  },
  true,
);
window.addEventListener(
  'click',
  (event) => {
    if (ignoreAttackEvent(event)) return;
    pointerX = event.clientX;
    pointerY = event.clientY;
    const now = performance.now();
    if (now - lastFireRequestAt > 120) requestFire(now, false);
  },
  true,
);
window.addEventListener('mouseup', (event) => {
  if (event.button === 0) {
    shooting = false;
    inputDirty = true;
    sendInput(true);
  }
});
canvas.addEventListener('contextmenu', (event) => event.preventDefault());
window.addEventListener('contextmenu', (event) => {
  if (joined) event.preventDefault();
});
window.addEventListener('blur', clearInput);
document.addEventListener('visibilitychange', () => {
  if (document.hidden) clearInput();
});

function advanceBullets(dt) {
  pruneShotAnchors();
  for (const bid of Object.keys(state.b)) {
    const b = state.b[bid];
    b.prevX = b.x;
    b.prevY = b.y;
    b.x += b.vx * dt;
    b.y += b.vy * dt;
    b.life -= dt;
    if (b.life <= -0.05) delete state.b[bid];
  }
}

let lastFrame = performance.now();
function loop(ts) {
  const dt = Math.min(0.05, (ts - lastFrame) / 1000 || 0);
  lastFrame = ts;

  updateAim();
  const inIntermission = Boolean(state.intermission?.active);
  if (joined) sendInput(dashReq || interactReq || fireReq || inputDirty);
  if (joined && sock?.tick) sock.tick(dt, ts / 1000);
  if (joined && !me.dead && !inventoryOpen && !inIntermission && scenePayloadReady) {
    if (me.vehicle && me.vehicleCd > 0) me.vehicleCd = Math.max(0, me.vehicleCd - dt);
    localDash(ts / 1000);
    localShotFx(ts / 1000);
    const seq = ZCNetcode.predictionSeq(inputSeq, inputDirty);
    predictor.config.speed = me.speed || playerSpeed;
    predictor.config.radius = me.radius || playerRadius;
    predictor.predict(
      me,
      {
        keys: {
          up: keys.w || keys.arrowup,
          down: keys.s || keys.arrowdown,
          left: keys.a || keys.arrowleft,
          right: keys.d || keys.arrowright,
        },
        speedBoost: 1,
      },
      dt,
      seq,
      collisionObstacles,
    );
  }

  if (joined) {
    updateVisualMe(dt);
    syncOwnPlayerRenderState();
  }
  ZCInterpolation.interpolateEntities(state.pl, state.z, myId, ts, interpDelay);
  advanceBullets(dt);
  effects.update(dt);
  if (joined && state.pl[myId]) {
    followCamera(dt);
    updateAim();
  }
  sendInput(false);
  sendPing(ts);
  audio.update(nearbyDanger());

  const drawMinimap = ts - lastMinimap > 200;
  renderer.draw(state, me, myId, visualMe, camView, effects, ts, joined, { drawMinimap });
  if (drawMinimap) lastMinimap = ts;
  if (joined && ts - lastHUD > 100) {
    lastHUD = ts;
    publishDebugSnapshot();
    ui.updateHUD({
      me,
      state,
      weaponTypes,
      weaponOrder,
      pingMs,
      training,
      inventoryOpen,
    });
  }
  requestAnimationFrame(loop);
}

requestAnimationFrame(loop);

window.__zcDebug = debugSnapshot;
