function hexrgba(hex, alpha) {
  const h = (hex || '#ffffff').replace('#', '');
  const r = parseInt(h.substring(0, 2), 16) || 255;
  const g = parseInt(h.substring(2, 4), 16) || 255;
  const b = parseInt(h.substring(4, 6), 16) || 255;
  return `rgba(${r},${g},${b},${alpha})`;
}

function makeCanvas(w, h) {
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  return canvas;
}

function makeZombieSprite(type, color) {
  const isBoss = type === 'boss';
  const isCrawler = type === 'crawler';
  const isArmored = type === 'armored';
  const isLeaper = type === 'leaper';
  const isScreamer = type === 'screamer';
  const isBloater = type === 'bloater';
  const canvas = makeCanvas(96, 96);
  const ctx = canvas.getContext('2d');
  ctx.translate(48, 48);
  ctx.shadowColor = hexrgba(color, 0.65);
  ctx.shadowBlur = isBoss ? 24 : type === 'toxic' || isScreamer ? 18 : isBloater ? 15 : 8;
  ctx.fillStyle = 'rgba(0,0,0,.34)';
  ctx.beginPath();
  ctx.ellipse(0, isCrawler ? 28 : 24, isBoss ? 32 : isCrawler ? 22 : 25, isBoss ? 14 : isCrawler ? 8 : 11, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.rotate(isLeaper ? -0.28 : -0.12);
  ctx.lineCap = 'round';
  ctx.strokeStyle = isBoss ? '#3c1724' : isArmored ? '#3a4048' : '#283322';
  ctx.lineWidth = isBoss ? 11 : isCrawler ? 6 : 8;
  ctx.beginPath();
  ctx.moveTo(-16, isCrawler ? 6 : -3);
  ctx.lineTo(isBoss ? -40 : isCrawler ? -35 : -34, isBoss ? 14 : isCrawler ? 22 : 10);
  ctx.moveTo(17, isCrawler ? 7 : -1);
  ctx.lineTo(isBoss ? 40 : isCrawler ? 36 : 34, isBoss ? 15 : isCrawler ? 20 : 11);
  ctx.stroke();
  ctx.fillStyle = isBoss ? '#431b2a' : type === 'brute' ? '#5b4837' : isArmored ? '#5f6975' : isBloater ? '#6b4b32' : color;
  ctx.beginPath();
  ctx.ellipse(0, isCrawler ? 12 : 5, isBoss ? 27 : type === 'brute' || isArmored ? 21 : isBloater ? 24 : isCrawler ? 20 : 17, isBoss ? 30 : isCrawler ? 15 : type === 'runner' || isLeaper ? 21 : isBloater ? 27 : 25, 0, 0, Math.PI * 2);
  ctx.fill();
  if (isArmored) {
    ctx.strokeStyle = '#c9d4df';
    ctx.lineWidth = 4;
    for (let y = -12; y <= 12; y += 10) {
      ctx.beginPath();
      ctx.moveTo(-15, y);
      ctx.lineTo(15, y - 2);
      ctx.stroke();
    }
  } else if (isBloater) {
    ctx.fillStyle = hexrgba(color, 0.75);
    ctx.beginPath();
    ctx.arc(-9, 0, 5, 0, Math.PI * 2);
    ctx.arc(10, 8, 6, 0, Math.PI * 2);
    ctx.fill();
  } else if (isBoss) {
    ctx.strokeStyle = hexrgba(color, 0.9);
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(-20, -12);
    ctx.lineTo(-8, 3);
    ctx.lineTo(8, -5);
    ctx.lineTo(22, 10);
    ctx.stroke();
  }
  ctx.fillStyle = isScreamer ? '#332242' : '#2b3a2b';
  ctx.beginPath();
  ctx.ellipse(0, isCrawler ? -9 : -22, isBoss ? 19 : type === 'brute' || isArmored ? 16 : isScreamer ? 15 : 13, isBoss ? 17 : isCrawler ? 10 : type === 'runner' || isLeaper ? 12 : 14, 0, 0, Math.PI * 2);
  ctx.fill();
  if (isScreamer) {
    ctx.strokeStyle = hexrgba(color, 0.9);
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(0, -22, 23, -0.55, 0.55);
    ctx.stroke();
  }
  ctx.fillStyle = isBoss ? '#ffb3c8' : type === 'toxic' ? '#dfff5a' : isLeaper ? '#ffe0a3' : isScreamer ? '#f0d0ff' : '#fff1a6';
  ctx.beginPath();
  ctx.arc(-5, isCrawler ? -10 : -24, isBoss ? 3.2 : 2.3, 0, Math.PI * 2);
  ctx.arc(6, isCrawler ? -10 : -24, isBoss ? 3.2 : 2.3, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;
  ctx.strokeStyle = 'rgba(24,8,10,.7)';
  ctx.lineWidth = 2;
  for (let i = 0; i < (isCrawler ? 3 : 4); i += 1) {
    ctx.beginPath();
    ctx.moveTo(-9 + i * 6, isCrawler ? 8 : -5);
    ctx.lineTo(-12 + i * 6, isCrawler ? 18 : 14);
    ctx.stroke();
  }
  return canvas;
}

function renderScaleFor(w, h) {
  const native = Math.min(window.devicePixelRatio || 1, 2);
  const limit = Math.sqrt(920000 / Math.max(1, w * h));
  return Math.max(0.38, Math.min(native, limit));
}

export function createRenderer(canvas, minimap) {
  const ctx = canvas.getContext('2d', { alpha: false });
  const mini = minimap.getContext('2d');
  const sprites = {
    walker: makeZombieSprite('walker', '#6bd36b'),
    runner: makeZombieSprite('runner', '#9dff7a'),
    crawler: makeZombieSprite('crawler', '#7bdcff'),
    brute: makeZombieSprite('brute', '#8a6a4a'),
    toxic: makeZombieSprite('toxic', '#c4ff43'),
    armored: makeZombieSprite('armored', '#a9b1bc'),
    leaper: makeZombieSprite('leaper', '#ffb347'),
    screamer: makeZombieSprite('screamer', '#d88cff'),
    bloater: makeZombieSprite('bloater', '#ff8f52'),
    boss: makeZombieSprite('boss', '#ff4d7a'),
  };
  const groundMarks = Array.from({ length: 280 }, (_, i) => ({
    x: (i * 977 + 213) % 3400,
    y: (i * 619 + 89) % 3400,
    r: 8 + ((i * 37) % 34),
    a: 0.04 + ((i * 11) % 9) / 100,
  }));
  let width = 1;
  let height = 1;
  let dpr = 1;

  function resize() {
    const nextW = Math.max(1, window.innerWidth);
    const nextH = Math.max(1, window.innerHeight);
    const nextDpr = renderScaleFor(nextW, nextH);
    if (nextW === width && nextH === height && Math.abs(nextDpr - dpr) < 0.01) return;
    width = nextW;
    height = nextH;
    dpr = nextDpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    canvas.width = Math.max(1, Math.round(width * dpr));
    canvas.height = Math.max(1, Math.round(height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function clear() {
    ctx.fillStyle = '#11161d';
    ctx.fillRect(0, 0, width, height);
  }

  function drawGround(view, mapW, mapH) {
    const { x: cx, y: cy } = view;
    const grad = ctx.createLinearGradient(0, 0, width, height);
    grad.addColorStop(0, '#171c22');
    grad.addColorStop(0.55, '#101820');
    grad.addColorStop(1, '#1b1518');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = 'rgba(255,255,255,.045)';
    ctx.lineWidth = 1;
    const grid = 80;
    for (let x = -(cx % grid); x < width; x += grid) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = -(cy % grid); y < height; y += grid) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
    for (const mark of groundMarks) {
      const sx = mark.x - cx;
      const sy = mark.y - cy;
      if (sx < -60 || sx > width + 60 || sy < -60 || sy > height + 60) continue;
      ctx.beginPath();
      ctx.ellipse(sx, sy, mark.r * 1.7, mark.r, mark.a * 16, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0,0,0,${mark.a})`;
      ctx.fill();
    }
    ctx.strokeStyle = 'rgba(255,255,255,.24)';
    ctx.lineWidth = 3;
    ctx.strokeRect(-cx, -cy, mapW, mapH);
  }

  function drawObstacles(obs, view) {
    const { x: cx, y: cy } = view;
    for (const o of obs) {
      const sx = o.x - cx;
      const sy = o.y - cy;
      if (sx + o.w < -60 || sx > width + 60 || sy + o.h < -60 || sy > height + 60) continue;
      ctx.fillStyle = 'rgba(0,0,0,.28)';
      ctx.fillRect(sx + 5, sy + 6, o.w, o.h);
      ctx.fillStyle = '#323a42';
      ctx.fillRect(sx, sy, o.w, o.h);
      ctx.fillStyle = '#4d5a66';
      ctx.fillRect(sx, sy, o.w, 5);
      ctx.fillStyle = 'rgba(255,255,255,.08)';
      ctx.fillRect(sx + 6, sy + 8, Math.max(6, o.w - 12), 2);
    }
  }

  function drawBase(base, view, time) {
    if (!base) return;
    const sx = base.x - view.x;
    const sy = base.y - view.y;
    const r = base.radius || 54;
    if (sx < -140 || sx > width + 140 || sy < -140 || sy > height + 140) return;
    const pct = base.maxHp ? Math.max(0, Math.min(1, (base.hp || 0) / base.maxHp)) : 1;
    const pulse = 1 + Math.sin(time * 0.004) * 0.025;
    ctx.beginPath();
    ctx.arc(sx, sy, (r + 28) * pulse, 0, Math.PI * 2);
    ctx.fillStyle = base.down ? 'rgba(255,80,80,.12)' : 'rgba(72,240,160,.10)';
    ctx.fill();
    ctx.strokeStyle = base.down ? 'rgba(255,90,90,.68)' : 'rgba(72,240,160,.52)';
    ctx.lineWidth = 3;
    ctx.stroke();
    ctx.save();
    ctx.translate(sx, sy);
    ctx.rotate(Math.PI / 4);
    ctx.fillStyle = base.down ? '#3a2528' : '#25383a';
    ctx.strokeStyle = base.down ? '#ff6666' : '#8fffd0';
    ctx.lineWidth = 3;
    ctx.fillRect(-r * 0.72, -r * 0.72, r * 1.44, r * 1.44);
    ctx.strokeRect(-r * 0.72, -r * 0.72, r * 1.44, r * 1.44);
    ctx.restore();
    ctx.fillStyle = '#dffaf0';
    ctx.font = 'bold 12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(base.down ? '重启中' : '避难所', sx, sy + 4);
    const w = r * 2.2;
    ctx.fillStyle = 'rgba(0,0,0,.55)';
    ctx.fillRect(sx - w / 2, sy - r - 28, w, 6);
    ctx.fillStyle = pct < 0.35 ? '#ff6666' : pct < 0.65 ? '#ffc247' : '#48f0a0';
    ctx.fillRect(sx - w / 2, sy - r - 28, w * pct, 6);
  }

  function drawMission(mission, view, time) {
    if (!mission || mission.done || !mission.visible) return;
    const sx = mission.x - view.x;
    const sy = mission.y - view.y;
    const r = mission.radius || 88;
    if (sx < -150 || sx > width + 150 || sy < -150 || sy > height + 150) return;
    const charge = Math.max(0, Math.min(1, mission.charge || 0));
    const color = mission.ready ? '#48f0a0' : mission.color || '#ff4d5f';
    const pulse = 1 + Math.sin(time * 0.006) * 0.035;
    ctx.beginPath();
    ctx.arc(sx, sy, r * pulse, 0, Math.PI * 2);
    ctx.fillStyle = mission.ready ? 'rgba(72,240,160,.10)' : 'rgba(255,77,95,.10)';
    ctx.fill();
    ctx.strokeStyle = hexrgba(color, 0.68);
    ctx.lineWidth = 2;
    ctx.setLineDash([10, 8]);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.arc(sx, sy, r - 8, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * charge);
    ctx.strokeStyle = color;
    ctx.lineWidth = 5;
    ctx.stroke();
    ctx.fillStyle = mission.ready ? '#dcfff1' : '#ffdce1';
    ctx.font = 'bold 12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(mission.name || '撤离点', sx, sy + 4);
  }

  function drawExits(exits, mission, view, time) {
    const list = exits && exits.length ? exits : (mission ? [mission] : []);
    for (const exit of list) drawMission(exit, view, time);
  }

  function drawItems(items, view, time) {
    const { x: cx, y: cy } = view;
    for (const item of Object.values(items)) {
      const sx = item.x - cx;
      const sy = item.y - cy;
      if (sx < -45 || sx > width + 45 || sy < -45 || sy > height + 45) continue;
      const pulse = 1 + Math.sin(time * 0.004) * 0.08;
      ctx.beginPath();
      ctx.arc(sx, sy, (item.radius + 9) * pulse, 0, Math.PI * 2);
      ctx.fillStyle = hexrgba(item.color, 0.16);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(sx, sy, item.radius, 0, Math.PI * 2);
      ctx.fillStyle = item.color;
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,.88)';
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.fillStyle = '#111';
      ctx.font = 'bold 12px Arial';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(item.icon, sx, sy);
    }
  }

  function drawBullets(bullets, view) {
    const { x: cx, y: cy } = view;
    ctx.lineCap = 'round';
    for (const bullet of Object.values(bullets)) {
      const sx = bullet.x - cx;
      const sy = bullet.y - cy;
      if (sx < -70 || sx > width + 70 || sy < -70 || sy > height + 70) continue;
      const len = Math.min(34, Math.hypot(bullet.vx, bullet.vy) * 0.035);
      const angle = Math.atan2(bullet.vy, bullet.vx);
      ctx.strokeStyle = hexrgba(bullet.color, 0.3);
      ctx.lineWidth = 7;
      ctx.beginPath();
      ctx.moveTo(sx - Math.cos(angle) * len, sy - Math.sin(angle) * len);
      ctx.lineTo(sx, sy);
      ctx.stroke();
      ctx.strokeStyle = '#fff6bd';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(sx - Math.cos(angle) * len * 0.55, sy - Math.sin(angle) * len * 0.55);
      ctx.lineTo(sx, sy);
      ctx.stroke();
    }
  }

  function drawZombies(zombies, view, time) {
    const { x: cx, y: cy } = view;
    const sorted = Object.values(zombies).sort((a, b) => a.y - b.y);
    for (const z of sorted) {
      const sx = z.x - cx;
      const sy = z.y - cy;
      const r = z.radius || 16;
      if (sx < -70 || sx > width + 70 || sy < -70 || sy > height + 70) continue;
      const sprite = sprites[z.type] || sprites.walker;
      const angle = Math.atan2(z.vy || 1, z.vx || 0) + Math.PI / 2 + Math.sin(time * 0.006 + z.x) * 0.04;
      ctx.save();
      ctx.translate(sx, sy);
      ctx.rotate(angle);
      const scale = (r * 2.35) / 96;
      ctx.scale(scale, scale);
      ctx.drawImage(sprite, -48, -48);
      ctx.restore();
      if (z.hp < z.maxHp) {
        const w = r * 2.2;
        ctx.fillStyle = 'rgba(0,0,0,.55)';
        ctx.fillRect(sx - w / 2, sy - r - 15, w, 4);
        ctx.fillStyle = '#ff5b61';
        ctx.fillRect(sx - w / 2, sy - r - 15, w * Math.max(0, z.hp / z.maxHp), 4);
      }
    }
  }

  function drawPlayerBody(p, sx, sy, isMe, time) {
    const color = p.color || '#4da3ff';
    const angle = p.aim || 0;
    ctx.beginPath();
    ctx.ellipse(sx + 3, sy + 5, 19, 10, 0, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(0,0,0,.24)';
    ctx.fill();
    if (p.prot) {
      ctx.beginPath();
      ctx.arc(sx, sy, 31 + Math.sin(time * 0.006) * 2, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(255,255,255,.55)';
      ctx.lineWidth = 2;
      ctx.stroke();
    }
    ctx.save();
    ctx.translate(sx, sy);
    ctx.rotate(angle);
    ctx.strokeStyle = '#d9e7f2';
    ctx.lineWidth = 6;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(8, 1);
    ctx.lineTo(28, 1);
    ctx.stroke();
    ctx.strokeStyle = '#26313b';
    ctx.lineWidth = 9;
    ctx.beginPath();
    ctx.moveTo(2, 0);
    ctx.lineTo(18, 0);
    ctx.stroke();
    ctx.restore();
    ctx.beginPath();
    ctx.arc(sx, sy, isMe ? 18 : 16, 0, Math.PI * 2);
    ctx.fillStyle = p.dead ? hexrgba(color, 0.28) : color;
    ctx.fill();
    ctx.strokeStyle = isMe ? '#fff' : 'rgba(255,255,255,.62)';
    ctx.lineWidth = isMe ? 3 : 2;
    ctx.stroke();
    const hpPct = Math.max(0, Math.min(1, (p.hp || 0) / 100));
    ctx.strokeStyle = hpPct > 0.45 ? '#48f0a0' : '#ff5b61';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(sx, sy, 24, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * hpPct);
    ctx.stroke();
    ctx.fillStyle = '#edf7ff';
    ctx.font = 'bold 12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(p.name || '幸存者', sx, sy - 31);
  }

  function drawPlayers(players, me, myId, visualMe, view, time) {
    const { x: cx, y: cy } = view;
    const sorted = Object.entries(players).sort((a, b) => a[1].y - b[1].y);
    for (const [pid, p] of sorted) {
      const px = pid === myId ? visualMe.x : p.x;
      const py = pid === myId ? visualMe.y : p.y;
      const sx = px - cx;
      const sy = py - cy;
      if (sx < -80 || sx > width + 80 || sy < -80 || sy > height + 80) continue;
      drawPlayerBody(pid === myId ? Object.assign({}, p, me) : p, sx, sy, pid === myId, time);
    }
  }

  function drawEffects(effects, view) {
    const { x: cx, y: cy } = view;
    for (const d of effects.decals) {
      const sx = d.x - cx;
      const sy = d.y - cy;
      if (sx < -70 || sx > width + 70 || sy < -70 || sy > height + 70) continue;
      ctx.save();
      ctx.translate(sx, sy);
      ctx.rotate(d.rot);
      ctx.beginPath();
      ctx.ellipse(0, 0, d.r * 1.45, d.r, 0, 0, Math.PI * 2);
      ctx.fillStyle = d.color;
      ctx.fill();
      ctx.restore();
    }
    for (const r of effects.rings) {
      const sx = r.x - cx;
      const sy = r.y - cy;
      const a = Math.max(0, r.life / r.maxLife);
      ctx.globalAlpha = a;
      ctx.beginPath();
      ctx.arc(sx, sy, r.radius * (1.1 - a * 0.1), 0, Math.PI * 2);
      ctx.strokeStyle = r.color;
      ctx.lineWidth = r.width;
      ctx.stroke();
      ctx.globalAlpha = 1;
    }
    for (const p of effects.particles) {
      const sx = p.x - cx;
      const sy = p.y - cy;
      const a = Math.max(0, p.life / p.maxLife);
      ctx.globalAlpha = a;
      if (p.line) {
        ctx.strokeStyle = p.color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(sx, sy);
        ctx.lineTo(sx + p.dx, sy + p.dy);
        ctx.stroke();
      } else {
        ctx.beginPath();
        ctx.arc(sx, sy, p.size * a, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    }
  }

  function drawHorrorOverlay(time) {
    const flicker = 0.03 + Math.sin(time * 0.019) * 0.012;
    const grad = ctx.createRadialGradient(width / 2, height / 2, Math.min(width, height) * 0.18, width / 2, height / 2, Math.max(width, height) * 0.72);
    grad.addColorStop(0, 'rgba(0,0,0,0)');
    grad.addColorStop(0.72, `rgba(0,0,0,${0.28 + flicker})`);
    grad.addColorStop(1, `rgba(0,0,0,${0.72 + flicker})`);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);
  }

  function drawMinimap(state, me, myId, view, mapW, mapH) {
    const mw = minimap.width;
    const mh = minimap.height;
    const sx = mw / mapW;
    const sy = mh / mapH;
    mini.fillStyle = '#11161d';
    mini.fillRect(0, 0, mw, mh);
    const exits = state.exits && state.exits.length ? state.exits : (state.mission ? [state.mission] : []);
    for (const exit of exits) {
      if (!exit.visible || exit.done) continue;
      mini.strokeStyle = exit.ready ? '#48f0a0' : (exit.color || '#ff4d5f');
      mini.beginPath();
      mini.arc(exit.x * sx, exit.y * sy, 4, 0, Math.PI * 2);
      mini.stroke();
    }
    for (const z of Object.values(state.z)) {
      mini.fillStyle = z.color || '#6bd36b';
      mini.fillRect(z.x * sx - 1, z.y * sy - 1, 2, 2);
    }
    for (const item of Object.values(state.items)) {
      mini.fillStyle = item.color;
      mini.fillRect(item.x * sx - 1, item.y * sy - 1, 2, 2);
    }
    for (const p of Object.values(state.pl)) {
      mini.fillStyle = p.dead ? hexrgba(p.color, 0.3) : p.color;
      mini.beginPath();
      mini.arc(p.x * sx, p.y * sy, p.id === myId ? 4 : 3, 0, Math.PI * 2);
      mini.fill();
    }
    mini.strokeStyle = 'rgba(255,255,255,.25)';
    mini.strokeRect(view.x * sx, view.y * sy, width * sx, height * sy);
  }

  function draw(state, me, myId, visualMe, view, effects, time, joined) {
    clear();
    if (!joined) {
      ctx.fillStyle = '#44ffaa';
      ctx.font = 'bold 42px Arial';
      ctx.textAlign = 'center';
      ctx.fillText('僵尸危机', width / 2, height / 2 - 22);
      ctx.fillStyle = '#aeb7c2';
      ctx.font = '18px Arial';
      ctx.fillText('点击「加入游戏」开始防线', width / 2, height / 2 + 22);
      return;
    }
    drawGround(view, state.mw, state.mh);
    drawObstacles(state.obs, view);
    drawExits(state.exits, state.mission, view, time);
    drawEffects({ decals: effects.decals, rings: [], particles: [] }, view);
    drawItems(state.items, view, time);
    drawBullets(state.b, view);
    drawZombies(state.z, view, time);
    drawEffects({ decals: [], rings: effects.rings, particles: effects.particles }, view);
    drawPlayers(state.pl, me, myId, visualMe, view, time);
    drawHorrorOverlay(time);
    drawMinimap(state, me, myId, view, state.mw, state.mh);
  }

  resize();
  window.addEventListener('resize', resize, { passive: true });

  return {
    draw,
    resize,
    size: () => ({ width, height, dpr }),
  };
}
