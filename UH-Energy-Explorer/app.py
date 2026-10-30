
from pathlib import Path

import pandas as pd
import plotly.express as px

from dash import (
    Dash,
    dcc,
    html,
    Input,
    Output,
    State,
    callback
)

# --------------------------------------------------
# APPLICATION CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = (
    BASE_DIR
    / "data"
    / "Usage&Generation_simplified_FY24_25_rev1.xlsx"
)

app = Dash(__name__, assets_folder="style")
app.title = "UH Systems Data Energy Reports"

server = app.server

# --------------------------------------------------
# LOAD EXCEL DATA
# --------------------------------------------------

def load_data(path):
    return pd.read_excel(
        path,
        sheet_name="Sheet1"
    )


try:
    raw = load_data(DATA_PATH)
except (FileNotFoundError, ValueError, ImportError) as error:
    raise RuntimeError(
        f"Unable to load workbook: {error}"
    ) from error

# --------------------------------------------------
# VALIDATE DATA
# --------------------------------------------------

needed = {"Type", "Campus affiliation"}

years = [
    col for col in raw.columns
    if isinstance(col, str) and col.startswith("FY")
]

if not needed.issubset(raw.columns) or not years:
    raise ValueError(
        "Expected columns: Type, Campus affiliation, "
        "and FY fiscal-year columns."
    )

# --------------------------------------------------
# CLEAN AND RESHAPE DATA
# --------------------------------------------------

clean = raw.dropna(
    subset=["Type", "Campus affiliation"]
).copy()

clean["Type"] = (
    clean["Type"]
    .astype(str)
    .str.strip()
)

clean["Campus affiliation"] = (
    clean["Campus affiliation"]
    .astype(str)
    .str.strip()
)

# Exclude precomputed totals
clean = clean[
    ~clean["Type"].str.lower().eq("total")
]

clean = clean[
    ~clean["Campus affiliation"].str.upper().eq("ALL")
]

long = clean.melt(
    id_vars=["Type", "Campus affiliation"],
    value_vars=years,
    var_name="Fiscal year",
    value_name="Value"
)

long["Value"] = pd.to_numeric(
    long["Value"],
    errors="coerce"
)

long = long.dropna(subset=["Value"])

if long.empty:
    raise ValueError(
        "No numeric observations were found."
    )

# --------------------------------------------------
# DEFAULT VALUES
# --------------------------------------------------

metrics = sorted(
    long["Type"].unique()
)

default_metric = (
    "Production (kWh)"
    if "Production (kWh)" in metrics
    else metrics[0]
)

campuses = sorted(
    long["Campus affiliation"].unique()
)

preferred_campuses = [
    "UH Manoa",
    "Honolulu CC",
    "Kapiolani CC"
]

default_campuses = [
    campus
    for campus in preferred_campuses
    if campus in campuses
]

colors = [
    "#85b5a2",
    "#357d34",
    "#8b9fbc",
    "#142dba",
    "#5931dd",
    "#0f6a0c",
    "#a0a9ac"
]

color_map = {
    campus: colors[i % len(colors)]
    for i, campus in enumerate(campuses)
}

# --------------------------------------------------
# APPLICATION LAYOUT
# --------------------------------------------------

app.layout = html.Div(
    className="app-container",
    children=[

        # SIDEBAR
        html.Aside(
            className="sidebar",
            children=[

                html.Div(
                    "UH SYSTEMS DATA ENERGY REPORTS",
                    className="sidebar-brand"
                ),

                html.Label(
                    "Energy measurement",
                    className="control-label"
                ),

                dcc.Dropdown(
                    id="metric-select",
                    options=[
                        {"label": m, "value": m}
                        for m in metrics
                    ],
                    value=default_metric,
                    clearable=False
                ),

                html.Label(
                    "Chart type",
                    className="control-label"
                ),

                dcc.RadioItems(
                    id="chart-type",
                    options=[
                        {"label": "Line", "value": "Line"},
                        {"label": "Bar", "value": "Bar"}
                    ],
                    value="Line",
                    inline=True,
                    className="radio-options"
                ),

                html.Label(
                    "Fiscal year range",
                    className="control-label"
                ),

                # Slider is now present in the initial layout.
                dcc.RangeSlider(
                    id="year-range",
                    min=0,
                    max=len(years) - 1,
                    value=[0, len(years) - 1],
                    step=1,
                    marks={
                        i: str(year)
                        for i, year in enumerate(years)
                    },
                    allowCross=False
                ),

                html.Button(
                    "Export CSV",
                    id="export-button",
                    className="export-button"
                ),

                dcc.Download(
                    id="download-csv"
                )
            ]
        ),

        # MAIN CONTENT
        html.Main(
            className="main-content",
            children=[

                html.Div(
                    "RESEARCH / DATA EXPLORER",
                    className="small-label"
                ),

                html.H1(
                    "Energy Across Campuses"
                ),

                html.P(
                    "Explore electricity use, generation "
                    "and cost across the University of "
                    "Hawaiʻi system.",
                    className="description"
                ),

                html.Div(
                    className="dashboard-grid",
                    children=[

                        # GRAPH
                        html.Section(
                            className="graph-section",
                            children=[

                                html.H2(
                                    id="graph-title"
                                ),

                                dcc.Graph(
                                    id="energy-graph",
                                    config={
                                        "displayModeBar": False,
                                        "responsive": True
                                    },
                                    style={
                                        "height": "540px"
                                    }
                                ),

                                html.P(
                                    "Source: UH energy workbook · "
                                    "Missing values are omitted, "
                                    "not treated as zero.",
                                    className="chart-caption"
                                )
                            ]
                        ),

                        # CAMPUS SELECTION
                        html.Section(
                            className="campus-section",
                            children=[

                                html.H3(
                                    "Select Campuses"
                                ),

                                dcc.Checklist(
                                    id="campus-select",
                                    options=[
                                        {
                                            "label": campus,
                                            "value": campus
                                        }
                                        for campus in campuses
                                    ],
                                    value=default_campuses,
                                    className="campus-checklist"
                                )
                            ]
                        )
                    ]
                ),

                # UNDERLYING DATA
                html.Details(
                    className="data-details",
                    children=[

                        html.Summary(
                            "Underlying data / export"
                        ),

                        html.Div(
                            id="data-preview"
                        )
                    ]
                )
            ]
        )
    ]
)

# --------------------------------------------------
# FILTER DATA
# --------------------------------------------------

def filter_data(metric, selected, year_range):

    subset = long[
        long["Type"] == metric
    ].copy()

    if year_range is None:
        return subset.iloc[0:0].copy(), years

    start, end = year_range

    chosen = years[start:end + 1]

    view = subset[
        subset["Campus affiliation"].isin(selected or [])
        & subset["Fiscal year"].isin(chosen)
    ].copy()

    view["Fiscal year"] = pd.Categorical(
        view["Fiscal year"],
        categories=years,
        ordered=True
    )

    view = view.sort_values(
        ["Fiscal year", "Campus affiliation"]
    )

    return view, years

# --------------------------------------------------
# INTERACTIVE CHART CALLBACK
# --------------------------------------------------

@callback(
    Output("energy-graph", "figure"),
    Output("graph-title", "children"),
    Output("data-preview", "children"),

    Input("metric-select", "value"),
    Input("chart-type", "value"),
    Input("campus-select", "value"),
    Input("year-range", "value")
)
def update_graph(
    metric,
    chart_kind,
    selected,
    year_range
):

    view, available = filter_data(
        metric,
        selected,
        year_range
    )

    common = dict(
        data_frame=view,
        x="Fiscal year",
        y="Value",
        color="Campus affiliation",
        color_discrete_map=color_map,
        category_orders={
            "Fiscal year": available,
            "Campus affiliation": campuses
        }
    )

    # Create chart
    if chart_kind == "Bar":
        fig = px.bar(
            **common,
            barmode="group"
        )
    else:
        fig = px.line(
            **common,
            markers=True
        )

    # Chart styling
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0b0c0e",
        plot_bgcolor="#0b0c0e",
        font_color="#d7d9d9",
        height=540,
        legend_title_text="Campus",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11)
        ),
        hovermode=(
            "x unified"
            if chart_kind == "Line"
            else "closest"
        ),
        xaxis_title="Fiscal year",
        yaxis_title=metric,
        margin=dict(
            l=25,
            r=25,
            t=50,
            b=25
        )
    )

    fig.update_xaxes(
        showgrid=False
    )

    fig.update_yaxes(
        gridcolor="#25292c",
        zerolinecolor="#3b4145"
    )

    # Empty selection message
    if view.empty:
        fig.add_annotation(
            text="Select campuses with available data",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16)
        )

    # Prepare data table
    display = view.rename(
        columns={
            "Campus affiliation": "Campus",
            "Type": "Metric"
        }
    )[
        ["Campus", "Metric", "Fiscal year", "Value"]
    ].copy()

    display["Fiscal year"] = (
        display["Fiscal year"].astype(str)
    )

    table = html.Div(
        className="table-wrapper",
        children=[

            html.Table(
                children=[

                    html.Thead(
                        html.Tr([
                            html.Th(column)
                            for column in display.columns
                        ])
                    ),

                    html.Tbody([
                        html.Tr([
                            html.Td(str(value))
                            for value in row
                        ])
                        for row in display.itertuples(
                            index=False,
                            name=None
                        )
                    ])
                ],
                className="data-table"
            )
        ]
    )

    return fig, metric, table

# --------------------------------------------------
# CSV EXPORT CALLBACK
# --------------------------------------------------

@callback(
    Output("download-csv", "data"),

    Input("export-button", "n_clicks"),

    State("metric-select", "value"),
    State("campus-select", "value"),
    State("year-range", "value"),

    prevent_initial_call=True
)
def export_csv(
    n_clicks,
    metric,
    selected,
    year_range
):

    view, _ = filter_data(
        metric,
        selected,
        year_range
    )

    display = view.rename(
        columns={
            "Campus affiliation": "Campus",
            "Type": "Metric"
        }
    )[
        ["Campus", "Metric", "Fiscal year", "Value"]
    ].copy()

    display["Fiscal year"] = (
        display["Fiscal year"].astype(str)
    )

    return dcc.send_data_frame(
        display.to_csv,
        "uh_energy_filtered.csv",
        index=False
    )

# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
