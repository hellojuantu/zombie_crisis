/* touch_controls.js – dual fixed joystick: left=move, right=aim+autofire */
(function () {
  'use strict';

  if (!('ontouchstart' in window) && navigator.maxTouchPoints < 1) return;

  var DEAD = 16, MAX_R = 58, AIM_DEAD = 12;

  var activeKeys = {};
  /* left stick state */
  var jId = null, jBx = 0, jBy = 0, jBase, jThumb;
  /* right stick state */
  var rId = null, rBx = 0, rBy = 0, rBase, rThumb;
  var firing = false;
  var _canvas = null;

  /* ── key helpers ─────────────────────────────────────────────────────────── */
  function pressKey(k) {
    if (activeKeys[k]) return;
    activeKeys[k] = true;
    window.dispatchEvent(new KeyboardEvent('keydown', {
      key: k, code: k === ' ' ? 'Space' : 'Key' + k.toUpperCase(),
      bubbles: true, cancelable: true,
    }));
  }
  function releaseKey(k) {
    if (!activeKeys[k]) return;
    activeKeys[k] = false;
    window.dispatchEvent(new KeyboardEvent('keyup', {
      key: k, code: k === ' ' ? 'Space' : 'Key' + k.toUpperCase(),
      bubbles: true, cancelable: true,
    }));
  }
  function tapKey(k) { pressKey(k); setTimeout(function () { releaseKey(k); }, 90); }

  /* ── aim / fire ──────────────────────────────────────────────────────────── */
  function cv() { return _canvas || (_canvas = document.getElementById('gameCanvas') || document.body); }

  function aimDir(nx, ny) {
    var cx = window.innerWidth * 0.5, cy = window.innerHeight * 0.5;
    window.dispatchEvent(new MouseEvent('mousemove', {
      clientX: cx + nx * 600, clientY: cy + ny * 600, bubbles: true,
    }));
  }
  function startFire(nx, ny) {
    if (firing) return;
    firing = true;
    var cx = window.innerWidth * 0.5, cy = window.innerHeight * 0.5;
    cv().dispatchEvent(new MouseEvent('mousedown', {
      button: 0, buttons: 1,
      clientX: cx + nx * 600, clientY: cy + ny * 600,
      bubbles: true, cancelable: true,
    }));
  }
  function stopFire() {
    if (!firing) return;
    firing = false;
    window.dispatchEvent(new MouseEvent('mouseup', { button: 0, bubbles: true, cancelable: true }));
  }

  /* ── movement joystick logic ─────────────────────────────────────────────── */
  function updateMove(dx, dy) {
    var d = Math.hypot(dx, dy), c = Math.min(d, MAX_R);
    if (jThumb) {
      var tx = d > 0 ? (dx / d) * c : 0, ty = d > 0 ? (dy / d) * c : 0;
      jThumb.style.transform = 'translate(calc(-50% + ' + tx + 'px), calc(-50% + ' + ty + 'px))';
    }
    if (d < DEAD) { releaseKey('w'); releaseKey('s'); releaseKey('a'); releaseKey('d'); return; }
    var nx = dx / d, ny = dy / d, t = 0.36;
    nx < -t ? pressKey('a') : releaseKey('a');
    nx >  t ? pressKey('d') : releaseKey('d');
    ny < -t ? pressKey('w') : releaseKey('w');
    ny >  t ? pressKey('s') : releaseKey('s');
  }

  /* ── aim joystick logic ──────────────────────────────────────────────────── */
  function updateAim(dx, dy) {
    var d = Math.hypot(dx, dy), c = Math.min(d, MAX_R);
    if (rThumb) {
      var tx = d > 0 ? (dx / d) * c : 0, ty = d > 0 ? (dy / d) * c : 0;
      rThumb.style.transform = 'translate(calc(-50% + ' + tx + 'px), calc(-50% + ' + ty + 'px))';
    }
    if (d < AIM_DEAD) { stopFire(); return; }
    var nx = dx / d, ny = dy / d;
    aimDir(nx, ny);
    startFire(nx, ny);
  }

  /* ── DOM helpers ─────────────────────────────────────────────────────────── */
  function el(tag, styles) {
    var e = document.createElement(tag);
    if (styles) Object.assign(e.style, styles);
    return e;
  }

  /* Build a joystick at a fixed CSS position.
     accent = thumb ring color (rgba string).
     pos    = style object for positioning the base. */
  function mkStick(accent, pos) {
    var base = el('div', Object.assign({
      position: 'absolute',
      width: '140px', height: '140px', borderRadius: '50%',
      border: '1.5px solid rgba(255,255,255,0.08)',
      background: 'rgba(14,18,26,0.55)',
      backdropFilter: 'blur(4px)',
      pointerEvents: 'none',
      opacity: '0',
      transition: 'opacity 0.2s',
      /* centre-anchor the circle on its position point */
      transform: 'translate(-50%, -50%)',
    }, pos || {}));

    var thumb = el('div', {
      position: 'absolute', left: '50%', top: '50%',
      width: '58px', height: '58px', borderRadius: '50%',
      border: '2px solid ' + accent,
      background: accent.replace(/[\d.]+\)$/, '0.10)'),
      transform: 'translate(-50%, -50%)',
      pointerEvents: 'none',
      boxShadow: '0 0 18px ' + accent.replace(/[\d.]+\)$/, '0.18)'),
      transition: 'transform 0.04s',
    });
    base.appendChild(thumb);
    return { base: base, thumb: thumb };
  }

  function mkBtn(icon, label, styles) {
    var wrap = el('div', Object.assign({
      position: 'absolute',
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '3px',
      userSelect: 'none', WebkitUserSelect: 'none', touchAction: 'none',
      cursor: 'pointer', pointerEvents: 'none', opacity: '0',
      transition: 'opacity 0.2s',
    }, styles || {}));
    var circle = el('div', {
      width: '46px', height: '46px', borderRadius: '50%',
      border: '1.5px solid rgba(255,255,255,0.18)',
      background: 'rgba(14,18,26,0.80)',
      backdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: '16px', fontWeight: '900', color: 'rgba(210,225,241,0.88)',
      boxShadow: '0 2px 10px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.07)',
      transition: 'background 0.07s, border-color 0.07s, color 0.07s',
    });
    circle.textContent = icon;
    var lbl = el('div', {
      fontSize: '9px', color: 'rgba(148,160,174,0.80)',
      fontWeight: '600', letterSpacing: '0.3px', whiteSpace: 'nowrap',
    });
    lbl.textContent = label;
    wrap.appendChild(circle); wrap.appendChild(lbl);
    wrap._circle = circle;
    wrap._press = function (e) {
      e.preventDefault(); e.stopPropagation();
      Object.assign(circle.style, {
        background: 'rgba(72,240,160,0.22)', borderColor: 'rgba(72,240,160,0.58)', color: '#48f0a0',
      });
    };
    wrap._release = function (e) {
      if (e) { e.preventDefault(); e.stopPropagation(); }
      Object.assign(circle.style, {
        background: 'rgba(14,18,26,0.80)', borderColor: 'rgba(255,255,255,0.18)', color: 'rgba(210,225,241,0.88)',
      });
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
      textAlign: 'center', pointerEvents: 'auto',
    });
    portrait.id = 'tc-portrait';
    portrait.innerHTML =
      '<div style="width:54px;height:54px;border:2.5px solid #48f0a0;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-bottom:14px;font-size:26px;color:#48f0a0">&#x21BB;</div>' +
      '<div style="font-weight:800;font-size:19px">请将设备横屏</div>' +
      '<div style="color:#9aa4af;font-size:13px;margin-top:8px">竖屏不支持游戏操作</div>';
    document.body.appendChild(portrait);

    /* overlay */
    var overlay = el('div', {
      position: 'fixed', inset: '0', zIndex: '55',
      pointerEvents: 'none', touchAction: 'none',
      userSelect: 'none', WebkitUserSelect: 'none',
    });
    overlay.id = 'tc-overlay';
    document.body.appendChild(overlay);

    /* ── LEFT zone: touch anywhere in left half, joystick fixed at bottom-left ── */
    var lz = el('div', {
      position: 'absolute', left: '0', top: '0',
      width: '44%', height: '100%',
      pointerEvents: 'none', touchAction: 'none',
    });
    overlay.appendChild(lz);

    /* fixed rest position for left stick: 22% from left, 90px from bottom */
    var ls = mkStick('rgba(72,240,160,0.60)', {
      left: '22%', bottom: '90px', top: 'auto',
      transform: 'translate(-50%, 50%)',
    });
    jBase = ls.base; jThumb = ls.thumb;
    lz.appendChild(jBase);

    /* ── RIGHT zone: touch anywhere in right half, joystick fixed at bottom-right ── */
    var rz = el('div', {
      position: 'absolute', right: '0', top: '0',
      width: '56%', height: '100%',
      pointerEvents: 'none', touchAction: 'none',
    });
    overlay.appendChild(rz);

    /* fixed rest position for right stick: 22% from right, 90px from bottom */
    var rs = mkStick('rgba(72,240,160,0.60)', {
      right: '18%', left: 'auto', bottom: '90px', top: 'auto',
      transform: 'translate(50%, 50%)',
    });
    rBase = rs.base; rThumb = rs.thumb;
    rz.appendChild(rBase);

    /* ── action buttons ──────────────────────────────────────────────────────
       Between the two joysticks, accessible to both thumbs.
       Bottom centre area — row of small buttons.
    ──────────────────────────────────────────────────────────────────────── */
    var dashBtn   = mkBtn('»', '冲刺', { bottom: '12px', left:  'calc(44% - 68px)' });
    var reloadBtn = mkBtn('↺', '换弹', { bottom: '12px', left:  'calc(44% + 8px)'  });
    var wPrevBtn  = mkBtn('<', '上枪', { bottom: '12px', right: '162px' });
    var wNextBtn  = mkBtn('>', '下枪', { bottom: '12px', right: '96px'  });
    var bagBtn    = mkBtn('≡', '背包', { bottom: '12px', right: '18px'  });

    var allBtns = [dashBtn, reloadBtn, wPrevBtn, wNextBtn, bagBtn];
    allBtns.forEach(function (b) { overlay.appendChild(b); });

    function bindBtn(b, fn) {
      b.addEventListener('touchstart', function (e) { b._press(e); fn(); }, { passive: false });
      b.addEventListener('touchend',   function (e) { b._release(e); }, { passive: false });
      b.addEventListener('touchcancel', function ()  { b._release(); });
    }
    bindBtn(dashBtn,   function () { tapKey(' '); });
    bindBtn(reloadBtn, function () { tapKey('r'); });
    bindBtn(wPrevBtn,  function () { tapKey('q'); });
    bindBtn(wNextBtn,  function () { tapKey('e'); });
    bindBtn(bagBtn,    function () { tapKey('b'); });

    /* ── left zone touch (movement) ──────────────────────────────────────── */
    lz.addEventListener('touchstart', function (e) {
      e.preventDefault();
      var t = e.changedTouches[0];
      if (jId !== null) return;
      jId = t.identifier;
      /* anchor joystick at touch point */
      var r = lz.getBoundingClientRect();
      jBx = t.clientX; jBy = t.clientY;
      Object.assign(jBase.style, {
        left: (t.clientX - r.left) + 'px', top: (t.clientY - r.top) + 'px',
        bottom: 'auto', transform: 'translate(-50%, -50%)', opacity: '0.90',
      });
      updateMove(0, 0);
    }, { passive: false });

    lz.addEventListener('touchmove', function (e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        var t = e.changedTouches[i];
        if (t.identifier === jId) updateMove(t.clientX - jBx, t.clientY - jBy);
      }
    }, { passive: false });

    function jEnd(e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        if (e.changedTouches[i].identifier !== jId) continue;
        jId = null;
        updateMove(0, 0);
        /* snap back to rest */
        Object.assign(jBase.style, {
          left: '22%', top: 'auto', bottom: '90px',
          transform: 'translate(-50%, 50%)', opacity: '0.50',
        });
      }
    }
    lz.addEventListener('touchend',    jEnd, { passive: false });
    lz.addEventListener('touchcancel', jEnd, { passive: false });

    /* ── right zone touch (aim) ──────────────────────────────────────────── */
    rz.addEventListener('touchstart', function (e) {
      e.preventDefault();
      var t = e.changedTouches[0];
      if (rId !== null) return;
      rId = t.identifier;
      /* anchor aim joystick at touch point */
      var r = rz.getBoundingClientRect();
      rBx = t.clientX; rBy = t.clientY;
      Object.assign(rBase.style, {
        left: (t.clientX - r.left) + 'px', top: (t.clientY - r.top) + 'px',
        right: 'auto', bottom: 'auto', transform: 'translate(-50%, -50%)', opacity: '0.90',
      });
      updateAim(0, 0);
    }, { passive: false });

    rz.addEventListener('touchmove', function (e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        var t = e.changedTouches[i];
        if (t.identifier === rId) updateAim(t.clientX - rBx, t.clientY - rBy);
      }
    }, { passive: false });

    function rEnd(e) {
      e.preventDefault();
      for (var i = 0; i < e.changedTouches.length; i++) {
        if (e.changedTouches[i].identifier !== rId) continue;
        rId = null;
        stopFire();
        rThumb.style.transform = 'translate(-50%, -50%)';
        /* snap back to rest */
        Object.assign(rBase.style, {
          right: '18%', left: 'auto', top: 'auto', bottom: '90px',
          transform: 'translate(50%, 50%)', opacity: '0.50',
        });
      }
    }
    rz.addEventListener('touchend',    rEnd, { passive: false });
    rz.addEventListener('touchcancel', rEnd, { passive: false });

    /* ── enable / disable after join screen ──────────────────────────────── */
    function setActive(on) {
      var pe = on ? 'auto' : 'none';
      lz.style.pointerEvents = pe;
      rz.style.pointerEvents = pe;
      allBtns.forEach(function (b) { b.style.pointerEvents = pe; b.style.opacity = on ? '1' : '0'; });
      jBase.style.opacity = on ? '0.50' : '0';
      rBase.style.opacity = on ? '0.50' : '0';
      if (!on) {
        releaseKey('w'); releaseKey('s'); releaseKey('a'); releaseKey('d');
        stopFire(); jId = null; rId = null;
      }
    }

    var joinScreen = document.getElementById('join-screen');
    if (joinScreen) {
      new MutationObserver(function () {
        setActive(joinScreen.style.display === 'none');
      }).observe(joinScreen, { attributes: true, attributeFilter: ['style'] });
    }
    setActive(false);

    /* ── orientation ─────────────────────────────────────────────────────── */
    function checkOrientation() {
      portrait.style.display = window.innerWidth < window.innerHeight ? 'flex' : 'none';
    }
    window.addEventListener('resize', checkOrientation);
    window.addEventListener('orientationchange', function () { setTimeout(checkOrientation, 120); });
    checkOrientation();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build);
  else build();
})();
