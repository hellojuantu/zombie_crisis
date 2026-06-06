export function createEffects() {
  const particles = [];
  const rings = [];
  const decals = [];
  const maxParticles = 170;
  const maxRings = 18;
  const maxDecals = 55;

  function trim() {
    while (particles.length > maxParticles) particles.shift();
    while (rings.length > maxRings) rings.shift();
    while (decals.length > maxDecals) decals.shift();
  }

  function particlesAt(x, y, color, count, speed, life, size = 3) {
    const n = Math.max(0, Math.min(count, maxParticles - particles.length));
    for (let i = 0; i < n; i += 1) {
      const angle = Math.random() * Math.PI * 2;
      const velocity = Math.random() * speed + speed * 0.25;
      particles.push({
        x,
        y,
        dx: Math.cos(angle) * velocity,
        dy: Math.sin(angle) * velocity,
        color,
        life,
        maxLife: life,
        size: size * (0.7 + Math.random() * 0.8),
      });
    }
    trim();
  }

  function ring(x, y, radius, color, life, width = 3) {
    rings.push({ x, y, radius, color, life, maxLife: life, width });
    trim();
  }

  function line(x1, y1, x2, y2, color, life = 0.07, width = 2) {
    particles.push({ x: x1, y: y1, dx: x2 - x1, dy: y2 - y1, color, life, maxLife: life, size: width, line: true });
    trim();
  }

  function tracer(x1, y1, x2, y2, color) {
    rings.push({ x: x2, y: y2, radius: 16, color, life: 0.16, maxLife: 0.16, width: 2 });
    particles.push({ x: x1, y: y1, dx: x2 - x1, dy: y2 - y1, color, life: 0.08, maxLife: 0.08, size: 1, line: true });
    trim();
  }

  function slash(x, y, angle, radius, color, life = 0.16) {
    particles.push({
      x,
      y,
      dx: 0,
      dy: 0,
      color,
      life,
      maxLife: life,
      size: 1,
      slash: true,
      angle,
      radius,
      arc: 1.35,
      width: 11,
    });
    trim();
  }

  function blood(x, y, color = 'rgba(91,8,16,.68)') {
    decals.push({ x, y, r: 12 + Math.random() * 18, color, rot: Math.random() * Math.PI });
    trim();
  }

  function update(dt) {
    for (let i = particles.length - 1; i >= 0; i -= 1) {
      const p = particles[i];
      p.x += p.dx * dt;
      p.y += p.dy * dt;
      p.dx *= Math.pow(0.08, dt);
      p.dy *= Math.pow(0.08, dt);
      p.life -= dt;
      if (p.life <= 0) {
        particles[i] = particles[particles.length - 1];
        particles.pop();
      }
    }
    for (let i = rings.length - 1; i >= 0; i -= 1) {
      const r = rings[i];
      r.life -= dt;
      if (r.life <= 0) {
        rings[i] = rings[rings.length - 1];
        rings.pop();
      }
    }
  }

  function clear() {
    particles.length = 0;
    rings.length = 0;
    decals.length = 0;
  }

  return {
    particles,
    rings,
    decals,
    particlesAt,
    ring,
    line,
    tracer,
    slash,
    blood,
    update,
    clear,
  };
}
