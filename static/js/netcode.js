(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.ZCNetcode = api;
})(typeof globalThis !== 'undefined' ? globalThis : window, function () {
  function inputSignature(keys, shooting, dash, aim, aimEps) {
    const eps = aimEps || 0.04;
    const aimBucket = Math.round((Number(aim) || 0) / eps);
    return [
      keys.up ? 1 : 0,
      keys.down ? 1 : 0,
      keys.left ? 1 : 0,
      keys.right ? 1 : 0,
      shooting ? 1 : 0,
      dash ? 1 : 0,
      aimBucket,
    ].join('|');
  }

  function shouldSendInput(options) {
    const cfg = Object.assign({ activeMs: 66, idleMs: 160 }, options || {});
    if (cfg.force) return true;
    const minMs = cfg.active ? cfg.activeMs : cfg.idleMs;
    if (cfg.now - cfg.lastInputAt < minMs) return false;
    if (!cfg.active && !cfg.changed) return false;
    return true;
  }

  function predictionSeq(inputSeq, hasUnsentInput = false) {
    const seq = Number.isFinite(inputSeq) ? inputSeq : Number(inputSeq) || 0;
    return Math.max(0, Math.floor(seq)) + (hasUnsentInput ? 1 : 0);
  }

  return {
    inputSignature,
    predictionSeq,
    shouldSendInput,
  };
});
