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
<title>Phishing Simulation Report - {name}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; color: #1b1f23; }}
  h1 {{ margin-bottom: .2rem; }}
  h2 {{ margin-top: 2rem; font-size: 1.05rem; color: #57606a; }}
  .meta {{ color: #57606a; margin-bottom: 1.5rem; }}
  .kpis {{ display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; }}
  .kpi {{ background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px;
           padding: .75rem 1.25rem; min-width: 130px; }}
  .kpi .val {{ font-size: 1.6rem; font-weight: 700; }}
  .kpi .label {{ font-size: .8rem; color: #57606a; }}
  .kpi.danger .val {{ color: #cf222e; }}
  .kpi.warn .val {{ color: #9a6700; }}
  .kpi.ok .val {{ color: #1a7f37; }}
  .charts {{ display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.5rem; }}
  .charts img {{ max-width: 100%; border: 1px solid #d0d7de; border-radius: 6px; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
  th, td {{ border: 1px solid #d0d7de; padding: .5rem .75rem; text-align: left; }}
  th {{ background: #f6f8fa; }}
  tr.submitted {{ background: #ffeef0; }}
  tr.clicked {{ background: #fff8e6; }}
  .rec {{ border-left: 4px solid {rec_color}; background: #f6f8fa;
          padding: .9rem 1rem; border-radius: 0 4px 4px 0; margin-top: 1rem; }}
  .rec strong {{ color: {rec_color}; }}
  .lab-banner {{ background: #1b1f23; color: #f0f2f5; padding: .5rem 1rem;
                 font-size: .8rem; border-radius: 4px; margin-bottom: 1.5rem; }}
</style>
</head>
<body>
  <div class="lab-banner">LAB SIMULATION - Authorized security-awareness exercise only -
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
  <div class="charts">{charts}</div>

  <h2>Recipient detail</h2>
  <table>
    <thead><tr><th>Name</th><th>Email</th><th>Clicked at</th><th>Submitted at</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>Training recommendation</h2>
  <div class="rec"><strong>{rec_level}</strong> &mdash; {rec_text}</div>
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
