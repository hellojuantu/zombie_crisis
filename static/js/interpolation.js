(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.ZCInterpolation = api;
})(typeof globalThis !== 'undefined' ? globalThis : window, function () {
  function seedSamples(entity, t) {
    const now = Number.isFinite(t) ? t : nowMs();
    entity.samples = [{ t: now, x: entity.x, y: entity.y }];
    return entity;
  }

  function pushSample(entity, x, y, options) {
    const cfg = Object.assign({ t: nowMs(), snapDistance: 120, maxSamples: 8 }, options || {});
    if (!entity.samples) seedSamples(entity, cfg.t);
    if (Math.hypot(x - entity.x, y - entity.y) > cfg.snapDistance) {
      snapObject(entity, x, y, cfg.t);
      return 'snap';
    }
    const last = entity.samples[entity.samples.length - 1];
    const t = last && cfg.t <= last.t ? last.t + 1 : cfg.t;
    entity.samples.push({ t, x, y });
    while (entity.samples.length > cfg.maxSamples) entity.samples.shift();
    return 'sample';
  }

  function snapObject(entity, x, y, t) {
    const now = Number.isFinite(t) ? t : nowMs();
    entity.x = x;
    entity.y = y;
    entity.tx = x;
    entity.ty = y;
    entity.samples = [{ t: now, x, y }];
  }

  function interpolateObject(entity, renderAt) {
    const samples = entity.samples;
    if (!samples || !samples.length) return false;
    while (samples.length >= 2 && samples[1].t <= renderAt) samples.shift();
    if (samples.length >= 2) {
      const a = samples[0];
      const b = samples[1];
      const ratio = clamp((renderAt - a.t) / Math.max(1, b.t - a.t), 0, 1);
      entity.x = a.x + (b.x - a.x) * ratio;
      entity.y = a.y + (b.y - a.y) * ratio;
    } else {
      entity.x = samples[0].x;
      entity.y = samples[0].y;
    }
    return true;
  }

  function interpolateEntities(players, zombies, myId, timestamp, delay) {
    const renderAt = timestamp - delay;
    for (const pid in players) {
      if (pid !== myId) interpolateObject(players[pid], renderAt);
    }
    for (const zombie of Object.values(zombies)) interpolateObject(zombie, renderAt);
  }

  function nowMs() {
    if (typeof performance !== 'undefined' && performance.now) return performance.now();
    return Date.now();
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  return {
    seedSamples,
    pushSample,
    snapObject,
    interpolateObject,
    interpolateEntities,
  };
});
