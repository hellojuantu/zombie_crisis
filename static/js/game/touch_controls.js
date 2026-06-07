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

  /* ── joystick state ──────────────────────────────────────────────────────── */
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
    if (ny > t) pressKey('s'); else releaseKey('s');
    if (nx < -t) pressKey('a'); else releaseKey('a');
    if (nx > t) pressKey('d'); else releaseKey('d');
  }

  /* ── DOM helpers ─────────────────────────────────────────────────────────── */
  function el(tag, styles) {
    var e = document.createElement(tag);
    if (styles) Object.assign(e.style, styles);
    return e;
  }
  function mkBtn(label, styles) {
    var b = el('div', Object.assign({
      position: 'absolute',
      width: '56px', height: '56px',
      borderRadius: '50%',
      border: '2px solid rgba(255,255,255,0.20)',
      background: 'rgba(255,255,255,0.09)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: '14px', fontWeight: '900',
      color: 'rgba(255,255,255,0.72)',
      userSelect: 'none', WebkitUserSelect: 'none',
      touchAction: 'none',
      cursor: 'pointer',
      lineHeight: '1',
    }, styles || {}));
    b.textContent = label;
    return b;
  }

  /* ── build UI ────────────────────────────────────────────────────────────── */
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
      '<div style="font-size:56px;margin-bottom:18px">⟳</div>' +
      '<div style="font-weight:800">请将设备横屏</div>' +
      '<div style="color:#9aa4af;font-size:14px;margin-top:10px">竖屏模式不支持游戏操作</div>';
    document.body.appendChild(portrait);

    /* main overlay – full screen, pass-through by default */
    var overlay = el('div', {
      position: 'fixed', inset: '0', zIndex: '200',
      pointerEvents: 'none',
      userSelect: 'none', WebkitUserSelect: 'none',
      touchAction: 'none',
    });
    overlay.id = 'tc-overlay';
    document.body.appendChild(overlay);

    /* left joystick zone (44% wide) */
    var leftZone = el('div', {
      position: 'absolute',
      left: '0', top: '0',
      width: '44%', height: '100%',
      pointerEvents: 'auto',
      touchAction: 'none',
    });
    overlay.appendChild(leftZone);

    /* joystick visual base */
    jBaseEl = el('div', {
      position: 'absolute',
      left: '22%', bottom: '16%',
      width: '140px', height: '140px',
      borderRadius: '50%',
      border: '2px solid rgba(255,255,255,0.14)',
      background: 'rgba(255,255,255,0.05)',
      transform: 'translate(-50%, 50%)',
      pointerEvents: 'none',
      transition: 'opacity 0.18s',
      opacity: '0.7',
    });
    leftZone.appendChild(jBaseEl);

    jThumb = el('div', {
      position: 'absolute',
      left: '50%', top: '50%',
      width: '58px', height: '58px',
      borderRadius: '50%',
      border: '2px solid rgba(72,240,160,0.55)',
      background: 'rgba(72,240,160,0.18)',
      transform: 'translate(-50%, -50%)',
      pointerEvents: 'none',
    });
    jBaseEl.appendChild(jThumb);

    /* right fire zone (56% wide) */
    var rightZone = el('div', {
      position: 'absolute',
      right: '0', top: '0',
      width: '56%', height: '100%',
      pointerEvents: 'auto',
      touchAction: 'none',
    });
    overlay.appendChild(rightZone);

    /* fire zone hint ring (invisible by default) */
    var fireHint = el('div', {
      position: 'absolute',
      right: '12%', top: '50%',
      width: '100px', height: '100px',
      borderRadius: '50%',
      border: '1px solid rgba(255,255,255,0.06)',
      transform: 'translate(50%, -50%)',
      pointerEvents: 'none',
    });
    rightZone.appendChild(fireHint);

    /* ── action buttons ─────────────────────────────────────────────────── */

    /* Reload (R) – center-bottom, left side */
    var reloadBtn = mkBtn('R', { bottom: '10%', left: 'calc(44% - 90px)' });
    /* Dash (⚡) – center-bottom, slightly higher */
    var dashBtn = mkBtn('冲', { bottom: '10%', left: 'calc(44% - 24px)' });
    /* Weapon prev (◀) */
    var wPrevBtn = mkBtn('◀', { bottom: '10%', right: '22%' });
    /* Weapon next (▶) */
    var wNextBtn = mkBtn('▶', { bottom: '10%', right: '14%' });
    /* Bag (背) */
    var bagBtn = mkBtn('背', { bottom: '10%', right: '6%' });

    [reloadBtn, dashBtn, wPrevBtn, wNextBtn, bagBtn].forEach(function (b) {
      b.style.pointerEvents = 'auto';
      overlay.appendChild(b);
    });

    /* button touch handlers */
    function bindTap(b, downFn, upFn) {
      b.addEventListener('touchstart', function (e) {
        e.preventDefault(); e.stopPropagation();
        Object.assign(b.style, { background: 'rgba(72,240,160,0.28)', borderColor: 'rgba(72,240,160,0.6)' });
        downFn();
      }, { passive: false });
      b.addEventListener('touchend', function (e) {
        e.preventDefault(); e.stopPropagation();
        Object.assign(b.style, { background: 'rgba(255,255,255,0.09)', borderColor: 'rgba(255,255,255,0.20)' });
        if (upFn) upFn();
      }, { passive: false });
      b.addEventListener('touchcancel', function () {
        Object.assign(b.style, { background: 'rgba(255,255,255,0.09)', borderColor: 'rgba(255,255,255,0.20)' });
        if (upFn) upFn();
      });
    }

    bindTap(reloadBtn, function () { tapKey('r'); });
    bindTap(dashBtn, function () { tapKey(' '); });
    bindTap(wPrevBtn, function () { tapKey('q'); });
    bindTap(wNextBtn, function () { tapKey('e'); });
    bindTap(bagBtn, function () { tapKey('b'); });

    /* ── joystick touch ─────────────────────────────────────────────────── */
    leftZone.addEventListener('touchstart', function (e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        var t = e.changedTouches[i];
        if (jTouchId === null) {
          jTouchId = t.identifier;
          var rect = leftZone.getBoundingClientRect();
          jBaseX = t.clientX;
          jBaseY = t.clientY;
          Object.assign(jBaseEl.style, {
            left: (t.clientX - rect.left) + 'px',
            top: (t.clientY - rect.top) + 'px',
            bottom: 'auto',
            transform: 'translate(-50%, -50%)',
            opacity: '1',
          });
          updateJoystick(0, 0);
        }
      }
    }, { passive: false });

    leftZone.addEventListener('touchmove', function (e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        var t = e.changedTouches[i];
        if (t.identifier === jTouchId) {
          updateJoystick(t.clientX - jBaseX, t.clientY - jBaseY);
        }
      }
    }, { passive: false });

    function jEnd(e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        if (e.changedTouches[i].identifier === jTouchId) {
          jTouchId = null;
          updateJoystick(0, 0);
          Object.assign(jBaseEl.style, {
            left: '22%', top: 'auto', bottom: '16%',
            transform: 'translate(-50%, 50%)',
            opacity: '0.7',
          });
        }
      }
    }
    leftZone.addEventListener('touchend', jEnd, { passive: false });
    leftZone.addEventListener('touchcancel', jEnd, { passive: false });

    /* ── fire zone touch ────────────────────────────────────────────────── */
    rightZone.addEventListener('touchstart', function (e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        var t = e.changedTouches[i];
        if (aimTouchId === null) {
          aimTouchId = t.identifier;
          startFire(t.clientX, t.clientY);
        }
      }
    }, { passive: false });

    rightZone.addEventListener('touchmove', function (e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        var t = e.changedTouches[i];
        if (t.identifier === aimTouchId) {
          aimAt(t.clientX, t.clientY);
        }
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
    rightZone.addEventListener('touchend', fireEnd, { passive: false });
    rightZone.addEventListener('touchcancel', fireEnd, { passive: false });

    /* ── orientation check ──────────────────────────────────────────────── */
    function checkOrientation() {
      var isPortrait = window.innerWidth < window.innerHeight;
      portrait.style.display = isPortrait ? 'flex' : 'none';
      overlay.style.display = isPortrait ? 'none' : '';
    }
    window.addEventListener('resize', checkOrientation);
    window.addEventListener('orientationchange', function () {
      setTimeout(checkOrientation, 120);
    });
    checkOrientation();

    /* prevent context menu on long-press */
    document.addEventListener('contextmenu', function (e) {
      if (e.target === document.getElementById('gameCanvas') || e.target === overlay) {
        e.preventDefault();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', build);
  } else {
    build();
  }
})();
