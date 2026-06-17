// ═══ 华强卖瓜 v3 — 客户端 ═══════════════════════════════════════════════

const API = "/api";
let gameId = null, playerName = "";

// ─── Screens ─────────────────────────────────────────────────────────────────
function show(id) {
  const allScreens = document.querySelectorAll(".screen");
  allScreens.forEach(s => {
    if (s.id === id) {
      // 入屏: 设最高 z-index, 从透明过渡到不透明
      s.style.display = "flex";
      s.style.zIndex = "10";  // 确保覆盖其他 screen
      s.classList.remove("active");
      s.offsetHeight;  // 强制回流
      s.classList.add("active");
    } else if (s.classList.contains("active")) {
      // 出屏: 过渡到透明后隐藏
      s.classList.remove("active");
      s.style.zIndex = "1";
      const onEnd = () => {
        s.removeEventListener("transitionend", onEnd);
        if (!s.classList.contains("active")) {
          s.style.display = "none";
        }
      };
      s.addEventListener("transitionend", onEnd);
    }
  });
}

// ─── Audio Unlock ────────────────────────────────────────────────────────────
let audioUnlocked = false;
function unlockAudio() {
  if (audioUnlocked) return;
  // Play+ pause all audio elements to unlock them for future use
  document.querySelectorAll("audio").forEach(a => {
    a.muted = true;
    a.play().then(() => { a.pause(); a.currentTime = 0; a.muted = false; }).catch(() => {});
  });
  audioUnlocked = true;
}

// ─── Start ───────────────────────────────────────────────────────────────────
async function startGame() {
  unlockAudio();  // Unlock audio on user gesture
  playerName = document.getElementById("inp-name").value.trim() || "无名瓜摊";
  try {
    const res = await fetch(`${API}/game/new`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: playerName }),
    });
    if (!res.ok) throw new Error("创建失败");
    const game = await res.json();
    gameId = game.id;
    show("scr-game");
    updateStats(game);
    document.getElementById("result-overlay").classList.add("hidden");
    loadEvent();
  } catch (e) { alert("开摊失败: " + e.message); }
}

// ─── Transition ──────────────────────────────────────────────────────────────
async function showTransition(dayNum) {
  document.getElementById("trans-day").textContent = "第 " + dayNum + " 天";
  show("scr-transition");

  // 播放音频（不阻塞过渡）
  const audio = document.getElementById("audio-transition");
  if (audio) {
    audio.currentTime = 0;
    audio.play().catch(() => {});
  }

  // 固定2.5秒过渡动画
  await sleep(2500);
  show("scr-game");
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ─── Event ───────────────────────────────────────────────────────────────────
async function loadEvent() {
  document.getElementById("result-overlay").classList.add("hidden");
  // Animate dialog box out/in
  const dlg = document.getElementById("dialog-box");
  dlg.classList.add("fade-out");
  await sleep(300);

  try {
    // First check game state
    const gs = await fetch(`${API}/game/${gameId}`);
    if (gs.ok) {
      const g = await gs.json();
      updateStats(g);
      if (g.status !== "active") { showEnd(g); return; }
    }
    const res = await fetch(`${API}/game/${gameId}/event`);
    if (!res.ok) { const e = await res.json(); alert(e.detail); return; }
    const ev = await res.json();
    dlg.classList.remove("fade-out");
    renderEvent(ev);
  } catch (e) { alert("加载事件失败: " + e.message); }
}

function renderEvent(ev) {
  // 动态设置背景图, 缺失时使用fallback, with crossfade
  const imgEl = document.getElementById("img-bg");
  const newSrc = `/static/img/${ev.image}`;
  if (imgEl.src !== newSrc && !imgEl.src.endsWith("/static/img/" + ev.image)) {
    imgEl.classList.add("bg-crossfade");
    setTimeout(() => {
      imgEl.src = newSrc;
      imgEl.onerror = function() { this.src = "/static/img/bg_start.png"; };
      imgEl.classList.remove("bg-crossfade");
    }, 300);
  }

  document.getElementById("dlg-speaker").textContent = ev.speaker ? "— " + ev.speaker + " —" : "";
  document.getElementById("dlg-scene").textContent = "";
  document.getElementById("dlg-dialogue").textContent = "";
  document.getElementById("dlg-dayhint").textContent = ev.day_hint || "";

  // Typewriter: scene first, then dialogue
  typewriterSeq("dlg-scene", ev.scene, 25, () => {
    document.getElementById("dlg-dialogue").textContent = "「" + ev.dialogue + "」";
  });

  // Options
  const opts = document.getElementById("dlg-options");
  opts.innerHTML = "";
  ev.options.forEach((o, i) => {
    const btn = document.createElement("button");
    btn.className = "opt-btn";
    btn.innerHTML = `<span class="opt-num">${i + 1}</span>${o.text}`;
    btn.onclick = () => chooseOption(o.index);
    opts.appendChild(btn);
  });
}

function typewriterSeq(elId, text, speed, onDone) {
  const el = document.getElementById(elId);
  if (el._tw) clearInterval(el._tw);
  el.textContent = "";
  let i = 0;
  el._tw = setInterval(() => {
    el.textContent += text[i];
    i++;
    if (i >= text.length) { clearInterval(el._tw); el._tw = null; if (onDone) onDone(); }
  }, speed);
}

// ─── Action ──────────────────────────────────────────────────────────────────
async function chooseOption(idx) {
  document.querySelectorAll(".opt-btn").forEach(b => b.disabled = true);
  try {
    const res = await fetch(`${API}/game/${gameId}/action`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ option_idx: idx }),
    });
    if (!res.ok) {
      // Check if game is over
      const gs = await fetch(`${API}/game/${gameId}`);
      if (gs.ok) {
        const g = await gs.json();
        if (g.status !== "active") { showEnd(g); return; }
      }
      throw new Error("操作失败");
    }
    const data = await res.json();
    updateStats(data.game);
    showResult(data);
    // 成就弹窗
    if (data.new_achievements && data.new_achievements.length > 0) {
      data.new_achievements.forEach((a, i) => {
        setTimeout(() => showAchievementToast(a), i * 2800);
      });
      // If achievement modal is open, refresh it
      if (!document.getElementById("modal-achv").classList.contains("hidden")) {
        refreshAchievementsInGame(data.game.unlocked_achievements || []);
      }
    }
    if (data.is_game_over) {
      setTimeout(() => showEnd(data.game), 1500);
    }
  } catch (e) { alert("操作失败: " + e.message); loadEvent(); }
}

function showResult(data) {
  const overlay = document.getElementById("result-overlay");
  overlay.classList.remove("hidden");
  document.getElementById("result-text").textContent = data.result_text;
  const changes = document.getElementById("result-changes");
  changes.innerHTML = "";
  const labels = [["watermelons","西瓜"],["money","金钱"],["anger","怒气"],["police","警方"],["mind","心态"]];
  for (const [k, label] of labels) {
    const v = data.stat_changes[k];
    if (v && v !== 0) {
      const span = document.createElement("span");
      span.className = "r-change " + (v > 0 ? (k === "anger" ? "bad" : "good") : (k === "anger" ? "good" : "bad"));
      span.textContent = `${label} ${v > 0 ? "+" : ""}${v}`;
      changes.appendChild(span);
    }
  }
}

async function nextDay() {
  // 先隐藏结果浮层，否则会遮挡过渡画面 (z-index:20 > screen z-index:1)
  document.getElementById("result-overlay").classList.add("hidden");
  try {
    const res = await fetch(`${API}/game/${gameId}`);
    const game = await res.json();
    // 显示每日随机事件 (西瓜变动等)
    if (game.daily_msg) {
      document.getElementById("trans-sub").textContent = game.daily_msg;
    } else {
      document.getElementById("trans-sub").textContent = "新的一天开始了…";
    }
    await showTransition(game.day);
    loadEvent();
  } catch (e) { loadEvent(); }
}

// ─── Stats ───────────────────────────────────────────────────────────────────
function updateStats(game) {
  document.getElementById("s-day").textContent = game.day;
  document.getElementById("s-melon").textContent = game.watermelons;
  document.getElementById("s-money").textContent = game.money;
  const anger = document.getElementById("s-anger");
  anger.textContent = game.huaqiang_anger;
  anger.style.color = game.huaqiang_anger >= 70 ? "#c0392b" : game.huaqiang_anger >= 40 ? "#e67e22" : "";
  const police = document.getElementById("s-police");
  police.textContent = game.police_attention;
  police.style.color = game.police_attention >= 70 ? "#27ae60" : game.police_attention >= 40 ? "#2980b9" : "";
  const mind = document.getElementById("s-mind");
  mind.textContent = game.mentality;
  mind.style.color = game.mentality <= 30 ? "#c0392b" : "";
}

// ─── Settings ────────────────────────────────────────────────────────────────
function showSettings() {
  document.getElementById("modal-settings").classList.remove("hidden");
}

function closeSettings() {
  document.getElementById("modal-settings").classList.add("hidden");
}

// ─── Save / Load / Quit ──────────────────────────────────────────────────────
async function doSave() {
  if (!gameId || !playerName) { alert("没有可存档的游戏"); return; }
  // Fetch current saves to show slots
  try {
    const res = await fetch(`${API}/saves/${encodeURIComponent(playerName)}`);
    const saves = await res.json();
    const used = new Set(saves.map(s => s.slot));
    const slotsDiv = document.getElementById("save-slots");
    slotsDiv.innerHTML = [1,2,3,4,5].map(s => {
      const existing = saves.find(x => x.slot === s);
      return `<div class="save-slot save-slot-row" onclick="confirmSave(${s})">
        <span class="save-slot-num">${s}</span>
        <span class="save-slot-info">${existing ? `第${existing.day}天 (覆盖)` : "空槽位"}</span>
        ${existing ? `<span class="save-slot-date">${new Date(existing.saved_at).toLocaleString()}</span>` : ""}
      </div>`;
    }).join("");
    document.getElementById("modal-save").classList.remove("hidden");
  } catch (e) { alert("存档失败"); }
}

async function confirmSave(slot) {
  try {
    const res = await fetch(`${API}/save`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_name: playerName, slot }),
    });
    if (!res.ok) throw new Error("失败");
    document.getElementById("modal-save").classList.add("hidden");
    alert("存档成功！槽位 " + slot);
  } catch (e) { alert("存档失败: " + e.message); }
}

function closeSaveMenu() { document.getElementById("modal-save").classList.add("hidden"); }

async function showLoadMenu() {
  playerName = document.getElementById("inp-name").value.trim() || playerName || "无名瓜摊";
  try {
    const res = await fetch(`${API}/saves/${encodeURIComponent(playerName)}`);
    const saves = await res.json();
    const list = document.getElementById("load-list");
    if (!saves.length) {
      list.innerHTML = '<div style="text-align:center;color:#999;padding:20px">没有存档记录</div>';
    } else {
      list.innerHTML = saves.map(s => `
        <div class="save-slot save-slot-row" onclick="confirmLoad(${s.slot})">
          <span class="save-slot-num">${s.slot}</span>
          <span class="save-slot-info">第${s.day}天</span>
          <span class="save-slot-date">${new Date(s.saved_at).toLocaleString()}</span>
        </div>
      `).join("");
    }
    document.getElementById("modal-load").classList.remove("hidden");
  } catch (e) { alert("读取存档失败"); }
}

async function confirmLoad(slot) {
  try {
    const res = await fetch(`${API}/load`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_name: playerName, slot }),
    });
    if (!res.ok) throw new Error("失败");
    const game = await res.json();
    gameId = game.id;
    document.getElementById("modal-load").classList.add("hidden");
    show("scr-game");
    updateStats(game);
    document.getElementById("result-overlay").classList.add("hidden");
    await showTransition(game.day);
    loadEvent();
  } catch (e) { alert("读档失败: " + e.message); }
}

function closeLoadMenu() { document.getElementById("modal-load").classList.add("hidden"); }

async function doQuit() {
  if (!gameId || !playerName) return;
  if (!confirm("确定要收摊吗？当前进度将标记为主动退出。")) return;
  try {
    await fetch(`${API}/quit`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_name: playerName }),
    });
    gameId = null;
    show("scr-start");
  } catch (e) { alert("退出失败"); }
}

// ─── End ─────────────────────────────────────────────────────────────────────
function showEnd(game) {
  show("scr-end");
  const won = game.status === "won";
  document.getElementById("img-end").src = won ? "/static/img/bg_win.png" : "/static/img/bg_lose.png";
  document.getElementById("end-title").textContent = won ? "正义必胜" : "你没了";
  document.getElementById("end-title").style.color = won ? "#27ae60" : "#c0392b";
  document.getElementById("end-reason").textContent = game.lose_reason;
  document.getElementById("end-stats").innerHTML = [
    `<div class="tb-item">存活 ${game.day - 1} 天</div>`,
    `<div class="tb-item">剩瓜 ${game.watermelons}</div>`,
    `<div class="tb-item">余钱 ${game.money}</div>`,
  ].join("");

  // 播放结局音频
  const audioId = won ? "audio-win" : "audio-lose";
  const audio = document.getElementById(audioId);
  if (audio) {
    audio.currentTime = 0;
    audio.play().catch(() => {});
  }
}

function restartGame() { gameId = null; playerName = ""; show("scr-start"); }

// ─── Intro ───────────────────────────────────────────────────────────────────
async function showIntro() {
  const content = document.getElementById("intro-content");
  if (content.dataset.loaded !== "1") {
    try {
      const res = await fetch("/static/intro.txt");
      if (res.ok) {
        const text = await res.text();
        content.innerHTML = text.split("\n").filter(l => l.trim()).map(l => `<p>${l}</p>`).join("");
      } else {
        content.innerHTML = "<p>你是瓜摊老板。每天刘华强都会以不同方式出现。22个主题 × 5种变体 = 110套文案，25项成就等你解锁。目标：让警方关注度达到90——华强被捕，正义必胜！</p>";
      }
    } catch (e) {
      content.innerHTML = "<p>欢迎来到华强卖瓜。22个主题、110套文案、无数种结局——你在瓜摊上能活多少天？</p>";
    }
    content.dataset.loaded = "1";
  }
  document.getElementById("modal-intro").classList.remove("hidden");
}

function closeIntro() { document.getElementById("modal-intro").classList.add("hidden"); }

// ─── Leaderboard ─────────────────────────────────────────────────────────────
async function showLB() {
  document.getElementById("modal-lb").classList.remove("hidden");
  const list = document.getElementById("lb-list");
  list.innerHTML = '<div style="text-align:center;color:#999">加载中…</div>';
  try {
    const res = await fetch(`${API}/leaderboard`);
    const data = await res.json();
    if (!data.length) { list.innerHTML = '<div style="text-align:center;color:#999;padding:20px">还没有人留下传说</div>'; return; }
    list.innerHTML = data.map(r => `
      <div class="lb-row">
        <span class="lb-rank r${r.rank <= 3 ? r.rank : ""}">${r.rank <= 3 ? ["","I","II","III"][r.rank] : r.rank}</span>
        <span class="lb-name">${esc(r.player)}</span>
        <span class="lb-days">${r.days} 天</span>
        <span class="lb-status ${r.status === "won" ? "won" : "lost"}">${r.status === "won" ? "逮捕" : "阵亡"}</span>
      </div>
    `).join("");
  } catch (e) { list.innerHTML = '<div style="text-align:center;color:#999">加载失败</div>'; }
}

function closeLB() { document.getElementById("modal-lb").classList.add("hidden"); }

function toggleSettings() {
  const el = document.getElementById("start-settings");
  el.classList.toggle("hidden");
}

// ─── Achievements ────────────────────────────────────────────────────────────
const ALL_ACHV = {
  "day_1":    {id:1,  name:"初来乍到",   desc:"活过第1天",          icon:"🌅", group:"存活"},
  "day_7":    {id:2,  name:"一周瓜农",   desc:"存活7天",            icon:"📅", group:"存活"},
  "day_15":   {id:3,  name:"半月坚持",   desc:"存活15天",           icon:"📆", group:"存活"},
  "day_30":   {id:4,  name:"一月传奇",   desc:"存活30天",           icon:"🏆", group:"存活"},
  "quit":     {id:5,  name:"急流勇退",   desc:"主动收摊退出",        icon:"🚪", group:"存活"},
  "win":      {id:6,  name:"正义必胜",   desc:"警方抓捕华强(胜利)",   icon:"🚔", group:"结局"},
  "anger":    {id:7,  name:"怒火焚身",   desc:"死于华强刀下",        icon:"🔪", group:"结局"},
  "mind":     {id:8,  name:"心力交瘁",   desc:"心态崩溃",            icon:"💔", group:"结局"},
  "bankrupt": {id:9,  name:"破产清算",   desc:"金钱破产",            icon:"💸", group:"结局"},
  "no_wml":   {id:10, name:"弹尽粮绝",   desc:"瓜光钱光",            icon:"🫗", group:"结局"},
  "wml_50":   {id:11, name:"瓜满为患",   desc:"库存达到50个西瓜",     icon:"🍉", group:"西瓜"},
  "zero_live":{id:12, name:"绝处逢生",   desc:"西瓜归零后活过3天",    icon:"🌱", group:"西瓜"},
  "plaque":   {id:13, name:"童叟无欺",   desc:"华强为你题写匾额",     icon:"🖌️", group:"剧情"},
  "reconcile":{id:14, name:"和解协议",   desc:"与华强签署和解书",     icon:"🤝", group:"剧情"},
  "muse":     {id:15, name:"缪斯",       desc:"参加华强艺术回顾展",   icon:"🎨", group:"剧情"},
  "opera":    {id:16, name:"瓜摊恩仇录", desc:"华强原创黄梅戏",       icon:"🎭", group:"剧情"},
  "academic": {id:17, name:"学术尽头",   desc:"学术的尽头,是瓜摊",    icon:"📚", group:"剧情"},
  "no_more":  {id:18, name:"不再找茬",   desc:"华强收起秒表",         icon:"⏱️", group:"剧情"},
  "shinkai":  {id:19, name:"新海诚式告别",desc:"不说再见,只说路上吃",  icon:"🌈", group:"剧情"},
  "qiongyao": {id:20, name:"琼瑶对唱",   desc:"完成琼瑶式山歌对唱",   icon:"🎤", group:"剧情"},
  "real_one": {id:21, name:"真实的瓜",   desc:"无实物后一人一半真瓜",  icon:"🍈", group:"剧情"},
  "disband":  {id:22, name:"卧底解散",   desc:"黑衣组织因天热解散",   icon:"🕶️", group:"剧情"},
  "seen_all": {id:23, name:"见多识广",   desc:"触发全部22种事件",     icon:"👁️", group:"收集"},
  "all_variant":{id:24,name:"千面华强",  desc:"某事件5变体全见过",    icon:"🎭", group:"收集"},
  "seen_10":  {id:25, name:"十全十美",   desc:"触发10种不同事件",     icon:"✨", group:"收集"},
};

function renderAchievementList(unlocked) {
  const list = document.getElementById("achv-list");
  const groups = {};
  for (const [k, v] of Object.entries(ALL_ACHV)) {
    if (!groups[v.group]) groups[v.group] = [];
    v.key = k;
    v.unlocked = unlocked.includes(k);
    groups[v.group].push(v);
  }
  const total = Object.keys(ALL_ACHV).length;
  const unlockedCount = unlocked.length;
  const pct = total > 0 ? Math.round(unlockedCount / total * 100) : 0;
  list.innerHTML = `
    <div style="text-align:center;margin-bottom:12px;color:#d4a017;font-weight:bold">
      🏆 ${unlockedCount} / ${total} 已解锁 (${pct}%)
    </div>
    ${unlockedCount > 0 ? `<div style="text-align:center;margin-bottom:12px;font-size:12px;color:#999">进度条</div>
    <div style="width:100%;height:8px;background:#333;border-radius:4px;margin-bottom:16px;overflow:hidden">
      <div style="width:${pct}%;height:100%;background:linear-gradient(90deg,#d4a017,#f0c040);border-radius:4px;transition:width .5s ease"></div>
    </div>` : ""}
    ${Object.entries(groups).map(([g, items]) => `
      <div class="achv-group">
        <div class="achv-group-title">${g}</div>
        ${items.map(a => `
          <div class="achv-item ${a.unlocked ? '' : 'locked'}">
            <span class="achv-item-icon">${a.unlocked ? a.icon : '🔒'}</span>
            <span class="achv-item-name">${a.unlocked ? esc(a.name) : '???'}</span>
            <span class="achv-item-desc">${a.unlocked ? esc(a.desc) : '达成条件隐藏'}</span>
          </div>
        `).join("")}
      </div>
    `).join("")}
  `;
}

// ─── Start-page achievements (works with or without name) ────────────────────
async function showAchievementsStart() {
  const name = document.getElementById("inp-name").value.trim();
  document.getElementById("modal-achv").classList.remove("hidden");
  const list = document.getElementById("achv-list");

  if (!name) {
    // No name entered — show all achievements as locked
    renderAchievementList([]);
    return;
  }

  list.innerHTML = '<div style="text-align:center;color:#999;padding:20px">加载中…</div>';
  try {
    const res = await fetch(`${API}/achievements/${encodeURIComponent(name)}`);
    const data = await res.json();
    renderAchievementList(data.unlocked_achievements || []);
  } catch (e) { list.innerHTML = '<div style="text-align:center;color:#999">加载失败</div>'; }
}

// ─── In-game achievements (fetches via game state) ───────────────────────────
async function showAchievements() {
  if (!gameId) {
    // No game active — try with player name
    return showAchievementsStart();
  }
  document.getElementById("modal-achv").classList.remove("hidden");
  const list = document.getElementById("achv-list");
  list.innerHTML = '<div style="text-align:center;color:#999;padding:20px">加载中…</div>';
  try {
    const res = await fetch(`${API}/game/${gameId}`);
    const game = await res.json();
    renderAchievementList(game.unlocked_achievements || []);
  } catch (e) { list.innerHTML = '<div style="text-align:center;color:#999">加载失败</div>'; }
}

// Refresh achievement list in-place (called after new achievement unlocked)
function refreshAchievementsInGame(unlocked) {
  renderAchievementList(unlocked || []);
}

function closeAchievements() { document.getElementById("modal-achv").classList.add("hidden"); }

// ─── History ─────────────────────────────────────────────────────────────────
async function showHistory() {
  if (!gameId) { alert("没有进行中的游戏"); return; }
  document.getElementById("modal-history").classList.remove("hidden");
  const content = document.getElementById("history-content");
  content.innerHTML = '<div style="text-align:center;color:#999;padding:20px">加载中…</div>';
  try {
    const res = await fetch(`${API}/game/${gameId}/history?limit=100`);
    const data = await res.json();
    if (!data.length) { content.innerHTML = '<div style="text-align:center;color:#999;padding:20px">还没有记录</div>'; return; }
    content.innerHTML = data.map((h, i) => `
      <div style="padding:10px 0;border-bottom:1px solid #eee;font-size:13px;line-height:1.8">
        <b style="color:#c0392b">第${h.day}天</b> · ${esc(h.event_title)}<br>
        <span style="color:#555">${esc(h.event_scene).substring(0, 80)}…</span><br>
        <span style="color:#e67e22">→ ${esc(h.chosen_option_text)}</span>
      </div>
    `).join("");
  } catch (e) { content.innerHTML = '<div style="text-align:center;color:#999">加载失败</div>'; }
}

function closeHistory() { document.getElementById("modal-history").classList.add("hidden"); }

// ─── Keyboard ────────────────────────────────────────────────────────────────
document.addEventListener("keydown", e => {
  if (e.key === "Enter" && !document.getElementById("result-overlay").classList.contains("hidden")) {
    e.preventDefault(); nextDay();
  }
  const opts = document.querySelectorAll(".opt-btn");
  if (opts.length && !opts[0].disabled && document.getElementById("result-overlay").classList.contains("hidden")) {
    const idx = parseInt(e.key) - 1;
    if (idx >= 0 && idx < opts.length) { e.preventDefault(); opts[idx].click(); }
  }
  // Escape to close modals
  if (e.key === "Escape") {
    document.querySelectorAll(".modal").forEach(m => m.classList.add("hidden"));
  }
});

document.getElementById("inp-name").addEventListener("keydown", e => {
  if (e.key === "Enter") { e.preventDefault(); startGame(); }
});

function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

// ─── Achievement Toast (Steam-style, bottom-right) ────────────────────────────
function showAchievementToast(a) {
  const toast = document.createElement("div");
  toast.className = "achv-toast";
  toast.innerHTML = `
    <div class="achv-toast-icon">${a.icon}</div>
    <div class="achv-toast-body">
      <div class="achv-toast-label">成就解锁</div>
      <div class="achv-toast-name">${esc(a.name)}</div>
      <div class="achv-toast-desc">${esc(a.desc)}</div>
    </div>
  `;
  document.body.appendChild(toast);
  // Animate in
  requestAnimationFrame(() => {
    toast.classList.add("show");
  });
  // Remove after 5s
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 500);
  }, 5000);
}
