export function createAudio() {
  let ctx = null;
  let master = null;
  let limiter = null;
  let dcBlock = null;
  let reverbNode = null;
  let reverbSend = null;
  let ambient = null;
  let ambientGain = null;
  let musicGain = null;
  let bass = null;
  let mid = null;
  let noiseBed = null;
  let noiseBedGain = null;
  let breathingLfo = null;
  let breathingDepth = null;
  let heartbeatGain = null;
  let heartbeatOsc = null;
  let nextPulseAt = 0;
  let currentDanger = 0;
  let lastDeath = 0;
  let lastImpact = 0;
  let lastScream = 0;
  let nextDreadAt = 0;
  let nextAmbientEventAt = 0;
  let nextDripAt = 0;
  let enabled = true;
  let lastShot = 0;
  let lastFog = 0;

  // ── Context bootstrap ────────────────────────────────────────────────────

  function ensure() {
    if (!enabled) return null;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    if (!ctx) {
      ctx = new Ctx();

      // DC-block highpass at 20 Hz to remove any offset
      dcBlock = ctx.createBiquadFilter();
      dcBlock.type = 'highpass';
      dcBlock.frequency.value = 20;

      limiter = ctx.createDynamicsCompressor();
      limiter.threshold.value = -18;
      limiter.knee.value = 24;
      limiter.ratio.value = 7;
      limiter.attack.value = 0.006;
      limiter.release.value = 0.2;

      master = ctx.createGain();
      master.gain.value = 0.32;

      master.connect(dcBlock);
      dcBlock.connect(limiter);
      limiter.connect(ctx.destination);
    }
    if (ctx.state === 'suspended') ctx.resume()?.catch?.(() => {});
    return ctx;
  }

  // ── Impulse-response reverb ──────────────────────────────────────────────

  function makeImpulse(c, duration = 0.6, decay = 3.0) {
    const len = Math.floor(c.sampleRate * duration);
    const buf = c.createBuffer(2, len, c.sampleRate);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      for (let i = 0; i < len; i++)
        d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, decay);
    }
    return buf;
  }

  function initReverb(c) {
    if (reverbNode) return;
    reverbNode = c.createConvolver();
    reverbNode.normalize = true;
    reverbNode.buffer = makeImpulse(c, 0.6, 3.0);
    reverbSend = c.createGain();
    reverbSend.gain.value = 0;          // stays silent until set per-sound
    reverbSend.connect(reverbNode);
    reverbNode.connect(master);
  }

  // Helper: connect source to reverb with a given wet level (temporary send)
  function sendToReverb(c, sourceNode, wet = 0.22) {
    if (!reverbSend || !reverbNode) return;
    const send = c.createGain();
    send.gain.value = wet;
    sourceNode.connect(send);
    send.connect(reverbNode);
  }

  // ── Stereo panner ────────────────────────────────────────────────────────

  function makePanner(c, amount = 0.3) {
    let p;
    try {
      p = c.createStereoPanner();
      p.pan.value = (Math.random() * 2 - 1) * amount;
    } catch (e) {
      // fallback: just a gain pass-through
      p = c.createGain();
    }
    p.connect(master);
    return p;
  }

  // ── Waveshaper distortion ────────────────────────────────────────────────

  function makeDistortion(c, amount = 300) {
    const ws = c.createWaveShaper();
    const k = amount;
    const n = 256;
    const curve = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const x = (i * 2) / n - 1;
      curve[i] = ((Math.PI + k) * x) / (Math.PI + k * Math.abs(x));
    }
    ws.curve = curve;
    return ws;
  }

  // ── Noise buffers ────────────────────────────────────────────────────────

  function makeNoiseBuffer(c, duration = 5.2) {
    const buffer = c.createBuffer(1, Math.max(1, Math.floor(c.sampleRate * duration)), c.sampleRate);
    const data = buffer.getChannelData(0);
    let last = 0;
    for (let i = 0; i < data.length; i++) {
      last = last * 0.985 + (Math.random() * 2 - 1) * 0.12;
      const fade = Math.min(1, i / 800, (data.length - i) / 800);
      data[i] = last * fade;
    }
    return buffer;
  }

  function makeWhiteBuffer(c, duration) {
    const len = Math.max(1, Math.floor(c.sampleRate * duration));
    const buf = c.createBuffer(1, len, c.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    return buf;
  }

  // ── Low-level synthesis helpers ──────────────────────────────────────────

  // Returns a GainNode already connected to `dest` (default master) with an
  // ADSR-style envelope applied to its gain.
  function makeEnvGain(c, dest, peak, attackTime, decayTime, startVal = 0.0001) {
    const now = c.currentTime;
    const g = c.createGain();
    g.gain.setValueAtTime(startVal, now);
    g.gain.linearRampToValueAtTime(peak, now + attackTime);
    g.gain.exponentialRampToValueAtTime(0.0001, now + attackTime + decayTime);
    g.connect(dest || master);
    return g;
  }

  // Quick one-shot noise burst through a biquad filter
  function burstNoise(c, dest, filterType, freq, Q, vol, attack, decay, pan = 0) {
    const now = c.currentTime;
    const duration = attack + decay + 0.02;
    const buf = makeWhiteBuffer(c, duration);
    const src = c.createBufferSource();
    src.buffer = buf;

    const filt = c.createBiquadFilter();
    filt.type = filterType;
    filt.frequency.value = freq;
    filt.Q.value = Q;

    const g = c.createGain();
    g.gain.setValueAtTime(0.0001, now);
    g.gain.linearRampToValueAtTime(vol, now + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, now + attack + decay);

    let panner;
    try {
      panner = c.createStereoPanner();
      panner.pan.value = pan;
    } catch (e) {
      panner = c.createGain();
    }

    src.connect(filt);
    filt.connect(g);
    g.connect(panner);
    panner.connect(dest || master);

    src.start(now);
    src.stop(now + duration);
  }

  // One-shot oscillator with pitch slide
  function burstOsc(c, dest, type, startFreq, endFreq, vol, attack, decay, pan = 0) {
    const now = c.currentTime;
    const duration = attack + decay + 0.02;

    const osc = c.createOscillator();
    osc.type = type;
    osc.frequency.setValueAtTime(startFreq, now);
    if (endFreq !== startFreq)
      osc.frequency.exponentialRampToValueAtTime(Math.max(20, endFreq), now + attack + decay);

    const g = c.createGain();
    g.gain.setValueAtTime(0.0001, now);
    g.gain.linearRampToValueAtTime(vol, now + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, now + attack + decay);

    let panner;
    try {
      panner = c.createStereoPanner();
      panner.pan.value = pan;
    } catch (e) {
      panner = c.createGain();
    }

    osc.connect(g);
    g.connect(panner);
    panner.connect(dest || master);

    osc.start(now);
    osc.stop(now + duration);
  }

  // Delay helper (replaces setTimeout-based scheduling)
  function at(c, fn, delaySec) {
    // Use AudioContext clock for precise scheduling via a short timeout
    const ms = Math.max(0, delaySec * 1000);
    setTimeout(fn, ms);
  }

  // ── Formant voice synthesizer ────────────────────────────────────────────

  // formants = [{freq, Q, gain}, ...]
  function formantNoise(c, dest, formants, duration, vol, pan = 0, pitchDrop = false) {
    if (!c) return;
    const now = c.currentTime;
    const buf = makeWhiteBuffer(c, duration + 0.05);
    const src = c.createBufferSource();
    src.buffer = buf;

    const sumGain = c.createGain();
    sumGain.gain.value = vol;
    sumGain.gain.setValueAtTime(vol, now);
    sumGain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

    // Parallel bandpass filters
    for (const f of formants) {
      const bp = c.createBiquadFilter();
      bp.type = 'bandpass';
      bp.frequency.value = f.freq;
      bp.Q.value = f.Q;
      const fGain = c.createGain();
      fGain.gain.value = f.gain;
      if (pitchDrop) {
        bp.frequency.setValueAtTime(f.freq, now);
        bp.frequency.exponentialRampToValueAtTime(Math.max(40, f.freq * 0.35), now + duration);
      }
      src.connect(bp);
      bp.connect(fGain);
      fGain.connect(sumGain);
    }

    let panner;
    try {
      panner = c.createStereoPanner();
      panner.pan.value = pan;
    } catch (e) {
      panner = c.createGain();
    }

    sumGain.connect(panner);
    panner.connect(dest || master);
    sendToReverb(c, sumGain, 0.18);

    src.start(now);
    src.stop(now + duration + 0.05);
  }

  // Formant presets
  const FORMANTS = {
    growl:  [{freq: 380, Q: 8, gain: 1}, {freq: 780, Q: 5, gain: 0.7}, {freq: 1200, Q: 4, gain: 0.4}],
    scream: [{freq: 900, Q: 6, gain: 1}, {freq: 1800, Q: 5, gain: 0.8}, {freq: 3200, Q: 4, gain: 0.6}],
    moan:   [{freq: 200, Q: 10, gain: 1}, {freq: 450, Q: 8, gain: 0.8}, {freq: 900, Q: 6, gain: 0.4}],
    death:  [{freq: 150, Q: 8, gain: 1}, {freq: 380, Q: 6, gain: 0.7}],
  };

  // ── Ambient internal helpers ─────────────────────────────────────────────

  function metalCreak(intensity = 1) {
    const c = ensure();
    if (!c) return;
    const amount = Math.max(0.45, Math.min(1.9, intensity));
    const pan = (Math.random() * 2 - 1) * 0.28;
    burstNoise(c, master, 'bandpass', 700 + Math.random() * 80, 2.4, 0.045 * amount, 0.02, 0.48, pan);
    burstOsc(c, master, 'sawtooth', 190 + Math.random() * 80, 85, 0.026 * amount, 0.01, 0.45, pan);
    at(c, () => {
      const cc = ensure();
      if (!cc) return;
      burstOsc(cc, master, 'triangle', 72, 54, 0.026 * amount, 0.01, 0.33, pan);
      burstNoise(cc, master, 'highpass', 2100, 0.55, 0.06 * amount, 0.01, 0.12, pan);
    }, 0.34);
  }

  function radioWhisper(intensity = 1) {
    const c = ensure();
    if (!c) return;
    const amount = Math.max(0.45, Math.min(1.8, intensity));
    const pan = (Math.random() * 2 - 1) * 0.3;
    burstNoise(c, master, 'bandpass', 1180, 3.5, 0.055 * amount, 0.02, 0.83, pan);
    burstOsc(c, master, 'square', 246, 216, 0.018 * amount, 0.005, 0.095, pan);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'square', 311, 256, 0.014 * amount, 0.005, 0.075, pan);
    }, 0.13);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'square', 174, 149, 0.016 * amount, 0.005, 0.115, pan);
    }, 0.28);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstNoise(cc, master, 'highpass', 2600, 0.8, 0.04 * amount, 0.01, 0.15, pan);
    }, 0.5);
  }

  function distantScream(intensity = 1) {
    const c = ensure();
    if (!c) return;
    if (c.currentTime - lastScream < 2.6) return;
    lastScream = c.currentTime;
    const amount = Math.max(0.55, Math.min(2.1, intensity));
    const pan = (Math.random() * 2 - 1) * 0.35;
    formantNoise(c, master, FORMANTS.scream, 0.55, 0.045 * amount, pan);
    burstOsc(c, master, 'sawtooth', 620, 960, 0.028 * amount, 0.02, 0.5, pan);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'triangle', 930, 410, 0.032 * amount, 0.01, 0.25, pan);
    }, 0.08);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'sawtooth', 410, 230, 0.022 * amount, 0.02, 0.34, pan);
    }, 0.32);
  }

  function monsterGrowl(intensity = 1) {
    const c = ensure();
    if (!c) return;
    const amount = Math.max(0.55, Math.min(2.2, intensity));
    const pan = (Math.random() * 2 - 1) * 0.32;
    const dist = makeDistortion(c, 220);
    formantNoise(c, dist, FORMANTS.growl, 0.72, 0.075 * amount, 0, false);
    dist.connect(master);
    burstOsc(c, master, 'sawtooth', 72, 48, 0.065 * amount, 0.02, 0.76, pan);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'triangle', 93, 58, 0.04 * amount, 0.01, 0.45, pan);
    }, 0.08);
  }

  function slam(intensity = 1) {
    const c = ensure();
    if (!c) return;
    const amount = Math.max(0.45, Math.min(2.2, intensity));
    const pan = (Math.random() * 2 - 1) * 0.15;
    burstNoise(c, master, 'lowpass', 90, 0.5, 0.2 * amount, 0.002, 0.158, pan);
    burstOsc(c, master, 'sine', 42, 32, 0.18 * amount, 0.002, 0.338, pan);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstNoise(cc, master, 'bandpass', 1500, 1.8, 0.08 * amount, 0.01, 0.11, pan);
    }, 0.05);
    sendToReverb(c, (() => {
      const g = c.createGain(); g.gain.value = 0.25 * amount; g.connect(master); return g;
    })(), 0.2);
  }

  function jumpScare(intensity = 1) {
    const c = ensure();
    if (!c) return;
    const amount = Math.max(0.6, Math.min(2.4, intensity));
    slam(0.9 * amount);
    burstNoise(c, master, 'highpass', 2400, 0.65, 0.14 * amount, 0.002, 0.238, 0);
    burstOsc(c, master, 'square', 980, 370, 0.045 * amount, 0.005, 0.155, 0);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'sawtooth', 68, 46, 0.08 * amount, 0.01, 0.41, 0);
    }, 0.08);
  }

  function alarm(intensity = 1) {
    const c = ensure();
    if (!c) return;
    const amount = Math.max(0.55, Math.min(2, intensity));
    slam(0.55 * amount);
    for (let i = 0; i < 3; i++) {
      at(c, () => {
        const cc = ensure(); if (!cc) return;
        const pan = (Math.random() * 2 - 1) * 0.2;
        burstOsc(cc, master, 'sawtooth', 420, 580, 0.035 * amount, 0.01, 0.17, pan);
        burstNoise(cc, master, 'bandpass', 900, 1.3, 0.045 * amount, 0.01, 0.11, pan);
      }, i * 0.32);
    }
  }

  function drip() {
    const c = ensure();
    if (!c) return;
    const pan = (Math.random() * 2 - 1) * 0.5;
    burstNoise(c, master, 'highpass', 3200 + Math.random() * 2000, 4, 0.018, 0.003, 0.04, pan);
    burstOsc(c, master, 'sine', 1200 + Math.random() * 400, 600, 0.012, 0.003, 0.05, pan);
    sendToReverb(c, (() => { const g = c.createGain(); g.gain.value = 0.01; g.connect(master); return g; })(), 0.38);
  }

  function distantMoan() {
    const c = ensure();
    if (!c) return;
    const pan = (Math.random() * 2 - 1) * 0.4;
    formantNoise(c, master, FORMANTS.moan, 1.2, 0.018, pan, false);
    burstOsc(c, master, 'sine', 95 + Math.random() * 20, 65, 0.014, 0.08, 1.1, pan);
  }

  function ambientEvent(danger = 0) {
    const c = ensure();
    if (!c) return;
    const roll = Math.random();
    const intensity = 0.75 + danger * 0.6;
    if (roll < 0.22) radioWhisper(intensity);
    else if (roll < 0.44) metalCreak(intensity);
    else if (roll < 0.60) distantScream(intensity);
    else if (roll < 0.72) distantMoan();
    else if (roll < 0.84) monsterGrowl(0.7 + danger * 0.5);
    else jumpScare(0.72 + danger * 0.45);
  }

  // ── Public API ────────────────────────────────────────────────────────────

  function unlock() {
    ensure();
    startAmbient();
  }

  function setEnabled(on) {
    enabled = on;
    if (!enabled && master) master.gain.setTargetAtTime(0, ctx.currentTime, 0.02);
    if (enabled) {
      ensure();
      if (master) master.gain.setTargetAtTime(0.32, ctx.currentTime, 0.04);
      startAmbient();
    }
  }

  function startAmbient() {
    const c = ensure();
    if (!c || ambient) return;

    initReverb(c);

    musicGain = c.createGain();
    musicGain.gain.value = 0.9;
    musicGain.connect(master);

    // Sub drone
    ambient = c.createOscillator();
    ambient.type = 'sine';
    ambient.frequency.value = 46;
    ambientGain = c.createGain();
    ambientGain.gain.value = 0.04;
    ambient.connect(ambientGain);
    ambientGain.connect(musicGain);
    ambient.start();

    // Deep bass tone
    bass = c.createOscillator();
    bass.type = 'triangle';
    bass.frequency.value = 31;
    const bassGain = c.createGain();
    bassGain.gain.value = 0.034;
    bass.connect(bassGain);
    bassGain.connect(musicGain);
    bass.start();

    // Mid layer
    const midFilter = c.createBiquadFilter();
    midFilter.type = 'lowpass';
    midFilter.frequency.value = 420;
    midFilter.Q.value = 0.9;
    mid = c.createOscillator();
    mid.type = 'sawtooth';
    mid.frequency.value = 73;
    const midGain = c.createGain();
    midGain.gain.value = 0.014;
    mid.connect(midFilter);
    midFilter.connect(midGain);
    midGain.connect(musicGain);
    mid.start();

    // Noise bed with slow breathing LFO (0.2 Hz)
    const bedFilter = c.createBiquadFilter();
    bedFilter.type = 'bandpass';
    bedFilter.frequency.value = 185;
    bedFilter.Q.value = 0.55;
    noiseBedGain = c.createGain();
    noiseBedGain.gain.value = 0.046;
    noiseBed = c.createBufferSource();
    noiseBed.buffer = makeNoiseBuffer(c);
    noiseBed.loop = true;
    noiseBed.connect(bedFilter);
    bedFilter.connect(noiseBedGain);
    noiseBedGain.connect(musicGain);
    noiseBed.start();

    // Fast tension LFO (0.09 Hz)
    const tensionLfo = c.createOscillator();
    const tensionDepth = c.createGain();
    tensionLfo.type = 'sine';
    tensionLfo.frequency.value = 0.09;
    tensionDepth.gain.value = 0.012;
    tensionLfo.connect(tensionDepth);
    tensionDepth.connect(noiseBedGain.gain);
    tensionLfo.start();

    // Slow breathing LFO (0.2 Hz) on the noise bed
    breathingLfo = c.createOscillator();
    breathingDepth = c.createGain();
    breathingLfo.type = 'sine';
    breathingLfo.frequency.value = 0.2;
    breathingDepth.gain.value = 0.008;
    breathingLfo.connect(breathingDepth);
    breathingDepth.connect(noiseBedGain.gain);
    breathingLfo.start();

    // Heartbeat oscillator
    heartbeatOsc = c.createOscillator();
    heartbeatOsc.type = 'sine';
    heartbeatOsc.frequency.value = 58;
    heartbeatGain = c.createGain();
    heartbeatGain.gain.value = 0.0001;
    heartbeatOsc.connect(heartbeatGain);
    heartbeatGain.connect(musicGain);
    heartbeatOsc.start();

    nextDreadAt = c.currentTime + 5.5 + Math.random() * 4;
    nextPulseAt = c.currentTime + 1.2;
    nextAmbientEventAt = c.currentTime + 2.4 + Math.random() * 3.2;
    nextDripAt = c.currentTime + 3 + Math.random() * 8;
  }

  function pulse(intensity = 1) {
    if (!ctx || !heartbeatGain) return;
    const now = ctx.currentTime;
    const volume = 0.09 + Math.min(0.12, intensity * 0.055);
    heartbeatGain.gain.cancelScheduledValues(now);
    heartbeatGain.gain.setValueAtTime(0.0001, now);
    heartbeatGain.gain.exponentialRampToValueAtTime(volume, now + 0.025);
    heartbeatGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.24);
    heartbeatGain.gain.exponentialRampToValueAtTime(volume * 0.72, now + 0.34);
    heartbeatGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.62);
    // Low thud component
    if (ctx) burstOsc(ctx, master, 'sine', 55, 30, 0.04 * Math.min(1.5, intensity), 0.008, 0.22, 0);
  }

  function update(danger = 0) {
    if (!enabled || !ctx || !ambientGain) return;
    currentDanger = danger;
    ambientGain.gain.setTargetAtTime(0.038 + Math.min(0.105, danger * 0.062), ctx.currentTime, 0.18);
    if (ambient) ambient.frequency.setTargetAtTime(42 + Math.min(28, danger * 16), ctx.currentTime, 0.22);
    if (bass) bass.frequency.setTargetAtTime(29 + Math.min(6, danger * 3), ctx.currentTime, 0.4);
    if (mid)
      mid.frequency.setTargetAtTime(
        70 + Math.sin(ctx.currentTime * 0.37) * 3 + Math.min(18, danger * 9),
        ctx.currentTime,
        0.45,
      );
    if (musicGain) musicGain.gain.setTargetAtTime(0.82 + Math.min(0.36, danger * 0.22), ctx.currentTime, 0.35);
    if (noiseBedGain) noiseBedGain.gain.setTargetAtTime(0.046 + Math.min(0.07, danger * 0.04), ctx.currentTime, 0.4);

    // Heartbeat tempo varies with danger: faster under high danger
    const beatInterval = Math.max(0.55, 1.65 + Math.random() * 1.2 - Math.min(0.65, danger * 0.45));

    if (ctx.currentTime >= nextPulseAt) {
      pulse(0.7 + danger);
      nextPulseAt = ctx.currentTime + beatInterval;
    }
    if (ctx.currentTime >= nextAmbientEventAt) {
      ambientEvent(danger);
      nextAmbientEventAt = ctx.currentTime + 5.8 + Math.random() * 6.6 - Math.min(3.1, danger * 2.2);
    }
    if (ctx.currentTime >= nextDreadAt) {
      if (danger > 0.18 || Math.random() < 0.34) dread(0.85 + danger * 0.7);
      nextDreadAt = ctx.currentTime + 5.2 + Math.random() * 7.4 - Math.min(2.6, danger * 1.4);
    }
    // Occasional dripping water
    if (ctx.currentTime >= nextDripAt) {
      drip();
      nextDripAt = ctx.currentTime + 4 + Math.random() * 14 - Math.min(3, danger * 2);
    }
  }

  // ── Weapon shot ──────────────────────────────────────────────────────────

  const WEAPON_CFG = {
    pistol:   { subVol: 0.5,  midVol: 0.3,  highVol: 0.15, subFreq: 75, bodyStart: 120, bodyEnd: 40, decay: 0.16, pan: 0.08 },
    rifle:    { subVol: 0.7,  midVol: 0.25, highVol: 0.2,  subFreq: 60, bodyStart: 100, bodyEnd: 32, decay: 0.28, pan: 0.08 },
    shotgun:  { subVol: 0.8,  midVol: 0.4,  highVol: 0.22, subFreq: 65, bodyStart: 110, bodyEnd: 38, decay: 0.38, pan: 0.06 },
    smg:      { subVol: 0.35, midVol: 0.2,  highVol: 0.12, subFreq: 90, bodyStart: 130, bodyEnd: 48, decay: 0.10, pan: 0.08 },
    launcher: { subVol: 0.9,  midVol: 0.3,  highVol: 0.12, subFreq: 48, bodyStart:  90, bodyEnd: 22, decay: 0.55, pan: 0.05 },
  };

  function shotLayer(c, cfg, delayOffset = 0) {
    const now = c.currentTime + delayOffset;
    const pitchVar = 1 + (Math.random() * 0.06 - 0.03); // ±3%

    // 1. Sub-bass punch (lowpass noise, 30-60ms)
    {
      const dur = cfg.decay * 0.32;
      const buf = makeWhiteBuffer(c, dur + 0.01);
      const src = c.createBufferSource();
      src.buffer = buf;
      const filt = c.createBiquadFilter();
      filt.type = 'lowpass';
      filt.frequency.value = cfg.subFreq * pitchVar;
      filt.Q.value = 0.6;
      const g = c.createGain();
      g.gain.setValueAtTime(0.0001, now);
      g.gain.linearRampToValueAtTime(cfg.subVol, now + 0.003);
      g.gain.exponentialRampToValueAtTime(0.0001, now + dur);
      let pan; try { pan = c.createStereoPanner(); pan.pan.value = cfg.pan; } catch (e) { pan = c.createGain(); }
      src.connect(filt); filt.connect(g); g.connect(pan); pan.connect(master);
      sendToReverb(c, g, 0.15);
      src.start(now); src.stop(now + dur + 0.01);
    }

    // 2. Mid crack (bandpass 300-1200 Hz)
    {
      const dur = cfg.decay * 0.55;
      const buf = makeWhiteBuffer(c, dur + 0.01);
      const src = c.createBufferSource();
      src.buffer = buf;
      const filt = c.createBiquadFilter();
      filt.type = 'bandpass';
      filt.frequency.value = (350 + Math.random() * 400) * pitchVar;
      filt.Q.value = 1.2;
      const g = c.createGain();
      g.gain.setValueAtTime(0.0001, now);
      g.gain.linearRampToValueAtTime(cfg.midVol, now + 0.004);
      g.gain.exponentialRampToValueAtTime(0.0001, now + dur);
      let pan; try { pan = c.createStereoPanner(); pan.pan.value = cfg.pan + (Math.random() * 0.06 - 0.03); } catch (e) { pan = c.createGain(); }
      src.connect(filt); filt.connect(g); g.connect(pan); pan.connect(master);
      src.start(now); src.stop(now + dur + 0.01);
    }

    // 3. High snap (highpass 3k-8kHz, very short)
    {
      const dur = Math.min(0.04, cfg.decay * 0.25);
      const buf = makeWhiteBuffer(c, dur + 0.005);
      const src = c.createBufferSource();
      src.buffer = buf;
      const filt = c.createBiquadFilter();
      filt.type = 'highpass';
      filt.frequency.value = 3000 + Math.random() * 3000;
      const g = c.createGain();
      g.gain.setValueAtTime(0.0001, now);
      g.gain.linearRampToValueAtTime(cfg.highVol, now + 0.002);
      g.gain.exponentialRampToValueAtTime(0.0001, now + dur);
      let pan; try { pan = c.createStereoPanner(); pan.pan.value = cfg.pan; } catch (e) { pan = c.createGain(); }
      src.connect(filt); filt.connect(g); g.connect(pan); pan.connect(master);
      src.start(now); src.stop(now + dur + 0.005);
    }

    // 4. Body tone (oscillator pitch drop)
    {
      const dur = cfg.decay * 0.85;
      const osc = c.createOscillator();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(cfg.bodyStart * pitchVar, now);
      osc.frequency.exponentialRampToValueAtTime(Math.max(20, cfg.bodyEnd), now + dur * 0.6);
      const g = c.createGain();
      g.gain.setValueAtTime(0.0001, now);
      g.gain.linearRampToValueAtTime(cfg.subVol * 0.5, now + 0.005);
      g.gain.exponentialRampToValueAtTime(0.0001, now + dur);
      let pan; try { pan = c.createStereoPanner(); pan.pan.value = cfg.pan; } catch (e) { pan = c.createGain(); }
      osc.connect(g); g.connect(pan); pan.connect(master);
      osc.start(now); osc.stop(now + dur + 0.01);
    }
  }

  function shot(weaponId = 'pistol') {
    const c = ensure();
    if (!c || c.currentTime - lastShot < 0.025) return;
    lastShot = c.currentTime;
    const cfg = WEAPON_CFG[weaponId] || WEAPON_CFG.pistol;

    if (weaponId === 'shotgun') {
      // Multiple burst layers for pellet spread
      shotLayer(c, cfg, 0);
      shotLayer(c, { ...cfg, subVol: cfg.subVol * 0.45, midVol: cfg.midVol * 0.4, highVol: cfg.highVol * 0.5 }, 0.012);
      shotLayer(c, { ...cfg, subVol: cfg.subVol * 0.3,  midVol: cfg.midVol * 0.3, highVol: cfg.highVol * 0.4 }, 0.024);
    } else {
      shotLayer(c, cfg, 0);
    }
  }

  // ── Melee ────────────────────────────────────────────────────────────────

  function melee() {
    const c = ensure();
    if (!c) return;
    const pan = (Math.random() * 2 - 1) * 0.2;

    // Pre-swing whoosh: highpass sweep 2kHz → 500Hz
    burstNoise(c, master, 'highpass', 2000, 0.8, 0.055, 0.001, 0.018, pan);

    // Impact: formant thud
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'sine', 150, 55, 0.08, 0.004, 0.09, pan);
      // Flesh crack: bandpass 800Hz
      burstNoise(cc, master, 'bandpass', 800, 3, 0.06, 0.003, 0.065, pan);
      // Blood splat: short pink-ish noise at 600Hz
      burstNoise(cc, master, 'bandpass', 600, 1.5, 0.04, 0.002, 0.05, pan);
    }, 0.018);
  }

  // ── Reload ───────────────────────────────────────────────────────────────

  function reload() {
    const c = ensure();
    if (!c) return;
    const pan = (Math.random() * 2 - 1) * 0.15;

    // Magazine release: metallic rattle 2-4kHz
    burstNoise(c, master, 'bandpass', 2800, 5, 0.06, 0.005, 0.055, pan);

    at(c, () => {
      const cc = ensure(); if (!cc) return;
      // Magazine insertion: slightly lower rattle
      burstNoise(cc, master, 'bandpass', 2000, 4, 0.055, 0.005, 0.06, pan);
    }, 0.12);

    at(c, () => {
      const cc = ensure(); if (!cc) return;
      // Slide/bolt: crisp metal click 3-5kHz, very short
      burstNoise(cc, master, 'bandpass', 3800, 6, 0.07, 0.002, 0.028, pan);
      burstOsc(cc, master, 'square', 1200, 900, 0.03, 0.002, 0.025, pan);
    }, 0.3);
  }

  // ── Empty click ──────────────────────────────────────────────────────────

  function empty() {
    const c = ensure();
    if (!c) return;
    const pan = 0.08;
    burstOsc(c, master, 'square', 210, 150, 0.06, 0.003, 0.057, pan);
    burstNoise(c, master, 'bandpass', 2600, 5, 0.04, 0.002, 0.04, pan);
  }

  // ── Pickup ───────────────────────────────────────────────────────────────

  function pickup() {
    const c = ensure();
    if (!c) return;
    const pan = (Math.random() * 2 - 1) * 0.25;
    burstOsc(c, master, 'triangle', 720, 840, 0.06, 0.01, 0.06, pan);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstNoise(cc, master, 'bandpass', 1800, 1.4, 0.025, 0.005, 0.075, pan);
    }, 0.02);
  }

  // ── Objective ────────────────────────────────────────────────────────────

  function objective() {
    const c = ensure();
    if (!c) return;
    burstOsc(c, master, 'sawtooth', 172, 114, 0.082, 0.01, 0.21, 0);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'triangle', 420, 500, 0.058, 0.01, 0.15, 0);
    }, 0.09);
    radioWhisper(0.55);
  }

  // ── Fog wave ─────────────────────────────────────────────────────────────

  function fogWave(reason = 'director') {
    const c = ensure();
    if (!c || c.currentTime - lastFog < 1.15) return;
    lastFog = c.currentTime;
    const intense = reason === 'extraction' || reason === 'terminal';
    const pan = (Math.random() * 2 - 1) * 0.12;
    burstNoise(c, master, 'bandpass', intense ? 180 : 240, 0.55, intense ? 0.16 : 0.12, 0.02, 0.4, pan);
    burstOsc(c, master, 'sawtooth', intense ? 42 : 52, intense ? 26 : 36, intense ? 0.1 : 0.072, 0.01, 0.57, pan);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'triangle', intense ? 360 : 290, intense ? 210 : 140, intense ? 0.04 : 0.026, 0.01, 0.11, pan);
    }, 0.08);
    if (reason === 'lab' || reason === 'medbay') at(c, () => distantScream(0.85), 0.28);
  }

  // ── Hit ──────────────────────────────────────────────────────────────────

  function hit() {
    const c = ensure();
    if (!c || c.currentTime - lastImpact < 0.06) return;
    lastImpact = c.currentTime;
    const pan = (Math.random() * 2 - 1) * 0.2;
    burstNoise(c, master, 'bandpass', 520, 1.2, 0.12, 0.005, 0.115, pan);
    burstOsc(c, master, 'triangle', 68, 50, 0.04, 0.005, 0.115, pan);
  }

  // ── Zombie death (3 variants) ────────────────────────────────────────────

  function zombieDeath() {
    const c = ensure();
    if (!c || c.currentTime - lastDeath < 0.75) return;
    lastDeath = c.currentTime;
    const pan = (Math.random() * 2 - 1) * 0.35;

    const variant = Math.floor(Math.random() * 3);

    if (variant === 0) {
      // Gurgle: formant moan with pitch drop
      formantNoise(c, master, FORMANTS.death, 0.45, 0.072, pan, true);
      burstOsc(c, master, 'sine', 85, 38, 0.055, 0.01, 0.43, pan);
    } else if (variant === 1) {
      // Screech that cuts off abruptly
      formantNoise(c, master, FORMANTS.scream, 0.28, 0.058, pan, false);
      burstOsc(c, master, 'sawtooth', 720, 420, 0.038, 0.01, 0.27, pan);
    } else {
      // Crumple: impact thud + dying moan
      burstOsc(c, master, 'sine', 95, 42, 0.065, 0.005, 0.22, pan);
      burstNoise(c, master, 'bandpass', 240, 1.5, 0.05, 0.005, 0.21, pan);
      at(c, () => {
        const cc = ensure(); if (!cc) return;
        formantNoise(cc, master, FORMANTS.moan, 0.38, 0.035, pan, true);
      }, 0.08);
    }

    // Always: body-fall thud (low thump 80Hz)
    burstOsc(c, master, 'sine', 82, 28, 0.08, 0.003, 0.085, pan);
    burstNoise(c, master, 'lowpass', 95, 0.5, 0.07, 0.003, 0.08, pan);

    if (Math.random() < 0.52) at(c, () => dread(0.78), 0.26);
  }

  // ── Screamer ─────────────────────────────────────────────────────────────

  function screamer() {
    const c = ensure();
    if (!c) return;
    const pan = (Math.random() * 2 - 1) * 0.15;
    // Distorted formant scream
    const dist = makeDistortion(c, 350);
    formantNoise(c, dist, FORMANTS.scream, 0.6, 0.09, pan, false);
    dist.connect(master);
    jumpScare(0.8);
    at(c, () => distantScream(1.85), 0.12);
  }

  // ── Leaper ───────────────────────────────────────────────────────────────

  function leaper() {
    const c = ensure();
    if (!c) return;
    const pan = (Math.random() * 2 - 1) * 0.3;
    burstNoise(c, master, 'highpass', 1800, 0.75, 0.11, 0.005, 0.175, pan);
    burstOsc(c, master, 'sawtooth', 680, 250, 0.038, 0.01, 0.17, pan);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'triangle', 72, 54, 0.05, 0.01, 0.17, pan);
      formantNoise(cc, master, FORMANTS.growl, 0.28, 0.038, pan, false);
    }, 0.08);
  }

  // ── Explosion ────────────────────────────────────────────────────────────

  function explosion() {
    const c = ensure();
    if (!c) return;

    // Heavy reverb send for explosion
    const expReverbGain = c.createGain();
    expReverbGain.gain.value = 0;
    expReverbGain.connect(master);
    if (reverbNode) {
      const expSend = c.createGain();
      expSend.gain.value = 0.45;
      expReverbGain.connect(expSend);
      expSend.connect(reverbNode);
    }

    const dest = expReverbGain;

    // 1. Sub-bass (20-55 Hz oscillator, very loud, 500ms)
    burstOsc(c, dest, 'sine', 80, 20, 0.85, 0.003, 0.497, 0);

    // 2. Bass boom (55-200 Hz bandpass noise, 600ms)
    burstNoise(c, dest, 'bandpass', 100, 0.7, 0.55, 0.01, 0.59, 0);

    // 3. Mid burst (200-1200 Hz bandpass noise, longer)
    burstNoise(c, dest, 'bandpass', 600, 1.5, 0.35, 0.025, 0.375, 0);

    // 4. High crack (1.5k-8kHz, very short 100ms)
    burstNoise(c, dest, 'highpass', 2500, 0.5, 0.28, 0.002, 0.098, 0);

    // 5. LFO shockwave: lowpass filter sweeping 100Hz → 4000Hz over 800ms
    {
      const now = c.currentTime;
      const duration = 0.82;
      const buf = makeWhiteBuffer(c, duration + 0.05);
      const src = c.createBufferSource();
      src.buffer = buf;
      const lp = c.createBiquadFilter();
      lp.type = 'lowpass';
      lp.frequency.setValueAtTime(100, now);
      lp.frequency.exponentialRampToValueAtTime(4000, now + 0.08);
      lp.frequency.exponentialRampToValueAtTime(800, now + duration);
      const g = c.createGain();
      g.gain.setValueAtTime(0.0001, now);
      g.gain.linearRampToValueAtTime(0.4, now + 0.005);
      g.gain.exponentialRampToValueAtTime(0.0001, now + duration);
      src.connect(lp); lp.connect(g); g.connect(dest);
      src.start(now); src.stop(now + duration + 0.05);
    }

    expReverbGain.gain.setValueAtTime(1, c.currentTime);
    expReverbGain.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + 1.5);
  }

  // ── Boss ─────────────────────────────────────────────────────────────────

  function boss() {
    const c = ensure();
    if (!c) return;
    const dist = makeDistortion(c, 400);
    formantNoise(c, dist, FORMANTS.growl, 1.1, 0.1, 0, false);
    dist.connect(master);
    slam(1.85);
    burstOsc(c, master, 'sawtooth', 38, 28, 0.14, 0.02, 1.23, 0);
    at(c, () => distantScream(1.55), 0.52);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'sine', 42, 22, 0.12, 0.01, 0.9, 0);
    }, 0.28);
  }

  // ── Facility ─────────────────────────────────────────────────────────────

  function facility(kind = '') {
    if (kind === 'generator') { alarm(1.05); metalCreak(1.15); return; }
    if (kind === 'armory')    { metalCreak(1.25); alarm(0.8); return; }
    if (kind === 'lab')       { radioWhisper(1.25); distantScream(1.05); return; }
    if (kind === 'medbay')    {
      radioWhisper(0.9);
      const c = ensure(); if (!c) return;
      at(c, () => burstOsc(ensure(), master, 'sine', 880, 700, 0.025, 0.005, 0.075, 0), 0.08);
      return;
    }
    metalCreak(0.8);
  }

  // ── Extract ──────────────────────────────────────────────────────────────

  function extract() {
    alarm(0.85);
    const c = ensure();
    if (!c) return;
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'sawtooth', 146, 218, 0.06, 0.01, 0.49, 0);
    }, 0.12);
    radioWhisper(1.1);
  }

  // ── Stage ────────────────────────────────────────────────────────────────

  function stage(bossStage = false) {
    dread(bossStage ? 1.55 : 1.05);
    metalCreak(1);
    const c = ensure();
    if (!c) return;
    if (bossStage) at(c, () => boss(), 0.38);
    else at(c, () => radioWhisper(0.95), 0.26);
  }

  // ── Reward ───────────────────────────────────────────────────────────────

  function reward() {
    const c = ensure();
    if (!c) return;
    const pan = (Math.random() * 2 - 1) * 0.15;
    burstOsc(c, master, 'triangle', 520, 640, 0.06, 0.01, 0.07, pan);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'triangle', 840, 760, 0.045, 0.01, 0.09, pan);
    }, 0.08);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstNoise(cc, master, 'highpass', 2400, 0.55, 0.025, 0.005, 0.155, pan);
    }, 0);
  }

  // ── Player death ─────────────────────────────────────────────────────────

  function playerDeath() {
    const c = ensure();
    if (!c) return;
    jumpScare(1.2);
    burstOsc(c, master, 'sawtooth', 42, 30, 0.11, 0.01, 1.09, 0);
    at(c, () => radioWhisper(1.2), 0.48);
  }

  // ── Dread ────────────────────────────────────────────────────────────────

  function dread(intensity = 1) {
    const c = ensure();
    if (!c) return;
    const amount = Math.max(0.4, Math.min(1.6, intensity));
    const pan = (Math.random() * 2 - 1) * 0.18;
    burstNoise(c, master, 'bandpass', 240, 0.5, 0.05 * amount, 0.02, 0.68, pan);
    burstOsc(c, master, 'sawtooth', 54, 32, 0.052 * amount, 0.01, 0.81, pan);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'triangle', 118, 70, 0.024 * amount, 0.01, 0.17, pan);
    }, 0.18);
  }

  // ── First blood ──────────────────────────────────────────────────────────

  function firstBlood() {
    const c = ensure();
    if (!c) return;
    slam(1.1);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'triangle', 480, 800, 0.07, 0.01, 0.13, 0);
    }, 0.06);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'triangle', 860, 1040, 0.055, 0.01, 0.11, 0);
    }, 0.1);
  }

  // ── Level up ─────────────────────────────────────────────────────────────

  function levelUp() {
    const c = ensure();
    if (!c) return;
    const pan = (Math.random() * 2 - 1) * 0.1;
    burstOsc(c, master, 'triangle', 520, 720, 0.07, 0.01, 0.08, pan);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'triangle', 780, 920, 0.065, 0.01, 0.09, pan);
    }, 0.08);
    at(c, () => {
      const cc = ensure(); if (!cc) return;
      burstOsc(cc, master, 'triangle', 1040, 1160, 0.055, 0.01, 0.09, pan);
      burstNoise(cc, master, 'highpass', 3200, 0.6, 0.03, 0.005, 0.215, pan);
    }, 0.16);
  }

  // ── Combo milestone ──────────────────────────────────────────────────────

  function comboMilestone(tier = 1) {
    const c = ensure();
    if (!c) return;
    const pan = (Math.random() * 2 - 1) * 0.12;
    if (tier >= 3) {
      slam(0.9);
      at(c, () => {
        const cc = ensure(); if (!cc) return;
        burstOsc(cc, master, 'triangle', 640, 920, 0.08, 0.01, 0.14, pan);
      }, 0.05);
      at(c, () => {
        const cc = ensure(); if (!cc) return;
        burstOsc(cc, master, 'triangle', 960, 1120, 0.07, 0.01, 0.12, pan);
      }, 0.08);
      at(c, () => {
        const cc = ensure(); if (!cc) return;
        burstOsc(cc, master, 'triangle', 1280, 1440, 0.06, 0.01, 0.10, pan);
      }, 0.11);
    } else if (tier === 2) {
      at(c, () => {
        const cc = ensure(); if (!cc) return;
        burstOsc(cc, master, 'triangle', 700, 940, 0.07, 0.01, 0.11, pan);
      }, 0.04);
      at(c, () => {
        const cc = ensure(); if (!cc) return;
        burstOsc(cc, master, 'triangle', 1050, 1170, 0.06, 0.01, 0.10, pan);
      }, 0.07);
      at(c, () => {
        const cc = ensure(); if (!cc) return;
        burstOsc(cc, master, 'triangle', 1400, 1460, 0.05, 0.01, 0.09, pan);
      }, 0.10);
    } else {
      burstOsc(c, master, 'triangle', 800, 1000, 0.07, 0.01, 0.08, pan);
      at(c, () => {
        const cc = ensure(); if (!cc) return;
        burstOsc(cc, master, 'triangle', 1200, 1300, 0.055, 0.01, 0.09, pan);
      }, 0.07);
    }
  }

  // ── Exported API ─────────────────────────────────────────────────────────

  return {
    get enabled() { return enabled; },
    setEnabled,
    unlock,
    update,
    shot,
    melee,
    reload,
    empty,
    pickup,
    objective,
    fogWave,
    hit,
    zombieDeath,
    screamer,
    leaper,
    explosion,
    boss,
    facility,
    extract,
    stage,
    reward,
    playerDeath,
    dread,
    firstBlood,
    levelUp,
    comboMilestone,
  };
}
