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

const WEAPON_VISUALS = Object.freeze({
  pistol: { muzzle: 34, barrel: 34, core: 20, width: 5 },
  rifle: { muzzle: 44, barrel: 44, core: 26, width: 5 },
  shotgun: { muzzle: 35, barrel: 35, core: 20, width: 7 },
  smg: { muzzle: 32, barrel: 32, core: 20, width: 5 },
  launcher: { muzzle: 44, barrel: 44, core: 20, width: 9 },
});

function weaponVisual(weapon) {
  return WEAPON_VISUALS[weapon] || WEAPON_VISUALS.pistol;
}

function makeZombieSprite(type, color) {
  const isBoss = type === 'boss';
  const isCrawler = type === 'crawler';
  const isArmored = type === 'armored';
  const isLeaper = type === 'leaper';
  const isScreamer = type === 'screamer';
  const isBloater = type === 'bloater';
  const isShade = type === 'shade';
  const isStalker = type === 'stalker';
  const isSpitter = type === 'spitter';
  const isWarden = type === 'warden';
  const canvas = makeCanvas(96, 96);
  const ctx = canvas.getContext('2d');
  ctx.translate(48, 48);
  ctx.shadowColor = hexrgba(color, 0.65);
  ctx.shadowBlur =
    isBoss || isWarden
      ? 24
      : type === 'toxic' || isScreamer || isShade || isSpitter
        ? 18
        : isBloater || isStalker
          ? 15
          : 8;
  ctx.fillStyle = 'rgba(0,0,0,.34)';
  ctx.beginPath();
  ctx.ellipse(
    0,
    isCrawler ? 28 : 24,
    isBoss ? 32 : isCrawler ? 22 : 25,
    isBoss ? 14 : isCrawler ? 8 : 11,
    0,
    0,
    Math.PI * 2,
  );
  ctx.fill();
  ctx.rotate(isLeaper ? -0.28 : -0.12);
  ctx.lineCap = 'round';
  ctx.strokeStyle = isBoss ? '#3c1724' : isWarden ? '#2b223f' : isArmored ? '#3a4048' : isShade ? '#253839' : '#283322';
  ctx.lineWidth = isBoss || isWarden ? 11 : isCrawler ? 6 : 8;
  ctx.beginPath();
  ctx.moveTo(-16, isCrawler ? 6 : -3);
  ctx.lineTo(isBoss ? -40 : isCrawler ? -35 : -34, isBoss ? 14 : isCrawler ? 22 : 10);
  ctx.moveTo(17, isCrawler ? 7 : -1);
  ctx.lineTo(isBoss ? 40 : isCrawler ? 36 : 34, isBoss ? 15 : isCrawler ? 20 : 11);
  ctx.stroke();
  ctx.fillStyle = isBoss
    ? '#431b2a'
    : isWarden
      ? '#44345e'
      : type === 'brute'
        ? '#5b4837'
        : isArmored
          ? '#5f6975'
          : isBloater
            ? '#6b4b32'
            : isShade
              ? 'rgba(214,236,235,.72)'
              : isStalker
                ? 'rgba(207,210,255,.72)'
                : isSpitter
                  ? '#3f6840'
                  : color;
  ctx.beginPath();
  ctx.ellipse(
    0,
    isCrawler ? 12 : 5,
    isBoss ? 27 : isWarden ? 24 : type === 'brute' || isArmored ? 21 : isBloater ? 24 : isCrawler ? 20 : 17,
    isBoss
      ? 30
      : isWarden
        ? 29
        : isCrawler
          ? 15
          : type === 'runner' || isLeaper || isStalker
            ? 21
            : isBloater
              ? 27
              : 25,
    0,
    0,
    Math.PI * 2,
  );
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
  } else if (isSpitter) {
    ctx.fillStyle = hexrgba(color, 0.72);
    ctx.beginPath();
    ctx.arc(0, 2, 6, 0, Math.PI * 2);
    ctx.arc(9, -7, 4, 0, Math.PI * 2);
    ctx.fill();
  } else if (isBoss || isWarden) {
    ctx.strokeStyle = hexrgba(color, 0.9);
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(-20, -12);
    ctx.lineTo(-8, 3);
    ctx.lineTo(8, -5);
    ctx.lineTo(22, 10);
    ctx.stroke();
  }
  ctx.fillStyle = isScreamer ? '#332242' : isWarden ? '#251d34' : isShade ? '#d6eceb' : '#2b3a2b';
  ctx.beginPath();
  ctx.ellipse(
    0,
    isCrawler ? -9 : -22,
    isBoss ? 19 : isWarden ? 17 : type === 'brute' || isArmored ? 16 : isScreamer ? 15 : 13,
    isBoss ? 17 : isCrawler ? 10 : type === 'runner' || isLeaper || isStalker ? 12 : 14,
    0,
    0,
    Math.PI * 2,
  );
  ctx.fill();
  if (isScreamer) {
    ctx.strokeStyle = hexrgba(color, 0.9);
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(0, -22, 23, -0.55, 0.55);
    ctx.stroke();
  }
  ctx.fillStyle = isBoss
    ? '#ffd6df'
    : isWarden
      ? '#efe1ff'
      : type === 'toxic'
        ? '#e7ff8c'
        : isLeaper
          ? '#ffe0a3'
          : isScreamer
            ? '#f0d0ff'
            : isShade
              ? '#11161d'
              : '#fff1a6';
  ctx.beginPath();
  ctx.arc(-5, isCrawler ? -10 : -24, isBoss || isWarden ? 3.2 : 2.3, 0, Math.PI * 2);
  ctx.arc(6, isCrawler ? -10 : -24, isBoss || isWarden ? 3.2 : 2.3, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = 'rgba(80,0,10,.62)';
  ctx.lineWidth = isBoss ? 3 : 2;
  ctx.beginPath();
  ctx.moveTo(-7, isCrawler ? -2 : -15);
  ctx.lineTo(8, isCrawler ? 2 : -12);
  ctx.stroke();
  ctx.strokeStyle = 'rgba(210,32,48,.58)';
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(isCrawler ? -12 : -14, isCrawler ? 8 : 3);
  ctx.lineTo(isCrawler ? -2 : -5, isCrawler ? 18 : 18);
  ctx.moveTo(isBoss ? 14 : 10, isCrawler ? 7 : 2);
  ctx.lineTo(isBoss ? 24 : 16, isCrawler ? 18 : 16);
  ctx.stroke();
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
    walker: makeZombieSprite('walker', '#b8b09d'),
    runner: makeZombieSprite('runner', '#d0b38d'),
    crawler: makeZombieSprite('crawler', '#7b8b8e'),
    shade: makeZombieSprite('shade', '#d6eceb'),
    brute: makeZombieSprite('brute', '#8a5b4a'),
    toxic: makeZombieSprite('toxic', '#9db64b'),
    armored: makeZombieSprite('armored', '#8f98a3'),
    leaper: makeZombieSprite('leaper', '#c88b61'),
    screamer: makeZombieSprite('screamer', '#b68abf'),
    bloater: makeZombieSprite('bloater', '#b8694a'),
    stalker: makeZombieSprite('stalker', '#cfd2ff'),
    spitter: makeZombieSprite('spitter', '#7fdc71'),
    warden: makeZombieSprite('warden', '#b7a0ff'),
    boss: makeZombieSprite('boss', '#d9445f'),
  };
  const groundMarks = Array.from({ length: 170 }, (_, i) => ({
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
    grad.addColorStop(0, '#20262d');
    grad.addColorStop(0.55, '#172430');
    grad.addColorStop(1, '#251d21');
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
      const kind = o.kind || 'wall';
      ctx.fillStyle = 'rgba(0,0,0,.28)';
      ctx.fillRect(sx + 5, sy + 6, o.w, o.h);
      ctx.fillStyle =
        {
          wall: '#323a42',
          crate: '#4b3f35',
          gurney: '#596572',
          generator: '#2f4546',
          tank: '#4b555e',
          locker: '#394955',
        }[kind] || '#323a42';
      ctx.fillRect(sx, sy, o.w, o.h);
      ctx.fillStyle = kind === 'wall' ? '#4d5a66' : 'rgba(255,255,255,.14)';
      ctx.fillRect(sx, sy, o.w, 5);
      ctx.fillStyle = 'rgba(255,255,255,.08)';
      ctx.fillRect(sx + 6, sy + 8, Math.max(6, o.w - 12), 2);
      if (kind === 'generator') {
        ctx.fillStyle = 'rgba(72,240,160,.45)';
        ctx.fillRect(sx + o.w - 16, sy + 10, 7, Math.max(8, o.h - 20));
      } else if (kind === 'tank') {
        ctx.strokeStyle = 'rgba(180,210,220,.32)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.ellipse(sx + o.w / 2, sy + o.h / 2, o.w * 0.42, o.h * 0.42, 0, 0, Math.PI * 2);
        ctx.stroke();
      }
    }
  }

  function drawFeatures(features, view, time) {
    const { x: cx, y: cy } = view;
    for (const f of features || []) {
      const sx = f.x - cx;
      const sy = f.y - cy;
      const w = f.w || 44;
      const h = f.h || 28;
      if (sx + w < -80 || sx > width + 80 || sy + h < -80 || sy > height + 80) continue;
      if (f.kind === 'room') {
        const effect = f.effect || '';
        const tint =
          {
            medbay: '72,240,160',
            generator: '102,217,255',
            lab: '183,255,71',
            armory: '255,194,71',
            archive: '174,230,255',
            security: '217,140,255',
            morgue: '183,255,71',
          }[effect] || '220,231,241';
        ctx.fillStyle = `rgba(${tint},.045)`;
        ctx.fillRect(sx, sy, w, h);
        ctx.strokeStyle = `rgba(${tint},.18)`;
        ctx.strokeRect(sx, sy, w, h);
        ctx.fillStyle = `rgba(${tint},.12)`;
        if (effect === 'medbay') {
          for (let i = 0; i < 2; i += 1) {
            ctx.fillRect(sx + 22 + i * 78, sy + h * 0.42, 48, 18);
            ctx.fillStyle = 'rgba(240,248,255,.18)';
            ctx.fillRect(sx + 26 + i * 78, sy + h * 0.42 - 8, 18, 8);
            ctx.fillStyle = `rgba(${tint},.12)`;
          }
        } else if (effect === 'generator') {
          ctx.fillRect(sx + w * 0.5 - 28, sy + h * 0.38, 56, 44);
          ctx.fillStyle = `rgba(${tint},${f.active === false ? 0.18 : 0.42})`;
          ctx.fillRect(sx + w * 0.5 + 18, sy + h * 0.38 + 8, 8, 28);
        } else if (effect === 'lab') {
          for (let i = 0; i < 4; i += 1) {
            ctx.strokeStyle = `rgba(${tint},.28)`;
            ctx.strokeRect(sx + 22 + i * 42, sy + h * 0.38, 18, 42);
            ctx.fillStyle = `rgba(${tint},.16)`;
            ctx.fillRect(sx + 26 + i * 42, sy + h * 0.52, 10, 20);
          }
        } else if (effect === 'armory' || effect === 'security' || effect === 'archive') {
          for (let i = 0; i < 3; i += 1) {
            ctx.fillRect(sx + 22 + i * 48, sy + h * 0.46, 34, 24);
            ctx.strokeStyle = 'rgba(20,16,8,.45)';
            ctx.strokeRect(sx + 22 + i * 48, sy + h * 0.46, 34, 24);
          }
        } else if (effect === 'morgue') {
          for (let i = 0; i < 3; i += 1) {
            ctx.fillRect(sx + 18 + i * 54, sy + h * 0.42, 42, 16);
            ctx.fillRect(sx + 22 + i * 54, sy + h * 0.42 + 20, 34, 10);
          }
        }
        if (f.label) {
          ctx.fillStyle = `rgba(${tint},.55)`;
          ctx.font = 'bold 12px Arial';
          ctx.textAlign = 'left';
          ctx.fillText(f.label, sx + 10, sy + 18);
        }
      } else if (f.kind === 'blood') {
        ctx.beginPath();
        ctx.ellipse(sx, sy, w * 0.52, h * 0.48, (f.x + f.y) * 0.01, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(120,8,20,.42)';
        ctx.fill();
      } else if (f.kind === 'door') {
        const color = f.color || '#aee6ff';
        ctx.fillStyle = hexrgba(color, 0.16);
        ctx.fillRect(sx, sy, w, h);
        ctx.strokeStyle = hexrgba(color, 0.72);
        ctx.lineWidth = 2;
        ctx.strokeRect(sx + 1, sy + 1, w - 2, h - 2);
        ctx.fillStyle = hexrgba(color, 0.78);
        ctx.font = 'bold 12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(f.label || '出口', sx + w / 2, sy + h / 2 + 4);
      } else if (f.kind === 'pool') {
        ctx.beginPath();
        ctx.ellipse(sx, sy, w * 0.5, h * 0.48, 0.3, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(100,142,68,.18)';
        ctx.fill();
        ctx.strokeStyle = 'rgba(157,182,75,.16)';
        ctx.stroke();
      } else if (f.kind === 'light') {
        const blink = 0.15 + Math.max(0, Math.sin(time * 0.008 + f.x)) * 0.18;
        const grad = ctx.createRadialGradient(sx, sy, 4, sx, sy, Math.max(w, h));
        grad.addColorStop(0, `rgba(255,77,95,${blink})`);
        grad.addColorStop(1, 'rgba(255,77,95,0)');
        ctx.fillStyle = grad;
        ctx.fillRect(sx - w, sy - h, w * 2, h * 2);
      } else if (f.kind === 'warning') {
        ctx.strokeStyle = 'rgba(255,194,71,.22)';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(sx - w / 2, sy);
        ctx.lineTo(sx + w / 2, sy);
        ctx.stroke();
      }
    }
  }

  function drawMission(mission, view, time, index = 0) {
    if (!mission || mission.done || !mission.visible) return;
    const sx = mission.x - view.x;
    const sy = mission.y - view.y;
    const r = mission.radius || 88;
    if (sx < -150 || sx > width + 150 || sy < -150 || sy > height + 150) return;
    const charge = Math.max(0, Math.min(1, mission.charge || 0));
    const color = mission.ready ? '#48f0a0' : mission.color || '#ff4d5f';
    const marker = String(index + 1);
    const reward = mission.shortReward || mission.rewardTitle || '';
    const pulse = 1 + Math.sin(time * 0.006) * 0.035;
    ctx.beginPath();
    ctx.arc(sx, sy, r * pulse, 0, Math.PI * 2);
    ctx.fillStyle = mission.ready ? 'rgba(72,240,160,.08)' : 'rgba(255,77,95,.075)';
    ctx.fill();
    ctx.strokeStyle = hexrgba(color, 0.48);
    ctx.lineWidth = 2;
    ctx.setLineDash([14, 10]);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.arc(sx, sy, r - 8, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * charge);
    ctx.strokeStyle = color;
    ctx.lineWidth = 5;
    ctx.stroke();
    ctx.save();
    ctx.translate(sx, sy);
    ctx.fillStyle = 'rgba(0,0,0,.44)';
    ctx.fillRect(-34, -29, 68, 58);
    ctx.fillStyle = mission.ready ? '#203c32' : '#3a2228';
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.fillRect(-28, -34, 56, 68);
    ctx.strokeRect(-28, -34, 56, 68);
    ctx.fillStyle = '#11161d';
    ctx.fillRect(-19, -23, 38, 46);
    ctx.fillStyle = mission.ready ? '#48f0a0' : '#ff4d5f';
    ctx.fillRect(-14, -18, 28, 6);
    ctx.fillRect(-14, -6, 28 * Math.max(0.16, charge), 5);
    ctx.fillRect(-14, 7, 19, 5);
    ctx.beginPath();
    ctx.arc(-25, -35, 15, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,.9)';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = '#07110c';
    ctx.font = '900 16px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(marker, -25, -35);
    ctx.strokeStyle = 'rgba(255,255,255,.22)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(-42, 32);
    ctx.lineTo(-24, 18);
    ctx.moveTo(42, 32);
    ctx.lineTo(24, 18);
    ctx.stroke();
    ctx.restore();
    ctx.fillStyle = mission.ready ? '#dcfff1' : '#ffdce1';
    ctx.font = 'bold 13px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const title = `${marker}. ${mission.name || '撤离点'}`;
    const titleWidth = Math.min(170, Math.max(84, ctx.measureText(title).width + 18));
    ctx.fillStyle = 'rgba(2,4,7,.68)';
    ctx.strokeStyle = hexrgba(color, 0.45);
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(sx - titleWidth / 2, sy + r + 8, titleWidth, 24, 6);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = mission.ready ? '#dcfff1' : '#ffdce1';
    ctx.fillText(title, sx, sy + r + 20);
    if (reward) {
      const rewardText = `奖励:${reward}`;
      const rewardWidth = Math.min(150, Math.max(64, ctx.measureText(rewardText).width + 16));
      ctx.fillStyle = hexrgba(color, mission.ready ? 0.2 : 0.16);
      ctx.strokeStyle = hexrgba(color, 0.38);
      ctx.beginPath();
      ctx.roundRect(sx - rewardWidth / 2, sy + r + 36, rewardWidth, 21, 6);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#edf7ff';
      ctx.font = 'bold 12px Arial';
      ctx.fillText(rewardText, sx, sy + r + 46);
    }
  }

  function drawExits(exits, mission, view, time) {
    const list = exits && exits.length ? exits : mission ? [mission] : [];
    for (let i = 0; i < list.length; i += 1) drawMission(list[i], view, time, i);
  }

  function drawItems(items, view, time) {
    const { x: cx, y: cy } = view;
    for (const item of Object.values(items)) {
      const sx = item.x - cx;
      const sy = item.y - cy;
      if (sx < -45 || sx > width + 45 || sy < -45 || sy > height + 45) continue;
      const pulse = 1 + Math.sin(time * 0.004) * 0.08;
      ctx.save();
      ctx.translate(sx, sy);
      ctx.shadowColor = hexrgba(item.color, 0.55);
      ctx.shadowBlur = 12;
      ctx.fillStyle = hexrgba(item.color, 0.14);
      ctx.beginPath();
      ctx.roundRect(
        -(item.radius + 12) * pulse,
        -(item.radius + 8) * pulse,
        (item.radius + 12) * 2 * pulse,
        (item.radius + 8) * 2 * pulse,
        6,
      );
      ctx.fill();
      ctx.shadowBlur = 0;
      if (item.type === 'fuse') {
        ctx.fillStyle = '#202833';
        ctx.strokeStyle = item.color;
        ctx.lineWidth = 3;
        ctx.fillRect(-17, -7, 34, 14);
        ctx.strokeRect(-17, -7, 34, 14);
        ctx.strokeStyle = '#dce7f1';
        ctx.beginPath();
        ctx.moveTo(-22, 0);
        ctx.lineTo(-17, 0);
        ctx.moveTo(17, 0);
        ctx.lineTo(22, 0);
        ctx.stroke();
      } else if (item.type === 'sample') {
        ctx.fillStyle = '#151b22';
        ctx.strokeStyle = '#dce7f1';
        ctx.lineWidth = 2;
        ctx.fillRect(-8, -18, 16, 34);
        ctx.strokeRect(-8, -18, 16, 34);
        ctx.fillStyle = item.color;
        ctx.fillRect(-5, -2, 10, 15);
      } else if (item.type === 'keycard') {
        ctx.fillStyle = item.color;
        ctx.beginPath();
        ctx.roundRect(-18, -12, 36, 24, 4);
        ctx.fill();
        ctx.fillStyle = '#151b22';
        ctx.fillRect(-12, -5, 14, 4);
        ctx.fillRect(-12, 4, 24, 3);
      } else if ((item.type || '').startsWith('weapon_')) {
        ctx.fillStyle = '#202833';
        ctx.strokeStyle = item.color;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.roundRect(-24, -15, 48, 30, 5);
        ctx.fill();
        ctx.stroke();
        ctx.strokeStyle = '#edf7ff';
        ctx.lineWidth = 4;
        ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.moveTo(-13, 2);
        ctx.lineTo(12, -3);
        ctx.moveTo(9, -3);
        ctx.lineTo(18, -2);
        ctx.stroke();
      } else if (item.type === 'vehicle') {
        ctx.fillStyle = '#2d2b24';
        ctx.strokeStyle = item.color;
        ctx.lineWidth = 3;
        ctx.fillRect(-22, -12, 44, 20);
        ctx.strokeRect(-22, -12, 44, 20);
        ctx.strokeStyle = '#edf7ff';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(-18, -15);
        ctx.lineTo(18, -15);
        ctx.stroke();
        ctx.fillStyle = '#11161d';
        ctx.beginPath();
        ctx.arc(-13, 12, 5, 0, Math.PI * 2);
        ctx.arc(13, 12, 5, 0, Math.PI * 2);
        ctx.fill();
      } else {
        ctx.beginPath();
        ctx.arc(0, 0, item.radius, 0, Math.PI * 2);
        ctx.fillStyle = item.color;
        ctx.fill();
        ctx.strokeStyle = 'rgba(255,255,255,.88)';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
      ctx.fillStyle = item.type === 'sample' ? '#dce7f1' : '#111';
      ctx.font = 'bold 12px Arial';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      if (!['fuse', 'sample', 'keycard', 'vehicle'].includes(item.type) && !(item.type || '').startsWith('weapon_'))
        ctx.fillText(item.icon, 0, 0);
      ctx.restore();
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
      const prevX = Number.isFinite(bullet.prevX) ? bullet.prevX : bullet.x - Math.cos(angle) * len;
      const prevY = Number.isFinite(bullet.prevY) ? bullet.prevY : bullet.y - Math.sin(angle) * len;
      const prevDist = Math.hypot(bullet.x - prevX, bullet.y - prevY);
      const usePrevTail = prevDist > 1 && prevDist < 140;
      const tailX = usePrevTail ? prevX - cx : sx - Math.cos(angle) * len;
      const tailY = usePrevTail ? prevY - cy : sy - Math.sin(angle) * len;
      const explosive = (bullet.explosionRadius || 0) > 0 || bullet.weapon === 'launcher';
      ctx.strokeStyle = hexrgba(bullet.color, explosive ? 0.42 : 0.3);
      ctx.lineWidth = explosive ? 11 : 7;
      ctx.beginPath();
      ctx.moveTo(tailX, tailY);
      ctx.lineTo(sx, sy);
      ctx.stroke();
      ctx.strokeStyle = explosive ? '#ffd6a0' : '#fff6bd';
      ctx.lineWidth = explosive ? 4 : 2;
      ctx.beginPath();
      ctx.moveTo(
        usePrevTail ? tailX : sx - Math.cos(angle) * len * 0.55,
        usePrevTail ? tailY : sy - Math.sin(angle) * len * 0.55,
      );
      ctx.lineTo(sx, sy);
      ctx.stroke();
      if (explosive) {
        ctx.beginPath();
        ctx.arc(sx, sy, Math.max(5, bullet.radius || 5), 0, Math.PI * 2);
        ctx.fillStyle = bullet.color || '#ff8844';
        ctx.fill();
      }
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
    const weapon = p.weapon || 'pistol';
    const spec = weaponVisual(weapon);
    const weaponColor =
      {
        pistol: '#d9e7f2',
        rifle: '#8fd0ff',
        shotgun: '#ffc247',
        smg: '#48f0a0',
        launcher: '#ff8844',
      }[weapon] || '#d9e7f2';
    ctx.beginPath();
    ctx.ellipse(sx + 3, sy + 5, 19, 10, 0, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(0,0,0,.24)';
    ctx.fill();
    if (p.vehicle) {
      ctx.save();
      ctx.translate(sx, sy + 15);
      ctx.fillStyle = 'rgba(255,194,71,.16)';
      ctx.strokeStyle = 'rgba(255,194,71,.55)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.roundRect(-29, -11, 58, 24, 7);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#11161d';
      ctx.beginPath();
      ctx.arc(-18, 14, 4, 0, Math.PI * 2);
      ctx.arc(18, 14, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
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
    ctx.strokeStyle = weaponColor;
    ctx.lineWidth = spec.width;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(10, 0);
    ctx.lineTo(spec.barrel, 0);
    ctx.stroke();
    ctx.strokeStyle = '#26313b';
    ctx.lineWidth = weapon === 'launcher' ? 12 : 9;
    ctx.beginPath();
    ctx.moveTo(2, 0);
    ctx.lineTo(spec.core, 0);
    ctx.stroke();
    if (weapon === 'shotgun') {
      ctx.strokeStyle = '#1a2028';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(18, -4);
      ctx.lineTo(35, -4);
      ctx.moveTo(18, 4);
      ctx.lineTo(35, 4);
      ctx.stroke();
    } else if (weapon === 'launcher') {
      ctx.fillStyle = '#151b22';
      ctx.beginPath();
      ctx.ellipse(spec.muzzle - 8, 0, 8, 7, 0, 0, Math.PI * 2);
      ctx.fill();
    }
    if ((p.fireCd || 0) > 0 && !(p.reloadCd > 0)) {
      ctx.fillStyle = 'rgba(255,236,170,.86)';
      ctx.beginPath();
      ctx.ellipse(spec.muzzle, 0, weapon === 'launcher' ? 10 : 7, 3.4, 0, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
    ctx.beginPath();
    ctx.arc(sx, sy, isMe ? 18 : 16, 0, Math.PI * 2);
    ctx.fillStyle = p.dead ? hexrgba(color, 0.28) : color;
    ctx.fill();
    ctx.strokeStyle = isMe ? '#fff' : 'rgba(255,255,255,.62)';
    ctx.lineWidth = isMe ? 3 : 2;
    ctx.stroke();
    const hpPct = Math.max(0, Math.min(1, (p.hp || 0) / (p.maxHp || 100)));
    ctx.strokeStyle = hpPct > 0.45 ? '#48f0a0' : '#ff5b61';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(sx, sy, 24, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * hpPct);
    ctx.stroke();
    if ((p.reloadCd || 0) > 0) {
      ctx.strokeStyle = '#dce7f1';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(
        sx,
        sy,
        29,
        -Math.PI / 2,
        -Math.PI / 2 + Math.PI * 2 * Math.max(0.08, 1 - Math.min(1, p.reloadCd / 1.15)),
      );
      ctx.stroke();
    }
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
      if (p.slash) {
        const radius = p.radius || 72;
        const arc = p.arc || 1.25;
        const angle = p.angle || 0;
        const sweep = arc * (1.05 - a * 0.15);
        ctx.save();
        ctx.translate(sx, sy);
        ctx.rotate(angle);
        ctx.lineCap = 'round';
        ctx.shadowColor = p.color;
        ctx.shadowBlur = 16;
        ctx.strokeStyle = 'rgba(245,250,255,.92)';
        ctx.lineWidth = (p.width || 10) * a;
        ctx.beginPath();
        ctx.arc(0, 0, radius, -sweep / 2, sweep / 2);
        ctx.stroke();
        ctx.shadowBlur = 0;
        ctx.strokeStyle = hexrgba(p.color, 0.72 * a);
        ctx.lineWidth = Math.max(2, (p.width || 10) * 0.35 * a);
        ctx.beginPath();
        ctx.arc(0, 0, radius - 8, -sweep / 2, sweep / 2);
        ctx.stroke();
        ctx.restore();
      } else if (p.line) {
        ctx.strokeStyle = p.color;
        ctx.lineWidth = p.size || 2;
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
    const flicker = 0.016 + Math.sin(time * 0.019) * 0.008;
    const grad = ctx.createRadialGradient(
      width / 2,
      height / 2,
      Math.min(width, height) * 0.18,
      width / 2,
      height / 2,
      Math.max(width, height) * 0.72,
    );
    grad.addColorStop(0, 'rgba(0,0,0,0)');
    grad.addColorStop(0.72, `rgba(0,0,0,${0.12 + flicker})`);
    grad.addColorStop(1, `rgba(0,0,0,${0.36 + flicker})`);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);
  }

  function lightSpot(x, y, radius, inner = 0.94) {
    const grad = ctx.createRadialGradient(x, y, Math.max(1, radius * 0.12), x, y, radius);
    grad.addColorStop(0, `rgba(0,0,0,${inner})`);
    grad.addColorStop(0.52, 'rgba(0,0,0,.62)');
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
  }

  function drawDarknessCloud(state, me, myId, visualMe, view, effects, time) {
    const powered = Boolean(state.obj?.powered);
    const fogFactor = state.fog?.until && state.fog.until > time ? 0.86 : 1;
    const baseRadius = (powered ? 820 : 680) * fogFactor;
    const playerCenter = {
      x: (visualMe.ready ? visualMe.x : me.x) - view.x,
      y: (visualMe.ready ? visualMe.y : me.y) - view.y,
    };
    ctx.save();
    ctx.fillStyle = powered ? 'rgba(0,0,0,.56)' : 'rgba(0,0,0,.72)';
    ctx.fillRect(0, 0, width, height);
    ctx.globalCompositeOperation = 'destination-out';
    lightSpot(playerCenter.x, playerCenter.y, baseRadius, powered ? 0.98 : 0.94);
    for (const [pid, p] of Object.entries(state.pl || {})) {
      if (pid === myId || p.dead) continue;
      lightSpot(p.x - view.x, p.y - view.y, powered ? 320 : 260, 0.78);
    }
    for (const exit of state.exits || []) {
      if (!exit.visible || exit.done) continue;
      lightSpot(exit.x - view.x, exit.y - view.y, exit.ready ? 250 : 185, 0.68);
    }
    for (const ring of effects.rings || []) {
      lightSpot(ring.x - view.x, ring.y - view.y, Math.min(280, 90 + ring.radius * 0.6), 0.62);
    }
    for (const bullet of Object.values(state.b || {})) {
      lightSpot(bullet.x - view.x, bullet.y - view.y, bullet.weapon === 'launcher' ? 140 : 82, 0.55);
    }
    ctx.globalCompositeOperation = 'source-over';
    const edge = ctx.createRadialGradient(
      playerCenter.x,
      playerCenter.y,
      baseRadius * 0.55,
      playerCenter.x,
      playerCenter.y,
      baseRadius * 1.25,
    );
    edge.addColorStop(0, 'rgba(0,0,0,0)');
    edge.addColorStop(1, powered ? 'rgba(0,0,0,.12)' : 'rgba(0,0,0,.2)');
    ctx.fillStyle = edge;
    ctx.fillRect(0, 0, width, height);
    for (let i = 0; i < 10; i += 1) {
      const y = ((time * (0.01 + i * 0.001) + i * 131) % (height + 180)) - 90;
      ctx.fillStyle = `rgba(0,0,0,${powered ? 0.018 : 0.026})`;
      ctx.fillRect(-100, y, width + 200, 22 + (i % 5) * 10);
    }
    ctx.restore();
  }

  function drawFogOverlay(fog, time) {
    if (!fog || !fog.until) return;
    const left = Math.max(0, fog.until - time);
    if (left <= 0) return;
    const duration = Math.max(1000, (fog.duration || 4.8) * 1000);
    const pct = Math.min(1, left / duration);
    const intro = Math.min(1, (duration - left) / 520);
    const fade = Math.min(1, pct / 0.28);
    const intensity = Math.min(1, intro, fade);
    const sweep = Math.sin(time * 0.012) * 0.06;
    const color = fog.color || '#d6eceb';
    const alert = fog.reason === 'extraction' || fog.reason === 'terminal';
    const pulse = alert ? Math.max(0, Math.sin(time * 0.028)) * 0.08 : 0;
    ctx.fillStyle = hexrgba(color, (0.16 + pulse) * intensity);
    ctx.fillRect(0, 0, width, height);
    const grad = ctx.createRadialGradient(
      width / 2,
      height / 2,
      Math.min(width, height) * 0.12,
      width / 2,
      height / 2,
      Math.max(width, height) * 0.78,
    );
    grad.addColorStop(0, hexrgba(color, 0.06 * intensity));
    grad.addColorStop(0.55, hexrgba(color, (0.24 + sweep + pulse) * intensity));
    grad.addColorStop(1, `rgba(8,10,12,${(0.78 + pulse) * intensity})`);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);
    for (let i = 0; i < 8; i += 1) {
      const y = ((time * (0.018 + i * 0.002) + i * 97) % (height + 160)) - 80;
      ctx.fillStyle = hexrgba(color, (0.034 + (i % 3) * 0.012 + pulse * 0.4) * intensity);
      ctx.fillRect(-80, y, width + 160, 18 + (i % 4) * 9);
    }
  }

  function drawMinimap(state, me, myId, view, mapW, mapH) {
    const mw = minimap.width;
    const mh = minimap.height;
    const sx = mw / mapW;
    const sy = mh / mapH;
    mini.fillStyle = '#11161d';
    mini.fillRect(0, 0, mw, mh);
    const exits = state.exits && state.exits.length ? state.exits : state.mission ? [state.mission] : [];
    for (let i = 0; i < exits.length; i += 1) {
      const exit = exits[i];
      if (!exit.visible || exit.done) continue;
      const color = exit.ready ? '#48f0a0' : exit.color || '#ff4d5f';
      const x = exit.x * sx;
      const y = exit.y * sy;
      mini.fillStyle = hexrgba(color, 0.28);
      mini.beginPath();
      mini.arc(x, y, 7, 0, Math.PI * 2);
      mini.fill();
      mini.strokeStyle = color;
      mini.lineWidth = 1.5;
      mini.beginPath();
      mini.arc(x, y, 7, 0, Math.PI * 2);
      mini.stroke();
      mini.fillStyle = '#edf7ff';
      mini.font = '900 9px Arial';
      mini.textAlign = 'center';
      mini.textBaseline = 'middle';
      mini.fillText(String(i + 1), x, y + 0.5);
    }
    const vision = state.obj?.powered ? 620 : 380;
    const px = me.x || 0;
    const py = me.y || 0;
    for (const z of Object.values(state.z)) {
      if ((z.x - px) ** 2 + (z.y - py) ** 2 > vision * vision) continue;
      mini.fillStyle = z.color || '#6bd36b';
      mini.fillRect(z.x * sx - 1, z.y * sy - 1, 2, 2);
    }
    for (const item of Object.values(state.items)) {
      if ((item.x - px) ** 2 + (item.y - py) ** 2 > vision * vision) continue;
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

  function draw(state, me, myId, visualMe, view, effects, time, joined, options = {}) {
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
    drawFeatures(state.features, view, time);
    drawObstacles(state.obs, view);
    drawExits(state.exits, state.mission, view, time);
    drawEffects({ decals: effects.decals, rings: [], particles: [] }, view);
    drawItems(state.items, view, time);
    drawBullets(state.b, view);
    drawZombies(state.z, view, time);
    drawEffects({ decals: [], rings: effects.rings, particles: effects.particles }, view);
    drawPlayers(state.pl, me, myId, visualMe, view, time);
    drawDarknessCloud(state, me, myId, visualMe, view, effects, time);
    drawFogOverlay(state.fog, time);
    drawHorrorOverlay(time);
    if (options.drawMinimap !== false) drawMinimap(state, me, myId, view, state.mw, state.mh);
  }

  resize();
  window.addEventListener('resize', resize, { passive: true });

  return {
    draw,
    resize,
    size: () => ({ width, height, dpr }),
  };
}
