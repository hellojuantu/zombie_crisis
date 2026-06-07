/* touch_controls.js – virtual joystick + fire zone for mobile landscape play */
(function () {
  'use strict';

  if (!('ontouchstart' in window) && navigator.maxTouchPoints < 1) return;

  var DEAD = 18;
  var MAX_R = 68;
  var activeKeys = {};
  var jTouchId = null;
  var jBaseX = 0, jBaseY = 0;
  var aimTouchId = null;
  var jThumb = null;
  var jBaseEl = null;

  /* ── key helpers ─────────────────────────────────────────────────────────── */
  function pressKey(key) {
    if (activeKeys[key]) return;
    activeKeys[key] = true;
    window.dispatchEvent(new KeyboardEvent('keydown', {
      key: key,
      code: key === ' ' ? 'Space' : 'Key' + key.toUpperCase(),
      bubbles: true, cancelable: true,
    }));
  }
  function releaseKey(key) {
    if (!activeKeys[key]) return;
    activeKeys[key] = false;
    window.dispatchEvent(new KeyboardEvent('keyup', {
      key: key,
      code: key === ' ' ? 'Space' : 'Key' + key.toUpperCase(),
      bubbles: true, cancelable: true,
    }));
  }
  function tapKey(key) {
    pressKey(key);
    setTimeout(function () { releaseKey(key); }, 80);
  }

  /* ── mouse helpers ───────────────────────────────────────────────────────── */
  function aimAt(cx, cy) {
    window.dispatchEvent(new MouseEvent('mousemove', { clientX: cx, clientY: cy, bubbles: true }));
  }
  function startFire(cx, cy) {
    aimAt(cx, cy);
    var canvas = document.getElementById('gameCanvas');
    var target = canvas || document.body;
    target.dispatchEvent(new MouseEvent('mousedown', {
      button: 0, buttons: 1, clientX: cx, clientY: cy,
      bubbles: true, cancelable: true,
    }));
  }
  function stopFire() {
    window.dispatchEvent(new MouseEvent('mouseup', { button: 0, bubbles: true, cancelable: true }));
  }

  /* ── joystick ────────────────────────────────────────────────────────────── */
  function updateJoystick(dx, dy) {
    var d = Math.hypot(dx, dy);
    var clampD = Math.min(d, MAX_R);
    if (jThumb) {
      var tx = d > 0 ? (dx / d) * clampD : 0;
      var ty = d > 0 ? (dy / d) * clampD : 0;
      jThumb.style.transform = 'translate(calc(-50% + ' + tx + 'px), calc(-50% + ' + ty + 'px))';
    }
    if (d < DEAD) {
      releaseKey('w'); releaseKey('s'); releaseKey('a'); releaseKey('d');
      return;
    }
    var nx = dx / d, ny = dy / d, t = 0.36;
    if (ny < -t) pressKey('w'); else releaseKey('w');
    if (ny > t)  pressKey('s'); else releaseKey('s');
    if (nx < -t) pressKey('a'); else releaseKey('a');
    if (nx > t)  pressKey('d'); else releaseKey('d');
  }

  /* ── DOM helpers ─────────────────────────────────────────────────────────── */
  function el(tag, styles) {
    var e = document.createElement(tag);
    if (styles) Object.assign(e.style, styles);
    return e;
  }

  function mkBtn(icon, label, styles) {
    var wrap = el('div', Object.assign({
      position: 'absolute',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', gap: '3px',
      userSelect: 'none', WebkitUserSelect: 'none',
      touchAction: 'none', cursor: 'pointer',
      pointerEvents: 'auto',
    }, styles || {}));

    var circle = el('div', {
      width: '52px', height: '52px',
      borderRadius: '50%',
      border: '1.5px solid rgba(255,255,255,0.22)',
      background: 'rgba(16,20,28,0.72)',
      backdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: '18px', fontWeight: '900',
      color: 'rgba(220,231,241,0.85)',
      boxShadow: '0 2px 8px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.07)',
      transition: 'background 0.08s, border-color 0.08s',
    });
    circle.textContent = icon;

    var lbl = el('div', {
      fontSize: '10px',
      color: 'rgba(158,168,180,0.8)',
      fontWeight: '600',
      letterSpacing: '0.5px',
      whiteSpace: 'nowrap',
    });
    lbl.textContent = label;

    wrap.appendChild(circle);
    wrap.appendChild(lbl);

    function press(e) {
      e.preventDefault(); e.stopPropagation();
      Object.assign(circle.style, {
        background: 'rgba(72,240,160,0.22)',
        borderColor: 'rgba(72,240,160,0.55)',
        color: '#48f0a0',
      });
    }
    function release(e) {
      if (e) { e.preventDefault(); e.stopPropagation(); }
      Object.assign(circle.style, {
        background: 'rgba(16,20,28,0.72)',
        borderColor: 'rgba(255,255,255,0.22)',
        color: 'rgba(220,231,241,0.85)',
      });
    }
    wrap._press = press;
    wrap._release = release;
    wrap._circle = circle;
    return wrap;
  }

  /* ── build ───────────────────────────────────────────────────────────────── */
  function build() {
    /* portrait warning */
    var portrait = el('div', {
      position: 'fixed', inset: '0', zIndex: '9999',
      background: '#050608',
      display: 'none',
      flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      color: '#edf2f7',
      fontFamily: 'Microsoft YaHei, Arial, sans-serif',
      fontSize: '18px', textAlign: 'center',
      pointerEvents: 'auto',
    });
    portrait.id = 'tc-portrait';
    portrait.innerHTML =
      '<div style="font-size:64px;margin-bottom:20px;transform:rotate(90deg);display:inline-block">&#x2B62;</div>' +
      '<div style="font-weight:800;font-size:20px">请将设备横屏</div>' +
      '<div style="color:#9aa4af;font-size:14px;margin-top:10px">竖屏不支持游戏操作</div>';
    document.body.appendChild(portrait);

    /* main overlay */
    var overlay = el('div', {
      position: 'fixed', inset: '0', zIndex: '55',
      pointerEvents: 'none',
      userSelect: 'none', WebkitUserSelect: 'none',
      touchAction: 'none',
    });
    overlay.id = 'tc-overlay';
    document.body.appendChild(overlay);

    /* left zone (joystick) */
    var leftZone = el('div', {
      position: 'absolute',
      left: '0', top: '0',
      width: '44%', height: '100%',
      pointerEvents: 'none', /* enabled after game starts */
      touchAction: 'none',
    });
    overlay.appendChild(leftZone);

    /* joystick visual */
    jBaseEl = el('div', {
      position: 'absolute',
      left: '22%', bottom: '18%',
      width: '136px', height: '136px',
      borderRadius: '50%',
      border: '1.5px solid rgba(255,255,255,0.12)',
      background: 'rgba(16,20,28,0.52)',
      backdropFilter: 'blur(4px)',
      transform: 'translate(-50%, 50%)',
      pointerEvents: 'none',
      transition: 'opacity 0.2s',
      opacity: '0.6',
    });
    leftZone.appendChild(jBaseEl);

    jThumb = el('div', {
      position: 'absolute',
      left: '50%', top: '50%',
      width: '54px', height: '54px',
      borderRadius: '50%',
      border: '1.5px solid rgba(72,240,160,0.5)',
      background: 'rgba(72,240,160,0.15)',
      transform: 'translate(-50%, -50%)',
      pointerEvents: 'none',
      boxShadow: '0 0 12px rgba(72,240,160,0.18)',
    });
    jBaseEl.appendChild(jThumb);

    /* right zone (fire/aim) */
    var rightZone = el('div', {
      position: 'absolute',
      right: '0', top: '0',
      width: '56%', height: '100%',
      pointerEvents: 'none', /* enabled after game starts */
      touchAction: 'none',
    });
    overlay.appendChild(rightZone);

    /* ── action buttons ─────────────────────────────────────────────────── */
    var reloadBtn  = mkBtn('↺', '换弹', { bottom: '10%', left: 'calc(44% - 88px)' });
    var dashBtn    = mkBtn('»', '冲刺', { bottom: '10%', left: 'calc(44% - 22px)' });
    var wPrevBtn   = mkBtn('<',  '上枪', { bottom: '10%', right: '19%' });
    var wNextBtn   = mkBtn('>',  '下枪', { bottom: '10%', right: '11%' });
    var bagBtn     = mkBtn('≡', '背包', { bottom: '10%', right: '3%' });

    var allBtns = [reloadBtn, dashBtn, wPrevBtn, wNextBtn, bagBtn];
    allBtns.forEach(function (b) {
      b.style.pointerEvents = 'none'; /* enabled after game starts */
      overlay.appendChild(b);
    });

    /* button handlers */
    function bindBtn(b, fn) {
      b.addEventListener('touchstart', function (e) { b._press(e); fn(); }, { passive: false });
      b.addEventListener('touchend',   function (e) { b._release(e); }, { passive: false });
      b.addEventListener('touchcancel', function ()  { b._release(); }, { passive: false });
    }
    bindBtn(reloadBtn, function () { tapKey('r'); });
    bindBtn(dashBtn,   function () { tapKey(' '); });
    bindBtn(wPrevBtn,  function () { tapKey('q'); });
    bindBtn(wNextBtn,  function () { tapKey('e'); });
    bindBtn(bagBtn,    function () { tapKey('b'); });

    /* ── joystick handlers ──────────────────────────────────────────────── */
    leftZone.addEventListener('touchstart', function (e) {
      e.preventDefault();
      var t = e.changedTouches[0];
      if (jTouchId === null) {
        jTouchId = t.identifier;
        var rect = leftZone.getBoundingClientRect();
        jBaseX = t.clientX; jBaseY = t.clientY;
        Object.assign(jBaseEl.style, {
          left: (t.clientX - rect.left) + 'px',
          top:  (t.clientY - rect.top)  + 'px',
          bottom: 'auto',
          transform: 'translate(-50%, -50%)',
          opacity: '1',
        });
        updateJoystick(0, 0);
      }
    }, { passive: false });

    leftZone.addEventListener('touchmove', function (e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        var t = e.changedTouches[i];
        if (t.identifier === jTouchId)
          updateJoystick(t.clientX - jBaseX, t.clientY - jBaseY);
      }
    }, { passive: false });

    function jEnd(e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        if (e.changedTouches[i].identifier === jTouchId) {
          jTouchId = null;
          updateJoystick(0, 0);
          Object.assign(jBaseEl.style, {
            left: '22%', top: 'auto', bottom: '18%',
            transform: 'translate(-50%, 50%)',
            opacity: '0.6',
          });
        }
      }
    }
    leftZone.addEventListener('touchend',   jEnd, { passive: false });
    leftZone.addEventListener('touchcancel', jEnd, { passive: false });

    /* ── fire zone handlers ─────────────────────────────────────────────── */
    rightZone.addEventListener('touchstart', function (e) {
      e.preventDefault();
      var t = e.changedTouches[0];
      if (aimTouchId === null) {
        aimTouchId = t.identifier;
        startFire(t.clientX, t.clientY);
      }
    }, { passive: false });

    rightZone.addEventListener('touchmove', function (e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        var t = e.changedTouches[i];
        if (t.identifier === aimTouchId) aimAt(t.clientX, t.clientY);
      }
    }, { passive: false });

    function fireEnd(e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        if (e.changedTouches[i].identifier === aimTouchId) {
          aimTouchId = null;
          stopFire();
        }
      }
    }
    rightZone.addEventListener('touchend',   fireEnd, { passive: false });
    rightZone.addEventListener('touchcancel', fireEnd, { passive: false });

    /* ── enable zones once game starts (join-screen hides) ──────────────── */
    function setActive(on) {
      var pe = on ? 'auto' : 'none';
      leftZone.style.pointerEvents  = pe;
      rightZone.style.pointerEvents = pe;
      allBtns.forEach(function (b) {
        b.style.pointerEvents = pe;
        b.style.opacity = on ? '1' : '0';
      });
      if (!on) {
        releaseKey('w'); releaseKey('s'); releaseKey('a'); releaseKey('d');
        if (aimTouchId !== null) { stopFire(); aimTouchId = null; }
      }
    }

    var joinScreen = document.getElementById('join-screen');
    if (joinScreen) {
      new MutationObserver(function () {
        setActive(joinScreen.style.display === 'none');
      }).observe(joinScreen, { attributes: true, attributeFilter: ['style'] });
    }
    setActive(false); /* start inactive */

    /* ── orientation ────────────────────────────────────────────────────── */
    function checkOrientation() {
      var isPortrait = window.innerWidth < window.innerHeight;
      portrait.style.display = isPortrait ? 'flex' : 'none';
    }
    window.addEventListener('resize', checkOrientation);
    window.addEventListener('orientationchange', function () {
      setTimeout(checkOrientation, 120);
    });
    checkOrientation();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', build);
  } else {
    build();
  }
})();
