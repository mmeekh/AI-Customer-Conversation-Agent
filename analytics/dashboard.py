"""
Analytics dashboard for the AI Customer Conversation Agent.

Single-file FastAPI app that serves:
  - JSON endpoints (/api/*) the front-end consumes
  - One static HTML page that renders the modern dashboard

The HTML uses Tailwind CDN + Chart.js — zero build step, but a real,
production-looking dashboard with KPIs, time-series, distributions,
and a live event stream.
"""
from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

from analytics.metrics import MetricsCollector

app = FastAPI(title="AI Agent Analytics", docs_url="/api/docs")
metrics = MetricsCollector()


# --------------------------------------------------------------------------- #
# JSON API                                                                     #
# --------------------------------------------------------------------------- #

@app.get("/api/summary")
def summary(days: int = Query(7, ge=1, le=90)):
    s = metrics.summary(days=days)
    s["percentiles"] = metrics.percentiles(days=days)
    return JSONResponse(s)


@app.get("/api/trend")
def trend(days: int = Query(14, ge=2, le=90)):
    return JSONResponse(metrics.daily_trend(days=days))


@app.get("/api/response-histogram")
def response_histogram(days: int = Query(7, ge=1, le=90)):
    return JSONResponse(metrics.response_time_histogram(days=days))


@app.get("/api/events")
def events(limit: int = Query(50, ge=1, le=500)):
    return JSONResponse(metrics.recent_events(limit=limit))


# --------------------------------------------------------------------------- #
# Dashboard HTML (zero-build, single file)                                     #
# --------------------------------------------------------------------------- #

DASHBOARD_HTML = """<!doctype html>
<html lang="en" class="h-full">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI Agent · Analytics</title>
  <meta name="description" content="Live analytics for the multi-channel AI customer conversation agent: volume, escalation rate, sentiment trend, intent breakdown, response-time distribution." />
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><text y='26' font-size='28'>🤖</text></svg>" />
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            ink:   { 950: '#08090c', 900: '#0d0f14', 800: '#13161d', 700: '#1c2029', 600: '#272d3a' },
            line:  { DEFAULT: '#272d3a', soft: '#1c2029' },
            text:  { primary: '#e8eaf0', secondary: '#9ba3b4', muted: '#5b6478' },
            accent:{ primary: '#7c5cff', success: '#1bd99c', warn: '#ffb648', danger: '#ff5f7e', info: '#3eb1ff' },
          },
          fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui'] },
        }
      }
    }
  </script>
  <link rel="preconnect" href="https://rsms.me/" />
  <link rel="stylesheet" href="https://rsms.me/inter/inter.css" />
  <style>
    html, body { background: #08090c; }
    .card { background: linear-gradient(180deg, #13161d 0%, #0f1218 100%); border: 1px solid #272d3a; border-radius: 14px; box-shadow: 0 1px 0 0 rgba(255,255,255,0.04) inset, 0 8px 32px rgba(0,0,0,0.32); }
    .chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; letter-spacing: 0.02em; }
    .ring-dot { width: 8px; height: 8px; border-radius: 999px; box-shadow: 0 0 0 4px rgba(124,92,255,0.18); }
    .nav-btn[data-active="true"] { background: rgba(124,92,255,0.14); color: #e8eaf0; border-color: rgba(124,92,255,0.4); }
    .scroll-thin::-webkit-scrollbar { width: 6px; height: 6px; }
    .scroll-thin::-webkit-scrollbar-thumb { background: #272d3a; border-radius: 999px; }
  </style>
</head>
<body class="h-full text-text-primary font-sans antialiased">
  <div class="min-h-full">
    <!-- ============== Top bar ============== -->
    <header class="sticky top-0 z-30 backdrop-blur bg-ink-950/80 border-b border-line">
      <div class="max-w-7xl mx-auto px-5 lg:px-8 h-16 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-accent-primary to-accent-info flex items-center justify-center text-white text-base font-bold">🤖</div>
          <div>
            <div class="text-sm font-semibold tracking-tight">AI Agent · Analytics</div>
            <div class="text-[11px] text-text-secondary -mt-0.5">Multi-channel · live</div>
          </div>
        </div>

        <nav class="hidden md:flex items-center gap-1 bg-ink-800 border border-line rounded-full p-1 text-xs">
          <button class="nav-btn px-3 py-1.5 rounded-full border border-transparent text-text-secondary hover:text-text-primary transition" data-range="1"  data-active="false">24h</button>
          <button class="nav-btn px-3 py-1.5 rounded-full border border-transparent text-text-secondary hover:text-text-primary transition" data-range="7"  data-active="true">7d</button>
          <button class="nav-btn px-3 py-1.5 rounded-full border border-transparent text-text-secondary hover:text-text-primary transition" data-range="14" data-active="false">14d</button>
          <button class="nav-btn px-3 py-1.5 rounded-full border border-transparent text-text-secondary hover:text-text-primary transition" data-range="30" data-active="false">30d</button>
        </nav>

        <div class="flex items-center gap-3">
          <span class="chip bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"><span class="ring-dot bg-emerald-400"></span>Live</span>
          <span id="lastRefresh" class="hidden md:inline text-[11px] text-text-muted">just now</span>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-5 lg:px-8 py-8 space-y-6">

      <!-- ============== KPI Row ============== -->
      <section class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div class="card p-4 sm:p-5 min-w-0">
          <div class="text-[10px] sm:text-[11px] uppercase tracking-wider text-text-secondary font-semibold">Messages</div>
          <div class="mt-2 flex items-baseline gap-2 flex-wrap min-w-0">
            <div id="kpiMessages" class="text-2xl sm:text-3xl font-bold tabular-nums truncate">—</div>
            <div class="text-[11px] text-text-muted whitespace-nowrap">last <span data-window>7d</span></div>
          </div>
          <div class="mt-3 h-1 bg-ink-700 rounded overflow-hidden"><div id="bar-messages" class="h-full bg-accent-primary" style="width:0%"></div></div>
        </div>

        <div class="card p-4 sm:p-5 min-w-0">
          <div class="text-[10px] sm:text-[11px] uppercase tracking-wider text-text-secondary font-semibold">Escalation rate</div>
          <div class="mt-2 flex items-baseline gap-2 flex-wrap min-w-0">
            <div id="kpiEscalation" class="text-2xl sm:text-3xl font-bold tabular-nums truncate">—</div>
            <div id="kpiEscalationDot" class="text-[10px] text-text-muted whitespace-nowrap">target &lt; 15%</div>
          </div>
          <div class="mt-3 h-1 bg-ink-700 rounded overflow-hidden"><div id="bar-escalation" class="h-full bg-accent-warn" style="width:0%"></div></div>
        </div>

        <div class="card p-4 sm:p-5 min-w-0">
          <div class="text-[10px] sm:text-[11px] uppercase tracking-wider text-text-secondary font-semibold">Avg sentiment</div>
          <div class="mt-2 flex items-baseline gap-2 flex-wrap min-w-0">
            <div id="kpiSentiment" class="text-2xl sm:text-3xl font-bold tabular-nums">—</div>
            <div id="kpiSentimentBadge" class="chip whitespace-nowrap"></div>
          </div>
          <div class="mt-3 h-1 bg-ink-700 rounded relative overflow-hidden">
            <div class="absolute inset-y-0 left-1/2 w-px bg-line"></div>
            <div id="bar-sentiment" class="absolute inset-y-0 bg-accent-success" style="left:50%;width:0%"></div>
          </div>
        </div>

        <!-- Response Time spans both mobile columns (3 numbers don't fit half-width) -->
        <div class="card p-4 sm:p-5 col-span-2 lg:col-span-1 min-w-0">
          <div class="text-[10px] sm:text-[11px] uppercase tracking-wider text-text-secondary font-semibold">Response time</div>
          <div class="mt-2 flex items-end gap-4 sm:gap-3 flex-wrap">
            <div class="min-w-0">
              <div class="text-2xl sm:text-3xl font-bold tabular-nums leading-none" id="kpiAvgMs">—</div>
              <div class="text-[10px] text-text-muted mt-1">avg</div>
            </div>
            <div class="min-w-0">
              <div class="text-lg sm:text-base font-semibold text-text-secondary tabular-nums leading-none" id="kpiP50">—</div>
              <div class="text-[10px] text-text-muted mt-1">p50</div>
            </div>
            <div class="min-w-0">
              <div class="text-lg sm:text-base font-semibold text-text-secondary tabular-nums leading-none" id="kpiP95">—</div>
              <div class="text-[10px] text-text-muted mt-1">p95</div>
            </div>
          </div>
          <div class="mt-3 text-[10px] text-text-muted">Lower is better · target p95 &lt; 4 s</div>
        </div>
      </section>

      <!-- ============== Trend chart + Intent breakdown ============== -->
      <section class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div class="card p-5 lg:col-span-2">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="text-sm font-semibold">Daily volume</h3>
              <p class="text-[11px] text-text-secondary">Total messages & escalations</p>
            </div>
            <div class="flex items-center gap-3 text-[11px]">
              <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-sm bg-accent-primary"></span>Messages</span>
              <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-sm bg-accent-warn"></span>Escalated</span>
            </div>
          </div>
          <div class="relative h-72"><canvas id="trendChart"></canvas></div>
        </div>

        <div class="card p-5">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="text-sm font-semibold">Intent breakdown</h3>
              <p class="text-[11px] text-text-secondary">Where the workload lives</p>
            </div>
          </div>
          <div class="relative h-44"><canvas id="intentChart"></canvas></div>
          <div id="intentLegend" class="mt-4 grid grid-cols-2 gap-2 text-[12px]"></div>
        </div>
      </section>

      <!-- ============== Distribution + Channels + Sentiment ============== -->
      <section class="grid grid-cols-1 lg:grid-cols-3 gap-4">

        <div class="card p-5">
          <h3 class="text-sm font-semibold">Response-time distribution</h3>
          <p class="text-[11px] text-text-secondary mb-4">How fast the agent replied</p>
          <div class="relative h-56"><canvas id="responseChart"></canvas></div>
        </div>

        <div class="card p-5">
          <h3 class="text-sm font-semibold">Channels</h3>
          <p class="text-[11px] text-text-secondary mb-4">Volume per integration</p>
          <div id="channelList" class="space-y-3"></div>
        </div>

        <div class="card p-5">
          <h3 class="text-sm font-semibold">Sentiment trend</h3>
          <p class="text-[11px] text-text-secondary mb-4">Average per day · -1 to +1</p>
          <div class="relative h-56"><canvas id="sentimentChart"></canvas></div>
        </div>
      </section>

      <!-- ============== Recent events stream ============== -->
      <section class="card overflow-hidden">
        <div class="flex items-center justify-between p-5 border-b border-line">
          <div>
            <h3 class="text-sm font-semibold">Recent events</h3>
            <p class="text-[11px] text-text-secondary">Stream of the last 50 conversations</p>
          </div>
          <span class="chip bg-ink-700 text-text-secondary border border-line"><span class="w-1.5 h-1.5 rounded-full bg-accent-success"></span>auto-refresh 60 s</span>
        </div>
        <div class="overflow-x-auto scroll-thin">
          <table class="min-w-full text-sm">
            <thead class="text-[11px] uppercase tracking-wider text-text-muted bg-ink-800/60">
              <tr class="text-left">
                <th class="px-5 py-3 font-medium">Thread</th>
                <th class="px-5 py-3 font-medium">Channel</th>
                <th class="px-5 py-3 font-medium">Intent</th>
                <th class="px-5 py-3 font-medium">Sentiment</th>
                <th class="px-5 py-3 font-medium text-right">Response</th>
                <th class="px-5 py-3 font-medium text-right">When</th>
                <th class="px-5 py-3 font-medium text-center">Esc.</th>
              </tr>
            </thead>
            <tbody id="eventTable" class="divide-y divide-line/60"></tbody>
          </table>
        </div>
      </section>

      <footer class="text-center text-[11px] text-text-muted py-6">
        Powered by FastAPI · Gemini · ChromaDB · designed for the engineer who owns it.
      </footer>
    </main>
  </div>

<script>
  const STATE = { range: 7 };
  const fmtNum  = (n) => Number(n || 0).toLocaleString('en-US');
  const fmtMs   = (n) => (n >= 1000 ? (n/1000).toFixed(2) + ' s' : Math.round(n) + ' ms');
  const fmtSign = (n) => (n >= 0 ? '+' : '') + Number(n).toFixed(2);
  const COLORS_INTENT = ['#7c5cff', '#3eb1ff', '#1bd99c', '#ffb648', '#ff5f7e', '#a78bfa', '#34d399'];

  Chart.defaults.color = '#9ba3b4';
  Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
  Chart.defaults.font.family = 'Inter, system-ui';

  function badgeForSentiment(v) {
    if (v >= 0.3)  return ['bg-emerald-500/10 text-emerald-300 border border-emerald-500/20', 'positive'];
    if (v <= -0.3) return ['bg-rose-500/10 text-rose-300 border border-rose-500/20', 'negative'];
    return ['bg-amber-500/10 text-amber-300 border border-amber-500/20', 'neutral'];
  }
  function intentColor(name) {
    let h = 0; for (const c of (name||'')) h = (h*31 + c.charCodeAt(0)) >>> 0;
    return COLORS_INTENT[h % COLORS_INTENT.length];
  }
  function relTime(iso) {
    const t = Date.parse(iso); if (!t) return '';
    const s = Math.max(0, (Date.now() - t) / 1000);
    if (s < 60)   return Math.floor(s) + 's ago';
    if (s < 3600) return Math.floor(s/60) + 'm ago';
    if (s < 86400)return Math.floor(s/3600) + 'h ago';
    return Math.floor(s/86400) + 'd ago';
  }

  let trendChart, intentChart, responseChart, sentimentChart;
  function initCharts() {
    const grid = { color: 'rgba(255,255,255,0.06)' };
    const tickColor = '#5b6478';

    trendChart = new Chart(document.getElementById('trendChart'), {
      type: 'bar',
      data: { labels: [], datasets: [
        { label: 'Messages',  data: [], backgroundColor: 'rgba(124,92,255,0.85)', borderRadius: 4, stack: 'a' },
        { label: 'Escalated', data: [], backgroundColor: 'rgba(255,182,72,0.9)',  borderRadius: 4, stack: 'b' },
      ]},
      options: { responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
        scales: { x: { grid: { display: false }, ticks: { color: tickColor } },
                  y: { grid, ticks: { color: tickColor, precision: 0 }, beginAtZero: true } } }
    });

    intentChart = new Chart(document.getElementById('intentChart'), {
      type: 'doughnut',
      data: { labels: [], datasets: [{ data: [], backgroundColor: COLORS_INTENT, borderColor: '#0d0f14', borderWidth: 3 }] },
      options: { responsive: true, maintainAspectRatio: false, cutout: '70%', plugins: { legend: { display: false } } }
    });

    responseChart = new Chart(document.getElementById('responseChart'), {
      type: 'bar',
      data: { labels: [], datasets: [{ data: [], backgroundColor: 'rgba(62,177,255,0.85)', borderRadius: 4 }] },
      options: { responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { grid: { display: false }, ticks: { color: tickColor } },
                  y: { grid, ticks: { color: tickColor, precision: 0 }, beginAtZero: true } } }
    });

    sentimentChart = new Chart(document.getElementById('sentimentChart'), {
      type: 'line',
      data: { labels: [], datasets: [{
        data: [], borderColor: '#1bd99c', backgroundColor: (c) => {
          const a = c.chart.ctx.createLinearGradient(0, 0, 0, 240);
          a.addColorStop(0, 'rgba(27,217,156,0.32)'); a.addColorStop(1, 'rgba(27,217,156,0)');
          return a;
        },
        borderWidth: 2, tension: 0.35, fill: true, pointRadius: 0,
      }]},
      options: { responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { grid: { display: false }, ticks: { color: tickColor } },
                  y: { grid, ticks: { color: tickColor }, suggestedMin: -1, suggestedMax: 1 } } }
    });
  }

  async function load() {
    const days = STATE.range;
    document.querySelectorAll('[data-window]').forEach(e => e.textContent = days + 'd');
    const [summary, trend, hist, events] = await Promise.all([
      fetch('/api/summary?days=' + days).then(r => r.json()),
      fetch('/api/trend?days=' + Math.max(days, 7)).then(r => r.json()),
      fetch('/api/response-histogram?days=' + days).then(r => r.json()),
      fetch('/api/events?limit=50').then(r => r.json()),
    ]);
    renderKPIs(summary);
    renderTrend(trend);
    renderIntent(summary.by_intent || {});
    renderChannels(summary.by_channel || {}, summary.total_messages || 0);
    renderResponse(hist);
    renderSentimentTrend(trend);
    renderEvents(events);
    document.getElementById('lastRefresh').textContent =
      'updated ' + new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }

  function renderKPIs(s) {
    const total  = s.total_messages || 0;
    const escRate= (s.escalation_rate || 0) * 100;
    const sent   = s.avg_sentiment || 0;
    const avgMs  = s.avg_response_ms || 0;

    document.getElementById('kpiMessages').textContent = fmtNum(total);
    document.getElementById('bar-messages').style.width = '100%';

    document.getElementById('kpiEscalation').textContent = escRate.toFixed(1) + '%';
    document.getElementById('bar-escalation').style.width = Math.min(100, escRate * 2) + '%';
    const dotEl = document.getElementById('kpiEscalationDot');
    dotEl.textContent = escRate < 15 ? 'on target' : 'over target';
    dotEl.className = 'text-[11px] ' + (escRate < 15 ? 'text-emerald-300' : 'text-rose-300');

    document.getElementById('kpiSentiment').textContent = fmtSign(sent);
    const [bClass, bLabel] = badgeForSentiment(sent);
    const badge = document.getElementById('kpiSentimentBadge');
    badge.className = 'chip ' + bClass; badge.textContent = bLabel;
    const pct = Math.min(50, Math.abs(sent) * 50);
    const bar = document.getElementById('bar-sentiment');
    bar.style.width = pct + '%';
    bar.style.left  = sent >= 0 ? '50%' : (50 - pct) + '%';
    bar.className   = 'absolute inset-y-0 ' + (sent >= 0 ? 'bg-accent-success' : 'bg-accent-danger');

    document.getElementById('kpiAvgMs').textContent = fmtMs(avgMs);
    document.getElementById('kpiP50').textContent = fmtMs((s.percentiles||{}).p50 || 0);
    document.getElementById('kpiP95').textContent = fmtMs((s.percentiles||{}).p95 || 0);
  }

  function renderTrend(rows) {
    const labels = rows.map(r => r.day.slice(5));
    trendChart.data.labels = labels;
    trendChart.data.datasets[0].data = rows.map(r => r.total);
    trendChart.data.datasets[1].data = rows.map(r => r.escalated);
    trendChart.update();
  }

  function renderIntent(byIntent) {
    const entries = Object.entries(byIntent).sort((a,b) => b[1] - a[1]);
    const labels = entries.map(e => e[0]);
    const data   = entries.map(e => e[1]);
    const colors = labels.map(intentColor);
    intentChart.data.labels = labels;
    intentChart.data.datasets[0].data = data;
    intentChart.data.datasets[0].backgroundColor = colors;
    intentChart.update();

    const total = data.reduce((s,x) => s + x, 0) || 1;
    document.getElementById('intentLegend').innerHTML = entries.map(([name, n], i) => {
      const pct = ((n / total) * 100).toFixed(0);
      return '<div class="flex items-center gap-2">' +
        '<span class="w-2 h-2 rounded-sm" style="background:' + colors[i] + '"></span>' +
        '<span class="capitalize text-text-secondary">' + name.replace(/_/g, ' ') + '</span>' +
        '<span class="ml-auto tabular-nums text-text-primary">' + pct + '%</span>' +
      '</div>';
    }).join('') || '<div class="text-text-muted">no data</div>';
  }

  function renderChannels(byChannel, total) {
    const max = Math.max(1, ...Object.values(byChannel || {}));
    const entries = Object.entries(byChannel).sort((a,b) => b[1] - a[1]);
    document.getElementById('channelList').innerHTML = entries.map(([name, n]) => {
      const w = Math.round((n / max) * 100);
      const pct = total ? ((n / total) * 100).toFixed(0) : 0;
      const icon = name === 'gmail' ? '✉️' : name === 'intercom' ? '💬' : name === 'slack' ? '💼' : '🔌';
      return '<div>' +
        '<div class="flex items-center justify-between text-sm">' +
          '<span class="flex items-center gap-2"><span>' + icon + '</span><span class="capitalize">' + name + '</span></span>' +
          '<span class="tabular-nums text-text-secondary">' + fmtNum(n) + ' <span class="text-text-muted">· ' + pct + '%</span></span>' +
        '</div>' +
        '<div class="mt-1.5 h-2 bg-ink-700 rounded overflow-hidden"><div class="h-full bg-gradient-to-r from-accent-primary to-accent-info" style="width:' + w + '%"></div></div>' +
      '</div>';
    }).join('') || '<div class="text-text-muted text-sm">no channels</div>';
  }

  function renderResponse(rows) {
    responseChart.data.labels = rows.map(r => r.bucket);
    responseChart.data.datasets[0].data = rows.map(r => r.count);
    responseChart.update();
  }

  function renderSentimentTrend(rows) {
    sentimentChart.data.labels = rows.map(r => r.day.slice(5));
    sentimentChart.data.datasets[0].data = rows.map(r => r.avg_sentiment);
    sentimentChart.update();
  }

  function renderEvents(rows) {
    document.getElementById('eventTable').innerHTML = rows.map(e => {
      const [bClass] = badgeForSentiment(e.sentiment || 0);
      const ic = intentColor(e.intent || 'general');
      const intentBg = 'style="background:' + ic + '22; color:' + ic + '"';
      const tid = (e.thread_id || '').slice(0, 12);
      return '<tr class="hover:bg-ink-800/60 transition">' +
        '<td class="px-5 py-3 font-mono text-[12px] text-text-secondary">' + tid + '</td>' +
        '<td class="px-5 py-3 capitalize">' + (e.channel || '—') + '</td>' +
        '<td class="px-5 py-3"><span class="chip" ' + intentBg + '>' + (e.intent || 'general').replace(/_/g,' ') + '</span></td>' +
        '<td class="px-5 py-3"><span class="chip ' + bClass + ' tabular-nums">' + fmtSign(e.sentiment || 0) + '</span></td>' +
        '<td class="px-5 py-3 text-right tabular-nums text-text-secondary">' + fmtMs(e.response_ms || 0) + '</td>' +
        '<td class="px-5 py-3 text-right text-text-muted">' + relTime(e.timestamp) + '</td>' +
        '<td class="px-5 py-3 text-center">' + (e.escalated ? '<span class="chip bg-rose-500/15 text-rose-300 border border-rose-500/20">⚠</span>' : '<span class="text-text-muted">—</span>') + '</td>' +
      '</tr>';
    }).join('') || '<tr><td class="px-5 py-8 text-center text-text-muted" colspan="7">No events yet — the agent will populate this once it starts running.</td></tr>';
  }

  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.nav-btn').forEach(b => b.dataset.active = 'false');
      btn.dataset.active = 'true';
      STATE.range = Number(btn.dataset.range);
      load();
    });
  });

  initCharts();
  load();
  setInterval(load, 60000);
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(DASHBOARD_HTML)
