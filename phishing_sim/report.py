"""Renders campaign results as a console summary, CSV, or HTML report
with awareness training recommendations and embedded charts."""

from __future__ import annotations

import base64
import csv
import html
import io
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .models import Campaign, Recipient

# Awareness training recommendations keyed to click/submit rate bands
_RECS = [
    (0.50, "critical",
     "More than half of recipients submitted credentials. Immediate, mandatory "
     "security-awareness training is warranted. Consider restricting access to "
     "sensitive systems until training is complete."),
    (0.30, "high",
     "A significant portion of recipients submitted credentials. Schedule "
     "department-wide phishing awareness training within two weeks and increase "
     "the frequency of simulated exercises."),
    (0.10, "medium",
     "A moderate number of recipients were caught. Targeted awareness coaching "
     "for affected individuals is recommended, plus a follow-up simulation in "
     "30 days to measure improvement."),
    (0.0,  "low",
     "Submit rate is low. Maintain regular awareness exercises (quarterly) to "
     "keep vigilance high and monitor for any increase in click rates over time."),
]


def _recommendation(submit_rate: float) -> tuple[str, str]:
    for threshold, level, text in _RECS:
        if submit_rate >= threshold:
            return level, text
    return "low", _RECS[-1][2]


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "-"


# ----------------------------------------------------------------- console

def to_console(campaign: Campaign) -> str:
    lines = [
        f"Campaign : {campaign.name}",
        f"Template : {campaign.template}",
        f"Created  : {_fmt(campaign.created_at)}",
        f"Recipients: {len(campaign.recipients)}",
        f"Clicked  : {campaign.click_count} ({campaign.click_rate:.0%})",
        f"Submitted: {campaign.submit_count} ({campaign.submit_rate:.0%})",
        "",
    ]

    if not campaign.recipients:
        return "\n".join(lines) + "No recipients."

    headers = ["Name", "Email", "Clicked", "Submitted"]
    table = [headers] + [
        [r.name, r.email, _fmt(r.clicked_at), _fmt(r.submitted_at)]
        for r in campaign.recipients
    ]
    widths = [max(len(str(row[i])) for row in table) for i in range(4)]
    for idx, row in enumerate(table):
        lines.append(" | ".join(str(c).ljust(widths[j]) for j, c in enumerate(row)))
        if idx == 0:
            lines.append("-+-".join("-" * w for w in widths))

    level, rec = _recommendation(campaign.submit_rate)
    lines += ["", f"Recommendation ({level.upper()}): {rec}"]
    return "\n".join(lines)


# --------------------------------------------------------------------- csv

def to_csv(campaign: Campaign) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["campaign", "name", "email", "clicked_at", "submitted_at"])
    for r in campaign.recipients:
        writer.writerow([campaign.name, r.name, r.email,
                         _fmt(r.clicked_at), _fmt(r.submitted_at)])
    return buf.getvalue()


# -------------------------------------------------------------------- charts

def _fig_to_data_uri(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _funnel_chart(campaign: Campaign) -> str | None:
    n = len(campaign.recipients)
    if not n:
        return None
    stages = ["Sent", "Clicked", "Submitted"]
    counts = [n, campaign.click_count, campaign.submit_count]
    colors = ["#0969da", "#9a6700", "#cf222e"]

    fig, ax = plt.subplots(figsize=(5.5, 3.2))
    bars = ax.barh(stages[::-1], counts[::-1], color=colors[::-1])
    for bar, count in zip(bars, counts[::-1]):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                str(count), va="center", fontsize=9)
    ax.set_xlabel("Recipient count")
    ax.set_title("Campaign funnel")
    ax.set_xlim(0, n * 1.15)
    fig.tight_layout()
    return _fig_to_data_uri(fig)


def _timeline_chart(campaign: Campaign) -> str | None:
    clicks = [r.clicked_at for r in campaign.recipients if r.clicked_at]
    submits = [r.submitted_at for r in campaign.recipients if r.submitted_at]
    if not clicks and not submits:
        return None

    fig, ax = plt.subplots(figsize=(5.5, 3.2))
    if clicks:
        ax.scatter(clicks, ["Click"] * len(clicks), color="#9a6700", s=50, label="click", zorder=3)
    if submits:
        ax.scatter(submits, ["Submit"] * len(submits), color="#cf222e", s=50, label="submit", zorder=3)
    ax.set_title("Event timeline")
    ax.grid(axis="x", linestyle=":", alpha=0.5)
    ax.legend(fontsize=8)
    fig.autofmt_xdate()
    fig.tight_layout()
    return _fig_to_data_uri(fig)


# -------------------------------------------------------------------- html

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phishing Simulation Report - {name}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
    background: #f5f5f7;
    margin: 0;
    padding: 2.5rem 1.5rem 5rem;
    color: #1d1d1f;
    -webkit-font-smoothing: antialiased;
  }}
  .container {{ max-width: 1040px; margin: 0 auto; }}
  h1 {{
    font-size: 2.2rem;
    font-weight: 700;
    letter-spacing: -0.025em;
    margin: 0 0 0.4rem;
  }}
  h2 {{
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #6e6e73;
    margin: 2.5rem 0 0.8rem;
  }}
  .meta {{
    font-size: 0.88rem;
    color: #6e6e73;
    margin: 0 0 1rem;
  }}
  .lab-banner {{
    background: #1d1d1f;
    color: rgba(255,255,255,.82);
    padding: 0.55rem 1.1rem;
    font-size: 0.78rem;
    border-radius: 10px;
    margin-bottom: 2rem;
    letter-spacing: 0.01em;
  }}
  .kpis {{ display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 0.5rem; }}
  .kpi {{
    background: #fff;
    border-radius: 14px;
    padding: 1rem 1.5rem;
    min-width: 130px;
    box-shadow: 0 2px 10px rgba(0,0,0,.06);
  }}
  .kpi .val {{
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    line-height: 1;
  }}
  .kpi .label {{ font-size: 0.75rem; color: #6e6e73; margin-top: 0.3rem; }}
  .kpi.danger .val {{ color: #ff3b30; }}
  .kpi.warn .val   {{ color: #ff9500; }}
  .kpi.ok .val     {{ color: #34c759; }}
  .card {{
    background: #fff;
    border-radius: 18px;
    box-shadow: 0 2px 14px rgba(0,0,0,.06);
    overflow: hidden;
    margin-bottom: 1rem;
  }}
  .charts {{ display: flex; flex-wrap: wrap; gap: 1rem; padding: 1.5rem; }}
  .charts img {{ max-width: 100%; border-radius: 10px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.88rem; }}
  th {{
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #6e6e73;
    padding: 0.85rem 1.25rem;
    text-align: left;
    background: #fafafa;
    border-bottom: 1px solid #f0f0f0;
    white-space: nowrap;
  }}
  td {{
    padding: 0.85rem 1.25rem;
    border-bottom: 1px solid #f5f5f7;
    vertical-align: top;
  }}
  tr:last-child td {{ border-bottom: none; }}
  tr.submitted {{ background: rgba(255,59,48,.045); }}
  tr.clicked   {{ background: rgba(255,149,0,.045); }}
  .rec {{
    background: #fff;
    border-radius: 14px;
    padding: 1.2rem 1.5rem;
    box-shadow: 0 2px 10px rgba(0,0,0,.06);
    border-left: 4px solid {rec_color};
  }}
  .rec strong {{ color: {rec_color}; }}
</style>
</head>
<body>
<div class="container">
  <div class="lab-banner">LAB SIMULATION &mdash; Authorized security-awareness exercise only &mdash;
    No real credentials were captured.</div>
  <h1>Phishing Simulation Report</h1>
  <p class="meta">Campaign: <strong>{name}</strong> &middot; Template: {template}
     &middot; Generated {generated}</p>

  <div class="kpis">
    <div class="kpi"><div class="val">{total}</div><div class="label">Recipients</div></div>
    <div class="kpi {click_cls}"><div class="val">{click_pct}</div><div class="label">Click rate</div></div>
    <div class="kpi {submit_cls}"><div class="val">{submit_pct}</div><div class="label">Submit rate</div></div>
  </div>

  <h2>Overview</h2>
  <div class="card"><div class="charts">{charts}</div></div>

  <h2>Recipient detail</h2>
  <div class="card">
    <table>
      <thead><tr><th>Name</th><th>Email</th><th>Clicked at</th><th>Submitted at</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>

  <h2>Training recommendation</h2>
  <div class="rec"><strong>{rec_level}</strong> &mdash; {rec_text}</div>
</div>
</body>
</html>
"""

_REC_COLORS = {"critical": "#82071e", "high": "#cf222e", "medium": "#9a6700", "low": "#1a7f37"}
_RATE_CLASS = lambda r: "danger" if r >= 0.30 else ("warn" if r >= 0.10 else "ok")


def to_html(campaign: Campaign) -> str:
    level, rec_text = _recommendation(campaign.submit_rate)

    charts_html = "\n".join(
        f'<figure><img src="{uri}" alt="{title}"></figure>'
        for title, uri in [
            ("Campaign funnel", _funnel_chart(campaign)),
            ("Event timeline", _timeline_chart(campaign)),
        ]
        if uri
    ) or "<p>No events recorded yet.</p>"

    body_rows = []
    for r in campaign.recipients:
        cls = "submitted" if r.submitted_at else ("clicked" if r.clicked_at else "")
        body_rows.append(
            f'<tr class="{cls}"><td>{html.escape(r.name)}</td>'
            f'<td>{html.escape(r.email)}</td>'
            f'<td>{_fmt(r.clicked_at)}</td>'
            f'<td>{_fmt(r.submitted_at)}</td></tr>'
        )
    if not body_rows:
        body_rows.append('<tr><td colspan="4">No recipients.</td></tr>')

    return _HTML.format(
        name=html.escape(campaign.name),
        template=html.escape(campaign.template),
        generated=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        total=len(campaign.recipients),
        click_pct=f"{campaign.click_rate:.0%}",
        submit_pct=f"{campaign.submit_rate:.0%}",
        click_cls=_RATE_CLASS(campaign.click_rate),
        submit_cls=_RATE_CLASS(campaign.submit_rate),
        charts=charts_html,
        rows="\n".join(body_rows),
        rec_level=level.upper(),
        rec_text=html.escape(rec_text),
        rec_color=_REC_COLORS[level],
    )
