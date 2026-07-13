#!/usr/bin/env python3
"""Build and validate the offline dashboard from the derived snapshot."""

from __future__ import annotations

import argparse
import html
import json
import math
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "11_insights/data/current_snapshot.json"
OUTPUT_PATH = ROOT / "dashboard.html"


def close_enough(actual: float, expected: float, tolerance: float = 0.05) -> bool:
    return math.isclose(actual, expected, abs_tol=tolerance)


def validate(data: dict) -> list[str]:
    errors: list[str] = []

    required_top_level = {
        "schema_version",
        "meta",
        "profile",
        "evidence_types",
        "headline_metrics",
        "growth",
        "nutrition_and_rhythm",
        "elimination",
        "dimensions",
        "followups",
        "recent_timeline",
        "source_links",
    }
    missing = required_top_level - data.keys()
    if missing:
        errors.append(f"Missing top-level keys: {', '.join(sorted(missing))}")
        return errors

    try:
        as_of = date.fromisoformat(data["meta"]["as_of"])
        birth = date.fromisoformat(data["profile"]["birth_date"])
    except (KeyError, ValueError) as exc:
        errors.append(f"Invalid profile date: {exc}")
        return errors

    age_days = (as_of - birth).days
    if age_days != data["profile"]["age_days_as_of"]:
        errors.append(
            f"age_days_as_of should be {age_days}, got "
            f"{data['profile']['age_days_as_of']}"
        )

    weights = data["growth"]["weight_history"]
    if len(weights) < 2:
        errors.append("At least two weight points are required")
    else:
        weight_dates = [date.fromisoformat(item["date"]) for item in weights]
        if weight_dates != sorted(weight_dates):
            errors.append("Weight history must be sorted by date")
        for item, observed_date in zip(weights, weight_dates):
            expected_age = (observed_date - birth).days
            if item["age_days"] != expected_age:
                errors.append(
                    f"Weight age mismatch for {item['date']}: "
                    f"expected {expected_age}, got {item['age_days']}"
                )

        first, last = weights[0], weights[-1]
        summary = data["growth"]["summary"]
        elapsed = (weight_dates[-1] - weight_dates[0]).days
        gain = last["weight_g"] - first["weight_g"]
        gain_percent = gain / first["weight_g"] * 100
        daily_gain = gain / elapsed
        checks = [
            (summary["elapsed_days_by_date"], elapsed, "growth elapsed days"),
            (summary["gain_g"], gain, "growth gain"),
            (summary["gain_percent"], gain_percent, "growth gain percent"),
            (summary["daily_gain_by_date_g"], daily_gain, "daily gain"),
            (data["profile"]["latest_weight_g"], last["weight_g"], "latest weight"),
        ]
        for actual, expected, label in checks:
            if not close_enough(float(actual), float(expected)):
                errors.append(f"{label} mismatch: expected {expected:.2f}, got {actual}")

    nutrition = data["nutrition_and_rhythm"]
    core = nutrition["core_window"]
    normalized_food = core["dry_food_consumed_g"] * 1440 / core["minutes"]
    if not close_enough(core["normalized_dry_food_g_per_24h"], normalized_food):
        errors.append("Normalized dry-food value does not match the core window")

    evening = nutrition["direct_evening_window"]
    evening_share = evening["consumed_g"] / core["dry_food_consumed_g"] * 100
    if not close_enough(evening["share_percent"], evening_share):
        errors.append("Evening food share does not match consumed grams")

    segments = nutrition["clock_segments"]
    segment_share = sum(item["share_percent"] for item in segments)
    if not close_enough(segment_share, 100, tolerance=0.2):
        errors.append(f"Clock-segment shares sum to {segment_share}, expected about 100")

    bowls = nutrition["water_bowls"]
    bowl_sum = bowls["white_bowl_loss_ml"] + bowls["yellow_bowl_loss_ml"]
    if not close_enough(bowls["gross_loss_ml"], bowl_sum):
        errors.append("Water-bowl total does not match both bowls")

    evidence_ids = {item["id"] for item in data["evidence_types"]}
    for metric in data["headline_metrics"]:
        if metric["evidence_type"] not in evidence_ids:
            errors.append(
                f"Unknown evidence type {metric['evidence_type']} in metric {metric['id']}"
            )

    source_paths: set[str] = set()
    source_paths.update(item["path"] for item in data["source_links"])
    source_paths.update(item["source"] for item in data["headline_metrics"])
    source_paths.add(data["growth"]["source"])
    source_paths.update(nutrition["sources"])
    source_paths.update(data["elimination"]["sources"])
    source_paths.update(item["source"] for item in data["followups"])
    source_paths.update(item["source"] for item in data["recent_timeline"])
    for clue in data["cross_dimension_clues"]:
        source_paths.update(clue["sources"])

    for source in sorted(source_paths):
        source_path = Path(source)
        if source_path.is_absolute() or ".." in source_path.parts:
            errors.append(f"Unsafe source path: {source}")
        elif not (ROOT / source_path).exists():
            errors.append(f"Missing source path: {source}")

    return errors


def json_for_script(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return payload.replace("</", "<\\/")


def render(data: dict) -> str:
    title = html.escape(data["meta"]["title"])
    as_of = html.escape(data["meta"]["as_of"])
    payload = json_for_script(data)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta name="description" content="小咪的离线生活档案与多维照护看板">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f3f6f2;
      --surface: #ffffff;
      --surface-soft: #eaf1ed;
      --ink: #17211c;
      --muted: #5d6b63;
      --line: #cdd8d1;
      --green: #27705c;
      --green-soft: #dbece5;
      --coral: #c85f49;
      --coral-soft: #f5ded8;
      --gold: #a77d20;
      --gold-soft: #f2e8c9;
      --blue: #397896;
      --blue-soft: #dcebf2;
      --purple: #775f8f;
      --purple-soft: #e9e0ef;
      --shadow: 0 8px 28px rgba(24, 45, 35, 0.08);
      --radius: 8px;
      --max: 1180px;
    }}

    @media (prefers-color-scheme: dark) {{
      :root {{
        color-scheme: dark;
        --bg: #101713;
        --surface: #17211b;
        --surface-soft: #1e2b24;
        --ink: #edf4ef;
        --muted: #aab9b0;
        --line: #33463b;
        --green: #72bca3;
        --green-soft: #233f35;
        --coral: #e5927f;
        --coral-soft: #4a2e28;
        --gold: #d7b85f;
        --gold-soft: #463c21;
        --blue: #7db3cf;
        --blue-soft: #263f4c;
        --purple: #b7a2cc;
        --purple-soft: #3d3346;
        --shadow: 0 10px 32px rgba(0, 0, 0, 0.24);
      }}
    }}

    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
        "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      font-size: 16px;
      line-height: 1.62;
      letter-spacing: 0;
    }}
    a {{ color: var(--green); text-underline-offset: 3px; }}
    a:hover {{ text-decoration-thickness: 2px; }}
    button, input {{ font: inherit; }}
    button:focus-visible, a:focus-visible, summary:focus-visible {{
      outline: 3px solid color-mix(in srgb, var(--green) 46%, transparent);
      outline-offset: 3px;
    }}
    .skip-link {{
      position: absolute;
      left: 16px;
      top: -80px;
      z-index: 10;
      padding: 8px 12px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 6px;
    }}
    .skip-link:focus {{ top: 12px; }}
    .shell {{ width: min(calc(100% - 32px), var(--max)); margin-inline: auto; }}

    .topbar {{
      border-bottom: 1px solid var(--line);
      background: color-mix(in srgb, var(--bg) 91%, transparent);
    }}
    .topbar-inner {{
      min-height: 64px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
    }}
    .brand {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      color: var(--ink);
      font-weight: 700;
      text-decoration: none;
      white-space: nowrap;
    }}
    .brand-mark {{
      width: 34px;
      height: 34px;
      display: grid;
      place-items: center;
      border-radius: 50%;
      background: var(--green-soft);
      color: var(--green);
    }}
    .brand-mark svg {{ width: 20px; height: 20px; }}
    nav {{ display: flex; gap: 4px; flex-wrap: wrap; justify-content: flex-end; }}
    nav a {{
      color: var(--muted);
      text-decoration: none;
      padding: 6px 9px;
      border-radius: 6px;
    }}
    nav a:hover {{ background: var(--surface-soft); color: var(--ink); }}

    .intro {{
      padding: 52px 0 38px;
      display: grid;
      grid-template-columns: minmax(0, 1.45fr) minmax(260px, 0.55fr);
      gap: 44px;
      align-items: end;
    }}
    .eyebrow {{
      margin: 0 0 9px;
      color: var(--green);
      font-size: 0.86rem;
      font-weight: 700;
      text-transform: uppercase;
    }}
    h1, h2, h3, p {{ margin-top: 0; }}
    h1 {{
      max-width: 760px;
      margin-bottom: 14px;
      font-size: 4.3rem;
      line-height: 1.06;
      letter-spacing: 0;
    }}
    h2 {{ margin-bottom: 8px; font-size: 2.25rem; line-height: 1.2; }}
    h3 {{ margin-bottom: 8px; font-size: 1.04rem; line-height: 1.35; }}
    .lede {{ max-width: 760px; margin-bottom: 0; color: var(--muted); font-size: 1.08rem; }}
    .profile-strip {{
      margin: 0;
      padding: 18px 0 2px 20px;
      border-left: 3px solid var(--green);
      display: grid;
      gap: 11px;
    }}
    .profile-strip div {{ display: grid; grid-template-columns: 90px 1fr; gap: 10px; }}
    .profile-strip dt {{ color: var(--muted); }}
    .profile-strip dd {{ margin: 0; font-weight: 650; }}

    main {{ padding-bottom: 80px; }}
    section {{ padding: 42px 0; border-top: 1px solid var(--line); }}
    .section-head {{
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 24px;
      margin-bottom: 24px;
    }}
    .section-head > div:first-child {{ max-width: 750px; }}
    .section-head p {{ margin-bottom: 0; color: var(--muted); }}
    .as-of {{ color: var(--muted); font-size: 0.88rem; white-space: nowrap; }}

    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }}
    .metric {{
      min-width: 0;
      padding: 17px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }}
    .metric-label {{ color: var(--muted); font-size: 0.86rem; }}
    .metric-value {{
      margin: 4px 0 2px;
      font-size: 2rem;
      font-weight: 760;
      line-height: 1.18;
      overflow-wrap: anywhere;
    }}
    .metric-meta {{ color: var(--muted); font-size: 0.8rem; }}
    .metric a {{ display: inline-block; margin-top: 8px; font-size: 0.8rem; }}

    .badge {{
      display: inline-flex;
      align-items: center;
      width: fit-content;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 0.76rem;
      font-weight: 700;
      white-space: nowrap;
    }}
    .badge-recorded {{ background: var(--green-soft); color: var(--green); }}
    .badge-observed {{ background: var(--blue-soft); color: var(--blue); }}
    .badge-estimated {{ background: var(--gold-soft); color: var(--gold); }}
    .badge-inferred {{ background: var(--purple-soft); color: var(--purple); }}
    .badge-reference {{ background: var(--coral-soft); color: var(--coral); }}

    .chart-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.55fr) minmax(260px, 0.45fr);
      gap: 28px;
      align-items: start;
    }}
    .chart-wrap {{
      position: relative;
      min-height: 360px;
      padding: 12px 0 0;
    }}
    #weight-chart {{ width: 100%; height: auto; display: block; overflow: visible; }}
    .chart-line {{ fill: none; stroke: var(--green); stroke-width: 3; }}
    .chart-area {{ fill: color-mix(in srgb, var(--green) 12%, transparent); }}
    .chart-gridline {{ stroke: var(--line); stroke-width: 1; }}
    .chart-axis-label, .chart-tick {{ fill: var(--muted); font-size: 12px; }}
    .chart-point {{ stroke: var(--surface); stroke-width: 3; fill: var(--green); }}
    .chart-point.estimated {{ fill: var(--surface); stroke: var(--gold); stroke-width: 3; }}
    .chart-value-label {{ fill: var(--ink); font-size: 12px; font-weight: 700; }}
    .chart-detail {{
      min-height: 48px;
      margin: 8px 0 0;
      color: var(--muted);
    }}
    .chart-detail strong {{ color: var(--ink); }}
    .segmented {{
      display: inline-flex;
      gap: 3px;
      padding: 3px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: var(--surface-soft);
    }}
    .segmented button, .filters button {{
      border: 0;
      border-radius: 5px;
      padding: 6px 10px;
      color: var(--muted);
      background: transparent;
      cursor: pointer;
    }}
    .segmented button[aria-pressed="true"], .filters button[aria-pressed="true"] {{
      background: var(--surface);
      color: var(--ink);
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
    }}
    .analysis-list {{ display: grid; gap: 18px; }}
    .analysis-item {{ padding-bottom: 18px; border-bottom: 1px solid var(--line); }}
    .analysis-item:last-child {{ border-bottom: 0; }}
    .analysis-item .value {{ font-size: 1.45rem; font-weight: 760; line-height: 1.2; }}
    .analysis-item p {{ margin-bottom: 0; color: var(--muted); }}

    details {{ margin-top: 16px; }}
    summary {{ color: var(--green); cursor: pointer; font-weight: 700; }}
    .table-wrap {{ overflow-x: auto; margin-top: 12px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
    th, td {{ padding: 9px 10px; text-align: left; border-bottom: 1px solid var(--line); white-space: nowrap; }}
    th {{ color: var(--muted); font-weight: 650; }}

    .rhythm-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr);
      gap: 32px;
      align-items: start;
    }}
    .rhythm-callout {{
      margin-bottom: 24px;
      padding-left: 18px;
      border-left: 3px solid var(--coral);
    }}
    .rhythm-callout strong {{ display: block; font-size: 1.35rem; line-height: 1.3; }}
    .stacked-bar {{
      display: flex;
      width: 100%;
      height: 42px;
      overflow: hidden;
      border-radius: 7px;
      background: var(--surface-soft);
    }}
    .stacked-segment {{ min-width: 2px; position: relative; }}
    .stacked-segment:nth-child(1) {{ background: var(--purple); }}
    .stacked-segment:nth-child(2) {{ background: var(--blue); }}
    .stacked-segment:nth-child(3) {{ background: var(--gold); }}
    .stacked-segment:nth-child(4) {{ background: var(--coral); }}
    .stacked-segment:nth-child(5) {{ background: var(--green); }}
    .legend {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px 14px;
      margin-top: 14px;
    }}
    .legend-item {{ display: grid; grid-template-columns: 12px 1fr auto; gap: 7px; align-items: center; font-size: 0.84rem; }}
    .swatch {{ width: 10px; height: 10px; border-radius: 2px; }}
    .legend-item:nth-child(1) .swatch {{ background: var(--purple); }}
    .legend-item:nth-child(2) .swatch {{ background: var(--blue); }}
    .legend-item:nth-child(3) .swatch {{ background: var(--gold); }}
    .legend-item:nth-child(4) .swatch {{ background: var(--coral); }}
    .legend-item:nth-child(5) .swatch {{ background: var(--green); }}
    .legend-value {{ color: var(--muted); }}
    .fine-print {{ margin-top: 12px; color: var(--muted); font-size: 0.82rem; }}
    .bowl-comparison {{ display: grid; gap: 14px; }}
    .bowl-row {{ display: grid; grid-template-columns: 76px 1fr 62px; gap: 10px; align-items: center; }}
    .bowl-track {{ height: 12px; background: var(--surface-soft); border-radius: 4px; overflow: hidden; }}
    .bowl-fill {{ height: 100%; background: var(--blue); border-radius: inherit; }}
    .bowl-row:nth-child(2) .bowl-fill {{ background: var(--gold); }}

    .dimension-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .dimension-card {{
      padding: 20px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }}
    .dimension-card dl {{ margin: 0; display: grid; gap: 13px; }}
    .dimension-card dt {{ color: var(--muted); font-size: 0.78rem; font-weight: 700; }}
    .dimension-card dd {{ margin: 2px 0 0; }}
    .dimension-card .next {{ padding-top: 12px; border-top: 1px solid var(--line); color: var(--green); font-weight: 650; }}

    .clues {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px 32px; margin-top: 34px; }}
    .clue {{ padding-top: 16px; border-top: 3px solid var(--line); }}
    .clue p {{ margin-bottom: 7px; }}
    .clue .limit {{ color: var(--muted); font-size: 0.86rem; }}

    .filters {{ display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 18px; }}
    .filters button {{ border: 1px solid var(--line); }}
    .followup-list {{ display: grid; gap: 10px; }}
    .followup {{
      display: grid;
      grid-template-columns: 118px minmax(0, 1fr) minmax(250px, 0.8fr);
      gap: 18px;
      align-items: start;
      padding: 17px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
    }}
    .followup[hidden] {{ display: none; }}
    .followup-state {{ display: grid; gap: 7px; justify-items: start; }}
    .attention {{ font-size: 0.78rem; color: var(--muted); }}
    .followup p {{ margin-bottom: 6px; color: var(--muted); }}
    .followup .action {{ color: var(--ink); }}
    .followup .escalate {{ color: var(--coral); font-size: 0.86rem; }}
    .followup a {{ font-size: 0.8rem; }}

    .timeline {{ position: relative; display: grid; gap: 0; }}
    .timeline::before {{
      content: "";
      position: absolute;
      left: 91px;
      top: 8px;
      bottom: 8px;
      width: 1px;
      background: var(--line);
    }}
    .timeline-item {{ display: grid; grid-template-columns: 74px 34px minmax(0, 1fr); gap: 0; padding: 0 0 24px; }}
    .timeline-date {{ color: var(--muted); font-size: 0.84rem; }}
    .timeline-dot {{
      position: relative;
      z-index: 1;
      justify-self: center;
      width: 11px;
      height: 11px;
      margin-top: 7px;
      border: 2px solid var(--bg);
      border-radius: 50%;
      background: var(--green);
      box-shadow: 0 0 0 1px var(--green);
    }}
    .timeline-content p {{ margin-bottom: 4px; color: var(--muted); }}
    .timeline-content a {{ font-size: 0.8rem; }}

    .source-groups {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 28px; }}
    .source-group ul {{ list-style: none; padding: 0; margin: 8px 0 0; display: grid; gap: 8px; }}
    .source-group a {{ display: inline-flex; align-items: center; gap: 8px; }}
    .source-group a::after {{ content: "↗"; font-size: 0.8rem; }}
    .footer-note {{ margin: 30px 0 0; padding-top: 20px; border-top: 1px solid var(--line); color: var(--muted); font-size: 0.84rem; }}

    @media (max-width: 900px) {{
      .intro, .chart-grid, .rhythm-grid {{ grid-template-columns: 1fr; }}
      .intro {{ gap: 28px; }}
      h1 {{ font-size: 3.35rem; }}
      h2 {{ font-size: 2rem; }}
      .metric-value {{ font-size: 1.8rem; }}
      .profile-strip {{ max-width: 600px; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .followup {{ grid-template-columns: 110px minmax(0, 1fr); }}
      .followup > div:last-child {{ grid-column: 2; }}
    }}

    @media (max-width: 680px) {{
      .shell {{ width: min(calc(100% - 24px), var(--max)); }}
      .topbar-inner {{ align-items: flex-start; padding: 13px 0; }}
      nav {{ display: none; }}
      .intro {{ padding: 38px 0 30px; }}
      h1 {{ font-size: 2.45rem; }}
      section {{ padding: 34px 0; }}
      .section-head {{ align-items: start; flex-direction: column; gap: 12px; }}
      .metrics, .dimension-grid, .clues, .source-groups {{ grid-template-columns: 1fr; }}
      .legend {{ grid-template-columns: 1fr; }}
      .followup {{ grid-template-columns: 1fr; gap: 10px; }}
      .followup > div:last-child {{ grid-column: auto; }}
      .profile-strip div {{ grid-template-columns: 82px 1fr; }}
      .chart-wrap {{ min-height: 270px; }}
      .timeline::before {{ left: 79px; }}
      .timeline-item {{ grid-template-columns: 62px 34px minmax(0, 1fr); }}
    }}

    @media (max-width: 390px) {{
      .metrics {{ grid-template-columns: 1fr; }}
      .segmented {{ width: 100%; }}
      .segmented button {{ flex: 1; }}
      .bowl-row {{ grid-template-columns: 68px 1fr 56px; }}
    }}

    @media (prefers-reduced-motion: reduce) {{
      html {{ scroll-behavior: auto; }}
      *, *::before, *::after {{ animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }}
    }}
  </style>
</head>
<body>
  <a class="skip-link" href="#main">跳到主要内容</a>
  <header class="topbar">
    <div class="shell topbar-inner">
      <a class="brand" href="#top" aria-label="返回小咪看板顶部">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M7 10 5 4l5 3.2h4L19 4l-2 6c1.1 1.1 1.7 2.5 1.7 4 0 3.6-3 6-6.7 6s-6.7-2.4-6.7-6c0-1.5.6-2.9 1.7-4Z"/>
            <path d="M9 14h.01M15 14h.01M10 17c1.3.7 2.7.7 4 0"/>
          </svg>
        </span>
        小咪档案
      </a>
      <nav aria-label="页面导航">
        <a href="#growth">生长</a>
        <a href="#rhythm">饮食节律</a>
        <a href="#dimensions">多维观察</a>
        <a href="#followups">待跟进</a>
        <a href="#sources">档案入口</a>
      </nav>
    </div>
  </header>

  <div id="top" class="shell">
    <div class="intro">
      <div>
        <p class="eyebrow">档案截至 {as_of}</p>
        <h1>小咪正在稳稳长大。</h1>
        <p class="lede">她的体重、食欲和排泄已经有了一条可追踪的基线，晚上也显出很鲜明的活跃与进食节律。现在最值得温柔地继续留意的，是皮肤、耳眼鼻，以及地面长发和线状物。</p>
      </div>
      <dl class="profile-strip" id="profile-strip" aria-label="小咪基础信息"></dl>
    </div>
  </div>

  <main id="main" class="shell">
    <section aria-labelledby="snapshot-title">
      <div class="section-head">
        <div>
          <h2 id="snapshot-title">先看这几条基线</h2>
          <p>每个数字都保留时间窗口和数据性质；“水碗减少量”不会被写成精确饮水量。</p>
        </div>
        <span class="as-of">一次摄入观察 n=1</span>
      </div>
      <div class="metrics" id="metrics"></div>
    </section>

    <section id="growth" aria-labelledby="growth-title">
      <div class="section-head">
        <div>
          <h2 id="growth-title">小咪最近长得怎么样</h2>
          <p>从到家时的 560 g 到最近的 1300 g，方向持续向上。短间隔的跳动不单独当作生理增速解读。</p>
        </div>
        <div class="segmented" aria-label="体重图数据范围">
          <button type="button" data-weight-mode="all" aria-pressed="true">含估计点</button>
          <button type="button" data-weight-mode="recorded" aria-pressed="false">仅记录值</button>
        </div>
      </div>
      <div class="chart-grid">
        <div>
          <div class="chart-wrap">
            <svg id="weight-chart" viewBox="0 0 760 360" role="img" aria-labelledby="weight-chart-title weight-chart-desc">
              <title id="weight-chart-title">小咪体重变化折线图</title>
              <desc id="weight-chart-desc">显示 2026-05-30 至 2026-07-10 的体重记录，估计日期使用空心点。</desc>
            </svg>
          </div>
          <p class="chart-detail" id="weight-detail" aria-live="polite"></p>
          <details>
            <summary>查看全部体重数据</summary>
            <div class="table-wrap">
              <table>
                <thead><tr><th>日期</th><th>日龄</th><th>体重</th><th>类型</th><th>备注</th></tr></thead>
                <tbody id="weight-table"></tbody>
              </table>
            </div>
          </details>
        </div>
        <div class="analysis-list" id="growth-summary"></div>
      </div>
    </section>

    <section id="rhythm" aria-labelledby="rhythm-title">
      <div class="section-head">
        <div>
          <h2 id="rhythm-title">她什么时候最爱吃</h2>
          <p>一次完整观察里，傍晚到夜间的摄入明显集中，和她晚上爱玩的习惯对得上。</p>
        </div>
        <a href="04_nutrition/reports/2026-07-07_24h_intake_analysis.md">打开完整报告</a>
      </div>
      <div class="rhythm-grid">
        <div>
          <div class="rhythm-callout" id="rhythm-callout"></div>
          <div class="stacked-bar" id="rhythm-bar" role="img" aria-label="一次 24 小时观察的进食时段估算分布"></div>
          <div class="legend" id="rhythm-legend"></div>
          <p class="fine-print" id="rhythm-limitation"></p>
        </div>
        <div>
          <h3>两只水碗的减少量</h3>
          <div class="bowl-comparison" id="bowl-comparison"></div>
          <p class="fine-print" id="bowl-limitation"></p>
        </div>
      </div>
    </section>

    <section id="dimensions" aria-labelledby="dimensions-title">
      <div class="section-head">
        <div>
          <h2 id="dimensions-title">四个维度一起看</h2>
          <p>每一块都分清“看到了什么、意味着什么、还不能说明什么、下一次怎么记”。</p>
        </div>
      </div>
      <div class="dimension-grid" id="dimension-grid"></div>
      <div class="clues" id="clues" aria-label="跨维度线索"></div>
    </section>

    <section id="followups" aria-labelledby="followups-title">
      <div class="section-head">
        <div>
          <h2 id="followups-title">这周一起留意</h2>
          <p>这些是观察和计划入口，不是诊断清单。高风险信号出现时仍以兽医判断为准。</p>
        </div>
        <a href="08_questions_decisions/action_queue.md">打开行动队列</a>
      </div>
      <div class="filters" id="followup-filters" aria-label="筛选待跟进事项"></div>
      <div class="followup-list" id="followup-list"></div>
    </section>

    <section aria-labelledby="timeline-title">
      <div class="section-head">
        <div>
          <h2 id="timeline-title">最近发生的事</h2>
          <p>从新食物、排便到体重和疫苗，按日期回到原始记录。</p>
        </div>
      </div>
      <div class="timeline" id="timeline"></div>
    </section>

    <section id="sources" aria-labelledby="sources-title">
      <div class="section-head">
        <div>
          <h2 id="sources-title">继续翻小咪的档案</h2>
          <p>看板只是入口。想核对细节时，直接打开对应的 Markdown 原始记录。</p>
        </div>
      </div>
      <div class="source-groups" id="source-groups"></div>
      <p class="footer-note">本页由 <code>11_insights/data/current_snapshot.json</code> 生成。数据截至 {as_of}；若源记录更新而看板未同步，请运行 <code>python3 scripts/build_dashboard.py</code>。医疗与用药相关决定以兽医面诊和当次医嘱为准。</p>
    </section>
  </main>

  <script type="application/json" id="xiaomi-data">{payload}</script>
  <script>
    (() => {{
      const data = JSON.parse(document.getElementById('xiaomi-data').textContent);
      const escapeHtml = (value) => String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
      const evidence = Object.fromEntries(data.evidence_types.map(item => [item.id, item]));
      const evidenceBadge = (id) => `<span class="badge badge-${{id}}">${{escapeHtml(evidence[id].label)}}</span>`;

      const profile = data.profile;
      document.getElementById('profile-strip').innerHTML = [
        ['当时年龄', profile.age_label_as_of],
        ['最近体重', `${{(profile.latest_weight_g / 1000).toFixed(2)}} kg`],
        ['到家日期', profile.arrival_date],
        ['花色记录', profile.coat]
      ].map(([label, value]) => `<div><dt>${{escapeHtml(label)}}</dt><dd>${{escapeHtml(value)}}</dd></div>`).join('');

      document.getElementById('metrics').innerHTML = data.headline_metrics.map(metric => `
        <article class="metric">
          <div class="metric-label">${{escapeHtml(metric.label)}}</div>
          <div class="metric-value">${{escapeHtml(metric.display)}}</div>
          <div class="metric-meta">${{escapeHtml(metric.window)}}</div>
          <div class="metric-meta">${{evidenceBadge(metric.evidence_type)}} · ${{escapeHtml(metric.limitation)}}</div>
          <a href="${{escapeHtml(metric.source)}}">查看来源</a>
        </article>
      `).join('');

      const weights = data.growth.weight_history;
      const tableBody = document.getElementById('weight-table');
      tableBody.innerHTML = weights.map(item => `
        <tr>
          <td>${{escapeHtml(item.observed_at || item.date)}}</td>
          <td>${{item.age_days}} 天</td>
          <td>${{item.weight_g}} g</td>
          <td>${{evidenceBadge(item.value_type)}}</td>
          <td>${{escapeHtml(item.note)}}</td>
        </tr>
      `).join('');

      const growth = data.growth.summary;
      document.getElementById('growth-summary').innerHTML = [
        {{ value: `+${{growth.gain_g}} g`, title: '到家以来', text: `标准日期差 ${{growth.elapsed_days_by_date}} 天，体重增加 ${{growth.gain_percent}}%。` }},
        {{ value: `${{growth.daily_gain_range_g[0]}}-${{growth.daily_gain_range_g[1]}} g/日`, title: '总体平均增速', text: '范围来自起点称重时刻未知；按日期差为 18.0 g/日。' }},
        {{ value: `${{growth.three_week_weekly_gain_g}} g/周`, title: '近三周平均', text: '三周分别增加 100、150、100 g，现有节点没有停滞或下降。' }}
      ].map(item => `
        <div class="analysis-item">
          <div class="value">${{escapeHtml(item.value)}}</div>
          <h3>${{escapeHtml(item.title)}}</h3>
          <p>${{escapeHtml(item.text)}}</p>
        </div>
      `).join('');

      const svg = document.getElementById('weight-chart');
      const detail = document.getElementById('weight-detail');
      const NS = 'http://www.w3.org/2000/svg';
      const createSvg = (name, attrs = {{}}, text = '') => {{
        const el = document.createElementNS(NS, name);
        Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
        if (text) el.textContent = text;
        return el;
      }};

      function renderWeightChart(mode = 'all') {{
        const points = mode === 'recorded' ? weights.filter(item => item.value_type === 'recorded') : weights;
        const width = 760;
        const height = 360;
        const margin = {{ top: 30, right: 30, bottom: 52, left: 58 }};
        const x0 = new Date(points[0].date + 'T00:00:00').getTime();
        const x1 = new Date(points[points.length - 1].date + 'T00:00:00').getTime();
        const values = points.map(item => item.weight_g);
        const yMin = Math.floor((Math.min(...values) - 80) / 100) * 100;
        const yMax = Math.ceil((Math.max(...values) + 80) / 100) * 100;
        const x = (dateValue) => margin.left + (new Date(dateValue + 'T00:00:00').getTime() - x0) / (x1 - x0) * (width - margin.left - margin.right);
        const y = (value) => margin.top + (yMax - value) / (yMax - yMin) * (height - margin.top - margin.bottom);
        svg.replaceChildren(
          createSvg('title', {{ id: 'weight-chart-title' }}, '小咪体重变化折线图'),
          createSvg('desc', {{ id: 'weight-chart-desc' }}, mode === 'recorded' ? '仅显示有明确记录日期的体重点。' : '显示全部体重点，估计日期使用空心点。')
        );

        for (let value = yMin; value <= yMax; value += 200) {{
          const yPos = y(value);
          svg.append(createSvg('line', {{ x1: margin.left, x2: width - margin.right, y1: yPos, y2: yPos, class: 'chart-gridline' }}));
          svg.append(createSvg('text', {{ x: margin.left - 10, y: yPos + 4, 'text-anchor': 'end', class: 'chart-tick' }}, `${{value}}g`));
        }}

        const tickIndexes = [...new Set([0, Math.floor((points.length - 1) / 2), points.length - 1])];
        tickIndexes.forEach(index => {{
          const item = points[index];
          const xPos = x(item.date);
          svg.append(createSvg('line', {{ x1: xPos, x2: xPos, y1: margin.top, y2: height - margin.bottom, class: 'chart-gridline' }}));
          svg.append(createSvg('text', {{ x: xPos, y: height - 20, 'text-anchor': 'middle', class: 'chart-tick' }}, item.date.slice(5)));
        }});

        const linePoints = points.map(item => `${{x(item.date)}},${{y(item.weight_g)}}`).join(' ');
        const areaPoints = `${{margin.left}},${{height - margin.bottom}} ${{linePoints}} ${{x(points.at(-1).date)}},${{height - margin.bottom}}`;
        svg.append(createSvg('polygon', {{ points: areaPoints, class: 'chart-area' }}));
        svg.append(createSvg('polyline', {{ points: linePoints, class: 'chart-line' }}));

        points.forEach((item, index) => {{
          const cx = x(item.date);
          const cy = y(item.weight_g);
          const point = createSvg('circle', {{
            cx,
            cy,
            r: item.value_type === 'estimated' ? 6 : 5,
            class: `chart-point ${{item.value_type === 'estimated' ? 'estimated' : ''}}`,
            'aria-hidden': 'true'
          }});
          const showDetail = () => {{
            detail.innerHTML = `<strong>${{escapeHtml(item.observed_at || item.date)}} · ${{item.weight_g}} g</strong> · ${{escapeHtml(evidence[item.value_type].label)}} · ${{escapeHtml(item.note)}}`;
          }};
          point.addEventListener('mouseenter', showDetail);
          point.addEventListener('click', showDetail);
          svg.append(point);
          if (index === 0 || index === points.length - 1) {{
            svg.append(createSvg('text', {{
              x: cx,
              y: cy - 13,
              'text-anchor': index === 0 ? 'start' : 'end',
              class: 'chart-value-label'
            }}, `${{item.weight_g}} g`));
          }}
        }});

        const latest = points.at(-1);
        detail.innerHTML = `<strong>${{escapeHtml(latest.observed_at || latest.date)}} · ${{latest.weight_g}} g</strong> · ${{escapeHtml(evidence[latest.value_type].label)}} · ${{escapeHtml(latest.note)}}`;
      }}

      document.querySelectorAll('[data-weight-mode]').forEach(button => {{
        button.addEventListener('click', () => {{
          document.querySelectorAll('[data-weight-mode]').forEach(peer => peer.setAttribute('aria-pressed', String(peer === button)));
          renderWeightChart(button.dataset.weightMode);
        }});
      }});
      renderWeightChart();

      const rhythm = data.nutrition_and_rhythm;
      const evening = rhythm.direct_evening_window;
      document.getElementById('rhythm-callout').innerHTML = `
        <strong>${{evening.hours}} 小时吃了 ${{evening.consumed_g}} g</strong>
        <span>占核心全天 ${{evening.share_percent}}%，平均速度约为其余时间的 ${{evening.rate_ratio}} 倍。</span>
      `;
      document.getElementById('rhythm-bar').innerHTML = rhythm.clock_segments.map(item => `
        <span class="stacked-segment" style="width:${{item.share_percent}}%" aria-label="${{escapeHtml(item.label)}} ${{item.share_percent}}%"></span>
      `).join('');
      document.getElementById('rhythm-legend').innerHTML = rhythm.clock_segments.map(item => `
        <div class="legend-item">
          <span class="swatch" aria-hidden="true"></span>
          <span>${{escapeHtml(item.label)}}</span>
          <span class="legend-value">${{item.grams}} g · ${{item.share_percent}}%</span>
        </div>
      `).join('');
      document.getElementById('rhythm-limitation').textContent = rhythm.clock_segments_limitation;

      const bowls = rhythm.water_bowls;
      const bowlData = [
        {{ label: '白色水碗', value: bowls.white_bowl_loss_ml, share: bowls.white_share_percent }},
        {{ label: '黄色水碗', value: bowls.yellow_bowl_loss_ml, share: bowls.yellow_share_percent }}
      ];
      document.getElementById('bowl-comparison').innerHTML = bowlData.map(item => `
        <div class="bowl-row">
          <span>${{item.label}}</span>
          <span class="bowl-track"><span class="bowl-fill" style="width:${{item.share}}%"></span></span>
          <strong>${{item.value}} ml</strong>
        </div>
      `).join('');
      document.getElementById('bowl-limitation').textContent = `两碗合计减少 ${{bowls.gross_loss_ml}} ml。${{bowls.limitation}}`;

      document.getElementById('dimension-grid').innerHTML = data.dimensions.map(item => `
        <article class="dimension-card">
          <h3>${{escapeHtml(item.label)}}</h3>
          <dl>
            <div><dt>看到了什么</dt><dd>${{escapeHtml(item.observed)}}</dd></div>
            <div><dt>这意味着什么</dt><dd>${{escapeHtml(item.meaning)}}</dd></div>
            <div><dt>还不能说明什么</dt><dd>${{escapeHtml(item.limitation)}}</dd></div>
            <div class="next"><dt>下一次怎么记</dt><dd>${{escapeHtml(item.next)}}</dd></div>
          </dl>
        </article>
      `).join('');

      document.getElementById('clues').innerHTML = data.cross_dimension_clues.map(item => `
        <article class="clue">
          <h3>${{escapeHtml(item.title)}}</h3>
          <p>${{escapeHtml(item.evidence)}}</p>
          <p><strong>${{escapeHtml(item.interpretation)}}</strong></p>
          <p class="limit">边界：${{escapeHtml(item.limitation)}}</p>
        </article>
      `).join('');

      const followups = data.followups;
      const dimensions = ['全部', ...new Set(followups.map(item => item.dimension))];
      const filterContainer = document.getElementById('followup-filters');
      filterContainer.innerHTML = dimensions.map((label, index) => `
        <button type="button" data-filter="${{escapeHtml(label)}}" aria-pressed="${{index === 0}}">${{escapeHtml(label)}}</button>
      `).join('');
      const followupList = document.getElementById('followup-list');
      followupList.innerHTML = followups.map(item => `
        <article class="followup" data-dimension="${{escapeHtml(item.dimension)}}">
          <div class="followup-state">
            <span class="badge badge-${{item.attention_level === '中' ? 'reference' : item.attention_level === '计划' ? 'estimated' : 'observed'}}">${{escapeHtml(item.status)}}</span>
            <span class="attention">${{escapeHtml(item.dimension)}} · ${{escapeHtml(item.attention_level)}}</span>
          </div>
          <div>
            <h3>${{escapeHtml(item.title)}}</h3>
            <p>${{escapeHtml(item.observed)}}</p>
            <a href="${{escapeHtml(item.source)}}">查看来源</a>
          </div>
          <div>
            <p class="action"><strong>下一步：</strong>${{escapeHtml(item.next)}}</p>
            <p class="escalate">${{escapeHtml(item.escalate)}}</p>
          </div>
        </article>
      `).join('');
      filterContainer.querySelectorAll('button').forEach(button => {{
        button.addEventListener('click', () => {{
          filterContainer.querySelectorAll('button').forEach(peer => peer.setAttribute('aria-pressed', String(peer === button)));
          followupList.querySelectorAll('.followup').forEach(item => {{
            item.hidden = button.dataset.filter !== '全部' && item.dataset.dimension !== button.dataset.filter;
          }});
        }});
      }});

      document.getElementById('timeline').innerHTML = data.recent_timeline.map(item => `
        <article class="timeline-item">
          <time class="timeline-date" datetime="${{escapeHtml(item.date)}}">${{escapeHtml(item.date.slice(5))}}</time>
          <span class="timeline-dot" aria-hidden="true"></span>
          <div class="timeline-content">
            <h3>${{escapeHtml(item.title)}}</h3>
            <p>${{escapeHtml(item.detail)}}</p>
            <a href="${{escapeHtml(item.source)}}">${{escapeHtml(item.category)}}记录</a>
          </div>
        </article>
      `).join('');

      const groupedSources = Object.groupBy
        ? Object.groupBy(data.source_links, item => item.group)
        : data.source_links.reduce((groups, item) => {{
            (groups[item.group] ||= []).push(item);
            return groups;
          }}, {{}});
      document.getElementById('source-groups').innerHTML = Object.entries(groupedSources).map(([group, items]) => `
        <div class="source-group">
          <h3>${{escapeHtml(group)}}</h3>
          <ul>${{items.map(item => `<li><a href="${{escapeHtml(item.path)}}">${{escapeHtml(item.label)}}</a></li>`).join('')}}</ul>
        </div>
      `).join('');
    }})();
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate data and fail when dashboard.html is out of date",
    )
    args = parser.parse_args()

    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Unable to read {DATA_PATH.relative_to(ROOT)}: {exc}", file=sys.stderr)
        return 1

    errors = validate(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    rendered = render(data)
    if args.check:
        if not OUTPUT_PATH.exists():
            print("ERROR: dashboard.html does not exist", file=sys.stderr)
            return 1
        current = OUTPUT_PATH.read_text(encoding="utf-8")
        if current != rendered:
            print(
                "ERROR: dashboard.html is out of date; run "
                "python3 scripts/build_dashboard.py",
                file=sys.stderr,
            )
            return 1
        print("Dashboard data and generated HTML are in sync.")
        return 0

    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    print(f"Built {OUTPUT_PATH.relative_to(ROOT)} from {DATA_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
