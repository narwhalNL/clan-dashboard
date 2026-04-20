"""
Clash Royale Clan War Dashboard — MOBILE UI
Run: python mobile.py  →  open http://localhost:8051
"""

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, dash_table, no_update, ctx
import dash_bootstrap_components as dbc

# ── Data ───────────────────────────────────────────────────────────────────────
df_raw = pd.read_excel("claudeshare.xlsx")
df_raw.columns = df_raw.columns.str.strip()

def stage_key(s):
    a, b = s.split("-"); return int(a) * 100 + int(b)

STAGES    = sorted(df_raw["stage"].unique(), key=stage_key)
STAGE_IDX = {s: i for i, s in enumerate(STAGES)}
MAX_CLAN, MAX_PLAYER = 800, 16

_sa = df_raw.groupby("stage").agg(
    tf=("fame","sum"), td=("decks used","sum"), np=("player tag","nunique")
).reset_index()
_sa["mpg"]  = _sa["tf"] / _sa["td"]
_sa["act"]  = _sa["td"] / MAX_CLAN * 100
_sa["mpp"]  = _sa["tf"] / _sa["np"]
_sa["miss"] = MAX_CLAN  - _sa["td"]

RECORD_FAME, RECORD_MPG     = int(_sa["tf"].max()), _sa["mpg"].max()
RECORD_ACTIVITY, RECORD_MPP = _sa["act"].max(), _sa["mpp"].max()
RECORD_MISS = int(_sa["miss"].min())

latest_name = (df_raw.sort_values("stage", key=lambda x: x.map(stage_key))
                     .groupby("player tag")["player name"].last())
total_entries_map = df_raw[df_raw["fame"] > 0].groupby("player tag").size().to_dict()
all_tags    = sorted(latest_name.index.tolist())
player_opts = [{"label": f"{latest_name[t]}  [{t}]", "value": t} for t in all_tags]
stage_opts  = [{"label": s, "value": s} for s in STAGES]

_lg = df_raw[df_raw["stage"] == STAGES[-1]]
LG_DECKS    = _lg.set_index("player tag")["decks used"].to_dict()
LG_FAME     = _lg.set_index("player tag")["fame"].to_dict()
ACTIVE_TAGS = set(LG_DECKS.keys())

def _nl_int(v): return f"{int(round(v)):,}".replace(",",".")
def _nl_dec(v): return f"{v:.1f}".replace(".",",")
def _nl_pct(v): return f"{v:.1f}".replace(".",",") + "%"
def _nl_k(v):
    v = int(v)
    if v >= 1000: return f"{v/1000:.1f}".replace(".",",") + "k"
    return str(v)

def _player_records(tag):
    p = df_raw[df_raw["player tag"] == tag].copy()
    if p.empty: return {}
    p["mpg"]  = p["fame"] / p["decks used"].replace(0,1)
    p["act"]  = p["decks used"] / MAX_PLAYER * 100
    p["miss"] = (MAX_PLAYER - p["decks used"]).clip(lower=0)
    return {"fame": int(p["fame"].max()), "mpg": p["mpg"].max(),
            "activity": p["act"].max(), "miss": int(p["miss"].min())}

def _period_table(src_df):
    p = src_df[src_df["player tag"].isin(ACTIVE_TAGS)]
    agg = p.groupby("player tag").agg(
        tf=("fame","sum"), td=("decks used","sum"), n=("stage","nunique")
    ).reset_index()
    agg["Avg Medals/Game"]  = (agg["tf"] / agg["td"].replace(0,1)).round(0).astype(int)
    agg["Avg Medals/Stage"] = (agg["tf"] / agg["n"]).round(0).astype(int)
    miss = (p.copy().assign(miss=lambda d: (MAX_PLAYER - d["decks used"]).clip(lower=0))
              .groupby("player tag")["miss"].sum().reset_index()
              .rename(columns={"miss":"Total Missed"}))
    agg = agg.merge(miss, on="player tag", how="left").fillna(0)
    agg["Entries"] = agg["player tag"].map(lambda t: total_entries_map.get(t,0))
    agg["Name"]    = agg["player tag"].map(latest_name)
    return agg.rename(columns={"player tag":"Tag"})

# ── Colours ────────────────────────────────────────────────────────────────────
BG, CARD, CARD_KPI, CARD2 = "#0d1117", "#161b27", "#1e2535", "#0d1929"
BORDER, TEXT, MUTED, MUTED2 = "#2a3a55", "#e6edf3", "#4a6080", "#8ba0b8"
C_FAME, C_ACTIVITY = "#f5a623", "#06d6a0"
CH_BLUE, CH_ORANGE, CH_TEAL, CH_RED = "#4da6ff", "#f5a623", "#06d6a0", "#ff4d6d"
C_4W = "#a78bfa"
FONT, TITLEF = "'Rajdhani', sans-serif", "'Orbitron', sans-serif"

# ── Table column definitions ───────────────────────────────────────────────────
_C = lambda n: {"name": n, "id": n}
T_COLS_PERIOD = [_C("#"),_C("Name"),_C("Avg Medals/Stage"),_C("Avg Medals/Game"),_C("Total Missed"),_C("Entries")]
T_COLS_LAST   = [_C("#"),_C("Name"),_C("Last Total Medals"),_C("Last Medals/Game"),_C("Last Missed"),_C("Entries")]
T_COLS_4W     = T_COLS_PERIOD

_COND_PERIOD = {
    "Avg Medals/Game":  ("{Avg Medals/Game} < 150",  "{Avg Medals/Game} >= 165"),
    "Total Missed":     ("{Total Missed} >= 5",       "{Total Missed} = 0"),
    "Avg Medals/Stage": ("{Avg Medals/Stage} < 2400", "{Avg Medals/Stage} >= 2600"),
}
_COND_LAST = {
    "Last Medals/Game":  ("{Last Medals/Game} < 150",   "{Last Medals/Game} >= 165"),
    "Last Missed":       ("{Last Missed} >= 5",          "{Last Missed} = 0"),
    "Last Total Medals": ("{Last Total Medals} < 2400",  "{Last Total Medals} >= 2600"),
}

T_CELL = {
    "backgroundColor": CARD2, "color": TEXT, "fontFamily": FONT,
    "fontSize": "0.74rem", "border": f"1px solid {BORDER}",
    "padding": "5px 6px", "textAlign": "center", "whiteSpace": "nowrap",
}
T_CELL_COND = [
    {"if": {"column_id": "Name"}, "textAlign": "left", "maxWidth": "100px",
     "overflow": "hidden", "textOverflow": "ellipsis", "color": CH_BLUE},
    {"if": {"column_id": "#"}, "width": "22px", "color": MUTED2, "fontSize": "0.68rem"},
]
T_HEADER = {
    "backgroundColor": "#0a1322", "color": C_FAME, "fontWeight": "700",
    "fontFamily": FONT, "fontSize": "0.62rem", "letterSpacing": "0.05em",
    "border": f"1px solid {BORDER}", "textAlign": "center", "padding": "6px 4px",
}

# ── Button styles (3-way toggle, all combinations precomputed) ─────────────────
_BTN = {"fontFamily": FONT, "fontSize": "0.6rem", "fontWeight": "700",
        "letterSpacing": "0.06em", "textTransform": "uppercase",
        "padding": "6px 4px", "cursor": "pointer", "whiteSpace": "nowrap",
        "flex": "1", "textAlign": "center"}

def _btn_style(mode_for, current_mode, position):
    """Return button style based on whether it's active, and pill position."""
    color_map = {"period": CH_TEAL, "4w": C_4W, "last": CH_ORANGE}
    radius = {"l": "4px 0 0 4px", "m": "0", "r": "0 4px 4px 0"}[position]
    base = {**_BTN, "borderRadius": radius}
    if position != "l":
        base["borderLeft"] = "none"
    if mode_for == current_mode:
        c = color_map[mode_for]
        base.update({"background": c, "color": BG, "border": f"1px solid {c}"})
        if position != "l": base["borderLeft"] = "none"
    else:
        base.update({"background": "transparent", "color": MUTED2,
                     "border": f"1px solid {BORDER}"})
        if position != "l": base["borderLeft"] = "none"
    return base

# ── CSS ────────────────────────────────────────────────────────────────────────
CSS = f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ height: 100%; background: {BG}; font-family: {FONT}; color: {TEXT}; overflow: hidden; }}
:root {{
    --Dash-Fill-Inverse-Strong: {CARD};
    --Dash-Fill-Inverse-Weak:   {CARD};
    --Dash-Stroke-Strong:       {BORDER};
    --Dash-Fill-Disabled:       {BORDER};
    --Dash-Text-Strong:         {TEXT};
    --Dash-Text-Weak:           {MUTED2};
    --Dash-Text-Disabled:       {MUTED};
    --Dash-Fill-Interactive-Strong: {CH_BLUE};
    --Dash-Fill-Interactive-Weak:   {BORDER};
    --Dash-Shading-Strong: rgba(0,0,0,0.5);
    --Dash-Shading-Weak:   rgba(0,0,0,0.2);
}}
.dash-dropdown {{ background:{CARD}!important; color:{TEXT}!important; border-color:{BORDER}!important; }}
.dash-dropdown-content {{ background:{CARD}!important; border-color:{BORDER}!important; z-index:9999!important; max-height:50vh!important; }}
.dash-dropdown-option:hover {{ background:{BORDER}!important; }}
.dash-dropdown-search-container {{ background:{CARD2}!important; border-color:{BORDER}!important; }}
.dash-dropdown-search {{ background:transparent!important; color:{TEXT}!important; }}
.dash-dropdown-value-count {{ background:{BORDER}!important; color:{TEXT}!important; }}
::-webkit-scrollbar {{ width:3px; height:3px; }}
::-webkit-scrollbar-track {{ background:{BG}; }}
::-webkit-scrollbar-thumb {{ background:{BORDER}; border-radius:2px; }}
.donut-mini-ring {{
    width: 68px; height: 68px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center; margin: 4px auto;
}}
.donut-mini-core {{
    width: 50px; height: 50px; border-radius: 50%;
    background: {CARD_KPI}; display: flex; align-items: center; justify-content: center;
}}
"""

# ── App ────────────────────────────────────────────────────────────────────────
app = Dash(__name__, external_stylesheets=[
    dbc.themes.BOOTSTRAP,
    "https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Orbitron:wght@700;900&display=swap",
], suppress_callback_exceptions=True)
app.title = "Clan War · Mobile"
server = app.server  # required for gunicorn
app.index_string = f"""<!DOCTYPE html>
<html><head>{{%metas%}}<title>{{%title%}}</title>{{%favicon%}}{{%css%}}
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<style>{CSS}</style></head>
<body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body></html>"""

TILE = {"background": CARD, "border": f"1px solid {BORDER}", "borderRadius": "10px", "padding": "10px 12px"}
TILE_CHART = {"background": CARD, "border": f"1px solid {BORDER}", "borderRadius": "10px", "padding": "8px 4px 4px 4px"}

# ── Helpers ────────────────────────────────────────────────────────────────────
def m_donut(label, value, color, pct, rec=None):
    deg = max(5, min(pct / 100 * 360, 360))
    return html.Div([
        html.Div(label, style={"fontSize": "0.55rem", "color": MUTED2, "letterSpacing": "0.06em",
                               "textTransform": "uppercase", "textAlign": "center", "fontWeight": "700"}),
        html.Div(className="donut-mini-ring",
                 style={"background": f"conic-gradient({color} {deg}deg,#1a2740 {deg}deg)"},
                 children=[html.Div(className="donut-mini-core", children=[
                     html.Span(value, style={"fontFamily": TITLEF, "fontSize": "0.62rem",
                                             "fontWeight": "900", "color": color,
                                             "textAlign": "center", "lineHeight": "1.1",
                                             "padding": "0 2px"})])]),
        html.Div(rec if rec else "", style={"fontSize": "0.55rem", "color": MUTED2, "textAlign": "center", "lineHeight": "1.2", "marginTop": "2px"}),
    ], style={"background": CARD_KPI, "borderRadius": "8px", "border": f"1px solid {BORDER}",
              "borderTop": f"2px solid {color}", "padding": "8px 4px", "textAlign": "center"})

def base_fig_mobile():
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=CARD2,
        font=dict(family=FONT, color=TEXT, size=10),
        margin=dict(l=22, r=22, t=8, b=28),
        hovermode="x unified", autosize=True,
        hoverlabel=dict(bgcolor="#1a2535", bordercolor=BORDER,
                        font=dict(color=TEXT, size=11, family=FONT)),
        showlegend=False, dragmode="pan",
    )
    return fig

def apply_x_m(fig, stages):
    fig.update_xaxes(tickvals=stages, ticktext=stages, tickangle=-45,
                     tickfont=dict(size=8, color=MUTED2),
                     gridcolor=BORDER, showgrid=False, zeroline=False, linecolor=BORDER)

def highlight_shapes_m(sel_set, hl_color="rgba(100,200,180,0.12)"):
    if not sel_set: return []
    idxs = sorted(STAGE_IDX[s] for s in sel_set if s in STAGE_IDX)
    if not idxs: return []
    groups, start, end = [], idxs[0], idxs[0]
    for i in idxs[1:]:
        if i == end+1: end = i
        else: groups.append((start,end)); start = end = i
    groups.append((start, end))
    return [dict(type="rect", xref="x", yref="paper", x0=s-0.45, x1=e+0.45,
                 y0=0, y1=1, fillcolor=hl_color, line=dict(width=0), layer="below")
            for s, e in groups]

# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT — both tabs always rendered in DOM, only visibility toggled
# ══════════════════════════════════════════════════════════════════════════════
TAB_VIS_STYLE   = {"display": "block"}
TAB_HIDE_STYLE  = {"display": "none"}

app.layout = html.Div(style={
    "background": BG, "height": "100vh", "display": "flex", "flexDirection": "column",
    "overflow": "hidden", "fontFamily": FONT, "color": TEXT,
}, children=[
    dcc.Store(id="m-tab",  data="visuals"),
    dcc.Store(id="m-mode", data="period"),

    # Header
    html.Div(style={
        "flex": "0 0 auto", "background": CARD, "borderBottom": f"1px solid {BORDER}",
        "padding": "8px 14px 6px", "display": "flex",
        "justifyContent": "space-between", "alignItems": "center",
    }, children=[
        html.Div([
            html.Div("⚔ CLAN WAR", style={"fontFamily": TITLEF, "fontSize": "1rem",
                     "fontWeight": "900", "color": C_FAME, "letterSpacing": "0.05em"}),
            html.Div(id="m-viewing-label", children="Clan #CGLPJ9",
                     style={"fontSize": "0.6rem", "color": MUTED2, "marginTop": "1px"}),
        ]),
        html.Div([
            html.Span(f"{len(STAGES)}", style={"fontFamily": TITLEF, "color": CH_TEAL, "fontSize": "0.78rem"}),
            html.Span(" stages  ", style={"color": MUTED2, "fontSize": "0.65rem"}),
            html.Span(f"{len(all_tags)}", style={"fontFamily": TITLEF, "color": CH_ORANGE, "fontSize": "0.78rem"}),
            html.Span(" members", style={"color": MUTED2, "fontSize": "0.65rem"}),
        ]),
    ]),

    # ── Tab bar ────────────────────────────────────────────────────────────────
    html.Div(id="m-tab-bar", style={"flex": "0 0 auto", "display": "flex",
                                     "background": CARD, "borderBottom": f"2px solid {BORDER}"},
             children=[
        html.Button("📊  VISUALS", id="m-tab-vis", n_clicks=0,
                    style={**_BTN, "padding": "10px 4px",
                           "borderBottom": f"2px solid {CH_TEAL}", "color": CH_TEAL,
                           "background": "transparent", "borderRadius": "0",
                           "borderTop": "none", "borderLeft": "none",
                           "borderRight": f"1px solid {BORDER}", "marginBottom": "-2px"}),
        html.Button("👥  PLAYERS", id="m-tab-players", n_clicks=0,
                    style={**_BTN, "padding": "10px 4px",
                           "borderBottom": "2px solid transparent", "color": MUTED2,
                           "background": "transparent", "borderRadius": "0",
                           "border": "none", "marginBottom": "-2px"}),
    ]),

    # ── TAB 1: VISUALS ─────────────────────────────────────────────────────────
    html.Div(id="m-tab-visuals", style={
        "flex": "1", "minHeight": "0", "overflowY": "auto", "overflowX": "hidden",
        "padding": "10px 6px 16px", "display": "block",
    }, children=[
        # Persistent filters at top
        html.Div(style={"display": "flex", "gap": "8px", "marginBottom": "10px"}, children=[
            html.Div(style={"flex": "1"}, children=[
                html.Label("STAGES", style={"fontSize":"0.55rem","color":MUTED2,
                           "letterSpacing":"0.1em","display":"block","marginBottom":"3px"}),
                dcc.Dropdown(id="m-stage-select", options=stage_opts, multi=True,
                             placeholder="All stages…",
                             style={"fontFamily":FONT,"fontSize":"0.78rem",
                                    "backgroundColor":CARD,"color":TEXT}),
            ]),
            html.Div(style={"flex": "1"}, children=[
                html.Label("PLAYER", style={"fontSize":"0.55rem","color":MUTED2,
                           "letterSpacing":"0.1em","display":"block","marginBottom":"3px"}),
                dcc.Dropdown(id="m-player-filter", options=player_opts, multi=True,
                             placeholder="All players…",
                             style={"fontFamily":FONT,"fontSize":"0.78rem",
                                    "backgroundColor":CARD,"color":TEXT}),
            ]),
        ]),

        # Segment 1: Donut grid 3×2
        html.Div(style={**TILE, "marginBottom":"10px"}, children=[
            html.Div("LAST STAGE STATS", style={"fontSize":"0.6rem","color":MUTED2,
                     "letterSpacing":"0.1em","fontWeight":"700","marginBottom":"8px"}),
            html.Div(id="m-donuts", style={
                "display":"grid","gridTemplateColumns":"1fr 1fr 1fr","gap":"8px",
            }),
        ]),

        # Segment 2: Activity & Medals/Game chart
        html.Div(style={**TILE_CHART, "marginBottom":"10px"}, children=[
            html.Div(style={"display":"flex","gap":"12px","marginBottom":"2px","padding":"0 8px"}, children=[
                html.Span("● Activity %",  style={"fontSize":"0.65rem","color":CH_BLUE,"fontWeight":"600"}),
                html.Span("● Medals/Game", style={"fontSize":"0.65rem","color":CH_ORANGE,"fontWeight":"600"}),
            ]),
            dcc.Graph(id="m-chart-activity",
                      config={"displayModeBar":False,"responsive":True,"scrollZoom":True},
                      style={"height":"36vh","width":"100%"}),
        ]),

        # Segment 3: Fame & Missed Attacks chart
        html.Div(style={**TILE_CHART, "marginBottom":"10px"}, children=[
            html.Div(style={"display":"flex","gap":"12px","marginBottom":"2px","padding":"0 8px"}, children=[
                html.Span("● Missed",   style={"fontSize":"0.65rem","color":CH_RED, "fontWeight":"600"}),
                html.Span("● Fame",     style={"fontSize":"0.65rem","color":CH_TEAL,"fontWeight":"600"}),
            ]),
            dcc.Graph(id="m-chart-fame",
                      config={"displayModeBar":False,"responsive":True,"scrollZoom":True},
                      style={"height":"36vh","width":"100%"}),
        ]),

        # Segment 4: Raw data table (CHANGE 3)
        html.Div(style={**TILE}, children=[
            html.Div("RAW DATA", style={"fontSize":"0.6rem","color":MUTED2,
                     "letterSpacing":"0.1em","fontWeight":"700","marginBottom":"8px"}),
            html.Div(style={"overflowY":"auto","overflowX":"auto","maxHeight":"45vh"}, children=[
                dash_table.DataTable(
                    id="m-raw-dt", data=[], columns=[
                        {"name":"Stage","id":"stage"},
                        {"name":"Player","id":"player name"},
                        {"name":"Medals","id":"fame"},
                        {"name":"Decks","id":"decks used"},
                        {"name":"M/Deck","id":"medals_per_deck"},
                    ],
                    page_action="none", sort_action="native",
                    style_table={"width":"100%","overflowX":"auto"},
                    style_cell={**T_CELL, "fontSize":"0.7rem","padding":"4px 6px"},
                    style_cell_conditional=[
                        {"if":{"column_id":"player name"}, "textAlign":"left", "maxWidth":"110px",
                         "overflow":"hidden","textOverflow":"ellipsis"},
                    ],
                    style_header={**T_HEADER,"fontSize":"0.58rem"},
                    style_data_conditional=[{"if":{"row_index":"odd"},"backgroundColor":"#0a1322"}],
                ),
            ]),
        ]),
    ]),

    # ── TAB 2: PLAYERS ─────────────────────────────────────────────────────────
    html.Div(id="m-tab-players-content", style={
        "flex": "1", "minHeight": "0", "overflowY": "auto", "overflowX": "hidden",
        "padding": "10px 10px 16px", "display": "none",
    }, children=[
        # Toggle buttons (3-way)
        html.Div(style={"display":"flex","marginBottom":"10px"}, children=[
            html.Button(f"All stages",        id="m-toggle",      n_clicks=0,
                        style=_btn_style("period","period","l")),
            html.Button("Last 4 weeks",       id="m-toggle-4w",   n_clicks=0,
                        style=_btn_style("4w",   "period","m")),
            html.Button(f"Last ({STAGES[-1]})", id="m-toggle-last", n_clicks=0,
                        style=_btn_style("last", "period","r")),
        ]),
        # Table container
        html.Div(style={"overflowY":"auto","overflowX":"auto"}, children=[
            dash_table.DataTable(
                id="m-player-dt",
                columns=T_COLS_PERIOD, data=[],
                sort_action="custom",
                sort_by=[{"column_id":"Avg Medals/Stage","direction":"desc"}],
                page_action="none",
                style_table={"width":"100%","overflowX":"auto"},
                style_cell=T_CELL, style_cell_conditional=T_CELL_COND,
                style_header=T_HEADER,
                style_data_conditional=[{"if":{"row_index":"odd"},"backgroundColor":"#0a1322"}],
            ),
        ]),
    ]),
])

# ══════════════════════════════════════════════════════════════════════════════
# CALLBACKS
# ══════════════════════════════════════════════════════════════════════════════

# ── Tab switching: just toggles visibility ────────────────────────────────────
@app.callback(
    Output("m-tab",                  "data"),
    Output("m-tab-visuals",          "style"),
    Output("m-tab-players-content",  "style"),
    Output("m-tab-vis",              "style"),
    Output("m-tab-players",          "style"),
    Input("m-tab-vis",     "n_clicks"),
    Input("m-tab-players", "n_clicks"),
    prevent_initial_call=True,
)
def switch_tab(n_v, n_p):
    triggered = ctx.triggered_id
    show_vis  = triggered == "m-tab-vis"
    tab_data  = "visuals" if show_vis else "players"
    vis_style    = {"flex":"1","minHeight":"0","overflowY":"auto","overflowX":"hidden",
                    "padding":"10px 6px 16px","display":"block" if show_vis else "none"}
    play_style   = {"flex":"1","minHeight":"0","overflowY":"auto","overflowX":"hidden",
                    "padding":"10px 10px 16px","display":"none" if show_vis else "block"}
    btn_active   = {**_BTN, "padding":"10px 4px",
                    "borderBottom":f"2px solid {CH_TEAL}", "color":CH_TEAL,
                    "background":"transparent", "borderRadius":"0",
                    "borderTop":"none","borderLeft":"none",
                    "borderRight":f"1px solid {BORDER}", "marginBottom":"-2px"}
    btn_inactive = {**_BTN, "padding":"10px 4px",
                    "borderBottom":"2px solid transparent", "color":MUTED2,
                    "background":"transparent", "borderRadius":"0",
                    "border":"none", "marginBottom":"-2px"}
    if show_vis:
        return tab_data, vis_style, play_style, btn_active, btn_inactive
    else:
        return tab_data, vis_style, play_style, btn_inactive, btn_active


# ── Visuals tab: donuts + 2 charts ────────────────────────────────────────────
@app.callback(
    Output("m-donuts",          "children"),
    Output("m-chart-activity",  "figure"),
    Output("m-chart-fame",      "figure"),
    Input("m-stage-select",  "value"),
    Input("m-player-filter", "value"),
)
def update_visuals(stage_val, sel_tags):
    sel_stages = sorted(stage_val, key=stage_key) if stage_val else STAGES
    sel_set    = set(sel_stages)
    has_filter = len(sel_stages) < len(STAGES)
    single     = sel_tags and len(sel_tags) == 1

    sa = (df_raw.groupby("stage").agg(td=("decks used","sum"), tf=("fame","sum"))
                .reindex(STAGES).fillna(0))
    sa["activity_pct"]    = (sa["td"] / MAX_CLAN * 100).round(1)
    sa["medals_per_game"] = (sa["tf"] / sa["td"].replace(0,1)).round(1)
    sa["miss_attacks"]    = (MAX_CLAN - sa["td"]).clip(lower=0)

    last_s = sel_stages[-1]
    ls     = df_raw[df_raw["stage"] == last_s]

    # KPI donuts
    if single:
        tag       = sel_tags[0]
        row       = ls[ls["player tag"] == tag]
        ls_d      = row["decks used"].sum()
        ls_f      = row["fame"].sum()
        ls_f_clan = ls["fame"].sum()
        ls_mpg    = (ls_f/ls_d) if ls_d else 0
        ls_act    = ls_d/MAX_PLAYER*100
        ls_miss   = max(0, MAX_PLAYER-ls_d)
        pr        = _player_records(tag)
        nm_kpi = latest_name.get(tag, tag)
        donuts = [
            m_donut("Clanmedals",    _nl_int(ls_f_clan), CH_TEAL,   ls_f_clan/180000*100, f"Clan record = {_nl_int(RECORD_FAME)}"),
            m_donut("Medals/Game",   _nl_dec(ls_mpg),    CH_ORANGE, ls_mpg/225*100,       f"{nm_kpi} best = {_nl_dec(pr.get('mpg',RECORD_MPG))}"),
            m_donut("Players",       "1",                "#9b59b6", 100),
            m_donut("Activity",      _nl_pct(ls_act),    CH_BLUE,   ls_act,               f"{nm_kpi} best = {_nl_pct(pr.get('activity',RECORD_ACTIVITY))}"),
            m_donut("Medals/Player", _nl_int(ls_f),      "#fe6c35", ls_f/3600*100,        f"{nm_kpi} best = {_nl_int(pr.get('fame',RECORD_MPP))}"),
            m_donut("Missed Atks",   _nl_int(ls_miss),   CH_RED,    ls_miss/MAX_PLAYER*100,f"{nm_kpi} best = {pr.get('miss',RECORD_MISS)}"),
        ]
    else:
        ls_d   = ls["decks used"].sum(); ls_f = ls["fame"].sum()
        ls_p   = ls["player tag"].nunique()
        ls_mpg = (ls_f/ls_d) if ls_d else 0
        ls_act = ls_d/MAX_CLAN*100
        ls_mpp = (ls_f/ls_p) if ls_p else 0
        ls_miss = MAX_CLAN-ls_d
        donuts = [
            m_donut("Clanmedals",    _nl_int(ls_f),   CH_TEAL,   ls_f/180000*100,   f"Clan record = {_nl_int(RECORD_FAME)}"),
            m_donut("Medals/Game",   _nl_dec(ls_mpg), CH_ORANGE, ls_mpg/225*100,    f"Clan record = {_nl_dec(RECORD_MPG)}"),
            m_donut("Players",       str(ls_p),       "#9b59b6", ls_p/50*100),
            m_donut("Activity",      _nl_pct(ls_act), CH_BLUE,   ls_act,            f"Clan record = {_nl_pct(RECORD_ACTIVITY)}"),
            m_donut("Medals/Player", _nl_int(ls_mpp), "#fe6c35", ls_mpp/3600*100,   f"Clan record = {_nl_int(RECORD_MPP)}"),
            m_donut("Missed Atks",   _nl_int(ls_miss),CH_RED,    ls_miss/MAX_CLAN*100,f"Clan record = {RECORD_MISS}"),
        ]

    # Chart data
    x      = list(STAGES)
    shapes = highlight_shapes_m(sel_set if has_filter else set())

    if single:
        tag    = sel_tags[0]
        p_df   = df_raw[df_raw["player tag"]==tag].set_index("stage").reindex(STAGES)
        y_act  = (p_df["decks used"]/MAX_PLAYER*100).round(1)
        y_mpg  = (p_df["fame"]/p_df["decks used"].replace(0,1)).round(1)
        y_miss = (MAX_PLAYER-p_df["decks used"]).clip(lower=0)
        y_fame = p_df["fame"]
        act_rng = [0,115]; miss_max = MAX_PLAYER*1.7
        fame_rng = [0, y_fame.max()*1.15+1]
    else:
        y_act  = sa["activity_pct"]; y_mpg  = sa["medals_per_game"]
        y_miss = sa["miss_attacks"]; y_fame = sa["tf"]
        act_rng = [60,115]; miss_max = max(sa["miss_attacks"].max()*1.65,50)
        fame_rng = [sa["tf"].min()*0.92, sa["tf"].max()*1.07]

    # Chart 1: Activity + Medals/Game
    fig1 = base_fig_mobile()
    fig1.add_trace(go.Scatter(x=x, y=list(y_mpg), mode="lines+markers+text",
        line=dict(color=CH_ORANGE,width=2), marker=dict(size=5,color=CH_ORANGE),
        text=[str(int(v)) if pd.notna(v) else "" for v in y_mpg], textposition="bottom center",
        textfont=dict(color=CH_ORANGE, size=9),
        customdata=[f"{int(v):,}" if pd.notna(v) else "" for v in y_mpg],
        hovertemplate="<b>Medals/Game</b>: %{customdata}<extra></extra>",
        yaxis="y2", showlegend=False))
    fig1.add_trace(go.Scatter(x=x, y=list(y_act), mode="lines+markers+text",
        line=dict(color=CH_BLUE,width=2), marker=dict(size=5,color=CH_BLUE),
        text=[f"{v:.0f}%" for v in y_act], textposition="top center",
        textfont=dict(color=CH_BLUE, size=9),
        customdata=[f"{v:.1f}".replace(".",",")+"%" for v in y_act],
        hovertemplate="<b>Activity</b>: %{customdata}<extra></extra>",
        yaxis="y1", showlegend=False))
    # Window: last 16 stages by default
    x_win_lo = max(0, len(STAGES) - 16) - 0.5
    x_win_hi = len(STAGES) - 0.5
    fig1.update_layout(
        yaxis=dict(range=act_rng, ticksuffix="%", gridcolor=BORDER, showgrid=True,
                   zeroline=False, tickfont=dict(size=9,color=MUTED2)),
        yaxis2=dict(overlaying="y", side="right", showgrid=False, zeroline=False,
                    range=[y_mpg.min()*0.78, y_mpg.max()*1.22], tickfont=dict(size=9,color=MUTED2)),
        xaxis=dict(range=[x_win_lo, x_win_hi]),
        shapes=shapes)
    if single: fig1.update_traces(connectgaps=False, selector=dict(type="scatter"))
    apply_x_m(fig1, x)

    # Chart 2: Fame + Missed
    fig2 = base_fig_mobile()
    fig2.add_trace(go.Bar(x=x, y=list(y_miss), marker_color=CH_RED, opacity=0.8,
        text=[str(int(v)) if pd.notna(v) else "" for v in y_miss], textposition="outside",
        textfont=dict(color=CH_RED, size=9),
        customdata=[f"{int(v):,}" if pd.notna(v) else "" for v in y_miss],
        hovertemplate="<b>Missed</b>: %{customdata}<extra></extra>",
        yaxis="y1", showlegend=False))
    fig2.add_trace(go.Scatter(x=x, y=list(y_fame), mode="lines+markers+text",
        line=dict(color=CH_TEAL,width=2), marker=dict(size=5,color=CH_TEAL),
        text=[_nl_k(v) if pd.notna(v) else "" for v in y_fame], textposition="top center",
        textfont=dict(color=CH_TEAL, size=9),
        customdata=[f"{int(v):,}" if pd.notna(v) else "" for v in y_fame],
        hovertemplate="<b>Fame</b>: %{customdata}<extra></extra>",
        yaxis="y2", showlegend=False))
    fig2.update_layout(
        barmode="overlay",
        yaxis=dict(range=[0,miss_max], gridcolor=BORDER, showgrid=True,
                   zeroline=True, zerolinecolor=BORDER, tickfont=dict(size=9,color=MUTED2)),
        yaxis2=dict(overlaying="y", side="right", showgrid=False, zeroline=False,
                    range=fame_rng, tickfont=dict(size=9,color=MUTED2)),
        xaxis=dict(range=[x_win_lo, x_win_hi]),
        shapes=shapes)
    if single: fig2.update_traces(connectgaps=False, selector=dict(type="scatter"))
    apply_x_m(fig2, x)

    return donuts, fig1, fig2


# ── Players tab: table + 3 toggle buttons ────────────────────────────────────
@app.callback(
    Output("m-player-dt",     "data"),
    Output("m-player-dt",     "columns"),
    Output("m-player-dt",     "style_data_conditional"),
    Output("m-mode",          "data"),
    Output("m-toggle",        "style"),
    Output("m-toggle-4w",     "style"),
    Output("m-toggle-last",   "style"),
    Input("m-toggle",         "n_clicks"),
    Input("m-toggle-4w",      "n_clicks"),
    Input("m-toggle-last",    "n_clicks"),
    Input("m-player-dt",      "sort_by"),
    State("m-mode",           "data"),
)
def update_players(n_p, n_4, n_l, sort_by, stored_mode):
    triggered = ctx.triggered_id
    MODE_MAP = {"m-toggle":"period","m-toggle-4w":"4w","m-toggle-last":"last"}
    mode = MODE_MAP.get(triggered, stored_mode or "period")

    if mode == "period":
        p_agg      = _period_table(df_raw)
        cond_map   = _COND_PERIOD
        t_cols_out = T_COLS_PERIOD
        use_cols   = ["#","Name","Tag","Avg Medals/Stage","Avg Medals/Game","Total Missed","Entries"]
        default_sb = [{"column_id":"Avg Medals/Stage","direction":"desc"}]
    elif mode == "4w":
        p_agg      = _period_table(df_raw[df_raw["stage"].isin(STAGES[-4:])])
        cond_map   = _COND_PERIOD
        t_cols_out = T_COLS_4W
        use_cols   = ["#","Name","Tag","Avg Medals/Stage","Avg Medals/Game","Total Missed","Entries"]
        default_sb = [{"column_id":"Avg Medals/Stage","direction":"desc"}]
    else:
        p_agg = pd.DataFrame({"Tag": list(ACTIVE_TAGS)})
        p_agg["Last Medals/Game"]  = p_agg["Tag"].map(lambda t: int(round(LG_FAME.get(t,0)/max(LG_DECKS.get(t,1),1))))
        p_agg["Last Missed"]       = p_agg["Tag"].map(lambda t: max(0,MAX_PLAYER-LG_DECKS.get(t,0)))
        p_agg["Last Total Medals"] = p_agg["Tag"].map(lambda t: LG_FAME.get(t,0))
        p_agg["Entries"]           = p_agg["Tag"].map(lambda t: total_entries_map.get(t,0))
        p_agg["Name"]              = p_agg["Tag"].map(latest_name)
        cond_map   = _COND_LAST
        t_cols_out = T_COLS_LAST
        use_cols   = ["#","Name","Tag","Last Total Medals","Last Medals/Game","Last Missed","Entries"]
        default_sb = [{"column_id":"Last Total Medals","direction":"desc"}]

    sb = ([s for s in sort_by if s["column_id"] in p_agg.columns] if sort_by else []) or default_sb
    p_agg = p_agg.sort_values([s["column_id"] for s in sb],
                               ascending=[s["direction"]=="asc" for s in sb],
                               na_position="last").reset_index(drop=True)
    p_agg["#"] = range(1, len(p_agg)+1)

    cond = [{"if":{"row_index":"odd"},"backgroundColor":"#0a1322"}]
    for col,(red_q,green_q) in cond_map.items():
        cond += [{"if":{"filter_query":red_q,  "column_id":col},"backgroundColor":"#3a0a12"},
                 {"if":{"filter_query":green_q,"column_id":col},"backgroundColor":"#0d2e1a"}]

    return (p_agg[use_cols].to_dict("records"), t_cols_out, cond, mode,
            _btn_style("period", mode, "l"),
            _btn_style("4w",     mode, "m"),
            _btn_style("last",   mode, "r"))



# ── Player selected from Players table → switch to Visuals + set filter ────────
@app.callback(
    Output("m-player-filter",         "value"),
    Output("m-tab-visuals",           "style", allow_duplicate=True),
    Output("m-tab-players-content",   "style", allow_duplicate=True),
    Output("m-tab-vis",               "style", allow_duplicate=True),
    Output("m-tab-players",           "style", allow_duplicate=True),
    Output("m-tab",                   "data",  allow_duplicate=True),
    Input("m-player-dt",              "active_cell"),
    State("m-player-dt",              "data"),
    State("m-player-filter",          "value"),
    prevent_initial_call=True,
)
def on_table_click(active_cell, data, current):
    if not active_cell or active_cell.get("column_id") != "Name" or not data:
        return (no_update,) * 6
    idx = active_cell["row"]
    if idx >= len(data): return (no_update,) * 6
    tag = data[idx].get("Tag")
    if not tag: return (no_update,) * 6
    # Toggle: clicking same player clears filter
    new_val = [] if current == [tag] else [tag]
    vis_style  = {"flex":"1","minHeight":"0","overflowY":"auto","overflowX":"hidden",
                  "padding":"10px 6px 16px","display":"block"}
    play_style = {"flex":"1","minHeight":"0","overflowY":"auto","overflowX":"hidden",
                  "padding":"10px 10px 16px","display":"none"}
    btn_active   = {**_BTN, "padding":"10px 4px",
                    "borderBottom":f"2px solid {CH_TEAL}", "color":CH_TEAL,
                    "background":"transparent", "borderRadius":"0",
                    "borderTop":"none","borderLeft":"none",
                    "borderRight":f"1px solid {BORDER}", "marginBottom":"-2px"}
    btn_inactive = {**_BTN, "padding":"10px 4px",
                    "borderBottom":"2px solid transparent", "color":MUTED2,
                    "background":"transparent", "borderRadius":"0",
                    "border":"none", "marginBottom":"-2px"}
    return new_val, vis_style, play_style, btn_active, btn_inactive, "visuals"


# ── Header "Viewing" label (reflects selected player) ─────────────────────────
@app.callback(
    Output("m-viewing-label", "children"),
    Input("m-player-filter",  "value"),
)
def update_viewing(sel_tags):
    if sel_tags and len(sel_tags) == 1:
        nm = latest_name.get(sel_tags[0], sel_tags[0])
        return f"Viewing: {nm}"
    return "Clan #CGLPJ9"



# ── Raw data table (Tab 1 bottom) — respects stage + player filters ──────────
@app.callback(
    Output("m-raw-dt", "data"),
    Input("m-stage-select",  "value"),
    Input("m-player-filter", "value"),
)
def update_raw(stage_val, sel_tags):
    sel_stages = sorted(stage_val, key=stage_key) if stage_val else STAGES
    df = df_raw[df_raw["stage"].isin(sel_stages)].copy()
    if sel_tags and len(sel_tags) == 1:
        df = df[df["player tag"] == sel_tags[0]]
        df["medals_per_deck"] = (df["fame"] / df["decks used"].replace(0, 1)).round(1)
        df = df.sort_values("stage", key=lambda x: x.map(stage_key), ascending=False)
        return df[["stage","player name","fame","decks used","medals_per_deck"]].to_dict("records")
    # Clan aggregate per stage
    g = df.groupby("stage").agg(fame=("fame","sum"),
                                 decks=("decks used","sum")).reset_index()
    g["medals_per_deck"] = (g["fame"] / g["decks"].replace(0,1)).round(1)
    g["player name"]     = "HollandseNieuwe"
    g = g.rename(columns={"decks":"decks used"})
    g["_k"] = g["stage"].map(stage_key)
    g = g.sort_values("_k", ascending=False).drop(columns="_k")
    return g[["stage","player name","fame","decks used","medals_per_deck"]].to_dict("records")


if __name__ == "__main__":
    print("\n  Mobile Dashboard → http://localhost:8051\n")
    app.run(debug=False, port=8051)
