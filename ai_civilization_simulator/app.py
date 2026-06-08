import io
import json
import zipfile

import pandas as pd
import streamlit as st

from config.settings import WORLD_WIDTH, WORLD_HEIGHT, DEFAULT_CIVILIZATIONS, RANDOM_SEED
from world.map_generator import WorldMap
from civilizations.factory import create_civilizations
from simulation.engine import SimulationEngine
from visuals.charts import world_map_figure, line_chart, bar_chart, multi_line_chart, pie_chart

st.set_page_config(page_title="AI Civilization Simulator", layout="wide")

st.title("AI Civilization Simulator")
st.caption(
    "Phase 12 — Professional Packaging & Strategic Map Overhaul: exportable reports, scenario controls, strategic map views, stable replayability, "
    "clearer map intelligence, exportable reports, scenario framing and GitHub-ready packaging."
)

st.markdown("""
<style>
    .stApp {background: linear-gradient(180deg, #F7F1E6 0%, #EEE3D1 100%); color: #263238;}
    h1, h2, h3 {letter-spacing: -0.02em; color: #24313A;}
    [data-testid="stMetric"] {background: linear-gradient(145deg, #FFFDF7, #F4E9D7); border: 1px solid rgba(120,83,45,0.18); border-radius: 14px; padding: 14px; box-shadow: 0 8px 22px rgba(75,53,35,0.10);}
    [data-testid="stMetricLabel"] {color: #6A5A48 !important;}
    [data-testid="stMetricValue"] {color: #2F3B44 !important;}
    .stTabs [data-baseweb="tab-list"] {gap: 8px; background: rgba(255,253,247,0.80); border-radius: 14px; padding: 8px; border: 1px solid rgba(120,83,45,0.12);}
    .stTabs [data-baseweb="tab"] {background: rgba(246,238,222,0.95); border-radius: 10px; padding: 8px 14px; border: 1px solid rgba(120,83,45,0.10); color: #40352B;}
    .stTabs [aria-selected="true"] {border-color: rgba(184,131,47,0.80); color: #8A5D1D; background: #FFF8E8;}
    .block-container {padding-top: 1.2rem; max-width: 1600px;}
    .strategy-card {background: linear-gradient(145deg, #FFFDF7, #F6EBD9); border: 1px solid rgba(120,83,45,0.14); border-radius: 16px; padding: 16px 18px; box-shadow: 0 10px 26px rgba(75,53,35,0.10); margin-bottom: 14px;}
    .gold-title {color: #9A681F; font-weight: 700; letter-spacing: 0.02em;}
    .news-item {border-left: 3px solid #B8832F; padding: 8px 12px; margin: 8px 0; background: rgba(255,253,247,0.82); border-radius: 8px;}
    .danger {border-left-color: #C94C4C;}
    .success {border-left-color: #4F9F5B;}
    .info {border-left-color: #4D8DB3;}
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------
def pct_change_from_history(df: pd.DataFrame, column: str, periods: int = 20) -> float:
    if df.empty or column not in df.columns or len(df) <= periods:
        return 0.0
    old = float(df[column].iloc[-periods - 1])
    new = float(df[column].iloc[-1])
    if old == 0:
        return 0.0
    return ((new - old) / abs(old)) * 100


def abs_change_from_history(df: pd.DataFrame, column: str, periods: int = 20) -> float:
    if df.empty or column not in df.columns or len(df) <= periods:
        return 0.0
    return float(df[column].iloc[-1]) - float(df[column].iloc[-periods - 1])


def risk_label(value: float) -> str:
    if value >= 70:
        return "High"
    if value >= 40:
        return "Medium"
    return "Low"


def stability_label(value: float) -> str:
    if value >= 75:
        return "Stable"
    if value >= 50:
        return "Fragile"
    return "Unstable"


def format_signed(value: float, suffix: str = "%") -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}{suffix}"


def classify_event(event_text: str) -> str:
    text = str(event_text).lower()
    if any(word in text for word in ["war", "rival", "alliance", "treaty", "geopolitical"]):
        return "Geopolitics"
    if any(word in text for word in ["price", "export", "deficit", "surplus", "market", "trade"]):
        return "Economy"
    if any(word in text for word in ["religion", "faith", "temple", "cult"]):
        return "Religion"
    if any(word in text for word in ["technology", "metallurgy", "writing", "engineering"]):
        return "Technology"
    if any(word in text for word in ["crisis", "revolt", "instability", "famine"]):
        return "Crisis"
    return "General"


def build_world_summary(civ_df, history_df, market_df, market_history_df, religion_df, tech_df, war_df, crisis_df):
    latest = history_df.iloc[-1]
    latest_market = market_history_df.iloc[-1]

    dominant_empire = civ_df.iloc[0]
    richest_empire = civ_df.sort_values("GDP", ascending=False).iloc[0]
    strongest_army = civ_df.sort_values("Military", ascending=False).iloc[0]
    most_advanced = tech_df.sort_values("Technology Level", ascending=False).iloc[0] if not tech_df.empty else dominant_empire
    most_religious = religion_df.sort_values("Faith Influence", ascending=False).iloc[0] if not religion_df.empty else dominant_empire

    commodity_change = pct_change_from_history(market_history_df, "commodity_index", 30)
    gdp_growth = pct_change_from_history(history_df, "world_gdp", 30)
    pop_growth = pct_change_from_history(history_df, "world_population", 30)
    stability = float(latest.get("avg_stability", 0))
    war_risk = float(latest.get("war_risk_index", 0))
    crisis_count = len(crisis_df) if crisis_df is not None else 0
    active_wars = len(war_df) if war_df is not None else 0

    if active_wars > 0:
        major_event = f"{active_wars} active conflict(s) are shaping the geopolitical order."
    elif crisis_count > 0:
        major_event = f"{crisis_count} active crisis/revolt event(s) are weakening internal stability."
    elif commodity_change > 5:
        major_event = "Commodity markets are heating up, suggesting pressure on strategic resources."
    elif gdp_growth > 5:
        major_event = "The world economy is expanding strongly."
    else:
        major_event = "The world is relatively calm, but power balances continue to shift."

    return {
        "year": int(latest["year"]),
        "dominant_empire": dominant_empire["Civilization"],
        "dominant_score": dominant_empire["Power Score"],
        "richest_empire": richest_empire["Civilization"],
        "strongest_army": strongest_army["Civilization"],
        "tech_leader": most_advanced["Civilization"],
        "largest_religion": most_religious.get("Religion", "Unknown"),
        "religion_center": most_religious["Civilization"],
        "world_gdp": latest["world_gdp"],
        "gdp_growth": gdp_growth,
        "population": latest["world_population"],
        "population_growth": pop_growth,
        "commodity_index": latest_market["commodity_index"],
        "commodity_change": commodity_change,
        "war_risk": war_risk,
        "war_label": risk_label(war_risk),
        "stability": stability,
        "stability_label": stability_label(stability),
        "active_wars": active_wars,
        "active_crises": crisis_count,
        "major_event": major_event,
        "inflation_proxy": market_df["Price Change %"].mean() if "Price Change %" in market_df.columns else 0,
    }



def build_historical_chronicle(summary, events_df, civ_df):
    dominant = summary["dominant_empire"]
    tech = summary["tech_leader"]
    religion = summary["largest_religion"]
    war_state = "a tense geopolitical age" if summary["active_wars"] else "a comparatively stable age"
    crisis_state = "internal revolts and crises are weakening several states" if summary["active_crises"] else "internal order remains broadly preserved"
    recent = events_df.sort_values("year", ascending=False).head(6) if not events_df.empty else pd.DataFrame()
    recent_lines = []
    for _, row in recent.iterrows():
        recent_lines.append(f"- Year {int(row['year'])}: {row['event']}")
    recent_text = "\n".join(recent_lines) if recent_lines else "- No major event has been recorded yet."
    return f"""
In year {summary['year']}, the world is dominated by **{dominant}**, while **{tech}** leads the technological race and **{religion}** remains the most influential faith. The global order is currently marked by **{war_state}**: geopolitical risk stands at **{summary['war_risk']:.1f}/100**, while world stability is assessed at **{summary['stability']:.1f}/100**. Economically, the world GDP reaches **{summary['world_gdp']:,.0f}**, with a recent growth signal of **{summary['gdp_growth']:.1f}%** and a commodity index at **{summary['commodity_index']:.1f}**.

The historical direction is clear: {crisis_state}. Power is not only determined by armies; trade balance, technological leadership, religious influence and resource pressure now shape the destiny of each civilization.

**Recent historical records**
{recent_text}
""".strip()


def build_civilization_biography(profile):
    status = "an expansionist power" if profile["Territory"] > 100 else "a compact but ambitious state"
    risk = "politically fragile" if profile["Stability"] < 60 else "politically stable"
    military = "militarized" if profile["Military"] > profile["GDP"] * 0.10 else "economically oriented"
    return f"""
**{profile['Civilization']}** is {status}, led by **{profile['Leader']}**. Its political culture is shaped by a **{profile['Personality']}** strategic identity, while its dominant religion is **{profile['Religion']}**.

The civilization currently controls **{int(profile['Territory'])} territories**, with a GDP of **{profile['GDP']:,.0f}**, a military strength of **{profile['Military']:,.0f}**, and a technology level of **{profile['Technology']:.1f}**. It is considered **{risk}** with a stability score of **{profile['Stability']:.1f}/100**. Its economy is mainly exposed to **{profile['Main Import']}** imports and relies on **{profile['Main Export']}** exports.

Strategically, {profile['Civilization']} appears **{military}**, with a total power score of **{profile['Power Score']:.1f}**. Its long-term survival depends on maintaining internal stability while protecting access to strategic resources.
""".strip()


def build_war_story(war_df):
    if war_df.empty:
        return "No active war is currently recorded. The world is not peaceful forever, but no major open conflict dominates the present year."
    lines = []
    for _, row in war_df.head(5).iterrows():
        attacker = row.get("Civilization A", row.get("Attacker", "A power"))
        defender = row.get("Civilization B", row.get("Defender", "a rival"))
        cause = row.get("Cause", "strategic pressure")
        intensity = row.get("Intensity", 0)
        lines.append(
            f"**{attacker} vs {defender}** — This conflict is driven by **{cause}**. "
            f"With an intensity score of **{float(intensity):.1f}**, it is reshaping local power balances and may influence commodity markets."
        )
    return "\n\n".join(lines)


def build_century_summary(events_df, history_df):
    if history_df.empty:
        return pd.DataFrame()
    df = history_df.copy()
    df["Century"] = (df["year"] // 100) * 100
    rows = []
    for century, group in df.groupby("Century"):
        first = group.iloc[0]
        last = group.iloc[-1]
        gdp_change = ((last["world_gdp"] - first["world_gdp"]) / max(abs(first["world_gdp"]), 1)) * 100
        pop_change = ((last["world_population"] - first["world_population"]) / max(abs(first["world_population"]), 1)) * 100
        avg_wars = group["active_wars"].mean() if "active_wars" in group else 0
        avg_risk = group["war_risk_index"].mean() if "war_risk_index" in group else 0
        era_events = events_df[(events_df["year"] >= century) & (events_df["year"] < century + 100)] if not events_df.empty else pd.DataFrame()
        key_event = era_events.sort_values("year", ascending=False).iloc[0]["event"] if not era_events.empty else "No major event recorded."
        rows.append({
            "Era": f"Years {int(century)}-{int(century+99)}",
            "GDP Change %": round(gdp_change, 1),
            "Population Change %": round(pop_change, 1),
            "Average Wars": round(avg_wars, 2),
            "Average Risk": round(avg_risk, 1),
            "Key Event": key_event,
        })
    return pd.DataFrame(rows)

def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    if df is None or df.empty:
        return b""
    return df.to_csv(index=False).encode("utf-8")


def build_export_zip(dataframes: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        metadata = {
            "project": "AI Civilization Simulator",
            "phase": "Phase 10 — World Intelligence & Analytics Engine",
            "description": "Exported simulation data package generated from Streamlit.",
            "files": []
        }
        for name, df in dataframes.items():
            if df is not None and not df.empty:
                filename = f"{name}.csv"
                zf.writestr(filename, df.to_csv(index=False))
                metadata["files"].append(filename)
        zf.writestr("simulation_metadata.json", json.dumps(metadata, indent=2))
    buffer.seek(0)
    return buffer.getvalue()


def safe_corr(df: pd.DataFrame, a: str, b: str) -> float:
    if df is None or df.empty or a not in df.columns or b not in df.columns:
        return 0.0
    try:
        return float(df[[a, b]].corr().iloc[0, 1])
    except Exception:
        return 0.0


def add_power_columns(civ_df: pd.DataFrame) -> pd.DataFrame:
    df = civ_df.copy()
    df["Economic Weight"] = df["GDP"] / df["GDP"].sum() * 100 if df["GDP"].sum() else 0
    df["Military Weight"] = df["Military"] / df["Military"].sum() * 100 if df["Military"].sum() else 0
    df["Status"] = df.apply(
        lambda r: "At War" if r.get("At War") == "Yes" else ("Fragile" if r.get("Stability", 100) < 55 else "Stable"),
        axis=1,
    )
    return df


def explain_event(row, civ_df: pd.DataFrame, market_df: pd.DataFrame, war_df: pd.DataFrame) -> str:
    """Turn a raw log line into a short analytical explanation."""
    event = str(row.get("event", ""))
    category = str(row.get("Category", classify_event(event)))
    civ_name = str(row.get("civilization", ""))
    year = int(row.get("year", 0))
    text = event.lower()

    reason = "The event reflects the current balance of power, resources and internal stability."
    impact = "It may affect the future distribution of wealth, security and influence."

    if category == "Geopolitics" or "war" in text:
        if not war_df.empty:
            cause = war_df.iloc[0].get("Cause", "strategic resource pressure")
            intensity = war_df.iloc[0].get("Intensity", 0)
            reason = f"The conflict is mainly linked to {cause}. The recorded war intensity is {float(intensity):.1f}/100."
        else:
            reason = "The event comes from worsening diplomatic relations, rivalries or resource competition."
        impact = "Wars usually increase military demand, pressure iron markets and reduce global stability."
    elif category == "Economy" or "price" in text or "market" in text:
        if not market_df.empty:
            pressure = market_df.sort_values("Price Change %", ascending=False).iloc[0]
            reason = f"The strongest market pressure currently comes from {pressure['Resource']}: price change {float(pressure['Price Change %']):.1f}% with a supply-demand balance of {float(pressure['Surplus / Deficit']):.1f}."
        else:
            reason = "The event is linked to changes in production, consumption or trade balance."
        impact = "Commodity shocks can redistribute wealth toward exporters and weaken import-dependent civilizations."
    elif category == "Religion":
        reason = "Religious influence grows when faith investment, stability and population reinforce the same belief system."
        impact = "Religious concentration can create cohesion, but rival faiths may later increase internal tension or conflict."
    elif category == "Technology":
        reason = "Technological leadership is driven by wealth, knowledge accumulation and long-term stability."
        impact = "Tech leaders usually gain higher productivity, stronger armies and better long-term economic performance."
    elif category == "Crisis":
        if civ_name in set(civ_df["Civilization"]):
            c = civ_df[civ_df["Civilization"] == civ_name].iloc[0]
            reason = f"{civ_name} has a stability score of {float(c['Stability']):.1f}/100, which increases revolt and crisis probability."
        else:
            reason = "The crisis is linked to instability, economic stress or resource shortages."
        impact = "Crises reduce confidence, weaken growth and can stop an empire from remaining dominant."

    return f"Year {year} — {event}\n\nWhy it happened: {reason}\n\nExpected impact: {impact}"


def commodity_volatility_table(market_history_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for resource in ["food", "wood", "stone", "iron", "gold"]:
        col = f"{resource}_price"
        if col in market_history_df.columns and len(market_history_df) > 2:
            returns = market_history_df[col].pct_change().dropna()
            rows.append({
                "Resource": resource.title(),
                "Volatility %": round(float(returns.std() * 100), 2),
                "Last Price": round(float(market_history_df[col].iloc[-1]), 2),
                "Total Change %": round(((float(market_history_df[col].iloc[-1]) / max(float(market_history_df[col].iloc[0]), 0.0001)) - 1) * 100, 1),
            })
    return pd.DataFrame(rows).sort_values("Volatility %", ascending=False) if rows else pd.DataFrame()


def build_final_simulation_report(summary, events_df, civ_df, history_df, market_history_df, war_df, crisis_df) -> str:
    winner = civ_df.sort_values("Power Score", ascending=False).iloc[0]
    richest = civ_df.sort_values("GDP", ascending=False).iloc[0]
    tech = civ_df.sort_values("Technology", ascending=False).iloc[0]
    stable = civ_df.sort_values("Stability", ascending=False).iloc[0]
    gdp_growth = pct_change_from_history(history_df, "world_gdp", min(100, max(1, len(history_df)-2)))
    commodity_change = pct_change_from_history(market_history_df, "commodity_index", min(100, max(1, len(market_history_df)-2)))
    major_events = events_df.sort_values("year", ascending=False).head(8) if not events_df.empty else pd.DataFrame()
    event_lines = "\n".join([f"- Year {int(r['year'])}: {r['event']}" for _, r in major_events.iterrows()]) if not major_events.empty else "- No major event recorded."

    victory_reason = []
    if winner["GDP"] >= civ_df["GDP"].quantile(0.75):
        victory_reason.append("economic scale")
    if winner["Military"] >= civ_df["Military"].quantile(0.75):
        victory_reason.append("military strength")
    if winner["Technology"] >= civ_df["Technology"].quantile(0.75):
        victory_reason.append("technological advantage")
    if winner["Stability"] >= civ_df["Stability"].quantile(0.60):
        victory_reason.append("political stability")
    if not victory_reason:
        victory_reason.append("balanced development across multiple dimensions")

    risk_sentence = "The world ended in a high-risk configuration." if summary["war_risk"] >= 60 else "The world ended in a relatively manageable geopolitical configuration."
    crisis_sentence = f"{len(crisis_df)} active crisis event(s) remained unresolved." if not crisis_df.empty else "No major active crisis remained at the end of the run."

    return f"""
### Executive Summary
After **{summary['year']} simulated years**, **{winner['Civilization']}** emerges as the leading civilization with a Power Score of **{float(winner['Power Score']):.1f}**. Its rise is mainly explained by **{', '.join(victory_reason)}**.

### Winner and Key Drivers
- **Final winner:** {winner['Civilization']}
- **Richest economy:** {richest['Civilization']} — GDP {float(richest['GDP']):,.0f}
- **Technology leader:** {tech['Civilization']} — Technology {float(tech['Technology']):.1f}
- **Most stable state:** {stable['Civilization']} — Stability {float(stable['Stability']):.1f}/100

### Macro Outcome
- **World GDP:** {summary['world_gdp']:,.0f}
- **Long-run GDP change:** {gdp_growth:.1f}%
- **Commodity index change:** {commodity_change:.1f}%
- **Final war risk:** {summary['war_risk']:.1f}/100
- **Final stability:** {summary['stability']:.1f}/100

### Risk Assessment
{risk_sentence} {crisis_sentence}

### Major Historical Events
{event_lines}

### Interpretation
This simulation was not decided by a single variable. The final balance of power came from the interaction between territorial expansion, resource access, commodity markets, wars, technology, religion, internal stability and modern development systems.
""".strip()


# -----------------------------------------------------------------------------
# Simulation runner
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("Simulation Controls")
    st.caption("Use a fixed seed to replay the same world, or generate a new random world for a completely different simulation.")
    scenario = st.selectbox("Scenario", ["Balanced World", "Resource Crisis", "Religious Tension", "Industrial Race", "Modern Space Race"], help="Scenario framing helps you read each run like a strategic case study. The simulation remains seed-driven.")
    difficulty = st.selectbox("Volatility mode", ["Peaceful", "Balanced", "Chaotic", "Hardcore"], index=1, help="Use this as an interpretation layer for how risky you want the run to feel.")
    if "current_seed" not in st.session_state:
        st.session_state.current_seed = RANDOM_SEED
    random_button = st.button("Generate New Random World", type="primary")
    if random_button:
        import random as _random
        st.session_state.current_seed = _random.randint(1, 999999)
        st.cache_data.clear()
    seed = st.number_input("World seed", min_value=1, max_value=999999, value=int(st.session_state.current_seed), step=1)
    if seed != st.session_state.current_seed:
        st.session_state.current_seed = int(seed)
    civ_count = st.slider("Civilizations", 3, 12, DEFAULT_CIVILIZATIONS)
    years = st.slider("Years to simulate", 1, 1200, 500)
    st.caption("Tip: higher years generate deeper history; new seeds change geography, resources, personalities and winners.")
    run_button = st.button("Run Selected Seed")


@st.cache_data(show_spinner=False)
def run_simulation(seed: int, civ_count: int, years: int):
    world = WorldMap(WORLD_WIDTH, WORLD_HEIGHT, seed=seed)
    civs = create_civilizations(world, civ_count, seed=seed)
    engine = SimulationEngine(world, civs)
    engine.run(years)
    return (
        world,
        civs,
        engine.civilization_dataframe(),
        engine.history_dataframe(),
        engine.events_dataframe(),
        engine.market_dataframe(),
        engine.market_history_dataframe(),
        engine.trade_dataframe(),
        engine.diplomacy_dataframe(),
        engine.war_dataframe(),
        engine.technology_dataframe(),
        engine.religion_dataframe(),
        engine.leader_dataframe(),
        engine.crisis_dataframe(),
        engine.weather_dataframe(),
        engine.disaster_dataframe(),
        engine.company_dataframe(),
        engine.financial_dataframe(),
        engine.central_bank_dataframe(),
        engine.phase_dataframe(),
    )


if random_button or run_button or "simulation_loaded" not in st.session_state:
    st.session_state.simulation_loaded = True
    result = run_simulation(seed, civ_count, years)
    (
        world,
        civs,
        civ_df,
        history_df,
        events_df,
        market_df,
        market_history_df,
        trade_df,
        diplomacy_df,
        war_df,
        tech_df,
        religion_df,
        leader_df,
        crisis_df,
        weather_df,
        disaster_df,
        company_df,
        financial_df,
        central_bank_df,
        phase_df,
    ) = result
    st.session_state.world = world
    st.session_state.civs = civs
    st.session_state.civ_df = civ_df
    st.session_state.history_df = history_df
    st.session_state.events_df = events_df
    st.session_state.market_df = market_df
    st.session_state.market_history_df = market_history_df
    st.session_state.trade_df = trade_df
    st.session_state.diplomacy_df = diplomacy_df
    st.session_state.war_df = war_df
    st.session_state.tech_df = tech_df
    st.session_state.religion_df = religion_df
    st.session_state.leader_df = leader_df
    st.session_state.crisis_df = crisis_df
    st.session_state.weather_df = weather_df
    st.session_state.disaster_df = disaster_df
    st.session_state.company_df = company_df
    st.session_state.financial_df = financial_df
    st.session_state.central_bank_df = central_bank_df
    st.session_state.phase_df = phase_df
else:
    world = st.session_state.world
    civs = st.session_state.civs
    civ_df = st.session_state.civ_df
    history_df = st.session_state.history_df
    events_df = st.session_state.events_df
    market_df = st.session_state.market_df
    market_history_df = st.session_state.market_history_df
    trade_df = st.session_state.trade_df
    diplomacy_df = st.session_state.diplomacy_df
    war_df = st.session_state.war_df
    tech_df = st.session_state.tech_df
    religion_df = st.session_state.religion_df
    leader_df = st.session_state.leader_df
    crisis_df = st.session_state.crisis_df
    weather_df = st.session_state.weather_df
    disaster_df = st.session_state.disaster_df
    company_df = st.session_state.company_df
    financial_df = st.session_state.financial_df
    central_bank_df = st.session_state.central_bank_df
    phase_df = st.session_state.phase_df

civ_df = add_power_columns(civ_df)
market_df = market_df.copy()
if not market_df.empty:
    for col in ["Supply", "Demand", "Surplus / Deficit", "Price", "Price Change %"]:
        if col in market_df.columns:
            market_df[col] = market_df[col].round(2)
    market_df["Trend"] = market_df["Price Change %"].apply(
        lambda x: "Rising" if x > 0.5 else ("Falling" if x < -0.5 else "Stable")
    )
    market_df["Pressure"] = market_df["Surplus / Deficit"].apply(
        lambda x: "Shortage" if x < 0 else ("Balanced" if x < 100 else "Surplus")
    )

if not events_df.empty:
    events_df = events_df.copy()
    events_df["Category"] = events_df["event"].apply(classify_event)

summary = build_world_summary(civ_df, history_df, market_df, market_history_df, religion_df, tech_df, war_df, crisis_df)
latest = history_df.iloc[-1]
latest_market = market_history_df.iloc[-1]

# -----------------------------------------------------------------------------
# Premium top-level dashboard
# -----------------------------------------------------------------------------
st.markdown("## World Situation Report")
report_left, report_mid, report_right = st.columns([1.2, 1, 1])
with report_left:
    st.markdown(
        f"""
        **Year {summary['year']}**  
        **Dominant power:** {summary['dominant_empire']} — Power Score {summary['dominant_score']:.1f}  
        **Main world signal:** {summary['major_event']}
        """
    )
with report_mid:
    st.markdown(
        f"""
        **Tech leader:** {summary['tech_leader']}  
        **Largest religion:** {summary['largest_religion']}  
        **Religious center:** {summary['religion_center']}
        """
    )
with report_right:
    st.markdown(
        f"""
        **World stability:** {summary['stability_label']} ({summary['stability']:.1f}/100)  
        **Geopolitical risk:** {summary['war_label']} ({summary['war_risk']:.1f}/100)  
        **Active wars/crises:** {summary['active_wars']} / {summary['active_crises']}
        """
    )

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("World GDP", f"{summary['world_gdp']:,.0f}", format_signed(summary["gdp_growth"]))
m2.metric("Population", f"{summary['population']:,.0f}", format_signed(summary["population_growth"]))
m3.metric("Inflation Proxy", f"{summary['inflation_proxy']:.2f}%")
m4.metric("Commodity Index", f"{summary['commodity_index']:.1f}", format_signed(summary["commodity_change"]))
m5.metric("War Risk Index", f"{summary['war_risk']:.1f}/100")
m6.metric("Stability Index", f"{summary['stability']:.1f}/100")

st.caption(f"Current world seed: {int(seed)} — Scenario: {scenario} — Volatility: {difficulty}. Regenerate a new world from the sidebar to test a different map, resource distribution and political outcome.")
map_view = st.radio(
    "Strategic map view",
    ["Territory", "Terrain", "Resources", "War", "Religion", "Economy", "Technology"],
    horizontal=True,
    help="Change the map layer to understand territory, conflicts, resources, religion, economy and technology at a glance."
)
st.plotly_chart(world_map_figure(world, civs, view_mode=map_view, civ_df=civ_df), width="stretch", key=f"world_map_{map_view}")
legend_text = {
    "Territory": "Territory view: each color represents a civilization. Stars show cities/capitals; diamonds show strategic resources.",
    "Terrain": "Terrain view: blue = water, green = forest/plains, grey = mountains, sand = desert.",
    "Resources": "Resources view: gold/brown intensity highlights strategic resource density, especially iron and gold.",
    "War": "War view: red territories belong to civilizations involved in active conflicts; green means no active war.",
    "Religion": "Religion view: territories are grouped by dominant faith, making cultural blocs easier to read.",
    "Economy": "Economy view: stronger warm colors indicate higher GDP concentration.",
    "Technology": "Technology view: stronger blue intensity indicates higher technology levels.",
}.get(map_view, "Use the map filters to read the world from different strategic angles.")
st.info(legend_text)

# -----------------------------------------------------------------------------
# Tabs
# -----------------------------------------------------------------------------
tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13, tab14 = st.tabs([
    "Command Center",
    "Economic Terminal",
    "Civilization Profiles",
    "Global Markets",
    "Strategic Affairs",
    "Living Civilizations",
    "Imperial Archives",
    "Modern World & Beyond",
    "Analytics Lab",
    "Trade Flows",
    "Resource Atlas",
    "Timeline Intelligence",
    "Civilization Comparator",
    "Strategic Map Room",
    "Final Report",
])

with tab0:
    st.subheader("Command Center")
    st.caption("A readable control room for understanding what is happening in the simulated world.")

    a, b, c, d = st.columns(4)
    a.metric("Dominant Empire", summary["dominant_empire"])
    b.metric("Richest Economy", summary["richest_empire"])
    c.metric("Strongest Army", summary["strongest_army"])
    d.metric("Technology Leader", summary["tech_leader"])

    st.markdown("### Global Rankings")
    r1, r2, r3 = st.columns(3)
    r1.plotly_chart(bar_chart(civ_df.head(8), "Civilization", "Power Score", "Overall Power Ranking"), width="stretch", key="rank_power")
    r2.plotly_chart(bar_chart(civ_df.sort_values("GDP", ascending=False).head(8), "Civilization", "GDP", "Economic Ranking"), width="stretch", key="rank_gdp")
    r3.plotly_chart(bar_chart(civ_df.sort_values("Military", ascending=False).head(8), "Civilization", "Military", "Military Ranking"), width="stretch", key="rank_military")

    st.markdown("### World News Feed")
    if events_df.empty:
        st.info("No major events yet. Run more years to generate a deeper world history.")
    else:
        news = events_df.sort_values("year", ascending=False).head(12)[["year", "Category", "civilization", "event"]]
        st.dataframe(news, width="stretch", hide_index=True)

    st.markdown("### Rise and Fall Tracker")
    trend_window = min(80, max(1, len(history_df) - 1))
    rise_data = civ_df[["Civilization", "Power Score", "Stability", "Technology", "GDP", "Military", "Status"]].copy()
    rise_data["Fragility Signal"] = rise_data.apply(
        lambda r: "Critical" if r["Stability"] < 45 else ("Watch" if r["Stability"] < 65 else "Safe"),
        axis=1,
    )
    st.dataframe(rise_data.sort_values("Power Score", ascending=False), width="stretch", hide_index=True)

with tab1:
    st.subheader("Economic Terminal")
    st.caption("A finance-oriented macro view of the simulated world economy.")

    e1, e2, e3, e4, e5, e6 = st.columns(6)
    e1.metric("World GDP", f"{summary['world_gdp']:,.0f}", format_signed(summary["gdp_growth"]))
    e2.metric("Global Growth", format_signed(summary["gdp_growth"]))
    e3.metric("Inflation Proxy", f"{summary['inflation_proxy']:.2f}%")
    e4.metric("Commodity Index", f"{summary['commodity_index']:.1f}", format_signed(summary["commodity_change"]))
    e5.metric("Geo Risk", f"{summary['war_risk']:.1f}/100")
    e6.metric("Stability", f"{summary['stability']:.1f}/100")

    g1, g2 = st.columns(2)
    g1.plotly_chart(line_chart(history_df, "world_gdp", "World GDP Over Time"), width="stretch", key="economy_gdp")
    g2.plotly_chart(line_chart(history_df, "world_population", "World Population Over Time"), width="stretch", key="economy_population")

    g3, g4 = st.columns(2)
    g3.plotly_chart(line_chart(history_df, "commodity_index", "World Commodity Index"), width="stretch", key="economy_commodity")
    g4.plotly_chart(line_chart(history_df, "war_risk_index", "Geopolitical Risk Index"), width="stretch", key="economy_risk")

    g5, g6 = st.columns(2)
    g5.plotly_chart(line_chart(history_df, "avg_stability", "World Stability Index"), width="stretch", key="economy_stability")
    g6.plotly_chart(multi_line_chart(history_df, ["active_wars", "active_crises", "alliances", "rivalries"], "World Order Dashboard"), width="stretch", key="economy_order")

    st.markdown("### Strategic Macro Interpretation")
    interpretations = []
    if summary["gdp_growth"] > 5:
        interpretations.append("The world economy is in expansion: GDP has grown strongly over the recent period.")
    elif summary["gdp_growth"] < -5:
        interpretations.append("The world economy is contracting: instability, wars or crises may be damaging production.")
    else:
        interpretations.append("The world economy is broadly stable, with no extreme GDP shock in the recent period.")

    if summary["war_risk"] >= 60:
        interpretations.append("Geopolitical risk is elevated: conflict dynamics may affect trade routes and commodity prices.")
    else:
        interpretations.append("Geopolitical risk remains contained, although rivalries can still reshape the balance of power.")

    if summary["inflation_proxy"] > 1:
        interpretations.append("The inflation proxy is positive: average commodity prices are rising.")
    elif summary["inflation_proxy"] < -1:
        interpretations.append("The inflation proxy is negative: commodity deflation or supply surpluses dominate.")
    else:
        interpretations.append("Commodity inflation is muted: the market is relatively balanced.")

    for item in interpretations:
        st.write("- " + item)

with tab2:
    st.subheader("Civilization Profiles")
    selected_civ = st.selectbox("Inspect a civilization", civ_df["Civilization"].tolist())
    profile = civ_df[civ_df["Civilization"] == selected_civ].iloc[0]

    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric("Power Score", f"{profile['Power Score']:.1f}")
    p2.metric("GDP", f"{profile['GDP']:,.0f}")
    p3.metric("Military", f"{profile['Military']:,.0f}")
    p4.metric("Stability", f"{profile['Stability']:.1f}")
    p5.metric("Technology", f"{profile['Technology']:.1f}")

    st.markdown(
        f"""
        **Leader:** {profile['Leader']}  
        **Personality:** {profile['Personality']}  
        **Religion:** {profile['Religion']}  
        **Main Export:** {profile['Main Export']}  
        **Main Import:** {profile['Main Import']}  
        **Current Status:** {profile['Status']}
        """
    )

    st.markdown("### Full Civilization Table")
    st.dataframe(civ_df, width="stretch", hide_index=True)
    c1, c2 = st.columns(2)
    c1.plotly_chart(bar_chart(civ_df, "Civilization", "Power Score", "Civilization Power Ranking"), width="stretch", key="civ_power")
    c2.plotly_chart(bar_chart(civ_df, "Civilization", "Trade Balance", "Trade Balance by Civilization"), width="stretch", key="civ_trade")

with tab3:
    st.subheader("Global Markets Dashboard")
    st.caption("Readable commodity intelligence: prices, pressure, top movers and strategic supply-demand imbalances.")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Commodity Index", f"{latest_market['commodity_index']:.1f}", format_signed(summary["commodity_change"]))
    c2.metric("Food Price", f"{float(market_df.loc[market_df['Resource']=='Food','Price'].iloc[0]):.2f}")
    c3.metric("Iron Price", f"{float(market_df.loc[market_df['Resource']=='Iron','Price'].iloc[0]):.2f}")
    c4.metric("Gold Price", f"{float(market_df.loc[market_df['Resource']=='Gold','Price'].iloc[0]):.2f}")
    c5.metric("Avg Price Change", f"{summary['inflation_proxy']:.2f}%")

    st.markdown("### Commodity Snapshot")
    st.dataframe(market_df, width="stretch", hide_index=True)

    top_gainers = market_df.sort_values("Price Change %", ascending=False).head(3)
    top_losers = market_df.sort_values("Price Change %", ascending=True).head(3)
    m1, m2 = st.columns(2)
    m1.plotly_chart(bar_chart(top_gainers, "Resource", "Price Change %", "Top Market Gainers"), width="stretch", key="market_gainers")
    m2.plotly_chart(bar_chart(top_losers, "Resource", "Price Change %", "Top Market Losers"), width="stretch", key="market_losers")

    m3, m4 = st.columns(2)
    m3.plotly_chart(line_chart(market_history_df, "commodity_index", "World Commodity Index"), width="stretch", key="market_index")
    m4.plotly_chart(bar_chart(market_df, "Resource", "Surplus / Deficit", "Current Supply-Demand Balance"), width="stretch", key="market_balance")

    st.markdown("### Market Reading")
    shortage_resources = market_df[market_df["Surplus / Deficit"] < 0]["Resource"].tolist()
    rising_resources = market_df[market_df["Trend"] == "Rising"]["Resource"].tolist()
    if shortage_resources:
        st.warning("Shortage detected in: " + ", ".join(shortage_resources))
    else:
        st.success("No global shortage detected at the end of the simulation.")
    if rising_resources:
        st.info("Resources with rising prices: " + ", ".join(rising_resources))
    else:
        st.info("No strong broad-based commodity price acceleration detected.")

with tab4:
    st.subheader("Strategic Affairs Center")
    st.caption("Diplomacy, alliances, rivalries, resource wars and geopolitical risk.")

    geo1, geo2, geo3, geo4 = st.columns(4)
    geo1.metric("Active Wars", int(latest["active_wars"]))
    geo2.metric("Alliances", int(latest["alliances"]))
    geo3.metric("Rivalries", int(latest["rivalries"]))
    geo4.metric("War Risk", f"{summary['war_risk']:.1f}/100")

    st.plotly_chart(line_chart(history_df, "war_risk_index", "War Risk Index Over Time"), width="stretch", key="geo_risk")

    g1, g2 = st.columns(2)
    with g1:
        st.markdown("### Active Wars")
        if war_df.empty:
            st.info("No active wars at the end of this simulation.")
        else:
            st.dataframe(war_df, width="stretch", hide_index=True)
            st.plotly_chart(bar_chart(war_df, "Cause", "Intensity", "War Intensity by Resource Cause"), width="stretch", key="geo_wars")
    with g2:
        st.markdown("### Diplomatic Relations")
        st.dataframe(diplomacy_df, width="stretch", hide_index=True)
        if "Status" in diplomacy_df.columns and "Relation Score" in diplomacy_df.columns:
            st.plotly_chart(bar_chart(diplomacy_df, "Status", "Relation Score", "Diplomatic Relationship Scores"), width="stretch", key="geo_diplomacy")

with tab5:
    st.subheader("Living Civilizations")
    st.caption("Religion, technology, leaders, crises and revolts — the layer that gives each civilization its own story.")

    l1, l2, l3 = st.columns(3)
    l1.plotly_chart(bar_chart(tech_df, "Civilization", "Technology Level", "Technology Race"), width="stretch", key="living_tech")
    l2.plotly_chart(bar_chart(religion_df, "Civilization", "Faith Influence", "Religious Influence"), width="stretch", key="living_religion")
    l3.plotly_chart(bar_chart(civ_df.sort_values("Stability"), "Civilization", "Stability", "Stability / Revolt Risk"), width="stretch", key="living_stability")

    st.markdown("### Leaders")
    st.dataframe(leader_df, width="stretch", hide_index=True)

    ctech, creligion = st.columns(2)
    with ctech:
        st.markdown("### Technologies")
        st.dataframe(tech_df, width="stretch", hide_index=True)
    with creligion:
        st.markdown("### Religions")
        st.dataframe(religion_df, width="stretch", hide_index=True)

    st.markdown("### Crises and Revolts")
    if crisis_df.empty:
        st.success("No active crisis at the end of this simulation.")
    else:
        st.dataframe(crisis_df, width="stretch", hide_index=True)

with tab6:
    st.subheader("Imperial Archives")
    st.caption("Narrative intelligence layer: chronicles, biographies, war stories and century-by-century summaries generated from simulation data.")

    n1, n2 = st.columns([1.15, 0.85])
    with n1:
        st.markdown("### Historical Chronicle")
        st.markdown(f"<div class='strategy-card'>{build_historical_chronicle(summary, events_df, civ_df).replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
    with n2:
        st.markdown("### Narrative Signals")
        st.metric("Historical year", int(summary["year"]))
        st.metric("Active wars", int(summary["active_wars"]))
        st.metric("Active crises", int(summary["active_crises"]))
        st.metric("War risk", f"{summary['war_risk']:.1f}/100")

    st.markdown("### Civilization Biography Generator")
    bio_civ = st.selectbox("Choose a civilization biography", civ_df["Civilization"].tolist(), key="bio_civ_selector")
    bio_profile = civ_df[civ_df["Civilization"] == bio_civ].iloc[0]
    st.markdown(f"<div class='strategy-card'>{build_civilization_biography(bio_profile).replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

    st.markdown("### War Narratives")
    st.markdown(f"<div class='strategy-card'>{build_war_story(war_df).replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

    st.markdown("### Summary of Past Centuries")
    century_df = build_century_summary(events_df, history_df)
    if century_df.empty:
        st.info("Run a longer simulation to generate century summaries.")
    else:
        st.dataframe(century_df.sort_values("Era", ascending=False), width="stretch", hide_index=True)
        st.plotly_chart(bar_chart(century_df.tail(8), "Era", "Average Risk", "Geopolitical Risk by Era"), width="stretch", key="historian_century_risk")

with tab7:
    st.subheader("Modern World & Beyond")
    st.caption("Climate systems, natural disasters, private companies, central banks, financial markets, industrialization, modern transitions and space exploration.")

    x1, x2, x3, x4 = st.columns(4)
    x1.metric("Weather Stress", f"{float(history_df['weather_stress_index'].iloc[-1]):.1f}/100" if "weather_stress_index" in history_df else "0")
    x2.metric("Industrialization", f"{float(history_df['industrialization_index'].iloc[-1]):.1f}/100" if "industrialization_index" in history_df else "0")
    x3.metric("Modern World", f"{float(history_df['modern_world_index'].iloc[-1]):.1f}/100" if "modern_world_index" in history_df else "0")
    x4.metric("Space Race", f"{float(history_df['space_race_index'].iloc[-1]):.1f}/100" if "space_race_index" in history_df else "0")

    st.markdown("### Climate, Seasons and Disasters")
    cext1, cext2 = st.columns(2)
    if not weather_df.empty:
        cext1.plotly_chart(line_chart(weather_df, "Weather Stress Index", "Weather Stress Over Time"), width="stretch", key="phase7_weather")
    if not disaster_df.empty:
        cext2.plotly_chart(bar_chart(disaster_df.tail(20), "Civilization", "Severity", "Recent Natural Disaster Severity"), width="stretch", key="phase7_disasters")
    else:
        cext2.info("No major natural disaster recorded at the end of this simulation. Run more years or increase world instability.")
    if not disaster_df.empty:
        st.dataframe(disaster_df.sort_values("Year", ascending=False), width="stretch", hide_index=True)

    st.markdown("### Private Companies")
    if company_df.empty:
        st.info("No private companies recorded yet.")
    else:
        co1, co2 = st.columns(2)
        co1.plotly_chart(bar_chart(company_df.head(10), "Company", "Market Cap", "Largest Private Companies"), width="stretch", key="phase7_companies")
        sector_df = company_df.groupby("Sector", as_index=False)["Market Cap"].sum().sort_values("Market Cap", ascending=False)
        co2.plotly_chart(bar_chart(sector_df, "Sector", "Market Cap", "Private Sector Market Cap by Sector"), width="stretch", key="phase7_sectors")
        st.dataframe(company_df.head(25), width="stretch", hide_index=True)

    st.markdown("### Central Banks and Financial Markets")
    f1, f2 = st.columns(2)
    if not central_bank_df.empty:
        latest_cb = central_bank_df.sort_values("year").groupby("Civilization").tail(1)
        f1.plotly_chart(bar_chart(latest_cb, "Civilization", "Policy Rate", "Policy Rates by Civilization"), width="stretch", key="phase7_rates")
        f2.plotly_chart(bar_chart(latest_cb, "Civilization", "Inflation", "Inflation by Civilization"), width="stretch", key="phase7_inflation")
        st.dataframe(latest_cb, width="stretch", hide_index=True)
    if not financial_df.empty:
        selected_market_civ = st.selectbox("Select civilization market", sorted(financial_df["Civilization"].unique()), key="market_civ_phase7")
        market_series = financial_df[financial_df["Civilization"] == selected_market_civ]
        mkt1, mkt2 = st.columns(2)
        mkt1.plotly_chart(line_chart(market_series, "Stock Index", f"{selected_market_civ} Stock Index"), width="stretch", key="phase7_stock")
        mkt2.plotly_chart(line_chart(market_series, "Bond Yield", f"{selected_market_civ} Bond Yield"), width="stretch", key="phase7_bond")

    st.markdown("### Industrial Revolution, Modern World and Space Exploration")
    if not phase_df.empty:
        p1, p2 = st.columns(2)
        p1.plotly_chart(multi_line_chart(phase_df, ["Industrialization Index", "Modern World Index", "Space Race Index"], "Civilizational Development Stages"), width="stretch", key="phase7_progress")
        dev_cols = ["Civilization", "Industrialization", "Modernization", "Space Progress", "Technology", "GDP"]
        p2.dataframe(civ_df[dev_cols].sort_values("Space Progress", ascending=False), width="stretch", hide_index=True)

    st.markdown("### Strategic Reading")
    st.write("- Weather and disasters create supply shocks that can weaken stability and production.")
    st.write("- Private companies represent the rise of a market economy and strategic industries.")
    st.write("- Central banks react to inflation and geopolitical stress through simulated policy rates.")
    st.write("- Industrialization unlocks the modern world, and advanced modern civilizations can enter a space race.")

with tab8:
    st.subheader("Analytics Lab")
    st.caption("Professional data layer for exporting, auditing and analyzing the simulated world like a macro-financial dataset.")

    st.markdown("### Simulation Export Center")
    export_data = {
        "civilizations": civ_df,
        "world_history": history_df,
        "events": events_df,
        "markets": market_df,
        "market_history": market_history_df,
        "trade_flows": trade_df,
        "diplomacy": diplomacy_df,
        "wars": war_df,
        "technologies": tech_df,
        "religions": religion_df,
        "leaders": leader_df,
        "crises": crisis_df,
        "weather": weather_df,
        "disasters": disaster_df,
        "companies": company_df,
        "financial_markets": financial_df,
        "central_banks": central_bank_df,
        "development_phases": phase_df,
    }
    dl1, dl2, dl3 = st.columns(3)
    dl1.download_button("Download full simulation ZIP", data=build_export_zip(export_data), file_name="ai_civilization_simulation_export.zip", mime="application/zip")
    dl2.download_button("Download civilization data", data=dataframe_to_csv_bytes(civ_df), file_name="civilizations.csv", mime="text/csv")
    dl3.download_button("Download world history", data=dataframe_to_csv_bytes(history_df), file_name="world_history.csv", mime="text/csv")

    st.markdown("### Macro Analytics")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("War / Iron correlation", f"{safe_corr(history_df, 'war_risk_index', 'iron_price'):.2f}" if "iron_price" in history_df else "N/A")
    a2.metric("War / GDP correlation", f"{safe_corr(history_df, 'war_risk_index', 'world_gdp'):.2f}")
    a3.metric("Stability / GDP correlation", f"{safe_corr(history_df, 'avg_stability', 'world_gdp'):.2f}")
    a4.metric("Commodity volatility", f"{market_history_df['commodity_index'].pct_change().std() * 100:.2f}%" if len(market_history_df) > 2 else "0.00%")

    lab1, lab2 = st.columns(2)
    if "iron_price" in history_df:
        lab1.plotly_chart(line_chart(history_df, "iron_price", "Iron Price and Resource-War Pressure"), width="stretch", key="analytics_iron")
    else:
        lab1.plotly_chart(line_chart(market_history_df, "commodity_index", "Commodity Index Volatility"), width="stretch", key="analytics_commodity")
    lab2.plotly_chart(multi_line_chart(history_df, ["war_risk_index", "avg_stability", "active_wars", "active_crises"], "Risk, Stability and Conflict Signals"), width="stretch", key="analytics_risk_pack")

    st.markdown("### Commodity Volatility")
    vol_df = commodity_volatility_table(market_history_df)
    if vol_df.empty:
        st.info("Not enough market history to calculate volatility.")
    else:
        v1, v2 = st.columns(2)
        v1.dataframe(vol_df, width="stretch", hide_index=True)
        v2.plotly_chart(bar_chart(vol_df, "Resource", "Volatility %", "Commodity Volatility Ranking"), width="stretch", key="analytics_volatility_rank")

    st.markdown("### Risk Ranking")
    risk_df = civ_df[["Civilization", "Power Score", "Stability", "Crisis Risk", "At War", "Inflation", "Trade Balance", "Drought Risk"]].copy()
    risk_df["Risk Score"] = (100 - risk_df["Stability"].astype(float)) + (risk_df["At War"].eq("Yes") * 20) + risk_df["Inflation"].abs() + risk_df["Drought Risk"].astype(float) * 20
    st.dataframe(risk_df.sort_values("Risk Score", ascending=False), width="stretch", hide_index=True)

    st.markdown("### Top Civilization Factors")
    factor_cols = [c for c in ["Civilization", "Power Score", "GDP", "Military", "Technology", "Stability", "Industrialization", "Modernization", "Space Progress"] if c in civ_df.columns]
    st.dataframe(civ_df[factor_cols].sort_values("Power Score", ascending=False), width="stretch", hide_index=True)

    st.markdown("### Save / Load Roadmap")
    st.info("This version exports complete simulation states as CSV/ZIP. Full interactive reload of saved worlds can be added next by serializing the world map and civilization objects into JSON.")

with tab9:
    st.subheader("Trade Flow Analysis")
    selected_resource = st.selectbox("Select a resource", sorted(trade_df["Resource"].unique()))
    filtered_trade = trade_df[trade_df["Resource"] == selected_resource]
    st.dataframe(filtered_trade, width="stretch", hide_index=True)
    c1, c2 = st.columns(2)
    c1.plotly_chart(bar_chart(filtered_trade, "Civilization", "Exports", f"Top Exporters — {selected_resource}"), width="stretch", key="trade_exports")
    c2.plotly_chart(bar_chart(filtered_trade, "Civilization", "Imports", f"Top Importers — {selected_resource}"), width="stretch", key="trade_imports")

with tab10:
    st.subheader("Resource Atlas and World Supply Potential")
    map_df = world.to_dataframe()
    resource_summary = map_df[["food", "wood", "stone", "iron", "gold"]].sum().reset_index()
    resource_summary.columns = ["Resource", "World Supply Potential"]
    st.dataframe(resource_summary, width="stretch", hide_index=True)
    st.plotly_chart(bar_chart(resource_summary, "Resource", "World Supply Potential", "Global Resource Distribution"), width="stretch", key="resources_distribution")

with tab11:
    st.subheader("Timeline Intelligence")
    st.caption("Interactive timeline with filters and clear explanations: why wars start, why prices move, why crises emerge.")
    if events_df.empty:
        st.info("No major events yet. Longer simulations will generate more market, city and geopolitical events.")
    else:
        t1, t2, t3 = st.columns([1, 1, 1])
        min_year = int(events_df["year"].min())
        max_year = int(events_df["year"].max())
        selected_categories = t1.multiselect(
            "Event categories",
            sorted(events_df["Category"].unique()),
            default=sorted(events_df["Category"].unique()),
        )
        selected_civs = t2.multiselect(
            "Civilizations / actors",
            sorted(events_df["civilization"].dropna().unique()),
            default=[],
            help="Leave empty to include all actors."
        )
        year_range = t3.slider("Year range", min_year, max_year, (min_year, max_year))

        filtered_events = events_df[
            (events_df["Category"].isin(selected_categories))
            & (events_df["year"].between(year_range[0], year_range[1]))
        ].copy()
        if selected_civs:
            filtered_events = filtered_events[filtered_events["civilization"].isin(selected_civs)]

        st.markdown("### Filtered timeline")
        st.dataframe(filtered_events.sort_values("year", ascending=False), width="stretch", hide_index=True)

        st.markdown("### Event explanations")
        if filtered_events.empty:
            st.info("No event matches the selected filters.")
        else:
            event_options = [f"Year {int(r['year'])} — {r['Category']} — {r['event'][:90]}" for _, r in filtered_events.sort_values("year", ascending=False).head(80).iterrows()]
            selected_event_label = st.selectbox("Select an event to understand why it happened", event_options)
            selected_index = event_options.index(selected_event_label)
            selected_row = filtered_events.sort_values("year", ascending=False).head(80).iloc[selected_index]
            st.markdown(f"<div class='strategy-card'>{explain_event(selected_row, civ_df, market_df, war_df).replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

        st.markdown("### Timeline composition")
        event_counts = filtered_events.groupby("Category", as_index=False).size().rename(columns={"size": "Events"}) if not filtered_events.empty else pd.DataFrame()
        if not event_counts.empty:
            st.plotly_chart(bar_chart(event_counts, "Category", "Events", "Events by Category"), width="stretch", key="timeline_category_counts")

with tab12:
    st.subheader("Civilization Comparator")
    st.caption("Compare two empires like macro countries: economy, military, technology, stability, trade and modern development.")
    civa, civb = st.columns(2)
    left_civ = civa.selectbox("Civilization A", civ_df["Civilization"].tolist(), index=0, key="compare_a")
    default_b = 1 if len(civ_df) > 1 else 0
    right_civ = civb.selectbox("Civilization B", civ_df["Civilization"].tolist(), index=default_b, key="compare_b")
    row_a = civ_df[civ_df["Civilization"] == left_civ].iloc[0]
    row_b = civ_df[civ_df["Civilization"] == right_civ].iloc[0]
    compare_metrics = [
        "Power Score", "GDP", "Population", "Military", "Technology", "Stability", "Territory",
        "Trade Balance", "Faith", "Inflation", "Policy Rate", "Stock Index", "Industrialization", "Modernization", "Space Progress"
    ]
    compare_rows = []
    for metric in compare_metrics:
        if metric in civ_df.columns:
            a_val = row_a[metric]
            b_val = row_b[metric]
            try:
                diff = float(a_val) - float(b_val)
            except Exception:
                diff = ""
            compare_rows.append({"Metric": metric, left_civ: a_val, right_civ: b_val, "Difference": round(diff, 2) if isinstance(diff, float) else diff})
    comp_df = pd.DataFrame(compare_rows)
    st.dataframe(comp_df, width="stretch", hide_index=True)

    radar_cols = [m for m in ["Power Score", "GDP", "Military", "Technology", "Stability", "Territory"] if m in civ_df.columns]
    norm_rows = []
    for civ_name, row in [(left_civ, row_a), (right_civ, row_b)]:
        out = {"Civilization": civ_name}
        for col in radar_cols:
            maxv = max(float(civ_df[col].max()), 1)
            out[col] = round(float(row[col]) / maxv * 100, 1)
        norm_rows.append(out)
    norm_df = pd.DataFrame(norm_rows)
    st.plotly_chart(multi_line_chart(norm_df.rename(columns={"Civilization": "year"}), radar_cols, "Normalized Comparison Index"), width="stretch", key="compare_normalized")

    st.markdown("### Strategic Interpretation")
    if float(row_a["Power Score"]) > float(row_b["Power Score"]):
        st.write(f"- **{left_civ}** currently has the stronger overall power position.")
    elif float(row_b["Power Score"]) > float(row_a["Power Score"]):
        st.write(f"- **{right_civ}** currently has the stronger overall power position.")
    else:
        st.write("- Both civilizations are almost equally powerful.")
    if float(row_a["Stability"]) < 55 or float(row_b["Stability"]) < 55:
        st.warning("At least one civilization has fragile internal stability, which can change the future balance of power quickly.")

with tab13:
    st.subheader("Strategic Map Room")
    st.caption("Dedicated map intelligence room with filters, legend and practical reading of the world map.")
    room_view = st.selectbox("Map intelligence layer", ["Territory", "Terrain", "Resources", "War", "Religion", "Economy", "Technology"], key="map_room_view")
    st.plotly_chart(world_map_figure(world, civs, view_mode=room_view, civ_df=civ_df), width="stretch", key=f"map_room_{room_view}")
    st.markdown("### How to read this map")
    if room_view == "Territory":
        st.write("- Territory view shows which civilization controls each tile. Use it to read expansion, borders and dominant empires.")
    elif room_view == "Terrain":
        st.write("- Terrain view shows the underlying geography. Plains and forests support growth; mountains and deserts often contain strategic resources.")
    elif room_view == "Resources":
        st.write("- Resource view highlights strategic deposits. Empires near iron and gold often gain economic or military advantages.")
    elif room_view == "War":
        st.write("- War view highlights civilizations currently involved in conflict. Red zones indicate active military pressure.")
    elif room_view == "Religion":
        st.write("- Religion view groups territories by dominant belief system. This helps identify cultural blocs and potential religious tension.")
    elif room_view == "Economy":
        st.write("- Economy view emphasizes GDP concentration. Stronger economic powers appear with more intense warm colors.")
    elif room_view == "Technology":
        st.write("- Technology view highlights scientific leaders. Stronger blue intensity means higher technology level.")
    st.markdown("### Map-linked rankings")
    map_rank_cols = [c for c in ["Civilization", "Territory", "GDP", "Military", "Technology", "Religion", "At War", "Main Export", "Main Import"] if c in civ_df.columns]
    st.dataframe(civ_df[map_rank_cols].sort_values("Territory", ascending=False), width="stretch", hide_index=True)

with tab14:
    st.subheader("Final Simulation Report")
    st.caption("Automatic end-of-run report after the selected simulation horizon. Built to make each run understandable and GitHub-presentable.")
    final_report_md = build_final_simulation_report(summary, events_df, civ_df, history_df, market_history_df, war_df, crisis_df)
    st.download_button("Download final report (.md)", data=final_report_md.encode("utf-8"), file_name=f"world_report_seed_{int(seed)}.md", mime="text/markdown")
    st.markdown(final_report_md)
    st.markdown("### Key final rankings")
    fr1, fr2, fr3 = st.columns(3)
    fr1.plotly_chart(bar_chart(civ_df.head(8), "Civilization", "Power Score", "Final Power Ranking"), width="stretch", key="final_power")
    fr2.plotly_chart(bar_chart(civ_df.sort_values("GDP", ascending=False).head(8), "Civilization", "GDP", "Final Economic Ranking"), width="stretch", key="final_gdp")
    fr3.plotly_chart(bar_chart(civ_df.sort_values("Technology", ascending=False).head(8), "Civilization", "Technology", "Final Technology Ranking"), width="stretch", key="final_tech")
    st.markdown("### Key historical charts")
    fh1, fh2 = st.columns(2)
    fh1.plotly_chart(line_chart(history_df, "world_gdp", "World GDP Across the Full Run"), width="stretch", key="final_gdp_line")
    fh2.plotly_chart(line_chart(history_df, "war_risk_index", "War Risk Across the Full Run"), width="stretch", key="final_war_line")
