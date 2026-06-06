export function createUI() {
  const joinScreen = document.getElementById('join-screen');
  const joinBtn = document.getElementById('joinBtn');
  const restartBtn = document.getElementById('restartBtn');
  const restartStageBtn = document.getElementById('restartStageBtn');
  const hud = document.getElementById('hud');
  const waveInfo = document.getElementById('wave-info');
  const scoreboard = document.getElementById('scoreboard');
  const trainingPanel = document.getElementById('training-panel');
  const trainingSteps = document.getElementById('trainingSteps');
  const introGuide = document.getElementById('intro-guide');
  const introStartBtn = document.getElementById('introStartBtn');
  const audioBtn = document.getElementById('audioBtn');
  const deathOverlay = document.getElementById('death-overlay');
  const notifications = document.getElementById('notifications');
  const bagSummary = document.getElementById('bag-summary');
  const inventoryOverlay = document.getElementById('inventory-overlay');
  const inventoryCloseBtn = document.getElementById('inventoryCloseBtn');
  const intermissionOverlay = document.getElementById('intermission-overlay');
  const continueStageBtn = document.getElementById('continueStageBtn');
  const talentList = document.getElementById('talentList');
  let joinTimer = null;
  let intermissionFeedbackTimer = null;
  let intermissionTalentKey = '';
  const introKey = 'zombie-crisis-intro-seen-v1';
  const taskNames = { fuse: '保险丝', sample: '样本', keycard: '门禁卡', lore: '档案' };
  const ammoNames = {
    pistol: '手枪弹',
    rifle: '步枪弹',
    smg: '冲锋弹',
    shell: '霰弹',
    explosive: '爆破弹',
  };

  function ammoSummary(pools = {}) {
    return Object.keys(ammoNames)
      .map((key) => `${ammoNames[key]} ${Math.max(0, Math.round(pools[key] || 0))}`)
      .join(' · ');
  }

  function setJoinLoading(on) {
    joinBtn.disabled = on;
    joinBtn.textContent = on ? '加入中...' : '加入游戏';
    if (joinTimer) clearTimeout(joinTimer);
    joinTimer = on ? setTimeout(() => setJoinLoading(false), 8000) : null;
  }

  function bindActions(onJoin, onRestart, onRestartStage) {
    joinBtn.onclick = onJoin;
    restartBtn.onclick = onRestart;
    if (restartStageBtn) restartStageBtn.onclick = onRestartStage;
  }

  function bindAudioToggle(onToggle) {
    audioBtn.onclick = onToggle;
  }

  function bindInventory(onOpen, onClose) {
    if (bagSummary) {
      bagSummary.onclick = onOpen;
      bagSummary.onkeydown = (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onOpen();
        }
      };
    }
    if (inventoryCloseBtn) inventoryCloseBtn.onclick = onClose;
    if (inventoryOverlay) {
      inventoryOverlay.onclick = (event) => {
        if (event.target === inventoryOverlay) onClose();
      };
    }
  }

  function bindIntermission(onContinue, onBuyTalent) {
    if (continueStageBtn) continueStageBtn.onclick = onContinue;
    if (talentList) {
      talentList.onclick = (event) => {
        const button = event.target?.closest?.('button[data-talent]');
        if (!button || button.disabled) return;
        button.disabled = true;
        button.textContent = '升级中...';
        button.closest('.talent-row')?.classList.add('pending');
        onBuyTalent(button.dataset.talent);
      };
    }
  }

  function introSeen() {
    try {
      return window.localStorage.getItem(introKey) === '1';
    } catch (err) {
      return false;
    }
  }

  function setIntroSeen() {
    try {
      window.localStorage.setItem(introKey, '1');
    } catch (err) {
      // Local storage can be disabled; the guide still hides for this session.
    }
  }

  function bindIntroStart(onStart) {
    if (!introStartBtn) return;
    introStartBtn.onclick = () => {
      setIntroSeen();
      if (introGuide) introGuide.style.display = 'none';
      if (typeof onStart === 'function') onStart();
    };
  }

  function showIntroOnce() {
    if (!introGuide) return;
    introGuide.style.display = introSeen() ? 'none' : 'flex';
  }

  function showGame(name, color) {
    setJoinLoading(false);
    joinScreen.style.display = 'none';
    hud.style.display = 'block';
    waveInfo.style.display = 'block';
    scoreboard.style.display = 'block';
    trainingPanel.style.display = 'none';
    audioBtn.style.display = 'block';
    showIntroOnce();
    const pname = document.getElementById('pname');
    pname.textContent = name;
    pname.style.color = color;
  }

  function showJoin() {
    setJoinLoading(false);
    joinScreen.style.display = 'flex';
    trainingPanel.style.display = 'none';
    if (introGuide) introGuide.style.display = 'none';
    setInventoryOpen(false);
    setIntermission(null);
    audioBtn.style.display = 'none';
  }

  function setInventoryOpen(open) {
    if (!inventoryOverlay) return;
    inventoryOverlay.style.display = open ? 'flex' : 'none';
    inventoryOverlay.setAttribute('aria-hidden', open ? 'false' : 'true');
  }

  function setIntermission(data, me = {}) {
    if (!intermissionOverlay) return;
    const active = Boolean(data?.active);
    intermissionOverlay.style.display = active ? 'flex' : 'none';
    intermissionOverlay.setAttribute('aria-hidden', active ? 'false' : 'true');
    if (!active) {
      setIntermissionFeedback('');
      intermissionTalentKey = '';
      return;
    }

    const byId = (id) => document.getElementById(id);
    const cleared = data.clearedWave || 1;
    const next = data.nextWave || cleared + 1;
    const title = byId('intermissionTitle');
    const kicker = byId('intermissionKicker');
    const reward = byId('intermissionReward');
    const hook = byId('intermissionHook');
    const feedback = byId('intermissionFeedback');
    const bag = byId('intermissionBag');
    const bossText = data.nextBoss ? ` · 第 ${next} 关 Boss：${data.bossName || '黑墙巨像'}` : '';
    if (kicker) kicker.textContent = data.ending ? `第 ${cleared} 关主线结束` : `第 ${cleared} 关撤离成功`;
    if (title) title.textContent = data.ending ? data.endingTitle || '主线结局' : `整备第 ${next} 关`;
    if (reward)
      reward.textContent = data.ending
        ? data.endingText || '真相已经揭露，但设施还在继续下沉。'
        : `${data.rewardTitle || '路线奖励'}：${data.rewardText || '收益已结算。'}`;
    if (hook)
      hook.textContent = data.ending
        ? `主线已通关，可继续进入深层无尽模式。${bossText}`
        : `${data.routeHook || '无线电里传来新的坐标。'}${bossText}`;
    if (feedback && !feedback.dataset.locked)
      feedback.textContent = data.nextBoss && !data.ending ? '下一层会出现重型感染体，整备弹药和天赋。' : '';
    if (bag) {
      bag.textContent = `零件 ${Math.max(0, Math.round(me.materials || 0))} · 档案 ${Math.max(0, Math.round(me.lore || 0))} · ${ammoSummary(me.ammoPools)}`;
    }
    if (continueStageBtn)
      continueStageBtn.textContent = data.youReady
        ? data.ending
          ? '正在进入深层...'
          : '正在进入下一层...'
        : data.ending
          ? '继续深层无尽'
          : `进入第 ${next} 关`;

    const talents = Object.values(data.talents || {});
    const talentKey = JSON.stringify({
      materials: me.materials || 0,
      talents: talents.map((talent) => [talent.id, talent.level, talent.cost, talent.max]),
    });
    if (talentList && talentKey !== intermissionTalentKey) {
      intermissionTalentKey = talentKey;
      const nodes = talents.length
        ? talents.map((talent) => {
            const row = document.createElement('div');
            row.className = 'talent-row';
            const info = document.createElement('div');
            const name = document.createElement('b');
            name.textContent = `${talent.name} Lv.${talent.level}/${talent.max}`;
            const desc = document.createElement('span');
            const maxed = talent.level >= talent.max;
            desc.textContent = maxed ? `${talent.desc} · 已满级` : `${talent.desc} · 需要零件 ${talent.cost}`;
            info.append(name, desc);
            const button = document.createElement('button');
            button.type = 'button';
            button.dataset.talent = talent.id;
            button.textContent = maxed ? '满级' : `升级 ${talent.cost}`;
            button.disabled = maxed || (me.materials || 0) < talent.cost;
            row.append(info, button);
            return row;
          })
        : (() => {
            const row = document.createElement('div');
            row.className = 'intermission-note';
            row.textContent = '正在同步天赋数据...';
            return [row];
          })();
      talentList.replaceChildren(...nodes);
    }
  }

  function setIntermissionFeedback(text, color = '#48f0a0') {
    const feedback = document.getElementById('intermissionFeedback');
    if (!feedback) return;
    if (intermissionFeedbackTimer) clearTimeout(intermissionFeedbackTimer);
    feedback.dataset.locked = text ? '1' : '';
    feedback.textContent = text || '';
    feedback.style.color = color;
    if (text) {
      intermissionFeedbackTimer = setTimeout(() => {
        feedback.dataset.locked = '';
        feedback.textContent = '';
      }, 2200);
    }
  }

  function setAudioOn(on) {
    audioBtn.textContent = on ? '音频 开' : '音频 关';
    audioBtn.style.color = on ? '#48f0a0' : '#aeb7c2';
  }

  function setPing(ms) {
    const el = document.getElementById('pingstat');
    if (!el) return;
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

  function maxRequirements(exits) {
    const goals = { fuse: 0, sample: 0, keycard: 0, lore: 0 };
    for (const exit of exits || []) {
      const req = exit.requires || {};
      for (const typ of Object.keys(goals)) goals[typ] = Math.max(goals[typ], req[typ] || 0);
    }
    return goals;
  }

  function requirementText(req = {}, task = {}) {
    const parts = [];
    for (const typ of ['fuse', 'sample', 'keycard', 'lore']) {
      const need = req[typ] || 0;
      if (!need) continue;
      parts.push(`${taskNames[typ]} ${task[typ] || 0}/${need}`);
    }
    return parts.length ? parts.join(' · ') : '无需材料';
  }

  function renderTaskList(task, exits) {
    const goals = maxRequirements(exits);
    const nodes = ['fuse', 'sample', 'keycard', 'lore'].map((typ) => {
      const need = goals[typ] || 0;
      const have = task?.[typ] || 0;
      const node = document.createElement('div');
      node.className = 'taskpill';
      if (need && have >= need) node.style.borderColor = 'rgba(72,240,160,.55)';
      const title = document.createElement('b');
      title.textContent = taskNames[typ];
      const sub = document.createElement('span');
      sub.textContent = need ? `${have}/${need}` : `${have} 已取得`;
      node.append(title, sub);
      return node;
    });
    document.getElementById('tasklist').replaceChildren(...nodes);
  }

  function renderExitList(exits, task) {
    const all = exits || [];
    const visible = all.filter((exit) => exit.visible || exit.ready);
    const ready = all.filter((exit) => exit.ready);
    const list = ready.length ? ready : visible;
    if (!list.length) {
      const node = document.createElement('div');
      node.className = 'exitrow hidden';
      const title = document.createElement('b');
      title.textContent = `未知撤离终端 ${all.length || 3} 个`;
      const sub = document.createElement('span');
      sub.textContent = '先探索设施边缘，靠近后显示条件';
      node.append(title, sub);
      document.getElementById('exitlist').replaceChildren(node);
      return;
    }
    const nodes = list.slice(0, 3).map((exit, idx) => {
      const node = document.createElement('div');
      node.className = `exitrow ${exit.ready ? 'ready' : ''} ${exit.visible ? '' : 'hidden'}`;
      node.style.borderLeftColor = exit.ready ? '#48f0a0' : exit.color || '#ff4d5f';
      const title = document.createElement('b');
      title.textContent = `${exit.name || `撤离终端 ${idx + 1}`}${exit.ready ? ' 可撤离' : ''}`;
      const sub = document.createElement('span');
      const reward = exit.shortReward || exit.rewardTitle;
      sub.textContent = `${exit.ready ? '进入范围等待' : requirementText(exit.requires, task)}${reward ? ` · 奖励:${reward}` : ''}`;
      node.append(title, sub);
      return node;
    });
    document.getElementById('exitlist').replaceChildren(...nodes);
  }

  function updateTraining(training) {
    if (trainingSteps) trainingSteps.replaceChildren();
    trainingPanel.style.display = 'none';
  }

  function updateInventory(me, state, weaponTypes, weaponOrder) {
    const owned = new Set(me.weapons || ['pistol']);
    const order = weaponOrder.length ? weaponOrder : Array.from(owned);
    const maxHp = me.maxHp || 100;
    const hp = Math.max(0, Math.min(maxHp, Math.round(me.hp || 0)));
    const topValues = {
      invHp: `${hp}/${maxHp}`,
      invCurrentWeapon: me.weaponName || '手枪',
      invScore: me.score || 0,
      invKills: me.kills || 0,
    };
    for (const [id, value] of Object.entries(topValues)) {
      const node = document.getElementById(id);
      if (node) node.textContent = value;
    }
    const weaponNodes = order.map((id) => {
      const meta = weaponTypes[id] || {};
      const locked = !owned.has(id);
      const node = document.createElement('div');
      node.className = `inv-weapon ${id === me.weapon ? 'active' : ''} ${locked ? 'locked' : ''}`;
      const title = document.createElement('b');
      title.textContent = locked ? '未发现武器' : meta.name || id;
      const sub = document.createElement('span');
      if (locked) {
        sub.textContent = '探索仓库或安保路线解锁';
      } else if (id === me.weapon) {
        sub.textContent = `${me.ammo || 0}/${me.magSize || meta.mag_size || 0} · 当前装备`;
      } else {
        sub.textContent = `右键/QE 可切换`;
      }
      node.append(title, sub);
      return node;
    });
    const weaponList = document.getElementById('inventoryWeapons');
    if (weaponList) weaponList.replaceChildren(...weaponNodes);
    const task = state.obj?.task || {};
    const values = {
      invFuse: task.fuse || 0,
      invSample: task.sample || 0,
      invKeycard: task.keycard || 0,
      invParts: Math.max(0, Math.round(me.materials ?? 0)),
      invLore: Math.max(0, Math.round(me.lore ?? state.obj?.lore ?? 0)),
      invReserve: ammoSummary(me.ammoPools),
    };
    for (const [id, value] of Object.entries(values)) {
      const node = document.getElementById(id);
      if (node) node.textContent = value;
    }
    const objective = document.getElementById('inventoryObjective');
    if (objective) objective.textContent = state.obj?.text || '先搜任务物，再确认撤离终端条件。';
    const story = document.getElementById('inventoryStory');
    if (story) story.textContent = state.obj?.story || '耳机里只剩呼吸声。';
    const allExits = state.exits || [];
    const exitNodes = allExits.length
      ? allExits.map((exit, idx) => {
          const node = document.createElement('div');
          node.className = `inv-exit ${exit.ready ? 'ready' : ''}`;
          node.style.borderLeftColor = exit.ready
            ? '#48f0a0'
            : exit.visible
              ? exit.color || '#ff4d5f'
              : 'rgba(255,255,255,.2)';
          const title = document.createElement('b');
          title.textContent = exit.visible
            ? `${exit.name || `撤离终端 ${idx + 1}`}${exit.ready ? ' · 可撤离' : ''}`
            : `未知撤离终端 ${idx + 1}`;
          const sub = document.createElement('span');
          const reward = exit.shortReward || exit.rewardTitle;
          sub.textContent = exit.visible
            ? `${exit.ready ? '进入范围等待撤离' : requirementText(exit.requires || {}, state.obj?.task || {})}${reward ? ` · 奖励:${reward}` : ''}`
            : '靠近后显示条件';
          node.append(title, sub);
          return node;
        })
      : (() => {
          const node = document.createElement('div');
          node.className = 'inv-exit';
          const title = document.createElement('b');
          title.textContent = '暂无撤离数据';
          const sub = document.createElement('span');
          sub.textContent = '继续探索设施边缘';
          node.append(title, sub);
          return [node];
        })();
    const exits = document.getElementById('inventoryExits');
    if (exits) exits.replaceChildren(...exitNodes);
  }

  function updateHUD(data) {
    const { me, state, weaponTypes = {}, weaponOrder = [], pingMs, training } = data;
    setIntermission(state.intermission, me);
    const maxHp = me.maxHp || 100;
    const hp = Math.max(0, Math.min(maxHp, Math.round(me.hp)));
    document.getElementById('hpstat').textContent = `${hp}/${maxHp}`;
    document.getElementById('scorestat').textContent = me.score || 0;
    const killStat = document.getElementById('killstat');
    if (killStat) killStat.textContent = me.kills || 0;
    document.getElementById('lvl').textContent = me.level || 1;
    document.getElementById('combo').textContent = me.combo > 1 ? `连杀 x${me.combo}` : '';
    const ammo = Math.max(0, Math.round(me.ammo ?? 0));
    const magSize = Math.max(1, Math.round(me.magSize ?? 18));
    const reserve = Math.max(0, Math.round(me.currentReserve ?? 0));
    const ammoEl = document.getElementById('ammostat');
    ammoEl.textContent = `${ammo}/${magSize}`;
    ammoEl.style.color = ammo <= Math.max(3, magSize * 0.22) ? '#ff6666' : '#dce7f1';
    document.getElementById('reservestat').textContent = `${me.ammoTypeName || '备用弹'} ${reserve}`;
    document.getElementById('weaponname').textContent = me.weaponName || '手枪';
    const owned = new Set(me.weapons || ['pistol']);
    const order = weaponOrder.length ? weaponOrder : Array.from(owned);
    const weaponNodes = order.map((id) => {
      const node = document.createElement('div');
      const locked = !owned.has(id);
      node.className = `weaponchip ${id === me.weapon ? 'active' : ''} ${locked ? 'locked' : ''}`;
      node.textContent = locked ? '???' : weaponTypes[id]?.name || id;
      return node;
    });
    const belt = document.getElementById('weaponbelt');
    if (belt) belt.replaceChildren(...weaponNodes);
    const parts = Math.max(0, Math.round(me.materials ?? 0));
    const lore = Math.max(0, Math.round(me.lore ?? state.obj?.lore ?? 0));
    document.getElementById('weaponstat').textContent = Math.max(1, Math.round(me.weaponLevel ?? 1));
    const task = state.obj?.task || {};
    const bagCount = document.getElementById('bagcount');
    if (bagCount) {
      const total = (task.fuse || 0) + (task.sample || 0) + (task.keycard || 0) + parts + lore;
      bagCount.textContent = total > 99 ? '99+' : `${total}`;
      bagCount.style.display = total > 0 ? 'block' : 'none';
    }
    updateInventory(me, state, weaponTypes, weaponOrder);
    document.getElementById('wavestat').textContent = state.wave || 1;
    document.getElementById('zombiestat').textContent = state.zt ?? Object.keys(state.z).length;
    const obj = state.obj || {};
    const title = document.getElementById('objtitle');
    const stat = document.getElementById('objstat');
    const bar = document.getElementById('objbar');
    const story = document.getElementById('storyline');
    const inRoom = state.scene && state.scene !== 'main';
    title.textContent = inRoom ? `${state.sceneName || '设施'}内部` : obj.title || '搜寻撤离点';
    title.style.color = obj.readyExits ? '#48f0a0' : obj.boss ? '#ff4d7a' : '#ff4d5f';
    const sourceLeft = Math.max(0, Math.round(obj.infectionSource || 0));
    const sourceHint = sourceLeft > 0 ? ' · 感染源仍在活动' : '';
    stat.textContent = inRoom
      ? `${me.facilityStatus || '调查房间'} · 出口门返回走廊${sourceHint}`
      : `${obj.text || `收集任务物，感染体 ${state.wr || 0} 只`}${sourceHint}`;
    bar.style.width = `${Math.round(Math.max(0, Math.min(1, obj.progress || 0)) * 100)}%`;
    bar.style.background = obj.readyExits ? '#48f0a0' : obj.boss ? '#ff4d7a' : '#ff4d5f';
    renderTaskList(obj.task || {}, state.exits || []);
    renderExitList(state.exits || [], obj.task || {});
    const loreTotal = Math.max(1, obj.loreTotal || 6);
    document.getElementById('mysterylog').textContent =
      `档案 ${lore}/${loreTotal}${lore >= loreTotal ? ' · 真相已拼合' : ''}`;
    story.textContent = obj.story || '耳机里只剩呼吸声。';
    deathOverlay.style.display = me.dead ? 'flex' : 'none';
    if (me.dead) {
      const sub = deathOverlay.querySelector('.sub');
      const lives = Math.max(0, Math.round(me.lives ?? 0));
      const maxLives = Math.max(1, Math.round(me.maxLives ?? 3));
      if (sub) sub.textContent = lives > 0 ? `剩余部署 ${lives}/${maxLives}` : '部署耗尽，本关正在重开...';
    }
    const lifeNode = document.getElementById('livestat');
    if (lifeNode)
      lifeNode.textContent = `${Math.max(0, Math.round(me.lives ?? 3))}/${Math.max(1, Math.round(me.maxLives ?? 3))}`;
    updateTraining(training || {});
    setPing(pingMs);

    const rows =
      state.lb && state.lb.length
        ? state.lb
        : Object.values(state.pl)
            .sort((a, b) => (b.score || 0) - (a.score || 0))
            .slice(0, 8);
    const list = document.getElementById('slist');
    list.replaceChildren(
      ...rows.map((p) => {
        const row = document.createElement('div');
        row.className = 'entry';
        const dot = document.createElement('span');
        dot.className = 'dot';
        dot.style.background = p.color || '#ffffff';
        const text = document.createTextNode(`${p.name || '幸存者'}: ${p.score || 0}`);
        row.append(dot, text);
        return row;
      }),
    );
  }

  return {
    bindActions,
    bindAudioToggle,
    bindInventory,
    bindIntermission,
    bindIntroStart,
    notify,
    setAudioOn,
    setJoinLoading,
    setPing,
    setInventoryOpen,
    setIntermission,
    setIntermissionFeedback,
    showGame,
    showJoin,
    updateHUD,
  };
}
