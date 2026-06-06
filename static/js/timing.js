(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.ZCTiming = api;
})(typeof globalThis !== 'undefined' ? globalThis : window, function () {
  function finiteNumber(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function createClockSync(options) {
    const cfg = Object.assign({ smoothing: 0.08 }, options || {});
    const state = { ready: false, offsetMs: 0 };

    function sampleTime(serverSeconds, receivedAtMs) {
      const server = finiteNumber(serverSeconds);
      const received = finiteNumber(receivedAtMs);
      if (server === null || received === null) return received || 0;

      const serverMs = server * 1000;
      const targetOffset = received - serverMs;
      if (!state.ready) {
        state.offsetMs = targetOffset;
        state.ready = true;
      } else {
        state.offsetMs += (targetOffset - state.offsetMs) * cfg.smoothing;
      }
      return Math.min(serverMs + state.offsetMs, received);
    }

    function reset() {
      state.ready = false;
      state.offsetMs = 0;
    }

    return { state, sampleTime, reset };
  }

  return { createClockSync };
});
