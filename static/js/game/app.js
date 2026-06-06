import { createAudio } from './audio.js?v=39';
import { createEffects } from './effects.js?v=39';
import { createRenderer } from './render.js?v=39';
import { createUI } from './ui.js?v=39';

const { ZCProtocol, ZCPrediction, ZCInterpolation, ZCCamera, ZCTiming, ZCNetcode } = window;

let playerSpeed = 315;
let playerRadius = 17;
let dashDist = 112;
let dashCd = 1.15;
let fireInterval = 0.145;
let muzzleForward = 34;
let mapW = 3400;
let mapH = 3400;
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
const MAX_SAMPLES = 10;
const INPUT_ACTIVE_MS = 66;
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
  softSnap: 34,
  hardSnap: 190,
  softFactor: 0.055,
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

const state = {
  mw: mapW,
  mh: mapH,
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
};

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
  reserveAmmo: 108,
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
  reloadCd: 0,
  xp: 0,
  radius: playerRadius,
  speed: playerSpeed,
};
const visualMe = { x: 0, y: 0, ready: false };

function hpMaxForLevel(level) {
  return 100 + Math.min(45, Math.max(0, level - 1) * 5);
}

function currentWeaponMeta() {
  return weaponTypes[me.weapon] || weaponTypes.pistol || {};
}

function weaponLabelList(list) {
  return (list && list.length ? list : ['pistol'])
    .map((id, idx) => `${idx + 1}.${weaponTypes[id]?.name || id}`)
    .join(' ');
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
  target.reserveAmmo = next.reserveAmmo;
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

function resetState() {
  state.obs = [];
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
  effects.clear();
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

function circleRect(cx, cy, cr, rx, ry, rw, rh) {
  const nx = Math.max(rx, Math.min(cx, rx + rw));
  const ny = Math.max(ry, Math.min(cy, ry + rh));
  return (cx - nx) ** 2 + (cy - ny) ** 2 < cr * cr;
}

function moveLocalOnce(x, y, radius, dx, dy) {
  let nx = Math.max(radius, Math.min(mapW - radius, x + dx));
  let ny = Math.max(radius, Math.min(mapH - radius, y + dy));
  for (const o of state.obs) {
    if (!circleRect(nx, ny, radius, o.x, o.y, o.w, o.h)) continue;
    if (!circleRect(nx, y, radius, o.x, o.y, o.w, o.h)) ny = y;
    else if (!circleRect(x, ny, radius, o.x, o.y, o.w, o.h)) nx = x;
    else {
      nx = x;
      ny = y;
    }
  }
  return [nx, ny];
}

function moveLocal(x, y, radius, dx, dy) {
  const dist = Math.hypot(dx, dy);
  if (dist <= 0.01) return [x, y];
  const steps = Math.max(1, Math.ceil(dist / 14));
  const stepX = dx / steps;
  const stepY = dy / steps;
  let cx = x;
  let cy = y;
  for (let i = 0; i < steps; i += 1) {
    const [nx, ny] = moveLocalOnce(cx, cy, radius, stepX, stepY);
    if (Math.abs(nx - cx) < 0.001 && Math.abs(ny - cy) < 0.001) break;
    cx = nx;
    cy = ny;
  }
  return [cx, cy];
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

function updateVisualMe(dt) {
  if (!visualMe.ready) {
    visualMe.x = me.x;
    visualMe.y = me.y;
    visualMe.ready = true;
    return;
  }
  const err = Math.hypot(me.x - visualMe.x, me.y - visualMe.y);
  if (err > 210) {
    visualMe.x = me.x;
    visualMe.y = me.y;
    return;
  }
  const alpha = 1 - Math.exp(-18 * Math.min(dt, 0.05));
  visualMe.x += (me.x - visualMe.x) * alpha;
  visualMe.y += (me.y - visualMe.y) * alpha;
}

function localDash(nowSeconds) {
  if (!dashReq || me.dead || nowSeconds < localDashReady) return;
  let [dx, dy] = inputDir();
  if (!dx && !dy) {
    dx = Math.cos(me.aim);
    dy = Math.sin(me.aim);
  }
  const sx = me.x;
  const sy = me.y;
  const [nx, ny] = moveLocal(me.x, me.y, me.radius || playerRadius, dx * dashDist, dy * dashDist);
  me.x = nx;
  me.y = ny;
  me.vx = dx * (me.speed || playerSpeed) * 0.22;
  me.vy = dy * (me.speed || playerSpeed) * 0.22;
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
  if (Number.isFinite(data.reserve)) me.reserveAmmo = data.reserve;
  if (state.pl[myId]) {
    state.pl[myId].weapon = me.weapon;
    state.pl[myId].weaponName = me.weaponName;
    state.pl[myId].weapons = me.weapons;
    state.pl[myId].magSize = me.magSize;
    state.pl[myId].ammo = me.ammo;
    state.pl[myId].reserveAmmo = me.reserveAmmo;
  }
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
  const ik = {
    up: !paused && (keys.w || keys.arrowup),
    down: !paused && (keys.s || keys.arrowdown),
    left: !paused && (keys.a || keys.arrowleft),
    right: !paused && (keys.d || keys.arrowright),
  };
  const now = performance.now();
  const dash = paused ? false : dashReq;
  const reload = paused ? false : reloadReq;
  const fire = paused ? false : fireReq;
  const weapon = paused ? '' : weaponReq;
  const aimTarget = worldAimTarget();
  const active = paused || ik.up || ik.down || ik.left || ik.right || shooting || dash || reload || fire || weapon;
  const sig = `${ZCNetcode.inputSignature(ik, paused ? false : shooting, dash, me.aim, AIM_EPS)}|${reload ? 1 : 0}|${fire ? 1 : 0}|${weapon}|${paused ? 1 : 0}`;
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
    reload,
    fire,
    weapon,
    paused,
  });
  inputDirty = false;
  if (dash) dashReq = false;
  if (reload) reloadReq = false;
  if (fire) fireReq = false;
  if (weapon) weaponReq = '';
}

function createSocket() {
  if (typeof window.io !== 'function') {
    ui.setJoinLoading(false);
    ui.notify('联机脚本加载失败', '#ff6666');
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
      weaponOrder = data.cfg.weaponOrder || weaponOrder;
      weaponTypes = data.cfg.weaponTypes || weaponTypes;
      predictor.config.accel = data.cfg.moveAccel || predictor.config.accel;
      predictor.config.decel = data.cfg.moveDecel || predictor.config.decel;
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
    state.mw = mapW;
    state.mh = mapH;
    state.obs = data.obs || [];
    state.features = data.features || [];
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
    me.maxHp = p.maxHp || hpMaxForLevel(me.level);
    visualMe.x = me.x;
    visualMe.y = me.y;
    visualMe.ready = true;
    joined = true;
    joining = false;
    inputSeq = 0;
    inputDirty = true;
    lastInputSig = '';
    dashReq = false;
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
    for (const pid of Object.keys(data.p || {})) {
      const next = mkP(pid, data.p[pid]);
      if (!state.pl[pid]) state.pl[pid] = seedSamples(next, syncT);
      const p = state.pl[pid];
      if (pid === myId) {
        Object.assign(me, {
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
          reserveAmmo: next.reserveAmmo,
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
        predictor.reconcile(me, next, next.ack, state.obs);
        p.x = me.x;
        p.y = me.y;
        applyPlayer(p, next);
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
      reserveAmmo: 108,
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
    ui.notify(`${data.name || 'Boss'} 出现`, data.color || '#ff4d7a');
    effects.ring(data.x, data.y, 150, data.color || '#ff4d7a', 0.68, 5);
    effects.particlesAt(data.x, data.y, data.color || '#ff4d7a', 36, 230, 0.58, 4.4);
    audio.boss();
  });
  sock.on('fog_wave', (data) => {
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
    effects.ring(data.x, data.y, 160, data.col || '#d6eceb', 0.78, 5);
    effects.particlesAt(data.x, data.y, data.col || '#d6eceb', 44, 230, 0.7, 4.2);
    audio.fogWave(data.reason || 'director');
  });
  sock.on('z_leap', (data) => {
    effects.tracer(data.sx, data.sy, data.x, data.y, data.col || '#ffb347');
    effects.ring(data.sx, data.sy, 46, data.col || '#ffb347', 0.24, 3);
    audio.leaper();
  });
  sock.on('z_scream', (data) => {
    effects.ring(data.x, data.y, data.r || 260, data.col || '#d88cff', 0.38, 4);
    effects.particlesAt(data.x, data.y, data.col || '#d88cff', Math.min(28, 8 + (data.buffed || 0)), 140, 0.32, 2.6);
    audio.screamer();
  });
  sock.on('z_explode', (data) => {
    effects.ring(data.x, data.y, data.r || 150, data.col || '#ff8f52', 0.58, 5);
    effects.particlesAt(data.x, data.y, data.col || '#ff8f52', 34, 230, 0.5, 4.1);
    audio.explosion();
  });
  sock.on('grenade_explode', (data) => {
    effects.ring(data.x, data.y, data.r || 150, data.col || '#ff8844', 0.58, 5);
    effects.particlesAt(data.x, data.y, data.col || '#ff8844', 36, 240, 0.5, 4.2);
    audio.explosion();
    if (data.pid === myId) audio.hit();
  });
  sock.on('z_die', (data) => {
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
    state.obj = Object.assign({}, state.obj || {}, { task: data.task || {} });
    markTraining('objective');
    ui.notify(`取得 ${data.name} x${data.count}`, data.col || '#dce7f1');
    audio.pickup();
    effects.ring(data.x, data.y, 58, data.col || '#dce7f1', 0.42, 3);
    effects.particlesAt(data.x, data.y, data.col || '#dce7f1', 18, 130, 0.38, 3);
  });
  sock.on('i_spawn', (data) => {
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
    delete state.items[data.iid];
    effects.ring(data.x, data.y, 46, data.col || '#fff', 0.38, 3);
    effects.particlesAt(data.x, data.y, data.col || '#fff', 16, 120, 0.38, 3);
    if (data.pid === myId) {
      if (Number.isFinite(data.ammo)) me.ammo = data.ammo;
      if (Number.isFinite(data.reserve)) me.reserveAmmo = data.reserve;
      if (Number.isFinite(data.materials)) me.materials = data.materials;
      if (Number.isFinite(data.lore)) me.lore = data.lore;
      if (Number.isFinite(data.weaponLevel)) me.weaponLevel = data.weaponLevel;
      applyWeaponEvent(data);
      me.vehicle = Boolean(data.vehicle);
      const suffix = data.amount && data.amount > 1 ? ` +${data.amount}` : '';
      markTraining('objective');
      ui.notify(`获得 ${data.name}${suffix}`, data.col || '#fff');
      audio.pickup();
    }
  });
  sock.on('ammo_empty', (data) => {
    if (data.pid !== myId) return;
    me.ammo = data.ammo || 0;
    me.reserveAmmo = data.reserve || 0;
    applyWeaponEvent(data);
    ui.notify(data.reserve > 0 ? '换弹中' : '弹药耗尽', data.reserve > 0 ? '#dce7f1' : '#ff6666');
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
    me.reserveAmmo = data.reserve || 0;
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
    ui.notify(`解锁 ${data.weaponName || '新武器'} · ${weaponLabelList(me.weapons)}`, data.col || '#8fd0ff');
    effects.ring(data.x, data.y, 72, data.col || '#8fd0ff', 0.48, 4);
    audio.reward();
  });
  sock.on('weapon_switch', (data) => {
    if (data.pid !== myId) return;
    applyWeaponEvent(data);
    localShotReady = 0;
    ui.notify(`切换 ${me.weaponName}`, data.col || '#dce7f1');
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
    effects.ring(data.x, data.y, 44, data.col || '#ffc247', 0.24, 4);
    effects.particlesAt(data.x, data.y, data.col || '#ffc247', 14, 150, 0.24, 3.2);
    if (data.pid === myId) audio.explosion();
  });
  sock.on('facility_pulse', (data) => {
    if (data.pid !== myId) return;
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
    if (data.pid === myId) ui.notify(data.text || '设施已使用', data.col || '#aee6ff');
    effects.ring(data.x, data.y, 76, data.col || '#aee6ff', 0.46, 4);
    audio.facility(data.facility || '');
  });
  sock.on('lore_found', (data) => {
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
    effects.ring(data.x, data.y, data.r, '#ff8844', 0.62, 5);
    effects.particlesAt(data.x, data.y, '#ffcc66', 42, 260, 0.55, 4);
    if (data.pid === myId) ui.notify(`清场 ${data.kills}`, '#ffcc66');
  });
  sock.on('mission_revealed', (data) => {
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
    if (data.pid === myId) {
      if (Math.hypot(data.x - me.x, data.y - me.y) > 82) {
        me.x = data.x;
        me.y = data.y;
        visualMe.x = data.x;
        visualMe.y = data.y;
      }
    } else if (state.pl[data.pid]) {
      snapObject(state.pl[data.pid], data.x, data.y);
    }
    effects.tracer(data.sx, data.sy, data.x, data.y, data.col || '#fff');
  });
  sock.on('melee_swing', (data) => {
    const col = data.col || '#dce7f1';
    effects.slash(data.x, data.y, data.angle || 0, 72, col, 0.16);
    if (data.hit) effects.particlesAt(data.tx, data.ty, '#dce7f1', 10, 120, 0.22, 2.4);
    if (data.pid === myId) {
      markTraining('shoot');
      audio.melee();
    }
  });
  sock.on('p_die', (data) => {
    if (data.pid === myId) {
      me.dead = true;
      shooting = false;
      audio.playerDeath();
    }
    if (state.pl[data.pid]) state.pl[data.pid].dead = true;
    effects.ring(data.x, data.y, 72, data.col || '#ff6666', 0.5, 4);
    effects.particlesAt(data.x, data.y, '#ff5b61', 26, 150, 0.45, 4);
  });
  sock.on('p_resp', (data) => {
    if (data.pid === myId) {
      me.x = data.x;
      me.y = data.y;
      me.hp = data.hp || me.maxHp;
      me.dead = false;
      visualMe.x = data.x;
      visualMe.y = data.y;
      visualMe.ready = true;
      snapCamera();
    }
    if (state.pl[data.pid]) {
      snapObject(state.pl[data.pid], data.x, data.y);
      state.pl[data.pid].dead = false;
      state.pl[data.pid].hp = data.hp || 100;
    }
    effects.ring(data.x, data.y, 54, '#ffffff', 0.38, 3);
  });
  sock.on('level_up', (data) => {
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
    state.obj = data.obj || state.obj;
    state.mission = data.mission || state.mission;
    state.exits = data.exits || state.exits;
    if (data.obs) {
      state.obs = data.obs;
      state.features = data.features || [];
      state.z = {};
      state.b = {};
      state.items = {};
      state.zt = 0;
      state.bt = 0;
      state.it = 0;
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
  reloadReq = false;
  fireReq = false;
  weaponReq = '';
  me.vx = 0;
  me.vy = 0;
  inputDirty = true;
  ui.setInventoryOpen(open);
  sendInput(true);
}

ui.bindActions(joinGame, restartGame);
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
  if (joined && !me.dead && !inventoryOpen && !inIntermission) {
    if (me.vehicle && me.vehicleCd > 0) me.vehicleCd = Math.max(0, me.vehicleCd - dt);
    localDash(ts / 1000);
    localShotFx(ts / 1000);
    const seq = inputSeq + (dashReq || inputDirty ? 1 : 0);
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
      state.obs,
    );
    if (state.pl[myId]) {
      state.pl[myId].x = me.x;
      state.pl[myId].y = me.y;
      state.pl[myId].aim = me.aim;
      state.pl[myId].hp = me.hp;
      state.pl[myId].score = me.score;
      state.pl[myId].dead = me.dead;
      state.pl[myId].rapid = me.rapid;
      state.pl[myId].spread = me.spread;
      state.pl[myId].prot = me.prot;
      state.pl[myId].level = me.level;
      state.pl[myId].combo = me.combo;
      state.pl[myId].kills = me.kills;
      state.pl[myId].ammo = me.ammo;
      state.pl[myId].magSize = me.magSize;
      state.pl[myId].reserveAmmo = me.reserveAmmo;
      state.pl[myId].materials = me.materials;
      state.pl[myId].lore = me.lore;
      state.pl[myId].weaponLevel = me.weaponLevel;
      state.pl[myId].weapon = me.weapon;
      state.pl[myId].weaponName = me.weaponName;
      state.pl[myId].weapons = me.weapons;
      state.pl[myId].vehicle = me.vehicle;
      state.pl[myId].vehicleCd = me.vehicleCd;
      state.pl[myId].facility = me.facility;
      state.pl[myId].facilityStatus = me.facilityStatus;
      state.pl[myId].reloadCd = me.reloadCd;
      state.pl[myId].radius = me.radius;
      state.pl[myId].speed = me.speed;
    }
  }

  if (joined) updateVisualMe(dt);
  ZCInterpolation.interpolateEntities(state.pl, state.z, myId, ts, interpDelay);
  advanceBullets(dt);
  effects.update(dt);
  if (joined && state.pl[myId]) {
    followCamera(dt);
    updateAim();
  }
  sendInput(dashReq || fireReq || inputDirty);
  sendPing(ts);
  audio.update(nearbyDanger());

  const drawMinimap = ts - lastMinimap > 200;
  renderer.draw(state, me, myId, visualMe, camView, effects, ts, joined, { drawMinimap });
  if (drawMinimap) lastMinimap = ts;
  if (joined && ts - lastHUD > 100) {
    lastHUD = ts;
    ui.updateHUD({
      me,
      state,
      weaponTypes,
      weaponOrder,
      pingMs,
      training,
    });
  }
  requestAnimationFrame(loop);
}

requestAnimationFrame(loop);
