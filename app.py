"""
India Automotive Intelligence Platform (IAIP) - Streamlit dashboard
Team The Quants · IISc DA 231o

Reads the Gold layer (Parquet) produced by notebooks 01-06 directly. Nothing is copied or re-computed by hand.
Run:  double-click run_dashboard.bat   (or:  python -m streamlit run app.py  from this folder)
"""
import os
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

T_START = time.perf_counter()
st.set_page_config(page_title="IAIP · India Automotive Intelligence", page_icon="🚗", layout="wide")

HERE = Path(__file__).resolve().parent
BASE = HERE.parent                                      # ...\Desktop\IAIP  (when run on the laptop)
DEPLOY = not (BASE / "warehouse" / "gold").exists() and (HERE / "data").exists()   # True on Streamlit Cloud
WH = HERE / "data" if DEPLOY else BASE / "warehouse"
REPORTS = WH / "reports" if DEPLOY else BASE / "reports"
TEST_CSV = os.environ.get("IAIP_TEST_CSV")              # only used for testing without Parquet support

BLUE, ORANGE, GREEN, GREY, RED, PURPLE = "#1f4e79", "#d9822b", "#2e8b57", "#8c8c8c", "#c0392b", "#8e44ad"
FUEL_COLORS = {"EV": GREEN, "PETROL": ORANGE, "DIESEL": BLUE, "HYBRID": PURPLE, "GAS": "#17a2b8", "OTHER": GREY}
VT_NAMES = {"ALL": "All vehicles", "NT": "Private (Non-Transport)", "T": "Commercial (Transport)"}


# ---------------------------------------------------------------- data loading (cached: read once, reuse)
def _fix(df):
    for c in df.columns:
        if c in ("month_date",):
            df[c] = pd.to_datetime(df[c])
        elif df[c].dtype == object and set(df[c].dropna().astype(str).str.lower().unique()) <= {"true", "false"}:
            df[c] = df[c].astype(str).str.lower().eq("true")
    for c in ("year", "state_code", "cluster"):
        if c in df.columns and str(df[c].dtype) == "category":
            df[c] = df[c].astype(int if c in ("year", "cluster") else str)
    return df


@st.cache_data(show_spinner=False)
def load(name, folder="gold"):
    if TEST_CSV:
        return _fix(pd.read_csv(Path(TEST_CSV) / f"{name}.csv"))
    path = WH / folder / (f"{name}.parquet" if DEPLOY else name)   # cloud: one file per table; laptop: Spark folders
    return _fix(pd.read_parquet(path))


@st.cache_data(show_spinner=False)
def load_optional(name, folder):
    try:
        return load(name, folder)
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def state_groups():
    """KMeans groups with a plain-English name from each group's averages (robust to KMeans renumbering)."""
    g = load_optional("ml_state_groups", "gold")
    if g is None:
        return None, None
    feats = ["growth_2025_pct", "ev_share_2025_private_pct", "ev_share_2025_commercial_pct",
             "ev_share_gain_2022_2025", "two_wheeler_share_2025", "deaths_per_10k_new_reg_2023"]
    prof = g.groupby("cluster").agg(n=("state_code", "size"), **{f: (f, "mean") for f in feats},
                                    states=("state_code", lambda s: ", ".join(sorted(s)))).reset_index()
    names, left_ = {}, set(prof.cluster)
    for cl in prof[prof.n == 1].cluster:
        names[cl] = "Outlier (very small numbers)"; left_.discard(cl)
    rules = [("ev_share_2025_commercial_pct", "max", "E-rickshaw belt"), ("growth_2025_pct", "max", "Small fast-growing UTs"),
             ("ev_share_2025_private_pct", "max", "Big mainstream markets"), ("ev_share_2025_private_pct", "min", "Slow EV adopters")]
    for col, how, label in rules:
        cand = prof[prof.cluster.isin(left_)]
        if len(cand):
            cl = cand.loc[cand[col].idxmax() if how == "max" else cand[col].idxmin(), "cluster"]
            names[cl] = label; left_.discard(cl)
    for cl in left_:
        names[cl] = f"Group {cl}"
    g = g.assign(group=g.cluster.map(names))
    prof.insert(1, "group", prof.cluster.map(names))
    return g, prof


@st.cache_data(show_spinner=False)
def load_report(name):
    p = REPORTS / f"{name}.csv"
    return pd.read_csv(p) if p.exists() else None


def crore(n):
    """Indian style: 2,92,91,584 -> '2.93 crore'; 5,95,515 -> '5.96 lakh'."""
    if n is None or pd.isna(n):
        return "–"
    n = float(n)
    if abs(n) >= 1e7:
        return f"{n/1e7:.2f} crore"
    if abs(n) >= 1e5:
        return f"{n/1e5:.2f} lakh"
    return f"{n:,.0f}"


def pct(x, d=1):
    return "–" if x is None or pd.isna(x) else f"{x:.{d}f}%"


def note(text):
    st.caption(text)


# ---------------------------------------------------------------- sidebar
st.sidebar.title("🚗 IAIP")
st.sidebar.caption("India Automotive Intelligence Platform\nTeam The Quants · IISc DA 231o")
PAGES = ["🇮🇳 India overview", "⚡ EV transition", "📍 State profile", "🏭 Brands",
         "🛣️ Road safety", "🤖 ML insights", "✅ Pipeline & data quality"]
page = st.sidebar.radio("Page", PAGES, label_visibility="collapsed")

smr = load("state_month_registrations")
LAST_COMPLETE = smr.loc[~smr.is_partial_month, "month_date"].max()
LAST_MONTH = smr.month_date.max()
st.sidebar.markdown("---")
st.sidebar.caption(("☁️ Cloud copy of the Gold layer · " if DEPLOY else "💻 Live Gold layer on this laptop · ") +
                   f"Data: VAHAN (MoRTH) Jan 2020 – {LAST_MONTH:%b %Y}"
                   f"{' (latest month partial)' if smr.is_partial_month.any() else ''} · Road safety: MoRTH 2019–2023")

states = load("dim_state").sort_values("state_name")
STATE_NAMES = dict(zip(states.state_code, states.state_name))


# ================================================================ 1. INDIA OVERVIEW
if page == PAGES[0]:
    st.title("India overview")
    year_tot = (smr[(smr.state_code == "IN") & (smr.vehicle_type == "ALL")]
                .groupby("year").agg(reg=("registrations", "sum"), partial=("is_partial_month", "any")))
    full_years = year_tot[~year_tot.partial].index
    y1, y0 = full_years.max(), full_years.max() - 1
    ev = load("ev_share_state_month")
    ev_in = ev[(ev.state_code == "IN") & (ev.vehicle_type == "ALL")].groupby("year")[["ev_registrations", "total_registrations"]].sum()
    et = load("emission_transition")
    bs6 = et[(et.state_code == "IN") & (et.vehicle_type == "ALL") & (et.norm_group == "BS-VI")].set_index("year").share_pct

    c = st.columns(4)
    c[0].metric(f"New registrations {y1}", crore(year_tot.reg[y1]),
                f"{100*(year_tot.reg[y1]/year_tot.reg[y0]-1):+.1f}% vs {y0}")
    c[1].metric(f"EV share {y1}", pct(100 * ev_in.ev_registrations[y1] / ev_in.total_registrations[y1], 2),
                f"{100*(ev_in.ev_registrations[y1]/ev_in.total_registrations[y1] - ev_in.ev_registrations[y0]/ev_in.total_registrations[y0]):+.2f} pp vs {y0}")
    c[2].metric(f"BS-VI share {y1}", pct(bs6.get(y1)), "EVs have no emission norm", delta_color="off")
    c[3].metric("States & UTs covered", f"{states.shape[0]}", "every state and UT", delta_color="off")

    vt = st.radio("Vehicle type", ["ALL", "NT", "T"], format_func=VT_NAMES.get, horizontal=True)
    m = smr[(smr.state_code == "IN") & (smr.vehicle_type == vt)].sort_values("month_date")
    fig = px.line(m, x="month_date", y="registrations", markers=True,
                  title=f"Monthly new registrations · All India · {VT_NAMES[vt]}",
                  labels={"month_date": "", "registrations": "registrations"}, color_discrete_sequence=[BLUE])
    part = m[m.is_partial_month]
    if len(part):
        fig.add_scatter(x=part.month_date, y=part.registrations, mode="markers", marker=dict(color=ORANGE, size=11),
                        name="partial month (still being counted)")
    st.plotly_chart(fig, width="stretch")
    note("The 2020 dip is the COVID-19 lockdown. A partial month (orange) is the month the data was downloaded in.")

    left, right = st.columns(2)
    fm = load("fuel_mix_trend")
    f = fm[(fm.state_code == "IN") & (fm.vehicle_type == vt)]
    fig = px.bar(f, x="year", y="share_pct", color="fuel_group", color_discrete_map=FUEL_COLORS,
                 title="Fuel mix of new registrations (%)", labels={"share_pct": "%", "year": "", "fuel_group": "fuel"},
                 category_orders={"fuel_group": list(FUEL_COLORS)})
    left.plotly_chart(fig, width="stretch")
    e = et[(et.state_code == "IN") & (et.vehicle_type == vt)]
    fig = px.bar(e, x="year", y="share_pct", color="norm_group", title="Emission norm of new registrations (%)",
                 labels={"share_pct": "%", "year": "", "norm_group": "norm"},
                 color_discrete_sequence=[GREEN, BLUE, ORANGE, PURPLE, GREY, RED])
    right.plotly_chart(fig, width="stretch")
    note("BS-VI became compulsory in April 2020. Its share later dips slightly because EVs (no emission norm) are growing, "
         "not because older engines are coming back.")


# ================================================================ 2. EV TRANSITION
elif page == PAGES[1]:
    st.title("EV transition")
    ev = load("ev_share_state_month")
    vt = st.radio("Vehicle type", ["ALL", "NT", "T"], format_func=VT_NAMES.get, horizontal=True)
    y = ev[(ev.vehicle_type == vt) & (ev.state_code != "IN")].groupby(["state_code", "state_name", "year"])[
        ["ev_registrations", "total_registrations"]].sum().reset_index()
    y["ev_share_pct"] = 100 * y.ev_registrations / y.total_registrations
    years = sorted(y.year.unique())
    yr = st.select_slider("Year", options=years, value=years[-2] if len(years) > 1 else years[-1])
    min_reg = st.slider("Only states with at least this many registrations in the year", 0, 200_000, 50_000, 10_000)
    rank = y[(y.year == yr) & (y.total_registrations >= min_reg)].sort_values("ev_share_pct")
    fig = px.bar(rank, x="ev_share_pct", y="state_name", orientation="h", color="ev_share_pct",
                 color_continuous_scale="Greens", height=max(400, 22 * len(rank)),
                 title=f"EV share of new registrations by state · {yr} · {VT_NAMES[vt]}",
                 labels={"ev_share_pct": "EV share %", "state_name": ""}, hover_data={"total_registrations": ":,"})
    fig.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch")
    if vt == "T":
        note("Commercial EV share is very high in UP, Bihar, West Bengal and Assam because of battery e-rickshaws.")

    st.subheader("Monthly trend")
    default = ["IN"] + list(rank.sort_values("ev_share_pct", ascending=False).state_code.head(3))
    pick = st.multiselect("States", ["IN"] + list(states.state_code), default=default,
                          format_func=lambda s: "All India" if s == "IN" else STATE_NAMES.get(s, s))
    t = ev[(ev.vehicle_type == vt) & ev.state_code.isin(pick)].copy()
    t["state"] = t.state_code.map(lambda s: "All India" if s == "IN" else STATE_NAMES.get(s, s))
    fig = px.line(t.sort_values("month_date"), x="month_date", y="ev_share_pct", color="state",
                  labels={"month_date": "", "ev_share_pct": "EV share %"}, title=f"EV share by month · {VT_NAMES[vt]}")
    st.plotly_chart(fig, width="stretch")

    st.subheader("EV share heat map (state × year)")
    hm = y[y.total_registrations >= min_reg].pivot(index="state_name", columns="year", values="ev_share_pct")
    hm = hm.sort_values(hm.columns[-2] if hm.shape[1] > 1 else hm.columns[-1], ascending=False)
    fig = px.imshow(hm.round(1), text_auto=True, aspect="auto", color_continuous_scale="Greens",
                    labels={"x": "", "y": "", "color": "EV %"}, height=max(400, 24 * len(hm)))
    st.plotly_chart(fig, width="stretch")
    note(f"{years[-1]} is a partial year.")


# ================================================================ 3. STATE PROFILE
elif page == PAGES[2]:
    prof = load("state_profile_latest")
    code = st.selectbox("State / UT", list(states.state_code), format_func=STATE_NAMES.get,
                        index=list(states.state_code).index("UP") if "UP" in set(states.state_code) else 0)
    p = prof[prof.state_code == code].iloc[0]
    st.title(p.state_name)
    st.caption(f"{p.region} region · {'Union Territory' if p.is_union_territory else 'State'}")

    c = st.columns(5)
    c[0].metric("Registrations 2025", crore(p.reg_2025), pct(p.growth_2025_pct) + " vs 2024")
    c[1].metric("EV share 2025", pct(p.ev_share_2025_pct, 2))
    c[2].metric("EV share · private / commercial", f"{pct(p.ev_share_2025_private_pct)} / {pct(p.ev_share_2025_commercial_pct)}")
    c[3].metric("Top brand 2025", str(p.top_brand_2025), pct(p.top_brand_share_pct) + " share", delta_color="off")
    c[4].metric("Road deaths 2023", crore(p.road_deaths_2023),
                "–" if pd.isna(p.deaths_per_10k_new_reg_2023) else f"{p.deaths_per_10k_new_reg_2023:.0f} per 10k new vehicles",
                delta_color="off")

    g, _ = state_groups()
    if g is not None and code in set(g.state_code):
        st.info(f"ML state group: **{g.set_index('state_code').group[code]}** (see 🤖 ML insights for what each group means)")

    m = smr[(smr.state_code == code) & (smr.vehicle_type.isin(["NT", "T"]))].copy()
    m["type"] = m.vehicle_type.map(VT_NAMES)
    fig = px.area(m.sort_values("month_date"), x="month_date", y="registrations", color="type",
                  title="Monthly new registrations", labels={"month_date": "", "registrations": ""},
                  color_discrete_sequence=[BLUE, ORANGE])
    st.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)
    fm = load("fuel_mix_trend")
    f = fm[(fm.state_code == code) & (fm.vehicle_type == "ALL")]
    left.plotly_chart(px.bar(f, x="year", y="share_pct", color="fuel_group", color_discrete_map=FUEL_COLORS,
                             title="Fuel mix (%)", labels={"share_pct": "%", "year": "", "fuel_group": "fuel"},
                             category_orders={"fuel_group": list(FUEL_COLORS)}), width="stretch")
    cg = load("category_growth")
    g = cg[(cg.state_code == code) & (cg.vehicle_type == "ALL")]
    right.plotly_chart(px.bar(g, x="year", y="registrations", color="category_group", title="Vehicle categories",
                              labels={"registrations": "", "year": "", "category_group": "category"}),
                       width="stretch")

    mk, dm = load("fact_registration_maker_year"), load("dim_maker")
    b = (mk[(mk.state_code == code) & (mk.year == 2025)].merge(dm, on="maker_key")
         .groupby("brand").registrations.sum().sort_values(ascending=False).head(10).reset_index())
    left.plotly_chart(px.bar(b.sort_values("registrations"), x="registrations", y="brand", orientation="h",
                             title="Top 10 brands in 2025", labels={"registrations": "", "brand": ""},
                             color_discrete_sequence=[BLUE]), width="stretch")
    sp = load("state_safety_profile")
    s = sp[sp.state_code == code]
    fig = go.Figure()
    fig.add_bar(x=s.year, y=s.killed, name="road deaths", marker_color=RED)
    fig.add_scatter(x=s.year, y=s.deaths_per_10k_new_registrations, name="deaths per 10k new vehicles",
                    yaxis="y2", mode="lines+markers", line=dict(color=BLUE))
    fig.update_layout(title="Road safety", yaxis2=dict(overlaying="y", side="right", showgrid=False),
                      legend=dict(orientation="h", y=-0.2))
    right.plotly_chart(fig, width="stretch")


# ================================================================ 4. BRANDS
elif page == PAGES[3]:
    st.title("Brands")
    bs = load("brand_share_year")
    c1, c2, c3 = st.columns([2, 2, 1])
    vt = c1.radio("Vehicle type", ["ALL", "NT", "T"], format_func=VT_NAMES.get, horizontal=True)
    yr = c2.select_slider("Year", options=sorted(bs.year.unique()), value=2025)
    hide_tail = c3.checkbox("Hide long tail", value=True)
    d = bs[(bs.vehicle_type == vt) & (bs.year == yr)]
    if hide_tail:
        d = d[~d.brand.str.contains("long tail", case=False)]
    top = d.sort_values("registrations", ascending=False).head(15)
    fig = px.bar(top.sort_values("registrations"), x="share_pct", y="brand", orientation="h", text="share_pct",
                 title=f"Top 15 brands · {yr} · {VT_NAMES[vt]} (% of all registrations)",
                 labels={"share_pct": "share %", "brand": ""}, color_discrete_sequence=[BLUE], height=520)
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    st.plotly_chart(fig, width="stretch")

    top8 = list(bs[(bs.vehicle_type == vt) & (bs.year == 2025) & ~bs.brand.str.contains("long tail", case=False)]
                .sort_values("registrations", ascending=False).brand.head(8))
    t = bs[(bs.vehicle_type == vt) & bs.brand.isin(top8)]
    st.plotly_chart(px.line(t, x="year", y="share_pct", color="brand", markers=True,
                            title="Market share over time · top 8 brands of 2025", labels={"share_pct": "share %", "year": ""}),
                    width="stretch")
    note("Maker names in VAHAN are mapped to brands with 55 rules; they cover 97.3% of registrations. "
         f"{bs.year.max()} is a partial year.")


# ================================================================ 5. ROAD SAFETY
elif page == PAGES[4]:
    st.title("Road safety vs new vehicles")
    sp = load("state_safety_profile")
    yr = st.select_slider("Year", options=sorted(sp.year.unique()), value=sp.year.max())
    metric = st.radio("Measure", ["deaths_per_10k_new_registrations", "deaths_per_100_accidents", "killed"],
                      format_func={"deaths_per_10k_new_registrations": "Deaths per 10,000 new vehicles",
                                   "deaths_per_100_accidents": "Deaths per 100 accidents (severity)",
                                   "killed": "Road deaths"}.get, horizontal=True)
    d = sp[(sp.year == yr) & (sp.new_registrations >= 10_000)].sort_values(metric)
    fig = px.bar(d, x=metric, y="state_name", orientation="h", color=metric, color_continuous_scale="Reds",
                 height=max(400, 22 * len(d)), labels={metric: "", "state_name": ""},
                 hover_data={"killed": ":,", "accidents": ":,", "new_registrations": ":,"})
    fig.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch")

    st.subheader("More vehicles, more deaths?")
    fig = px.scatter(d, x="new_registrations", y="killed", size="accidents", color="region", hover_name="state_name",
                     log_x=True, labels={"new_registrations": "new registrations (log scale)", "killed": "road deaths"})
    st.plotly_chart(fig, width="stretch")
    note("Road-safety data (MoRTH) ends in 2023. VAHAN gives new registrations, not all vehicles on the road, so "
         "'deaths per 10,000 new vehicles' is a proxy. J&K includes Ladakh in 2019–2020. States with fewer than "
         "10,000 new registrations are hidden.")


# ================================================================ 6. ML INSIGHTS
elif page == PAGES[5]:
    st.title("ML insights (Spark MLlib)")
    cmpr, test, fut = load("ml_model_comparison"), load("ml_ev_forecast_test"), load("ml_ev_forecast_future")
    ev = load("ev_share_state_month")
    chosen = cmpr[cmpr.chosen_on_validation].iloc[0]
    b12 = cmpr[cmpr.model.str.contains("same month")].iloc[0]
    b1 = cmpr[cmpr.model.str.contains("last month")].iloc[0]

    st.subheader("A · Next-month EV-share forecast")
    c = st.columns(3)
    c[0].metric("Chosen model (on 2025 validation)", chosen.model)
    c[1].metric("2026 test error (RMSE)", f"{chosen.rmse:.2f} pp", f"{100*(1-chosen.rmse/b12.rmse):.0f}% better than same-month-last-year")
    c[2].metric("vs 'last month' guess", f"{b1.rmse:.2f} pp", f"{100*(1-chosen.rmse/b1.rmse):.0f}% better")

    opts = ["IN"] + sorted(test.state_code.unique())
    code = st.selectbox("Series", opts, format_func=lambda s: "All India (weighted)" if s == "IN" else STATE_NAMES.get(s, s))
    vt = st.radio("Vehicle type ", ["NT", "T"], format_func=VT_NAMES.get, horizontal=True)
    if code == "IN":
        a = ev[(ev.state_code == "IN") & (ev.vehicle_type == vt) & ~ev.is_partial_month & (ev.year >= 2023)]
        a = a.rename(columns={"ev_share_pct": "share"})[["month_date", "share"]]
        t = test[test.vehicle_type == vt].assign(w=lambda x: x.total_registrations)
        t = (t.assign(p=t.predicted_ev_share * t.w, b=t.baseline_same_month_last_year * t.w).groupby("month_date")
              .agg(p=("p", "sum"), b=("b", "sum"), w=("w", "sum")).reset_index())
        t["pred"], t["base"] = t.p / t.w, t.b / t.w
        w = ev[(ev.vehicle_type == vt) & (ev.state_code != "IN") & (ev.year == 2025)][["state_code", "month", "total_registrations"]]
        f = fut[fut.vehicle_type == vt].assign(month=lambda x: x.month_date.dt.month).merge(w, on=["state_code", "month"])
        f = (f.assign(p=f.forecast_ev_share * f.total_registrations).groupby("month_date")
              .agg(p=("p", "sum"), w=("total_registrations", "sum")).reset_index())
        f["fc"] = f.p / f.w
    else:
        a = ev[(ev.state_code == code) & (ev.vehicle_type == vt) & ~ev.is_partial_month & (ev.year >= 2023)]
        a = a.rename(columns={"ev_share_pct": "share"})[["month_date", "share"]]
        t = test[(test.state_code == code) & (test.vehicle_type == vt)].rename(
            columns={"predicted_ev_share": "pred", "baseline_same_month_last_year": "base"})
        f = fut[(fut.state_code == code) & (fut.vehicle_type == vt)].rename(columns={"forecast_ev_share": "fc"})
    fig = go.Figure()
    fig.add_scatter(x=a.month_date, y=a.share, name="actual", line=dict(color=BLUE, width=3))
    fig.add_scatter(x=t.month_date, y=t.pred, name=f"model on 2026 test", mode="lines+markers", line=dict(color=ORANGE))
    fig.add_scatter(x=t.month_date, y=t.base, name="baseline: same month last year", line=dict(color=GREY, dash="dot"))
    fig.add_scatter(x=f.month_date, y=f.fc, name="forecast (next 3 months)", mode="lines+markers",
                    line=dict(color=ORANGE, dash="dash"))
    fig.update_layout(title=f"EV share % · {VT_NAMES[vt]}", yaxis_title="%", legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig, width="stretch")
    with st.expander("All models compared on 2026 (lower RMSE is better)"):
        st.dataframe(cmpr[["model", "settings", "rmse", "mae", "r2", "chosen_on_validation"]], hide_index=True,
                     width="stretch")
        note("Linear regression wins because 2026 EV shares are higher than anything in the training years: "
             "tree models cannot predict beyond the range they have seen, a straight-line model can follow the trend.")

    st.subheader("B · State groups (KMeans)")
    g, prof = state_groups()
    feats = ["growth_2025_pct", "ev_share_2025_private_pct", "ev_share_2025_commercial_pct",
             "ev_share_gain_2022_2025", "two_wheeler_share_2025", "deaths_per_10k_new_reg_2023"]
    fig = px.scatter(g, x="pc1", y="pc2", color="group", text="state_code", hover_name="state_name",
                     hover_data={c: ":.1f" for c in feats} | {"pc1": False, "pc2": False}, height=520,
                     labels={"pc1": "component 1", "pc2": "component 2"},
                     title=f"{g.state_code.nunique()} states/UTs in {g.cluster.nunique()} groups (7 features, PCA view)")
    fig.update_traces(textposition="top center", marker=dict(size=12))
    st.plotly_chart(fig, width="stretch")
    st.dataframe(prof.drop(columns="cluster").round(1), hide_index=True, width="stretch")


# ================================================================ 7. PIPELINE & DATA QUALITY
elif page == PAGES[6]:
    st.title("Pipeline & data quality")
    st.markdown("""
**VAHAN + MoRTH files → Bronze** (raw, all text, lineage) **→ Silver** (cleaned, checked, mapped)
**→ Gold** (star schema + Spark SQL views) **→ this dashboard / Power BI** · monthly refresh via **Kafka → Spark Structured Streaming**
""")
    sq, gq = load_optional("_quality_report", "silver"), load_optional("_gold_checks", "gold")
    sc, lg = load_optional("_stream_checks", "stream"), load_optional("_stream_log", "stream")
    e3, e1 = load_report("e3_quality_test"), load_report("e1_scalability")

    c = st.columns(4)
    if sq is not None:
        c[0].metric("Silver checks", f"{int(sq.passed.sum())} / {len(sq)} passed")
    if gq is not None:
        c[1].metric("Gold checks", f"{int(gq.passed.sum())} / {len(gq)} passed")
    if sc is not None:
        c[2].metric("Streaming checks", f"{int(sc.passed.sum())} / {len(sc)} passed")
    if e3 is not None:
        c[3].metric("E3 · injected errors caught", f"{int(e3.caught.sum())} / {int(e3.injected.sum())}",
                    f"{100*e3.caught.sum()/e3.injected.sum():.0f}% (target 90%)")

    tabs = st.tabs(["E3 · bad-data test", "E1 · scalability", "E2 · Kafka refresh log", "Silver checks", "Gold checks"])
    with tabs[0]:
        if e3 is not None:
            fig = px.bar(e3, x="caught_pct", y="err_type", orientation="h", range_x=[0, 100], text="caught_pct",
                         labels={"caught_pct": "% caught", "err_type": ""}, color_discrete_sequence=[GREEN])
            fig.add_vline(x=90, line_dash="dash", line_color=GREY, annotation_text="target 90%")
            st.plotly_chart(fig, width="stretch")
            st.dataframe(e3, hide_index=True, width="stretch")
    with tabs[1]:
        if e1 is not None:
            l, r = st.columns(2)
            s = e1[e1.test == "data size"]
            l.plotly_chart(px.line(s, x="rows", y="seconds", markers=True, title="Data size (all cores)",
                                   labels={"rows": "rows processed", "seconds": "seconds"}), width="stretch")
            k = e1[e1.test == "cores"]
            fig = px.line(k, x="cores", y="speedup", markers=True, title="Speed-up vs 1 core", text="seconds")
            fig.add_scatter(x=k.cores, y=k.cores, name="ideal", line=dict(dash="dash", color=GREY))
            fig.update_traces(texttemplate="%{text:.0f}s", textposition="top left", selector=dict(mode="lines+markers+text"))
            r.plotly_chart(fig, width="stretch")
            st.dataframe(e1, hide_index=True, width="stretch")
    with tabs[2]:
        if lg is not None:
            st.dataframe(lg.sort_values("batch_id", ascending=False), hide_index=True, width="stretch")
            upd = lg[lg.gold_updated]
            if len(upd):
                st.metric("Kafka → Gold latency when Gold changes", f"{upd.latency_s.mean():.1f} s (average)")
    with tabs[3]:
        if sq is not None:
            st.dataframe(sq, hide_index=True, width="stretch")
    with tabs[4]:
        if gq is not None:
            st.dataframe(gq, hide_index=True, width="stretch")


# ---------------------------------------------------------------- E5: how long did this page take?
elapsed = time.perf_counter() - T_START
st.sidebar.markdown("---")
st.sidebar.metric("⏱️ Page rendered in", f"{elapsed:.2f} s", "target < 3 s" + (" ✓" if elapsed < 3 else " ✗"),
                  delta_color="normal" if elapsed < 3 else "inverse")
