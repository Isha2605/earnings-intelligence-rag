import json
import os
import sys

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.formatting import flag_anomaly, format_abs_delta, format_millions

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KPI_PATH  = os.path.join(BASE_DIR, "data", "kpis.json")

C_PRIMARY  = "#5B7CFA"
C_POSITIVE = "#85D478"
C_NEGATIVE = "#F16672"
C_ACCENT   = "#F5BE4F"
C_CLOUD    = "#43C6E8"
C_TEXT     = "#F3F7FC"
C_SUBTEXT  = "#A7B4C7"
C_MUTED    = "#93A4BB"
C_CARD     = "#101826"
C_CARD_2   = "#121D2E"
C_BORDER   = "rgba(148,163,184,0.18)"
C_GRID     = "rgba(148,163,184,0.08)"

YEARS      = ["2022", "2023", "2024"]
YR_LABELS  = ["FY2022", "FY2023", "FY2024"]


@st.cache_data
def load_kpis():
    with open(KPI_PATH, "r") as f:
        return json.load(f)


# ── SVG sparklines (pure HTML, no JS, no iframe) ──────────────────────────────

def _svg_spark(values, color, uid):
    W, H, PAD = 178, 42, 5
    lo, hi = min(values), max(values)
    n = len(values)

    def px(i):
        return PAD + i / (n - 1) * (W - 2 * PAD)

    def py(v):
        return H / 2 if hi == lo else H - PAD - (v - lo) / (hi - lo) * (H - 2 * PAD)

    pts  = [(px(i), py(v)) for i, v in enumerate(values)]
    line = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
    fill = line + f" {pts[-1][0]:.2f},{H} {pts[0][0]:.2f},{H}"
    dots = "".join(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="{color}" '
        f'stroke="{C_CARD}" stroke-width="2"/>'
        for x, y in pts
    )
    return (
        f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;height:{H}px;display:block;overflow:visible">'
        f'<defs><linearGradient id="gr{uid}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.45"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0.02"/>'
        f'</linearGradient></defs>'
        f'<polygon points="{fill}" fill="url(#gr{uid})"/>'
        f'<polyline points="{line}" fill="none" stroke="{color}" '
        f'stroke-width="2.7" stroke-linejoin="round" stroke-linecap="round"/>'
        f'{dots}</svg>'
    )


def _kpi_cards(kpis):
    cards = [
        ("Total Revenue",     "total_revenue",             C_PRIMARY),
        ("Intelligent Cloud", "intelligent_cloud_revenue", C_CLOUD),
        ("Operating Income",  "operating_income",          C_ACCENT),
        ("Net Income",        "net_income",                C_POSITIVE),
    ]
    for i, ((label, key, color), col) in enumerate(zip(cards, st.columns(4, gap="small"))):
        vals      = [kpis[y][key] for y in YEARS]
        cur, prev = vals[-1], vals[-2]
        pct       = (cur - prev) / prev * 100
        dc        = C_POSITIVE if pct >= 0 else C_NEGATIVE
        arrow     = "▲" if pct >= 0 else "▼"
        sign      = "+" if pct >= 0 else ""
        col.markdown(
            f'<div style="position:relative;overflow:hidden;border:1px solid {C_BORDER};border-radius:14px;'
            f'padding:17px 17px 11px;background:linear-gradient(180deg,{C_CARD_2},{C_CARD});'
            f'box-shadow:0 16px 36px rgba(0,0,0,0.18);">'
            f'<div style="position:absolute;inset:0 0 auto 0;height:2px;background:{color};opacity:.9;"></div>'
            f'<div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:6px;">'
            f'<div style="font-size:11px;color:{C_SUBTEXT};font-weight:800;letter-spacing:0.08em;'
            f'text-transform:uppercase;">{label}</div>'
            f'<div style="font-size:11px;color:{dc};font-weight:850;background:rgba(255,255,255,0.04);'
            f'border:1px solid rgba(148,163,184,0.14);padding:3px 7px;border-radius:999px;white-space:nowrap;">'
            f'{arrow} {sign}{pct:.1f}%</div></div>'
            f'<div style="font-size:29px;font-weight:850;color:{C_TEXT};line-height:1.04;'
            f'margin-bottom:5px;letter-spacing:0;">{format_millions(cur)}</div>'
            f'<div style="font-size:12px;color:{C_MUTED};font-weight:650;margin-bottom:10px;">'
            f'FY2024 vs FY2023 <span style="color:{dc};">{format_abs_delta(cur, prev)}</span></div>'
            f'<div style="width:58%;min-width:168px;max-width:210px;margin:8px auto 0;'
            f'padding:3px 0 0;">'
            f'{_svg_spark([v / 1000 for v in vals], color, uid=i)}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── Altair chart theme ─────────────────────────────────────────────────────────

def _theme(chart):
    return (
        chart
        .configure(background="transparent")
        .configure_view(strokeWidth=0, fill="transparent")
        .configure_axis(
            grid=False,
            domainColor="rgba(148,163,184,0.20)", tickColor="rgba(148,163,184,0.20)",
            labelColor="#A7B4C7", titleColor="#D8E3F3",
            labelFontSize=12, titleFontSize=12,
            titleFontWeight=700,
        )
        .configure_legend(
            labelColor="#A7B4C7", titleColor="#D8E3F3",
            labelFontSize=12, titleFontSize=12,
            orient="bottom", padding=8, rowPadding=4,
            symbolType="square",
        )
        .configure_mark(opacity=0.96)
    )


def _section(title):
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px;margin:28px 0 12px 0;'>"
        f"<span style='width:8px;height:8px;border-radius:999px;background:{C_PRIMARY};"
        f"box-shadow:0 0 0 4px rgba(91,124,250,0.13);'></span>"
        f"<span style='font-size:12px;font-weight:850;letter-spacing:0.11em;"
        f"text-transform:uppercase;color:{C_TEXT};'>{title}</span></div>",
        unsafe_allow_html=True,
    )


def _chart_label(title, note):
    st.markdown(
        f"<div style='margin:2px 0 16px 2px;'>"
        f"<div style='font-size:14px;font-weight:850;color:{C_TEXT};letter-spacing:0;'>{title}</div>"
        f"<div style='font-size:12px;color:{C_SUBTEXT};margin-top:4px;line-height:1.35;'>{note}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _page_intro(kpis):
    rev_22 = kpis["2022"]["total_revenue"]
    rev_24 = kpis["2024"]["total_revenue"]
    cloud_24 = kpis["2024"]["intelligent_cloud_revenue"]
    net_24 = kpis["2024"]["net_income"]
    rev_cagr = ((rev_24 / rev_22) ** (1 / 2) - 1) * 100
    cloud_mix = cloud_24 / rev_24 * 100
    net_margin = net_24 / rev_24 * 100
    st.markdown(
        f"""
        <div style="display:grid;grid-template-columns:minmax(0,1.45fr) repeat(3,minmax(150px,0.55fr));gap:14px;margin:4px 0 18px 0;">
          <div style="border:1px solid {C_BORDER};border-radius:14px;padding:20px 22px;background:linear-gradient(180deg,{C_CARD_2},{C_CARD});box-shadow:0 16px 36px rgba(0,0,0,.18);">
            <div style="font-size:12px;font-weight:850;letter-spacing:.12em;text-transform:uppercase;color:{C_PRIMARY};margin-bottom:8px;">Executive view</div>
            <div style="font-size:27px;line-height:1.15;font-weight:850;color:{C_TEXT};letter-spacing:0;margin-bottom:8px;">Microsoft FY2022-FY2024 earnings cockpit</div>
            <div style="font-size:14px;line-height:1.6;color:{C_SUBTEXT};max-width:760px;">Revenue expansion accelerated in FY2024, with cloud scale and operating leverage driving the sharpest profitability improvement in the three-year window.</div>
          </div>
          <div style="border:1px solid {C_BORDER};border-radius:14px;padding:18px;background:{C_CARD};box-shadow:0 16px 36px rgba(0,0,0,.14);">
            <div style="font-size:11px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:{C_MUTED};">Revenue CAGR</div>
            <div style="font-size:25px;font-weight:850;color:{C_TEXT};margin-top:8px;">{rev_cagr:.1f}%</div>
            <div style="font-size:12px;color:{C_SUBTEXT};margin-top:4px;">FY2022 to FY2024</div>
          </div>
          <div style="border:1px solid {C_BORDER};border-radius:14px;padding:18px;background:{C_CARD};box-shadow:0 16px 36px rgba(0,0,0,.14);">
            <div style="font-size:11px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:{C_MUTED};">Cloud mix</div>
            <div style="font-size:25px;font-weight:850;color:{C_TEXT};margin-top:8px;">{cloud_mix:.1f}%</div>
            <div style="font-size:12px;color:{C_SUBTEXT};margin-top:4px;">of FY2024 revenue</div>
          </div>
          <div style="border:1px solid {C_BORDER};border-radius:14px;padding:18px;background:{C_CARD};box-shadow:0 16px 36px rgba(0,0,0,.14);">
            <div style="font-size:11px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:{C_MUTED};">Net margin</div>
            <div style="font-size:25px;font-weight:850;color:{C_TEXT};margin-top:8px;">{net_margin:.1f}%</div>
            <div style="font-size:12px;color:{C_SUBTEXT};margin-top:4px;">FY2024</div>
          </div>
        </div>
        <style>
        @media (max-width: 1000px) {{
          div[style*="grid-template-columns:minmax(0,1.45fr)"] {{
            grid-template-columns: 1fr !important;
          }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── Cached DataFrames ──────────────────────────────────────────────────────────

@st.cache_data
def _revenue_df(frozen):
    kpis = json.loads(frozen)
    rows = []
    for y in YEARS:
        for seg, key in [
            ("Productivity & BP", "productivity_and_business_processes_revenue"),
            ("Intelligent Cloud", "intelligent_cloud_revenue"),
            ("More Personal Computing", "more_personal_computing_revenue"),
        ]:
            rows.append({"Year": f"FY{y}", "Segment": seg,
                         "Revenue": round(kpis[y][key] / 1000, 1)})
    return pd.DataFrame(rows)


@st.cache_data
def _azure_df(frozen):
    kpis = json.loads(frozen)
    return pd.DataFrame([
        {"Year": f"FY{y}", "Growth": kpis[y]["azure_growth_yoy_pct"]}
        for y in YEARS
    ])


@st.cache_data
def _waterfall_df(frozen):
    kpis = json.loads(frozen)

    fy22 = round(kpis["2022"]["total_revenue"] / 1000, 1)
    fy23 = round(kpis["2023"]["total_revenue"] / 1000, 1)
    fy24 = round(kpis["2024"]["total_revenue"] / 1000, 1)

    def dv(k, a, b):
        return round((kpis[b][k] - kpis[a][k]) / 1000, 1)

    deltas = [
        dv("intelligent_cloud_revenue",                       "2022", "2023"),
        dv("productivity_and_business_processes_revenue",      "2022", "2023"),
        dv("more_personal_computing_revenue",                 "2022", "2023"),
        dv("intelligent_cloud_revenue",                       "2023", "2024"),
        dv("productivity_and_business_processes_revenue",      "2023", "2024"),
        dv("more_personal_computing_revenue",                 "2023", "2024"),
    ]
    bridge_labels = ["Cloud '23", "Prod '23", "MPC '23",
                     "Cloud '24", "Prod '24", "MPC '24"]

    bars, run = [], 0.0

    def add_total(label, val):
        bars.append({"label": label, "bottom": 0.0, "top": float(val),
                     "value": float(val), "kind": "total",
                     "text": f"${val:.0f}B"})
        return float(val)

    def add_bridge(label, d, r):
        if d >= 0:
            bars.append({"label": label, "bottom": r, "top": r + d,
                         "value": d, "kind": "increase",
                         "text": f"+${d:.1f}B"})
        else:
            bars.append({"label": label, "bottom": r + d, "top": r,
                         "value": d, "kind": "decrease",
                         "text": f"-${abs(d):.1f}B"})
        return r + d

    run = add_total("FY2022", fy22)
    for lbl, d in zip(bridge_labels[:3], deltas[:3]):
        run = add_bridge(lbl, d, run)
    run = add_total("FY2023", fy23)
    for lbl, d in zip(bridge_labels[3:], deltas[3:]):
        run = add_bridge(lbl, d, run)
    add_total("FY2024", fy24)

    return pd.DataFrame(bars)


# ── Chart builders ─────────────────────────────────────────────────────────────

def _revenue_chart(frozen):
    df    = _revenue_df(frozen)
    order = YR_LABELS
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=7, cornerRadiusTopRight=7)
        .encode(
            x=alt.X("Year:N", sort=order, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Revenue:Q", title="Revenue ($B)"),
            color=alt.Color(
                "Segment:N",
                scale=alt.Scale(
                    domain=["Productivity & BP", "Intelligent Cloud", "More Personal Computing"],
                    range=[C_PRIMARY, C_CLOUD, C_ACCENT],
                ),
                legend=alt.Legend(title=None),
            ),
            order=alt.Order("color:N"),
            tooltip=[
                alt.Tooltip("Year:N"),
                alt.Tooltip("Segment:N"),
                alt.Tooltip("Revenue:Q", format=".1f", title="Revenue ($B)"),
            ],
        )
        .properties(width="container", height=300)
    )
    return _theme(chart)


def _azure_chart(frozen):
    df    = _azure_df(frozen)
    order = YR_LABELS
    base  = alt.Chart(df)

    area = base.mark_area(opacity=0.20, color=C_PRIMARY, line=False).encode(
        x=alt.X("Year:N", sort=order, title=None),
        y=alt.Y("Growth:Q", title="YoY Growth (%)", scale=alt.Scale(domain=[0, 55])),
    )
    line = base.mark_line(color=C_PRIMARY, strokeWidth=3.4).encode(
        x=alt.X("Year:N", sort=order, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Growth:Q"),
    )
    dots = base.mark_circle(color=C_PRIMARY, size=130, opacity=1).encode(
        x=alt.X("Year:N", sort=order, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Growth:Q"),
        tooltip=[alt.Tooltip("Year:N"),
                 alt.Tooltip("Growth:Q", format=".0f", title="Azure Growth %")],
    )
    lbls = base.mark_text(color=C_TEXT, dy=-18, fontSize=16, fontWeight="bold").encode(
        x=alt.X("Year:N", sort=order, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Growth:Q"),
        text=alt.Text("Growth:Q", format=".0f"),
    )
    return _theme((area + line + dots + lbls).properties(width="container", height=300))


def _waterfall_chart(frozen):
    df        = _waterfall_df(frozen)
    bar_order = list(df["label"])

    bars = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=7, cornerRadiusTopRight=7)
        .encode(
            x=alt.X("label:N", sort=bar_order, title=None,
                    axis=alt.Axis(labelAngle=-25, labelFontSize=12)),
            y=alt.Y("bottom:Q", title="Revenue ($B)",
                    scale=alt.Scale(domain=[0, 280])),
            y2=alt.Y2("top:Q"),
            color=alt.Color(
                "kind:N",
                scale=alt.Scale(domain=["total", "increase", "decrease"],
                                range=[C_PRIMARY, C_POSITIVE, C_NEGATIVE]),
                legend=alt.Legend(title=None),
            ),
            tooltip=[
                alt.Tooltip("label:N", title=""),
                alt.Tooltip("text:N", title="Change"),
            ],
        )
    )
    text = (
        alt.Chart(df)
        .mark_text(dy=-9, fontSize=12, fontWeight="bold")
        .encode(
            x=alt.X("label:N", sort=bar_order),
            y=alt.Y("top:Q"),
            text=alt.Text("text:N"),
            color=alt.Color(
                "kind:N",
                scale=alt.Scale(
                    domain=["total", "increase", "decrease"],
                    range=[C_TEXT, C_POSITIVE, C_NEGATIVE],
                ),
                legend=None,
            ),
        )
    )
    return _theme((bars + text).properties(width="container", height=350))


# ── Insights ──────────────────────────────────────────────────────────────────

@st.cache_data
def _insight_data(frozen):
    kpis  = json.loads(frozen)
    flags = []

    az22, az23, az24 = (kpis[y]["azure_growth_yoy_pct"] for y in YEARS)
    if az23 < az22 * 0.75:
        flags.append(("warn",
            f"Azure growth decelerated from {az22:.0f}% to {az23:.0f}% in FY2023 "
            f"({(az23-az22)/az22*100:.0f}% slowdown) — cloud spend normalization after the post-pandemic surge."))
    if az24 > az23:
        flags.append(("ok",
            f"Azure growth stabilized at {az24:.0f}% in FY2024, recovering from the FY2023 trough "
            f"as AI workloads began flowing through Azure infrastructure."))

    ni22, ni23, ni24 = kpis["2022"]["net_income"], kpis["2023"]["net_income"], kpis["2024"]["net_income"]
    c2223 = (ni23 - ni22) / ni22 * 100
    c2324 = (ni24 - ni23) / ni23 * 100
    if abs(c2223) < 2:
        flags.append(("warn",
            f"Net income nearly flat in FY2023 ({c2223:+.1f}%) despite revenue growing 6.9% — "
            f"elevated costs from the Activision Blizzard acquisition compressed margins."))
    if c2324 > 15:
        flags.append(("ok",
            f"Net income surged {c2324:.0f}% in FY2024 ({format_millions(ni23)} → {format_millions(ni24)}), "
            f"the strongest year-over-year growth in the 3-year window."))

    rev_g = (kpis["2024"]["total_revenue"] - kpis["2023"]["total_revenue"]) / kpis["2023"]["total_revenue"] * 100
    oi_g  = (kpis["2024"]["operating_income"] - kpis["2023"]["operating_income"]) / kpis["2023"]["operating_income"] * 100
    if oi_g > rev_g * 1.4:
        flags.append(("ok",
            f"Strong operating leverage in FY2024: revenue grew {rev_g:.1f}% while operating income "
            f"grew {oi_g:.1f}%, expanding operating margin by ~4 percentage points."))

    if flag_anomaly([ni22, ni23, ni24]):
        flags.append(("ok",
            f"FY2024 net income of {format_millions(ni24)} is a statistical outlier — more than 1 std dev "
            f"above the 3-year mean, signalling exceptional profitability acceleration."))
    return flags


def _render_insights(frozen):
    flags = _insight_data(frozen)
    if not flags:
        return
    _section("Auto-Generated Insights")
    for kind, text in flags:
        bg  = "rgba(245,190,79,0.10)" if kind == "warn" else "rgba(133,212,120,0.10)"
        bdr = C_ACCENT                  if kind == "warn" else C_POSITIVE
        ico = "⚠️" if kind == "warn" else "✅"
        st.markdown(
            f"<div style='background:{bg};border:1px solid {C_BORDER};"
            f"border-left:4px solid {bdr};border-radius:10px;"
            f"padding:14px 17px;margin-bottom:10px;font-size:14px;color:{C_TEXT};"
            f"line-height:1.65;box-shadow:0 8px 18px rgba(15,31,58,0.055);'>"
            f"<span style='margin-right:8px;'>{ico}</span>{text}</div>",
            unsafe_allow_html=True,
        )


# ── Entry point ───────────────────────────────────────────────────────────────

def render():
    kpis   = load_kpis()
    frozen = json.dumps(kpis, sort_keys=True)

    _page_intro(kpis)
    _kpi_cards(kpis)

    _section("Revenue Breakdown")
    col1, col2 = st.columns([1.05, 1], gap="large")
    with col1:
        _chart_label("Segment revenue composition", "Stacked revenue by reporting segment")
        st.altair_chart(_revenue_chart(frozen), use_container_width=True, theme=None)
    with col2:
        _chart_label("Azure revenue growth", "Year-over-year growth rate")
        st.altair_chart(_azure_chart(frozen), use_container_width=True, theme=None)

    _section("Revenue Bridge")
    _chart_label("Revenue movement bridge", "Segment contribution to total revenue change")
    st.altair_chart(_waterfall_chart(frozen), use_container_width=True, theme=None)

    _render_insights(frozen)
