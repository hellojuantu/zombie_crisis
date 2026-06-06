(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.ZCPrediction = api;
})(typeof globalThis !== 'undefined' ? globalThis : window, function () {
  function inputVector(keys) {
    const dx = (keys.right ? 1 : 0) - (keys.left ? 1 : 0);
    const dy = (keys.down ? 1 : 0) - (keys.up ? 1 : 0);
    if (dx && dy) return [dx * Math.SQRT1_2, dy * Math.SQRT1_2];
    return [dx, dy];
  }

  function circleRect(cx, cy, cr, rx, ry, rw, rh) {
    const nx = Math.max(rx, Math.min(cx, rx + rw));
    const ny = Math.max(ry, Math.min(cy, ry + rh));
    return (cx - nx) ** 2 + (cy - ny) ** 2 < cr * cr;
  }

  function moveOnce(x, y, radius, dx, dy, mapW, mapH, obstacles) {
    let nx = Math.max(radius, Math.min(mapW - radius, x + dx));
    let ny = Math.max(radius, Math.min(mapH - radius, y + dy));
    for (const o of obstacles || []) {
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

  function moveWithCollision(x, y, radius, dx, dy, mapW, mapH, obstacles) {
    const dist = Math.hypot(dx, dy);
    if (dist <= 0.01) return [x, y];
    const steps = Math.max(1, Math.ceil(dist / 14));
    const stepX = dx / steps;
    const stepY = dy / steps;
    let cx = x;
    let cy = y;
    for (let i = 0; i < steps; i += 1) {
      const [nx, ny] = moveOnce(cx, cy, radius, stepX, stepY, mapW, mapH, obstacles);
      if (Math.abs(nx - cx) < 0.001 && Math.abs(ny - cy) < 0.001) break;
      cx = nx;
      cy = ny;
    }
    return [cx, cy];
  }

  function approach(current, target, step) {
    if (current < target) return Math.min(target, current + step);
    if (current > target) return Math.max(target, current - step);
    return target;
  }

  function integrateVelocity(player, input, dt, cfg) {
    const keys = input.keys || {};
    const [dx, dy] = inputVector(keys);
    const speed = cfg.speed * (input.speedBoost || 1);
    const targetVx = dx * speed;
    const targetVy = dy * speed;
    const rate = dx || dy ? cfg.accel : cfg.decel;
    player.vx = approach(player.vx || 0, targetVx, rate * dt);
    player.vy = approach(player.vy || 0, targetVy, rate * dt);
    if (Math.abs(player.vx) < 0.01) player.vx = 0;
    if (Math.abs(player.vy) < 0.01) player.vy = 0;
    return { vx: player.vx, vy: player.vy, moving: Boolean(dx || dy || player.vx || player.vy) };
  }

  function createPredictor(options) {
    const cfg = Object.assign(
      {
        speed: 360,
        radius: 16,
        mapW: 3000,
        mapH: 3000,
        softSnap: 10,
        hardSnap: 90,
        softFactor: 0.12,
        accel: 1800,
        decel: 2400,
        maxPending: 180,
      },
      options || {},
    );
    const pending = [];

    function predict(player, input, dt, seq, obstacles) {
      const keys = input.keys || {};
      const velocity = integrateVelocity(player, input, dt, cfg);
      if (!velocity.moving) return false;
      const [x, y] = moveWithCollision(
        player.x,
        player.y,
        cfg.radius,
        velocity.vx * dt,
        velocity.vy * dt,
        cfg.mapW,
        cfg.mapH,
        obstacles,
      );
      player.x = x;
      player.y = y;
      pending.push({ seq, dt, keys: Object.assign({}, keys), speedBoost: input.speedBoost || 1 });
      while (pending.length > cfg.maxPending) pending.shift();
      return true;
    }

    function replay(player, obstacles) {
      for (const frame of pending) {
        const velocity = integrateVelocity(player, frame, frame.dt, cfg);
        if (!velocity.moving) continue;
        const pos = moveWithCollision(
          player.x,
          player.y,
          cfg.radius,
          velocity.vx * frame.dt,
          velocity.vy * frame.dt,
          cfg.mapW,
          cfg.mapH,
          obstacles,
        );
        player.x = pos[0];
        player.y = pos[1];
      }
    }

    function reconcile(player, authoritative, ackSeq, obstacles) {
      while (pending.length && pending[0].seq <= ackSeq) pending.shift();
      const error = Math.hypot(authoritative.x - player.x, authoritative.y - player.y);
      if (error > cfg.hardSnap) {
        player.x = authoritative.x;
        player.y = authoritative.y;
        player.vx = authoritative.vx || 0;
        player.vy = authoritative.vy || 0;
        replay(player, obstacles);
      } else if (error > cfg.softSnap) {
        player.x += (authoritative.x - player.x) * cfg.softFactor;
        player.y += (authoritative.y - player.y) * cfg.softFactor;
      }
      if (Number.isFinite(authoritative.vx)) player.vx = player.vx * 0.8 + authoritative.vx * 0.2;
      if (Number.isFinite(authoritative.vy)) player.vy = player.vy * 0.8 + authoritative.vy * 0.2;
      return { error, pending: pending.length };
    }

    function clear() {
      pending.length = 0;
    }

    return {
      pending,
      predict,
      reconcile,
      clear,
      config: cfg,
    };
  }

  return {
    inputVector,
    circleRect,
    moveWithCollision,
    approach,
    integrateVelocity,
    createPredictor,
  };
});
