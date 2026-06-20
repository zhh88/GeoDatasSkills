from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .models import UnifiedDataSet
from .output import dataset_to_dict
from .rules import OutputRules


def export_html_report(dataset: UnifiedDataSet, path: str | Path, *, title: str = "GeoDatasSkills Report") -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = dataset_to_dict(dataset, OutputRules(mode="standard", summary=True, include_report=True, drop_empty=True))
    target.write_text(render_html_report(data, title=title), encoding="utf-8")


def render_html_report(data: dict[str, Any], *, title: str) -> str:
    payload = json.dumps(_client_payload(data), ensure_ascii=False)
    summary = data.get("summary") or {}
    table_rows = _object_rows(data)
    safe_title = html.escape(title)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_title}</title>
  <style>
    body {{ margin:0; font-family: Arial, 'Microsoft YaHei', sans-serif; background:#f5f7fb; color:#172033; }}
    header {{ padding:22px 28px; background:#0f2747; color:white; }}
    h1 {{ margin:0; font-size:22px; }}
    main {{ padding:20px 28px 32px; display:grid; gap:18px; }}
    .cards {{ display:grid; grid-template-columns: repeat(6, minmax(120px, 1fr)); gap:10px; }}
    .card {{ background:white; border:1px solid #d8dee9; border-radius:8px; padding:13px; }}
    .card b {{ display:block; font-size:22px; margin-bottom:4px; }}
    .card span {{ color:#657084; font-size:12px; }}
    .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap:18px; }}
    section {{ background:white; border:1px solid #d8dee9; border-radius:8px; padding:16px; }}
    h2 {{ margin:0 0 12px; font-size:16px; }}
    canvas {{ width:100%; height:360px; border:1px solid #e2e8f0; background:#fbfdff; border-radius:6px; }}
    table {{ width:100%; border-collapse:collapse; font-size:12px; }}
    th, td {{ border-bottom:1px solid #e5e7eb; padding:8px; text-align:left; vertical-align:top; }}
    th {{ background:#f8fafc; color:#334155; }}
    .scroll {{ max-height:360px; overflow:auto; }}
    .events {{ max-height:240px; overflow:auto; font-family:Consolas, monospace; font-size:12px; background:#0f172a; color:#dbeafe; padding:10px; border-radius:6px; }}
    input[type=range] {{ width:100%; }}
    @media (max-width: 1100px) {{ .grid {{ grid-template-columns:1fr; }} .cards {{ grid-template-columns:repeat(2, 1fr); }} }}
  </style>
</head>
<body>
  <header><h1>{safe_title}</h1><div>统一时空模型输出、空间预览、三维表达与时效性视图</div></header>
  <main>
    <div class="cards">
      {_card("对象数", summary.get("object_count"))}
      {_card("输入数", summary.get("input_count"))}
      {_card("过滤数", summary.get("filtered_count"))}
      {_card("修复数", summary.get("repaired_count"))}
      {_card("无效数", summary.get("invalid_count"))}
      {_card("模态数", summary.get("modality_count"))}
    </div>
    <div class="grid">
      <section><h2>二维空间预览</h2><canvas id="map"></canvas></section>
      <section><h2>三维数值预览</h2><canvas id="bars"></canvas></section>
    </div>
    <section>
      <h2>时间动态视图</h2>
      <input id="timeSlider" type="range" min="0" max="100" value="100" />
      <canvas id="time"></canvas>
    </section>
    <section>
      <h2>对象表格</h2>
      <div class="scroll"><table><thead><tr><th>ID</th><th>Geometry</th><th>Time</th><th>Attributes</th><th>Quality</th></tr></thead><tbody>{table_rows}</tbody></table></div>
    </section>
    <section>
      <h2>转换事件</h2>
      <div class="events">{_events(data)}</div>
    </section>
  </main>
  <script>
    const DATA = {payload};
    const colors = ['#2563eb', '#16a34a', '#f59e0b', '#dc2626'];
    function resizeCanvas(c) {{ c.width = c.clientWidth * devicePixelRatio; c.height = c.clientHeight * devicePixelRatio; const ctx=c.getContext('2d'); ctx.setTransform(devicePixelRatio,0,0,devicePixelRatio,0,0); return ctx; }}
    function pointOf(obj) {{
      const g = obj.geometry || {{}};
      const c = g.coordinates || [];
      if (g.type === 'point' && c.length >= 2) return [Number(c[0]), Number(c[1]), Number(c[2]||0)];
      if ((g.type === 'polygon' || g.type === 'line' || g.type === 'trajectory') && Array.isArray(c)) {{
        const pts = [];
        const walk = v => Array.isArray(v) && typeof v[0] === 'number' ? pts.push(v) : Array.isArray(v) && v.forEach(walk);
        walk(c); if (!pts.length) return null;
        return [pts.reduce((s,p)=>s+p[0],0)/pts.length, pts.reduce((s,p)=>s+p[1],0)/pts.length, 0];
      }}
      return null;
    }}
    const objects = DATA.objects.map(o => ({{...o, point: pointOf(o)}})).filter(o => o.point);
    const xs = objects.map(o=>o.point[0]), ys = objects.map(o=>o.point[1]);
    const bounds = {{ minX: Math.min(...xs), maxX: Math.max(...xs), minY: Math.min(...ys), maxY: Math.max(...ys) }};
    function project(p, c) {{
      const pad = 24, w = c.clientWidth, h = c.clientHeight;
      const x = pad + (p[0]-bounds.minX)/((bounds.maxX-bounds.minX)||1)*(w-pad*2);
      const y = h - pad - (p[1]-bounds.minY)/((bounds.maxY-bounds.minY)||1)*(h-pad*2);
      return [x,y];
    }}
    function drawMap() {{
      const c=document.getElementById('map'), ctx=resizeCanvas(c); ctx.clearRect(0,0,c.clientWidth,c.clientHeight);
      objects.forEach((o,i)=>{{ const [x,y]=project(o.point,c); ctx.fillStyle=colors[i%colors.length]; ctx.beginPath(); ctx.arc(x,y,5,0,Math.PI*2); ctx.fill(); }});
    }}
    function drawBars() {{
      const c=document.getElementById('bars'), ctx=resizeCanvas(c); ctx.clearRect(0,0,c.clientWidth,c.clientHeight);
      objects.forEach((o,i)=>{{ const [x,y]=project(o.point,c); const attrs=o.attributes||{{}}; const val=Number(attrs.risk||attrs.value||o.point[2]||10); const h=Math.max(8, Math.min(140, val)); ctx.strokeStyle=colors[i%colors.length]; ctx.lineWidth=6; ctx.beginPath(); ctx.moveTo(x,y); ctx.lineTo(x,y-h); ctx.stroke(); ctx.fillStyle=ctx.strokeStyle; ctx.fillRect(x-4,y-h-4,8,8); }});
    }}
    function timeValue(o) {{ const t=o.time||{{}}; return t.timestamp || (t.timestamps && t.timestamps[0]) || null; }}
    function drawTime() {{
      const c=document.getElementById('time'), ctx=resizeCanvas(c); ctx.clearRect(0,0,c.clientWidth,c.clientHeight);
      const dated = objects.map(o=>({{...o,t:timeValue(o)}})).filter(o=>o.t); if(!dated.length) {{ ctx.fillText('无时间字段', 20, 30); return; }}
      const min=Math.min(...dated.map(o=>o.t)), max=Math.max(...dated.map(o=>o.t)); const cutoff=min+(max-min)*(document.getElementById('timeSlider').value/100);
      dated.forEach((o,i)=>{{ const x=20+(o.t-min)/((max-min)||1)*(c.clientWidth-40); const y=c.clientHeight/2; ctx.fillStyle=o.t<=cutoff?colors[i%colors.length]:'#cbd5e1'; ctx.beginPath(); ctx.arc(x,y,6,0,Math.PI*2); ctx.fill(); }});
    }}
    document.getElementById('timeSlider').addEventListener('input', drawTime);
    addEventListener('resize', ()=>{{drawMap();drawBars();drawTime();}});
    drawMap(); drawBars(); drawTime();
  </script>
</body>
</html>"""


def _client_payload(data: dict[str, Any]) -> dict[str, Any]:
    return {"objects": data.get("objects") or [], "summary": data.get("summary") or {}, "report": data.get("report") or {}}


def _card(label: str, value: Any) -> str:
    return f"<div class='card'><b>{html.escape(str(value if value is not None else 0))}</b><span>{html.escape(label)}</span></div>"


def _object_rows(data: dict[str, Any]) -> str:
    rows = []
    for obj in (data.get("objects") or [])[:200]:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(obj.get('id', '')))}</td>"
            f"<td>{html.escape((obj.get('geometry') or {}).get('type', ''))}</td>"
            f"<td>{html.escape(json.dumps(obj.get('time'), ensure_ascii=False) if obj.get('time') else '')}</td>"
            f"<td>{html.escape(json.dumps(obj.get('attributes') or {}, ensure_ascii=False)[:320])}</td>"
            f"<td>{html.escape(json.dumps(obj.get('quality') or {}, ensure_ascii=False)[:220])}</td>"
            "</tr>"
        )
    return "".join(rows)


def _events(data: dict[str, Any]) -> str:
    events = ((data.get("report") or {}).get("events") or [])[:300]
    if not events:
        return "No transform events."
    return "<br/>".join(html.escape(f"[{e.get('level')}] {e.get('code')}: {e.get('message')}") for e in events)
