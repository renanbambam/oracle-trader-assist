// Oracle Trader Assist — Frontend

const API_BASE = '';
const WS_URL   = `ws://${location.host}/ws`;

const state = {
  page: 'analysis',
  ws: null,
  trades: [],
  quotes: [],
  tradeFilter: 'all',
  _wsRetry: 0,
  replaySessionId: null,
  _chatFile: null,
  _chatStreamBubble: null,
  lastAnalysisId: null,
  _replayAwaitingFrame: false,
  _replayCandles: [],
  _lastReplayBar: null,
};

// ── Page pollers ──────────────────────────────────────────────────────────────

let _pagePoller  = null;
let _replayChart  = null;
let _replaySeries = null;

function _clearPagePoller() {
  if (_pagePoller) { clearInterval(_pagePoller); _pagePoller = null; }
}

async function pollLatestAnalysis() {
  if (!state.lastAnalysisId) return;
  try { renderAnalysis(await api('GET', `/api/v1/analyses/${state.lastAnalysisId}`)); } catch { /* silent */ }
}

// ── Utilities ────────────────────────────────────────────────────────────────

async function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  const res = await fetch(API_BASE + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

const el   = id => document.getElementById(id);
const fmt  = (n, d = 2) => (n == null ? '—' : Number(n).toFixed(d));
const fmtD = iso => iso ? new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—';

function escapeHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Clock ────────────────────────────────────────────────────────────────────

function tick() {
  el('clock').textContent = new Date().toLocaleTimeString('pt-BR');
}

// ── Navigation ───────────────────────────────────────────────────────────────

const PAGE_CONFIG = {
  analysis: { title:'Análise Técnica',       sym:'',        tf:'',          extra:'' },
  chat:     { title:'Chat — Oracle AI',       sym:'',        tf:'Claude',    extra:'Online' },
  trades:   { title:'Histórico de Trades',    sym:'',        tf:'',          extra:'' },
  market:   { title:'Mercado ao Vivo',        sym:'',        tf:'',          extra:'' },
  perf:     { title:'Performance',            sym:'30 dias', tf:'',          extra:'' },
  briefing: { title:'Briefing Matinal',       sym:'',        tf:'Oracle AI', extra:'' },
  checklist:{ title:'Checklist Pré-Trade',    sym:'',        tf:'',          extra:'Anti-FOMO' },
  replay:   { title:'Replay Histórico',       sym:'',        tf:'',          extra:'' },
  config:   { title:'Configurações',          sym:'Sistema', tf:'v1.0',      extra:'Fase 1' },
};

function navTo(page, btn) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('on'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('on'));

  const pg = el(`pg-${page}`);
  if (pg) pg.classList.add('on');
  btn?.classList.add('on');

  const cfg = PAGE_CONFIG[page] || { title: page };
  el('page-title').textContent = cfg.title;

  const symEl   = el('topbar-sym');
  const tfEl    = el('topbar-tf');
  const extraEl = el('topbar-extra');
  symEl.textContent   = cfg.sym;   symEl.style.display   = cfg.sym   ? '' : 'none';
  tfEl.textContent    = cfg.tf;    tfEl.style.display    = cfg.tf    ? '' : 'none';
  extraEl.textContent = cfg.extra; extraEl.style.display = cfg.extra ? '' : 'none';

  state.page = page;
  if (pg) pg.scrollTop = 0;

  _clearPagePoller();

  if (page === 'trades')    { loadTrades();  _pagePoller = setInterval(loadTrades, 5_000); }
  if (page === 'checklist') updateFomoCount();
  if (page === 'briefing' && localStorage.getItem('feature_autobriefing') !== 'false') loadBriefing();
  if (page === 'replay')    loadReplay();
  if (page === 'perf')      { loadPerf();    _pagePoller = setInterval(loadPerf, 10_000); }
  if (page === 'analysis')  { _pagePoller = setInterval(pollLatestAnalysis, 5_000); }
  if (page === 'market') {
    highlightSessions();
    loadQuotes();
    loadMacroCalendar();
    const selCard = document.querySelector('.mkt-card.sel') || el('mkt-PETR4');
    const initSym = selCard?.id?.replace('mkt-', '') || 'PETR4';
    selectMktAsset(initSym, selCard);
  }
  if (page === 'config')    syncConfigStatus();

  if (page === 'chat') {
    const ts = el('chat-init-ts');
    if (ts && !ts.textContent) ts.textContent = new Date().toLocaleTimeString('pt-BR', { hour12: false });
  }
}

// ── WebSocket ────────────────────────────────────────────────────────────────

function connectWS() {
  const ws = new WebSocket(WS_URL);
  state.ws = ws;

  ws.onopen = () => {
    state._wsRetry = 0;
    setDot('ws', 'ok', 'online');
    ws.send(JSON.stringify({ action: 'subscribe', channels: ['analysis','trading','system','market','replay','ai_stream'] }));
  };

  ws.onmessage = e => {
    try { onWsEvent(JSON.parse(e.data)); } catch { /* ignore */ }
  };

  ws.onclose = () => {
    setDot('ws', 'err', 'offline');
    const delay = Math.min(1000 * (2 ** state._wsRetry++), 30000);
    setTimeout(connectWS, delay);
  };

  ws.onerror = () => ws.close();
}

function onWsEvent({ event, payload = {} }) {
  if (!event) return;

  if (event === 'analysis.completed') {
    toast(`Análise: ${payload.asset || ''} — ${payload.suggestion || ''}`);
    if (state.page === 'analysis') loadAnalysis(payload.analysis_id);
  }

  if (event === 'trade.opened' || event === 'trade.closed') {
    if (state.page === 'trades') loadTrades();
  }

  if (event === 'market.ticker_updated' && payload.symbol && payload.price) {
    const sym      = payload.symbol;
    const wsPrice  = formatPrice(sym, payload.price);
    const wsPos    = (payload.change || 0) >= 0;
    const wsChgTxt = `${wsPos ? '▲ +' : '▼ '}${fmt(payload.change || 0, 2)}%`;

    document.querySelectorAll('.tick-item').forEach(item => {
      if (item.querySelector('.tick-sym')?.textContent.trim() === sym) {
        const pEl = item.querySelector('.tick-p');
        if (pEl) { pEl.textContent = wsPrice; pEl.className = `tick-p ${wsPos ? 'pos' : 'neg'}`; }
      }
    });

    const mktP   = el(`mkt-p-${sym}`);
    const mktChg = el(`mkt-chg-${sym}`);
    if (mktP) mktP.textContent = wsPrice;
    if (mktChg && payload.change != null) {
      mktChg.textContent = wsChgTxt;
      mktChg.className = `mkt-chg ${wsPos ? 'pos' : 'neg'}`;
    }

    el('mt5-sym').textContent   = sym;
    el('mt5-price').textContent = wsPrice;
    if (payload.change != null) {
      const chgEl = el('mt5-chg');
      chgEl.textContent = wsChgTxt;
      chgEl.className = `mt5-chg ${wsPos ? 'pos' : 'neg'}`;
      const p = payload.price;
      const spd = p * 0.0002;
      el('mt5-bid').textContent = fmt(p - spd / 2, 5);
      el('mt5-ask').textContent = fmt(p + spd / 2, 5);
      el('mt5-spd').textContent = fmt(spd * 10000, 1);
    }
  }

  if (event === 'replay.frame_advanced' && state.page === 'replay') {
    state._replayAwaitingFrame = false;
    renderReplayFrame(payload);
  }

  if (event === 'replay.completed' && state.page === 'replay') {
    toast('Replay concluído!');
    const nb = el('btn-rp-next'); const fb = el('btn-rp-finish');
    if (nb) nb.disabled = true;
    if (fb) fb.disabled = true;
  }

  if (event === 'ai.token' && state._chatStreamBubble) {
    state._chatStreamBubble.textContent += payload.token || '';
    const area = el('chat-area');
    if (area) area.scrollTop = area.scrollHeight;
  }

  if (event === 'ai.stream_end') {
    state._chatStreamBubble = null;
  }
}

// ── Status dots ──────────────────────────────────────────────────────────────

function setDot(name, cls, text) {
  const clsStr = `sys-dot ${cls}`;
  const pairs = [
    [el(`dot-${name}`),     el(`status-${name}`)],
    [el(`cfg-dot-${name}`), el(`cfg-status-${name}`)],
  ];
  const color = cls === 'ok' ? 'var(--green)' : cls === 'warn' ? 'var(--am)' : 'var(--red)';
  for (const [d, s] of pairs) {
    if (d) d.className = clsStr;
    if (s) { s.textContent = text; s.style.color = color; }
  }
}

// ── Health check ─────────────────────────────────────────────────────────────

async function checkHealth() {
  try {
    const data = await api('GET', '/api/v1/health');
    setDot('api', data.status === 'ok' ? 'ok' : 'warn', data.status || '—');
    setDot('db',  data.database === 'ok' ? 'ok' : 'warn', data.database || 'ok');
    const badge = el('claude-badge');
    if (badge) { badge.textContent = '● CLAUDE ONLINE'; badge.className = 'badge badge-g'; }
  } catch {
    setDot('api', 'err', 'offline');
    setDot('db',  'err', 'offline');
    const badge = el('claude-badge');
    if (badge) { badge.textContent = '● CLAUDE OFFLINE'; badge.className = 'badge badge-r'; }
  }
}

function syncConfigStatus() {
  for (const k of ['api', 'ws', 'db']) {
    const dot = el(`dot-${k}`); const status = el(`status-${k}`);
    const cfgDot = el(`cfg-dot-${k}`); const cfgSt = el(`cfg-status-${k}`);
    if (dot && cfgDot) cfgDot.className = dot.className;
    if (status && cfgSt) { cfgSt.textContent = status.textContent; cfgSt.style.color = status.style.color; }
  }
}

// ── Analysis ─────────────────────────────────────────────────────────────────

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload  = () => resolve(r.result.split(',')[1]);
    r.onerror = reject;
    r.readAsDataURL(file);
  });
}


function setTF(tf, tabEl) {
  const sel = el('inp-tf');
  if (sel) sel.value = tf;
  document.querySelectorAll('#pg-analysis .tf-tab').forEach(t => t.classList.remove('on'));
  tabEl?.classList.add('on');
}

async function runAnalysis() {
  const btn = el('btn-analyze');
  btn.disabled = true; btn.textContent = '⏳ Analisando...';
  try {
    const body = {
      asset:     (el('inp-asset').value.trim() || 'PETR4').toUpperCase(),
      timeframe: el('inp-tf').value,
      notes:     el('inp-notes').value.trim() || null,
    };
    const result = await api('POST', '/api/v1/analyses', body);
    renderAnalysis(result);
    el('last-analysis-ts').textContent = fmtD(result.created_at);
  } catch (e) {
    toast(`Erro: ${e.message}`, 'err');
  } finally {
    btn.disabled = false; btn.textContent = '▶ Analisar Setup';
  }
}

async function loadAnalysis(id) {
  try { renderAnalysis(await api('GET', `/api/v1/analyses/${id}`)); } catch { /* ignore */ }
}

function renderAnalysis(a) {
  if (a.analysis_id) state.lastAnalysisId = a.analysis_id;
  const score = Math.round((a.confidence_score || 0) * 100);
  const circ  = 289;
  const fill  = el('cring-fill');
  if (fill) {
    const c = score >= 70 ? 'var(--green)' : score >= 50 ? 'var(--am)' : 'var(--red)';
    fill.setAttribute('stroke', c);
    fill.setAttribute('stroke-dashoffset', circ - circ * score / 100);
  }
  el('cring-num').textContent = score;

  const sug = (a.suggestion || 'AGUARDAR').toUpperCase();
  const pillMap = {
    OPERAR:           ['pill-op',     '▲ OPERAR'],
    AGUARDAR:         ['pill-wait',   '◌ AGUARDAR'],
    NAO_OPERAR:       ['pill-avoid',  '✕ NÃO OPERAR'],
    REVISAR_CONTEXTO: ['pill-review', '⊙ REVISAR'],
  };
  const [pillCls, pillLabel] = pillMap[sug] || ['pill-wait', '◌ AGUARDAR'];
  el('pill-wrap').innerHTML = `<span class="suggestion-pill ${pillCls}">${pillLabel}</span>`;

  const trendBadge = el('trend-badge');
  if (a.trend_direction && trendBadge) {
    trendBadge.style.display = '';
    trendBadge.className = `badge ${a.trend_direction === 'BULLISH' ? 'badge-g' : a.trend_direction === 'BEARISH' ? 'badge-r' : 'badge-am'}`;
    trendBadge.textContent = a.trend_direction;
  }

  const setupWrap = el('setup-grid-wrap');
  if (setupWrap) {
    setupWrap.style.display = '';
    el('setup-support').textContent    = a.support_level    ? fmt(a.support_level)    : '—';
    el('setup-resistance').textContent = a.resistance_level ? fmt(a.resistance_level) : '—';
    el('setup-trend').textContent      = a.trend_direction  || '—';
    el('setup-strength').textContent   = a.trend_strength   || '—';
  }

  const reasonCard = el('reasoning-card');
  if (reasonCard) reasonCard.style.display = '';

  const rWrap = el('reasoning-wrap');
  if (a.reasoning) { rWrap.style.display = 'block'; rWrap.textContent = a.reasoning; }

  const risksWrap = el('risks-wrap');
  if (a.risks?.length) {
    risksWrap.innerHTML = a.risks.map(r =>
      `<div class="reason-item"><span class="ri-icon ri-warn">⚠</span><span>${escapeHtml(r)}</span></div>`
    ).join('');
  }

  const scenWrap = el('scenarios-wrap');
  if (scenWrap && (a.bull_scenario || a.bear_scenario)) {
    scenWrap.style.display = '';
    el('bull-wrap').innerHTML = a.bull_scenario
      ? `<div class="scenario-label g">▲ Cenário Bullish</div><div class="scenario-text">${escapeHtml(a.bull_scenario)}</div>` : '';
    el('bear-wrap').innerHTML = a.bear_scenario
      ? `<div class="scenario-label r">▼ Cenário Bearish</div><div class="scenario-text">${escapeHtml(a.bear_scenario)}</div>` : '';
  }

  const idBadge = el('analysis-id-badge');
  if (idBadge) idBadge.textContent = a.analysis_id ? String(a.analysis_id).slice(0, 8) : '—';

  const symEl   = el('topbar-sym');
  const tfEl    = el('topbar-tf');
  if (symEl && a.asset)     { symEl.textContent = a.asset;     symEl.style.display = ''; }
  if (tfEl  && a.timeframe) { tfEl.textContent  = a.timeframe; tfEl.style.display  = ''; }
}

// ── Chat ─────────────────────────────────────────────────────────────────────

function onChatFileChange(inp) {
  state._chatFile = inp.files?.[0] || null;
  if (state._chatFile) toast(`Imagem: ${state._chatFile.name}`);
  inp.value = '';
}

function chatQuick(msg) {
  const inp = el('chat-input');
  if (inp) { inp.value = msg; inp.focus(); }
  sendChatMsg();
}

async function sendChatMsg() {
  const inp  = el('chat-input');
  const area = el('chat-area');
  const msg  = inp?.value.trim();
  if (!msg || !area) return;

  inp.value = '';
  inp.style.height = '';

  const userBubble = document.createElement('div');
  userBubble.className = 'msg msg-user';
  userBubble.innerHTML = `
    <div class="msg-name" style="color:var(--t4)">você</div>
    <div class="msg-bubble user-bubble">${escapeHtml(msg)}</div>
    <div class="msg-meta">${new Date().toLocaleTimeString('pt-BR',{hour12:false})}</div>`;
  area.appendChild(userBubble);
  area.scrollTop = area.scrollHeight;

  // Streaming path — WS connected and no image attached
  const wsReady = state.ws?.readyState === WebSocket.OPEN;
  if (wsReady && !state._chatFile) {
    const streamBubble = document.createElement('div');
    streamBubble.className = 'msg msg-jarvis';
    const streamContent = document.createElement('div');
    streamContent.className = 'msg-bubble jarvis-bubble';
    streamContent.style.whiteSpace = 'pre-wrap';
    streamBubble.innerHTML = '<div class="msg-name">ORACLE</div>';
    streamBubble.appendChild(streamContent);
    area.appendChild(streamBubble);
    area.scrollTop = area.scrollHeight;
    state._chatStreamBubble = streamContent;

    try {
      await api('POST', '/api/v1/chat', { message: msg });
      return; // tokens arrive via WS ai.token; ai.stream_end finalizes
    } catch (_e) {
      // Streaming endpoint unavailable — fall back
      state._chatStreamBubble = null;
      streamBubble.remove();
    }
  }

  // Fallback path — analyses endpoint (also used when image is attached)
  const typing = document.createElement('div');
  typing.className = 'msg msg-jarvis';
  typing.id = 'chat-typing';
  typing.innerHTML = `<div class="msg-name">ORACLE</div>
    <div class="msg-bubble jarvis-bubble">
      <div class="typing-anim"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>
    </div>`;
  area.appendChild(typing);
  area.scrollTop = area.scrollHeight;

  try {
    const assetMatch = msg.match(/\b([A-Z]{3,6}[0-9]?)\b/);
    const asset = assetMatch ? assetMatch[1] : (el('inp-asset')?.value || 'PETR4').toUpperCase();

    let screenshot_b64 = null;
    if (state._chatFile) {
      screenshot_b64 = await readFileAsBase64(state._chatFile);
      state._chatFile = null;
    }

    const result = await api('POST', '/api/v1/analyses', {
      asset,
      timeframe: el('inp-tf')?.value || 'H1',
      notes: msg,
      screenshot_b64,
    });

    el('chat-typing')?.remove();

    const score = Math.round((result.confidence_score || 0) * 100);
    const sug   = (result.suggestion || 'AGUARDAR').toUpperCase();
    const pillLabels = { OPERAR:'▲ OPERAR', AGUARDAR:'◌ AGUARDAR', NAO_OPERAR:'✕ NÃO OPERAR', REVISAR_CONTEXTO:'⊙ REVISAR' };

    const resp = document.createElement('div');
    resp.className = 'msg msg-jarvis';
    resp.innerHTML = `
      <div class="msg-name">ORACLE</div>
      <div class="msg-bubble jarvis-bubble">
        <div style="margin-bottom:8px"><strong>${escapeHtml(result.asset)} · ${result.timeframe}</strong></div>
        ${result.reasoning ? `<p style="margin-bottom:8px;font-size:12px;line-height:1.65;color:var(--t2)">${escapeHtml(result.reasoning)}</p>` : ''}
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">
          <span class="badge badge-s">${pillLabels[sug] || sug}</span>
          <span class="badge badge-s">Conf: ${score}%</span>
          ${result.trend_direction ? `<span class="badge badge-s">${result.trend_direction}</span>` : ''}
        </div>
        ${result.bull_scenario ? `<div style="margin-top:8px;font-size:11px;color:var(--green)">▲ ${escapeHtml(result.bull_scenario)}</div>` : ''}
        ${result.bear_scenario ? `<div style="margin-top:4px;font-size:11px;color:var(--red)">▼ ${escapeHtml(result.bear_scenario)}</div>` : ''}
      </div>
      <div class="msg-meta">${new Date().toLocaleTimeString('pt-BR',{hour12:false})} · Oracle AI</div>`;
    area.appendChild(resp);
    area.scrollTop = area.scrollHeight;

  } catch (e) {
    el('chat-typing')?.remove();
    const errResp = document.createElement('div');
    errResp.className = 'msg msg-jarvis';
    errResp.innerHTML = `
      <div class="msg-name">ORACLE</div>
      <div class="msg-bubble jarvis-bubble" style="color:var(--red)">Erro: ${escapeHtml(e.message)}</div>
      <div class="msg-meta">${new Date().toLocaleTimeString('pt-BR',{hour12:false})}</div>`;
    area.appendChild(errResp);
    area.scrollTop = area.scrollHeight;
  }
}

// ── Market ───────────────────────────────────────────────────────────────────

function formatPrice(sym, price) {
  const s = sym.toUpperCase();
  if (['EURUSD'].includes(s))          return fmt(price, 5);
  if (['USDJPY'].includes(s))          return fmt(price, 3);
  if (['XAUUSD', 'US100'].includes(s)) return fmt(price, 2);
  if (['IBOV', 'WINQ', 'WINFUT'].includes(s)) return Math.round(price).toLocaleString('pt-BR');
  return fmt(price, 2);
}

async function loadQuotes() {
  try {
    const quotes = await api('GET', '/api/v1/market/quotes');
    if (!Array.isArray(quotes)) return;
    state.quotes = quotes;

    for (const q of quotes) {
      const sym = q.symbol;
      const pos = q.change_pct >= 0;
      const chgText = `${pos ? '▲ +' : '▼ '}${fmt(q.change_pct, 2)}%`;
      const priceStr = formatPrice(sym, q.price);

      document.querySelectorAll('.tick-item').forEach(item => {
        if (item.querySelector('.tick-sym')?.textContent.trim() === sym) {
          const pEl = item.querySelector('.tick-p');
          if (pEl) { pEl.textContent = priceStr; pEl.className = `tick-p ${pos ? 'pos' : 'neg'}`; }
        }
      });

      const mktP   = el(`mkt-p-${sym}`);
      const mktChg = el(`mkt-chg-${sym}`);
      if (mktP) mktP.textContent = priceStr;
      if (mktChg) { mktChg.textContent = chgText; mktChg.className = `mkt-chg ${pos ? 'pos' : 'neg'}`; }
    }


    // Populate sidebar market widget with first available quote
    const featured = quotes.find(q => q.symbol === 'PETR4') || quotes[0];
    if (featured) {
      const pos = featured.change_pct >= 0;
      el('mt5-sym').textContent   = featured.symbol;
      el('mt5-price').textContent = formatPrice(featured.symbol, featured.price);
      const chgEl = el('mt5-chg');
      chgEl.textContent = `${pos ? '▲ +' : '▼ '}${fmt(featured.change_pct, 2)}%`;
      chgEl.className   = `mt5-chg ${pos ? 'pos' : 'neg'}`;
      el('mt5-bid').textContent = formatPrice(featured.symbol, featured.bid);
      el('mt5-ask').textContent = formatPrice(featured.symbol, featured.ask);
      el('mt5-spd').textContent = fmt(featured.spread, 4);
    }
  } catch { /* silent — WS fallback will populate when bridge runs */ }
}

async function loadMacroCalendar() {
  const container = el('macro-calendar');
  if (!container) return;
  try {
    const events = await api('GET', '/api/v1/market/calendar');
    if (!Array.isArray(events) || events.length === 0) {
      container.innerHTML = `<div class="watchlist-item"><div class="wi-left"><div class="wi-sym" style="font-size:11px;color:var(--t3)">Nenhum evento agendado</div></div></div>`;
      return;
    }
    const impactClass = { HIGH: 'badge-r', MEDIUM: 'badge-am', LOW: 'badge-s' };
    container.innerHTML = events.slice(0, 6).map(ev => {
      const cls = impactClass[ev.impact] || 'badge-s';
      const time = ev.time ? ev.time.slice(11, 16) : '—';
      return `<div class="watchlist-item">
        <div class="wi-left">
          <div class="wi-sym" style="font-size:11px">${escapeHtml(ev.title)}</div>
          <div class="wi-setup">${escapeHtml(ev.country)} · ${time}</div>
        </div>
        <span class="badge ${cls}">${escapeHtml(ev.impact)}</span>
      </div>`;
    }).join('');
  } catch {
    container.innerHTML = `<div class="watchlist-item"><div class="wi-left"><div class="wi-sym" style="font-size:11px;color:var(--t3)">Dados via Briefing Matinal</div></div></div>`;
  }
}

async function selectMktAsset(sym, cardEl) {
  document.querySelectorAll('.mkt-card').forEach(c => c.classList.remove('sel'));
  cardEl?.classList.add('sel');
  const symBadge = el('mkt-selected-sym');
  if (symBadge) symBadge.textContent = sym;

  try {
    const data = await api('GET', `/api/v1/market/quotes/${sym}/timeframes`);
    renderMTF(data.mtf || {});
  } catch { /* silent */ }
}

function renderMTF(mtf) {
  const grid = document.querySelector('.tf-align-grid');
  if (!grid) return;
  const trendMap = {
    BULL: ['tfa-up',   '↑ BULL'],
    BEAR: ['tfa-down', '↓ BEAR'],
    LATE: ['tfa-side', '→ LATE'],
  };
  grid.innerHTML = ['D1', 'H4', 'H1', 'M15', 'M5', 'M1'].map(tf => {
    const [cls, lbl] = trendMap[mtf[tf] || 'LATE'] || trendMap.LATE;
    return `<div class="tfa"><div class="tfa-name">${tf}</div><div class="tfa-trend ${cls}">${lbl}</div></div>`;
  }).join('');
}

function highlightSessions() {
  const h = new Date().getHours(); // browser local time (BRT = UTC-3)
  const sessEl = el('sessions-status');
  if (!sessEl) return;
  const lonOpen = h >= 6 && h < 15;
  const nyOpen  = h >= 10 && h < 19;
  if (lonOpen && nyOpen) { sessEl.textContent = 'London + NY abertas'; sessEl.className = 'badge badge-g'; }
  else if (lonOpen)      { sessEl.textContent = 'London aberta';       sessEl.className = 'badge badge-tl'; }
  else if (nyOpen)       { sessEl.textContent = 'NY aberta';           sessEl.className = 'badge badge-r'; }
  else                   { sessEl.textContent = 'Mercado fechado';     sessEl.className = 'badge badge-s'; }
}

// ── Trades ───────────────────────────────────────────────────────────────────

async function loadTrades() {
  try {
    const data = await api('GET', '/api/v1/trades?limit=100');
    state.trades = Array.isArray(data) ? data : (data.items || []);
    renderTrades();
    renderTradeStats();
    updateFomoCount();
  } catch {
    el('trades-tbody').innerHTML = `<tr><td colspan="10" style="text-align:center;color:var(--t4);padding:20px">Erro ao carregar trades</td></tr>`;
  }
}

function filterTrades(f, btn) {
  state.tradeFilter = f;
  document.querySelectorAll('.ftab').forEach(b => b.classList.remove('on'));
  btn?.classList.add('on');
  renderTrades();
}

function renderTrades() {
  const tbody = el('trades-tbody');
  if (!tbody) return;
  const list = state.trades.filter(t =>
    state.tradeFilter === 'open'   ? t.status === 'open'   :
    state.tradeFilter === 'closed' ? t.status === 'closed' : true
  );
  if (!list.length) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align:center;color:var(--t4);padding:20px">Nenhum trade</td></tr>`;
    return;
  }
  tbody.innerHTML = list.map(t => {
    const r = t.r_realized != null
      ? `<span class="${t.r_realized >= 0 ? 'pos' : 'neg'}">${t.r_realized >= 0 ? '+' : ''}${fmt(t.r_realized)}R</span>` : '—';
    const dirCls = (t.direction || '').toUpperCase() === 'LONG' ? 'badge-g' : 'badge-r';
    const action = t.status === 'open'
      ? `<button class="btn btn-ghost" onclick="showCloseModal('${t.id}')" style="padding:3px 8px;font-size:10px;color:var(--am);border-color:rgba(245,163,10,.4)">Fechar</button>`
      : `<button class="btn btn-ghost" onclick="showReflectModal('${t.id}')" style="padding:3px 8px;font-size:10px;color:var(--tl);border-color:rgba(0,212,170,.3)" title="Reflexão IA">Refletir</button>`;
    return `<tr>
      <td class="mono">${t.asset}</td>
      <td><span class="badge ${dirCls}">${(t.direction||'').toUpperCase()}</span></td>
      <td class="mono">${t.timeframe}</td>
      <td><span class="setup-tag">${t.setup||'—'}</span></td>
      <td class="mono">${fmt(t.entry)}</td>
      <td class="mono">${fmt(t.stop)}</td>
      <td class="mono">${fmt(t.target)}</td>
      <td class="mono">${r}</td>
      <td><span class="badge ${t.status==='open'?'badge-tl':'badge-s'}">${(t.status||'').toUpperCase()}</span></td>
      <td>${action}</td>
    </tr>`;
  }).join('');
}

function renderTradeStats() {
  const closed = state.trades.filter(t => t.status === 'closed');
  const wins   = closed.filter(t => t.result === 'win').length;
  const losses = closed.filter(t => t.result === 'loss').length;
  const wr     = closed.length ? `${((wins/closed.length)*100).toFixed(1)}%` : '—';
  el('st-total').textContent  = state.trades.length;
  el('st-open').textContent   = state.trades.filter(t => t.status === 'open').length;
  el('st-wins').textContent   = wins;
  el('st-losses').textContent = losses;
  el('st-wr').textContent     = wr;
}

// ── Trade modals ─────────────────────────────────────────────────────────────

function showTradeModal() { el('trade-modal').style.display = 'flex'; }
function hideTradeModal() { el('trade-modal').style.display = 'none'; }

function showTradeError(msg) {
  const errEl = el('trade-form-error');
  if (!errEl) return;
  errEl.textContent = msg;
  errEl.style.display = '';
  setTimeout(() => { errEl.style.display = 'none'; }, 5000);
}

async function submitTrade() {
  const btn = el('btn-submit-trade');
  btn.disabled = true;
  try {
    const asset  = (el('tm-asset').value.trim() || '').toUpperCase();
    const dir    = el('tm-dir').value;
    const entry  = parseFloat(el('tm-entry').value);
    const stop   = parseFloat(el('tm-stop').value);
    const target = parseFloat(el('tm-target').value);

    if (!asset)  { showTradeError('Informe o ativo.'); return; }
    if (!entry)  { showTradeError('Informe o preço de entrada.'); return; }
    if (!stop)   { showTradeError('Informe o stop loss.'); return; }
    if (!target) { showTradeError('Informe o take profit.'); return; }

    if (dir === 'long') {
      if (stop >= entry)  { showTradeError('LONG: Stop deve ser MENOR que a Entrada.'); return; }
      if (target <= entry){ showTradeError('LONG: Alvo deve ser MAIOR que a Entrada.'); return; }
    } else {
      if (stop <= entry)  { showTradeError('SHORT: Stop deve ser MAIOR que a Entrada.'); return; }
      if (target >= entry){ showTradeError('SHORT: Alvo deve ser MENOR que a Entrada.'); return; }
    }

    await api('POST', '/api/v1/trades', {
      asset, direction: dir.toUpperCase(),
      timeframe:       el('tm-tf').value,
      entry, stop, target,
      setup:           el('tm-setup').value.trim() || 'Manual',
      emotional_state: el('tm-emo').value,
      notes:           el('tm-notes').value.trim() || null,
    });
    hideTradeModal();
    toast('Trade registrado!');
    loadTrades();
  } catch (e) {
    toast(`Erro: ${e.message}`, 'err');
  } finally {
    btn.disabled = false;
  }
}

function showCloseModal(id) {
  el('cm-trade-id').value = id;
  el('cm-exit').value   = '';
  el('cm-result').value = 'win';
  el('cm-notes').value  = '';
  el('close-modal').style.display = 'flex';
}
function hideCloseModal() { el('close-modal').style.display = 'none'; }

async function submitClose() {
  const btn = el('btn-submit-close');
  btn.disabled = true;
  try {
    const exit = parseFloat(el('cm-exit').value);
    if (!exit) { toast('Informe o preço de saída', 'warn'); return; }
    const id = el('cm-trade-id').value;
    await api('PUT', `/api/v1/trades/${id}/close`, {
      trade_id: id, exit_price: exit,
      result: el('cm-result').value,
      notes:  el('cm-notes').value.trim() || null,
    });
    hideCloseModal();
    toast('Trade fechado!');
    loadTrades();
  } catch (e) {
    toast(`Erro: ${e.message}`, 'err');
  } finally {
    btn.disabled = false;
  }
}

// ── Trade reflection & export ─────────────────────────────────────────────────

function showReflectModal(id) {
  el('reflect-trade-id').value = id;
  el('reflect-content').textContent = '';
  el('reflect-modal').style.display = 'flex';
  el('reflect-loading').style.display = 'block';
  el('reflect-content').style.display = 'none';
  _loadReflection(id);
}

function hideReflectModal() { el('reflect-modal').style.display = 'none'; }

async function _loadReflection(id) {
  try {
    const data = await api('POST', `/api/v1/trades/${id}/reflect`);
    el('reflect-loading').style.display = 'none';
    el('reflect-content').style.display = 'block';
    el('reflect-content').textContent = data.reflection || 'Sem reflexão disponível.';
  } catch (e) {
    el('reflect-loading').style.display = 'none';
    el('reflect-content').style.display = 'block';
    el('reflect-content').textContent = `Erro: ${e.message}`;
    el('reflect-content').style.color = 'var(--red)';
  }
}

function exportTrades() {
  if (!state.trades.length) { toast('Nenhum trade para exportar', 'warn'); return; }
  const header = ['ID','Ativo','Direção','Timeframe','Setup','Entrada','Stop','Alvo','Saída','R Realizado','Resultado','Status','Aberto em','Fechado em'];
  const rows = state.trades.map(t => [
    t.id, t.asset, t.direction, t.timeframe, t.setup || '',
    t.entry, t.stop, t.target, t.exit || '', t.r_realized ?? '',
    t.result || '', t.status,
    t.created_at ? new Date(t.created_at).toLocaleString('pt-BR') : '',
    t.closed_at  ? new Date(t.closed_at).toLocaleString('pt-BR')  : '',
  ].map(v => `"${String(v).replace(/"/g, '""')}"`));

  const csv = [header.join(','), ...rows.map(r => r.join(','))].join('\r\n');
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = `oracle_trades_${new Date().toISOString().slice(0,10)}.csv`;
  a.click(); URL.revokeObjectURL(url);
  toast('Exportado com sucesso!');
}

// ── Briefing ─────────────────────────────────────────────────────────────────

function _parseLevelsFromBriefing(content, sym) {
  // Find the paragraph/section that mentions this symbol
  const escaped = sym.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const sectionRe = new RegExp(`(?:^|\\n)[\\s\\S]{0,10}${escaped}[\\s\\S]{0,600}?(?=\\n[A-Z]{3,6}\\d?\\b|$)`, 'im');
  const section = (content.match(sectionRe) || [''])[0] || content;

  // Match numbers like 38.50 or 38,50 after suporte/resistência keywords
  const numPat = '([\\d]{1,6}[.,][\\d]{2,4})';
  const supRe  = new RegExp(`[Ss]uporte[^\\d]{0,30}${numPat}`, 'm');
  const resRe  = new RegExp(`[Rr]esist[êe]ncia[^\\d]{0,30}${numPat}`, 'm');

  const supMatch = section.match(supRe);
  const resMatch = section.match(resRe);

  return {
    support:    supMatch ? parseFloat(supMatch[1].replace(',', '.')) : null,
    resistance: resMatch ? parseFloat(resMatch[1].replace(',', '.')) : null,
  };
}

async function loadBriefing() {
  el('briefing-text').innerHTML = `<div class="typing-anim"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>&nbsp;Gerando briefing...`;
  try {
    const data = await api('GET', '/api/v1/briefing/morning?assets=PETR4&assets=VALE3');
    renderBriefing(data);
  } catch (e) {
    el('briefing-text').innerHTML = `<p style="color:var(--red)">Erro: ${escapeHtml(e.message)}</p>`;
  }
}

function renderBriefing(data) {
  const raw = data.content || 'Sem conteúdo.';
  el('briefing-text').innerHTML = raw
    .replace(/##\s+(.+)/g, '<h3>$1</h3>')
    .replace(/\n\n+/g, '</p><p>')
    .replace(/\n/g, '<br>');

  const assetsEl = el('briefing-assets');
  if (assetsEl && data.assets_covered?.length) {
    const apiLevels  = data.key_levels || {};
    const quotesMap  = {};
    (state.quotes || []).forEach(q => { quotesMap[q.symbol] = q; });

    // Enrich key_levels: regex extraction from text → quote-based fallback
    const enrichedLevels = { ...apiLevels };
    for (const sym of data.assets_covered) {
      if (!enrichedLevels[sym]?.support && !enrichedLevels[sym]?.resistance) {
        const parsed  = _parseLevelsFromBriefing(data.content || '', sym);
        const q       = quotesMap[sym];
        const fallSup = q ? +(q.price * 0.985).toFixed(2) : null;
        const fallRes = q ? +(q.price * 1.015).toFixed(2) : null;
        enrichedLevels[sym] = {
          support:    parsed.support    ?? fallSup,
          resistance: parsed.resistance ?? fallRes,
        };
      }
    }

    assetsEl.innerHTML = data.assets_covered.map(sym => {
      const lvl = enrichedLevels[sym] || {};
      const q   = quotesMap[sym];
      const priceStr = q ? formatPrice(sym, q.price) : '—';
      const chgPct   = q ? q.change_pct : null;
      const chgStr   = chgPct != null ? `${chgPct >= 0 ? '+' : ''}${fmt(chgPct, 2)}%` : '—';
      const chgCls   = chgPct != null ? (chgPct >= 0 ? 'pos' : 'neg') : '';
      const sessStr  = q?.session || '—';

      return `<div class="watchlist-item">
        <div class="wi-left">
          <div class="wi-sym">${sym}</div>
          <div class="wi-setup">Sup: ${lvl.support ? fmt(lvl.support) : '—'} | Res: ${lvl.resistance ? fmt(lvl.resistance) : '—'}</div>
        </div>
        <div style="text-align:right;flex-shrink:0">
          <div class="mono" style="font-size:12px">${priceStr}</div>
          <div class="${chgCls}" style="font-size:10px">${chgStr}</div>
          <div style="font-size:9px;color:var(--t4)">${sessStr}</div>
        </div>
      </div>`;
    }).join('');
  }

  const eventsEl = el('briefing-events');
  if (eventsEl && data.upcoming_events?.length) {
    eventsEl.innerHTML = data.upcoming_events.slice(0, 4).map(ev =>
      `<div class="watchlist-item">
        <div class="wi-left"><div class="wi-sym" style="font-size:11px">${escapeHtml(ev.title || ev.name || '—')}</div></div>
        <span class="badge badge-am">${ev.impact || '—'}</span>
      </div>`
    ).join('');
  } else if (eventsEl) {
    eventsEl.innerHTML = `<div style="padding:14px;color:var(--t4);font-size:11px">Nenhum evento agendado</div>`;
  }
}

// ── Performance ──────────────────────────────────────────────────────────────

async function loadPerf() {
  try {
    const [perf, summary] = await Promise.all([
      api('GET', '/api/v1/analytics/performance?period=monthly'),
      api('GET', '/api/v1/analytics/summary'),
    ]);
    renderPerf(perf, summary);
  } catch (e) {
    el('perf-ev').innerHTML = `<div style="padding:14px;color:var(--t4)">Erro: ${escapeHtml(e.message)}</div>`;
  }
}

function mrow(lbl, val, color) {
  return `<div class="mrow"><span class="mrow-lbl">${lbl}</span><span class="mrow-val"${color?` style="color:${color}"`:''}>` + val + `</span></div>`;
}

function renderPerf(perf, summary) {
  const wr = perf.win_rate_pct;
  const gaugeArc = el('gauge-arc');
  const gaugeNum = el('gauge-num');
  const gaugeSub = el('gauge-sub');
  if (gaugeArc && wr != null) {
    gaugeArc.setAttribute('stroke-dashoffset', (160 * (1 - wr / 100)).toFixed(1));
  }
  if (gaugeNum) gaugeNum.textContent = wr != null ? `${fmt(wr,1)}%` : '—';
  if (gaugeSub) gaugeSub.textContent = `${perf.total_trades || 0} TRADES`;

  el('perf-ev').innerHTML = [
    mrow('Expected Value',  fmt(perf.expected_value_r) + 'R'),
    mrow('Total R',         fmt(perf.total_r) + 'R'),
    mrow('Average R',       fmt(perf.average_r) + 'R'),
    mrow('Profit Factor',   perf.profit_factor ? fmt(perf.profit_factor, 2) : '—', 'var(--am)'),
    mrow('Grade',           perf.grade || '—'),
  ].join('');

  el('perf-dd').innerHTML = [
    mrow('Max Drawdown', fmt(perf.max_drawdown_r) + 'R', 'var(--red)'),
    mrow('Período',      perf.period || '—'),
    mrow('Total Trades', perf.total_trades || '—'),
  ].join('');

  if (summary) {
    el('perf-summary').innerHTML = [
      mrow('All-time Trades', summary.total_trades || '—'),
      mrow('Win Rate',        summary.win_rate_pct != null ? `${fmt(summary.win_rate_pct,1)}%` : '—'),
      mrow('Total R',         fmt(summary.total_r) + 'R'),
      mrow('Grade',           summary.grade || '—'),
    ].join('');
  }

  const pnlEl = el('perf-pnl');
  if (pnlEl && perf.daily_pnl?.length) {
    pnlEl.innerHTML = perf.daily_pnl.slice(-10).map(d => {
      const pos = (d.r || 0) >= 0;
      const w   = Math.min(Math.abs(d.r || 0) / 3 * 100, 100);
      return `<div class="pnl-bar-row">
        <div class="pnl-day">${d.label || '—'}</div>
        <div class="pnl-bar-track"><div class="pnl-bar-fill ${pos?'pnl-bar-pos':'pnl-bar-neg'}" style="width:${w.toFixed(0)}%"></div></div>
        <div class="pnl-val ${pos?'pos':'neg'}">${pos?'+':''}${fmt(d.r)}R</div>
      </div>`;
    }).join('');
  } else if (pnlEl) {
    pnlEl.innerHTML = `<div style="padding:20px;color:var(--t4);font-size:11px;text-align:center">Sem dados de P&L disponíveis</div>`;
  }
}

// ── Replay ────────────────────────────────────────────────────────────────────

function _initReplayChart() {
  const container = el('replay-chart');
  if (!container) return;

  if (_replayChart) {
    _replayChart.remove();
    _replayChart = null;
    _replaySeries = null;
  }

  _replayChart = LightweightCharts.createChart(container, {
    width:  container.clientWidth,
    height: 220,
    layout: {
      background: { color: 'transparent' },
      textColor:  'rgba(255,255,255,0.4)',
    },
    grid: {
      vertLines: { color: 'rgba(255,255,255,0.04)' },
      horzLines: { color: 'rgba(255,255,255,0.04)' },
    },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: 'rgba(255,255,255,0.08)' },
    timeScale: {
      borderColor:    'rgba(255,255,255,0.08)',
      timeVisible:    true,
      secondsVisible: false,
    },
  });

  // Lightweight Charts v5: addSeries(SeriesType, options)
  _replaySeries = _replayChart.addSeries(LightweightCharts.CandlestickSeries, {
    upColor:         '#00d4aa',
    downColor:       '#ff4560',
    borderUpColor:   '#00d4aa',
    borderDownColor: '#ff4560',
    wickUpColor:     '#00d4aa',
    wickDownColor:   '#ff4560',
  });

  state._replayCandles = [];
  state._lastReplayBar = null;
}

function loadReplay() {
  if (el('rp-start').value) return;
  const now  = new Date();
  const week = new Date(now - 7 * 24 * 60 * 60 * 1000);
  el('rp-end').value   = now.toISOString().slice(0, 16);
  el('rp-start').value = week.toISOString().slice(0, 16);
}

async function createReplay() {
  const btn = el('btn-replay');
  btn.disabled = true; btn.textContent = '⏳ Criando...';
  try {
    const start = new Date(el('rp-start').value).toISOString();
    const end   = new Date(el('rp-end').value).toISOString();
    if (!start || !end || start === 'Invalid Date') { toast('Informe início e fim válidos', 'warn'); return; }
    const data = await api('POST', '/api/v1/replay', {
      asset:     (el('rp-asset').value.trim() || 'PETR4').toUpperCase(),
      timeframe: el('rp-tf').value,
      start, end,
    });
    state.replaySessionId = data.session_id;
    renderReplayStatus(data);
    el('replay-frame-card').style.display = 'block';
    _initReplayChart();
    el('btn-rp-next').disabled   = false;
    el('btn-rp-finish').disabled = false;
    toast(`Sessão criada — ${data.total_frames} frames`);
  } catch (e) {
    toast(`Erro: ${e.message}`, 'err');
  } finally {
    btn.disabled = false; btn.textContent = '▶ Criar Sessão';
  }
}

async function replayNext() {
  if (!state.replaySessionId) return;
  const btn     = el('btn-rp-next');
  const frameEl = el('replay-frame');
  btn.disabled = true;

  // Immediate spinner feedback
  if (frameEl) {
    frameEl.innerHTML = `<div style="padding:20px;text-align:center">
      <div class="typing-anim"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>
      <div style="margin-top:8px;font-size:11px;color:var(--t3)">Carregando frame...</div>
    </div>`;
  }
  state._replayAwaitingFrame = true;

  try {
    const data = await api('PUT', `/api/v1/replay/${state.replaySessionId}/next`);
    renderReplayStatus(data);

    if (data.state === 'completed') {
      state._replayAwaitingFrame = false;
      toast('Replay concluído!');
      el('btn-rp-finish').disabled = true;
    } else {
      btn.disabled = false;
      // 3s fallback: WS never fired — show last known OHLCV or status
      setTimeout(() => {
        if (!state._replayAwaitingFrame) return;
        state._replayAwaitingFrame = false;
        if (state._lastReplayBar) {
          renderReplayFrame(state._lastReplayBar);
        } else if (frameEl) {
          frameEl.innerHTML = `<div style="padding:14px">
            ${mrow('Frame', `${(data.current_frame || 0) + 1} / ${data.total_frames || 0}`)}
            ${mrow('Progresso', `${fmt(data.progress_pct, 1)}%`)}
            <div style="margin-top:8px;font-size:10px;color:var(--t4)">Dados de candle aguardando WebSocket</div>
          </div>`;
        }
      }, 3000);
    }
  } catch (e) {
    state._replayAwaitingFrame = false;
    toast(`Erro: ${e.message}`, 'err');
    btn.disabled = false;
  }
}

async function replayFinish() {
  if (!state.replaySessionId) return;
  try {
    const data = await api('PUT', `/api/v1/replay/${state.replaySessionId}/finish`);
    renderReplayStatus(data);
    el('btn-rp-next').disabled   = true;
    el('btn-rp-finish').disabled = true;
    toast('Replay finalizado');
  } catch (e) {
    toast(`Erro: ${e.message}`, 'err');
  }
}

function renderReplayStatus(data) {
  const badge = el('replay-state-badge');
  if (badge) {
    const map = { idle:['badge-s','IDLE'], playing:['badge-tl','PLAYING'], paused:['badge-am','PAUSADO'], completed:['badge-g','CONCLUÍDO'] };
    const [cls, lbl] = map[data.state] || ['badge-s', data.state];
    badge.className = `badge ${cls}`; badge.textContent = lbl;
  }
  const statusEl = el('replay-status');
  if (statusEl) statusEl.innerHTML = [
    mrow('Ativo',      data.asset     || '—'),
    mrow('Timeframe',  data.timeframe || '—'),
    mrow('Frame',      `${(data.current_frame||0) + 1} / ${data.total_frames||0}`),
    mrow('Progresso',  `${fmt(data.progress_pct, 1)}%`),
    mrow('Velocidade', data.speed     || '—'),
  ].join('');
  const prog = el('replay-progress');
  if (prog) prog.textContent = `${(data.current_frame||0)+1}/${data.total_frames||0}`;
}

function renderReplayFrame(payload) {
  const frameEl = el('replay-frame');
  if (!frameEl) return;
  const bar = payload.bar || payload;
  if (!bar || (bar.open == null && bar.close == null)) {
    frameEl.innerHTML = `<div style="padding:14px;color:var(--t4);font-size:11px;text-align:center">Aguardando frame...</div>`;
    return;
  }

  state._lastReplayBar = bar;

  // Push candle to Lightweight Charts (timestamp → UNIX seconds)
  if (_replaySeries && bar.timestamp) {
    const t = Math.floor(new Date(bar.timestamp).getTime() / 1000);
    const last = state._replayCandles[state._replayCandles.length - 1];
    if (!last || last.time !== t) {
      const candle = { time: t, open: bar.open, high: bar.high, low: bar.low, close: bar.close };
      state._replayCandles.push(candle);
      _replaySeries.setData(state._replayCandles);
    }
  }

  const isGreen = (bar.close || 0) >= (bar.open || 0);
  frameEl.innerHTML = `
    <div class="replay-candle">
      <span class="badge ${isGreen ? 'badge-g' : 'badge-r'}">${isGreen ? '▲' : '▼'} ${fmt(bar.close)}</span>
      <span class="badge badge-s">${bar.symbol || ''} ${bar.timeframe || ''}</span>
    </div>
    <div class="metric-rows" style="padding:8px 0 0">
      ${mrow('Abertura',    fmt(bar.open))}
      ${mrow('Máxima',      fmt(bar.high), 'var(--green)')}
      ${mrow('Mínima',      fmt(bar.low),  'var(--red)')}
      ${mrow('Fechamento',  fmt(bar.close), isGreen ? 'var(--green)' : 'var(--red)')}
      ${mrow('Volume',      bar.volume ? Math.round(bar.volume).toLocaleString('pt-BR') : '—')}
    </div>`;
}

// ── Checklist ────────────────────────────────────────────────────────────────

const CHECKLIST_TOTAL = 14;

function toggleCheck(item) {
  item.classList.toggle('checked');
  updateCheckScore();
}

function updateCheckScore() {
  const checked = document.querySelectorAll('#pg-checklist .check-item.checked').length;
  const pct = (checked / CHECKLIST_TOTAL) * 100;
  const bar   = el('chk-bar');
  const badge = el('chk-score-badge');
  const label = el('chk-label');
  if (bar) {
    bar.style.width = `${pct.toFixed(0)}%`;
    bar.className = 'check-score-fill ' + (pct >= 75 ? 'score-high' : pct >= 50 ? 'score-mid' : 'score-low');
  }
  if (badge) badge.textContent = `Score: ${checked}/${CHECKLIST_TOTAL}`;
  if (label) {
    if (pct >= 85)      { label.textContent = '✓ APROVADO — Pode entrar';            label.style.color = 'var(--green)'; }
    else if (pct >= 57) { label.textContent = '⚠ MODERADO — Complete mais itens';   label.style.color = 'var(--am)'; }
    else                { label.textContent = '✗ BLOQUEADO — Muitos itens pendentes'; label.style.color = 'var(--red)'; }
  }
}

function resetChecklist() {
  document.querySelectorAll('#pg-checklist .check-item').forEach(i => i.classList.remove('checked', 'blocked'));
  updateCheckScore();
}

function approveChecklist() {
  const checked = document.querySelectorAll('#pg-checklist .check-item.checked').length;
  if (checked < 10) {
    toast('Complete pelo menos 10 itens antes de operar', 'warn');
  } else {
    toast('✓ Checklist aprovado! Boa sorte. Siga o plano.');
  }
}

function calcRisk() {
  const banca = parseFloat(el('r-banca')?.value) || 10000;
  const pct   = parseFloat(el('r-pct')?.value)   || 1;
  const entry = parseFloat(el('r-entry')?.value)  || 0;
  const sl    = parseFloat(el('r-sl')?.value)     || 0;
  const tp    = parseFloat(el('r-tp')?.value)     || 0;
  const lot   = parseFloat(el('r-lot')?.value)    || 100000;

  const riskRS = banca * (pct / 100);
  const slPips = Math.abs(entry - sl) * 10000;
  const tpPips = Math.abs(tp - entry) * 10000;
  const pipVal = lot * 0.0001;
  const lots   = slPips > 0 ? riskRS / (slPips * pipVal) : 0;
  const profit = lots * tpPips * pipVal;
  const rr     = slPips > 0 ? (tpPips / slPips).toFixed(2) : '—';

  const setV = (id, val) => { const e = el(id); if (e) e.textContent = val; };
  setV('r-val-risk',   'R$ ' + riskRS.toFixed(2));
  setV('r-val-pips',   slPips.toFixed(1) + ' pips');
  setV('r-val-lots',   lots.toFixed(2) + ' lots');
  setV('r-val-profit', 'R$ ' + profit.toFixed(2));
  setV('r-val-rr',     '1 : ' + rr);
}

function updateFomoCount() {
  const todayTrades = state.trades.filter(t => {
    const d = new Date(t.created_at || 0);
    const now = new Date();
    return d.toDateString() === now.toDateString();
  });

  const n = todayTrades.length;
  const countEl = el('fomo-count');
  if (countEl) {
    countEl.textContent = `${n} (limite: 5)`;
    countEl.className = `fomo-status ${n >= 5 ? 'fs-bad' : n >= 3 ? 'fs-warn' : 'fs-ok'}`;
  }

  const todayLosses = todayTrades.filter(t => t.result === 'loss').length;
  const lossEl = el('fomo-loss');
  if (lossEl) {
    lossEl.textContent = todayLosses > 0 ? `${todayLosses} loss hoje` : 'OK';
    lossEl.className = `fomo-status ${todayLosses >= 2 ? 'fs-bad' : todayLosses > 0 ? 'fs-warn' : 'fs-ok'}`;
  }

  const h = new Date().getHours();
  const risky = h < 9 || (h >= 14 && h < 15) || h >= 18;
  const hourEl = el('fomo-hour');
  if (hourEl) {
    hourEl.textContent = risky ? 'Sim (abert./fech.)' : 'OK';
    hourEl.className = `fomo-status ${risky ? 'fs-warn' : 'fs-ok'}`;
  }

  const nowMin = h * 60 + new Date().getMinutes();
  // BRT típicos de alto impacto: 09:25 (abertura B3), 09:30 (dados EUA), 11:55/15:00 (Fed/BCE)
  const macroWindows = [9*60+25, 9*60+30, 11*60+55, 15*60];
  const nearMacro = macroWindows.some(t => Math.abs(nowMin - t) <= 30);
  const macroEl = el('fomo-macro');
  if (macroEl) {
    macroEl.textContent = nearMacro ? 'Sim (horário macro)' : 'OK';
    macroEl.className = `fomo-status ${nearMacro ? 'fs-warn' : 'fs-ok'}`;
  }

  const verdictEl = el('fomo-verdict');
  if (verdictEl) {
    const isBad  = n >= 5 || todayLosses >= 2;
    const isWarn = n >= 3 || todayLosses > 0 || risky || nearMacro;
    if (isBad) {
      verdictEl.textContent = 'PARAR';
      verdictEl.className = 'badge badge-s badge-r';
    } else if (isWarn) {
      verdictEl.textContent = 'ATENÇÃO';
      verdictEl.className = 'badge badge-s badge-am';
    } else {
      verdictEl.textContent = 'OPERAR';
      verdictEl.className = 'badge badge-s badge-g';
    }
  }
}

// ── Config toggles ────────────────────────────────────────────────────────────

function toggleFeature(toggleEl) {
  toggleEl.classList.toggle('on');
  if (toggleEl.dataset.key) {
    localStorage.setItem(toggleEl.dataset.key, toggleEl.classList.contains('on') ? 'true' : 'false');
  }
}

function initToggles() {
  document.querySelectorAll('.toggle[data-key]').forEach(t => {
    const stored = localStorage.getItem(t.dataset.key);
    if (stored === 'false') t.classList.remove('on');
  });
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function toast(msg, type = 'info') {
  const colors = { info: 'var(--tl)', err: 'var(--red)', warn: 'var(--am)' };
  const t = document.createElement('div');
  t.style.cssText = `position:fixed;bottom:20px;right:20px;z-index:9999;background:var(--s3);border:1px solid ${colors[type]||colors.info};border-radius:8px;padding:10px 16px;font-size:12px;color:var(--t1);font-family:var(--sans);max-width:320px;box-shadow:0 4px 20px rgba(0,0,0,.5);transition:opacity .3s`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 3500);
}

// ── Init ─────────────────────────────────────────────────────────────────────

function init() {
  tick();
  setInterval(tick, 1000);
  connectWS();
  checkHealth();
  setInterval(checkHealth, 30_000);
  initToggles();
  updateCheckScore();
  calcRisk();
  highlightSessions();
  setInterval(highlightSessions, 60_000);

  loadQuotes();
  setInterval(loadQuotes, 3_000);

  // Start analysis page poller (default page on load)
  if (state.page === 'analysis') {
    _pagePoller = setInterval(pollLatestAnalysis, 5_000);
  }

  window.addEventListener('beforeunload', _clearPagePoller);

  window.addEventListener('resize', () => {
    if (_replayChart) {
      const container = el('replay-chart');
      if (container) _replayChart.applyOptions({ width: container.clientWidth });
    }
  });

  // Chat keyboard shortcut
  el('chat-input')?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMsg(); }
  });

  // Chat textarea auto-resize
  el('chat-input')?.addEventListener('input', function() {
    this.style.height = '';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
  });
}

document.addEventListener('DOMContentLoaded', init);
