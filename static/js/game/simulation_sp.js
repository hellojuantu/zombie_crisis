/* Single-player simulation — no WebSocket, runs entirely in-browser.
 * Emits the same events as the server so app.js works unchanged.
 * Dispatches: init, sync, z_spawn, z_die, shot_fired, reload_start, reload_done,
 *   ammo_empty, i_spawn, item_pick, score_gain, combo_bonus, wave_start, wave_clear,
 *   wave_reward, p_die, p_resp, stage_failed, game_restart, task_update,
 *   exit_ready, mission_revealed, mission_complete, intermission_start,
 *   p_dash, melee_swing, fog_wave, level_up, lore_found */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.ZCSimulationSP = api;
})(typeof globalThis !== 'undefined' ? globalThis : window, function () {
  // ─── constants ────────────────────────────────────────────────────────────
  const MAP_W = 3400, MAP_H = 3400;
  const PLAYER_R = 17, PLAYER_SPD = 315;
  const PLAYER_MAX_HP = 100;
  const MOVE_ACCEL = 1900, MOVE_DECEL = 2400;
  const PROTECT_SECS = 2.0;
  const DASH_DIST = 112, DASH_CD = 1.15;
  const MELEE_AUTO_RANGE = 52, MELEE_RANGE = 64;
  const MELEE_ARC = 1.65, MELEE_DAMAGE = 34;
  const MELEE_CD = 0.48, MELEE_KNOCKBACK = 46;
  const MAG_SIZE = 24, START_AMMO = 108, RELOAD_SECS = 1.15;
  const STAGE_LIVES = 3;
  const ZOMBIE_ATK_RANGE = 8;
  const ZOMBIE_SPAWN_DT = 0.12;
  const WAVE_BASE = 92, WAVE_STEP = 24;
  const BOSS_WAVE_INTERVAL = 3;
  const ITEM_R = 15;
  const ITEM_SPAWN_DT = 13.5;
  const MAX_ITEMS = 7;
  const LEVEL_XP_BASE = 90;
  const COMBO_WINDOW = 3.6;
  const COMBO_RAPID_AT = 10, COMBO_SPREAD_AT = 20, COMBO_SHIELD_AT = 30;
  const EXTRACTION_SECS = 3.2;
  const EXTRACT_RADIUS = 78;
  const FOG_WAVE_CD = 16.0;
  const SNAP_HZ = 20;
  const MAZE_CELL = 280, MAZE_WALL = 42;
  const MAZE_EXTRA_LINKS = 8;
  const SPAWN_MIN_DIST = 560, SPAWN_MAX_DIST = 900;
  const TASK_DROP_CHANCE = 0.34;

  const MAX_RESERVE = { pistol: 168, rifle: 108, smg: 216, shell: 42, explosive: 4 };
  const AMMO_PICKUP = { pistol: [18, 32], rifle: [12, 22], smg: [28, 46], shell: [5, 9], explosive: [1, 2] };
  const AMMO_LABELS = { pistol: '手枪弹', rifle: '步枪弹', smg: '冲锋枪弹', shell: '霰弹', explosive: '爆破弹' };

  const WEAPONS = {
    pistol:   { name:'手枪',   mag:24, interval:0.145, reload:1.15, speed:760,  life:0.9,  radius:4.2, damage:26, pellets:1, spread:0,    ammo:'pistol',    muzzle:34, color:'#dce7f1', expR:0,   pierce:0 },
    rifle:    { name:'步枪',   mag:24, interval:0.18,  reload:1.25, speed:940,  life:1.05, radius:4.4, damage:42, pellets:1, spread:0.035, ammo:'rifle',     muzzle:44, color:'#8fd0ff', expR:0,   pierce:1 },
    shotgun:  { name:'散弹枪', mag:8,  interval:0.62,  reload:1.35, speed:720,  life:0.48, radius:4.6, damage:17, pellets:7, spread:0.38,  ammo:'shell',     muzzle:35, color:'#ffc247', expR:0,   pierce:0 },
    smg:      { name:'冲锋枪', mag:36, interval:0.068, reload:1.2,  speed:760,  life:0.72, radius:3.6, damage:16, pellets:1, spread:0.095, ammo:'smg',       muzzle:32, color:'#48f0a0', expR:0,   pierce:0 },
    launcher: { name:'爆破枪', mag:2,  interval:0.86,  reload:1.75, speed:500,  life:1.05, radius:7.2, damage:22, pellets:1, spread:0.02,  ammo:'explosive', muzzle:44, color:'#ff8844', expR:118, pierce:0, expDmg:52 },
  };
  const WEAPON_ORDER = ['pistol','rifle','shotgun','smg','launcher'];

  const ZTYPES = {
    walker:  { hp:46,   speed:104, radius:16, damage:15, score:12, color:'#b8b09d', unlock:1 },
    runner:  { hp:32,   speed:158, radius:13, damage:12, score:16, color:'#d0b38d', unlock:1 },
    crawler: { hp:26,   speed:178, radius:11, damage:9,  score:18, color:'#7b8b8e', unlock:1 },
    shade:   { hp:42,   speed:146, radius:14, damage:16, score:26, color:'#d6eceb', unlock:1 },
    brute:   { hp:132,  speed:72,  radius:24, damage:28, score:38, color:'#8a5b4a', unlock:1 },
    toxic:   { hp:62,   speed:92,  radius:17, damage:20, score:22, color:'#9db64b', unlock:1 },
    armored: { hp:188,  speed:58,  radius:25, damage:34, score:55, color:'#8f98a3', unlock:2 },
    leaper:  { hp:54,   speed:116, radius:15, damage:18, score:32, color:'#c88b61', unlock:2 },
    screamer:{ hp:72,   speed:86,  radius:18, damage:12, score:44, color:'#b68abf', unlock:3 },
    bloater: { hp:118,  speed:66,  radius:23, damage:24, score:46, color:'#b8694a', unlock:3 },
    stalker: { hp:66,   speed:192, radius:13, damage:19, score:34, color:'#cfd2ff', unlock:2 },
    boss:    { hp:2400, speed:86,  radius:43, damage:58, score:560,color:'#d9445f', unlock:3 },
  };
  const ZTYPE_POOL_BY_WAVE = [
    ['walker','runner','crawler','shade','brute'],
    ['walker','runner','crawler','shade','brute','toxic'],
    ['walker','runner','crawler','shade','brute','toxic','armored','leaper'],
    ['walker','runner','crawler','shade','brute','toxic','armored','leaper','screamer','bloater','stalker'],
  ];

  const ITEM_TYPES = {
    rapid:    { color:'#44ffaa', icon:'R',  name:'速射',     weight:2 },
    spread:   { color:'#ffcc44', icon:'3',  name:'三连发',   weight:2 },
    shield:   { color:'#ffffff', icon:'S',  name:'护盾',     weight:1 },
    medkit:   { color:'#ff6688', icon:'+',  name:'医疗包',   weight:3 },
    ammo:     { color:'#dce7f1', icon:'A',  name:'弹药包',   weight:3 },
    parts:    { color:'#8fd0ff', icon:'P',  name:'武器零件', weight:2 },
    nuke:     { color:'#ff8844', icon:'!',  name:'清场炸弹', weight:1 },
    weapon_rifle:    { color:'#8fd0ff', icon:'AR',  name:'步枪箱',   weight:0 },
    weapon_shotgun:  { color:'#ffc247', icon:'SG',  name:'散弹枪箱', weight:0 },
    weapon_smg:      { color:'#48f0a0', icon:'SMG', name:'冲锋枪箱', weight:0 },
    weapon_launcher: { color:'#ff8844', icon:'EX',  name:'爆破枪箱', weight:0 },
    vehicle:  { color:'#ffc247', icon:'V',  name:'维修推车', weight:0 },
    fuse:     { color:'#66d9ff', icon:'F',  name:'保险丝',   weight:0, task:true },
    sample:   { color:'#b7ff47', icon:'V',  name:'病毒样本', weight:0, task:true },
    keycard:  { color:'#d98cff', icon:'K',  name:'门禁卡',   weight:0, task:true },
    lore:     { color:'#aee6ff', icon:'D',  name:'档案碎片', weight:0 },
  };

  const STORY_BEATS = [
    '第 {wave} 关：耳机里只剩呼吸声，撤离门藏在黑暗深处。',
    '墙后有东西在拖行，别在同一条走廊停太久。',
    '应急灯一闪一灭，地图结构已经和上一层完全不同。',
    '地面有新鲜抓痕，撤离点附近一定有更重的东西。',
    '广播重复着不存在的坐标，真正的出口不会主动暴露。',
    '设施深处传来尖叫，尸群正在向脚步声聚拢。',
    '血雾从通风管漏下来，补给越来越少。',
    '铁门还没开完，撑住最后几秒，不要回头。',
  ];

  const STAGE_TITLES = ['深层设施', '防疫隔离区', '地下实验室', '安保禁区', '核心舱室', '最终层级'];

  // ─── math helpers ─────────────────────────────────────────────────────────
  const rng = () => Math.random();
  const rngInt = (lo, hi) => lo + Math.floor(rng() * (hi - lo + 1));
  const rngChoice = (arr) => arr[Math.floor(rng() * arr.length)];
  const rngShuffle = (arr) => { for (let i = arr.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); [arr[i], arr[j]] = [arr[j], arr[i]]; } return arr; };
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const dist2 = (ax, ay, bx, by) => (ax - bx) ** 2 + (ay - by) ** 2;
  const circleRect = (cx, cy, cr, rx, ry, rw, rh) => {
    const nx = Math.max(rx, Math.min(cx, rx + rw));
    const ny = Math.max(ry, Math.min(cy, ry + rh));
    return (cx - nx) ** 2 + (cy - ny) ** 2 < cr * cr;
  };
  const approach = (cur, tgt, step) => cur < tgt ? Math.min(tgt, cur + step) : cur > tgt ? Math.max(tgt, cur - step) : cur;

  // ─── collision ────────────────────────────────────────────────────────────
  function moveOnce(x, y, r, dx, dy, obs) {
    let nx = clamp(x + dx, r, MAP_W - r);
    let ny = clamp(y + dy, r, MAP_H - r);
    for (const o of obs) {
      if (!circleRect(nx, ny, r, o.x, o.y, o.w, o.h)) continue;
      if (!circleRect(nx, y, r, o.x, o.y, o.w, o.h)) { ny = y; continue; }
      if (!circleRect(x, ny, r, o.x, o.y, o.w, o.h)) { nx = x; continue; }
      nx = x; ny = y;
    }
    return [nx, ny];
  }

  function moveWithCollision(x, y, r, dx, dy, obs, step = 14) {
    const d = Math.hypot(dx, dy);
    if (d <= 0.01) return [x, y];
    const n = Math.max(1, Math.ceil(d / step));
    const sx = dx / n, sy = dy / n;
    let cx = x, cy = y;
    for (let i = 0; i < n; i++) {
      const [nx, ny] = moveOnce(cx, cy, r, sx, sy, obs);
      if (Math.abs(nx - cx) < 0.001 && Math.abs(ny - cy) < 0.001) break;
      cx = nx; cy = ny;
    }
    return [cx, cy];
  }

  function resolveOverlap(x, y, r, obs) {
    let cx = clamp(x, r, MAP_W - r), cy = clamp(y, r, MAP_H - r);
    for (let pass = 0; pass < 3; pass++) {
      let moved = false;
      for (const o of obs) {
        const nearX = Math.max(o.x, Math.min(cx, o.x + o.w));
        const nearY = Math.max(o.y, Math.min(cy, o.y + o.h));
        const ddx = cx - nearX, ddy = cy - nearY;
        const dSq = ddx * ddx + ddy * ddy;
        if (dSq >= r * r) continue;
        if (dSq > 0.0001) {
          const dist = Math.sqrt(dSq);
          cx += (ddx / dist) * (r - dist + 0.35);
          cy += (ddy / dist) * (r - dist + 0.35);
        } else { cx = o.x - r - 0.35; }
        cx = clamp(cx, r, MAP_W - r); cy = clamp(cy, r, MAP_H - r);
        moved = true;
      }
      if (!moved) break;
    }
    return [cx, cy];
  }

  function nearObs(obstacles, x, y, pad = 80) {
    return obstacles.filter(o =>
      x + pad > o.x && x - pad < o.x + o.w &&
      y + pad > o.y && y - pad < o.y + o.h
    );
  }

  // ─── maze generation ──────────────────────────────────────────────────────
  function genMaze(wave) {
    const layouts = [[12, 9], [10, 11], [9, 12], [11, 10]];
    const [cols, rows] = layouts[(wave - 1) % layouts.length];
    const marginX = (MAP_W - cols * MAZE_CELL) / 2;
    const marginY = (MAP_H - rows * MAZE_CELL) / 2;
    const mid = Math.floor(rows / 2);
    const start = [0, mid];
    const active = new Set();
    const key = (c, r) => `${c},${r}`;

    const addCell = (c, r) => { if (c >= 0 && c < cols && r >= 0 && r < rows) active.add(key(c, r)); };
    const carve = (ac, ar, bc, br) => {
      const sc = bc >= ac ? 1 : -1;
      for (let c = ac; c !== bc + sc; c += sc) addCell(c, ar);
      const sr = br >= ar ? 1 : -1;
      for (let r = ar; r !== br + sr; r += sr) addCell(bc, r);
    };

    for (let c = 0; c < cols; c++) addCell(c, mid);

    const branches = 8 + Math.min(7, wave);
    for (let i = 0; i < branches; i++) {
      const c = rngInt(1, cols - 2);
      const dir = (i + wave) % 2 === 0 ? -1 : 1;
      const len = rngInt(2, Math.max(3, Math.floor(rows / 2)));
      const endR = clamp(mid + dir * len, 0, rows - 1);
      carve(c, mid, c, endR);
      if (rng() < 0.72) addCell(clamp(c + (rng() < 0.5 ? -1 : 1), 0, cols - 1), endR);
    }

    const visited = new Set([key(...start)]);
    const openings = new Map();
    const stack = [[...start]];
    const getOpen = (c, r) => { const k = key(c, r); if (!openings.has(k)) openings.set(k, new Set()); return openings.get(k); };
    const neighbors = (c, r) => {
      const ns = [];
      if (active.has(key(c - 1, r))) ns.push(['W', c - 1, r, 'E']);
      if (active.has(key(c + 1, r))) ns.push(['E', c + 1, r, 'W']);
      if (active.has(key(c, r - 1))) ns.push(['N', c, r - 1, 'S']);
      if (active.has(key(c, r + 1))) ns.push(['S', c, r + 1, 'N']);
      return rngShuffle(ns);
    };

    while (stack.length && visited.size < active.size) {
      const [cc, cr] = stack[stack.length - 1];
      const cands = neighbors(cc, cr).filter(([, nc, nr]) => !visited.has(key(nc, nr)));
      if (!cands.length) {
        stack.pop();
        if (!stack.length) {
          const missing = [...active].filter(k => !visited.has(k));
          if (missing.length) {
            const [mc, mr] = missing[0].split(',').map(Number);
            carve(start[0], start[1], mc, mr);
            visited.add(key(mc, mr));
            stack.push([mc, mr]);
          }
        }
        continue;
      }
      const [dir, nc, nr, back] = cands[0];
      getOpen(cc, cr).add(dir);
      getOpen(nc, nr).add(back);
      visited.add(key(nc, nr));
      stack.push([nc, nr]);
    }

    const extraLinks = Math.max(4, MAZE_EXTRA_LINKS + Math.min(4, Math.floor(wave / 2)));
    const activeList = [...active].map(k => k.split(',').map(Number));
    for (let i = 0; i < extraLinks; i++) {
      const [lc, lr] = rngChoice(activeList);
      const ns = neighbors(lc, lr);
      if (!ns.length) continue;
      const [dir, nc, nr, back] = rngChoice(ns);
      getOpen(lc, lr).add(dir);
      getOpen(nc, nr).add(back);
    }

    const center = (c, r) => ({ x: marginX + c * MAZE_CELL + MAZE_CELL / 2, y: marginY + r * MAZE_CELL + MAZE_CELL / 2 });
    const floorPoints = activeList.map(([c, r]) => center(c, r));
    const spawnPoint = center(...start);
    const extractCell = activeList.reduce((best, cell) => {
      const [bc, br] = best, [cc, cr] = cell;
      return (cc - start[0]) ** 2 + (cr - start[1]) ** 2 > (bc - start[0]) ** 2 + (br - start[1]) ** 2 ? cell : best;
    }, activeList[0]);
    const extractPoint = center(...extractCell);

    const wallKeys = new Set();
    const obstacles = [];
    const w = MAZE_WALL;

    const addWall = (x, y, ww, hh, kind = 'wall') => {
      const k = `${Math.round(x * 10)},${Math.round(y * 10)},${Math.round(ww * 10)},${Math.round(hh * 10)},${kind}`;
      if (wallKeys.has(k)) return;
      wallKeys.add(k);
      obstacles.push({ x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10, w: Math.round(ww * 10) / 10, h: Math.round(hh * 10) / 10, kind });
    };

    for (const [cc, cr] of activeList) {
      const cx = marginX + cc * MAZE_CELL;
      const cy = marginY + cr * MAZE_CELL;
      const op = getOpen(cc, cr);
      if (!op.has('N')) addWall(cx - w / 2, cy - w / 2, MAZE_CELL + w, w);
      if (!op.has('S')) addWall(cx - w / 2, cy + MAZE_CELL - w / 2, MAZE_CELL + w, w);
      if (!op.has('W')) addWall(cx - w / 2, cy - w / 2, w, MAZE_CELL + w);
      if (!op.has('E')) addWall(cx + MAZE_CELL - w / 2, cy - w / 2, w, MAZE_CELL + w);
    }

    const features = [];
    const propCells = activeList.filter(([c, r]) => !(c === start[0] && r === start[1]) && Math.abs(c - start[0]) + Math.abs(r - start[1]) > 3);
    rngShuffle(propCells);
    const propKinds = ['crate', 'locker', 'generator', 'tank', 'gurney'];
    for (let i = 0; i < Math.min(18, 8 + wave * 2) && i < propCells.length; i++) {
      const [pc, pr] = propCells[i];
      const { x: px, y: py } = center(pc, pr);
      if (rng() < 0.28) {
        const kind = propKinds[i % propKinds.length];
        let pw = 54, ph = 46;
        if (kind === 'locker' || kind === 'gurney') [pw, ph] = rng() < 0.5 ? [72, 30] : [30, 72];
        else if (kind === 'generator') [pw, ph] = [78, 54];
        else if (kind === 'tank') [pw, ph] = [52, 52];
        addWall(px - pw / 2, py - ph / 2, pw, ph, kind);
      } else if (rng() < 0.5) {
        features.push({ kind: rngChoice(['blood', 'light', 'warning', 'pool']), x: Math.round(px + (rng() - 0.5) * 108), y: Math.round(py + (rng() - 0.5) * 108), w: Math.round(34 + rng() * 52), h: Math.round(18 + rng() * 44) });
      }
    }

    return { obstacles, features, floorPoints, spawnPoint, extractPoint };
  }

  // ─── LocalTransport ───────────────────────────────────────────────────────
  class LocalTransport {
    constructor() {
      this._handlers = {};
      this._sim = null;
      this.connected = true;
    }
    on(event, handler) {
      if (!this._handlers[event]) this._handlers[event] = [];
      this._handlers[event].push(handler);
    }
    emit(event, data) {
      if (this._sim) this._sim.handleClientEvent(event, data || {});
    }
    dispatch(event, data) {
      for (const h of this._handlers[event] || []) { try { h(data); } catch (_) {} }
    }
    tick(dt, now) {
      if (this._sim && this._sim.running) this._sim.tick(dt, now);
    }
    bindSimulation(sim) {
      this._sim = sim;
      sim.transport = this;
    }
  }

  // ─── Simulation ───────────────────────────────────────────────────────────
  class Simulation {
    constructor() {
      this.transport = null;
      this.running = false;
      this.player = null;
      this.zombies = new Map();
      this.bullets = new Map();
      this.items = new Map();
      this.obstacles = [];
      this.features = [];
      this.floorPoints = [];
      this.spawnPoint = { x: MAP_W / 2, y: MAP_H / 2 };
      this.extractPoint = { x: MAP_W / 2 + 500, y: MAP_H / 2 };
      this.wave = 0;
      this.waveRemaining = 0;
      this.waveSpawnQueue = 0;
      this.lastSpawn = 0;
      this.lastItemSpawn = 0;
      this.lastSnapshot = 0;
      this.lastFog = 0;
      this.exitData = null;
      this.exitCharging = false;
      this.extractCharge = 0;
      this.stageCleared = false;
      this.intermission = null;
      this.taskCounts = { fuse: 0, sample: 0, keycard: 0 };
      this.now = 0;
      this._zid = 0;
      this._bid = 0;
      this._iid = 0;
    }

    handleClientEvent(event, data) {
      switch (event) {
        case 'join_game':    this.start(); break;
        case 'player_input': this._applyInput(data); break;
        case 'restart_game': this._restartGame(); break;
        case 'restart_stage': this._restartStage(); break;
        case 'continue_stage': this._continueStage(); break;
        case 'buy_talent': break; // no talents in SP
        case 'client_ping': this.transport.dispatch('server_pong', { seq: data.seq, t: data.t }); break;
        case 'request_scene': this._sendScenePayload(); break;
      }
    }

    start() {
      if (this.running) return;
      this.running = true;
      this._newStage(1);
    }

    _newStage(wave) {
      this.wave = wave;
      const { obstacles, features, floorPoints, spawnPoint, extractPoint } = genMaze(wave);
      this.obstacles = obstacles;
      this.features = features;
      this.floorPoints = floorPoints;
      this.spawnPoint = spawnPoint;
      this.extractPoint = extractPoint;
      this.zombies.clear();
      this.bullets.clear();
      this.items.clear();
      this.taskCounts = { fuse: 0, sample: 0, keycard: 0 };
      this.stageCleared = false;
      this.exitCharging = false;
      this.extractCharge = 0;
      this.lastFog = this.now;

      const isBoss = wave % BOSS_WAVE_INTERVAL === 0;
      const budget = WAVE_BASE + (wave - 1) * WAVE_STEP;
      this.waveSpawnQueue = isBoss ? budget : budget;
      this.waveRemaining = this.waveSpawnQueue;
      this.lastSpawn = this.now;
      this.lastItemSpawn = this.now;

      this.exitData = {
        id: 'exit-1', x: extractPoint.x, y: extractPoint.y,
        visible: false, ready: false, name: '撤离终端',
        color: '#48f0a0', requires: {}, charge: 0,
      };

      if (!this.player) {
        this.player = this._createPlayer(spawnPoint.x, spawnPoint.y);
      } else {
        const p = this.player;
        const [nx, ny] = resolveOverlap(spawnPoint.x, spawnPoint.y, PLAYER_R, obstacles);
        p.x = nx; p.y = ny;
        p.vx = 0; p.vy = 0;
        p.dead = false;
        p.protUntil = this.now + PROTECT_SECS;
        p.facilityLabel = '';
        p.facilityStatus = '';
      }

      this._spawnInitialItems();

      const story = STORY_BEATS[(wave - 1) % STORY_BEATS.length].replace('{wave}', wave);
      const title = STAGE_TITLES[(wave - 1) % STAGE_TITLES.length];
      this.transport.dispatch('wave_start', {
        wave, remaining: this.waveRemaining, boss: isBoss,
        story, stage: { title },
        obs: this.obstacles, features: this.features,
        scene: 'main', sceneName: '设施楼层',
        mw: MAP_W, mh: MAP_H,
        obj: this._objSnapshot(),
        mission: this._missionSnapshot(),
        exits: [this.exitData],
        routeReward: null,
      });
    }

    _createPlayer(x, y) {
      return {
        x, y, vx: 0, vy: 0,
        hp: PLAYER_MAX_HP, maxHp: PLAYER_MAX_HP,
        dead: false,
        aim: 0,
        score: 0, xp: 0, kills: 0,
        level: 1, combo: 0, comboUntil: 0,
        protUntil: this.now + PROTECT_SECS,
        rapidUntil: 0, spreadUntil: 0,
        fireCd: 0, reloadUntil: 0,
        meleeCd: 0, dashCd: 0,
        weapon: 'pistol', weapons: ['pistol'],
        weaponLevel: 1,
        ammo: MAG_SIZE, magSize: MAG_SIZE,
        weaponAmmo: { pistol: MAG_SIZE },
        ammoPools: { pistol: START_AMMO, rifle: 0, smg: 0, shell: 0, explosive: 0 },
        materials: 0, lore: 0,
        vehicle: false, vehicleUntil: 0,
        lives: STAGE_LIVES, maxLives: STAGE_LIVES,
        ackSeq: 0,
        facilityLabel: '', facilityStatus: '',
        // input state
        keys: {}, shooting: false, fire: false, dash: false, interact: false, reload: false, weapon_req: '',
        input_seq: 0,
      };
    }

    _applyInput(data) {
      if (!this.player || this.player.dead) return;
      const p = this.player;
      const rawKeys = data.keys || {};
      p.keys = { up: !!rawKeys.up, down: !!rawKeys.down, left: !!rawKeys.left, right: !!rawKeys.right };
      if (typeof data.aim_angle === 'number' && isFinite(data.aim_angle)) p.aim = data.aim_angle;
      p.shooting = !!data.shooting;
      if (data.fire) p.fire = true;
      if (data.dash) p.dash = true;
      if (data.reload) p.reload = true;
      if (data.weapon) p.weapon_req = data.weapon;
      if (typeof data.seq === 'number') p.input_seq = data.seq;
    }

    tick(dt, now) {
      this.now = now;
      if (this.intermission) return;
      dt = Math.min(dt, 0.05);

      this._tickPlayer(dt, now);
      this._tickZombies(dt, now);
      this._tickBullets(dt, now);
      this._collectItems(now);
      this._maintainWave(dt, now);
      this._tickExtraction(dt, now);
      this._tickFog(dt, now);

      if (now - this.lastSnapshot >= 1 / SNAP_HZ) {
        this.lastSnapshot = now;
        this.transport.dispatch('sync', this._snapshotPayload(now));
      }
    }

    _tickPlayer(dt, now) {
      const p = this.player;
      if (!p || p.dead) return;

      // weapon switch
      if (p.weapon_req && p.weapons.includes(p.weapon_req) && p.weapon_req !== p.weapon) {
        // save current weapon ammo
        if (!p.weaponAmmo) p.weaponAmmo = {};
        p.weaponAmmo[p.weapon] = p.ammo;
        // switch
        p.weapon = p.weapon_req;
        const wm = WEAPONS[p.weapon];
        p.magSize = wm.mag;
        // restore this weapon's saved ammo (or full mag if never used)
        p.ammo = p.weaponAmmo[p.weapon] !== undefined ? p.weaponAmmo[p.weapon] : wm.mag;
        p.reloadUntil = 0;
        const at = wm.ammo || 'pistol';
        const poolStr = Object.entries(p.ammoPools).map(([k, v]) => `${k}:${v}`).join(',');
        this.transport.dispatch('weapon_switch', {
          pid: 'local',
          weapon: p.weapon,
          weaponName: wm.name,
          ammo: p.ammo,
          magSize: p.magSize,
          weapons: p.weapons,
          ammoPools: poolStr,
          currentReserve: p.ammoPools[at] || 0,
          ammoType: at,
          ammoTypeName: AMMO_LABELS[at] || '弹药',
        });
      }
      p.weapon_req = '';

      // reload
      if (p.reload && p.reloadUntil === 0 && p.ammo < p.magSize) {
        this._tryReload(p, now);
      }
      p.reload = false;
      if (p.reloadUntil > 0 && now >= p.reloadUntil) {
        this._finishReload(p, now);
      }

      // dash
      if (p.dash && now >= p.dashCd) {
        p.dashCd = now + DASH_CD;
        const ang = p.aim;
        const dx = Math.cos(ang) * DASH_DIST;
        const dy = Math.sin(ang) * DASH_DIST;
        const obs = nearObs(this.obstacles, p.x, p.y, DASH_DIST + 40);
        const [nx, ny] = moveWithCollision(p.x, p.y, PLAYER_R, dx, dy, obs);
        p.x = nx; p.y = ny;
        p.protUntil = Math.max(p.protUntil, now + 0.25);
        this.transport.dispatch('p_dash', { pid: 'local', x: p.x, y: p.y, vx: dx, vy: dy });
      }
      p.dash = false;

      // movement
      const keys = p.keys || {};
      const idx = (keys.right ? 1 : 0) - (keys.left ? 1 : 0);
      const idy = (keys.down ? 1 : 0) - (keys.up ? 1 : 0);
      const [ddx, ddy] = idx && idy ? [idx * Math.SQRT1_2, idy * Math.SQRT1_2] : [idx, idy];
      const spd = p.vehicle && now < p.vehicleUntil ? PLAYER_SPD * 1.52 : PLAYER_SPD;
      const rate = (ddx || ddy) ? MOVE_ACCEL : MOVE_DECEL;
      p.vx = approach(p.vx, ddx * spd, rate * dt);
      p.vy = approach(p.vy, ddy * spd, rate * dt);
      if (Math.abs(p.vx) < 0.01) p.vx = 0;
      if (Math.abs(p.vy) < 0.01) p.vy = 0;

      if (p.vx || p.vy) {
        const obs = nearObs(this.obstacles, p.x, p.y, Math.abs(p.vx) * dt + Math.abs(p.vy) * dt + 80);
        const [nx, ny] = moveWithCollision(p.x, p.y, PLAYER_R, p.vx * dt, p.vy * dt, obs);
        p.x = nx; p.y = ny;
      }

      // vehicle expiry
      if (p.vehicle && now >= p.vehicleUntil) {
        p.vehicle = false;
        this.transport.dispatch('vehicle_end', { pid: 'local' });
      }

      // shooting / melee
      const wm = WEAPONS[p.weapon];
      const nearZ = this._nearestZombie(p.x, p.y, MELEE_AUTO_RANGE);
      const usesMelee = nearZ && dist2(p.x, p.y, nearZ.x, nearZ.y) <= MELEE_AUTO_RANGE ** 2;

      if (usesMelee && now >= p.meleeCd) {
        p.meleeCd = now + MELEE_CD;
        const meleeKills = this._doMelee(p, now);
        this.transport.dispatch('melee_swing', { pid: 'local', x: p.x, y: p.y, aim: p.aim, kills: meleeKills });
      } else if ((p.shooting || p.fire) && now >= p.fireCd && p.reloadUntil === 0) {
        if (p.ammo > 0) {
          this._fireWeapon(p, wm, now);
          p.fire = false;
        } else {
          // auto-reload when magazine is empty, like the server does
          if (!this._tryReload(p, now)) {
            if (p.fire && now >= (p.dryUntil || 0)) {
              p.dryUntil = now + 0.55;
              const at = wm.ammo || 'pistol';
              const poolStr = Object.entries(p.ammoPools).map(([k, v]) => `${k}:${v}`).join(',');
              this.transport.dispatch('ammo_empty', {
                pid: 'local', ammo: p.ammo, weapon: p.weapon, weaponName: wm.name,
                ammoPools: poolStr, currentReserve: p.ammoPools[at] || 0,
                ammoType: at, ammoTypeName: AMMO_LABELS[at] || '弹药',
              });
            }
          }
          p.fire = false;
        }
      } else {
        p.fire = false;
      }

      p.ackSeq = p.input_seq;
    }

    _tryReload(p, now) {
      if (p.dead || p.reloadUntil > now) return false;
      const wm = WEAPONS[p.weapon];
      if (p.ammo >= p.magSize) return false;
      const reserve = p.ammoPools[wm.ammo] || 0;
      if (reserve <= 0) return false;
      p.shooting = false;
      p.reloadUntil = now + wm.reload;
      const at = wm.ammo || 'pistol';
      const poolStr = Object.entries(p.ammoPools).map(([k, v]) => `${k}:${v}`).join(',');
      this.transport.dispatch('reload_start', {
        pid: 'local', duration: wm.reload, ammo: p.ammo,
        weapon: p.weapon, weaponName: wm.name, magSize: p.magSize,
        ammoPools: poolStr, currentReserve: reserve,
        ammoType: at, ammoTypeName: AMMO_LABELS[at] || '弹药',
      });
      return true;
    }

    _finishReload(p, now) {
      if (!p.reloadUntil || p.reloadUntil > now) return;
      p.reloadUntil = 0;
      const wm = WEAPONS[p.weapon];
      const need = p.magSize - p.ammo;
      const reserve = p.ammoPools[wm.ammo] || 0;
      const add = Math.min(need, reserve);
      p.ammo += add;
      p.ammoPools[wm.ammo] = reserve - add;
      if (!p.weaponAmmo) p.weaponAmmo = {};
      p.weaponAmmo[p.weapon] = p.ammo;
      const at = wm.ammo || 'pistol';
      const poolStr = Object.entries(p.ammoPools).map(([k, v]) => `${k}:${v}`).join(',');
      this.transport.dispatch('reload_done', {
        pid: 'local', ammo: p.ammo, weapon: p.weapon, weaponName: wm.name, magSize: p.magSize,
        ammoPools: poolStr, currentReserve: p.ammoPools[at] || 0,
        ammoType: at, ammoTypeName: AMMO_LABELS[at] || '弹药',
      });
    }

    _fireWeapon(p, wm, now) {
      const rapid = now < p.rapidUntil;
      const spread = now < p.spreadUntil;
      const interval = rapid ? wm.interval * 0.58 : wm.interval;
      p.fireCd = now + interval;
      p.ammo -= wm.ammo_cost || 1;

      const shots = spread ? 3 : wm.pellets;
      const spreadAngle = spread ? 0.18 : wm.spread;
      const seq = this._bid;

      for (let pi = 0; pi < shots; pi++) {
        const angleOff = shots > 1 ? (pi - (shots - 1) / 2) * (spreadAngle / Math.max(1, shots - 1)) : (rng() - 0.5) * spreadAngle;
        const ang = p.aim + angleOff;
        const bx = p.x + Math.cos(ang) * wm.muzzle;
        const by = p.y + Math.sin(ang) * wm.muzzle;
        const bid = `b${++this._bid}`;
        this.bullets.set(bid, {
          x: bx, y: by, vx: Math.cos(ang) * wm.speed, vy: Math.sin(ang) * wm.speed,
          life: wm.life, color: wm.color, radius: wm.radius,
          damage: wm.damage, weapon: p.weapon, owner: 'local',
          expR: wm.expR || 0, expDmg: wm.expDmg || 0,
          pierce: wm.pierce || 0, piercedSet: new Set(),
          spawnX: bx, spawnY: by, prevX: bx, prevY: by, shotSeq: seq,
        });
      }
      this.transport.dispatch('shot_fired', { pid: 'local', x: p.x, y: p.y, aim: p.aim, weapon: p.weapon, seq });
    }

    _doMelee(p, now) {
      let kills = 0;
      for (const [zid, z] of this.zombies) {
        if (dist2(p.x, p.y, z.x, z.y) > MELEE_RANGE ** 2) continue;
        const ang = Math.atan2(z.y - p.y, z.x - p.x);
        let diff = ang - p.aim;
        while (diff > Math.PI) diff -= 2 * Math.PI;
        while (diff < -Math.PI) diff += 2 * Math.PI;
        if (Math.abs(diff) > MELEE_ARC / 2) continue;
        z.hp -= MELEE_DAMAGE;
        const kbAng = Math.atan2(z.y - p.y, z.x - p.x);
        z.x += Math.cos(kbAng) * MELEE_KNOCKBACK;
        z.y += Math.sin(kbAng) * MELEE_KNOCKBACK;
        if (z.hp <= 0) { this._killZombie(zid, z, now); kills++; }
      }
      return kills;
    }

    _nearestZombie(x, y, maxDist) {
      let best = null, bestD = maxDist ** 2;
      for (const z of this.zombies.values()) {
        const d = dist2(x, y, z.x, z.y);
        if (d < bestD) { bestD = d; best = z; }
      }
      return best;
    }

    _tickZombies(dt, now) {
      const p = this.player;
      if (!p || p.dead) return;
      for (const [zid, z] of this.zombies) {
        this._steerZombie(z, p, dt);
        // attack
        const atkD = (z.radius + PLAYER_R + ZOMBIE_ATK_RANGE) ** 2;
        if (dist2(z.x, z.y, p.x, p.y) <= atkD && now >= (z.atkCd || 0)) {
          z.atkCd = now + 0.8;
          if (now >= p.protUntil) this._damagePlayer(z.damage, now, z);
        }
        // leaper
        if (z.type === 'leaper' && now >= (z.leapCd || 0) && dist2(z.x, z.y, p.x, p.y) > 220 ** 2 && dist2(z.x, z.y, p.x, p.y) < 620 ** 2) {
          z.leapCd = now + 2.15;
          const ang = Math.atan2(p.y - z.y, p.x - z.x);
          const sx = z.x, sy = z.y;
          z.x = Math.min(MAP_W - z.radius, Math.max(z.radius, p.x + (Math.random() - 0.5) * 60));
          z.y = Math.min(MAP_H - z.radius, Math.max(z.radius, p.y + (Math.random() - 0.5) * 60));
          this.transport.dispatch('z_leap', { sx, sy, x: z.x, y: z.y, col: z.color });
        }
        // screamer rally
        if (z.type === 'screamer' && now >= (z.screamCd || 0)) {
          z.screamCd = now + 4.0;
          let buffed = 0;
          for (const nz of this.zombies.values()) {
            if (nz === z) continue;
            if (dist2(z.x, z.y, nz.x, nz.y) <= 290 ** 2) { nz.rallyUntil = now + 2.8; buffed++; }
          }
          this.transport.dispatch('z_scream', { x: z.x, y: z.y, r: 290, col: z.color, buffed });
        }
        // boss phases
        if (z.type === 'boss') {
          const frac = z.hp / z.maxHp;
          const phase = frac > 0.66 ? 1 : frac > 0.33 ? 2 : 3;
          if (phase !== (z.phase || 1)) {
            z.phase = phase;
            this.transport.dispatch('boss_phase', { x: z.x, y: z.y, phase, col: z.color, text: `Boss 进入第 ${phase} 阶段` });
          }
        }
      }
    }

    _steerZombie(z, p, dt) {
      const spd = (z.type === 'boss' ? 86 : ZTYPES[z.type]?.speed || 104) * (z.rallyUntil && this.now < z.rallyUntil ? 1.22 : 1);
      const dx = p.x - z.x, dy = p.y - z.y;
      const d = Math.hypot(dx, dy);
      if (d < 0.1) return;
      let nx = dx / d, ny = dy / d;

      // simple 3-way obstacle avoidance: try direct, then ±70°
      const step = spd * dt;
      const obs = nearObs(this.obstacles, z.x, z.y, step + 60);
      const tries = [[nx, ny], ...[-1, 1].map(s => {
        const a = Math.atan2(ny, nx) + s * 1.2;
        return [Math.cos(a), Math.sin(a)];
      })];

      let moved = false;
      for (const [tx, ty] of tries) {
        const ex = clamp(z.x + tx * step, z.radius, MAP_W - z.radius);
        const ey = clamp(z.y + ty * step, z.radius, MAP_H - z.radius);
        if (!obs.some(o => circleRect(ex, ey, z.radius, o.x, o.y, o.w, o.h))) {
          z.x = ex; z.y = ey;
          z.vx = tx * spd; z.vy = ty * spd;
          moved = true; break;
        }
      }
      if (!moved) { z.vx = 0; z.vy = 0; }
    }

    _tickBullets(dt, now) {
      for (const [bid, b] of this.bullets) {
        b.prevX = b.x; b.prevY = b.y;
        b.x += b.vx * dt; b.y += b.vy * dt;
        b.life -= dt;

        if (b.life <= 0 || b.x < 0 || b.x > MAP_W || b.y < 0 || b.y > MAP_H) {
          if (b.expR > 0) this._explode(b, now);
          this.bullets.delete(bid);
          continue;
        }

        // wall collision
        let hitWall = false;
        for (const o of nearObs(this.obstacles, b.x, b.y, b.radius + 60)) {
          if (circleRect(b.x, b.y, b.radius, o.x, o.y, o.w, o.h)) { hitWall = true; break; }
        }
        if (hitWall) {
          if (b.expR > 0) this._explode(b, now);
          this.bullets.delete(bid);
          continue;
        }

        // zombie collision
        let hitZ = false;
        for (const [zid, z] of this.zombies) {
          if (b.piercedSet.has(zid)) continue;
          if (dist2(b.x, b.y, z.x, z.y) > (b.radius + z.radius) ** 2) continue;
          z.hp -= b.damage;
          this.transport.dispatch('score_gain', { pid: 'local', score: this.player.score, kills: this.player.kills, combo: this.player.combo, level: this.player.level, col: '#ffc247' });
          if (z.hp <= 0) { this._killZombie(zid, z, now); }
          if (b.pierce > 0 && b.pierce > b.piercedSet.size) {
            b.piercedSet.add(zid);
          } else {
            if (b.expR > 0) this._explode(b, now);
            this.bullets.delete(bid);
            hitZ = true; break;
          }
        }
        if (hitZ) continue;

        // player friendly fire not needed
      }
    }

    _explode(b, now) {
      const p = this.player;
      this.transport.dispatch('grenade_explode', { x: b.x, y: b.y, r: b.expR, col: '#ff8844', pid: 'local' });
      for (const [zid, z] of this.zombies) {
        if (dist2(b.x, b.y, z.x, z.y) > b.expR ** 2) continue;
        z.hp -= b.expDmg || 52;
        if (z.hp <= 0) this._killZombie(zid, z, now);
      }
    }

    _killZombie(zid, z, now) {
      const p = this.player;
      this.zombies.delete(zid);
      this.waveRemaining = Math.max(0, this.waveRemaining - 1);

      // score
      const xpGain = Math.floor(z.score * 0.6);
      p.score += z.score;
      p.kills++;
      p.xp += xpGain;
      p.combo++;
      p.comboUntil = now + COMBO_WINDOW;

      // level up
      const xpNeeded = LEVEL_XP_BASE * p.level;
      if (p.xp >= xpNeeded) { p.xp -= xpNeeded; p.level++; p.maxHp = PLAYER_MAX_HP + Math.min(45, (p.level - 1) * 5); p.hp = Math.min(p.hp + 20, p.maxHp); this.transport.dispatch('level_up', { pid: 'local', level: p.level, xp: p.xp }); }

      // combo bonuses
      if (p.combo === COMBO_RAPID_AT) { p.rapidUntil = now + 4.0; this.transport.dispatch('combo_bonus', { pid: 'local', type: 'rapid', name: '速射', combo: p.combo, col: '#44ffaa', x: p.x, y: p.y }); }
      else if (p.combo === COMBO_SPREAD_AT) { p.spreadUntil = now + 4.0; this.transport.dispatch('combo_bonus', { pid: 'local', type: 'spread', name: '三连发', combo: p.combo, col: '#ffcc44', x: p.x, y: p.y }); }
      else if (p.combo === COMBO_SHIELD_AT) { p.protUntil = now + 3.0; this.transport.dispatch('combo_bonus', { pid: 'local', type: 'shield', name: '护盾', combo: p.combo, col: '#fff', x: p.x, y: p.y }); }

      this.transport.dispatch('score_gain', { pid: 'local', score: p.score, kills: p.kills, combo: p.combo, level: p.level, col: '#ffc247' });
      this.transport.dispatch('z_die', { zid, pid: 'local', x: z.x, y: z.y, col: z.color });

      // item drop
      this._tryDropItem(z, now);
      // task drop
      this._tryDropTask(z, now);

      // bloater explosion
      if (z.type === 'bloater') {
        this.transport.dispatch('z_explode', { x: z.x, y: z.y, r: 150, col: z.color });
        if (p && dist2(p.x, p.y, z.x, z.y) <= 150 ** 2 && now >= p.protUntil) {
          this._damagePlayer(24, now);
        }
      }
    }

    _tryDropItem(z, now) {
      if (rng() > 0.22) return;
      const candidates = ['ammo', 'medkit', 'parts'];
      const type = rngChoice(candidates);
      this._spawnItem(z.x + (rng() - 0.5) * 40, z.y + (rng() - 0.5) * 40, type, now);
    }

    _tryDropTask(z, now) {
      if (rng() > TASK_DROP_CHANCE) return;
      const pool = ['sample', 'fuse', 'keycard'];
      const type = rngChoice(pool);
      this._spawnItem(z.x + (rng() - 0.5) * 30, z.y + (rng() - 0.5) * 30, type, now);
    }

    _damagePlayer(amount, now, source) {
      const p = this.player;
      if (!p || p.dead || now < p.protUntil) return;
      p.hp = Math.max(0, p.hp - amount);
      if (p.hp <= 0) this._killPlayer(now);
    }

    _killPlayer(now) {
      const p = this.player;
      p.dead = true;
      p.lives--;
      p.combo = 0; p.comboUntil = 0;
      this.transport.dispatch('p_die', { pid: 'local', x: p.x, y: p.y });
      if (p.lives <= 0) {
        setTimeout(() => {
          this.transport.dispatch('stage_failed', {
            wave: this.wave, reason: 'wipe',
            obs: this.obstacles, features: this.features,
            scene: 'main', sceneName: '设施楼层',
            mw: MAP_W, mh: MAP_H,
            obj: this._objSnapshot(), mission: this._missionSnapshot(), exits: [this.exitData],
          });
        }, 800);
      } else {
        setTimeout(() => {
          const [rx, ry] = resolveOverlap(this.spawnPoint.x, this.spawnPoint.y, PLAYER_R, this.obstacles);
          p.x = rx; p.y = ry;
          p.hp = p.maxHp; p.vx = 0; p.vy = 0;
          p.dead = false; p.protUntil = now + PROTECT_SECS;
          this.transport.dispatch('p_resp', { pid: 'local', x: p.x, y: p.y, lives: p.lives, maxLives: p.maxLives, hp: p.hp, prot: true });
        }, 1500);
      }
    }

    _maintainWave(dt, now) {
      const p = this.player;
      if (!p || this.stageCleared) return;
      if (this.waveSpawnQueue > 0 && now - this.lastSpawn >= ZOMBIE_SPAWN_DT) {
        this.lastSpawn = now;
        this._spawnZombie(now);
        this.waveSpawnQueue--;
      }
      if (this.waveSpawnQueue === 0 && this.zombies.size === 0 && !this.stageCleared) {
        this.stageCleared = true;
        this.exitData.visible = true;
        this.exitData.ready = true;
        this.transport.dispatch('exit_ready', { id: 'exit-1', x: this.exitData.x, y: this.exitData.y, visible: true, ready: true, name: '撤离终端', requires_text: '', reward_text: '' });
        this.transport.dispatch('mission_revealed', { id: 'exit-1', x: this.exitData.x, y: this.exitData.y, name: '撤离终端', col: '#48f0a0' });
        this.transport.dispatch('wave_clear', { wave: this.wave });
      }
    }

    _spawnZombie(now) {
      const p = this.player;
      const isBoss = this.wave % BOSS_WAVE_INTERVAL === 0 && this.zombies.size === 0 && this.waveSpawnQueue === 1;
      const type = isBoss ? 'boss' : this._pickZombieType();
      const zt = ZTYPES[type] || ZTYPES.walker;

      let sx, sy;
      const tries = 20;
      for (let i = 0; i < tries; i++) {
        const fp = rngChoice(this.floorPoints);
        const d2 = dist2(fp.x, fp.y, p.x, p.y);
        if (d2 >= SPAWN_MIN_DIST ** 2 && d2 <= SPAWN_MAX_DIST ** 2) {
          sx = fp.x + (rng() - 0.5) * 80; sy = fp.y + (rng() - 0.5) * 80; break;
        }
      }
      if (!sx) { const fp = rngChoice(this.floorPoints); sx = fp.x; sy = fp.y; }
      sx = clamp(sx, zt.radius + 5, MAP_W - zt.radius - 5);
      sy = clamp(sy, zt.radius + 5, MAP_H - zt.radius - 5);

      const zid = `z${++this._zid}`;
      const hp = zt.hp * (1 + (this.wave - 1) * 0.06);
      const zombie = { x: sx, y: sy, vx: 0, vy: 0, hp, maxHp: hp, type, color: zt.color, radius: zt.radius, damage: zt.damage, score: zt.score };
      this.zombies.set(zid, zombie);
      this.transport.dispatch('z_spawn', { id: zid, x: sx, y: sy, hp, maxHp: hp, type, color: zt.color, radius: zt.radius, sceneId: 'main' });
      if (type === 'boss') this.transport.dispatch('boss_spawn', { x: sx, y: sy, name: '黑墙巨像', color: zt.color });
    }

    _pickZombieType() {
      const poolIdx = Math.min(3, Math.floor((this.wave - 1) / 2));
      const pool = ZTYPE_POOL_BY_WAVE[poolIdx];
      return rngChoice(pool);
    }

    _tickExtraction(dt, now) {
      const p = this.player;
      if (!p || p.dead || !this.stageCleared || !this.exitData) return;

      const ex = this.exitData.x, ey = this.exitData.y;
      const inZone = dist2(p.x, p.y, ex, ey) <= EXTRACT_RADIUS ** 2;

      if (inZone) {
        this.exitCharging = true;
        this.extractCharge = Math.min(1, this.extractCharge + dt / EXTRACTION_SECS);
        this.exitData.charge = this.extractCharge;
        if (this.extractCharge >= 1) {
          this.extractCharge = 1;
          this._stageClear(now);
        }
      } else {
        if (this.exitCharging && this.extractCharge > 0) {
          this.extractCharge = Math.max(0, this.extractCharge - dt * 0.5);
          this.exitData.charge = this.extractCharge;
        }
        this.exitCharging = false;
      }
    }

    _stageClear(now) {
      const p = this.player;
      this.stageCleared = false;
      this.extractCharge = 0;
      this.transport.dispatch('mission_complete', { x: this.exitData.x, y: this.exitData.y, name: '撤离终端' });
      this.transport.dispatch('wave_reward', { pid: 'local', hp: Math.min(p.maxHp, p.hp + 30), x: p.x, y: p.y, col: '#48f0a0' });
      p.hp = Math.min(p.maxHp, p.hp + 30);
      p.protUntil = now + PROTECT_SECS;

      this.intermission = {
        active: true,
        clearedWave: this.wave,
        nextWave: this.wave + 1,
        nextBoss: (this.wave + 1) % BOSS_WAVE_INTERVAL === 0,
        bossName: '黑墙巨像',
        ending: this.wave === 6,
        endingTitle: '主线结局',
        endingText: 'B13 层的真相已揭露，但设施还在继续下沉。',
        rewardTitle: '生存奖励',
        rewardText: `+30 HP · 第 ${this.wave} 关完成`,
        routeHook: '感染体密度上升，下一层更加危险。',
        youReady: false,
        talents: {},
      };
      this.transport.dispatch('intermission_start', this.intermission);
    }

    _continueStage() {
      if (!this.intermission) return;
      const nextWave = this.intermission.nextWave;
      this.intermission = null;
      this._newStage(nextWave);
    }

    _restartStage() {
      if (this.intermission) return;
      this.transport.dispatch('game_restart', {});
      setTimeout(() => {
        const p = this.player;
        p.lives = STAGE_LIVES; p.maxLives = STAGE_LIVES;
        p.hp = p.maxHp; p.dead = false;
        p.score = 0; p.kills = 0; p.xp = 0;
        p.combo = 0; p.comboUntil = 0;
        p.ammo = p.magSize; p.ammoPools = { pistol: START_AMMO, rifle: 0, smg: 0, shell: 0, explosive: 0 };
        this.intermission = null;
        this._newStage(this.wave);
        this.transport.dispatch('wave_start', {
          wave: this.wave, remaining: this.waveRemaining, boss: this.wave % BOSS_WAVE_INTERVAL === 0,
          obs: this.obstacles, features: this.features,
          scene: 'main', sceneName: '设施楼层',
          mw: MAP_W, mh: MAP_H,
          obj: this._objSnapshot(), mission: this._missionSnapshot(), exits: [this.exitData],
        });
      }, 100);
    }

    _restartGame() {
      const p = this.player;
      if (p) {
        p.lives = STAGE_LIVES; p.maxLives = STAGE_LIVES;
        p.hp = p.maxHp; p.dead = false;
        p.score = 0; p.kills = 0; p.xp = 0; p.level = 1; p.maxHp = PLAYER_MAX_HP;
        p.combo = 0; p.comboUntil = 0;
        p.weapon = 'pistol'; p.weapons = ['pistol'];
        p.ammo = MAG_SIZE; p.ammoPools = { pistol: START_AMMO, rifle: 0, smg: 0, shell: 0, explosive: 0 };
        p.materials = 0; p.lore = 0;
      }
      this.intermission = null;
      this._newStage(1);
      this.transport.dispatch('wave_start', {
        wave: 1, remaining: this.waveRemaining, boss: false,
        obs: this.obstacles, features: this.features,
        scene: 'main', sceneName: '设施楼层', mw: MAP_W, mh: MAP_H,
        obj: this._objSnapshot(), mission: this._missionSnapshot(), exits: [this.exitData],
      });
    }

    _tickFog(dt, now) {
      const p = this.player;
      if (!p || p.dead) return;
      if (now - this.lastFog < FOG_WAVE_CD) return;
      if (this.stageCleared) return;
      this.lastFog = now;
      const count = 6 + Math.min(8, this.wave);
      const fp = rngChoice(this.floorPoints) || this.spawnPoint;
      this.transport.dispatch('fog_wave', {
        x: fp.x, y: fp.y, spawnX: fp.x, spawnY: fp.y,
        count, duration: 4.8, reason: 'director',
        col: '#d6eceb', sourceCount: 0,
      });
      for (let i = 0; i < Math.min(4, count); i++) {
        this.waveSpawnQueue++;
        this.waveRemaining++;
      }
    }

    _spawnInitialItems() {
      const now = this.now;
      const types = ['ammo', 'medkit', 'ammo', 'parts'];
      rngShuffle(this.floorPoints.slice(1, 10)).slice(0, 4).forEach((fp, i) => {
        this._spawnItem(fp.x + (rng() - 0.5) * 60, fp.y + (rng() - 0.5) * 60, types[i] || 'ammo', now);
      });
    }

    _spawnItem(x, y, type, now) {
      if (this.items.size >= MAX_ITEMS && !ITEM_TYPES[type]?.task) return;
      const meta = ITEM_TYPES[type];
      if (!meta) return;
      x = clamp(x, ITEM_R + 5, MAP_W - ITEM_R - 5);
      y = clamp(y, ITEM_R + 5, MAP_H - ITEM_R - 5);
      const iid = `i${++this._iid}`;
      this.items.set(iid, { x, y, type, color: meta.color, icon: meta.icon, name: meta.name, radius: ITEM_R });
      this.transport.dispatch('i_spawn', { id: iid, x, y, type, color: meta.color, icon: meta.icon, name: meta.name, radius: ITEM_R, sceneId: 'main' });
    }

    _collectItems(now) {
      const p = this.player;
      if (!p || p.dead) return;
      for (const [iid, item] of this.items) {
        if (dist2(p.x, p.y, item.x, item.y) > (PLAYER_R + item.radius) ** 2) continue;
        const eventData = { iid, pid: 'local', x: item.x, y: item.y, col: item.color, sceneId: 'main' };
        this._applyItem(p, item, now, eventData);
        this.items.delete(iid);
        this.transport.dispatch('item_pick', eventData);
      }
    }

    _applyItem(p, item, now, ev) {
      const type = item.type;
      const meta = ITEM_TYPES[type] || {};

      if (type === 'medkit') { p.hp = Math.min(p.maxHp, p.hp + 40); }
      else if (type === 'ammo') {
        const at = WEAPONS[p.weapon]?.ammo || 'pistol';
        const [lo, hi] = AMMO_PICKUP[at] || [16, 30];
        const add = rngInt(lo, hi);
        p.ammoPools[at] = Math.min(MAX_RESERVE[at] || 168, (p.ammoPools[at] || 0) + add);
        p.currentReserve = p.ammoPools[WEAPONS[p.weapon]?.ammo || 'pistol'];
        ev.ammo = p.ammo;
      }
      else if (type === 'parts') { p.materials++; p.weaponLevel = Math.min(8, p.weaponLevel + 1); ev.weaponLevel = p.weaponLevel; ev.materials = p.materials; }
      else if (type === 'rapid') { p.rapidUntil = now + 6; }
      else if (type === 'spread') { p.spreadUntil = now + 6; }
      else if (type === 'shield') { p.protUntil = now + 4; }
      else if (type === 'nuke') { this._nuke(now); }
      else if (type === 'vehicle') { p.vehicle = true; p.vehicleUntil = now + 10; ev.vehicle = true; this.transport.dispatch('vehicle_start', { pid: 'local', seconds: 10 }); }
      else if (type.startsWith('weapon_')) {
        const wid = type.replace('weapon_', '');
        if (WEAPONS[wid] && !p.weapons.includes(wid)) {
          const wm = WEAPONS[wid];
          if (!p.weaponAmmo) p.weaponAmmo = {};
          p.weaponAmmo[p.weapon] = p.ammo;  // save current weapon ammo
          p.weapons.push(wid);
          p.weapon = wid;
          p.magSize = wm.mag;
          p.ammo = wm.mag;
          p.weaponAmmo[wid] = wm.mag;
          p.reloadUntil = 0;
          p.ammoPools[wm.ammo] = (p.ammoPools[wm.ammo] || 0) + wm.mag * 3;
          const at = wm.ammo || 'pistol';
          const poolStr = Object.entries(p.ammoPools).map(([k, v]) => `${k}:${v}`).join(',');
          this.transport.dispatch('weapon_unlock', { pid: 'local', weapon: wid, weaponName: wm.name, col: wm.color, x: item.x, y: item.y });
          this.transport.dispatch('weapon_switch', {
            pid: 'local', weapon: wid, weaponName: wm.name, ammo: p.ammo, magSize: p.magSize,
            weapons: p.weapons, ammoPools: poolStr, currentReserve: p.ammoPools[at] || 0,
            ammoType: at, ammoTypeName: AMMO_LABELS[at] || '弹药',
          });
        }
      }
      else if (type === 'fuse' || type === 'sample' || type === 'keycard') {
        this.taskCounts[type] = (this.taskCounts[type] || 0) + 1;
        this.transport.dispatch('task_update', { pid: 'local', task: { ...this.taskCounts }, name: meta.name, count: this.taskCounts[type], col: meta.color, x: item.x, y: item.y, sceneId: 'main' });
        ev.lore = p.lore;
      }
      else if (type === 'lore') { p.lore++; ev.lore = p.lore; this.transport.dispatch('lore_found', { pid: 'local', text: `档案 ${p.lore.toString().padStart(2,'0')}：设施记录已解密。` }); }
    }

    _nuke(now) {
      const p = this.player;
      let cleared = 0;
      for (const [zid, z] of this.zombies) {
        z.hp = 0;
        this._killZombie(zid, z, now);
        cleared++;
      }
      this.transport.dispatch('nuke', { x: p.x, y: p.y, pid: 'local', count: cleared });
    }

    _sendScenePayload() {
      this.transport.dispatch('scene_change', {
        pid: 'local', scene: 'main', sceneName: '设施楼层',
        x: this.player?.x || MAP_W / 2, y: this.player?.y || MAP_H / 2,
        mw: MAP_W, mh: MAP_H,
        obs: this.obstacles, features: this.features,
        mission: this._missionSnapshot(), exits: [this.exitData],
      });
    }

    // ─── snapshot / tuple builders ──────────────────────────────────────────
    _playerTuple(p, now) {
      const wm = WEAPONS[p.weapon] || WEAPONS.pistol;
      const vehLeft = Math.max(0, p.vehicleUntil - now);
      const spd = p.vehicle && vehLeft > 0 ? PLAYER_SPD * 1.52 : PLAYER_SPD;
      const at = wm.ammo || 'pistol';
      const poolStr = Object.entries(p.ammoPools).map(([k, v]) => `${k}:${v}`).join(',');
      return [
        Math.round(p.x * 10) / 10, Math.round(p.y * 10) / 10,
        Math.round(Math.max(0, p.hp) * 10) / 10,
        p.score,
        p.dead,
        now < p.rapidUntil,
        Math.round((p.aim || 0) * 100) / 100,
        now < p.protUntil,
        '#4da3ff', '蓝色游骑',
        p.level,
        now < p.comboUntil ? p.combo : 0,
        Math.round(Math.max(0, p.fireCd - now) * 100) / 100,
        p.xp,
        p.ackSeq || 0,
        Math.round((p.vx || 0) * 10) / 10,
        Math.round((p.vy || 0) * 10) / 10,
        PLAYER_R,
        Math.round(spd * 10) / 10,
        p.kills,
        now < p.spreadUntil,
        p.maxHp,
        p.ammo,
        p.magSize,
        p.ammoPools[at] || 0,
        p.materials || 0,
        p.lore || 0,
        p.weaponLevel || 1,
        Math.round(Math.max(0, p.reloadUntil - now) * 100) / 100,
        p.weapon,
        wm.name || '手枪',
        p.weapons.join(','),
        p.vehicle && vehLeft > 0,
        Math.round(vehLeft * 100) / 100,
        p.facilityLabel || '',
        p.facilityStatus || '',
        poolStr,
        at,
        AMMO_LABELS[at] || '弹药',
        p.lives,
        p.maxLives,
        'main',
        '设施楼层',
      ];
    }

    _zombieTuple(z) {
      return [
        Math.round(z.x * 10) / 10, Math.round(z.y * 10) / 10,
        Math.round(Math.max(0, z.hp) * 10) / 10,
        z.type, z.color, z.radius, 'local',
        Math.round((z.vx || 0) * 10) / 10,
        Math.round((z.vy || 0) * 10) / 10,
        Math.round(z.maxHp * 10) / 10,
      ];
    }

    _bulletTuple(b) {
      return [
        Math.round(b.x * 10) / 10, Math.round(b.y * 10) / 10,
        Math.round(b.vx * 10) / 10, Math.round(b.vy * 10) / 10,
        b.color, b.radius, b.owner,
        Math.round(Math.max(0, b.life) * 100) / 100,
        b.weapon, b.expR || 0, b.damage,
        b.spawnX, b.spawnY, b.prevX || b.spawnX, b.prevY || b.spawnY, b.shotSeq || 0,
      ];
    }

    _itemTuple(item) {
      return [item.x, item.y, item.type, item.color, item.icon, item.name, item.radius];
    }

    _objSnapshot() {
      const p = this.player;
      const budget = Math.max(1, WAVE_BASE + (this.wave - 1) * WAVE_STEP);
      const remaining = this.waveRemaining + this.waveSpawnQueue + this.zombies.size;
      const killed = Math.max(0, budget - remaining);
      const progress = this.stageCleared ? this.extractCharge : Math.min(1, killed / budget);
      let title, text;
      if (this.stageCleared && this.exitData?.ready) {
        const pct = Math.round(this.extractCharge * 100);
        title = '可以撤离'; text = pct > 0 ? `撤离中 ${pct}% · 留在终端范围内` : '前往撤离终端，等待 3.2s';
      } else {
        title = `感染体剩余 ${remaining}`; text = `消灭所有感染体后前往撤离终端`;
      }
      return {
        remaining, budget, progress: Math.round(Math.max(0, Math.min(1, progress)) * 1000) / 1000,
        boss: this.wave % BOSS_WAVE_INTERVAL === 0,
        task: { ...this.taskCounts, lore: p?.lore || 0 },
        lore: p?.lore || 0, loreTotal: 12,
        visibleExits: this.exitData?.visible ? 1 : 0,
        readyExits: this.exitData?.ready ? 1 : 0,
        stageId: 'clear', stageTitle: STAGE_TITLES[(this.wave - 1) % STAGE_TITLES.length],
        infectionSource: 0, powered: false,
        title, text,
        story: STORY_BEATS[(this.wave - 1) % STORY_BEATS.length].replace('{wave}', this.wave),
        hook: '',
      };
    }

    _missionSnapshot() {
      return {
        done: this.stageCleared && this.extractCharge >= 1,
        charge: this.extractCharge,
        text: '消灭所有感染体后撤离',
      };
    }

    _snapshotPayload(now) {
      const p = this.player;
      const pl = p ? { local: this._playerTuple(p, now) } : {};
      const z = {};
      for (const [id, zb] of this.zombies) z[id] = this._zombieTuple(zb);
      const b = {};
      for (const [id, bl] of this.bullets) b[id] = this._bulletTuple(bl);
      const items = {};
      for (const [id, it] of this.items) items[id] = this._itemTuple(it);
      return {
        v: 18, tick: 0, time: now,
        scene: 'main', sceneName: '设施楼层',
        mw: MAP_W, mh: MAP_H,
        dynamicAoi: 980,
        p: pl, z, b, i: items,
        zt: this.zombies.size, bt: this.bullets.size, it: this.items.size,
        w: this.wave, wr: this.waveRemaining + this.waveSpawnQueue,
        lb: p ? [{ nm: p.name || '蓝色游骑', score: p.score, kills: p.kills, col: '#4da3ff' }] : [],
        obj: this._objSnapshot(),
        mission: this._missionSnapshot(),
        exits: this.exitData ? [this.exitData] : [],
        intermission: this.intermission,
      };
    }

    _initPayload(now) {
      const p = this.player;
      return {
        v: 18, tick: 0, time: now || this.now,
        scene: 'main', sceneName: '设施楼层',
        id: 'local', col: '#4da3ff', nm: '蓝色游骑', idx: 0,
        mw: MAP_W, mh: MAP_H,
        cfg: {
          playerSpeed: PLAYER_SPD, playerRadius: PLAYER_R, playerMaxHp: PLAYER_MAX_HP,
          dashDist: DASH_DIST, dashCd: DASH_CD,
          fireInterval: WEAPONS.pistol.interval, bulletSpeed: WEAPONS.pistol.speed,
          muzzleForward: WEAPONS.pistol.muzzle,
          magSize: MAG_SIZE, vehicleSpeedMult: 1.52,
          dynamicAoiMain: 980, dynamicAoiRoom: 520,
          weaponOrder: WEAPON_ORDER,
          weaponTypes: Object.fromEntries(Object.entries(WEAPONS).map(([id, wm]) => [id, {
            name: wm.name, mag_size: wm.mag, fire_interval: wm.interval, bullet_speed: wm.speed,
            bullet_life: wm.life, pellets: wm.pellets, spread: wm.spread, ammo_cost: 1,
            muzzle: wm.muzzle, color: wm.color,
          }])),
          moveAccel: MOVE_ACCEL, moveDecel: MOVE_DECEL, moveCollisionStep: 14,
          maxReserveByType: MAX_RESERVE,
        },
        obs: this.obstacles, features: this.features,
        pl: p ? { local: this._playerTuple(p, this.now) } : {},
        z: {}, b: {},
        i: Object.fromEntries([...this.items.entries()].map(([id, it]) => [id, this._itemTuple(it)])),
        w: this.wave, wr: this.waveRemaining,
        lb: [], obj: this._objSnapshot(),
        mission: this._missionSnapshot(),
        exits: this.exitData ? [this.exitData] : [],
        intermission: null,
      };
    }
  }

  // ─── public API ───────────────────────────────────────────────────────────
  function create() {
    const transport = new LocalTransport();
    const sim = new Simulation();
    transport.bindSimulation(sim);

    // Intercept join_game to also send init after wave_start
    const origEmit = transport.emit.bind(transport);
    transport.emit = function (event, data) {
      if (event === 'join_game') {
        sim.handleClientEvent('join_game', data || {});
        // send init payload after maze is ready
        const now = performance.now() / 1000;
        transport.dispatch('init', sim._initPayload(now));
        return;
      }
      origEmit(event, data);
    };

    return transport;
  }

  return { create };
});
