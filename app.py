"""PharmaSignal - Streamlit app.

Run the notebook once (it creates outputs/), then:   streamlit run app.py
"""
import os
import re
from datetime import datetime, timezone

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import pharmasignal_core as core
import ui

st.set_page_config(page_title="PharmaSignal", page_icon="💊", layout="wide", initial_sidebar_state="auto")
ui.apply_style()
st.logo(str(core.ROOT / "assets" / "logo.svg"), size="large", icon_image=str(core.ROOT / "assets" / "icon.svg"))



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
def get_llm():
    return core.make_llm(api_key=ANTHROPIC_API_KEY)


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
llm = get_llm()
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


# ============================================================ Overview
def overview():
    by_month = EVENTS.dropna(subset=["report_date_dt"]).set_index("report_date_dt").resample("MS").event_id.nunique()
    peak_month, peak_n = by_month.idxmax(), int(by_month.max())
    ui.hero("PharmaSignal, drug-quality recall intelligence for Kenya",
            "Check a supplier's recall record before you award the tender",
            "Fourteen years of US FDA drug-quality recalls, turned into evidence a procurement team can use: what went "
            "wrong, which firms and products keep recurring, and which documents to ask a bidder for.",
            by_month.values,
            f"Each point is one month of FDA drug-quality recall events, {by_month.index.min():%b %Y} to "
            f"{by_month.index.max():%b %Y}. The amber dot is the busiest month: {peak_month:%B %Y}, {peak_n} events.")
    ui.who_strip("Pharmacists and procurement officers in Kenyan hospitals, counties and supply agencies",
                 "Screen the firms and products bidding for a medicines tender",
                 "Proceed with a bidder, or ask for more documents before award")

    ui.section("What would you like to do?")
    c1, c2, c3 = st.columns(3)
    c1.page_link(tender_pg, label="Screen tender bidders", icon=":material/fact_check:", width="stretch")
    c2.page_link(signals_pg, label="Check recent recall signals", icon=":material/monitoring:", width="stretch")
    c3.page_link(ask_pg, label="Ask a question in plain English", icon=":material/forum:", width="stretch")

    # ---- four facts, always for the whole dataset
    n_ev = EVENTS.event_id.nunique()
    share_i = (EVENTS.classification == "Class I").mean()
    cats = EVENTS.analysis_category.value_counts(normalize=True)
    forms = EVENTS.product_group.value_counts(normalize=True)
    per_firm = EVENTS.groupby("firm_std").event_id.nunique()
    top3 = [nice_cat(c).lower() for c in cats.index[:3]]
    ui.section("What the recall record shows",
               f"Four facts from {n_ev:,} recall events published by the FDA between "
               f"{d.provenance['report_date_range'][0][:4]} and {d.provenance['report_date_range'][1][:4]}.")
    ui.findings([
        (f"1 in {round(1 / share_i)}", "recall events is Class I: a reasonable chance of serious harm or death.", "coral"),
        (f"{cats.iloc[:3].sum() * 100:.0f}%", f"of recalls come from three failure types: {top3[0]}, {top3[1]} and {top3[2]}.", ""),
        (f"{forms.iloc[0] * 100:.0f}%", f"involve {forms.index[0].lower()} products such as tablets and capsules; "
                                        f"{forms.index[1].lower()} products are next at {forms.iloc[1] * 100:.0f}%.", "ink"),
        (f"{(per_firm > 1).mean() * 100:.0f}%", "of recalling firms recalled more than once. Repeat recallers are where "
                                                "a buyer's questions should start.", "amber")])

    # ---- explore
    years = sorted(int(y) for y in d.recalls.year.dropna().unique())
    ui.section("How serious were the recalls, year by year?")
    ui.class_legend()
    with st.expander("Filter the charts below by year or class"):
        f1, f2 = st.columns([2, 1])
        yr = f1.slider("Publication year", years[0], years[-1], (years[0], years[-1]))
        all_classes = ["Class I", "Class II", "Class III"]
        classes = f2.multiselect("Recall class", all_classes, default=all_classes)
    f = d.recalls[d.recalls.year.between(*yr) & (d.recalls.classification.isin(classes)
                                                 | ~d.recalls.classification.isin(all_classes))]
    ev = f.drop_duplicates("event_id")
    per_year = ev[ev.classification.isin(classes)].groupby(["year", "classification"]).size().reset_index(name="events")
    st.subheader("Class II recalls dominate every year; Class I is the smaller, most serious share")
    ui.chart(alt.Chart(per_year).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("events:Q", title="Recall events"),
        color=alt.Color("classification:N", title=None, scale=ui.CLASS_COLOURS),
        order=alt.Order("classification:N", sort="ascending"),
        tooltip=["year", "classification", "events"]), 300)

    ui.section("What goes wrong, and in which products?")
    a, b = st.columns(2, gap="large")
    with a:
        c = ev.analysis_category.map(nice_cat).value_counts().rename_axis("failure").reset_index(name="events")
        st.subheader(f"{c.failure.iloc[0]} and {c.failure.iloc[1].lower()} lead")
        ui.ranked_bars(c, "events", "failure", highlight=2, height=340)
    with b:
        g = ev.product_group.value_counts().rename_axis("dosage form").reset_index(name="events")
        st.subheader(f"{g['dosage form'].iloc[0]} and {g['dosage form'].iloc[1].lower()} products lead")
        ui.ranked_bars(g, "events", "dosage form", highlight=2, colour=ui.INK, height=340)

    ui.section("Which firms recall most often?",
               "The recalling firm announced the recall. It may be a distributor or repackager rather than the manufacturer, "
               "so treat a name as the start of a question, not a conclusion.")
    top = (ev.groupby("firm_std").agg(events=("event_id", "nunique"),
                                      class_I=("classification", lambda s: int((s == "Class I").sum())))
           .sort_values("events", ascending=False).head(10).reset_index())
    top["firm_std"] = top.firm_std.map(firm_title)
    st.dataframe(top, hide_index=True, width="stretch", column_config={
        "firm_std": st.column_config.TextColumn("Recalling firm", width="large"),
        "events": st.column_config.ProgressColumn("Recall events", format="%d", min_value=0, max_value=int(top.events.max())),
        "class_I": st.column_config.NumberColumn("Of which Class I", width="small")})

    with st.expander("Search individual recall records"):
        q = st.text_input("Product, firm or reason contains", placeholder="e.g. metformin, benzene, Teva")
        if q:
            hit = f[f.product_description.str.contains(q, case=False, na=False, regex=False)
                    | f.recalling_firm.str.contains(q, case=False, na=False, regex=False)
                    | f.reason_clean.str.contains(q, case=False, na=False, regex=False)]
            st.caption(f"{len(hit):,} records match; showing the newest 500.")
            out = hit.sort_values("report_date", ascending=False)[
                ["recall_number", "report_date", "classification", "recalling_firm", "analysis_category",
                 "product_group", "reason_clean", "product_description"]].head(500)
            out["analysis_category"] = out.analysis_category.map(nice_cat)
            st.dataframe(out, hide_index=True, width="stretch")
            st.download_button("Download these records (CSV)", out.to_csv(index=False), "recall_search.csv", "text/csv")
    ui.footer(d.source)


# ============================================================ Signals
def signals():
    ui.page_header("Recall signals",
                   "A signal means a month had clearly more recall events than usual for a failure type, dosage form or firm. "
                   "It is a prompt to look closer, not a confirmed quality failure.")
    ui.steps(["Choose the period and what to watch", "Read why each month was flagged",
              "Open a trend to see the signal against the usual level"])

    al_all = d.alerts.copy()
    cons = al_all[al_all.n_methods >= 2].sort_values(["month", "n_methods"], ascending=False)
    if len(cons):
        latest = cons.iloc[0]
        label = nice_cat(latest.series_name) if latest.series_type == "category" else firm_title(latest.series_name)
        what = {"category": "failure type", "product_group": "dosage form", "firm": "firm"}[latest.series_type]
        ui.note(f"<b>Most recent consensus signal:</b> {ui.esc(label)} ({what}) in {month_label(latest.month)}, with "
                f"{int(latest.n_events)} recall events against a usual {latest.hist_mean:.1f} a month. "
                f"{int(latest.n_methods)} of 3 methods agreed.", "warn")

    c1, c2, c3 = st.columns(3)
    window = c1.selectbox("Period", ["Last 6 months", "Last 12 months", "All history"], index=1)
    kinds = c2.multiselect("Watch", ["category", "product_group", "firm"], default=["category", "product_group", "firm"],
                           format_func={"category": "Failure types", "product_group": "Dosage forms", "firm": "Firms"}.get)
    min_methods = c3.select_slider("Methods that must agree", [1, 2, 3], value=1,
                                   help="Three methods check each month. 2 or more agreeing = consensus signal.")
    al = al_all
    if window != "All history":
        al = al[al.month > str(d.last_month - (6 if window == "Last 6 months" else 12))]
    al = al[al.series_type.isin(kinds) & (al.n_methods >= min_methods)].sort_values(["month", "n_methods"], ascending=False)
    ui.kpis([(f"{len(al)}", "signals in this view", "amber"),
             (f"{int((al.n_methods >= 2).sum())}", "consensus signals, where 2+ methods agree", "amber"),
             (f"{al.series_name.nunique()}", "failure types, dosage forms or firms affected", ""),
             (month_label(d.last_month), "latest month in the data", "")])
    show = al[["month", "series_type", "series_name", "n_events", "hist_mean", "n_methods", "why_flagged"]].copy()
    show["series_name"] = [nice_cat(n) if t == "category" else firm_title(n) for t, n in zip(show.series_type, show.series_name)]
    show["month"] = show.month.map(month_label)
    show["flagged_by"] = show.why_flagged.str.extract(r"flagged by ([^;]+)")[0].str.replace("zscore", "z-score")
    show["class_i"] = show.why_flagged.str.extract(r"(\d+)% of records Class I")[0].astype(float)
    show = show.drop(columns="why_flagged")
    show["series_type"] = show.series_type.map({"category": "Failure type", "product_group": "Dosage form", "firm": "Firm"})
    if show.empty:
        ui.note("No signals match these filters. Widen the period or lower the number of methods that must agree.", "info")
    else:
        st.subheader("Latest signals in this view")
        cards = show.head(6)
        ui.signal_cards([{"name": r.series_name, "kind": r.series_type, "month": r.month, "events": int(r.n_events),
                          "usual": float(r.hist_mean), "methods": int(r.n_methods),
                          "flagged_by": r.flagged_by if isinstance(r.flagged_by, str) else "the detectors",
                          "class_i": r.class_i} for r in cards.itertuples()])
        if len(show) > 6:
            st.caption(f"Showing the 6 most recent of {len(show)} signals. Open the full table below to see them all.")
    if not show.empty:
        with st.expander(f"All {len(show)} signals as a table"):
            st.dataframe(show, hide_index=True, width="stretch", column_config={
                "month": "Month", "series_type": "Watching", "series_name": "Name", "n_events": "Events",
                "hist_mean": st.column_config.NumberColumn("Usual per month", format="%.1f"),
                "n_methods": st.column_config.ProgressColumn("Methods agreeing", min_value=0, max_value=3, format="%d of 3",
                                                             width="small"),
                "flagged_by": st.column_config.TextColumn("Flagged by", width="medium"),
                "class_i": st.column_config.NumberColumn("Class I share", format="%d%%")})
            st.download_button("Download these signals (CSV)", show.to_csv(index=False), "pharmasignal_signals.csv",
                               "text/csv")

    with st.expander("How the three methods decide"):
        m1, m2, m3 = st.columns(3)
        m1.markdown("**Z-score**  \nHow far this month sits above the 12-month average, measured in standard deviations. "
                    "Signals at 3 or more.")
        m2.markdown("**IQR fence**  \nAbove the normal range of the last 12 months (Q3 + 1.5 × IQR). Earlier spikes do not "
                    "distort it, so it caught the most past crises.")
        m3.markdown("**Isolation Forest**  \nA machine-learning check of seven features together, such as event count, "
                    "Class I share and number of firms involved.")
        st.caption("Every method needs at least 3 events in the month and more than the 12-month average.")

    ms = d.monthly.copy()
    ui.section("Try a different sensitivity",
               "Stricter settings mean fewer alerts to review but more problems missed. Move the sliders to see the trade-off "
               "for failure types and dosage forms.")
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
    change = lambda n, o: "same as the project setting" if abs(n - o) < 0.005 else f"{n - o:+.2f} compared with the project setting"
    ui.kpis([(f"{new[0]:.2f}", f"Z-score alerts per month ({change(new[0], base[0])})", "teal"),
             (f"{new[1]:.2f}", f"IQR alerts per month ({change(new[1], base[1])})", "teal")])

    options = ms[ms.series_type != "firm"][["series_type", "series_name"]].drop_duplicates().apply(tuple, axis=1).tolist()
    default = options.index(("category", "IMPURITIES")) if ("category", "IMPURITIES") in options else 0
    pick = st.selectbox("Show the trend for", options, index=default,
                        format_func=lambda t: nice_cat(t[1]) if t[0] == "category" else f"{t[1]} (dosage form)")
    s = ms[(ms.series_type == pick[0]) & (ms.series_name == pick[1])].copy()
    s["date"] = pd.to_datetime(s.month)
    s["signal"] = s.z_new | s.iqr_new
    name = nice_cat(pick[1]) if pick[0] == "category" else pick[1]
    st.subheader(f"{name}: monthly recall events, with signals at your settings")
    base_c = alt.Chart(s).encode(x=alt.X("date:T", title=None))
    ui.chart(base_c.mark_area(color=ui.TEAL, opacity=0.10).encode(y="n_events:Q")
             + base_c.mark_line(color=ui.TEAL, strokeWidth=1.6).encode(
                 y=alt.Y("n_events:Q", title="Recall events per month"),
                 tooltip=[alt.Tooltip("month:N", title="Month"), alt.Tooltip("n_events:Q", title="Events"),
                          alt.Tooltip("hist_mean:Q", title="Usual per month", format=".1f")])
             + base_c.mark_line(strokeDash=[5, 4], color=ui.SLATE, strokeWidth=1.4).encode(y="hist_mean:Q")
             + base_c.transform_filter("datum.signal").mark_point(color=ui.AMBER, size=90, filled=True, opacity=1,
                                                                  stroke=ui.INK, strokeWidth=1).encode(y="n_events:Q"), 330)
    st.caption("Teal line: recall events each month. Dashed line: the usual level (average of the previous 12 months). "
               "Amber dots: months that signal at the settings above.")

    if len(d.backtest):
        ui.section("Would it have caught real crises?",
                   "We replayed six known recall crises, such as nitrosamines in sartans and methanol in hand sanitisers.")
        ms_ = d.method_summary.copy()
        ms_["method"] = ms_.method.map({"iqr": "IQR fence", "zscore": "Z-score", "iforest": "Isolation Forest",
                                        "consensus": "Consensus (2+ agree)"}).fillna(ms_.method)
        st.dataframe(ms_[["method", "events_detected", "watch_alerts_per_month", "median_lead_vs_public"]],
                     hide_index=True, width="stretch", column_config={
                         "method": "Method", "events_detected": st.column_config.ProgressColumn(
                             "Crises detected, of 6", min_value=0, max_value=6, format="%d"),
                         "watch_alerts_per_month": st.column_config.NumberColumn("Alerts per month", format="%.2f"),
                         "median_lead_vs_public": st.column_config.NumberColumn("Months after public news", format="%+.0f")})
        ui.note("<b>What this means:</b> signals arrived in the crisis peak month, about 2 months after the news, mainly "
                "because the FDA publishes recalls weeks after they start. PharmaSignal recognises clusters; it does not "
                "predict them. Slow-building problems such as benzene in sprays produced no monthly spike.", "limit")
    ui.footer(d.source)


# ============================================================ Tender screening
EXAMPLE_BIDDERS = "Sun Pharmaceutical Industries\nLupin Pharmaceuticals\nMarksans Pharma\nNairobi Generics Ltd"


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
                "Check PPB registration and GMP evidence as usual. No FDA record is not proof of good quality.")
    if row.class_I_12m > 0:
        return ("Recent Class I recall", "coral",
                "Ask for the root-cause investigation and corrective actions, plus the documents in the brief.")
    if row["flags"] not in ("none", "", None):
        return ("Evidence to discuss", "amber", "Raise the flagged issues with the bidder and request the documents in the brief.")
    return ("No recent flags", "teal", "Request the standard documents listed in the brief.")


def tender():
    ui.page_header("Tender screening",
                   "See each bidder's FDA recall evidence side by side, with a checklist of documents to request before award.")
    ui.steps(["Add the bidders: type them, upload a list, or use the example", "Enter the product being tendered",
              "Screen, then download each bidder's evidence brief"])
    if "bidders_text" not in st.session_state:
        st.session_state.bidders_text = ""
    left, right = st.columns([3, 2], gap="large")
    with left:
        tab_type, tab_upload = st.tabs(["Type the names", "Upload a list"])
        with tab_type:
            st.text_area("Bidders, one per line", key="bidders_text", height=140,
                         placeholder="e.g. Sun Pharmaceutical Industries")
            st.button("Use example bidders", icon=":material/science:", on_click=fill_example)
        with tab_upload:
            up = st.file_uploader("CSV or Excel file, one bidder per row", type=["csv", "xlsx"],
                                  help="Uses a column called 'bidder' (or firm, supplier, name), otherwise the first column.")
            st.download_button("Download a template", "bidder\nSun Pharmaceutical Industries\nLupin Pharmaceuticals\n",
                               "bidder_template.csv", "text/csv")
    with right:
        product = st.text_input("Product being tendered", key="product", placeholder="e.g. metformin")
        run = st.button("Screen bidders", type="primary", icon=":material/fact_check:", width="stretch")
        ui.note("<b>Good to know:</b> no US FDA record is not evidence of good quality. The firm may not sell in the US "
                "or may trade under another name.", "limit")

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
        ui.section(f"Results for {len(table)} bidders, {prod}")
        ui.kpis([(f"{len(table)}", "bidders screened", ""),
                 (f"{tones.count('coral')}", "with a Class I recall in the last 12 months", "coral"),
                 (f"{tones.count('amber')}", "with other evidence to discuss", "amber"),
                 (f"{tones.count('grey')}", "with no FDA recall record", "")])
        order = {"coral": 0, "amber": 1, "teal": 2, "grey": 3}
        for i in sorted(range(len(table)), key=lambda i: order[tones[i]]):
            r, (status, tone, nxt) = table.iloc[i], statuses[i]
            match = ("Not found among FDA recalling firms" if r.matched_firm == "-"
                     else f"Matched to {firm_title(r.matched_firm)} ({r.match})")
            flags = nice_flags(r["flags"])
            ui.bidder_card(r.bidder, match, f"Evidence flags: {flags}" if flags else "", status, tone,
                           [("All recall events", int(r.events_total)), ("Last 12 months", int(r.events_12m)),
                            ("Class I, last 12 months", int(r.class_I_12m)), (f"{prod.title()} recalls", int(r[prod_col]))],
                           nxt)
            with st.expander(f"Evidence brief and checklist for {r.bidder}"):
                st.markdown(briefs[r.bidder])
                st.download_button("Download this brief", briefs[r.bidder], key=f"dl-{r.bidder}",
                                   file_name=re.sub(r"[^a-z0-9]+", "_", r.bidder.lower()) + ".md", mime="text/markdown")
        dl1, dl2 = st.columns(2)
        dl1.download_button("Download the summary table (CSV)", table.to_csv(index=False), "tender_screening.csv",
                            "text/csv", width="stretch", icon=":material/download:")
        dl2.download_button("Download all evidence briefs", "\n\n---\n\n".join(briefs.values()), "tender_briefs.md",
                            "text/markdown", width="stretch", icon=":material/download:")

    ui.section("Watch list: firms with recent evidence flags",
               f"Firms with recall activity and at least one flag between {d.recent_start} and {d.last_month}.")
    watch = d.fe[(d.fe.events_12m > 0) & (d.fe.n_flags > 0)].sort_values(["n_flags", "events_12m"], ascending=False).copy()
    watch["firm_std"] = watch.firm_std.map(firm_title)
    watch["flags"] = watch["flags"].map(nice_flags)
    st.dataframe(watch[["firm_std", "events_12m", "class_I_events_12m", "prior_events_per_year", "alert_months_12m", "flags"]],
                 hide_index=True, width="stretch", column_config={
                     "firm_std": "Firm", "events_12m": "Events, last 12 months", "class_I_events_12m": "Class I",
                     "prior_events_per_year": st.column_config.NumberColumn("Usual per year", format="%.1f"),
                     "alert_months_12m": "Signal months", "flags": st.column_config.TextColumn("Evidence flags", width="large")})
    ui.footer(d.source)


# ============================================================ Assistant
EXAMPLES = ["Has Teva Pharmaceuticals USA had Class I recalls?",
            "Have there been unusual increases in contamination-related recalls?",
            "What happened during the nitrosamine recalls of valsartan?",
            "What checks should KEMSA do before awarding a supply contract?"]


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


def assistant():
    ui.page_header("Ask PharmaSignal",
                   "Ask in plain English about firms, products, failure types or signals. Answers use only the recall data, "
                   "cite recall numbers, and are checked by code before you see them.")
    ui.steps(["Pick an example or type your own question", "Read the answer and the recall numbers it cites",
              "Open 'Sources and data used' to check the evidence"])
    allowed = llm is not None and llm_allowed()
    if llm is None:
        ui.note("<b>Evidence-only mode.</b> Claude is not connected, so you see the evidence without a written summary. "
                "Add <code>ANTHROPIC_API_KEY</code> to the app's secrets to switch on written answers.", "warn")
    elif not allowed:
        ui.note("<b>Written answers are paused.</b> Today's limit for this app has been reached, so you see the evidence "
                "only. Written answers start again tomorrow.", "warn")
    if "chat" not in st.session_state:
        st.session_state.chat = []
    cols = st.columns(2)
    clicked = next((q for i, q in enumerate(EXAMPLES) if cols[i % 2].button(q, width="stretch", key=f"ex{i}",
                                                                           icon=":material/chat_bubble:")), None)
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

    for q, res in reversed(st.session_state.chat):
        with st.chat_message("user", avatar=":material/person:"):
            st.write(q)
        with st.chat_message("assistant", avatar=":material/medication:"):
            for w in res["warnings"]:
                ui.note(w, "warn")
            if res["answer"]:
                with st.container(border=True):
                    st.markdown(res["answer"])
                if res["verified"]:
                    st.caption(":material/verified: Checked: every number and recall ID in this answer appears in the "
                               f"evidence. Written by Claude ({core.LLM_MODEL}) from PharmaSignal data only.")
                else:
                    ui.note("<b>Check this answer carefully.</b> Some numbers or IDs could not be matched to the evidence: "
                            f"{ui.esc(res['status'])}", "warn")
            else:
                if res["status"].startswith("Claude call failed"):
                    ui.note("Claude could not be reached just now, so here is the evidence on its own. Try again in a "
                            "minute.", "limit")
                st.markdown("**Here is what the data shows**")
                for title, tab in res["facts"]:
                    st.caption(clean_title(title))
                    st.dataframe(tidy(tab), hide_index=True, width="stretch")
                st.markdown("**Closest recall records**")
                ui.evidence_cards(res["evidence"])
            with st.expander("Sources and data used"):
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
ROLES = {"Cindy Murogo": "Project lead and data pipeline",
         "Mananda Kirungu Salim": "Exploratory analysis and data quality",
         "Daniel Kimasar": "Classification, model evaluation and business analytics",
         "Varlerly Maina": "Anomaly detection",
         "Nelson Masaki": "App, dashboard and documentation"}
TERMS = {"Recall event": "One recall decision by a firm. It can cover several products or strengths.",
         "Class I, II, III": "FDA severity levels. Class I is the most serious: serious harm or death is reasonably possible.",
         "Recalling firm": "The company that announced the recall; it may not be the manufacturer.",
         "Signal": "A month with clearly more recall events than the previous 12 months. A prompt to look closer.",
         "Consensus signal": "A signal where at least two of the three detection methods agree.",
         "Evidence flag": "A factual note about a firm, such as a recent Class I recall or a recurring failure type."}


def about():
    ui.page_header("About PharmaSignal", "What the tool does, how well it works, what it cannot tell you, and who built it.")
    ui.section("How it works")
    ui.steps([f"Take a fixed snapshot of {d.provenance['records']:,} FDA recall records",
              "Clean firm names and assign each product a dosage form",
              "Classify every recall reason into a failure type",
              "Compare each month with the previous 12 to find signals",
              "Summarise each firm's record as factual flags",
              "Answer questions from the data, checked by code"])
    with st.expander("Method details"):
        st.markdown(f"""
- **Snapshot:** {d.provenance['records']:,} openFDA drug-enforcement records ({d.provenance['events']:,} recall events),
  {d.provenance['report_date_range'][0]} to {d.provenance['report_date_range'][1]}, fingerprinted with SHA-256.
- **Classifier:** TF-IDF features with logistic regression; low-confidence predictions go to human review.
- **Signals:** z-score, IQR fence and Isolation Forest, each using only past months.
- **Assistant:** SQL facts plus the closest recall records go to Claude; a checker verifies every number and recall ID.
""")
    ui.section("How well it works")
    if len(d.evaluation):
        st.dataframe(d.evaluation, hide_index=True, width="stretch", column_config={
            "component": st.column_config.TextColumn("Component", width="small"),
            "target": st.column_config.TextColumn("Target", width="medium"),
            "achieved": st.column_config.TextColumn("Result", width="large"),
            "status": st.column_config.TextColumn("Status", width="medium")})
    figs = core.OUT / "figures"
    if (figs / "backtests.png").exists():
        with st.expander("Back-test charts for the six known crises"):
            st.image(str(figs / "backtests.png"), width="stretch")

    ui.section("What it cannot tell you")
    ui.note("""<ul style="margin:0;padding-left:1.1rem">
<li>It uses US FDA data only. Products, sites and batches supplied to Kenya may differ.</li>
<li>No recall record is not evidence of good quality.</li>
<li>The recalling firm may be a distributor or repackager rather than the manufacturer.</li>
<li>Signals come about 2 months after public news, because of the FDA's publication lag.</li>
<li>Decisions stay with people, alongside PPB registration, GMP status and laboratory testing.</li></ul>""", "limit")

    ui.section("Key terms")
    st.dataframe(pd.DataFrame({"Term": list(TERMS), "Meaning": list(TERMS.values())}), hide_index=True, width="stretch",
                 column_config={"Term": st.column_config.TextColumn(width="small"),
                                "Meaning": st.column_config.TextColumn(width="large")})

    ui.section("Use of AI")
    st.markdown("The recall-reason labels were drafted by LLM-assisted annotation (Claude) using a written codebook and "
                "checked with a blind human review of 150 records. Claude also assisted with code and documentation, and "
                "writes the assistant's answers from the evidence shown.")

    ui.section("The team")
    st.dataframe(pd.DataFrame({"Member": list(ROLES), "Role": list(ROLES.values())}), hide_index=True, width="stretch")

    ui.section("Tell us what you think")
    with st.form("feedback", clear_on_submit=True):
        rating = st.feedback("thumbs")
        comment = st.text_area("What would make PharmaSignal more useful?", placeholder="Optional")
        sent = st.form_submit_button("Send feedback", icon=":material/send:")
    if sent:
        if rating is None and not comment.strip():
            st.warning("Choose thumbs up or down, or write a comment, before sending.")
        else:
            row = pd.DataFrame([{"time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                 "rating": {0: "down", 1: "up"}.get(rating, ""), "comment": comment.strip()}])
            try:
                path = core.OUT / "feedback.csv"
                row.to_csv(path, mode="a", header=not path.exists(), index=False)
                st.success("Feedback sent. Thank you.")
            except Exception:
                st.success("Thank you. Feedback could not be saved on this server, so please also tell the team.")
    ui.footer(d.source)


# ============================================================ navigation and sidebar
home_pg = st.Page(overview, title="Overview", icon=":material/dashboard:", default=True)
signals_pg = st.Page(signals, title="Recall signals", icon=":material/monitoring:", url_path="signals")
tender_pg = st.Page(tender, title="Tender screening", icon=":material/fact_check:", url_path="tender")
ask_pg = st.Page(assistant, title="Ask PharmaSignal", icon=":material/forum:", url_path="ask")
about_pg = st.Page(about, title="About and methods", icon=":material/info:", url_path="about")
pg = st.navigation({"Explore": [home_pg, signals_pg], "Decide": [tender_pg, ask_pg], "Project": [about_pg]})

with st.sidebar:
    ai_on = llm is not None
    st.markdown(f"""<div class="ps-side">
<p>Drug-quality recall intelligence for medicines procurement in Kenya.</p>
<p><b>Data</b><br>openFDA snapshot, {d.provenance['effective_snapshot_date']}<br>
{d.provenance['records']:,} records, {d.provenance['events']:,} recall events</p>
<p><b>Assistant</b><br><span class="dot" style="background:{ui.TEAL_LIGHT if ai_on else ui.AMBER}"></span>
{'Claude connected' if ai_on else 'Evidence only (no API key)'}</p>
<p><b>Team</b><br>{'<br>'.join(ui.TEAM)}</p>
<p>MSc Pharmaceutical Sciences capstone</p></div>""", unsafe_allow_html=True)

pg.run()
