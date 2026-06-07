export function createAudio() {
  let ctx = null;
  let master = null;
  let limiter = null;
  let ambient = null;
  let ambientGain = null;
  let musicGain = null;
  let bass = null;
  let mid = null;
  let noiseBed = null;
  let noiseBedGain = null;
  let heartbeatGain = null;
  let nextPulseAt = 0;
  let lastDeath = 0;
  let lastImpact = 0;
  let lastScream = 0;
  let nextDreadAt = 0;
  let nextAmbientEventAt = 0;
  let enabled = true;
  let lastShot = 0;
  let lastFog = 0;

  function ensure() {
    if (!enabled) return null;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    if (!ctx) {
      ctx = new Ctx();
      limiter = ctx.createDynamicsCompressor();
      limiter.threshold.value = -18;
      limiter.knee.value = 24;
      limiter.ratio.value = 7;
      limiter.attack.value = 0.006;
      limiter.release.value = 0.2;
      master = ctx.createGain();
      master.gain.value = 0.32;
      master.connect(limiter);
      limiter.connect(ctx.destination);
    }
    if (ctx.state === 'suspended') ctx.resume()?.catch?.(() => {});
    return ctx;
  }

  function makeNoiseBuffer(c, duration = 5.2) {
    const buffer = c.createBuffer(1, Math.max(1, Math.floor(c.sampleRate * duration)), c.sampleRate);
    const data = buffer.getChannelData(0);
    let last = 0;
    for (let i = 0; i < data.length; i += 1) {
      last = last * 0.985 + (Math.random() * 2 - 1) * 0.12;
      const fade = Math.min(1, i / 800, (data.length - i) / 800);
      data[i] = last * fade;
    }
    return buffer;
  }

  function envGain(start, peak, end, duration) {
    const c = ensure();
    if (!c || !master) return null;
    const gain = c.createGain();
    gain.gain.setValueAtTime(start, c.currentTime);
    gain.gain.linearRampToValueAtTime(peak, c.currentTime + duration * 0.12);
    gain.gain.exponentialRampToValueAtTime(Math.max(0.0001, end), c.currentTime + duration);
    gain.connect(master);
    return gain;
  }

  function tone(freq, duration, type = 'sine', volume = 0.16, slide = 0) {
    const c = ensure();
    const gain = envGain(0.0001, volume, 0.0001, duration);
    if (!c || !gain) return;
    const osc = c.createOscillator();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, c.currentTime);
    if (slide) osc.frequency.exponentialRampToValueAtTime(Math.max(20, freq + slide), c.currentTime + duration);
    osc.connect(gain);
    osc.start();
    osc.stop(c.currentTime + duration + 0.02);
  }

  function noise(duration, volume = 0.12, filter = 900) {
    return filteredNoise(duration, volume, filter, 'bandpass', 0.7);
  }

  function filteredNoise(duration, volume = 0.12, filter = 900, type = 'bandpass', q = 0.7) {
    const c = ensure();
    const gain = envGain(0.0001, volume, 0.0001, duration);
    if (!c || !gain) return;
    const buffer = c.createBuffer(1, Math.max(1, Math.floor(c.sampleRate * duration)), c.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < data.length; i += 1) {
      const tail = Math.pow(1 - i / data.length, 1.45);
      data[i] = (Math.random() * 2 - 1) * tail;
    }
    const source = c.createBufferSource();
    source.buffer = buffer;
    const biquad = c.createBiquadFilter();
    biquad.type = type;
    biquad.frequency.value = filter;
    biquad.Q.value = q;
    source.connect(biquad);
    biquad.connect(gain);
    source.start();
  }

  function toneAt(freq, delay, duration, type = 'sine', volume = 0.16, slide = 0) {
    setTimeout(() => tone(freq, duration, type, volume, slide), Math.max(0, delay * 1000));
  }

  function noiseAt(delay, duration, volume = 0.12, filter = 900, type = 'bandpass', q = 0.7) {
    setTimeout(() => filteredNoise(duration, volume, filter, type, q), Math.max(0, delay * 1000));
  }

  function dread(intensity = 1) {
    const amount = Math.max(0.4, Math.min(1.6, intensity));
    filteredNoise(0.7, 0.05 * amount, 240, 'bandpass', 0.5);
    tone(54, 0.82, 'sawtooth', 0.052 * amount, -22);
    toneAt(118, 0.18, 0.18, 'triangle', 0.024 * amount, -48);
  }

  function metalCreak(intensity = 1) {
    const amount = Math.max(0.45, Math.min(1.9, intensity));
    filteredNoise(0.5, 0.045 * amount, 720, 'bandpass', 2.4);
    tone(190 + Math.random() * 80, 0.46, 'sawtooth', 0.026 * amount, -105);
    toneAt(72, 0.13, 0.34, 'triangle', 0.026 * amount, -18);
    noiseAt(0.34, 0.13, 0.06 * amount, 2100, 'highpass', 0.55);
  }

  function radioWhisper(intensity = 1) {
    const amount = Math.max(0.45, Math.min(1.8, intensity));
    filteredNoise(0.85, 0.055 * amount, 1180, 'bandpass', 3.5);
    tone(246, 0.1, 'square', 0.018 * amount, -30);
    toneAt(311, 0.13, 0.08, 'square', 0.014 * amount, -55);
    toneAt(174, 0.28, 0.12, 'square', 0.016 * amount, -25);
    noiseAt(0.5, 0.16, 0.04 * amount, 2600, 'highpass', 0.8);
  }

  function distantScream(intensity = 1) {
    const c = ensure();
    if (!c) return;
    if (c.currentTime - lastScream < 2.6) return;
    lastScream = c.currentTime;
    const amount = Math.max(0.55, Math.min(2.1, intensity));
    filteredNoise(0.55, 0.06 * amount, 1500, 'bandpass', 2.1);
    tone(620, 0.52, 'sawtooth', 0.028 * amount, 340);
    toneAt(930, 0.08, 0.26, 'triangle', 0.032 * amount, -520);
    toneAt(410, 0.32, 0.36, 'sawtooth', 0.022 * amount, -180);
  }

  function slam(intensity = 1) {
    const amount = Math.max(0.45, Math.min(2.2, intensity));
    filteredNoise(0.16, 0.2 * amount, 90, 'lowpass', 0.5);
    tone(42, 0.34, 'sine', 0.18 * amount, -10);
    noiseAt(0.05, 0.12, 0.08 * amount, 1500, 'bandpass', 1.8);
  }

  function monsterGrowl(intensity = 1) {
    const amount = Math.max(0.55, Math.min(2.2, intensity));
    filteredNoise(0.72, 0.075 * amount, 170, 'bandpass', 0.65);
    tone(72, 0.78, 'sawtooth', 0.065 * amount, -24);
    toneAt(93, 0.08, 0.46, 'triangle', 0.04 * amount, -35);
  }

  function jumpScare(intensity = 1) {
    const amount = Math.max(0.6, Math.min(2.4, intensity));
    slam(0.9 * amount);
    filteredNoise(0.24, 0.14 * amount, 2400, 'highpass', 0.65);
    tone(980, 0.16, 'square', 0.045 * amount, -610);
    toneAt(68, 0.08, 0.42, 'sawtooth', 0.08 * amount, -22);
  }

  function alarm(intensity = 1) {
    const amount = Math.max(0.55, Math.min(2, intensity));
    slam(0.55 * amount);
    for (let i = 0; i < 3; i += 1) {
      toneAt(420, i * 0.32, 0.18, 'sawtooth', 0.035 * amount, 160);
      noiseAt(i * 0.32 + 0.05, 0.12, 0.045 * amount, 900, 'bandpass', 1.3);
    }
  }

  function ambientEvent(danger = 0) {
    const roll = Math.random();
    const intensity = 0.75 + danger * 0.6;
    if (roll < 0.24) radioWhisper(intensity);
    else if (roll < 0.48) metalCreak(intensity);
    else if (roll < 0.67) distantScream(intensity);
    else if (roll < 0.84) monsterGrowl(0.7 + danger * 0.5);
    else jumpScare(0.72 + danger * 0.45);
  }

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
    musicGain = c.createGain();
    musicGain.gain.value = 0.9;
    musicGain.connect(master);

    ambient = c.createOscillator();
    ambient.type = 'sine';
    ambient.frequency.value = 46;
    ambientGain = c.createGain();
    ambientGain.gain.value = 0.04;
    ambient.connect(ambientGain);
    ambientGain.connect(musicGain);
    ambient.start();

    const bassGain = c.createGain();
    bassGain.gain.value = 0.034;
    bass = c.createOscillator();
    bass.type = 'triangle';
    bass.frequency.value = 31;
    bass.connect(bassGain);
    bassGain.connect(musicGain);
    bass.start();

    const midGain = c.createGain();
    midGain.gain.value = 0.014;
    const filter = c.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 420;
    filter.Q.value = 0.9;
    mid = c.createOscillator();
    mid.type = 'sawtooth';
    mid.frequency.value = 73;
    mid.connect(filter);
    filter.connect(midGain);
    midGain.connect(musicGain);
    mid.start();

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

    const lfo = c.createOscillator();
    const lfoDepth = c.createGain();
    lfo.type = 'sine';
    lfo.frequency.value = 0.09;
    lfoDepth.gain.value = 0.012;
    lfo.connect(lfoDepth);
    lfoDepth.connect(noiseBedGain.gain);
    lfo.start();

    const heartbeat = c.createOscillator();
    heartbeat.type = 'sine';
    heartbeat.frequency.value = 58;
    heartbeatGain = c.createGain();
    heartbeatGain.gain.value = 0.0001;
    heartbeat.connect(heartbeatGain);
    heartbeatGain.connect(musicGain);
    heartbeat.start();

    nextDreadAt = c.currentTime + 5.5 + Math.random() * 4;
    nextPulseAt = c.currentTime + 1.2;
    nextAmbientEventAt = c.currentTime + 2.4 + Math.random() * 3.2;
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
  }

  function update(danger = 0) {
    if (!enabled || !ctx || !ambientGain) return;
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
    if (ctx.currentTime >= nextPulseAt) {
      pulse(0.7 + danger);
      nextPulseAt = ctx.currentTime + 1.65 + Math.random() * 1.2 - Math.min(0.65, danger * 0.45);
    }
    if (ctx.currentTime >= nextAmbientEventAt) {
      ambientEvent(danger);
      nextAmbientEventAt = ctx.currentTime + 5.8 + Math.random() * 6.6 - Math.min(3.1, danger * 2.2);
    }
    if (ctx.currentTime >= nextDreadAt) {
      if (danger > 0.18 || Math.random() < 0.34) dread(0.85 + danger * 0.7);
      nextDreadAt = ctx.currentTime + 5.2 + Math.random() * 7.4 - Math.min(2.6, danger * 1.4);
    }
  }

  function shot() {
    const c = ensure();
    if (!c || c.currentTime - lastShot < 0.035) return;
    lastShot = c.currentTime;
    noise(0.08, 0.2, 1300);
    tone(112, 0.08, 'square', 0.09, -42);
    noiseAt(0.04, 0.05, 0.05, 2600, 'highpass', 0.55);
  }

  function melee() {
    noise(0.065, 0.1, 2100);
    tone(310, 0.09, 'sawtooth', 0.07, -155);
    toneAt(86, 0.05, 0.08, 'triangle', 0.04, -18);
  }

  function reload() {
    metalCreak(0.75);
    toneAt(380, 0.03, 0.04, 'square', 0.045, -60);
    toneAt(520, 0.12, 0.035, 'square', 0.04, -80);
  }

  function empty() {
    tone(210, 0.06, 'square', 0.06, -60);
    metalCreak(0.55);
  }

  function pickup() {
    tone(720, 0.07, 'triangle', 0.06, 120);
    noiseAt(0.02, 0.08, 0.025, 1800, 'bandpass', 1.4);
  }

  function objective() {
    tone(172, 0.22, 'sawtooth', 0.082, -58);
    toneAt(420, 0.09, 0.16, 'triangle', 0.058, 80);
    radioWhisper(0.55);
  }

  function fogWave(reason = 'director') {
    const c = ensure();
    if (!c || c.currentTime - lastFog < 1.15) return;
    lastFog = c.currentTime;
    const intense = reason === 'extraction' || reason === 'terminal';
    filteredNoise(0.42, intense ? 0.16 : 0.12, intense ? 180 : 240, 'bandpass', 0.55);
    tone(intense ? 42 : 52, 0.58, 'sawtooth', intense ? 0.1 : 0.072, -16);
    toneAt(intense ? 360 : 290, 0.08, 0.12, 'triangle', intense ? 0.04 : 0.026, -150);
    if (reason === 'lab' || reason === 'medbay') setTimeout(() => distantScream(0.85), 280);
  }

  function hit() {
    const c = ensure();
    if (!c || c.currentTime - lastImpact < 0.06) return;
    lastImpact = c.currentTime;
    noise(0.12, 0.12, 520);
    tone(68, 0.12, 'triangle', 0.04, -18);
  }

  function zombieDeath() {
    const c = ensure();
    if (!c || c.currentTime - lastDeath < 0.75) return;
    lastDeath = c.currentTime;
    noise(0.24, 0.092, 330);
    tone(82, 0.24, 'sawtooth', 0.062, -40);
    if (Math.random() < 0.35) toneAt(510, 0.07, 0.11, 'triangle', 0.026, -330);
    if (Math.random() < 0.52) setTimeout(() => dread(0.78), 260);
  }

  function screamer() {
    distantScream(1.85);
    jumpScare(0.8);
  }

  function leaper() {
    filteredNoise(0.18, 0.11, 1800, 'highpass', 0.75);
    tone(680, 0.18, 'sawtooth', 0.038, -430);
    toneAt(72, 0.08, 0.18, 'triangle', 0.05, -18);
  }

  function explosion() {
    slam(1.45);
    filteredNoise(0.46, 0.18, 125, 'lowpass', 0.45);
    noiseAt(0.05, 0.2, 0.11, 2100, 'bandpass', 0.7);
  }

  function boss() {
    slam(1.85);
    monsterGrowl(1.85);
    toneAt(38, 0.28, 1.25, 'sawtooth', 0.14, -10);
    setTimeout(() => distantScream(1.55), 520);
  }

  function facility(kind = '') {
    if (kind === 'generator') {
      alarm(1.05);
      metalCreak(1.15);
      return;
    }
    if (kind === 'armory') {
      metalCreak(1.25);
      alarm(0.8);
      return;
    }
    if (kind === 'lab') {
      radioWhisper(1.25);
      distantScream(1.05);
      return;
    }
    if (kind === 'medbay') {
      radioWhisper(0.9);
      toneAt(880, 0.08, 0.08, 'sine', 0.025, -180);
      return;
    }
    metalCreak(0.8);
  }

  function extract() {
    alarm(0.85);
    toneAt(146, 0.12, 0.5, 'sawtooth', 0.06, 72);
    radioWhisper(1.1);
  }

  function stage(bossStage = false) {
    dread(bossStage ? 1.55 : 1.05);
    metalCreak(1);
    if (bossStage) setTimeout(() => boss(), 380);
    else setTimeout(() => radioWhisper(0.95), 260);
  }

  function reward() {
    tone(520, 0.08, 'triangle', 0.06, 120);
    toneAt(840, 0.08, 0.1, 'triangle', 0.045, -80);
    filteredNoise(0.16, 0.025, 2400, 'highpass', 0.55);
  }

  function playerDeath() {
    jumpScare(1.2);
    toneAt(42, 0.14, 1.1, 'sawtooth', 0.11, -12);
    setTimeout(() => radioWhisper(1.2), 480);
  }

  return {
    get enabled() {
      return enabled;
    },
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
  };
}
