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
      key: key, code: key === ' ' ? 'Space' : 'Key' + key.toUpperCase(),
      bubbles: true, cancelable: true,
    }));
  }
  function releaseKey(key) {
    if (!activeKeys[key]) return;
    activeKeys[key] = false;
    window.dispatchEvent(new KeyboardEvent('keyup', {
      key: key, code: key === ' ' ? 'Space' : 'Key' + key.toUpperCase(),
      bubbles: true, cancelable: true,
    }));
  }
  function tapKey(key) { pressKey(key); setTimeout(function () { releaseKey(key); }, 90); }

  /* ── mouse helpers ───────────────────────────────────────────────────────── */
  function aimAt(cx, cy) {
    window.dispatchEvent(new MouseEvent('mousemove', { clientX: cx, clientY: cy, bubbles: true }));
  }
  function startFire(cx, cy) {
    aimAt(cx, cy);
    var canvas = document.getElementById('gameCanvas') || document.body;
    canvas.dispatchEvent(new MouseEvent('mousedown', {
      button: 0, buttons: 1, clientX: cx, clientY: cy, bubbles: true, cancelable: true,
    }));
  }
  function stopFire() {
    window.dispatchEvent(new MouseEvent('mouseup', { button: 0, bubbles: true, cancelable: true }));
  }

  /* ── joystick ────────────────────────────────────────────────────────────── */
  function updateJoystick(dx, dy) {
    var d = Math.hypot(dx, dy);
    var c = Math.min(d, MAX_R);
    if (jThumb) {
      var tx = d > 0 ? (dx / d) * c : 0, ty = d > 0 ? (dy / d) * c : 0;
      jThumb.style.transform = 'translate(calc(-50% + ' + tx + 'px), calc(-50% + ' + ty + 'px))';
    }
    if (d < DEAD) { releaseKey('w'); releaseKey('s'); releaseKey('a'); releaseKey('d'); return; }
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
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '3px',
      userSelect: 'none', WebkitUserSelect: 'none', touchAction: 'none',
      cursor: 'pointer', pointerEvents: 'none',
    }, styles || {}));

    var circle = el('div', {
      width: '50px', height: '50px', borderRadius: '50%',
      border: '1.5px solid rgba(255,255,255,0.20)',
      background: 'rgba(14,18,26,0.78)',
      backdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: '17px', fontWeight: '900', color: 'rgba(210,225,241,0.88)',
      boxShadow: '0 2px 10px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.07)',
      transition: 'background 0.07s, border-color 0.07s, color 0.07s',
    });
    circle.textContent = icon;

    var lbl = el('div', {
      fontSize: '10px', color: 'rgba(148,160,174,0.82)',
      fontWeight: '600', letterSpacing: '0.3px', whiteSpace: 'nowrap',
    });
    lbl.textContent = label;

    wrap.appendChild(circle);
    wrap.appendChild(lbl);
    wrap._circle = circle;
    wrap._press = function (e) {
      e.preventDefault(); e.stopPropagation();
      Object.assign(circle.style, { background: 'rgba(72,240,160,0.24)', borderColor: 'rgba(72,240,160,0.6)', color: '#48f0a0' });
    };
    wrap._release = function (e) {
      if (e) { e.preventDefault(); e.stopPropagation(); }
      Object.assign(circle.style, { background: 'rgba(14,18,26,0.78)', borderColor: 'rgba(255,255,255,0.20)', color: 'rgba(210,225,241,0.88)' });
    };
    return wrap;
  }

  /* ── build ───────────────────────────────────────────────────────────────── */
  function build() {
    /* portrait warning */
    var portrait = el('div', {
      position: 'fixed', inset: '0', zIndex: '9999',
      background: '#050608', display: 'none',
      flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      color: '#edf2f7', fontFamily: 'Microsoft YaHei, Arial, sans-serif',
      fontSize: '18px', textAlign: 'center', pointerEvents: 'auto',
    });
    portrait.id = 'tc-portrait';
    portrait.innerHTML =
      '<div style="width:60px;height:60px;border:2.5px solid #48f0a0;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-bottom:18px;font-size:28px;color:#48f0a0">&#x21BB;</div>' +
      '<div style="font-weight:800;font-size:20px">请将设备横屏</div>' +
      '<div style="color:#9aa4af;font-size:13px;margin-top:10px">竖屏不支持游戏操作</div>';
    document.body.appendChild(portrait);

    /* main overlay */
    var overlay = el('div', {
      position: 'fixed', inset: '0', zIndex: '55',
      pointerEvents: 'none', touchAction: 'none',
      userSelect: 'none', WebkitUserSelect: 'none',
    });
    overlay.id = 'tc-overlay';
    document.body.appendChild(overlay);

    /* left zone */
    var leftZone = el('div', {
      position: 'absolute', left: '0', top: '0',
      width: '44%', height: '100%',
      pointerEvents: 'none', touchAction: 'none',
    });
    overlay.appendChild(leftZone);

    /* joystick visual */
    jBaseEl = el('div', {
      position: 'absolute',
      left: '22%', bottom: '90px',
      width: '140px', height: '140px',
      borderRadius: '50%',
      border: '1.5px solid rgba(255,255,255,0.10)',
      background: 'rgba(14,18,26,0.45)',
      backdropFilter: 'blur(3px)',
      transform: 'translate(-50%, 50%)',
      pointerEvents: 'none',
      opacity: '0.55',
      transition: 'opacity 0.18s',
    });
    leftZone.appendChild(jBaseEl);

    jThumb = el('div', {
      position: 'absolute', left: '50%', top: '50%',
      width: '56px', height: '56px', borderRadius: '50%',
      border: '1.5px solid rgba(72,240,160,0.52)',
      background: 'rgba(72,240,160,0.14)',
      transform: 'translate(-50%, -50%)',
      pointerEvents: 'none',
      boxShadow: '0 0 14px rgba(72,240,160,0.18)',
    });
    jBaseEl.appendChild(jThumb);

    /* right zone */
    var rightZone = el('div', {
      position: 'absolute', right: '0', top: '0',
      width: '56%', height: '100%',
      pointerEvents: 'none', touchAction: 'none',
    });
    overlay.appendChild(rightZone);

    /* aim dot – appears at touch point in fire zone */
    var aimDot = el('div', {
      position: 'absolute', display: 'none',
      width: '22px', height: '22px', borderRadius: '50%',
      border: '1.5px solid rgba(255,255,255,0.55)',
      background: 'rgba(255,255,255,0.10)',
      transform: 'translate(-50%, -50%)',
      pointerEvents: 'none',
      boxShadow: '0 0 8px rgba(255,255,255,0.12)',
    });
    rightZone.appendChild(aimDot);

    /* aim crosshair lines */
    ['w','h'].forEach(function(axis) {
      var line = el('div', {
        position: 'absolute',
        background: 'rgba(255,255,255,0.35)',
        borderRadius: '1px',
        transform: axis === 'w' ? 'translate(-50%, -50%)' : 'translate(-50%, -50%)',
        pointerEvents: 'none',
        width:  axis === 'w' ? '14px' : '1.5px',
        height: axis === 'w' ? '1.5px' : '14px',
      });
      aimDot.appendChild(line);
    });

    /* fire zone label (fades after first touch) */
    var fireHint = el('div', {
      position: 'absolute', left: '50%', top: '50%',
      transform: 'translate(-50%, -50%)',
      color: 'rgba(255,255,255,0.14)',
      fontSize: '12px', fontWeight: '600', letterSpacing: '0.5px',
      pointerEvents: 'none', whiteSpace: 'nowrap',
      transition: 'opacity 0.6s',
      fontFamily: 'Microsoft YaHei, Arial, sans-serif',
    });
    fireHint.textContent = '触控瞄准';
    rightZone.appendChild(fireHint);

    /* ── action buttons ────────────────────────────────────────────────────── */
    /* Left-side: Reload and Dash – near left thumb bottom area */
    var reloadBtn = mkBtn('↺', '换弹',  { bottom: '8px', left: 'calc(44% - 122px)' });
    var dashBtn   = mkBtn('»', '冲刺',  { bottom: '8px', left: 'calc(44% - 58px)'  });
    /* Right-side: Weapon prev/next and Bag – accessible to right thumb */
    var wPrevBtn  = mkBtn('<',  '上枪', { bottom: '8px', right: '156px' });
    var wNextBtn  = mkBtn('>',  '下枪', { bottom: '8px', right: '88px'  });
    var bagBtn    = mkBtn('≡', '背包',  { bottom: '8px', right: '16px'  });

    var allBtns = [reloadBtn, dashBtn, wPrevBtn, wNextBtn, bagBtn];
    allBtns.forEach(function (b) { overlay.appendChild(b); });

    function bindBtn(b, fn) {
      b.addEventListener('touchstart', function (e) { b._press(e); fn(); }, { passive: false });
      b.addEventListener('touchend',   function (e) { b._release(e); }, { passive: false });
      b.addEventListener('touchcancel', function ()  { b._release(); });
    }
    bindBtn(reloadBtn, function () { tapKey('r'); });
    bindBtn(dashBtn,   function () { tapKey(' '); });
    bindBtn(wPrevBtn,  function () { tapKey('q'); });
    bindBtn(wNextBtn,  function () { tapKey('e'); });
    bindBtn(bagBtn,    function () { tapKey('b'); });

    /* ── joystick touch ────────────────────────────────────────────────────── */
    leftZone.addEventListener('touchstart', function (e) {
      e.preventDefault();
      var t = e.changedTouches[0];
      if (jTouchId === null) {
        jTouchId = t.identifier;
        var rect = leftZone.getBoundingClientRect();
        jBaseX = t.clientX; jBaseY = t.clientY;
        Object.assign(jBaseEl.style, {
          left:   (t.clientX - rect.left) + 'px',
          top:    (t.clientY - rect.top)  + 'px',
          bottom: 'auto',
          transform: 'translate(-50%, -50%)',
          opacity: '0.9',
        });
        updateJoystick(0, 0);
      }
    }, { passive: false });

    leftZone.addEventListener('touchmove', function (e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        var t = e.changedTouches[i];
        if (t.identifier === jTouchId) updateJoystick(t.clientX - jBaseX, t.clientY - jBaseY);
      }
    }, { passive: false });

    function jEnd(e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        if (e.changedTouches[i].identifier === jTouchId) {
          jTouchId = null;
          updateJoystick(0, 0);
          Object.assign(jBaseEl.style, {
            left: '22%', top: 'auto', bottom: '90px',
            transform: 'translate(-50%, 50%)',
            opacity: '0.55',
          });
        }
      }
    }
    leftZone.addEventListener('touchend',   jEnd, { passive: false });
    leftZone.addEventListener('touchcancel', jEnd, { passive: false });

    /* ── fire zone touch ───────────────────────────────────────────────────── */
    var fireHintFaded = false;
    rightZone.addEventListener('touchstart', function (e) {
      e.preventDefault();
      var t = e.changedTouches[0];
      if (aimTouchId === null) {
        aimTouchId = t.identifier;
        var rect = rightZone.getBoundingClientRect();
        aimDot.style.display = 'block';
        aimDot.style.left = (t.clientX - rect.left) + 'px';
        aimDot.style.top  = (t.clientY - rect.top)  + 'px';
        if (!fireHintFaded) {
          fireHintFaded = true;
          fireHint.style.opacity = '0';
        }
        startFire(t.clientX, t.clientY);
      }
    }, { passive: false });

    rightZone.addEventListener('touchmove', function (e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        var t = e.changedTouches[i];
        if (t.identifier === aimTouchId) {
          var rect = rightZone.getBoundingClientRect();
          aimDot.style.left = (t.clientX - rect.left) + 'px';
          aimDot.style.top  = (t.clientY - rect.top)  + 'px';
          aimAt(t.clientX, t.clientY);
        }
      }
    }, { passive: false });

    function fireEnd(e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        if (e.changedTouches[i].identifier === aimTouchId) {
          aimTouchId = null;
          aimDot.style.display = 'none';
          stopFire();
        }
      }
    }
    rightZone.addEventListener('touchend',   fireEnd, { passive: false });
    rightZone.addEventListener('touchcancel', fireEnd, { passive: false });

    /* ── enable zones after join-screen hides ──────────────────────────────── */
    function setActive(on) {
      var pe = on ? 'auto' : 'none';
      leftZone.style.pointerEvents  = pe;
      rightZone.style.pointerEvents = pe;
      allBtns.forEach(function (b) {
        b.style.pointerEvents = pe;
        b.style.opacity = on ? '1' : '0';
        b.style.transition = 'opacity 0.2s';
      });
      if (!on) {
        releaseKey('w'); releaseKey('s'); releaseKey('a'); releaseKey('d');
        if (aimTouchId !== null) { stopFire(); aimTouchId = null; aimDot.style.display = 'none'; }
      }
    }

    var joinScreen = document.getElementById('join-screen');
    if (joinScreen) {
      new MutationObserver(function () {
        setActive(joinScreen.style.display === 'none');
      }).observe(joinScreen, { attributes: true, attributeFilter: ['style'] });
    }
    setActive(false);

    /* ── orientation ───────────────────────────────────────────────────────── */
    function checkOrientation() {
      var p = window.innerWidth < window.innerHeight;
      portrait.style.display = p ? 'flex' : 'none';
    }
    window.addEventListener('resize', checkOrientation);
    window.addEventListener('orientationchange', function () { setTimeout(checkOrientation, 120); });
    checkOrientation();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build);
  else build();
})();
