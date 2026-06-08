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

  function prepareObstacles(obstacles, cellSize = 180) {
    const list = Array.isArray(obstacles) ? obstacles : obstacles?.list || [];
    const grid = new Map();
    for (const obstacle of list) {
      const minX = Math.floor(obstacle.x / cellSize);
      const maxX = Math.floor((obstacle.x + obstacle.w) / cellSize);
      const minY = Math.floor(obstacle.y / cellSize);
      const maxY = Math.floor((obstacle.y + obstacle.h) / cellSize);
      for (let gx = minX; gx <= maxX; gx += 1) {
        for (let gy = minY; gy <= maxY; gy += 1) {
          const key = `${gx},${gy}`;
          const bucket = grid.get(key);
          if (bucket) bucket.push(obstacle);
          else grid.set(key, [obstacle]);
        }
      }
    }
    return { list, grid, cellSize };
  }

  function nearObstacles(obstacles, x, y, radius = 80) {
    if (!obstacles) return [];
    if (Array.isArray(obstacles)) return obstacles;
    const cellSize = obstacles.cellSize || 180;
    const minX = Math.floor((x - radius) / cellSize);
    const maxX = Math.floor((x + radius) / cellSize);
    const minY = Math.floor((y - radius) / cellSize);
    const maxY = Math.floor((y + radius) / cellSize);
    const seen = new Set();
    const result = [];
    for (let gx = minX; gx <= maxX; gx += 1) {
      for (let gy = minY; gy <= maxY; gy += 1) {
        const bucket = obstacles.grid?.get(`${gx},${gy}`) || [];
        for (const obstacle of bucket) {
          if (seen.has(obstacle)) continue;
          seen.add(obstacle);
          result.push(obstacle);
        }
      }
    }
    return result;
  }

  function resolveOverlap(x, y, radius, mapW, mapH, obstacles) {
    let cx = Math.max(radius, Math.min(mapW - radius, x));
    let cy = Math.max(radius, Math.min(mapH - radius, y));
    for (let pass = 0; pass < 3; pass += 1) {
      let moved = false;
      for (const o of nearObstacles(obstacles, cx, cy, radius + 90)) {
        const nearestX = Math.max(o.x, Math.min(cx, o.x + o.w));
        const nearestY = Math.max(o.y, Math.min(cy, o.y + o.h));
        const dx = cx - nearestX;
        const dy = cy - nearestY;
        const distSq = dx * dx + dy * dy;
        if (distSq >= radius * radius) continue;
        if (distSq > 0.0001) {
          const dist = Math.sqrt(distSq);
          const push = radius - dist + 0.35;
          cx += (dx / dist) * push;
          cy += (dy / dist) * push;
        } else {
          const choices = [
            [Math.abs(cx - o.x), o.x - radius - 0.35, cy],
            [Math.abs(o.x + o.w - cx), o.x + o.w + radius + 0.35, cy],
            [Math.abs(cy - o.y), cx, o.y - radius - 0.35],
            [Math.abs(o.y + o.h - cy), cx, o.y + o.h + radius + 0.35],
          ].sort((a, b) => a[0] - b[0]);
          cx = choices[0][1];
          cy = choices[0][2];
        }
        cx = Math.max(radius, Math.min(mapW - radius, cx));
        cy = Math.max(radius, Math.min(mapH - radius, cy));
        moved = true;
      }
      if (!moved) break;
    }
    let nearby = nearObstacles(obstacles, cx, cy, radius + 120);
    if (nearby.some((o) => circleRect(cx, cy, radius, o.x, o.y, o.w, o.h))) {
      const candidates = [];
      for (const o of nearby) {
        const safeLeft = o.x - radius - 0.35;
        const safeRight = o.x + o.w + radius + 0.35;
        const safeTop = o.y - radius - 0.35;
        const safeBottom = o.y + o.h + radius + 0.35;
        const midX = Math.max(o.x, Math.min(cx, o.x + o.w));
        const midY = Math.max(o.y, Math.min(cy, o.y + o.h));
        candidates.push(
          [safeLeft, midY],
          [safeRight, midY],
          [midX, safeTop],
          [midX, safeBottom],
          [safeLeft, safeTop],
          [safeLeft, safeBottom],
          [safeRight, safeTop],
          [safeRight, safeBottom],
        );
      }
      const valid = candidates
        .map(([px, py]) => [
          Math.max(radius, Math.min(mapW - radius, px)),
          Math.max(radius, Math.min(mapH - radius, py)),
        ])
        .filter(
          ([px, py]) =>
            !nearObstacles(obstacles, px, py, radius + 120).some((o) => circleRect(px, py, radius, o.x, o.y, o.w, o.h)),
        );
      if (valid.length) {
        valid.sort((a, b) => (a[0] - x) ** 2 + (a[1] - y) ** 2 - ((b[0] - x) ** 2 + (b[1] - y) ** 2));
        [cx, cy] = valid[0];
      }
    }
    return [cx, cy];
  }

  function moveOnce(x, y, radius, dx, dy, mapW, mapH, obstacles) {
    let nx = Math.max(radius, Math.min(mapW - radius, x + dx));
    let ny = Math.max(radius, Math.min(mapH - radius, y + dy));
    for (const o of nearObstacles(obstacles, nx, ny, radius + 90)) {
      if (!circleRect(nx, ny, radius, o.x, o.y, o.w, o.h)) continue;
      if (!circleRect(nx, y, radius, o.x, o.y, o.w, o.h)) ny = y;
      else if (!circleRect(x, ny, radius, o.x, o.y, o.w, o.h)) nx = x;
      else {
        nx = x;
        ny = y;
      }
    }
    return resolveOverlap(nx, ny, radius, mapW, mapH, obstacles);
  }

  function moveWithCollision(x, y, radius, dx, dy, mapW, mapH, obstacles, collisionStep = 14) {
    const dist = Math.hypot(dx, dy);
    if (dist <= 0.01) return resolveOverlap(x, y, radius, mapW, mapH, obstacles);
    const steps = Math.max(1, Math.ceil(dist / collisionStep));
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
        collisionStep: 14,
        maxPending: 180,
        trackPending: true,
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
        cfg.collisionStep,
      );
      player.x = x;
      player.y = y;
      if (cfg.trackPending) {
        pending.push({ seq, dt, keys: Object.assign({}, keys), speedBoost: input.speedBoost || 1 });
        while (pending.length > cfg.maxPending) pending.shift();
      }
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
          cfg.collisionStep,
        );
        player.x = pos[0];
        player.y = pos[1];
      }
    }

    function reconcile(player, authoritative, ackSeq, obstacles) {
      while (pending.length && pending[0].seq <= ackSeq) pending.shift();
      const predictedX = player.x;
      const predictedY = player.y;
      const target = {
        x: authoritative.x,
        y: authoritative.y,
        vx: authoritative.vx || 0,
        vy: authoritative.vy || 0,
      };
      replay(target, obstacles);
      const dx = target.x - predictedX;
      const dy = target.y - predictedY;
      const error = Math.hypot(dx, dy);
      let mode = 'none';
      if (error > cfg.hardSnap) {
        mode = 'hard';
        player.x = target.x;
        player.y = target.y;
        player.vx = target.vx || 0;
        player.vy = target.vy || 0;
      } else if (error > cfg.softSnap) {
        mode = 'soft';
        const factor = Math.max(0, Math.min(1, cfg.softFactor || 0.12));
        player.x = predictedX + dx * factor;
        player.y = predictedY + dy * factor;
        player.vx = (player.vx || 0) + ((target.vx || 0) - (player.vx || 0)) * factor;
        player.vy = (player.vy || 0) + ((target.vy || 0) - (player.vy || 0)) * factor;
      }
      return {
        error,
        dx,
        dy,
        mode,
        pending: pending.length,
        authoritativeError: Math.hypot(authoritative.x - predictedX, authoritative.y - predictedY),
      };
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
    prepareObstacles,
    nearObstacles,
    moveWithCollision,
    resolveOverlap,
    approach,
    integrateVelocity,
    createPredictor,
  };
});
