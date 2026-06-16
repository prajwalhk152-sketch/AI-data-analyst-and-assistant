from pathlib import Path
import sys
import uuid

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from werkzeug.utils import secure_filename

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import Config
from services.ai_service import (
    analyze_dataset_question,
    check_file_quality,
    generate_dataset_overview,
    generate_overview_table_data,
)
from services.chart_service import get_dashboard_data
from services.data_service import basic_summary, clean_data, load_data
from services.db_service import save_to_database
from services.state import clear_current_data, set_current_data
from utils.validator import allowed_file

FRONTEND_CSS = ROOT_DIR / "frontend" / "styles.css"
COLOR_PALETTE = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
    "#F7DC6F", "#BB8FCE", "#85C1E2", "#F8B88B", "#ABEBC6",
    "#F1948A", "#52BE80", "#D7BCCB",
]
CHART_STYLE_PALETTES = {
    "Dashboard": COLOR_PALETTE,
    "Warm": ["#d6a56f", "#d1866f", "#b27847", "#f8b88b", "#c15f4f"],
    "Cool": ["#38BDF8", "#4ECDC4", "#85C1E2", "#10B981", "#60A5FA"],
    "Finance": ["#10B981", "#22C55E", "#FACC15", "#F97316", "#38BDF8"],
    "Muted": ["#8aa57d", "#b78a6f", "#a59c93", "#7e9a78", "#ba8f6c"],
}


st.set_page_config(
    page_title="AI Data Analyst Assistant",
    page_icon="AI",
    layout="wide",
)


def init_session_defaults():
    defaults = {
        "theme": "dark",
        "dataset_loaded": False,
        "dataframe": None,
        "filename": "",
        "upload_key": 0,
        "last_answer": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def apply_theme():
    is_light = st.session_state.get("theme") == "light"
    colors = {
        "bg": "#f7f1ec" if is_light else "#100f12",
        "surface": "#ffffff" if is_light else "#17161a",
        "surface_soft": "#f2ebe5" if is_light else "#25222a",
        "text": "#1f1a16" if is_light else "#ece6e1",
        "muted": "#6a5d51" if is_light else "#a59c93",
        "accent": "#c18a5c" if is_light else "#d6a56f",
        "border": "rgba(47, 62, 70, 0.14)" if is_light else "rgba(206, 183, 150, 0.16)",
    }

    if FRONTEND_CSS.exists():
        st.markdown(f"<style>{FRONTEND_CSS.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <style>
          .stApp {{
            background: linear-gradient(135deg, {colors["bg"]}, {colors["surface_soft"]});
            color: {colors["text"]};
          }}
          [data-testid="stHeader"] {{
            background: transparent;
          }}
          [data-testid="stSidebar"] {{
            background: {colors["surface"]};
            border-right: 1px solid {colors["border"]};
          }}
          div[data-testid="stMetric"],
          div[data-testid="stDataFrame"],
          div[data-testid="stVerticalBlockBorderWrapper"] {{
            background: {colors["surface"]};
            border-color: {colors["border"]};
            border-radius: 8px;
          }}
          h1, h2, h3, label, p, span {{
            color: {colors["text"]};
          }}
          .stCaption, [data-testid="stMarkdownContainer"] small {{
            color: {colors["muted"]};
          }}
          .stButton > button {{
            border: 1px solid {colors["border"]};
            background: rgba(214, 165, 111, 0.16);
            color: {colors["text"]};
            border-radius: 8px;
            font-weight: 700;
          }}
          .stButton > button:hover {{
            border-color: {colors["accent"]};
            color: {colors["text"]};
          }}
          div[data-testid="stMetric"] {{
            border-left: 4px solid {colors["accent"]};
            padding: 1rem;
          }}
          div[data-testid="stMetricValue"] {{
            color: {colors["accent"]};
          }}
          .block-container {{
            padding-top: 1.5rem;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_plotly_template():
    return "plotly_white" if st.session_state.get("theme") == "light" else "plotly_dark"


def toggle_theme():
    st.session_state["theme"] = "light" if st.session_state.get("theme") == "dark" else "dark"


def clear_data():
    st.session_state["dataset_loaded"] = False
    st.session_state["dataframe"] = None
    st.session_state["filename"] = ""
    st.session_state["upload_key"] = st.session_state.get("upload_key", 0) + 1
    st.session_state["last_answer"] = ""
    clear_current_data()


def detect_currency_type(df):
    default = {"code": "USD", "symbol": "$"}
    if df is None or df.empty:
        return default

    symbol_to_code = {
        "$": "USD",
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
        "₹": "INR",
    }
    code_to_symbol = {code: symbol for symbol, code in symbol_to_code.items()}
    columns = [str(col).lower() for col in df.columns]

    for code, symbol in code_to_symbol.items():
        code_lower = code.lower()
        if any(code_lower in col for col in columns):
            return {"code": code, "symbol": symbol}

    keyword_map = {
        "dollar": ("USD", "$"),
        "usd": ("USD", "$"),
        "revenue": ("USD", "$"),
        "sales": ("USD", "$"),
        "euro": ("EUR", "€"),
        "pound": ("GBP", "£"),
        "yen": ("JPY", "¥"),
        "rupee": ("INR", "₹"),
        "inr": ("INR", "₹"),
    }
    for keyword, (code, symbol) in keyword_map.items():
        if any(keyword in col for col in columns):
            return {"code": code, "symbol": symbol}

    sample = df.head(25).astype(str)
    for value in sample.to_numpy().flatten():
        for symbol, code in symbol_to_code.items():
            if symbol in value:
                return {"code": code, "symbol": symbol}

    return default


def compact_currency(value, symbol="$"):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0

    sign = "-" if number < 0 else ""
    abs_value = abs(number)
    if abs_value >= 1_000_000_000_000:
        return f"{sign}{symbol}{abs_value / 1_000_000_000_000:.0f}T"
    if abs_value >= 1_000_000_000:
        return f"{sign}{symbol}{abs_value / 1_000_000_000:.0f}B"
    if abs_value >= 1_000_000:
        return f"{sign}{symbol}{abs_value / 1_000_000:.0f}M"
    if abs_value >= 1_000:
        return f"{sign}{symbol}{abs_value / 1_000:.0f}K"
    return f"{sign}{symbol}{abs_value:,.0f}"


def save_uploaded_file(uploaded_file):
    upload_folder = Path(Config.UPLOAD_FOLDER or "data/uploads")
    if not upload_folder.is_absolute():
        upload_folder = ROOT_DIR / upload_folder
    upload_folder.mkdir(parents=True, exist_ok=True)

    safe_name = secure_filename(uploaded_file.name)
    file_path = upload_folder / f"{uuid.uuid4().hex}_{safe_name}"
    file_path.write_bytes(uploaded_file.getbuffer())
    return file_path


def load_uploaded_dataset(uploaded_file):
    if not uploaded_file:
        return None, None

    if not allowed_file(uploaded_file.name):
        st.error("Only CSV and XLSX files are allowed.")
        return None, None

    file_path = save_uploaded_file(uploaded_file)
    df = clean_data(load_data(file_path))
    set_current_data(df)
    save_to_database(df)
    st.session_state["dataset_loaded"] = True
    st.session_state["dataframe"] = df
    st.session_state["filename"] = uploaded_file.name
    st.session_state["last_answer"] = ""
    return df, file_path


def get_active_dataframe():
    df = st.session_state.get("dataframe")
    if isinstance(df, pd.DataFrame) and not df.empty:
        set_current_data(df)
        return df
    return None


def render_kpis(kpis, df):
    currency = detect_currency_type(df)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows", f"{kpis.get('rows', 0):,}")
    col2.metric("Columns", f"{kpis.get('columns', 0):,}")
    col3.metric("Numeric Fields", f"{kpis.get('numeric_fields', 0):,}")
    col4.metric(f"Numeric Total ({currency['code']})", compact_currency(kpis.get("numeric_sum", 0), currency["symbol"]))


def render_overview_table():
    table_data = generate_overview_table_data()
    if table_data.get("error"):
        st.warning(table_data["error"])
        return

    overview_df = pd.DataFrame(table_data["rows"], columns=table_data["columns"])
    st.subheader(table_data.get("title", "Dataset Overview Table"))

    type_options = ["All"] + overview_df["Type"].drop_duplicates().tolist()
    type_filter, search_filter = st.columns([1, 2])
    selected_type = type_filter.selectbox("Show", type_options, index=0)
    search_text = search_filter.text_input("Search metrics", placeholder="Type a column or metric name")

    display_df = overview_df.copy()
    if selected_type != "All":
        display_df = display_df[display_df["Type"] == selected_type]
    if search_text.strip():
        search = search_text.strip().lower()
        display_df = display_df[
            display_df.apply(lambda row: row.astype(str).str.lower().str.contains(search, regex=False).any(), axis=1)
        ]

    if display_df.empty:
        st.info("No overview rows match the current filter.")
        return

    render_html_table(display_df, max_height=540)


def render_html_table(df, max_height=520):
    table_html = df.to_html(index=False, classes="preview-table", border=0, escape=True)
    st.markdown(
        f"""
        <div class="preview-table-wrapper" style="max-height: {max_height}px; overflow: auto;">
          {table_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_preview(df):
    st.subheader("Data Preview")
    st.caption(f"{len(df):,} rows x {len(df.columns):,} columns")

    option_col, row_col, seed_col = st.columns([1.2, 1, 1])
    preview_mode = option_col.selectbox("Preview", ["First rows", "Last rows", "Random sample"], index=0)
    max_rows = min(500, max(5, len(df)))
    default_rows = min(100, max_rows)
    row_count = row_col.slider("Rows", min_value=5, max_value=max_rows, value=default_rows, step=5)
    random_seed = seed_col.number_input("Sample seed", min_value=0, value=42, step=1, disabled=preview_mode != "Random sample")

    selected_columns = st.multiselect(
        "Columns",
        options=df.columns.tolist(),
        default=df.columns.tolist(),
        placeholder="Choose columns to display",
    )
    if not selected_columns:
        st.warning("Select at least one column to preview.")
        return

    if preview_mode == "Last rows":
        preview_df = df[selected_columns].tail(row_count)
    elif preview_mode == "Random sample":
        preview_df = df[selected_columns].sample(n=min(row_count, len(df)), random_state=int(random_seed))
    else:
        preview_df = df[selected_columns].head(row_count)

    render_html_table(preview_df, max_height=560)


def render_visualization(df):
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        st.info("Upload a dataset with numeric columns to generate a chart.")
        return

    columns = df.columns.tolist()
    text_cols = [col for col in columns if col not in numeric_cols]

    chart_col, style_col, x_col, y_col, limit_col = st.columns([1.1, 1, 1, 1, 0.8])
    chart_type = chart_col.selectbox(
        "Chart Type",
        [
            "Bar",
            "Horizontal Bar",
            "Line",
            "Area",
            "Scatter",
            "Pie",
            "Doughnut",
            "Polar Area",
            "Radar",
            "Waterfall",
            "Waffle",
            "Numeric Totals",
        ],
        index=0,
    )
    chart_style = style_col.selectbox("Chart Style", list(CHART_STYLE_PALETTES.keys()), index=0)
    x_axis = x_col.selectbox("X Axis", text_cols or columns, index=0)
    y_axis = y_col.selectbox("Y Axis", numeric_cols, index=0)
    row_limit = limit_col.slider("Top Rows", min_value=5, max_value=50, value=20, step=5)

    chart_df = df[[x_axis, y_axis]].copy()
    chart_df[y_axis] = pd.to_numeric(chart_df[y_axis], errors="coerce").fillna(0)
    chart_df = (
        chart_df.groupby(x_axis, dropna=False)[y_axis]
        .sum()
        .sort_values(ascending=False)
        .head(row_limit)
        .reset_index()
    )
    chart_df[x_axis] = chart_df[x_axis].astype(str)
    template = get_plotly_template()
    palette = CHART_STYLE_PALETTES[chart_style]
    currency = detect_currency_type(df)
    y_title = f"{y_axis} ({currency['code']})"

    if chart_type == "Numeric Totals":
        totals = df[numeric_cols].sum(numeric_only=True).sort_values(ascending=False).head(row_limit).reset_index()
        totals.columns = ["Metric", "Value"]
        fig = px.bar(totals, x="Metric", y="Value", color="Metric", color_discrete_sequence=palette, template=template)
        fig.update_yaxes(title=f"Total ({currency['code']})", tickprefix=currency["symbol"])
        fig.update_traces(hovertemplate="%{x}<br>Total: " + currency["symbol"] + "%{y:,.0f}<extra></extra>")
        fig.update_layout(height=520, margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        return

    if chart_type == "Line":
        fig = px.line(chart_df, x=x_axis, y=y_axis, markers=True, color_discrete_sequence=palette, template=template)
    elif chart_type == "Area":
        fig = px.area(chart_df, x=x_axis, y=y_axis, color_discrete_sequence=palette, template=template)
    elif chart_type == "Scatter":
        fig = px.scatter(chart_df, x=x_axis, y=y_axis, size=y_axis, color=x_axis, color_discrete_sequence=palette, template=template)
    elif chart_type == "Pie":
        fig = px.pie(chart_df, names=x_axis, values=y_axis, color_discrete_sequence=palette, template=template)
    elif chart_type == "Doughnut":
        fig = px.pie(chart_df, names=x_axis, values=y_axis, hole=0.45, color_discrete_sequence=palette, template=template)
    elif chart_type == "Polar Area":
        fig = px.bar_polar(chart_df, r=y_axis, theta=x_axis, color=x_axis, color_discrete_sequence=palette, template=template)
    elif chart_type == "Radar":
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=chart_df[y_axis], theta=chart_df[x_axis], fill="toself", name=y_axis, line_color=palette[0]))
        fig.update_layout(template=template, polar=dict(radialaxis=dict(visible=True)))
    elif chart_type == "Waterfall":
        running = chart_df[y_axis].tolist()
        fig = go.Figure(go.Waterfall(
            x=chart_df[x_axis],
            y=running,
            measure=["relative"] * len(running),
            increasing={"marker": {"color": "#10B981"}},
            decreasing={"marker": {"color": "#F97316"}},
            totals={"marker": {"color": "#38BDF8"}},
        ))
        fig.update_layout(template=template)
    elif chart_type == "Waffle":
        waffle = chart_df.copy()
        total = waffle[y_axis].sum()
        waffle["share"] = (waffle[y_axis] / total * 100).round(1) if total else 0
        fig = px.treemap(waffle, path=[x_axis], values=y_axis, color="share", color_continuous_scale="Viridis", template=template)
    elif chart_type == "Horizontal Bar":
        fig = px.bar(chart_df, x=y_axis, y=x_axis, color=x_axis, orientation="h", color_discrete_sequence=palette, template=template)
        fig.update_xaxes(title=y_title, tickprefix=currency["symbol"])
    else:
        fig = px.bar(chart_df, x=x_axis, y=y_axis, color=x_axis, color_discrete_sequence=palette, template=template)

    if chart_type not in ["Pie", "Doughnut", "Polar Area", "Radar", "Waffle", "Horizontal Bar"]:
        fig.update_yaxes(title=y_title, tickprefix=currency["symbol"])
        fig.update_traces(hovertemplate="%{x}<br>" + y_title + ": " + currency["symbol"] + "%{y:,.0f}<extra></extra>")
    elif chart_type == "Horizontal Bar":
        fig.update_traces(hovertemplate="%{y}<br>" + y_title + ": " + currency["symbol"] + "%{x:,.0f}<extra></extra>")
    elif chart_type in ["Pie", "Doughnut", "Polar Area"]:
        fig.update_traces(hovertemplate="%{label}<br>" + y_title + ": " + currency["symbol"] + "%{value:,.0f}<extra></extra>")
    fig.update_layout(height=520, margin=dict(l=10, r=10, t=40, b=10), showlegend=chart_type in ["Pie", "Doughnut", "Polar Area"])
    st.plotly_chart(fig, use_container_width=True)


def main():
    init_session_defaults()
    apply_theme()

    st.title("AI Data Analyst Assistant")
    st.caption("Upload a CSV or XLSX file, review KPIs, generate overview tables, and ask basic data questions.")

    action_col1, action_col2, action_col3 = st.columns([1, 1, 4])
    if action_col1.button("Refresh"):
        st.rerun()
    if action_col2.button("Clear All"):
        clear_data()
        st.rerun()
    theme_label = "Light Mode" if st.session_state.get("theme") == "dark" else "Dark Mode"
    if action_col3.button(theme_label):
        toggle_theme()
        st.rerun()

    uploaded_file = st.file_uploader("Upload CSV or XLSX data", type=["csv", "xlsx"], key=f"upload_{st.session_state['upload_key']}")
    if uploaded_file and uploaded_file.name != st.session_state.get("filename"):
        df, _ = load_uploaded_dataset(uploaded_file)
        if df is not None:
            summary = basic_summary(df)
            st.success(
                f"Uploaded {uploaded_file.name}: {summary['rows']:,} rows and {len(summary['columns']):,} columns."
            )

    df = get_active_dataframe()
    if df is None:
        st.info("Upload a dataset to start analysis.")
        return

    dashboard_data = get_dashboard_data()
    render_kpis(dashboard_data.get("kpis", {}), df)

    tabs = st.tabs(["Overview", "Overview Table", "Visualization", "Ask", "Data Quality", "Preview"])

    with tabs[0]:
        st.subheader("Dataset Overview")
        st.write(generate_dataset_overview())

    with tabs[1]:
        render_overview_table()

    with tabs[2]:
        render_visualization(df)

    with tabs[3]:
        st.subheader("Ask Your Data")
        question = st.text_input(
            "Question",
            placeholder="Example: What are the top 5 regions by total sales?",
        )
        if st.button("Analyze Question", type="primary") and question.strip():
            st.session_state["last_answer"] = analyze_dataset_question(question.strip())
        if st.session_state.get("last_answer"):
            st.markdown(st.session_state["last_answer"])

    with tabs[4]:
        if st.button("Check Data Quality"):
            st.write(check_file_quality())

    with tabs[5]:
        render_preview(df)


if __name__ == "__main__":
    main()
