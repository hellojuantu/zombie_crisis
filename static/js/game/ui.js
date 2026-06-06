export function createUI() {
  const joinScreen = document.getElementById('join-screen');
  const joinBtn = document.getElementById('joinBtn');
  const restartBtn = document.getElementById('restartBtn');
  const hud = document.getElementById('hud');
  const waveInfo = document.getElementById('wave-info');
  const scoreboard = document.getElementById('scoreboard');
  const deathOverlay = document.getElementById('death-overlay');
  const notifications = document.getElementById('notifications');
  let joinTimer = null;

  function setJoinLoading(on) {
    joinBtn.disabled = on;
    joinBtn.textContent = on ? '加入中...' : '加入游戏';
    if (joinTimer) clearTimeout(joinTimer);
    joinTimer = on ? setTimeout(() => setJoinLoading(false), 8000) : null;
  }

  function bindActions(onJoin, onRestart) {
    joinBtn.onclick = onJoin;
    restartBtn.onclick = onRestart;
  }

  function showGame(name, color) {
    setJoinLoading(false);
    joinScreen.style.display = 'none';
    hud.style.display = 'block';
    waveInfo.style.display = 'block';
    scoreboard.style.display = 'block';
    const pname = document.getElementById('pname');
    pname.textContent = name;
    pname.style.color = color;
  }

  function showJoin() {
    setJoinLoading(false);
    joinScreen.style.display = 'flex';
  }

  function setNet(text, color = '#aaa') {
    const el = document.getElementById('netstat');
    el.textContent = text;
    el.style.color = color;
  }

  function setPing(ms) {
    const el = document.getElementById('pingstat');
    if (ms == null) {
      el.textContent = '--';
      el.style.color = '#aaa';
      return;
    }
    el.textContent = `${Math.round(ms)}ms`;
    el.style.color = ms < 50 ? '#48f0a0' : ms < 120 ? '#ffc247' : '#ff6666';
  }

  function notify(text, color = '#fff') {
    const node = document.createElement('div');
    node.className = 'nt';
    node.style.color = color;
    node.textContent = text;
    notifications.appendChild(node);
    setTimeout(() => node.remove(), 1800);
  }

  function updateHUD(data) {
    const { me, state, pingMs, fps, serverPerf, renderScale } = data;
    const maxHp = me.maxHp || 100;
    const hp = Math.max(0, Math.min(maxHp, Math.round(me.hp)));
    document.getElementById('hpstat').textContent = `${hp}/${maxHp}`;
    document.getElementById('scorestat').textContent = me.score || 0;
    document.getElementById('killstat').textContent = me.kills || 0;
    document.getElementById('lvl').textContent = me.level || 1;
    document.getElementById('combo').textContent = me.combo > 1 ? `连杀 x${me.combo}` : '';
    document.getElementById('firecd').textContent = me.fireCd > 0 ? `${me.fireCd.toFixed(1)}s` : '就绪';
    const buffs = [];
    if (me.rapid) buffs.push('速射');
    if (me.spread) buffs.push('三连发');
    if (me.prot) buffs.push('护盾');
    document.getElementById('buffstat').textContent = buffs.length ? buffs.join(' / ') : '无';
    document.getElementById('wavestat').textContent = state.wave || 1;
    document.getElementById('zombiestat').textContent = state.zt ?? Object.keys(state.z).length;
    const obj = state.obj || {};
    const title = document.getElementById('objtitle');
    const stat = document.getElementById('objstat');
    const bar = document.getElementById('objbar');
    const story = document.getElementById('storyline');
    title.textContent = obj.title || '搜寻撤离点';
    title.style.color = obj.readyExits ? '#48f0a0' : obj.boss ? '#ff4d7a' : '#ff4d5f';
    stat.textContent = obj.text || `收集任务物，感染体 ${state.wr || 0} 只`;
    bar.style.width = `${Math.round(Math.max(0, Math.min(1, obj.progress || 0)) * 100)}%`;
    bar.style.background = obj.readyExits ? '#48f0a0' : obj.boss ? '#ff4d7a' : '#ff4d5f';
    story.textContent = obj.story || '耳机里只剩呼吸声。';
    deathOverlay.style.display = me.dead ? 'flex' : 'none';
    setPing(pingMs);

    const fpsEl = document.getElementById('fpsstat');
    fpsEl.textContent = Math.round(fps);
    fpsEl.style.color = fps >= 55 ? '#48f0a0' : fps >= 42 ? '#ffc247' : '#ff6666';
    const srvEl = document.getElementById('srvstat');
    if (serverPerf) {
      const slow = Math.max(serverPerf.tick_ms || 0, serverPerf.sync_ms || 0);
      srvEl.textContent = `${(serverPerf.tick_ms || 0).toFixed(1)}/${(serverPerf.sync_ms || 0).toFixed(1)}ms`;
      srvEl.style.color = slow < 8 ? '#48f0a0' : slow < 18 ? '#ffc247' : '#ff6666';
    }
    document.getElementById('entstat').textContent = `P${Object.keys(state.pl).length} Z${state.zt ?? Object.keys(state.z).length} B${state.bt ?? Object.keys(state.b).length} I${state.it ?? Object.keys(state.items).length}`;
    document.getElementById('renderstat').textContent = `${Math.round(renderScale * 100)}%`;

    const rows = state.lb && state.lb.length
      ? state.lb
      : Object.values(state.pl).sort((a, b) => (b.score || 0) - (a.score || 0)).slice(0, 8);
    const list = document.getElementById('slist');
    list.replaceChildren(...rows.map((p) => {
      const row = document.createElement('div');
      row.className = 'entry';
      const dot = document.createElement('span');
      dot.className = 'dot';
      dot.style.background = p.color || '#ffffff';
      const text = document.createTextNode(`${p.name || '幸存者'}: ${p.score || 0}`);
      row.append(dot, text);
      return row;
    }));
  }

  return {
    bindActions,
    notify,
    setJoinLoading,
    setNet,
    setPing,
    showGame,
    showJoin,
    updateHUD,
  };
}
