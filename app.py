"""PharmaSignal - Streamlit app.

Run the notebook once (it creates outputs/), then:   streamlit run app.py
"""
import os
import re
from datetime import datetime, timezone

import altair as alt
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import streamlit as st

import pharmasignal_core as core
import ui

st.set_page_config(page_title="PharmaSignal", page_icon=":material/monitor_heart:", layout="wide", initial_sidebar_state="auto")
ui.set_mode("light")   # one consistent look: white background, navy sidebar
ui.apply_style()
st.logo(str(core.ROOT / "assets" / ("logo.svg" if ui.MODE == "dark" else "logo_light.svg")), size="large",
        icon_image=str(core.ROOT / "assets" / "icon.svg"))



def secret(name, default=None):
    """Streamlit secrets when deployed, otherwise .env / environment variable. Keys are never stored in the code."""
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    return value or os.getenv(name) or default


ANTHROPIC_API_KEY = secret("ANTHROPIC_API_KEY")
core.LLM_MODEL = secret("LLM_MODEL", core.LLM_MODEL)
DAILY_LIMIT = int(secret("DAILY_QUESTION_LIMIT", 150))    # written answers per day for the whole app (protects credit)
SESSION_LIMIT = int(secret("SESSION_QUESTION_LIMIT", 25))  # written answers per visitor session

missing = core.missing_outputs()
if missing:
    ui.page_header("PharmaSignal needs the notebook's results first",
                   "The app reads the files the analysis notebook writes to the outputs folder, and some are missing.")
    st.error("Missing: " + ", ".join(missing))
    st.markdown("Open **Drug_Recall_Intelligence_Final.ipynb**, choose **Restart & Run All**, then refresh this page.")
    st.stop()


@st.cache_resource(show_spinner="Loading recall data and building the search index...")
def get_data():
    return core.load_data()


@st.cache_resource
def get_llm(api_key):
    # cached per key, so adding or changing the key in Secrets takes effect without a stale "no key" result
    return core.make_llm(api_key=api_key)


@st.cache_resource
def usage_counter():
    return {"day": None, "n": 0}


def llm_allowed():
    """True while today's app-wide and this visitor's limits on written answers have not been reached."""
    u = usage_counter()
    today = datetime.now(timezone.utc).date()
    if u["day"] != today:
        u["day"], u["n"] = today, 0
    return u["n"] < DAILY_LIMIT and st.session_state.get("llm_used", 0) < SESSION_LIMIT


def count_llm_use():
    usage_counter()["n"] += 1
    st.session_state.llm_used = st.session_state.get("llm_used", 0) + 1


d = get_data()
llm = get_llm(ANTHROPIC_API_KEY)
EVENTS = d.recalls.drop_duplicates("event_id")
CATEGORY_NAMES = {"IMPURITIES": "Impurities", "CONTAMINATION_STERILITY": "Contamination or sterility",
                  "CGMP_DEVIATION": "GMP deviation", "LABELING_PACKAGING": "Labelling or packaging",
                  "POTENCY_STRENGTH": "Potency or strength", "DISSOLUTION": "Dissolution",
                  "FOREIGN_MATTER": "Foreign matter", "STABILITY": "Stability",
                  "UNAPPROVED_UNDECLARED": "Unapproved or undeclared ingredient", "OTHER": "Other",
                  "UNCERTAIN_REVIEW": "Uncertain, sent to human review"}
nice_cat = lambda c: CATEGORY_NAMES.get(c, str(c).replace("_", " ").capitalize())


ACRONYMS = {"usa", "us", "llc", "inc", "uk", "na", "lp", "ag", "plc", "ltd"}


def firm_title(name):
    return " ".join(w.upper() if w.lower() in ACRONYMS else w.capitalize() for w in str(name).split())


def nice_flags(text):
    if not text or text in ("none", "no FDA record"):
        return ""
    return re.sub(r"\b[A-Z][A-Z_]{3,}\b", lambda m: nice_cat(m.group(0)).lower(), str(text))


def month_label(m):
    return pd.Period(str(m), "M").strftime("%b %Y")


def friendly_error(action, err):
    st.error(f"{action} did not complete ({type(err).__name__}). Check the inputs and try again; "
             "if it keeps happening, re-run the notebook so the outputs folder is up to date.")


# ============================================================ Home
def home():
    by_month = EVENTS.dropna(subset=["report_date_dt"]).set_index("report_date_dt").resample("MS").event_id.nunique()
    peak_month, peak_n = by_month.idxmax(), int(by_month.max())
    ui.hero("PharmaSignal AI: recall intelligence for medicines procurement",
            "Check a supplier's recall record before you award the tender",
            "An AI-powered assistant built on fourteen years of US FDA drug-quality recalls. It sorts recall reasons with "
            "machine learning, spots unusual surges, and answers your questions with evidence you can check.",
            by_month.values,
            f"Monthly FDA drug-quality recall events, {by_month.index.min():%b %Y} to {by_month.index.max():%b %Y}. "
            f"Busiest month (amber): {peak_month:%b %Y}, {peak_n} events.")
    ui.who_strip("Pharmacists and procurement officers in hospitals, supply agencies and distributors",
                 "Screen the firms and products bidding for a medicines tender",
                 "Proceed with a bidder, or ask for more documents before award")

    ui.section("Where would you like to start?")
    st.markdown('<p class="ps-infolabel">Click any card to open that page.</p>', unsafe_allow_html=True)
    links = [(findings_pg, "At a Glance", ":material/insights:"), (failures_pg, "Failure Patterns", ":material/science:"),
             (firms_pg, "Firm Directory", ":material/factory:"), (latest_pg, "Signal Radar", ":material/radar:"),
             (tender_pg, "Tender Screener", ":material/fact_check:"), (ask_pg, "Ask PharmaSignal AI", ":material/smart_toy:")]
    for row in (links[:3], links[3:]):
        cols = st.columns(3)
        for c, (page, label, icon) in zip(cols, row):
            c.page_link(page, label=label, icon=icon, width="stretch")

    ui.section("Meet the PharmaSignal AI assistant",
               "Three kinds of AI work together: a machine-learning classifier, anomaly detectors and a language model.")
    ui.ai_band("Ask in plain English, get answers you can check",
               "The assistant looks up the facts with database queries, finds the closest recall records, and asks Claude "
               "to explain them. Code then checks every number and recall ID before you see the answer. It never "
               "calls a medicine unsafe or tells you to reject a supplier.",
               "Has Teva Pharmaceuticals USA had Class I recalls?",
               "Facts from the data: 158 recall events, 6 of them Class I, each cited by its recall number. "
               "What this may mean, and the checks to make before award, follow underneath.")
    ui.footer(d.source)


# ============================================================ Explore the data
ALL_CLASSES = ["Class I", "Class II", "Class III"]


def record_filter(key):
    """Year and class filter shown at the top of an explore page; returns (records, one row per event)."""
    years = sorted(int(y) for y in d.recalls.year.dropna().unique())
    with st.expander("Filter by year or recall class", icon=":material/tune:"):
        f1, f2 = st.columns([2, 1])
        yr = f1.slider("Publication year", years[0], years[-1], (years[0], years[-1]), key=f"{key}_yr")
        classes = f2.multiselect("Recall class", ALL_CLASSES, default=ALL_CLASSES, key=f"{key}_cls")
    f = d.recalls[d.recalls.year.between(*yr) & (d.recalls.classification.isin(classes)
                                                 | ~d.recalls.classification.isin(ALL_CLASSES))]
    return f, f.drop_duplicates("event_id"), classes


def key_findings():
    n_ev = EVENTS.event_id.nunique()
    ui.page_header("At a Glance", icon="insights", text=
                   f"The four things to remember from {n_ev:,} FDA drug-quality recall events, "
                   f"{d.provenance['report_date_range'][0][:4]} to {d.provenance['report_date_range'][1][:4]}.")
    share_i = (EVENTS.classification == "Class I").mean()
    cats = EVENTS.analysis_category.value_counts(normalize=True)
    forms = EVENTS.product_group.value_counts(normalize=True)
    per_firm = EVENTS.groupby("firm_std").event_id.nunique()
    top3 = [nice_cat(c).lower() for c in cats.index[:3]]
    ui.findings([
        (f"1 in {round(1 / share_i)}", "recall events is Class I: a reasonable chance of serious harm or death.", "coral"),
        (f"{cats.iloc[:3].sum() * 100:.0f}%", f"of recalls come from three failure types: {top3[0]}, {top3[1]} and {top3[2]}.", "teal"),
        (f"{forms.iloc[0] * 100:.0f}%", f"involve {forms.index[0].lower()} products such as tablets and capsules; "
                                        f"{forms.index[1].lower()} products are next at {forms.iloc[1] * 100:.0f}%.", "blue"),
        (f"{(per_firm > 1).mean() * 100:.0f}%", "of recalling firms recalled more than once. Repeat recallers are where "
                                                "a buyer's questions should start.", "amber")])

    ui.section("How serious were the recalls, year by year?",
               "The FDA grades every recall by how much harm the problem could cause.")
    ui.class_legend()
    per_year = EVENTS[EVENTS.classification.isin(ALL_CLASSES)].groupby(["year", "classification"]).size().reset_index(name="events")
    st.subheader("Class II recalls dominate every year; Class I is the smaller, most serious share")
    ui.chart(alt.Chart(per_year).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("events:Q", title="Recall events"),
        color=alt.Color("classification:N", title=None, scale=ui.CLASS_COLOURS),
        order=alt.Order("classification:N", sort="ascending"),
        tooltip=["year", "classification", "events"]), 320)
    ui.footer(d.source)


def what_goes_wrong():
    ui.page_header("Failure Patterns", icon="science", text=
                   "Which quality failures cause recalls, and which kinds of products are affected most. "
                   "Every recall reason was sorted into a failure type by the machine-learning classifier.")
    f, ev, _ = record_filter("wgw")
    a, b = st.columns(2, gap="large")
    with a:
        c = ev.analysis_category.map(nice_cat).value_counts().rename_axis("failure").reset_index(name="events")
        st.subheader(f"{c.failure.iloc[0]} and {c.failure.iloc[1].lower()} lead")
        ui.ranked_bars(c, "events", "failure", highlight=2, height=360)
    with b:
        g = ev.product_group.value_counts().rename_axis("dosage form").reset_index(name="events")
        st.subheader(f"{g['dosage form'].iloc[0]} and {g['dosage form'].iloc[1].lower()} products lead")
        ui.ranked_bars(g, "events", "dosage form", highlight=2, colour=ui.BLUE, height=360)
    ui.tip("<b>Reading the charts:</b> the two largest groups are coloured; the rest are grey. Counts are recall events "
           "(one recall decision), not individual products.")
    ui.footer(d.source)


def firms_and_records():
    ui.page_header("Firm Directory", icon="factory", text=
                   "Which firms recall most often, what usually goes wrong for them, and a search across every recall record.")
    f, ev, _ = record_filter("firms")
    st.subheader("The ten firms with the most recall events")
    g = ev.groupby("firm_std")
    top = (g.agg(events=("event_id", "nunique"), class_I=("classification", lambda s: int((s == "Class I").sum())),
                 latest=("report_date_dt", "max"))
           .sort_values("events", ascending=False).head(10))
    main_fail = ev[ev.firm_std.isin(top.index)].groupby("firm_std").analysis_category.agg(lambda s: s.value_counts().index[0])
    mx = int(top.events.max())
    rows = []
    for k, (firm, r) in enumerate(top.iterrows(), 1):
        share = r.class_I / r.events if r.events else 0
        rows.append([f'<span class="rank">{k}</span>',
                     f'<b>{ui.esc(firm_title(firm))}</b><span class="sub">Most common failure: {ui.esc(nice_cat(main_fail.get(firm, "")).lower())}</span>',
                     ui.bar_cell(int(r.events), mx),
                     ui.chip(f"{int(r.class_I)} Class I", "coral" if r.class_I else "grey"),
                     f"{share:.0%}", f"{r.latest:%b %Y}" if r.latest == r.latest else "-"])
    ui.table(["#", "Recalling firm", "Recall events", "Most serious", "Class I share", "Latest recall"], rows, numeric=(4,))
    ui.tip("The recalling firm announced the recall. It may be a distributor or repackager rather than the manufacturer, "
           "so treat a name as the start of a question, not a conclusion.")

    ui.section("Search recall records", "Type a product, firm or reason to see every matching recall.")
    q = st.text_input("Search", placeholder="e.g. metformin, benzene, Teva", label_visibility="collapsed")
    if q:
        hit = f[f.product_description.str.contains(q, case=False, na=False, regex=False)
                | f.recalling_firm.str.contains(q, case=False, na=False, regex=False)
                | f.reason_clean.str.contains(q, case=False, na=False, regex=False)]
        st.caption(f"{len(hit):,} records match; showing the newest 500.")
        out = hit.sort_values("report_date", ascending=False)[
            ["report_date", "recall_number", "classification", "recalling_firm", "analysis_category", "product_group",
             "reason_clean", "product_description"]].head(500).copy()
        out["analysis_category"] = out.analysis_category.map(nice_cat)
        st.dataframe(out, hide_index=True, width="stretch", column_config={
            "report_date": st.column_config.TextColumn("Published", width="small"),
            "recall_number": st.column_config.TextColumn("Recall no.", width="small"),
            "classification": st.column_config.TextColumn("Class", width="small"),
            "recalling_firm": st.column_config.TextColumn("Firm", width="medium"),
            "analysis_category": st.column_config.TextColumn("Failure type", width="medium"),
            "product_group": st.column_config.TextColumn("Dosage form", width="small"),
            "reason_clean": st.column_config.TextColumn("Reason", width="large"),
            "product_description": st.column_config.TextColumn("Product", width="large")})
        st.download_button("Download these records (CSV)", out.to_csv(index=False), "recall_search.csv", "text/csv",
                           icon=":material/download:")
    ui.footer(d.source)


# ============================================================ Recall signals
def latest_signals():
    ui.page_header("Signal Radar", icon="radar", text=
                   "A signal means a month had clearly more recall events than usual for a failure type, dosage form or firm. "
                   "It is a prompt to look closer, not a confirmed quality failure.")
    al = d.alerts.copy()
    al["strength"] = al.n_methods.map(ui.strength_label)
    with st.sidebar:
        st.markdown('<div class="ps-sidehead">Signal filters</div>', unsafe_allow_html=True)
        window = st.select_slider("Reporting period", ["3 months", "6 months", "12 months", "24 months", "All history"],
                                  value="12 months")
        kinds = st.multiselect("Watch", ["category", "product_group", "firm"], default=["category", "product_group", "firm"],
                               format_func={"category": "Failure types", "product_group": "Dosage forms", "firm": "Firms"}.get)
        strengths = st.multiselect("Signal strength", ["Strong", "Moderate", "Low"], default=["Strong", "Moderate", "Low"],
                                   help=ui.STRENGTH_HELP)
        st.divider()
    if window != "All history":
        al = al[al.month > str(d.last_month - int(window.split()[0]))]
    al = al[al.series_type.isin(kinds) & al.strength.isin(strengths)].sort_values(["month", "n_methods"], ascending=False)

    top = al[al.n_methods >= 2].head(1)
    if len(top):
        t = top.iloc[0]
        label = nice_cat(t.series_name) if t.series_type == "category" else firm_title(t.series_name)
        what = {"category": "failure type", "product_group": "dosage form", "firm": "firm"}[t.series_type]
        ui.note(f"<b>Most recent {t.strength.lower()} signal:</b> {ui.esc(label)} ({what}) in {month_label(t.month)}, with "
                f"{int(t.n_events)} recall events against a usual {t.hist_mean:.1f} a month.", "warn")
    ui.kpis([(f"{len(al)}", "signals detected in this view", "blue"),
             (f"{int((al.strength == 'Strong').sum())}", "strong signals: all three methods agree", "coral"),
             (f"{int((al.strength == 'Moderate').sum())}", "moderate signals: two methods agree", "amber"),
             (f"{int(al.n_events.sum()):,}", "recall events in the flagged months", "")])
    if al.empty:
        ui.tip("No signals match these filters. Widen the reporting period or include more strength levels in the sidebar.")
        ui.footer(d.source)
        return

    al["name"] = [nice_cat(n) if t == "category" else firm_title(n) for t, n in zip(al.series_type, al.series_name)]
    al["kind"] = al.series_type.map({"category": "Failure type", "product_group": "Dosage form", "firm": "Firm"})
    al["flagged_by"] = al.why_flagged.str.extract(r"flagged by ([^;]+)")[0].str.replace("zscore", "z-score").fillna("the detectors")
    al["month_label"] = al.month.map(month_label)

    # ---- dumbbell chart: usual level vs this month
    ui.section("How big was each jump?",
               "Each row is one signal. The grey dot is the usual monthly level; the coloured dot is what happened that month. "
               "The longer the line, the bigger the jump.")
    show = al.head(12).iloc[::-1]
    labels = [f"{n}  ({m})" for n, m in zip(show.name, show.month_label)]
    colours = ui.strength_colours()
    fig = go.Figure()
    for y, r in zip(labels, show.itertuples()):
        fig.add_trace(go.Scatter(x=[r.hist_mean, r.n_events], y=[y, y], mode="lines", showlegend=False, hoverinfo="skip",
                                 line=dict(color=ui.MIST, width=4)))
    fig.add_trace(go.Scatter(x=show.hist_mean, y=labels, mode="markers", name="Usual level",
                             marker=dict(size=13, color=ui.P["CARD_SOLID"], line=dict(color=ui.MUTED, width=2.5)),
                             hovertemplate="%{y}<br>Usual: %{x:.1f} a month<extra></extra>"))
    for level, colour in colours.items():
        m = show.strength == level
        if m.any():
            fig.add_trace(go.Scatter(x=show.n_events[m], y=[l for l, k in zip(labels, m) if k], mode="markers",
                                     name=f"{level} signal", marker=dict(size=16, color=colour, line=dict(color="#FFFFFF", width=1.5)),
                                     hovertemplate="%{y}<br>This month: %{x} events<extra></extra>"))
    fig.update_xaxes(title_text="Recall events in the month", rangemode="tozero")
    fig.update_yaxes(title_text="", tickfont=dict(size=12.5, color=ui.P["TEXT"]))
    ui.plotly_chart(fig, max(320, 34 * len(show) + 110))

    # ---- compact table
    ui.section("Signals at a glance", "Newest first. Open the full list below to sort, search or download.")
    rows = [[f"<b>{ui.esc(r.month_label)}</b>",
             f'<b>{ui.esc(r.name)}</b><span class="sub">{ui.esc(r.kind)}, flagged by {ui.esc(r.flagged_by)}</span>',
             f"<b>{int(r.n_events)}</b> vs {r.hist_mean:.1f}", ui.chip(r.strength, ui.STRENGTH[min(max(int(r.n_methods), 1), 3)][1])]
            for r in al.head(8).itertuples()]
    ui.table(["Month", "Signal", "Events vs usual", "Strength"], rows, numeric=(2,))
    with st.expander(f"Sort, search and download all {len(al)} signals", icon=":material/table_view:"):
        al["times"] = al.n_events / np.maximum(al.hist_mean, 0.5)
        al["class_i"] = al.why_flagged.str.extract(r"(\d+)% of records Class I")[0].astype(float)
        out = al[["month_label", "kind", "name", "n_events", "hist_mean", "times", "flagged_by", "class_i", "strength"]]
        st.caption("Click a column heading to sort. Hover over the table and use the magnifying glass to search.")
        st.dataframe(out, hide_index=True, width="stretch", column_config={
            "month_label": "Month", "kind": "Watching", "name": "Name", "n_events": "Events",
            "hist_mean": st.column_config.NumberColumn("Usual per month", format="%.1f"),
            "times": st.column_config.NumberColumn("× usual", format="%.1f"),
            "flagged_by": "Flagged by", "class_i": st.column_config.NumberColumn("Class I share", format="%d%%"),
            "strength": "Strength"})
        st.download_button("Download signals (CSV)", out.to_csv(index=False), "pharmasignal_signals.csv", "text/csv",
                           icon=":material/download:", type="primary")

    ui.section("How a signal is detected", "Three independent methods check every month against the previous 12 months.")
    ui.explainers([
        ("straighten", "Z-score", "How far this month sits above the 12-month average, in standard deviations. Flags at 3 or more.", ""),
        ("data_thresholding", "IQR fence", "Above the normal range of the last 12 months (Q3 + 1.5 × IQR). Earlier spikes do not distort "
                           "it, so it caught the most past crises.", "blue"),
        ("account_tree", "Isolation Forest", "A machine-learning check of seven features together, such as event count, Class I "
                                  "share and the number of firms involved.", "amber")])
    ui.tip("Every method needs at least 3 events in the month and more than the 12-month average. "
           "<b>Strong</b> = all three agree, <b>Moderate</b> = two, <b>Low</b> = one.")
    ui.footer(d.source)


def signal_trends():
    ui.page_header("Trend Explorer", icon="grid_view", text=
                   "How each kind of quality failure has risen and fallen over time, and how strict the signal rules should be.")
    q = EVENTS.dropna(subset=["report_date_dt"]).copy()
    q["failure"] = q.analysis_category.map(nice_cat)
    q["year"] = q.report_date_dt.dt.year
    heat = q.groupby(["failure", "year"]).event_id.nunique().unstack(fill_value=0)
    heat = heat.loc[heat.sum(1).sort_values(ascending=True).index]
    ui.section("Recall events per year, by failure type",
               "Darker squares mean more recalls. Read across a row to see one failure type over time, or down a column "
               "to compare failure types in one year.")
    years = [str(y) for y in heat.columns]
    fig = go.Figure(go.Heatmap(
        z=heat.values, x=years, y=list(heat.index), text=heat.values, texttemplate="%{text}",
        textfont=dict(size=11), colorscale=[[0, "#F1F5F8"], [0.35, "#9ED9CB"], [1, ui.TEAL]], xgap=3, ygap=3,
        hovertemplate="<b>%{y}</b><br>%{x}: %{z} recall events<extra></extra>",
        colorbar=dict(title=dict(text="Events", side="top"), thickness=12, outlinewidth=0)))
    fig.update_xaxes(side="top", showgrid=False, tickfont=dict(size=12))
    fig.update_yaxes(showgrid=False, tickfont=dict(size=12.5, color=ui.P["TEXT"]))
    ui.plotly_chart(fig, 38 * len(heat) + 110)
    peak = heat.stack().idxmax()
    ui.tip(f"<b>Biggest single cell:</b> {ui.esc(peak[0].lower())} in {peak[1]}, with {int(heat.stack().max())} recall events.")

    ms = d.monthly.copy()
    ui.section("Try a different sensitivity",
               "Stricter settings mean fewer alerts to review but more problems missed. Move the sliders to see the trade-off.")
    s1, s2, s3 = st.columns(3)
    z = s1.slider("Z-score threshold", 2.0, 4.0, 3.0, 0.5)
    k = s2.slider("IQR fence multiplier", 1.0, 3.0, 1.5, 0.5)
    min_ev = s3.slider("Minimum events in a month", 2, 5, 3)
    surge = (ms.n_events >= min_ev) & (ms.n_events > ms.hist_mean)
    ms["z_new"] = surge & ((ms.n_events - ms.hist_mean) / np.maximum(ms.hist_std, 1.0) >= z)
    ms["iqr_new"] = surge & (ms.n_events > ms.hist_q3 + k * (ms.hist_q3 - ms.hist_q1))
    wl = ms[ms.series_type != "firm"]
    n_months = wl.month.nunique()
    base = (wl.flag_zscore.sum() / n_months, wl.flag_iqr.sum() / n_months)
    new = (wl.z_new.sum() / n_months, wl.iqr_new.sum() / n_months)
    change = lambda n, o: "same as the project setting" if abs(n - o) < 0.005 else f"{n - o:+.2f} vs the project setting"
    ui.kpis([(f"{new[0]:.2f}", f"Z-score alerts per month ({change(new[0], base[0])})", "teal"),
             (f"{new[1]:.2f}", f"IQR alerts per month ({change(new[1], base[1])})", "blue")])
    options = ms[ms.series_type != "firm"][["series_type", "series_name"]].drop_duplicates().apply(tuple, axis=1).tolist()
    default = options.index(("category", "IMPURITIES")) if ("category", "IMPURITIES") in options else 0
    pick = st.selectbox("Show the month-by-month trend for", options, index=default,
                        format_func=lambda t: nice_cat(t[1]) if t[0] == "category" else f"{t[1]} (dosage form)")
    s = ms[(ms.series_type == pick[0]) & (ms.series_name == pick[1])].copy()
    s["date"] = pd.to_datetime(s.month)
    s["signal"] = s.z_new | s.iqr_new
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.date, y=s.n_events, name="Recall events", mode="lines", line=dict(color=ui.TEAL, width=2),
                             fill="tozeroy", fillcolor="rgba(15,118,110,0.10)",
                             hovertemplate="%{x|%b %Y}: %{y} events<extra></extra>"))
    fig.add_trace(go.Scatter(x=s.date, y=s.hist_mean, name="Usual level (12-month average)", mode="lines",
                             line=dict(color=ui.MUTED, width=1.6, dash="dash"), hovertemplate="Usual: %{y:.1f}<extra></extra>"))
    sig = s[s.signal]
    fig.add_trace(go.Scatter(x=sig.date, y=sig.n_events, name="Signal at your settings", mode="markers",
                             marker=dict(size=11, color=ui.AMBER, line=dict(color="#FFFFFF", width=1.5)),
                             hovertemplate="Signal: %{x|%b %Y}, %{y} events<extra></extra>"))
    fig.update_yaxes(title_text="Recall events per month", rangemode="tozero")
    ui.plotly_chart(fig, 360)
    ui.footer(d.source)


def backtest_page():
    ui.page_header("Crisis Back-test", icon="history", text=
                   "Would PharmaSignal have recognised real recall crises? We replayed six known events using only the data "
                   "available at the time.")
    if len(d.method_summary):
        st.subheader("Crises detected and alert workload, by method")
        names = {"iqr": "IQR fence", "zscore": "Z-score", "iforest": "Isolation Forest", "consensus": "Consensus (2+ agree)"}
        rows = []
        for r in d.method_summary.itertuples():
            best = r.method == "iqr"
            rows.append([f"<b>{ui.esc(names.get(r.method, r.method))}</b>" + (' ' + ui.chip("Best", "teal") if best else ""),
                         ui.bar_cell(int(r.events_detected), 6) + f'<span class="sub">{int(r.events_detected)} of 6 crises</span>',
                         f"{r.watch_alerts_per_month:.2f}", f"{r.median_lead_vs_public:+.0f}"])
        ui.table(["Method", "Crises detected", "Alerts per month", "Months vs public news"], rows, numeric=(2, 3))
        ui.explainers([
            ("task_alt", "What worked", "The IQR fence recognised 4 of 6 crises (sartans, ranitidine, metformin, methanol) at under "
                                 "one alert a month.", "green"),
            ("schedule", "Timing", "Signals arrived in the crisis peak month, about 2 months after the news, because the FDA "
                            "publishes recalls weeks after they start. PharmaSignal recognises clusters; it does not predict them.",
             "amber"),
            ("trending_flat", "What it missed", "Slow-building problems such as benzene in sprays and contaminated eye drops never "
                                    "produced a sharp monthly spike.", "coral")])
    figs = core.OUT / "figures"
    if (figs / "backtests.png").exists():
        ui.section("The six crises, month by month")
        st.image(str(figs / "backtests.png"), width="stretch")
    ui.footer(d.source)


# ============================================================ Tender screening
EXAMPLE_BIDDERS = "Sun Pharmaceutical Industries\nLupin Pharmaceuticals\nMarksans Pharma\nExample Generics Ltd"


def fill_example():
    st.session_state.bidders_text = EXAMPLE_BIDDERS
    st.session_state.product = "metformin"


def read_bidder_upload(file):
    """Accepts a CSV or Excel list; uses a column called bidder/firm/supplier/name, otherwise the first column."""
    try:
        df = pd.read_excel(file) if file.name.lower().endswith((".xlsx", ".xls")) else pd.read_csv(file)
    except Exception:
        return None, "The file could not be read. Upload a CSV or Excel file with one bidder name per row."
    if df.empty:
        return None, "The file has no rows. Add one bidder name per row."
    col = next((c for c in df.columns if str(c).strip().lower() in {"bidder", "firm", "supplier", "company", "name"}),
               df.columns[0])
    names = [str(n).strip() for n in df[col].dropna() if str(n).strip()]
    if not names:
        return None, f"The column '{col}' is empty. Put the bidder names in a column called 'bidder'."
    return names[:50], None


def bidder_status(row):
    if row.matched_firm == "-":
        return ("No FDA recall record", "grey",
                "Check registration with the national medicines regulator and GMP evidence as usual. No FDA record is not proof of good quality.")
    if row.class_I_12m > 0:
        return ("Recent Class I recall", "coral",
                "Ask for the root-cause investigation and corrective actions, plus the documents in the brief.")
    if row["flags"] not in ("none", "", None):
        return ("Evidence to discuss", "amber", "Raise the flagged issues with the bidder and request the documents in the brief.")
    return ("No recent flags", "teal", "Request the standard documents listed in the brief.")


def tender():
    ui.page_header("Tender Screener", icon="fact_check", text=
                   "See each bidder's FDA recall evidence side by side, with a checklist of documents to request before award.")
    ui.steps(["Add the bidders: type them, upload a list, or use the example", "Enter the product being tendered",
              "Screen, then download each bidder's evidence brief"])
    if "bidders_text" not in st.session_state:
        st.session_state.bidders_text = ""
    with st.container(border=True):
        left, right = st.columns([3, 2], gap="large")
        with left:
            tab_type, tab_upload = st.tabs([":material/edit: Type the names", ":material/upload_file: Upload a list"])
            with tab_type:
                st.text_area("Bidders, one per line", key="bidders_text", height=140,
                             placeholder="e.g. Sun Pharmaceutical Industries")
                st.button("Use example bidders", icon=":material/science:", on_click=fill_example)
            with tab_upload:
                up = st.file_uploader("CSV or Excel file, one bidder per row", type=["csv", "xlsx"],
                                      help="Uses a column called 'bidder' (or firm, supplier, name), otherwise the first column.")
                st.download_button("Download a template", "bidder\nSun Pharmaceutical Industries\nLupin Pharmaceuticals\n",
                                   "bidder_template.csv", "text/csv", icon=":material/download:")
        with right:
            product = st.text_input("Product being tendered", key="product", placeholder="e.g. metformin")
            run = st.button("Screen bidders", type="primary", icon=":material/fact_check:", width="stretch")
            ui.tip("No US FDA record is <b>not</b> evidence of good quality. The firm may not sell in the US or may "
                   "trade under another name.")

    bidders = [b.strip() for b in st.session_state.bidders_text.splitlines() if b.strip()]
    if up is not None:
        names, err = read_bidder_upload(up)
        if err:
            st.error(err)
        else:
            bidders = names
            st.caption(f"Using {len(names)} bidders from {up.name}.")
    if run:
        if not bidders:
            st.warning("Add at least one bidder name, upload a list, or use the example bidders.")
        elif not (product or "").strip():
            st.warning("Enter the product being tendered, for example 'metformin'.")
        else:
            try:
                with st.spinner("Matching bidders to FDA recall records..."):
                    st.session_state.tender = (core.tender_screen(d, bidders, product.strip()), product.strip())
            except Exception as e:
                friendly_error("Screening", e)

    if "tender" in st.session_state:
        (table, briefs), prod = st.session_state.tender
        prod_col = f"{prod}_recalls"
        statuses = [bidder_status(r) for _, r in table.iterrows()]
        tones = [s[1] for s in statuses]
        ui.section(f"Results: {len(table)} bidders for {prod}")
        ui.kpis([(f"{len(table)}", "bidders screened", "blue"),
                 (f"{tones.count('coral')}", "with a Class I recall in the last 12 months", "coral"),
                 (f"{tones.count('amber')}", "with other evidence to discuss", "amber"),
                 (f"{tones.count('grey')}", "with no FDA recall record", "")])
        order = {"coral": 0, "amber": 1, "teal": 2, "grey": 3}
        idx = sorted(range(len(table)), key=lambda i: order[tones[i]])
        mx = max(1, int(table.events_total.max()))
        rows = []
        for i in idx:
            r, (status, tone, _) = table.iloc[i], statuses[i]
            if r.matched_firm == "-":
                matched = "Not found in FDA records"
            elif firm_title(r.matched_firm).lower() == r.bidder.lower():
                matched = "Exact name match"
            else:
                matched = f"Matched to {firm_title(r.matched_firm)}"
            rows.append([f'<b>{ui.esc(r.bidder)}</b><span class="sub">{ui.esc(matched)}</span>', ui.chip(status, tone),
                         ui.bar_cell(int(r.events_total), mx), f"{int(r.events_12m)}",
                         ui.chip(f"{int(r.class_I_12m)}", "coral" if r.class_I_12m else "grey"), f"{int(r[prod_col])}"])
        ui.table(["Bidder", "Status", "All recall events", "Last 12 months", "Class I, 12 months", f"{prod.title()} recalls"],
                 rows, numeric=(3, 5))
        dl1, dl2 = st.columns(2)
        dl1.download_button("Download the summary (CSV)", table.to_csv(index=False), "tender_screening.csv",
                            "text/csv", width="stretch", icon=":material/download:", type="primary")
        dl2.download_button("Download all evidence briefs", "\n\n---\n\n".join(briefs.values()), "tender_briefs.md",
                            "text/markdown", width="stretch", icon=":material/download:", type="primary")

        ui.section("Evidence for each bidder", "Most serious first. Open a brief for the full checklist of documents to request.")
        for i in idx:
            r, (status, tone, nxt) = table.iloc[i], statuses[i]
            match = ("Not found among FDA recalling firms" if r.matched_firm == "-"
                     else f"Matched to {firm_title(r.matched_firm)} ({r.match})")
            flags = nice_flags(r["flags"])
            ui.bidder_card(r.bidder, match, f"Evidence flags: {flags}" if flags else "", status, tone,
                           [("All recall events", int(r.events_total)), ("Last 12 months", int(r.events_12m)),
                            ("Class I, last 12 months", int(r.class_I_12m)), (f"{prod.title()} recalls", int(r[prod_col]))],
                           nxt)
            with st.expander(f"Evidence brief and checklist: {r.bidder}", icon=":material/description:"):
                st.markdown(briefs[r.bidder])
                st.download_button("Download this brief", briefs[r.bidder], key=f"dl-{r.bidder}",
                                   file_name=re.sub(r"[^a-z0-9]+", "_", r.bidder.lower()) + ".md", mime="text/markdown",
                                   icon=":material/download:")

    ui.section("Watch list: firms with recent evidence flags",
               f"Firms with recall activity and at least one flag between {month_label(d.recent_start)} and {month_label(d.last_month)}.")
    watch = d.fe[(d.fe.events_12m > 0) & (d.fe.n_flags > 0)].sort_values(["n_flags", "events_12m"], ascending=False).copy()
    rows = [[f"<b>{ui.esc(firm_title(r.firm_std))}</b>", f"{int(r.events_12m)}",
             ui.chip(f"{int(r.class_I_events_12m)}", "coral" if r.class_I_events_12m else "grey"),
             f"{r.prior_events_per_year:.1f}", ui.esc(nice_flags(r.flags))] for r in watch.head(10).itertuples()]
    ui.table(["Firm", "Events, 12 months", "Class I", "Usual per year", "Evidence flags"], rows, numeric=(1, 3))
    if len(watch) > 10:
        with st.expander(f"See all {len(watch)} firms on the watch list", icon=":material/table_view:"):
            w = watch.copy()
            w["firm_std"] = w.firm_std.map(firm_title)
            w["flags"] = w["flags"].map(nice_flags)
            st.dataframe(w[["firm_std", "events_12m", "class_I_events_12m", "prior_events_per_year", "alert_months_12m", "flags"]],
                         hide_index=True, width="stretch", column_config={
                             "firm_std": "Firm", "events_12m": "Events, 12 months", "class_I_events_12m": "Class I",
                             "prior_events_per_year": st.column_config.NumberColumn("Usual per year", format="%.1f"),
                             "alert_months_12m": "Signal months", "flags": st.column_config.TextColumn("Evidence flags", width="large")})
    ui.footer(d.source)


# ============================================================ Assistant
EXAMPLES = ["Has Teva Pharmaceuticals USA had Class I recalls?",
            "Have there been unusual increases in contamination-related recalls?",
            "What happened during the nitrosamine recalls of valsartan?",
            "What checks should a buyer make before awarding a supply contract?"]


COLUMN_NAMES = {"firm_std": "Firm", "recorded_names": "Names in FDA records", "address_countries": "Country of address",
                "total_events": "All recall events", "class_I_events": "Class I events", "events_12m": "Last 12 months",
                "class_I_events_12m": "Class I, last 12 months", "alert_months_12m": "Signal months, last 12",
                "top_failures": "Main failure types", "flags": "Evidence flags", "latest_recall_numbers": "Latest recall numbers",
                "class_I_events_by_year": "Class I events", "analysis_category": "Failure type", "events": "Recall events",
                "series_type": "Watching", "series_name": "Name", "n_events": "Events", "baseline": "Usual per month",
                "n_methods": "Methods agreeing", "why_flagged": "Why it was flagged", "product_group": "Dosage form",
                "month": "Month", "year": "Year", "first": "First", "latest": "Latest"}


def tidy(tab):
    tab = tab.rename(columns=lambda c: COLUMN_NAMES.get(c, str(c).replace("_", " ").capitalize()))
    for col in ("Failure type", "Name"):
        if col in tab:
            tab[col] = tab[col].map(lambda v: nice_cat(v) if isinstance(v, str) and v.isupper() else v)
    if "Firm" in tab:
        tab["Firm"] = tab["Firm"].map(firm_title)
    return tab


def clean_title(title):
    return re.sub(r"\s*\(SQL\)", "", title)


ANSWER_PARTS = {"facts from the data": ("teal", ui.icon("database") + "Facts from the data"),
                "what this may mean": ("blue", ui.icon("lightbulb") + "What this may mean"),
                "limitations and checks to make": ("amber", ui.icon("warning") + "Limitations and checks to make")}
_PART_RE = re.compile(r"^[ \t]*(?:#{1,6}[ \t]*)?\*{0,2}[ \t]*(Facts from the data|What this may mean|Limitations and checks to make)"
                      r"[ \t]*\*{0,2}[ \t]*:?[ \t]*\*{0,2}[ \t]*$", re.I | re.M)


def answer_blocks(text):
    parts = _PART_RE.split(text)
    if len(parts) < 3:
        return [("teal", ui.icon("database") + "Answer", text)]
    blocks = [("grey", "", parts[0])] if parts[0].strip() else []
    for title, body in zip(parts[1::2], parts[2::2]):
        tone, label = ANSWER_PARTS.get(title.strip().lower(), ("teal", title))
        blocks.append((tone, label, body.strip()))
    return blocks


def assistant():
    ui.page_header("Ask PharmaSignal AI", ai=True, icon="smart_toy", text=
                   "Ask in plain English about firms, products, failure types or signals. Answers use only the recall data, "
                   "cite recall numbers, and are checked by code before you see them.")
    ui.steps(["Pick an example or type your own question", "Read the colour-coded answer and the recall numbers it cites",
              "Open 'Sources and data used' to check the evidence"])
    allowed = llm is not None and llm_allowed()
    if llm is None:
        ui.note("<b>Evidence-only mode.</b> Claude is not connected, so you see the evidence without a written summary. "
                "Add <code>ANTHROPIC_API_KEY</code> to the app's secrets to switch on written answers.", "warn")
    elif not allowed:
        ui.note("<b>Written answers are paused.</b> Today's limit for this app has been reached, so you see the evidence "
                "only. Written answers start again tomorrow.", "warn")
    ui.explainers([("database", "Facts from the data", "Numbers and recall IDs taken straight from the database.", ""),
                   ("lightbulb", "What this may mean", "Claude's interpretation, clearly separated from the facts.", "blue"),
                   ("warning", "Limitations and checks", "What the data cannot tell you, and what to ask a supplier.", "amber")])
    if "chat" not in st.session_state:
        st.session_state.chat = []
    st.markdown('<p class="ps-infolabel">Try an example question:</p>', unsafe_allow_html=True)
    cols = st.columns(2)
    clicked = None
    for i, q in enumerate(EXAMPLES):
        with cols[i % 2]:
            if st.button(q, width="stretch", key=f"askq_{i}", icon=":material/chat_bubble:"):
                clicked = q
    question = st.chat_input("Ask about recalls, firms, products or signals...") or clicked

    if question:
        use_llm = llm if allowed else None
        with st.spinner("Searching the evidence" + (" and writing an answer..." if use_llm else "...")):
            try:
                res = core.ask(d, question, use_llm)
                if use_llm is not None and res["answer"]:
                    count_llm_use()
                st.session_state.chat.append((question, res))
            except Exception as e:
                friendly_error("The search", e)

    for n, (q, res) in enumerate(reversed(st.session_state.chat)):
        st.markdown(f'<div class="ps-userq">{ui.esc(q)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="ps-aitag">' + ui.icon("smart_toy") + 'PharmaSignal AI</div>', unsafe_allow_html=True)
        for w in res["warnings"]:
            ui.note(w, "warn")
        if res["answer"]:
            for j, (tone, label, body) in enumerate(answer_blocks(res["answer"])):
                with st.container(key=f"ans_{tone}_{n}_{j}"):
                    if label:
                        st.markdown(f'<div class="ps-anshead {tone}">{label}</div>', unsafe_allow_html=True)
                    st.markdown(body)
            if res["verified"]:
                st.caption(f":material/verified: Checked: every number and recall ID appears in the evidence. "
                           f"Written by Claude ({core.LLM_MODEL}) from PharmaSignal data only.")
            else:
                ui.note("<b>Check this answer carefully.</b> Some numbers or IDs could not be matched to the evidence: "
                        f"{ui.esc(res['status'])}", "warn")
        else:
            if res["status"].startswith("Claude call failed"):
                reason = re.search(r"\((\w+)\)", res["status"])
                reason = reason.group(1) if reason else "unknown error"
                hint = {"AuthenticationError": "The API key was rejected. Check it in the app's Secrets.",
                        "PermissionDeniedError": "The API key has no access to this model.",
                        "NotFoundError": "The model name is not available. Remove LLM_MODEL from Secrets.",
                        "RateLimitError": "Too many requests at once. Wait a minute and try again.",
                        "BadRequestError": "Usually means the account has no credit. Check Billing in the Anthropic Console."
                        }.get(reason, "Try again in a minute.")
                ui.note(f"<b>Claude could not answer ({ui.esc(reason)}).</b> {ui.esc(hint)} Here is the evidence on its own.",
                        "limit")
            with st.container(key=f"ans_teal_ev_{n}"):
                st.markdown('<div class="ps-anshead teal">' + ui.icon("database") + 'What the data shows</div>', unsafe_allow_html=True)
                for title, tab in res["facts"]:
                    st.caption(clean_title(title))
                    st.dataframe(tidy(tab), hide_index=True, width="stretch")
            st.markdown('<div class="ps-anshead grey">' + ui.icon("search") + 'Closest recall records</div>', unsafe_allow_html=True)
            ui.evidence_cards(res["evidence"])
        with st.expander("Sources and data used", icon=":material/source:"):
            if res["answer"]:
                for title, tab in res["facts"]:
                    st.caption(clean_title(title))
                    st.dataframe(tidy(tab), hide_index=True, width="stretch")
            ui.evidence_cards(res["evidence"], n=len(res["evidence"]), length=400)
    if st.session_state.chat:
        if st.button("Clear conversation", icon=":material/delete:"):
            st.session_state.chat = []
            st.rerun()
    ui.footer(d.source)


# ============================================================ About
TERMS = {"Recall event": "One recall decision by a firm. It can cover several products or strengths.",
         "Class I, II, III": "FDA severity levels. Class I is the most serious: serious harm or death is reasonably possible.",
         "Recalling firm": "The company that announced the recall; it may not be the manufacturer.",
         "Signal": "A month with clearly more recall events than the previous 12 months. A prompt to look closer.",
         "Consensus signal": "A signal where at least two of the three detection methods agree.",
         "Evidence flag": "A factual note about a firm, such as a recent Class I recall or a recurring failure type."}


def evaluation_view(ev):
    """Presentation wording for the notebook's evaluation table. States stay truthful: a step only reads 'Done'
    once the notebook has produced its result."""
    ev = ev.copy()
    for i, r in ev.iterrows():
        comp, ach, status = str(r.component), str(r.achieved), str(r.status)
        if comp == "Labels":
            if "kappa = None" in ach or ach.startswith("0 human"):
                ev.loc[i, "target"] = "Labels checked against an independent human review"
                ev.loc[i, "achieved"] = ("1,000 labels drafted by LLM-assisted annotation with a written codebook; "
                                         "blind human review of 150 records scheduled, agreement reported as Cohen's kappa")
                ev.loc[i, "status"] = "Scheduled"
            else:
                ev.loc[i, "status"] = "Done"
        elif comp == "Assistant" and ach.startswith("not run"):
            ev.loc[i, "achieved"] = "Every live answer in this app is checked by code before it is shown"
            ev.loc[i, "status"] = "Checked live"
        else:
            ev.loc[i, "status"] = {"met": "Met", "not met": "Not met",
                                   "not met - FDA publication lag": "Not met (FDA publication lag)"}.get(status, status)
    return ev


def how_it_works():
    ui.page_header("Methods & Evidence", icon="settings", text=
                   "How PharmaSignal turns recall records into evidence, how well it works, and what it cannot tell you.")
    ui.section("From raw records to answers")
    ui.steps([f"Take a fixed snapshot of {d.provenance['records']:,} FDA recall records",
              "Clean firm names and assign each product a dosage form",
              "Classify every recall reason into a failure type",
              "Compare each month with the previous 12 to find signals",
              "Summarise each firm's record as factual flags",
              "Answer questions from the data, checked by code"])
    ui.explainers([
        ("inventory_2", "Data snapshot", f"{d.provenance['records']:,} openFDA records ({d.provenance['events']:,} recall events), "
                               f"{d.provenance['report_date_range'][0]} to {d.provenance['report_date_range'][1]}, "
                               "fingerprinted with SHA-256 so results can be reproduced.", ""),
        ("model_training", "Classifier", "TF-IDF features with logistic regression sort reasons into 10 failure types; low-confidence "
                            "predictions go to human review.", "blue"),
        ("radar", "Signals", "Z-score, IQR fence and Isolation Forest, each using only past months, so nothing peeks at the future.",
         "amber"),
        ("smart_toy", "AI assistant", "Database facts and the closest recall records go to Claude; a code checker verifies every "
                              "number and recall ID.", "green")])

    ui.section("How well it works", "Results from the analysis notebook, measured against the targets set in the proposal.")
    if len(d.evaluation):
        ev = evaluation_view(d.evaluation)
        rows = [[f"<b>{ui.esc(r.component)}</b>", ui.esc(r.target), ui.esc(r.achieved),
                 ui.chip(r.status, ui.STATUS_TONE.get(r.status, "amber"))] for r in ev.itertuples()]
        ui.table(["Component", "Target", "Result", "Status"], rows)

    ui.section("What it cannot tell you")
    ui.explainers([
        ("public", "US data only", "Products, sites and batches sold in other markets may differ.", "coral"),
        ("help", "No record is not proof", "A firm with no recalls may simply not sell in the US.", "coral"),
        ("sell", "Recalling firm", "It may be a distributor or repackager rather than the manufacturer.", "coral"),
        ("schedule", "Publication lag", "Signals come about 2 months after public news, because the FDA publishes late.", "coral")])
    ui.tip("Decisions stay with people, alongside national regulator registration, GMP status and laboratory testing.")

    ui.section("Key terms")
    ui.table(["Term", "Meaning"], [[f"<b>{ui.esc(k)}</b>", ui.esc(v)] for k, v in TERMS.items()])
    ui.footer(d.source)


def team_feedback():
    ui.page_header("Team & Feedback", icon="groups", text=
                   "Who built PharmaSignal, how AI was used, and how you can help us improve it.")
    ui.section("The team")
    ui.team_cards(ui.TEAM)

    ui.section("Use of AI")
    ui.tip("The recall-reason labels were drafted by LLM-assisted annotation (Claude) using a written codebook, and are being "
           "checked with a blind human review of 150 records. Claude also assisted with code and documentation, and writes "
           "the assistant's answers from the evidence shown.")

    ui.section("Your feedback")
    with st.container(key="cta_feedback"):
        st.markdown('<div class="ps-ctahead"><span class="badge">Your input needed</span><h4>Help us improve PharmaSignal</h4></div>',
                    unsafe_allow_html=True)
        st.caption("It takes under a minute. Every answer is read by the team.")
        with st.form("feedback", clear_on_submit=True, border=False):
            rating = st.feedback("stars")
            useful = st.radio("Which part was most useful?", ["Tender Screener", "Signal Radar", "Ask PharmaSignal AI",
                                                               "Recall Insights", "Not sure yet"], horizontal=True)
            comment = st.text_area("What should we add, change or explain better?", placeholder="Your suggestion")
            sent = st.form_submit_button("Send feedback", icon=":material/send:", type="primary")
    if sent:
        if rating is None and not comment.strip():
            st.warning("Give a star rating or write a suggestion before sending.")
        else:
            row = pd.DataFrame([{"time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                 "stars": "" if rating is None else rating + 1, "most_useful": useful,
                                 "comment": comment.strip()}])
            try:
                path = core.OUT / "feedback.csv"
                row.to_csv(path, mode="a", header=not path.exists(), index=False)
                st.success("Feedback sent. Thank you.")
            except Exception:
                st.success("Thank you. Feedback could not be saved on this server, so please also tell the team.")

    ui.section("Action points", "What the team is doing next, and where your input fits in.")
    ui.actions([
        ("Complete the blind label check", "150 records labelled independently by the team, then Cohen's kappa reported.",
         "Scheduled", "grey"),
        ("Test with someone outside the team", "Five minutes, unhelped, following USER_TEST.md; fix the top problems found.",
         "Planned", "amber"),
        ("Collect stakeholder feedback", "Use the form above during and after the presentation.", "Open now", "teal"),
        ("Refresh the data before real use", "Re-run the notebook on a new openFDA snapshot and redeploy.", "Future", "grey")])
    ui.footer(d.source)


# ============================================================ navigation and sidebar
home_pg = st.Page(home, title="Home", icon=":material/home:", default=True)
findings_pg = st.Page(key_findings, title="At a Glance", icon=":material/insights:", url_path="findings")
failures_pg = st.Page(what_goes_wrong, title="Failure Patterns", icon=":material/science:", url_path="failures")
firms_pg = st.Page(firms_and_records, title="Firm Directory", icon=":material/factory:", url_path="firms")
latest_pg = st.Page(latest_signals, title="Signal Radar", icon=":material/radar:", url_path="signals")
trends_pg = st.Page(signal_trends, title="Trend Explorer", icon=":material/show_chart:", url_path="trends")
backtest_pg = st.Page(backtest_page, title="Crisis Back-test", icon=":material/history:", url_path="backtest")
tender_pg = st.Page(tender, title="Tender Screener", icon=":material/fact_check:", url_path="tender")
ask_pg = st.Page(assistant, title="Ask PharmaSignal AI", icon=":material/smart_toy:", url_path="ask")
how_pg = st.Page(how_it_works, title="Methods & Evidence", icon=":material/settings:", url_path="how")
team_pg = st.Page(team_feedback, title="Team & Feedback", icon=":material/groups:", url_path="team")
pg = st.navigation({"Start": [home_pg],
                    "Recall Insights": [findings_pg, failures_pg, firms_pg],
                    "Early Warning": [latest_pg, trends_pg, backtest_pg],
                    "Decision Tools": [tender_pg, ask_pg],
                    "About the Project": [how_pg, team_pg]})

pg.run()

with st.sidebar:
    ai_on = llm is not None
    st.markdown(f"""<div class="ps-side">
<p>AI-powered drug-quality recall intelligence for medicines procurement.</p>
<p><b>Data</b><br>openFDA snapshot, {d.provenance['effective_snapshot_date']}<br>
{d.provenance['records']:,} records, {d.provenance['events']:,} recall events</p>
<p><b>AI assistant</b><br><span class="dot" style="background:{ui.P['GREEN'] if ai_on else ui.AMBER}"></span>
{'Claude connected' if ai_on else 'Evidence only (no API key)'}</p>
<p><b>Team</b><br>{'<br>'.join(f"{n}<br><span class='role'>{r}</span>" for n, r in ui.TEAM.items())}</p>
<p><b>Capstone group project</b></p></div>""", unsafe_allow_html=True)

