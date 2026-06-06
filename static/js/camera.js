(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.ZCCamera = api;
})(typeof globalThis !== 'undefined' ? globalThis : window, function () {
  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function targetTopLeft(targetX, targetY, cfg) {
    const viewportW = cfg.viewportW || 1;
    const viewportH = cfg.viewportH || 1;
    const mapW = cfg.mapW || viewportW;
    const mapH = cfg.mapH || viewportH;
    const maxX = Math.max(0, mapW - viewportW);
    const maxY = Math.max(0, mapH - viewportH);
    return {
      x: clamp(targetX - viewportW / 2, 0, maxX),
      y: clamp(targetY - viewportH / 2, 0, maxY),
    };
  }

  function pixelAlign(value, pixelRatio) {
    const ratio = Math.max(1, pixelRatio || 1);
    return Math.round(value * ratio) / ratio;
  }

  function createCamera(options) {
    const cfg = Object.assign(
      {
        stiffness: 18,
        snapDistance: 260,
        viewportW: 1,
        viewportH: 1,
        mapW: 3000,
        mapH: 3000,
      },
      options || {},
    );
    const state = { x: 0, y: 0, ready: false };

    function configure(options) {
      Object.assign(cfg, options || {});
      return state;
    }

    function snapTo(targetX, targetY, options) {
      configure(options);
      const target = targetTopLeft(targetX, targetY, cfg);
      state.x = target.x;
      state.y = target.y;
      state.ready = true;
      return state;
    }

    function follow(targetX, targetY, dt, options) {
      configure(options);
      const target = targetTopLeft(targetX, targetY, cfg);
      if (!state.ready || !Number.isFinite(dt) || dt <= 0) {
        return snapTo(targetX, targetY, cfg);
      }

      const error = Math.hypot(target.x - state.x, target.y - state.y);
      if (error > cfg.snapDistance) {
        state.x = target.x;
        state.y = target.y;
        return state;
      }

      const alpha = 1 - Math.exp(-cfg.stiffness * Math.min(dt, 0.05));
      state.x += (target.x - state.x) * alpha;
      state.y += (target.y - state.y) * alpha;
      return state;
    }

    function view(pixelRatio) {
      return {
        x: pixelAlign(state.x, pixelRatio),
        y: pixelAlign(state.y, pixelRatio),
      };
    }

    return {
      state,
      config: cfg,
      configure,
      follow,
      snapTo,
      view,
    };
  }

  return {
    clamp,
    createCamera,
    pixelAlign,
    targetTopLeft,
  };
});
