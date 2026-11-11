"""Shared look and feel for the PharmaSignal app.

One palette, one chart theme and a small set of building blocks (hero, findings, steps, KPI tiles, status chips,
callouts) so every page looks and reads the same way.
"""
import html

import altair as alt
import numpy as np
import streamlit as st

# ---------------------------------------------------------------- palette
INK = "#102A43"          # navy: sidebar, headings, hero
INK_2 = "#1B3A57"
TEXT = "#243B53"
SLATE = "#627D98"        # secondary text
MIST = "#A8BBCC"         # de-emphasised data, Class III
LINE = "#DCE4EA"
PAPER = "#F7F9FA"
TEAL = "#0F766E"         # primary: actions and the data that matters
TEAL_SOFT = "#E6F2F0"
TEAL_LIGHT = "#7DD3C0"
AMBER = "#D9912B"        # signals
AMBER_SOFT = "#FBF3E4"
CORAL = "#C2462F"        # Class I only
CORAL_SOFT = "#FBEAE6"

CLASS_COLOURS = alt.Scale(domain=["Class I", "Class II", "Class III"], range=[CORAL, AMBER, MIST])
CLASS_TEXT = {"Class I": "Serious harm or death is reasonably possible.",
              "Class II": "Temporary or reversible harm is possible; serious harm is unlikely.",
              "Class III": "Unlikely to cause harm, but breaks the rules (e.g. a labelling error)."}

TEAM = ["Cindy Murogo", "Daniel Kimasar", "Mananda Kirungu Salim", "Nelson Masaki", "Varlerly Maina"]


# ---------------------------------------------------------------- chart theme
@alt.theme.register("pharmasignal", enable=True)
def _theme():
    font = "IBM Plex Sans, Segoe UI, Arial, sans-serif"
    return alt.theme.ThemeConfig({"config": {
        "font": font, "background": "transparent", "view": {"stroke": None},
        "axis": {"labelColor": SLATE, "titleColor": SLATE, "labelFontSize": 12, "titleFontSize": 12,
                 "titleFontWeight": 500, "gridColor": "#E9EEF2", "domainColor": LINE, "tickColor": LINE},
        "axisY": {"domain": False, "ticks": False},
        "legend": {"labelColor": TEXT, "titleColor": SLATE, "labelFontSize": 12, "titleFontSize": 12,
                   "orient": "top", "direction": "horizontal", "symbolType": "square"},
        "bar": {"color": TEAL}, "line": {"color": TEAL},
    }})


def chart(c, height=320):
    st.altair_chart(c.properties(height=height), width="stretch", theme=None)


def ranked_bars(df, value, label, highlight=2, colour=TEAL, height=320):
    """Horizontal bars, largest first; the top `highlight` bars in colour, the rest muted, value printed at the end."""
    df = df.sort_values(value, ascending=False).reset_index(drop=True)
    df["_rank"] = df.index
    base = alt.Chart(df).encode(y=alt.Y(f"{label}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260, labelFontSize=12.5, labelPadding=8)),
                                x=alt.X(f"{value}:Q", title=None, axis=None))
    bars = base.mark_bar(cornerRadiusEnd=4, height={"band": 0.72}).encode(
        color=alt.condition(f"datum._rank < {highlight}", alt.value(colour), alt.value(MIST)),
        tooltip=[alt.Tooltip(f"{label}:N"), alt.Tooltip(f"{value}:Q", format=",")])
    labels = base.mark_text(align="left", dx=5, fontSize=12, color=TEXT).encode(text=alt.Text(f"{value}:Q", format=","))
    chart(bars + labels, height)


# ---------------------------------------------------------------- CSS
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, button, input, textarea, select {{
  font-family: 'IBM Plex Sans', 'Segoe UI', Arial, sans-serif; }}
.block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 1160px; }}
.stMain h1, .stMain h2, .stMain h3 {{ color: {INK}; letter-spacing: -0.01em; }}
.stMain h2 {{ font-size: 1.5rem !important; font-weight: 600 !important; margin: 2.2rem 0 0.2rem 0 !important; }}
.stMain h3 {{ font-size: 1.12rem !important; font-weight: 600 !important; margin-top: 0.6rem !important; }}
.ps-sub {{ color: {SLATE}; font-size: 0.97rem; margin: 0 0 14px 0; max-width: 75ch; line-height: 1.5; }}

/* hero */
.ps-hero {{ background: {INK}; border-radius: 16px; padding: 34px 38px 0 38px; margin-bottom: 20px; overflow: hidden; }}
.ps-hero .kicker {{ color: {TEAL_LIGHT}; font-size: 0.95rem; font-weight: 500; margin-bottom: 10px; }}
.ps-hero h1 {{ color: #FFFFFF; font-size: clamp(1.55rem, 3.6vw, 2.35rem); font-weight: 600; line-height: 1.15;
              margin: 0 0 10px 0; padding: 0; max-width: 24ch; }}
.ps-hero p {{ color: #BCCCDC; font-size: 1.05rem; margin: 0; max-width: 60ch; line-height: 1.55; }}
.ps-hero .ps-spark {{ display: block; width: calc(100% + 76px); margin: 22px -38px 0 -38px; height: 96px; }}
.ps-hero .note {{ color: #829AB1; font-size: 0.8rem; padding: 8px 0 14px 0; }}

/* inner page header */
.ps-head {{ border-bottom: 1px solid {LINE}; padding-bottom: 14px; margin-bottom: 18px; }}
.ps-head h1 {{ font-size: 2rem; font-weight: 600; margin: 0 0 4px 0; padding: 0; color: {INK}; }}
.ps-head p {{ color: {SLATE}; margin: 0; font-size: 1.02rem; max-width: 70ch; line-height: 1.5; }}

/* findings: the four things to remember */
.ps-find {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; margin: 6px 0 4px 0; }}
.ps-find > div {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 12px; padding: 18px 18px 16px 18px; }}
.ps-find .n {{ font-size: 2.1rem; font-weight: 600; line-height: 1; color: {TEAL}; }}
.ps-find .n.coral {{ color: {CORAL}; }} .ps-find .n.amber {{ color: {AMBER}; }} .ps-find .n.ink {{ color: {INK}; }}
.ps-find .t {{ color: {TEXT}; font-size: 0.97rem; line-height: 1.45; margin-top: 10px; }}

/* KPI tiles */
.ps-kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: 6px 0 10px 0; }}
.ps-kpi {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 12px; padding: 14px 16px; }}
.ps-kpi .v {{ font-size: 1.7rem; font-weight: 600; color: {INK}; line-height: 1.1; }}
.ps-kpi .l {{ font-size: 0.88rem; color: {SLATE}; margin-top: 5px; line-height: 1.35; }}
.ps-kpi.coral {{ box-shadow: inset 4px 0 0 {CORAL}; }} .ps-kpi.amber {{ box-shadow: inset 4px 0 0 {AMBER}; }}
.ps-kpi.teal {{ box-shadow: inset 4px 0 0 {TEAL}; }}

/* who / job / decision */
.ps-who {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); background: {TEAL_SOFT};
          border-radius: 12px; margin: 0 0 10px 0; }}
.ps-who > div {{ padding: 16px 20px; }}
.ps-who b {{ display: block; color: {TEAL}; font-size: 0.88rem; font-weight: 600; margin-bottom: 4px; }}
.ps-who span {{ color: {INK}; font-size: 1rem; line-height: 1.45; }}

/* how-to steps (a real sequence) */
.ps-steps {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 0 0 18px 0; }}
.ps-steps > div {{ display: flex; gap: 10px; align-items: flex-start; color: {TEXT}; font-size: 0.95rem; line-height: 1.4; }}
.ps-steps .k {{ flex: none; width: 26px; height: 26px; border-radius: 50%; background: {INK}; color: #FFF;
               font-size: 0.85rem; font-weight: 600; display: flex; align-items: center; justify-content: center; }}

/* recall class legend */
.ps-classes {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; margin: 4px 0 12px 0; }}
.ps-classes > div {{ border-radius: 10px; padding: 10px 14px; font-size: 0.9rem; line-height: 1.4; color: {TEXT}; background: #FFFFFF;
                    border: 1px solid {LINE}; }}
.ps-classes b {{ display: inline-block; border-radius: 6px; padding: 1px 8px; margin-right: 6px; font-weight: 600; font-size: 0.82rem; }}

/* status chips */
.ps-chip {{ display: inline-block; border-radius: 999px; padding: 3px 11px; font-size: 0.82rem; font-weight: 600; white-space: nowrap; }}
.ps-chip.coral {{ background: {CORAL_SOFT}; color: {CORAL}; }} .ps-chip.amber {{ background: {AMBER_SOFT}; color: #9A5B07; }}
.ps-chip.teal {{ background: {TEAL_SOFT}; color: {TEAL}; }} .ps-chip.grey {{ background: #EEF2F6; color: {SLATE}; }}

/* bidder result cards */
.ps-bid {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 12px; padding: 16px 18px; margin: 0 0 4px 0; }}
.ps-bid .top {{ display: flex; justify-content: space-between; gap: 10px; align-items: center; flex-wrap: wrap; }}
.ps-bid .name {{ font-size: 1.08rem; font-weight: 600; color: {INK}; }}
.ps-bid .match {{ color: {SLATE}; font-size: 0.85rem; margin-top: 2px; }}
.ps-bid .flags {{ margin-top: 8px; font-size: 0.9rem; color: {TEXT}; }}
.ps-bid .nums {{ display: flex; gap: 26px; flex-wrap: wrap; margin: 12px 0 8px 0; }}
.ps-bid .nums div {{ font-size: 0.82rem; color: {SLATE}; }}
.ps-bid .nums b {{ display: block; font-size: 1.3rem; color: {INK}; font-weight: 600; }}
.ps-bid .next {{ font-size: 0.93rem; color: {TEXT}; border-top: 1px solid #EEF2F6; padding-top: 9px; }}

/* signal cards */
.ps-sigs {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; margin: 4px 0 10px 0; }}
.ps-sig {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 12px; padding: 14px 16px; }}
.ps-sig .top {{ display: flex; justify-content: space-between; gap: 8px; align-items: flex-start; }}
.ps-sig .name {{ font-weight: 600; color: {INK}; font-size: 1.02rem; }}
.ps-sig .meta {{ color: {SLATE}; font-size: 0.84rem; margin-top: 1px; }}
.ps-sig .body {{ color: {TEXT}; font-size: 0.93rem; line-height: 1.45; margin-top: 8px; }}
.ps-sig .bar {{ height: 6px; border-radius: 3px; background: #EEF2F6; margin-top: 10px; overflow: hidden; }}
.ps-sig .bar span {{ display: block; height: 100%; background: {AMBER}; border-radius: 3px; }}

/* evidence cards in the assistant */
.ps-evs {{ display: grid; gap: 8px; margin: 4px 0 6px 0; }}
.ps-ev {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 10px; padding: 10px 14px; font-size: 0.9rem;
         line-height: 1.45; color: {TEXT}; }}
.ps-ev code {{ background: {TEAL_SOFT}; color: {TEAL}; border-radius: 6px; padding: 1px 7px; font-size: 0.8rem; margin-right: 6px; }}

/* callouts */
.ps-note {{ border-radius: 10px; padding: 12px 16px; margin: 8px 0 14px 0; line-height: 1.5; font-size: 0.95rem; }}
.ps-note.info {{ background: {TEAL_SOFT}; color: {INK}; }}
.ps-note.warn {{ background: {AMBER_SOFT}; color: #6B4205; }}
.ps-note.limit {{ background: #EEF2F6; color: {TEXT}; }}
.ps-note b {{ font-weight: 600; }}

/* buttons and links */
.stMain [data-testid="stPageLink"] a {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 10px; padding: 12px 14px;
  justify-content: center; }}
.stMain [data-testid="stPageLink"] a:hover {{ border-color: {TEAL}; background: {TEAL_SOFT}; }}
.stMain [data-testid="stPageLink"] a p {{ font-weight: 600; color: {INK}; }}

/* sidebar */
[data-testid="stSidebar"] .ps-side {{ font-size: 0.84rem; color: #BCCCDC; line-height: 1.55; }}
[data-testid="stSidebar"] .ps-side b {{ color: #FFFFFF; font-weight: 600; }}
[data-testid="stSidebar"] .ps-side .dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }}
.ps-foot {{ color: {SLATE}; font-size: 0.8rem; border-top: 1px solid {LINE}; margin-top: 36px; padding-top: 12px; }}
</style>
"""


def apply_style():
    st.markdown(CSS, unsafe_allow_html=True)


def esc(text):
    return html.escape(str(text))


def _html(markup):
    st.markdown(markup, unsafe_allow_html=True)


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
            f'<polygon points="0,{height} {pts} {width},{height}" fill="rgba(15,118,110,0.35)"/>'
            f'<polyline points="{pts}" fill="none" stroke="{TEAL_LIGHT}" stroke-width="1.8" vector-effect="non-scaling-stroke"/>'
            f'<circle cx="{x[peak]:.1f}" cy="{y[peak]:.1f}" r="5" fill="{AMBER}" stroke="{INK}" stroke-width="2"/></svg>')


def hero(kicker, title, text, spark_values=None, spark_note=""):
    spark = sparkline_svg(spark_values) if spark_values is not None else ""
    note = f'<div class="note">{esc(spark_note)}</div>' if spark_note else '<div style="height:28px"></div>'
    _html(f'<div class="ps-hero"><div class="kicker">{esc(kicker)}</div><h1>{esc(title)}</h1><p>{esc(text)}</p>{spark}{note}</div>')


def page_header(title, text):
    _html(f'<div class="ps-head"><h1>{esc(title)}</h1><p>{esc(text)}</p></div>')


def section(title, text=None):
    st.header(title, anchor=False)
    if text:
        _html(f'<p class="ps-sub">{esc(text)}</p>')


def findings(items):
    """items: list of (big value, sentence, tone) where tone is '', 'coral', 'amber' or 'ink'."""
    _html('<div class="ps-find">' + "".join(f'<div><div class="n {t}">{esc(n)}</div><div class="t">{esc(s)}</div></div>'
                                            for n, s, t in items) + "</div>")


def kpis(items):
    """items: list of (value, label, tone) where tone is '', 'coral', 'amber' or 'teal'."""
    _html('<div class="ps-kpis">' + "".join(f'<div class="ps-kpi {t}"><div class="v">{esc(v)}</div><div class="l">{esc(l)}</div></div>'
                                            for v, l, t in items) + "</div>")


def steps(items):
    _html('<div class="ps-steps">' + "".join(f'<div><span class="k">{i}</span><span>{esc(s)}</span></div>'
                                             for i, s in enumerate(items, 1)) + "</div>")


def who_strip(user, job, decision):
    _html(f'<div class="ps-who"><div><b>Who it is for</b><span>{esc(user)}</span></div>'
          f'<div><b>Their job</b><span>{esc(job)}</span></div>'
          f'<div><b>The decision it supports</b><span>{esc(decision)}</span></div></div>')


def class_legend():
    fills = {"Class I": (CORAL_SOFT, CORAL), "Class II": (AMBER_SOFT, "#9A5B07"), "Class III": ("#EEF2F6", SLATE)}
    _html('<div class="ps-classes">' + "".join(
        f'<div><b style="background:{bg};color:{fg}">{c}</b>{esc(CLASS_TEXT[c])}</div>' for c, (bg, fg) in fills.items()) + "</div>")


def chip(text, tone):
    return f'<span class="ps-chip {tone}">{esc(text)}</span>'


def bidder_card(name, match_text, flags_text, status_text, tone, numbers, next_step):
    nums = "".join(f'<div><b>{esc(v)}</b>{esc(k)}</div>' for k, v in numbers)
    flags = f'<div class="flags">{esc(flags_text)}</div>' if flags_text else ""
    _html(f'<div class="ps-bid"><div class="top"><div><div class="name">{esc(name)}</div>'
          f'<div class="match">{esc(match_text)}</div></div>{chip(status_text, tone)}</div>{flags}'
          f'<div class="nums">{nums}</div><div class="next"><b>Next step:</b> {esc(next_step)}</div></div>')


def note(text, kind="info"):
    _html(f'<div class="ps-note {kind}">{text}</div>')


def footer(source):
    _html(f'<div class="ps-foot">Data: {esc(source)}. PharmaSignal is decision support: it gives evidence for people to weigh '
          'and never a verdict on a medicine or supplier.</div>')


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
