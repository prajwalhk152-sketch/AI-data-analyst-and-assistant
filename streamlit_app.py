from pathlib import Path
import sys
import uuid

import pandas as pd
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
from services.state import set_current_data
from utils.validator import allowed_file


st.set_page_config(
    page_title="AI Data Analyst Assistant",
    page_icon="📊",
    layout="wide",
)


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
    return df, file_path


def get_active_dataframe():
    df = st.session_state.get("dataframe")
    if isinstance(df, pd.DataFrame) and not df.empty:
        set_current_data(df)
        return df
    return None


def render_kpis(kpis):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows", f"{kpis.get('rows', 0):,}")
    col2.metric("Columns", f"{kpis.get('columns', 0):,}")
    col3.metric("Numeric Fields", f"{kpis.get('numeric_fields', 0):,}")
    col4.metric("Numeric Total", f"{kpis.get('numeric_sum', 0):,.2f}")


def render_overview_table():
    table_data = generate_overview_table_data()
    if table_data.get("error"):
        st.warning(table_data["error"])
        return

    st.subheader(table_data.get("title", "Dataset Overview Table"))
    st.dataframe(pd.DataFrame(table_data["rows"], columns=table_data["columns"]), use_container_width=True)


def render_visualization(df):
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        st.info("Upload a dataset with numeric columns to generate a chart.")
        return

    columns = df.columns.tolist()
    text_cols = [col for col in columns if col not in numeric_cols]

    chart_col, x_col, y_col = st.columns(3)
    chart_type = chart_col.selectbox("Chart Type", ["Bar", "Line", "Area"], index=0)
    x_axis = x_col.selectbox("X Axis", text_cols or columns, index=0)
    y_axis = y_col.selectbox("Y Axis", numeric_cols, index=0)

    chart_df = df[[x_axis, y_axis]].copy()
    chart_df[y_axis] = pd.to_numeric(chart_df[y_axis], errors="coerce").fillna(0)
    chart_df = chart_df.groupby(x_axis, dropna=False)[y_axis].sum().sort_values(ascending=False).head(30)

    if chart_type == "Line":
        st.line_chart(chart_df)
    elif chart_type == "Area":
        st.area_chart(chart_df)
    else:
        st.bar_chart(chart_df)


def main():
    st.title("AI Data Analyst Assistant")
    st.caption("Upload a CSV or XLSX file, review KPIs, generate overview tables, and ask basic data questions.")

    uploaded_file = st.file_uploader("Upload CSV or XLSX data", type=["csv", "xlsx"])
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
    render_kpis(dashboard_data.get("kpis", {}))

    tabs = st.tabs(["Overview", "Overview Table", "Visualization", "Ask", "Data Quality", "Preview"])

    with tabs[0]:
        st.subheader("Dataset Overview")
        st.write(generate_dataset_overview())

    with tabs[1]:
        render_overview_table()

    with tabs[2]:
        render_visualization(df)

    with tabs[3]:
        question = st.text_input("Ask about rows, columns, unique values, or simple aggregations")
        if st.button("Analyze Question") and question.strip():
            st.write(analyze_dataset_question(question.strip()))

    with tabs[4]:
        if st.button("Check Data Quality"):
            st.write(check_file_quality())

    with tabs[5]:
        st.dataframe(df.head(100), use_container_width=True)


if __name__ == "__main__":
    main()
