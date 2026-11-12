"""Shared look and feel for the PharmaSignal app.

Two matching palettes (light and dark), one chart theme and a small set of building blocks (hero, findings, steps,
KPI tiles, status chips, cards, callouts) so every page looks and reads the same way in either mode.
"""
import html
import re

import altair as alt
import numpy as np
import plotly.graph_objects as go  # noqa: F401
import streamlit as st

# ---------------------------------------------------------------- palettes
PALETTES = {
    "light": dict(
        BG="#FFFFFF", CARD="#FFFFFF", INK="#0B2239", TEXT="#1B3550", MUTED="#3D5874", LINE="#D2DDE6", SOFTLINE="#E6EDF2",
        TEAL="#0F766E", TEAL_SOFT="#DDF1EC", TEAL_TEXT="#0B5E57", TEAL_LIGHT="#5FD4BD",
        AMBER="#DB8E1C", AMBER_SOFT="#FCF0DA", AMBER_TEXT="#8A5300",
        CORAL="#C0412A", CORAL_SOFT="#FBE6E1", CORAL_TEXT="#9E2F1B",
        BLUE="#1F5F99", BLUE_SOFT="#E3EEF8", MIST="#A3B7C9", GREY_SOFT="#F1F5F8",
        HERO="#0B2239", HERO_GLOW="rgba(45,191,169,0.28)", GRID="#E3EAF0", SIDEBAR="#0B2239",
        CARD_SOLID="#FFFFFF", FAINT="#7C93A8", GREEN="#1E9E6A"),
    "dark": dict(
        BG="#0B1826", CARD="#12253A", INK="#F2F7FB", TEXT="#DCE6EF", MUTED="#AFC1D1", LINE="#27425D", SOFTLINE="#1D3550",
        TEAL="#2EC4AE", TEAL_SOFT="#103B3A", TEAL_TEXT="#7BE3D1", TEAL_LIGHT="#7BE3D1",
        AMBER="#F2AE45", AMBER_SOFT="#3A2C12", AMBER_TEXT="#F7C979",
        CORAL="#F2785F", CORAL_SOFT="#3D1D17", CORAL_TEXT="#F8A493",
        BLUE="#7FB4E8", BLUE_SOFT="#16304A", MIST="#4E6A85", GREY_SOFT="#1A3048",
        HERO="#102F4B", HERO_GLOW="rgba(46,196,174,0.30)", GRID="#1E3650", SIDEBAR="#07111C",
        CARD_SOLID="#12253A", FAINT="#6F8AA3", GREEN="#3DD598"),
}
MODE = "light"
P = PALETTES[MODE]
TEAL = INK = AMBER = CORAL = BLUE = MIST = MUTED = SLATE = TEAL_LIGHT = None
CLASS_COLOURS = None
CLASS_TEXT = {"Class I": "Serious harm or death is reasonably possible.",
              "Class II": "Temporary or reversible harm is possible; serious harm is unlikely.",
              "Class III": "Unlikely to cause harm, but breaks the rules, such as a labelling error."}
CLASS_RISK = {"I": "high risk", "II": "medium risk", "III": "low risk"}
_CLASS_RE = re.compile(r"\bClass (III|II|I)\b(?!\s*\()")


def with_risk(text):
    """'Class I' -> 'Class I (high risk)', so nobody needs the key to read a recall class."""
    return _CLASS_RE.sub(lambda m: f"Class {m.group(1)} ({CLASS_RISK[m.group(1)]})", str(text))

TEAM = {"Cindy Murogo": "Project lead and data pipeline",
        "Daniel Kimasar": "Classification, evaluation and business analytics",
        "Mananda Kirungu Salim": "Exploratory analysis and data quality",
        "Nelson Masaki": "App, dashboard and documentation",
        "Varlerly Maina": "Anomaly detection"}


def set_mode(mode):
    """Switch every colour the app uses to the light or dark palette."""
    global MODE, P, TEAL, INK, AMBER, CORAL, BLUE, MIST, MUTED, SLATE, TEAL_LIGHT, CLASS_COLOURS
    MODE = mode if mode in PALETTES else "light"
    P = PALETTES[MODE]
    TEAL, INK, AMBER, CORAL, BLUE = P["TEAL"], P["INK"], P["AMBER"], P["CORAL"], P["BLUE"]
    MIST, MUTED, SLATE, TEAL_LIGHT = P["MIST"], P["MUTED"], P["MUTED"], P["TEAL_LIGHT"]
    CLASS_COLOURS = alt.Scale(domain=[with_risk(c) for c in ("Class I", "Class II", "Class III")], range=[P["CORAL"], P["AMBER"], P["MIST"]])


set_mode("light")


# ---------------------------------------------------------------- chart theme (reads the current palette)
@alt.theme.register("pharmasignal", enable=True)
def _theme():
    return alt.theme.ThemeConfig({"config": {
        "font": "IBM Plex Sans, Segoe UI, Arial, sans-serif", "background": "transparent", "view": {"stroke": None},
        "axis": {"labelColor": P["MUTED"], "titleColor": P["MUTED"], "labelFontSize": 12.5, "titleFontSize": 12.5,
                 "titleFontWeight": 500, "gridColor": P["GRID"], "domainColor": P["LINE"], "tickColor": P["LINE"]},
        "axisY": {"domain": False, "ticks": False},
        "legend": {"labelColor": P["TEXT"], "titleColor": P["MUTED"], "labelFontSize": 12.5, "orient": "top",
                   "direction": "horizontal", "symbolType": "square"},
        "text": {"color": P["TEXT"]}, "bar": {"color": P["TEAL"]}, "line": {"color": P["TEAL"]},
    }})


def chart(c, height=320):
    alt.theme.enable("pharmasignal")
    st.altair_chart(c.properties(height=height), width="stretch", theme=None)


def ranked_bars(df, value, label, highlight=2, colour=None, height=320):
    """Horizontal bars, largest first; the top `highlight` bars in colour, the rest muted, value printed at the end."""
    colour = colour or P["TEAL"]
    df = df.sort_values(value, ascending=False).reset_index(drop=True)
    df["_rank"] = df.index
    base = alt.Chart(df).encode(
        y=alt.Y(f"{label}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260, labelFontSize=13, labelPadding=8,
                                                                   labelColor=P["TEXT"])),
        x=alt.X(f"{value}:Q", title=None, axis=None))
    bars = base.mark_bar(cornerRadiusEnd=5, height={"band": 0.72}).encode(
        color=alt.condition(f"datum._rank < {highlight}", alt.value(colour), alt.value(P["MIST"])),
        tooltip=[alt.Tooltip(f"{label}:N"), alt.Tooltip(f"{value}:Q", format=",")])
    labels = base.mark_text(align="left", dx=6, fontSize=12.5, fontWeight=500, color=P["TEXT"]).encode(
        text=alt.Text(f"{value}:Q", format=","))
    chart(bars + labels, height)


# ---------------------------------------------------------------- CSS
def _css():
    p = P
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400..600,0..1,0&display=block');
:root {{ --ps-ink:{p['INK']}; --ps-text:{p['TEXT']}; --ps-muted:{p['MUTED']}; --ps-card:{p['CARD']}; --ps-line:{p['LINE']};
        --ps-teal:{p['TEAL']}; --ps-teal-soft:{p['TEAL_SOFT']}; --ps-teal-text:{p['TEAL_TEXT']}; }}
html, body, [class*="css"], .stMarkdown, button, input, textarea, select {{
  font-family: 'IBM Plex Sans', 'Segoe UI', Arial, sans-serif; }}
.stApp {{ background: {p['BG']}; }}
.block-container {{ padding-top: 1.8rem; padding-bottom: 3rem; max-width: 1160px; }}
.stMain p, .stMain li, .stMain label, .stMain [data-testid="stMarkdownContainer"] {{ color: {p['TEXT']}; }}
.stMain [data-testid="stCaptionContainer"], .stMain [data-testid="stCaptionContainer"] p {{ color: {p['MUTED']} !important; }}
.stMain [data-testid="stWidgetLabel"] p {{ color: {p['INK']} !important; font-weight: 500; }}

/* headings: section titles centred with an accent bar */
.stMain h1, .stMain h2, .stMain h3 {{ color: {p['INK']} !important; letter-spacing: -0.01em; }}
.stMain h2 {{ font-size: 1.65rem !important; font-weight: 700 !important; text-align: center;
             margin: 2.6rem 0 0.3rem 0 !important; padding-bottom: 0.9rem !important; position: relative; }}
.stMain h2::after {{ content: ""; position: absolute; left: 50%; bottom: 0; transform: translateX(-50%);
                    width: 56px; height: 4px; border-radius: 2px; background: {p['TEAL']}; }}
.stMain h3 {{ font-size: 1.12rem !important; font-weight: 600 !important; margin-top: 0.6rem !important; }}
.ps-subwrap {{ width: 100%; text-align: center; }}
.stMain .ps-sub {{ color: {p['MUTED']} !important; font-size: 1.03rem; margin: 6px auto 20px auto !important; max-width: 68ch;
          line-height: 1.55; text-align: center; display: inline-block; }}

/* hero */
.ps-hero {{ background: radial-gradient(90% 120% at 50% 0%, {p['HERO_GLOW']} 0%, rgba(0,0,0,0) 60%), {p['HERO']};
           border-radius: 18px; padding: 26px 32px 0 32px; margin-bottom: 18px; overflow: hidden; text-align: center;
           box-shadow: 0 10px 30px rgba(11,34,57,0.18); }}
.ps-hero .kicker {{ display: inline-flex; align-items: center; gap: 8px; background: rgba(95,212,189,0.16);
                   color: #A8F0E2; border: 1px solid rgba(95,212,189,0.5); border-radius: 999px; padding: 6px 18px;
                   font-size: 1.02rem; font-weight: 700; letter-spacing: 0.01em; margin-bottom: 14px; }}
.ps-hero h1 {{ color: #FFFFFF !important; font-size: clamp(1.35rem, 2.4vw, 1.85rem); font-weight: 700; line-height: 1.2;
              margin: 0 auto 8px auto; padding: 0; max-width: 34ch; }}
.ps-hero p {{ color: #D3E0EA; font-size: 0.97rem; margin: 0 auto; max-width: 66ch; line-height: 1.55; }}
.ps-hero .ps-spark {{ display: block; width: calc(100% + 64px); margin: 16px -32px 0 -32px; height: 54px; }}
.ps-hero .note {{ color: #A9BDCF; font-size: 0.74rem; padding: 6px 0 10px 0; }}

/* inner page header, centred */
.ps-head {{ text-align: center; padding: 8px 0 22px 0; margin-bottom: 20px; border-bottom: 1px solid {p['LINE']}; }}
.ps-head .icon {{ width: 54px; height: 54px; border-radius: 16px; background: {p['TEAL_SOFT']}; color: {p['TEAL_TEXT']};
                 display: inline-flex; align-items: center; justify-content: center; font-size: 26px; margin-bottom: 10px; }}
.ps-head h1 {{ font-size: 2.2rem !important; font-weight: 700; margin: 0 0 6px 0; padding: 0; color: {p['INK']} !important; }}
.ps-head p {{ color: {p['MUTED']}; margin: 0 auto; font-size: 1.05rem; max-width: 64ch; line-height: 1.55; }}
.ps-ai {{ display: inline-block; background: {p['TEAL']}; color: #FFFFFF; font-size: 0.72rem; font-weight: 700;
         border-radius: 6px; padding: 2px 7px; margin-left: 8px; vertical-align: middle; letter-spacing: 0.02em; }}

/* findings */
.ps-find {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; margin: 6px 0 4px 0; }}
.ps-find > div {{ border-radius: 16px; padding: 20px 20px 18px 20px; border: 1px solid transparent; }}
.ps-find .n {{ font-size: 2.3rem; font-weight: 700; line-height: 1; }}
.ps-find .t {{ font-size: 0.98rem; line-height: 1.5; margin-top: 12px; color: {p['TEXT']}; }}
.ps-find .coral {{ background: {p['CORAL_SOFT']}; }} .ps-find .coral .n {{ color: {p['CORAL_TEXT']}; }}
.ps-find .teal {{ background: {p['TEAL_SOFT']}; }} .ps-find .teal .n {{ color: {p['TEAL_TEXT']}; }}
.ps-find .blue {{ background: {p['BLUE_SOFT']}; }} .ps-find .blue .n {{ color: {p['BLUE']}; }}
.ps-find .amber {{ background: {p['AMBER_SOFT']}; }} .ps-find .amber .n {{ color: {p['AMBER_TEXT']}; }}

/* KPI tiles */
.ps-kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: 6px 0 12px 0; }}
.ps-kpi {{ background: {p['CARD']}; border: 1px solid {p['LINE']}; border-radius: 14px; padding: 15px 17px;
          border-top: 4px solid {p['LINE']}; }}
.ps-kpi .v {{ font-size: 1.75rem; font-weight: 700; color: {p['INK']}; line-height: 1.1; }}
.ps-kpi .l {{ font-size: 0.9rem; color: {p['MUTED']}; margin-top: 6px; line-height: 1.4; }}
.ps-kpi.coral {{ border-top-color: {p['CORAL']}; }} .ps-kpi.amber {{ border-top-color: {p['AMBER']}; }}
.ps-kpi.teal {{ border-top-color: {p['TEAL']}; }} .ps-kpi.blue {{ border-top-color: {p['BLUE']}; }}

/* who / job / decision */
.ps-who {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin: 0 0 8px 0; }}
.ps-who > div {{ background: {p['CARD']}; border: 1px solid {p['LINE']}; border-radius: 14px; padding: 16px 18px; text-align: center; }}
.ps-who b {{ display: block; color: {p['TEAL_TEXT']}; font-size: 0.9rem; font-weight: 700; margin-bottom: 6px; }}
.ps-who span {{ color: {p['INK']}; font-size: 1rem; line-height: 1.5; }}

/* AI assistant feature band */
.ps-aiband {{ display: grid; grid-template-columns: 1.2fr 1fr; gap: 18px; background: {p['CARD']}; border: 1px solid {p['LINE']};
             border-radius: 18px; padding: 22px 24px; align-items: center; }}
.ps-aiband h4 {{ color: {p['INK']}; font-size: 1.2rem; font-weight: 700; margin: 0 0 8px 0; padding: 0; }}
.ps-aiband p {{ color: {p['TEXT']}; margin: 0 0 6px 0; line-height: 1.55; }}
.ps-aiband .q {{ background: {p['TEAL_SOFT']}; color: {p['INK']}; border-radius: 14px 14px 14px 4px; padding: 12px 14px;
                font-size: 0.95rem; margin-bottom: 8px; }}
.ps-aiband .a {{ background: {p['GREY_SOFT']}; color: {p['TEXT']}; border-radius: 14px 14px 4px 14px; padding: 12px 14px;
                font-size: 0.93rem; line-height: 1.5; }}
@media (max-width: 760px) {{ .ps-aiband {{ grid-template-columns: 1fr; }} }}

/* how-to steps */
.ps-steps {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin: 0 0 22px 0; }}
.ps-steps > div {{ display: flex; gap: 12px; align-items: flex-start; background: {p['CARD']}; border: 1px solid {p['LINE']};
                  border-radius: 14px; padding: 13px 15px; color: {p['TEXT']}; font-size: 0.96rem; line-height: 1.45; }}
.ps-steps .k {{ flex: none; width: 28px; height: 28px; border-radius: 50%; background: {p['TEAL']}; color: #FFF;
               font-size: 0.88rem; font-weight: 700; display: flex; align-items: center; justify-content: center; }}

/* recall class legend */
.ps-classes {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; margin: 4px 0 14px 0; }}
.ps-classes > div {{ border-radius: 12px; padding: 11px 15px; font-size: 0.93rem; line-height: 1.45; color: {p['TEXT']};
                    background: {p['CARD']}; border: 1px solid {p['LINE']}; }}
.ps-classes b {{ display: inline-block; border-radius: 6px; padding: 1px 9px; margin-right: 7px; font-weight: 700; font-size: 0.84rem; }}

/* chips */
.ps-chip {{ display: inline-block; border-radius: 999px; padding: 4px 12px; font-size: 0.84rem; font-weight: 700; white-space: nowrap; }}
.ps-chip.coral {{ background: {p['CORAL_SOFT']}; color: {p['CORAL_TEXT']}; }}
.ps-chip.amber {{ background: {p['AMBER_SOFT']}; color: {p['AMBER_TEXT']}; }}
.ps-chip.teal {{ background: {p['TEAL_SOFT']}; color: {p['TEAL_TEXT']}; }}
.ps-chip.grey {{ background: {p['GREY_SOFT']}; color: {p['MUTED']}; }}

/* bidder and signal cards */
.ps-bid, .ps-sig {{ background: {p['CARD']}; border: 1px solid {p['LINE']}; border-radius: 16px; padding: 17px 19px; }}
.ps-bid {{ margin: 0 0 4px 0; border-left-width: 5px; }}
.ps-bid.coral {{ border-left-color: {p['CORAL']}; }} .ps-bid.amber {{ border-left-color: {p['AMBER']}; }}
.ps-bid.teal {{ border-left-color: {p['TEAL']}; }} .ps-bid.grey {{ border-left-color: {p['MIST']}; }}
.ps-bid .top, .ps-sig .top {{ display: flex; justify-content: space-between; gap: 10px; align-items: flex-start; flex-wrap: wrap; }}
.ps-bid .name, .ps-sig .name {{ font-size: 1.1rem; font-weight: 700; color: {p['INK']}; }}
.ps-bid .match, .ps-sig .meta {{ color: {p['MUTED']}; font-size: 0.88rem; margin-top: 2px; }}
.ps-bid .flags {{ margin-top: 9px; font-size: 0.93rem; color: {p['TEXT']}; }}
.ps-bid .nums {{ display: flex; gap: 28px; flex-wrap: wrap; margin: 13px 0 9px 0; }}
.ps-bid .nums div {{ font-size: 0.85rem; color: {p['MUTED']}; }}
.ps-bid .nums b {{ display: block; font-size: 1.35rem; color: {p['INK']}; font-weight: 700; }}
.ps-bid .next {{ font-size: 0.95rem; color: {p['TEXT']}; border-top: 1px solid {p['SOFTLINE']}; padding-top: 10px; }}
.ps-sigs {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; margin: 4px 0 10px 0; }}
.ps-sig .body {{ color: {p['TEXT']}; font-size: 0.95rem; line-height: 1.5; margin-top: 9px; }}
.ps-sig .bar {{ height: 6px; border-radius: 3px; background: {p['GREY_SOFT']}; margin-top: 11px; overflow: hidden; }}
.ps-sig .bar span {{ display: block; height: 100%; background: {p['AMBER']}; border-radius: 3px; }}

/* evidence cards */
.ps-evs {{ display: grid; gap: 8px; margin: 4px 0 6px 0; }}
.ps-ev {{ background: {p['CARD']}; border: 1px solid {p['LINE']}; border-radius: 12px; padding: 11px 15px; font-size: 0.93rem;
         line-height: 1.5; color: {p['TEXT']}; }}
.ps-ev code {{ background: {p['TEAL_SOFT']}; color: {p['TEAL_TEXT']}; border-radius: 6px; padding: 1px 7px; font-size: 0.8rem; margin-right: 6px; }}

/* team */
.ps-team {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }}
.ps-team > div {{ background: {p['CARD']}; border: 1px solid {p['LINE']}; border-radius: 16px; padding: 18px; text-align: center; }}
.ps-team .av {{ width: 52px; height: 52px; border-radius: 50%; background: {p['TEAL_SOFT']}; color: {p['TEAL_TEXT']};
               display: inline-flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1.05rem; margin-bottom: 10px; }}
.ps-team .nm {{ color: {p['INK']}; font-weight: 700; font-size: 1rem; }}
.ps-team .rl {{ color: {p['MUTED']}; font-size: 0.9rem; margin-top: 4px; line-height: 1.4; }}

/* callouts */
.ps-note {{ border-radius: 12px; padding: 13px 17px; margin: 8px 0 14px 0; line-height: 1.55; font-size: 0.97rem; }}
.ps-note.info {{ background: {p['TEAL_SOFT']}; color: {p['INK']}; }}
.ps-note.warn {{ background: {p['AMBER_SOFT']}; color: {p['INK']}; border-left: 4px solid {p['AMBER']}; }}
.ps-note.limit {{ background: {p['GREY_SOFT']}; color: {p['INK']}; }}
.ps-note b {{ font-weight: 700; }}

/* links, buttons and the sidebar */
.stMain [data-testid="stPageLink"] a {{ background: {p['CARD']}; border: 1px solid {p['LINE']}; border-radius: 14px; padding: 14px;
  justify-content: center; }}
.stMain [data-testid="stPageLink"] a:hover {{ border-color: {p['TEAL']}; background: {p['TEAL_SOFT']}; }}
.stMain [data-testid="stPageLink"] a p, .stMain [data-testid="stPageLink"] a span {{ font-weight: 600; color: {p['INK']} !important; }}
.stMain button[kind="primary"] {{ background: {p['TEAL']}; border-color: {p['TEAL']}; color: #FFFFFF; font-weight: 600; }}
.stMain button[kind="primary"]:hover {{ filter: brightness(1.08); }}
/* evaluation table */
.ps-eval {{ width: 100%; border-collapse: separate; border-spacing: 0; background: {p['CARD']}; border: 1px solid {p['LINE']};
           border-radius: 14px; overflow: hidden; font-size: 0.94rem; }}
.ps-eval th {{ text-align: left; color: {p['MUTED']}; font-weight: 600; padding: 11px 14px; border-bottom: 1px solid {p['LINE']};
              background: {p['GREY_SOFT']}; }}
.ps-eval td {{ color: {p['TEXT']}; padding: 11px 14px; border-bottom: 1px solid {p['SOFTLINE']}; vertical-align: top; line-height: 1.45; }}
.ps-eval tr:last-child td {{ border-bottom: none; }}
.ps-eval td.c {{ color: {p['INK']}; font-weight: 600; white-space: nowrap; }}
.ps-eval td.n {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.ps-plot-gap {{ height: 2px; }}
[data-testid="stHeader"] {{ background: transparent !important; }}

/* sidebar: styled here as well as in config.toml, so it stays readable even if the theme file is not loaded */
[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {{ background-color: {p['SIDEBAR']} !important; }}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] span, [data-testid="stSidebar"] [data-testid="stSidebarNavLink"] span,
[data-testid="stSidebar"] [data-testid="stNavSectionHeader"], [data-testid="stSidebar"] [data-testid="stNavSectionHeader"] span,
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] {{ color: #DCE6EF !important; }}
[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] {{ color: #93AEC4 !important; font-weight: 600; }}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {{ background-color: rgba(255,255,255,0.08) !important; }}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {{ background-color: rgba(46,196,174,0.22) !important; }}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] span {{ color: #FFFFFF !important; font-weight: 600; }}
[data-testid="stSidebar"] hr, [data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] {{ border-color: rgba(255,255,255,0.15) !important; }}
[data-testid="stSidebar"] button svg, [data-testid="stSidebarCollapseButton"] svg {{ color: #DCE6EF !important; fill: #DCE6EF; }}
[data-testid="stSidebar"] .ps-side {{ font-size: 0.86rem; color: #C9D7E3; line-height: 1.55; }}
[data-testid="stSidebar"] .ps-side b {{ color: #FFFFFF; font-weight: 600; }}
[data-testid="stSidebar"] .ps-side .role {{ color: #93AEC4; font-size: 0.8rem; }}
[data-testid="stSidebar"] .ps-sidehead {{ color: #FFFFFF; font-weight: 700; font-size: 0.95rem; margin: 6px 0 2px 0; }}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{ color: #DCE6EF !important; }}
[data-testid="stSidebar"] .ps-side .dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }}
.ps-kpi, .ps-who > div, .ps-aiband, .ps-steps > div, .ps-classes > div, .ps-bid, .ps-sig, .ps-ev, .ps-team > div,
.ps-eval, .stMain [data-testid="stPageLink"] a {{ box-shadow: 0 1px 2px rgba(11,34,57,0.04), 0 4px 14px rgba(11,34,57,0.05); }}
/* ---- clickable vs information: anything you can click is teal-tinted with an arrow; information panels are flat */
.stMain [data-testid="stPageLink"] a {{ background: {p['TEAL_SOFT']} !important; border: 1.5px solid {p['TEAL']} !important;
  border-radius: 14px !important; padding: 13px 16px !important; justify-content: center; transition: all .15s ease; }}
.stMain [data-testid="stPageLink"] a:hover {{ background: {p['TEAL']} !important; }}
.stMain [data-testid="stPageLink"] a:hover p, .stMain [data-testid="stPageLink"] a:hover span {{ color: #FFFFFF !important; }}
.stMain [data-testid="stPageLink"] a p {{ color: {p['TEAL_TEXT']} !important; font-weight: 700 !important; }}
.stMain [data-testid="stPageLink"] a span[data-testid="stIconMaterial"] {{ color: {p['TEAL']} !important; }}
.stMain [data-testid="stPageLink"] a::after {{ content: "›"; font-size: 1.35rem; line-height: 1; margin-left: 10px;
  color: {p['TEAL']}; font-weight: 700; }}
.stMain [data-testid="stPageLink"] a:hover::after {{ color: #FFFFFF; }}
.ps-who > div {{ background: {p['GREY_SOFT']} !important; border: none !important; box-shadow: none !important; text-align: left !important;
  border-top: 4px solid {p['TEAL']} !important; padding: 18px 20px 20px 20px !important; }}
.ps-who .wh {{ display: flex; align-items: center; gap: 10px; color: {p['INK']}; font-size: 1.22rem; font-weight: 700;
  line-height: 1.25; margin-bottom: 10px; }}
.ps-who .wh .msr {{ display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px; flex: none;
  border-radius: 10px; background: {p['TEAL_SOFT']}; color: {p['TEAL']}; font-size: 22px; }}
.ps-who p {{ color: {p['TEXT']}; font-size: 0.98rem; line-height: 1.55; margin: 0; }}
.ps-who .tags {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 2px; }}
.ps-who .tags span {{ display: inline-block; background: {p['CARD']}; border: 1px solid {p['LINE']}; color: {p['INK']};
  border-radius: 999px; padding: 3px 10px; font-size: 0.86rem; font-weight: 500; line-height: 1.4; }}
.ps-infolabel {{ text-align: center; color: {p['MUTED']}; font-size: 0.86rem; margin: 2px 0 12px 0; }}

/* ---- numbered route on the home page: solid buttons with a step number, a short note underneath */
.ps-stage {{ color: {p['INK']}; font-size: 1.05rem; font-weight: 700; margin: 4px 0 10px 0; padding-bottom: 8px;
  border-bottom: 2px solid {p['TEAL']}; }}
.ps-stage small {{ display: block; color: {p['MUTED']}; font-size: 0.82rem; font-weight: 500; margin-top: 2px; }}
.st-key-journey [data-testid="stPageLink"] a {{ background: {p['TEAL']} !important; border: 1.5px solid {p['TEAL']} !important;
  justify-content: flex-start !important; padding: 11px 14px !important; border-radius: 12px !important; min-height: 60px;
  box-shadow: 0 2px 0 {p['TEAL_TEXT']}, 0 6px 14px rgba(15,118,110,0.18) !important; }}
.st-key-journey [data-testid="stPageLink"] a:hover {{ background: {p['TEAL_TEXT']} !important; transform: translateY(-1px); }}
.st-key-journey [data-testid="stPageLink"] a p {{ color: #FFFFFF !important; font-size: 1rem !important; }}
.st-key-journey [data-testid="stPageLink"] a > span:has([data-testid="stIconMaterial"]) {{ display: none !important; }}
.st-key-journey [data-testid="stPageLink"] a > span:last-child {{ flex: 1 1 auto !important; overflow: visible !important;
  white-space: normal !important; min-width: 0; }}
.st-key-journey [data-testid="stPageLink"] a > span:last-child * {{ white-space: normal !important; text-align: left; line-height: 1.25; }}
.st-key-journey [data-testid="stPageLink"] a::before {{ display: inline-flex; align-items: center; justify-content: center; flex: none;
  width: 28px; height: 28px; border-radius: 50%; background: #FFFFFF; color: {p['TEAL_TEXT']}; font-weight: 800;
  font-size: 0.95rem; margin-right: 10px; }}
.st-key-journey [data-testid="stPageLink"] a::after {{ color: #FFFFFF !important; margin-left: auto !important; padding-left: 8px; }}
.ps-stepnote {{ color: {p['TEXT']}; font-size: 0.9rem; line-height: 1.45; margin: 6px 2px 16px 2px; }}

/* ---- expanders read as buttons, so nobody misses them */
.stMain [data-testid="stExpander"] details {{ border: 1.5px solid {p['TEAL']} !important; border-radius: 12px !important;
  overflow: hidden; background: {p['CARD']}; }}
.stMain [data-testid="stExpander"] summary {{ background: {p['TEAL_SOFT']}; padding-top: 10px; padding-bottom: 10px; }}
.stMain [data-testid="stExpander"] summary p, .stMain [data-testid="stExpander"] summary span {{ color: {p['TEAL_TEXT']} !important;
  font-weight: 700 !important; }}
.stMain [data-testid="stExpander"] summary svg {{ color: {p['TEAL']} !important; }}
.stMain [data-testid="stExpander"] summary:hover {{ background: {p['TEAL']}; }}
.stMain [data-testid="stExpander"] summary:hover p, .stMain [data-testid="stExpander"] summary:hover span,
.stMain [data-testid="stExpander"] summary:hover svg {{ color: #FFFFFF !important; }}

/* ---- readable tables */
.ps-table {{ width: 100%; border-collapse: separate; border-spacing: 0; background: {p['CARD']}; border: 1px solid {p['LINE']};
            border-radius: 14px; overflow: hidden; font-size: 0.95rem; margin: 4px 0 10px 0;
            box-shadow: 0 1px 2px rgba(11,34,57,0.04), 0 4px 14px rgba(11,34,57,0.05); }}
.ps-table th {{ text-align: left; background: {p['INK']}; color: #FFFFFF; font-weight: 600; padding: 11px 14px; font-size: 0.86rem; }}
.ps-table th.n, .ps-table td.n {{ text-align: right; }}
.ps-table td {{ color: {p['TEXT']}; padding: 11px 14px; border-bottom: 1px solid {p['SOFTLINE']}; vertical-align: middle; line-height: 1.4; }}
.ps-table tr:nth-child(even) td {{ background: {p['GREY_SOFT']}; }}
.ps-table tr:last-child td {{ border-bottom: none; }}
.ps-table td.strong {{ color: {p['INK']}; font-weight: 700; }}
.ps-table td.n {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
.ps-table .sub {{ display: block; color: {p['MUTED']}; font-size: 0.82rem; font-weight: 400; margin-top: 2px; }}
.ps-table .rank {{ display: inline-flex; width: 26px; height: 26px; border-radius: 50%; background: {p['TEAL_SOFT']};
                  color: {p['TEAL_TEXT']}; font-weight: 700; font-size: 0.82rem; align-items: center; justify-content: center; }}
.ps-bar {{ display: flex; align-items: center; gap: 8px; min-width: 140px; }}
.ps-bar .track {{ flex: 1; height: 8px; border-radius: 4px; background: {p['GREY_SOFT']}; overflow: hidden; }}
.ps-bar .fill {{ height: 100%; border-radius: 4px; background: {p['TEAL']}; }}
.ps-bar b {{ min-width: 34px; text-align: right; color: {p['INK']}; font-variant-numeric: tabular-nums; }}
.ps-tablewrap {{ overflow-x: auto; }}

/* ---- explainer cards */
.ps-explain {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; margin: 6px 0 14px 0; }}
.ps-explain > div {{ border-radius: 14px; padding: 15px 17px; border-top: 4px solid {p['TEAL']}; background: {p['CARD']};
                    border-left: 1px solid {p['LINE']}; border-right: 1px solid {p['LINE']}; border-bottom: 1px solid {p['LINE']};
                    box-shadow: 0 1px 2px rgba(11,34,57,0.04), 0 4px 14px rgba(11,34,57,0.05); }}
.ps-explain .ic {{ font-size: 1.35rem; }}
.ps-explain h5 {{ color: {p['INK']}; font-size: 1.02rem; font-weight: 700; margin: 6px 0 6px 0; padding: 0; }}
.ps-explain p {{ color: {p['TEXT']}; font-size: 0.93rem; line-height: 1.5; margin: 0; }}
.ps-explain .blue {{ border-top-color: {p['BLUE']}; }} .ps-explain .amber {{ border-top-color: {p['AMBER']}; }}
.ps-explain .coral {{ border-top-color: {p['CORAL']}; }} .ps-explain .green {{ border-top-color: {p['GREEN']}; }}
.ps-tip {{ display: flex; gap: 10px; align-items: flex-start; background: {p['BLUE_SOFT']}; border-radius: 12px; padding: 12px 15px;
          color: {p['INK']}; font-size: 0.94rem; line-height: 1.5; margin: 6px 0 12px 0; }}
.ps-tip .i {{ flex: none; width: 22px; height: 22px; border-radius: 50%; background: {p['BLUE']}; color: #FFF; font-weight: 700;
             font-size: 0.8rem; display: flex; align-items: center; justify-content: center; margin-top: 1px; }}

/* ---- AI assistant colour coding */
[class*="st-key-ans_teal"], [class*="st-key-ans_blue"], [class*="st-key-ans_amber"], [class*="st-key-ans_grey"] {{
  border-radius: 14px; padding: 12px 16px 6px 16px !important; margin-bottom: 8px; }}
[class*="st-key-ans_teal"] {{ background: {p['TEAL_SOFT']}; border-left: 5px solid {p['TEAL']}; }}
[class*="st-key-ans_blue"] {{ background: {p['BLUE_SOFT']}; border-left: 5px solid {p['BLUE']}; }}
[class*="st-key-ans_amber"] {{ background: {p['AMBER_SOFT']}; border-left: 5px solid {p['AMBER']}; }}
[class*="st-key-ans_grey"] {{ background: {p['GREY_SOFT']}; border-left: 5px solid {p['MIST']}; }}
.ps-anshead {{ font-weight: 700; font-size: 0.95rem; margin-bottom: 2px; }}
.ps-anshead.teal {{ color: {p['TEAL_TEXT']}; }} .ps-anshead.blue {{ color: {p['BLUE']}; }}
.ps-anshead.amber {{ color: {p['AMBER_TEXT']}; }} .ps-anshead.grey {{ color: {p['MUTED']}; }}
.stMain [data-testid="stChatMessage"] {{ background: transparent; }}
[class*="st-key-askq"] button {{ background: {p['CARD']} !important; border: 1.5px solid {p['TEAL']} !important;
  color: {p['TEAL_TEXT']} !important; font-weight: 600; border-radius: 12px !important; text-align: left; }}
[class*="st-key-askq"] button:hover {{ background: {p['TEAL']} !important; color: #FFFFFF !important; }}
.ps-userq {{ background: {p['INK']}; color: #FFFFFF; border-radius: 16px 16px 4px 16px; padding: 12px 16px; margin: 14px 0 8px auto;
            max-width: 80%; width: fit-content; font-weight: 500; }}
.ps-aitag {{ display: inline-flex; align-items: center; gap: 6px; color: {p['TEAL_TEXT']}; font-weight: 700; font-size: 0.9rem;
            margin: 4px 0 8px 0; }}

/* ---- call to action and action points */
[class*="st-key-cta"] {{ background: linear-gradient(135deg, {p['TEAL_SOFT']}, {p['BLUE_SOFT']}); border: 1.5px solid {p['TEAL']};
  border-radius: 18px; padding: 20px 22px 12px 22px !important; }}
.ps-ctahead {{ display: flex; gap: 12px; align-items: center; margin-bottom: 4px; }}
.ps-ctahead .badge {{ background: {p['TEAL']}; color: #FFF; border-radius: 999px; padding: 4px 12px; font-size: 0.78rem; font-weight: 700; }}
.ps-ctahead h4 {{ color: {p['INK']}; margin: 0; padding: 0; font-size: 1.2rem; font-weight: 700; }}
.ps-actions {{ display: grid; gap: 10px; margin: 6px 0 12px 0; }}
.ps-actions > div {{ display: grid; grid-template-columns: 34px 1fr auto; gap: 12px; align-items: center; background: {p['CARD']};
  border: 1px solid {p['LINE']}; border-radius: 14px; padding: 12px 16px; box-shadow: 0 1px 2px rgba(11,34,57,0.04); }}
.ps-actions .num {{ width: 30px; height: 30px; border-radius: 50%; background: {p['INK']}; color: #FFF; font-weight: 700;
  display: flex; align-items: center; justify-content: center; font-size: 0.9rem; }}
.ps-actions b {{ color: {p['INK']}; display: block; }}
.ps-actions span.d {{ color: {p['MUTED']}; font-size: 0.9rem; }}
.stMain [data-testid="stBaseButton-primary"], .stMain [data-testid="stBaseButton-primaryFormSubmit"] {{
  background: {p['TEAL']} !important; border-color: {p['TEAL']} !important; }}
.stMain [data-testid="stBaseButton-primary"] *, .stMain [data-testid="stBaseButton-primaryFormSubmit"] * {{ color: #FFFFFF !important; }}
.stMain [data-testid="stBaseButton-primary"]:hover, .stMain [data-testid="stBaseButton-primaryFormSubmit"]:hover {{ filter: brightness(1.1); }}
.ps-chip.grey {{ box-shadow: inset 0 0 0 1px {p['LINE']}; background: {p['CARD']} !important; }}
.msr {{ font-family: 'Material Symbols Rounded'; font-weight: 500; font-style: normal; line-height: 1; letter-spacing: normal;
  text-transform: none; display: inline-block; white-space: nowrap; direction: ltr; -webkit-font-feature-settings: 'liga';
  font-feature-settings: 'liga'; -webkit-font-smoothing: antialiased; vertical-align: -0.2em; }}
.ps-head .icon .msr {{ font-size: 30px; }}
.ps-explain .ic .msr {{ font-size: 28px; color: {p['TEAL']}; }}
.ps-explain .blue .ic .msr {{ color: {p['BLUE']}; }} .ps-explain .amber .ic .msr {{ color: {p['AMBER']}; }}
.ps-explain .coral .ic .msr {{ color: {p['CORAL']}; }} .ps-explain .green .ic .msr {{ color: {p['GREEN']}; }}
.ps-anshead .msr, .ps-aitag .msr {{ font-size: 20px; margin-right: 6px; }}
.ps-hero .kicker .msr {{ font-size: 20px; }}
.ps-foot {{ color: {p['MUTED']}; font-size: 0.84rem; border-top: 1px solid {p['LINE']}; margin-top: 40px; padding-top: 14px; text-align: center; }}
</style>
"""


def apply_style():
    st.markdown(_css(), unsafe_allow_html=True)


def icon(name):
    """A Material Symbols line icon (same family as the sidebar icons)."""
    return f'<span class="msr">{html.escape(name)}</span>'


def esc(text):
    return html.escape(str(text))


def _html(markup):
    st.markdown(with_risk(markup), unsafe_allow_html=True)


# ---------------------------------------------------------------- building blocks
def sparkline_svg(values, width=1000, height=96):
    v = np.asarray(values, dtype=float)
    if len(v) < 2:
        return ""
    x = np.linspace(0, width, len(v))
    y = height - 6 - (v - v.min()) / max(v.max() - v.min(), 1) * (height - 16)
    pts = " ".join(f"{a:.1f},{b:.1f}" for a, b in zip(x, y))
    peak = int(np.argmax(v))
    return (f'<svg class="ps-spark" viewBox="0 0 {width} {height}" preserveAspectRatio="none" role="img" '
            f'aria-label="Monthly recall events over time">'
            f'<polygon points="0,{height} {pts} {width},{height}" fill="rgba(46,196,174,0.30)"/>'
            f'<polyline points="{pts}" fill="none" stroke="#7BE3D1" stroke-width="1.8" vector-effect="non-scaling-stroke"/>'
            f'<circle cx="{x[peak]:.1f}" cy="{y[peak]:.1f}" r="5" fill="#F2AE45" stroke="#0B2239" stroke-width="2"/></svg>')


def hero(kicker, title, text, spark_values=None, spark_note=""):
    spark = sparkline_svg(spark_values) if spark_values is not None else ""
    note = f'<div class="note">{esc(spark_note)}</div>' if spark_note else '<div style="height:30px"></div>'
    _html(f'<div class="ps-hero"><div class="kicker">{icon("auto_awesome")}{esc(kicker)}</div><h1>{esc(title)}</h1><p>{esc(text)}</p>{spark}{note}</div>')


def page_header(title, text, icon="", ai=False):
    badge = '<span class="ps-ai">AI</span>' if ai else ""
    ic = f'<div class="icon"><span class="msr">{esc(icon)}</span></div><br>' if icon else ""
    _html(f'<div class="ps-head">{ic}<h1>{esc(title)}{badge}</h1><p>{esc(text)}</p></div>')


def section(title, text=None):
    st.header(title, anchor=False)
    if text:
        _html(f'<div class="ps-subwrap"><p class="ps-sub">{esc(text)}</p></div>')


def findings(items):
    """items: list of (big value, sentence, tone) where tone is 'coral', 'teal', 'blue' or 'amber'."""
    _html('<div class="ps-find">' + "".join(f'<div class="{t}"><div class="n">{esc(n)}</div><div class="t">{esc(s)}</div></div>'
                                            for n, s, t in items) + "</div>")


def kpis(items):
    """items: list of (value, label, tone) where tone is '', 'coral', 'amber', 'teal' or 'blue'."""
    _html('<div class="ps-kpis">' + "".join(f'<div class="ps-kpi {t}"><div class="v">{esc(v)}</div><div class="l">{esc(l)}</div></div>'
                                            for v, l, t in items) + "</div>")


def steps(items):
    _html('<div class="ps-steps">' + "".join(f'<div><span class="k">{i}</span><span>{esc(s)}</span></div>'
                                             for i, s in enumerate(items, 1)) + "</div>")


def who_strip(cards):
    """cards: list of (icon, heading, text, chips). chips is an optional list of short labels shown under the text."""
    out = []
    for ic, head, text, tags in cards:
        tagh = ('<div class="tags">' + "".join(f"<span>{esc(t)}</span>" for t in tags) + "</div>") if tags else ""
        body = f"<p>{esc(text)}</p>" if text else ""
        out.append(f'<div><div class="wh"><span class="msr">{esc(ic)}</span>{esc(head)}</div>{body}{tagh}</div>')
    _html('<div class="ps-who">' + "".join(out) + "</div>")


def journey_css(n_steps):
    """Number badges for the numbered route buttons on the home page."""
    return "<style>" + "".join(f'.st-key-jstep_{i} [data-testid="stPageLink"] a::before {{ content: "{i}"; }}'
                               for i in range(1, n_steps + 1)) + "</style>"


def ai_band(title, text, question, answer):
    _html(f'<div class="ps-aiband"><div><h4>{esc(title)}<span class="ps-ai">AI</span></h4><p>{esc(text)}</p></div>'
          f'<div><div class="q">{esc(question)}</div><div class="a">{esc(answer)}</div></div></div>')


def class_legend():
    fills = {"Class I": (P["CORAL_SOFT"], P["CORAL_TEXT"]), "Class II": (P["AMBER_SOFT"], P["AMBER_TEXT"]),
             "Class III": (P["GREY_SOFT"], P["MUTED"])}
    _html('<div class="ps-classes">' + "".join(
        f'<div><b style="background:{bg};color:{fg}">{c}</b>{esc(CLASS_TEXT[c])}</div>' for c, (bg, fg) in fills.items()) + "</div>")


def chip(text, tone):
    return f'<span class="ps-chip {tone}">{esc(text)}</span>'


def bidder_card(name, match_text, flags_text, status_text, tone, numbers, next_step):
    nums = "".join(f'<div><b>{esc(v)}</b>{esc(k)}</div>' for k, v in numbers)
    flags = f'<div class="flags">{esc(flags_text)}</div>' if flags_text else ""
    _html(f'<div class="ps-bid {tone}"><div class="top"><div><div class="name">{esc(name)}</div>'
          f'<div class="match">{esc(match_text)}</div></div>{chip(status_text, tone)}</div>{flags}'
          f'<div class="nums">{nums}</div><div class="next"><b>Next step:</b> {esc(next_step)}</div></div>')


def signal_cards(items):
    """items: dicts with name, kind, month, events, usual, methods, flagged_by, class_i."""
    cards = []
    for it in items:
        consensus = it["methods"] >= 2
        badge = chip(f"Consensus, {it['methods']} of 3" if consensus else f"{it['methods']} of 3 methods",
                     "amber" if consensus else "grey")
        ratio = it["events"] / max(it["usual"], 0.1)
        width = min(100, ratio / 6 * 100)
        jump = (f"about {ratio:.0f} times the normal level" if it["usual"] >= 1
                else "a sharp rise from a usually quiet level")
        cls = f" {it['class_i']:.0f}% of the records were Class I." if it.get("class_i") == it.get("class_i") else ""
        cards.append(f'<div class="ps-sig"><div class="top"><div><div class="name">{esc(it["name"])}</div>'
                     f'<div class="meta">{esc(it["kind"])}, {esc(it["month"])}</div></div>{badge}</div>'
                     f'<div class="body"><b>{it["events"]}</b> recall events against a usual <b>{it["usual"]:.1f}</b> a month, '
                     f'{jump}. Flagged by {esc(it["flagged_by"])}.{cls}</div>'
                     f'<div class="bar" title="Size of the jump"><span style="width:{width:.0f}%"></span></div></div>')
    _html('<div class="ps-sigs">' + "".join(cards) + "</div>")


def evidence_cards(df, n=3, length=260):
    rows = []
    for e in df.head(n).itertuples():
        text = e.text if len(e.text) <= length else e.text[:length].rsplit(" ", 1)[0] + "..."
        rows.append(f'<div class="ps-ev"><code>{esc(e.doc_id)}</code>{esc(text)}</div>')
    _html('<div class="ps-evs">' + "".join(rows) + "</div>")


def team_cards(team):
    initials = lambda n: "".join(w[0] for w in n.split()[:2]).upper()
    _html('<div class="ps-team">' + "".join(
        f'<div><div class="av">{initials(n)}</div><div class="nm">{esc(n)}</div><div class="rl">{esc(r)}</div></div>'
        for n, r in team.items()) + "</div>")


def note(text, kind="info"):
    _html(f'<div class="ps-note {kind}">{text}</div>')


def footer(source):
    _html(f'<div class="ps-foot">PharmaSignal AI, a capstone group project. Data: {esc(source)}. '
          'It gives evidence for people to weigh and never a verdict on a medicine or supplier.</div>')


STATUS_TONE = {"Met": "teal", "Done": "teal", "Checked live": "teal", "Scheduled": "grey"}


def eval_table(df):
    rows = "".join(
        f'<tr><td class="c">{esc(r.component)}</td><td>{esc(r.target)}</td><td>{esc(r.achieved)}</td>'
        f'<td>{chip(r.status, STATUS_TONE.get(r.status, "amber"))}</td></tr>' for r in df.itertuples())
    _html(f'<table class="ps-eval"><thead><tr><th>Component</th><th>Target</th><th>Result</th><th>Status</th></tr></thead>'
          f'<tbody>{rows}</tbody></table>')


# ---------------------------------------------------------------- Plotly (signals module)
STRENGTH = {3: ("Strong", "coral"), 2: ("Moderate", "amber"), 1: ("Low", "grey")}
STRENGTH_HELP = "Strong = all three detection methods agree; Moderate = two agree; Low = one method only."


def strength_label(n_methods):
    return STRENGTH.get(int(min(max(n_methods, 1), 3)))[0]


def strength_colours():
    return {"Strong": P["CORAL"], "Moderate": P["AMBER"], "Low": P["FAINT"]}


def plotly_chart(fig, height=380):
    font = "IBM Plex Sans, Segoe UI, Arial, sans-serif"
    fig.update_layout(height=height, margin=dict(l=70, r=16, t=40, b=56), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family=font, color=P["TEXT"], size=13),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=P["TEXT"]), title_text=""),
                      hoverlabel=dict(font_family=font, bgcolor=P["CARD_SOLID"], font_color=P["TEXT"], bordercolor=P["MIST"]))
    for ax in (fig.update_xaxes, fig.update_yaxes):
        ax(automargin=True, gridcolor=P["GRID"], zeroline=False, linecolor=P["MIST"], tickfont=dict(color=P["MUTED"]),
           title_font=dict(color=P["MUTED"]))
    _html('<div class="ps-plot-gap"></div>')
    st.plotly_chart(fig, width="stretch", theme=None,
                    config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]})


def signal_table(rows):
    """rows: dicts with month, kind, name, events, usual, times, flagged_by, class_i, strength."""
    tone = {k: t for k, t in STRENGTH.values()}
    body = "".join(
        f'<tr><td>{esc(r["month"])}</td><td>{esc(r["kind"])}</td><td class="c">{esc(r["name"])}</td>'
        f'<td class="n">{r["events"]}</td><td class="n">{r["usual"]:.1f}</td><td class="n">{r["times"]}</td>'
        f'<td>{esc(r["flagged_by"])}</td><td class="n">{r["class_i"]}</td>'
        f'<td>{chip(r["strength"], tone.get(r["strength"], "grey"))}</td></tr>' for r in rows)
    _html('<div style="overflow-x:auto"><table class="ps-eval ps-stable"><thead><tr><th>Month</th><th>Watching</th><th>Name</th>'
          '<th>Events</th><th>Usual / month</th><th>× usual</th><th>Flagged by</th><th>Class I share</th><th>Strength</th>'
          f'</tr></thead><tbody>{body}</tbody></table></div>')



# ---------------------------------------------------------------- polish components
def table(columns, rows, numeric=(), wrap=True):
    """columns: list of headers; rows: list of lists of HTML-safe cell strings (use esc for text)."""
    head = "".join(f'<th class="{"n" if i in numeric else ""}">{esc(c)}</th>' for i, c in enumerate(columns))
    body = "".join("<tr>" + "".join(f'<td class="{"n" if i in numeric else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>"
                   for r in rows)
    _html(f'<div class="ps-tablewrap"><table class="ps-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')


def bar_cell(value, maximum, colour=None):
    w = 0 if not maximum else max(3, value / maximum * 100)
    style = f"width:{w:.0f}%" + (f";background:{colour}" if colour else "")
    return f'<div class="ps-bar"><div class="track"><div class="fill" style="{style}"></div></div><b>{value:,}</b></div>'


def explainers(items):
    """items: list of (icon, title, text, tone) where tone is '', 'blue', 'amber', 'coral' or 'green'."""
    _html('<div class="ps-explain">' + "".join(
        f'<div class="{t}"><div class="ic"><span class="msr">{esc(ic)}</span></div><h5>{esc(ti)}</h5><p>{tx}</p></div>' for ic, ti, tx, t in items) + "</div>")


def tip(text):
    _html(f'<div class="ps-tip"><span class="i">i</span><span>{text}</span></div>')


def actions(items):
    """items: list of (title, detail, status, tone)."""
    _html('<div class="ps-actions">' + "".join(
        f'<div><span class="num">{i}</span><span><b>{esc(t)}</b><span class="d">{esc(dt)}</span></span>{chip(stt, tn)}</div>'
        for i, (t, dt, stt, tn) in enumerate(items, 1)) + "</div>")
