'use strict';

// ── Constants ──────────────────────────────────────────
const LOADING_STEPS = [
  'Connecting to exchange…',
  'Fetching 1D candle data…',
  'Fetching 4H candle data…',
  'Fetching 1H candle data…',
  'Fetching 15M candle data…',
  'Loading BTC reference data…',
  'Analyzing market structure…',
  'Detecting order blocks…',
  'Mapping FVG & liquidity zones…',
  'Computing RSI / MACD / EMA…',
  'Checking BOS & CHOCH…',
  'Scoring confidence…',
  'Applying signal filters…',
  'Assembling institutional signal…',
];

const TF_ORDER = ['daily', '4h', '1h', '15m'];

// ── State ──────────────────────────────────────────────
let stepInterval = null;
let stepIndex = 0;

// ── DOM refs ───────────────────────────────────────────
const $ = id => document.getElementById(id);

// ── Init ───────────────────────────────────────────────
async function init() {
  try {
    const res = await fetch('/api/pairs');
    const pairs = await res.json();
    renderPairList(pairs);
  } catch {
    renderPairList(['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT',
                    'XRP/USDT', 'AVAX/USDT', 'LINK/USDT', 'ARB/USDT']);
  }

  $('analyzeBtn').addEventListener('click', () => {
    const pair = $('pairInput').value.trim().toUpperCase() || 'BTC/USDT';
    analyze(pair);
  });

  $('pairInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') $('analyzeBtn').click();
  });
}

function renderPairList(pairs) {
  const list = $('pairList');
  list.innerHTML = '';
  pairs.forEach(pair => {
    const item = document.createElement('div');
    item.className = 'pair-item';
    item.dataset.pair = pair;
    item.innerHTML = `<span class="pair-status"></span>${pair}`;
    item.addEventListener('click', () => {
      $('pairInput').value = pair;
      analyze(pair);
    });
    list.appendChild(item);
  });
}

function setActivePair(pair) {
  document.querySelectorAll('.pair-item').forEach(el => {
    el.classList.toggle('active', el.dataset.pair === pair);
  });
}

// ── Analyze ────────────────────────────────────────────
async function analyze(pair) {
  setActivePair(pair);
  $('liveLabel').textContent = 'ANALYZING';
  $('analyzeBtn').disabled = true;
  $('btnLabel').style.display = 'none';
  $('btnSpinner').style.display = 'block';

  showLoading();

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);
    const res = await fetch(`/api/signal?pair=${encodeURIComponent(pair)}`, { signal: controller.signal });
    clearTimeout(timeout);
    const data = await res.json();
    renderSignal(data);
  } catch (err) {
    renderError(pair, err.message || 'Request failed');
  } finally {
    stopLoading();
    $('liveLabel').textContent = 'READY';
    $('analyzeBtn').disabled = false;
    $('btnLabel').style.display = '';
    $('btnSpinner').style.display = 'none';
  }
}

// ── Loading ────────────────────────────────────────────
function showLoading() {
  $('emptyState').style.display = 'none';
  $('signalContent').style.display = 'none';
  $('loadingWrap').style.display = 'flex';

  stepIndex = 0;
  const stepsEl = $('loaderSteps');
  stepsEl.innerHTML = '';

  LOADING_STEPS.forEach((msg, i) => {
    const el = document.createElement('div');
    el.className = 'loader-step';
    el.id = `step-${i}`;
    el.textContent = `▸ ${msg}`;
    stepsEl.appendChild(el);
  });

  // Activate first step
  document.getElementById('step-0').classList.add('active');

  stepInterval = setInterval(() => {
    const prev = document.getElementById(`step-${stepIndex}`);
    if (prev) { prev.classList.remove('active'); prev.classList.add('done'); prev.textContent = `✓ ${LOADING_STEPS[stepIndex]}`; }
    stepIndex++;
    if (stepIndex < LOADING_STEPS.length) {
      const next = document.getElementById(`step-${stepIndex}`);
      if (next) next.classList.add('active');
    } else {
      clearInterval(stepInterval);
    }
  }, 3200);
}

function stopLoading() {
  clearInterval(stepInterval);
  $('loadingWrap').style.display = 'none';
}

// ── Render Signal ──────────────────────────────────────
function renderSignal(d) {
  if (!d || !d.pair) return;

  $('signalContent').style.display = 'block';

  const sig = (d.signal || 'HOLD').toUpperCase();

  // Top bar
  $('dispPair').textContent = d.pair;
  const badge = $('signalBadge');
  badge.textContent = sig;
  badge.className = `signal-badge badge-${sig.toLowerCase()}`;

  $('setupChip').textContent = d.setup_type || 'INTRADAY';

  const topBar = document.querySelector('.top-bar');
  topBar.className = `top-bar glow-${sig.toLowerCase()}`;

  // Confidence
  const conf = d.confidence || 0;
  $('confPct').textContent = `${conf}%`;
  $('confFill').style.width = `${conf}%`;
  $('confFill').style.background =
    conf >= 90 ? 'linear-gradient(90deg,#00e676,#00ffcc)' :
    conf >= 85 ? 'linear-gradient(90deg,#00cfb4,#00e5c0)' :
                 'linear-gradient(90deg,#ffc400,#ffdb4d)';

  // Fear & Greed
  const fg = d.market_sentiment?.fear_greed || '';
  const fgNum = parseInt((fg.match(/\d+/) || ['--'])[0]);
  if (!isNaN(fgNum)) {
    $('fgVal').textContent = fgNum;
    $('fgPill').style.borderColor =
      fgNum <= 25 ? 'rgba(0,230,118,.4)' :
      fgNum >= 75 ? 'rgba(255,45,85,.4)' : '';
  }

  // Levels
  const ez = d.entry_zone || {};
  $('lcEntry').textContent = `${fmt(ez.from)} – ${fmt(ez.to)}`;
  const tps = d.take_profit || ['--', '--', '--'];
  $('lcTp1').textContent = fmt(tps[0]);
  $('lcTp2').textContent = fmt(tps[1]);
  $('lcTp3').textContent = fmt(tps[2]);
  $('lcSl').textContent = fmt(d.stop_loss);
  $('lcRr').textContent = d.risk_reward_ratio || '--';

  // Panels
  renderTrend(d.trend_analysis || {});
  renderSMC(d.smart_money_analysis || {});
  renderIndicators(d.indicator_analysis || {});
  renderSentiment(d.market_sentiment || {});
  renderRisk(d.risk_analysis || {});
  renderReasoning(d.trade_reasoning || []);
  renderWarnings(d.warnings || []);
}

// ── Trend Panel ────────────────────────────────────────
function renderTrend(t) {
  const body = $('trendBody');
  body.innerHTML = '';
  TF_ORDER.forEach(tf => {
    const raw = t[tf] || 'DATA_UNAVAILABLE';
    const parts = raw.split('|').map(s => s.trim());
    const trendStr = parts[0] || '';
    const details = parts.slice(1).join(' · ');

    const cls = classifyTrend(trendStr);
    const row = document.createElement('div');
    row.className = 'tf-row';
    row.innerHTML = `
      <span class="tf-badge">${tf.toUpperCase()}</span>
      <span class="tf-trend ${cls}">${normTrend(trendStr)}</span>
      <span class="tf-detail">${escHtml(details)}</span>`;
    body.appendChild(row);
  });
}

function classifyTrend(t) {
  const u = t.toUpperCase();
  if (u.includes('STRONGLY_UP') || (u.includes('UPTREND') && !u.includes('MILD'))) return 'tf-up';
  if (u.includes('STRONGLY_BEAR') || (u.includes('DOWNTREND') && !u.includes('MILD'))) return 'tf-down';
  if (u.includes('MILD')) return 'tf-mild';
  return 'tf-range';
}

function normTrend(t) {
  const u = t.toUpperCase();
  if (u.includes('STRONGLY_BULL') || u === 'UPTREND') return '↑↑ UPTREND';
  if (u.includes('MILD_UP'))   return '↑ MILD UP';
  if (u.includes('STRONGLY_BEAR') || u === 'DOWNTREND') return '↓↓ DOWNTREND';
  if (u.includes('MILD_DOWN')) return '↓ MILD DOWN';
  if (u.includes('RANGE'))     return '→ RANGING';
  return t.slice(0, 18);
}

// ── SMC Panel ──────────────────────────────────────────
function renderSMC(s) {
  renderKV($('smcBody'), [
    ['STRUCTURE', s.market_structure],
    ['BOS',       s.bos],
    ['CHOCH',     s.choch],
    ['SWEEP',     s.liquidity_sweep],
    ['OB',        s.order_block],
    ['FVG',       s.fvg],
    ['BIAS',      s.institutional_bias],
  ]);
}

// ── Indicators Panel ───────────────────────────────────
function renderIndicators(ind) {
  renderKV($('indBody'), [
    ['RSI',    ind.rsi],
    ['MACD',   ind.macd],
    ['EMA',    ind.ema_alignment],
    ['VOLUME', ind.volume_strength],
    ['MOMENTUM', ind.momentum],
  ]);
}

// ── Sentiment Panel ────────────────────────────────────
function renderSentiment(s) {
  renderKV($('sentBody'), [
    ['BTC',     s.btc_correlation],
    ['F&G',     s.fear_greed],
    ['NEWS',    s.news_sentiment],
    ['WHALES',  s.whale_activity],
    ['FUNDING', s.funding_rate],
  ]);
}

// ── Risk Panel ─────────────────────────────────────────
function renderRisk(r) {
  const body = $('riskBody');
  body.innerHTML = '';
  const items = [
    ['RISK LEVEL',   r.risk_level],
    ['VOLATILITY',   r.volatility_risk],
    ['LIQUIDATION',  r.liquidation_risk],
    ['LEVERAGE',     r.recommended_leverage],
  ];
  items.forEach(([k, v]) => {
    const el = document.createElement('div');
    el.className = 'risk-item p-row';
    el.innerHTML = `<div class="lc-label">${k}</div><div class="lc-val">${escHtml(v || 'N/A')}</div>`;
    body.appendChild(el);
  });
}

// ── Reasoning ──────────────────────────────────────────
function renderReasoning(reasons) {
  const list = $('reasoningList');
  list.innerHTML = '';
  reasons.forEach((r, i) => {
    const el = document.createElement('div');
    el.className = 'reason-item';
    el.innerHTML = `<div class="reason-num">${i + 1}</div><div>${escHtml(r)}</div>`;
    list.appendChild(el);
  });
}

// ── Warnings ───────────────────────────────────────────
function renderWarnings(warnings) {
  const list = $('warningsList');
  list.innerHTML = '';
  warnings.forEach(w => {
    const el = document.createElement('div');
    el.className = 'warn-item';
    el.innerHTML = `<div class="warn-dot"></div><div>${escHtml(w)}</div>`;
    list.appendChild(el);
  });
}

// ── Error display ──────────────────────────────────────
function renderError(pair, msg) {
  $('signalContent').style.display = 'block';
  $('dispPair').textContent = pair;
  $('signalBadge').textContent = 'HOLD';
  $('signalBadge').className = 'signal-badge badge-hold';
  $('setupChip').textContent = 'N/A';
  document.querySelector('.top-bar').className = 'top-bar glow-hold';
  $('confPct').textContent = '0%';
  $('confFill').style.width = '0%';
  $('lcEntry').textContent = '--';
  ['lcTp1','lcTp2','lcTp3','lcSl','lcRr'].forEach(id => { $(id).textContent = '--'; });
  $('trendBody').innerHTML = `<div class="p-row"><div class="p-val" style="color:var(--sell)">${escHtml(msg)}</div></div>`;
  ['smcBody','indBody','sentBody','riskBody','reasoningList','warningsList'].forEach(id => { $(id).innerHTML = ''; });
}

// ── Helpers ────────────────────────────────────────────
function renderKV(el, pairs) {
  el.innerHTML = '';
  pairs.forEach(([k, v]) => {
    if (!v) return;
    const row = document.createElement('div');
    row.className = 'p-row';
    row.innerHTML = `<div class="p-key">${k}</div><div class="p-val">${escHtml(String(v))}</div>`;
    el.appendChild(row);
  });
}

function fmt(val) {
  if (val == null || val === '') return '--';
  const n = parseFloat(val);
  if (isNaN(n)) return String(val);
  if (n >= 10000) return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (n >= 1)     return n.toFixed(4);
  return n.toPrecision(6);
}

function escHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Boot ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
