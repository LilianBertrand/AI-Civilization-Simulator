import plotly.express as px
import plotly.graph_objects as go
from config.settings import TERRAIN_COLORS

DARK_BG = "#F6F0E4"
PANEL_BG = "#FFFDF7"
GRID = "#D8CBB8"
TEXT = "#263238"
ACCENT = "#B8832F"

TERRAIN_NUM = {"water": 0, "plains": 1, "forest": 2, "mountain": 3, "desert": 4}
TERRAIN_SCALE = [
    [0.00, "#7BB7C9"], [0.20, "#7BB7C9"],
    [0.21, "#C8D68A"], [0.40, "#C8D68A"],
    [0.41, "#6FA66A"], [0.60, "#6FA66A"],
    [0.61, "#A7A29A"], [0.80, "#A7A29A"],
    [0.81, "#E4C07A"], [1.00, "#E4C07A"],
]


def _strategy_layout(fig, title=None, height=360):
    fig.update_layout(
        title=title,
        height=height,
        margin=dict(l=12, r=12, t=46 if title else 18, b=18),
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PANEL_BG,
        font=dict(color=TEXT, family="Inter, Arial, sans-serif"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT)),
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID),
    )
    return fig


def _stable_color(label: str):
    palette = ["#6D9DC5", "#F4A261", "#8AB17D", "#E76F51", "#9D4EDD", "#2A9D8F", "#E9C46A", "#B56576", "#577590", "#BC6C25"]
    return palette[abs(hash(str(label))) % len(palette)]


def world_map_figure(world_map, civilizations, view_mode="Territory", civ_df=None):
    """Strategic world map with multiple readable filters.

    view_mode can be: Territory, Terrain, Resources, War, Religion, Economy, Technology.
    The goal is not to be a 3D game map, but a much clearer strategic map.
    """
    df = world_map.to_dataframe()
    civ_color_map = {c.id: c.color for c in civilizations}
    civ_name_map = {c.id: c.name for c in civilizations}
    civ_capitals = {(c.capital_x, c.capital_y): c.name for c in civilizations}
    civ_attr = {c.name: c for c in civilizations}

    df["terrain_code"] = df["terrain"].map(TERRAIN_NUM).fillna(1)
    grid = df.pivot(index="y", columns="x", values="terrain_code").sort_index(ascending=False)

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=grid.values,
        x=list(grid.columns),
        y=[-v for v in grid.index],
        colorscale=TERRAIN_SCALE,
        showscale=False,
        hoverinfo="skip",
        name="Terrain",
    ))

    owned = df[df["owner_id"].notna()].copy()
    legend_notes = []
    if not owned.empty and view_mode != "Terrain":
        owned["owner"] = owned["owner_id"].apply(lambda v: civ_name_map.get(int(v), "Unclaimed"))
        owned["base_color"] = owned["owner_id"].apply(lambda v: civ_color_map.get(int(v), "#FFFFFF"))
        owned["hover"] = (
            "<b>" + owned["owner"] + "</b>"
            + "<br>Terrain: " + owned["terrain"]
            + "<br>Food: " + owned["food"].round(2).astype(str)
            + "<br>Iron: " + owned["iron"].round(2).astype(str)
            + "<br>Gold: " + owned["gold"].round(2).astype(str)
        )

        if view_mode == "War":
            owned["color"] = owned["owner"].apply(lambda n: "#C0392B" if getattr(civ_attr.get(n), "at_war", False) else "#8AB17D")
            legend_notes = ["Red = civilization at war", "Green = no active war"]
        elif view_mode == "Religion":
            owned["religion"] = owned["owner"].apply(lambda n: getattr(civ_attr.get(n), "religion", "Unknown"))
            owned["color"] = owned["religion"].apply(_stable_color)
            legend_notes = sorted(owned["religion"].dropna().unique().tolist())[:8]
        elif view_mode == "Economy" and civ_df is not None and not civ_df.empty:
            gdp_map = civ_df.set_index("Civilization")["GDP"].to_dict() if "GDP" in civ_df.columns else {}
            vals = [gdp_map.get(n, 0) for n in owned["owner"]]
            maxv = max(vals) if vals else 1
            owned["color_score"] = [gdp_map.get(n, 0) / maxv for n in owned["owner"]]
            owned["color"] = owned["color_score"].apply(lambda v: f"rgba({int(255*v)}, {int(180-60*v)}, {int(80+80*(1-v))}, 0.75)")
            legend_notes = ["Darker gold/red = larger GDP"]
        elif view_mode == "Technology" and civ_df is not None and not civ_df.empty:
            tech_map = civ_df.set_index("Civilization")["Technology"].to_dict() if "Technology" in civ_df.columns else {}
            vals = [tech_map.get(n, 0) for n in owned["owner"]]
            maxv = max(vals) if vals else 1
            owned["color_score"] = [tech_map.get(n, 0) / maxv for n in owned["owner"]]
            owned["color"] = owned["color_score"].apply(lambda v: f"rgba({int(70+80*v)}, {int(120+80*v)}, 220, 0.75)")
            legend_notes = ["Darker blue = higher technology level"]
        elif view_mode == "Resources":
            owned["strategic"] = owned[["iron", "gold", "stone"]].sum(axis=1)
            maxv = max(float(owned["strategic"].max()), 1)
            owned["color"] = owned["strategic"].apply(lambda v: f"rgba({int(130+125*v/maxv)}, {int(95+80*v/maxv)}, 35, 0.70)")
            legend_notes = ["Gold/brown intensity = strategic resource density"]
        else:
            owned["color"] = owned["base_color"]
            legend_notes = ["Each color represents one civilization territory"]

        fig.add_trace(go.Scatter(
            x=owned["x"], y=-owned["y"], mode="markers",
            marker=dict(size=13, color=owned["color"], symbol="square", opacity=0.62, line=dict(width=0.65, color="#FFFFFF")),
            text=owned["hover"], hoverinfo="text", name=view_mode,
        ))

    if view_mode in {"Resources", "Territory"}:
        resource_df = df[(df["iron"] > df["iron"].quantile(0.92)) | (df["gold"] > df["gold"].quantile(0.94))].copy()
        if not resource_df.empty:
            resource_df["hover"] = "Strategic resource" + "<br>Iron: " + resource_df["iron"].round(2).astype(str) + "<br>Gold: " + resource_df["gold"].round(2).astype(str)
            fig.add_trace(go.Scatter(
                x=resource_df["x"], y=-resource_df["y"], mode="markers",
                marker=dict(size=8, color=ACCENT, symbol="diamond", opacity=0.88, line=dict(width=0.5, color="#5B4636")),
                text=resource_df["hover"], hoverinfo="text", name="Strategic resources",
            ))

    city_df = df[df["city_id"].notna()].copy()
    if not city_df.empty:
        city_df["owner"] = city_df["owner_id"].apply(lambda v: civ_name_map.get(int(v), "Unknown") if v == v else "Unknown")
        city_df["is_capital"] = city_df.apply(lambda r: (r["x"], r["y"]) in civ_capitals, axis=1)
        fig.add_trace(go.Scatter(
            x=city_df["x"], y=-city_df["y"], mode="markers",
            marker=dict(size=city_df["is_capital"].map({True: 15, False: 9}), color="#FFD15C", symbol="star", line=dict(width=1.3, color="#FFFFFF")),
            text=city_df["owner"], hoverinfo="text", name="Cities / capitals",
        ))

    for civ in civilizations:
        fig.add_trace(go.Scatter(
            x=[civ.capital_x], y=[-civ.capital_y], mode="text",
            text=[civ.name], textposition="top center",
            textfont=dict(size=13, color="#4B3523", family="Georgia, serif"),
            hoverinfo="skip", showlegend=False,
        ))

    subtitle = " · ".join(str(x) for x in legend_notes[:6])
    fig.update_layout(
        height=720,
        margin=dict(l=8, r=8, t=52, b=8),
        title=f"Strategic World Map — {view_mode}" + (f"<br><sup>{subtitle}</sup>" if subtitle else ""),
        xaxis=dict(visible=False, constrain="domain"),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01, bgcolor="rgba(255,253,247,0.88)", font=dict(size=11, color=TEXT)),
        plot_bgcolor=DARK_BG,
        paper_bgcolor=DARK_BG,
        font=dict(color=TEXT, family="Inter, Arial, sans-serif"),
    )
    return fig

def line_chart(history_df, y, title):
    if history_df.empty:
        return go.Figure()
    fig = px.line(history_df, x="year", y=y, title=title, markers=False)
    fig.update_traces(line=dict(width=3))
    return _strategy_layout(fig, title=title, height=340)


def bar_chart(civ_df, x, y, title):
    fig = px.bar(civ_df, x=x, y=y, title=title)
    fig.update_traces(marker_line_width=0.4, marker_line_color="#5B4636")
    fig.update_layout(xaxis_tickangle=-28)
    return _strategy_layout(fig, title=title, height=380)


def multi_line_chart(df, y_columns, title):
    if df.empty:
        return go.Figure()
    fig = go.Figure()
    for col in y_columns:
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df["year"], y=df[col], mode="lines", name=col.replace("_", " ").title(), line=dict(width=3)))
    return _strategy_layout(fig, title=title, height=380)


def pie_chart(df, names, values, title):
    fig = px.pie(df, names=names, values=values, title=title, hole=0.55)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return _strategy_layout(fig, title=title, height=360)
