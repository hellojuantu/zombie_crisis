import { createEffects } from './effects.js';
import { createRenderer } from './render.js';
import { createUI } from './ui.js';

const { ZCProtocol, ZCPrediction, ZCInterpolation, ZCCamera, ZCTiming, ZCNetcode } = window;

let playerSpeed = 315;
let playerRadius = 17;
let dashDist = 112;
let dashCd = 1.15;
let fireInterval = 0.145;
let mapW = 3400;
let mapH = 3400;

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
let inputDirty = false;
let inputSeq = 0;
let lastInputAt = 0;
let lastInputSig = '';
let localDashReady = 0;
let localShotReady = 0;
let pingSeq = 0;
let pingSent = {};
let pingMs = null;
let lastPingAt = 0;
let fpsAvg = 60;
let interpDelay = BASE_INTERP_DELAY;
let serverPerf = null;
let lastHUD = 0;
let lastMinimap = 0;
let camView = { x: 0, y: 0 };

const state = {
  mw: mapW,
  mh: mapH,
  obs: [],
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
  base: null,
  mission: null,
  exits: [],
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
  xp: 0,
  radius: playerRadius,
  speed: playerSpeed,
};
const visualMe = { x: 0, y: 0, ready: false };

function hpMaxForLevel(level) {
  return 100 + Math.min(45, Math.max(0, level - 1) * 5);
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
  state.base = null;
  state.mission = null;
  state.exits = [];
  effects.clear();
}

function updateAim() {
  const sx = (visualMe.ready ? visualMe.x : me.x) - camView.x;
  const sy = (visualMe.ready ? visualMe.y : me.y) - camView.y;
  me.aim = Math.atan2(pointerY - sy, pointerX - sx);
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

function moveLocal(x, y, radius, dx, dy) {
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

function localShotFx(nowSeconds) {
  if (!shooting || me.dead || nowSeconds < localShotReady) return;
  const interval = fireInterval * (me.rapid ? 0.58 : 1);
  localShotReady = nowSeconds + interval;
  const angles = me.spread ? [me.aim - 0.16, me.aim, me.aim + 0.16] : [me.aim];
  for (const angle of angles) {
    const x1 = me.x + Math.cos(angle) * 25;
    const y1 = me.y + Math.sin(angle) * 25;
    const x2 = me.x + Math.cos(angle) * 170;
    const y2 = me.y + Math.sin(angle) * 170;
    effects.tracer(x1, y1, x2, y2, myCol);
  }
}

function setTransportStatus() {
  const transport = sock?.io?.engine?.transport?.name;
  if (transport === 'websocket') ui.setNet('websocket', '#48f0a0');
  else if (transport) ui.setNet(transport, '#ffc247');
  else ui.setNet('未连接', '#aaa');
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
  const ik = {
    up: keys.w || keys.arrowup,
    down: keys.s || keys.arrowdown,
    left: keys.a || keys.arrowleft,
    right: keys.d || keys.arrowright,
  };
  const now = performance.now();
  const dash = dashReq;
  const active = ik.up || ik.down || ik.left || ik.right || shooting || dash;
  const sig = ZCNetcode.inputSignature(ik, shooting, dash, me.aim, AIM_EPS);
  const changed = sig !== lastInputSig;
  if (!ZCNetcode.shouldSendInput({ force, now, lastInputAt, active, changed, activeMs: INPUT_ACTIVE_MS, idleMs: INPUT_IDLE_MS })) return;
  lastInputAt = now;
  lastInputSig = sig;
  inputSeq += 1;
  sock.emit('player_input', { seq: inputSeq, keys: ik, aim_angle: me.aim, shooting, dash });
  inputDirty = false;
  if (dash) dashReq = false;
}

function createSocket() {
  if (typeof window.io !== 'function') {
    ui.setJoinLoading(false);
    ui.setNet('脚本失败', '#ff6666');
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
  sock.io.on('reconnect_attempt', setTransportStatus);
  sock.io.on('reconnect', setTransportStatus);
  sock.on('connect', setTransportStatus);
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
    state.mw = mapW;
    state.mh = mapH;
    state.obs = data.obs || [];
    state.wave = data.w || 1;
    state.wr = data.wr || 0;
    state.lb = data.lb || [];
    state.obj = data.obj || {};
    state.base = data.base || null;
    state.mission = data.mission || null;
    state.exits = data.exits || [];
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
    localDashReady = 0;
    localShotReady = 0;
    pingMs = null;
    pingSent = {};
    lastPingAt = 0;
    interpDelay = BASE_INTERP_DELAY;
    snapCamera();
    updateAim();
    ui.showGame(myNm, myCol);
    setTransportStatus();
  });

  sock.on('sync', (data) => {
    serverPerf = data.perf || serverPerf;
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
      const next = mkB(bdata[bid]);
      if (state.b[bid]) {
        const b = state.b[bid];
        b.x += (next.x - b.x) * 0.35;
        b.y += (next.y - b.y) * 0.35;
        Object.assign(b, { vx: next.vx, vy: next.vy, color: next.color, radius: next.radius, owner: next.owner, life: next.life });
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
    state.base = data.base || null;
    state.mission = data.mission ? Object.assign({}, state.mission || {}, data.mission) : state.mission;
    if (data.exits) state.exits = data.exits;
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
    const z = { x: data.x, y: data.y, tx: data.x, ty: data.y, hp: data.hp, maxHp: data.maxHp, type: data.type, color: data.color, radius: data.radius, vx: 0, vy: 0 };
    state.z[data.id] = seedSamples(z);
    if (data.type === 'boss') {
      effects.ring(data.x, data.y, 120, data.color || '#ff4d7a', 0.55, 5);
    }
  });
  sock.on('boss_spawn', (data) => {
    ui.notify(`${data.name || 'Boss'} 出现`, data.color || '#ff4d7a');
    effects.ring(data.x, data.y, 150, data.color || '#ff4d7a', 0.68, 5);
    effects.particlesAt(data.x, data.y, data.color || '#ff4d7a', 36, 230, 0.58, 4.4);
  });
  sock.on('z_leap', (data) => {
    effects.tracer(data.sx, data.sy, data.x, data.y, data.col || '#ffb347');
    effects.ring(data.sx, data.sy, 46, data.col || '#ffb347', 0.24, 3);
  });
  sock.on('z_scream', (data) => {
    effects.ring(data.x, data.y, data.r || 260, data.col || '#d88cff', 0.38, 4);
    effects.particlesAt(data.x, data.y, data.col || '#d88cff', Math.min(28, 8 + (data.buffed || 0)), 140, 0.32, 2.6);
  });
  sock.on('z_explode', (data) => {
    effects.ring(data.x, data.y, data.r || 150, data.col || '#ff8f52', 0.58, 5);
    effects.particlesAt(data.x, data.y, data.col || '#ff8f52', 34, 230, 0.5, 4.1);
  });
  sock.on('z_die', (data) => {
    const old = state.z[data.zid];
    const x = data.x ?? old?.x ?? 0;
    const y = data.y ?? old?.y ?? 0;
    delete state.z[data.zid];
    effects.blood(x, y);
    effects.particlesAt(x, y, data.col || '#6bd36b', 18, 150, 0.34, 3);
    if (data.pid === myId) effects.ring(x, y, 30, myCol, 0.22, 2);
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
  });
  sock.on('task_update', (data) => {
    state.obj = Object.assign({}, state.obj || {}, { task: data.task || {} });
    ui.notify(`取得 ${data.name} x${data.count}`, data.col || '#dce7f1');
    effects.ring(data.x, data.y, 58, data.col || '#dce7f1', 0.42, 3);
    effects.particlesAt(data.x, data.y, data.col || '#dce7f1', 18, 130, 0.38, 3);
  });
  sock.on('i_spawn', (data) => {
    state.items[data.id] = { x: data.x, y: data.y, type: data.type, color: data.color, icon: data.icon, name: data.name, radius: data.radius };
  });
  sock.on('item_pick', (data) => {
    delete state.items[data.iid];
    effects.ring(data.x, data.y, 46, data.col || '#fff', 0.38, 3);
    effects.particlesAt(data.x, data.y, data.col || '#fff', 16, 120, 0.38, 3);
    if (data.pid === myId) ui.notify(`获得 ${data.name}`, data.col || '#fff');
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
    state.exits = state.exits.map((exit) => (exit.id === data.id ? Object.assign({}, exit, data, { visible: true }) : exit));
    ui.notify(`${data.name} 已发现`, data.col || '#ff4d5f');
    effects.ring(data.x, data.y, 118, data.col || '#ff4d5f', 0.52, 5);
    effects.particlesAt(data.x, data.y, data.col || '#ff4d5f', 22, 150, 0.42, 3.4);
  });
  sock.on('mission_complete', (data) => {
    if (state.mission) {
      state.mission.done = true;
      state.mission.charge = 1;
    }
    ui.notify(`${data.name || '撤离点'} 撤离成功`, '#48f0a0');
    effects.ring(data.x, data.y, 122, '#44ffaa', 0.62, 5);
    effects.particlesAt(data.x, data.y, '#44ffaa', 32, 180, 0.5, 3.6);
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
  sock.on('p_die', (data) => {
    if (data.pid === myId) {
      me.dead = true;
      shooting = false;
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
    state.wave = data.wave;
    state.wr = data.remaining;
    state.obj = data.obj || state.obj;
    state.mission = data.mission || state.mission;
    state.exits = data.exits || state.exits;
    state.base = null;
    if (data.obs) {
      state.obs = data.obs;
      state.z = {};
      state.b = {};
      state.items = {};
      state.zt = 0;
      state.bt = 0;
      state.it = 0;
    }
    ui.notify(data.boss ? `第 ${data.wave} 关：重型反应` : `进入第 ${data.wave} 关`, data.boss ? '#ff4d7a' : '#ffcc66');
    if (data.story) setTimeout(() => ui.notify(data.story, data.boss ? '#ff9bb6' : '#aee6ff'), 420);
  });
  sock.on('wave_clear', (data) => {
    ui.notify(`第 ${data.wave} 关撤离`, '#48f0a0');
  });
  sock.on('wave_reward', (data) => {
    if (data.pid !== myId) return;
    me.hp = data.hp;
    me.prot = true;
    ui.notify('波次奖励', data.col || '#48f0a0');
    effects.ring(data.x, data.y, 62, data.col || '#48f0a0', 0.46, 3);
  });
  sock.on('game_restart', () => {
    predictor.clear();
    resetState();
  });
  sock.on('connect_error', () => {
    joining = false;
    ui.setJoinLoading(false);
    ui.setNet('连接失败', '#ff6666');
    ui.notify('连接失败，请刷新后重试', '#ff6666');
  });
  sock.on('disconnect', () => {
    joined = false;
    joining = false;
    predictor.clear();
    ui.showJoin();
    ui.setNet('断开', '#ff6666');
    ui.setPing(null);
  });
}

function joinGame() {
  if (joining) return;
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

function clearInput() {
  keys = {};
  shooting = false;
  dashReq = false;
  inputDirty = true;
  sendInput(true);
}

ui.bindActions(joinGame, restartGame);

window.addEventListener('keydown', (event) => {
  const key = event.code === 'Space' ? ' ' : event.key.toLowerCase();
  if (['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright', ' ', 'shift'].includes(key)) event.preventDefault();
  if ((key === ' ' || key === 'shift') && !keys[key]) dashReq = true;
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
});
canvas.addEventListener('mousedown', (event) => {
  if (event.button === 0) {
    shooting = true;
    inputDirty = true;
  }
  if (event.button === 2) {
    dashReq = true;
    inputDirty = true;
  }
});
window.addEventListener('mouseup', (event) => {
  if (event.button === 0) {
    shooting = false;
    inputDirty = true;
  }
});
canvas.addEventListener('contextmenu', (event) => event.preventDefault());
window.addEventListener('blur', clearInput);
document.addEventListener('visibilitychange', () => {
  if (document.hidden) clearInput();
});

function advanceBullets(dt) {
  for (const bid of Object.keys(state.b)) {
    const b = state.b[bid];
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
  if (dt > 0) fpsAvg = fpsAvg * 0.92 + Math.min(120, 1 / dt) * 0.08;

  updateAim();
  if (joined && !me.dead) {
    localDash(ts / 1000);
    localShotFx(ts / 1000);
    const seq = inputSeq + (dashReq || inputDirty ? 1 : 0);
    predictor.config.speed = me.speed || playerSpeed;
    predictor.config.radius = me.radius || playerRadius;
    predictor.predict(me, {
      keys: {
        up: keys.w || keys.arrowup,
        down: keys.s || keys.arrowdown,
        left: keys.a || keys.arrowleft,
        right: keys.d || keys.arrowright,
      },
      speedBoost: 1,
    }, dt, seq, state.obs);
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
  sendInput(dashReq || inputDirty);
  sendPing(ts);

  const size = renderer.size();
  renderer.draw(state, me, myId, visualMe, camView, effects, ts, joined);
  if (joined && ts - lastHUD > 100) {
    lastHUD = ts;
    ui.updateHUD({
      me,
      state,
      pingMs,
      fps: fpsAvg,
      serverPerf,
      renderScale: size.dpr,
    });
    setTransportStatus();
  }
  if (ts - lastMinimap > 220) lastMinimap = ts;
  requestAnimationFrame(loop);
}

requestAnimationFrame(loop);
