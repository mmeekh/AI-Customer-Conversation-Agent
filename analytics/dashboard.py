"""
Tiny FastAPI dashboard exposing metrics + a simple HTML view.
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from analytics.metrics import MetricsCollector

app = FastAPI(title="Email Agent Analytics", docs_url="/api/docs")
metrics = MetricsCollector()


@app.get("/api/summary")
def summary(days: int = 7):
    return JSONResponse(metrics.summary(days=days))


@app.get("/api/events")
def events(limit: int = 50):
    return JSONResponse(metrics.recent_events(limit=limit))


@app.get("/", response_class=HTMLResponse)
def index():
    s = metrics.summary(days=7)
    rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in s["by_intent"].items()
    ) or "<tr><td colspan='2'>No data yet</td></tr>"
    return f"""
<!doctype html>
<html><head><title>Email Agent Analytics</title>
<style>
body{{font-family:system-ui;max-width:900px;margin:2rem auto;padding:0 1rem;color:#1a1a1a}}
.card{{background:#f7f7f8;border:1px solid #e5e5e5;border-radius:8px;padding:1.25rem;margin-bottom:1rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1rem}}
.metric{{font-size:1.75rem;font-weight:600}}
.label{{font-size:.85rem;color:#666;text-transform:uppercase;letter-spacing:.05em}}
table{{width:100%;border-collapse:collapse}}td,th{{padding:.5rem;border-bottom:1px solid #eee;text-align:left}}
</style></head>
<body>
<h1>Email Agent Analytics</h1>
<p>Last 7 days</p>
<div class="grid">
  <div class="card"><div class="label">Messages</div><div class="metric">{s['total_messages']}</div></div>
  <div class="card"><div class="label">Escalation Rate</div><div class="metric">{s['escalation_rate']:.1%}</div></div>
  <div class="card"><div class="label">Avg Sentiment</div><div class="metric">{s['avg_sentiment']:+.2f}</div></div>
  <div class="card"><div class="label">Avg Response</div><div class="metric">{s['avg_response_ms']:.0f}ms</div></div>
</div>
<div class="card"><h3>By Intent</h3><table><tr><th>Intent</th><th>Count</th></tr>{rows}</table></div>
</body></html>
"""
