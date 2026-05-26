from services.db_service import TABLE_NAME, engine
from services.state import get_current_data
import pandas as pd

# Load spaCy model once
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None
def answer_with_spacy(question, df):
    """
    Use spaCy to answer simple questions about the dataset columns or general info.
    """
    if nlp is None:
        return None
    doc = nlp(question.lower())
    # Example: "how many rows?", "list columns", "what columns exist?"
    if "column" in question.lower() or "feature" in question.lower():
        return f"Columns: {', '.join(df.columns)}"
    if "row" in question.lower() and ("how many" in question.lower() or "count" in question.lower()):
        return f"The dataset contains {len(df)} rows."
    if "unique" in question.lower():
        for col in df.columns:
            if col.lower() in question.lower():
                unique_vals = df[col].nunique()
                return f"Column '{col}' has {unique_vals} unique values."
    return None

def analyze_dataset_question(question):
    df = get_current_data()
    if df is None or df.empty:
        return "No dataset loaded. Please upload a file first."

    q = question.lower()
    if "column" in q or "feature" in q or "field" in q:
        return f"The dataset has {len(df.columns)} columns: {', '.join(df.columns)}."
    if "row" in q and ("how many" in q or "count" in q or "number" in q):
        return f"The dataset contains {len(df)} rows."
    if "unique" in q or "distinct" in q:
        for col in df.columns:
            if col.lower() in q:
                unique_vals = df[col].nunique()
                return f"The column '{col}' has {unique_vals} unique values."

    # Try spaCy for simple Q&A
    spacy_answer = answer_with_spacy(question, df)
    if spacy_answer:
        return spacy_answer

    # Try pandas for simple aggregations
    # Example: "average sales", "sum of profit", "max revenue"
    agg_map = {"average": "mean", "mean": "mean", "sum": "sum", "total": "sum", "max": "max", "min": "min"}
    for word, func in agg_map.items():
        if word in q:
            for col in df.columns:
                if col.lower() in q and pd.api.types.is_numeric_dtype(df[col]):
                    val = getattr(df[col], func)()
                    return f"The {word} of '{col}' is {val:.2f}."

    return (
        "No answer could be generated for your question. Try rephrasing or ask about columns, row counts, or simple aggregations."
    )

def get_analysis_dataframe():
    df = get_current_data()
    if df is not None and not df.empty:
        return df

    try:
        return pd.read_sql_query(f"SELECT * FROM {TABLE_NAME}", engine)
    except Exception:
        return None

def generate_dataset_overview():
    df = get_analysis_dataframe()
    if df is None or df.empty:
        return "No dataset loaded. Please upload a CSV or XLSX file first."

    rows = len(df)
    columns = df.columns.tolist()
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = [col for col in columns if col not in numeric_cols]

    lines = [
        f"Dataset overview: {rows:,} rows and {len(columns):,} columns were loaded.",
        f"Columns: {', '.join(columns[:12])}{'...' if len(columns) > 12 else ''}.",
    ]

    if numeric_cols:
        totals = df[numeric_cols].sum(numeric_only=True).sort_values(ascending=False)
        top_total_col = totals.index[0]
        lines.append(f"The largest numeric total is in '{top_total_col}' with {totals.iloc[0]:,.2f}.")

        means = df[numeric_cols].mean(numeric_only=True).sort_values(ascending=False)
        top_mean_col = means.index[0]
        lines.append(f"The highest numeric average is '{top_mean_col}' at {means.iloc[0]:,.2f}.")

    if text_cols:
        cat = text_cols[0]
        top_values = df[cat].astype(str).value_counts().head(3)
        if not top_values.empty:
            formatted = ", ".join(f"{idx} ({count})" for idx, count in top_values.items())
            lines.append(f"Most common values in '{cat}': {formatted}.")

    missing = df.isnull().sum()
    missing = missing[missing > 0].to_dict()
    lines.append(
        f"Missing values were found in: {missing}."
        if missing
        else "No missing values were detected after cleaning."
    )

    duplicate_count = int(df.duplicated().sum())
    lines.append(
        f"{duplicate_count:,} duplicate row(s) remain in the dataset."
        if duplicate_count
        else "No duplicate rows were found."
    )

    return "\n".join(lines)

def format_overview_value(value):
    if pd.isna(value):
        return ""
    if isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return str(value)

def generate_overview_table_data():
    df = get_analysis_dataframe()
    if df is None or df.empty:
        return {"error": "No dataset loaded. Please upload a CSV or XLSX file first."}

    rows = []
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = [col for col in df.columns if col not in numeric_cols]
    missing_cells = int(df.isnull().sum().sum())
    duplicate_count = int(df.duplicated().sum())

    rows.extend([
        {
            "Metric": "Rows",
            "Type": "Dataset",
            "Value": f"{len(df):,}",
            "Details": "Total records loaded",
        },
        {
            "Metric": "Columns",
            "Type": "Dataset",
            "Value": f"{len(df.columns):,}",
            "Details": "Fields available for analysis",
        },
        {
            "Metric": "Numeric fields",
            "Type": "Dataset",
            "Value": f"{len(numeric_cols):,}",
            "Details": ", ".join(numeric_cols[:8]) or "None",
        },
        {
            "Metric": "Text/date fields",
            "Type": "Dataset",
            "Value": f"{len(text_cols):,}",
            "Details": ", ".join(text_cols[:8]) or "None",
        },
        {
            "Metric": "Missing cells",
            "Type": "Quality",
            "Value": f"{missing_cells:,}",
            "Details": "Blank or null values detected",
        },
        {
            "Metric": "Duplicate rows",
            "Type": "Quality",
            "Value": f"{duplicate_count:,}",
            "Details": "Repeated complete rows",
        },
    ])

    for col in numeric_cols[:10]:
        series = df[col]
        rows.append({
            "Metric": col,
            "Type": "Numeric column",
            "Value": f"Total {series.sum():,.2f}",
            "Details": f"Average {series.mean():,.2f}; min {series.min():,.2f}; max {series.max():,.2f}; missing {int(series.isnull().sum()):,}",
        })

    for col in text_cols[:10]:
        series = df[col].astype(str)
        top_values = series.value_counts(dropna=False)
        top_label = top_values.index[0] if not top_values.empty else ""
        top_count = int(top_values.iloc[0]) if not top_values.empty else 0
        rows.append({
            "Metric": col,
            "Type": "Category column",
            "Value": f"{df[col].nunique(dropna=True):,} unique",
            "Details": f"Top value: {format_overview_value(top_label)} ({top_count:,}); missing {int(df[col].isnull().sum()):,}",
        })

    return {
        "title": "Dataset Overview Table",
        "columns": ["Metric", "Type", "Value", "Details"],
        "rows": rows,
    }

def generate_analysis_chart_data():
    df = get_analysis_dataframe()
    if df is None or df.empty:
        return {"error": "No dataset loaded. Please upload a CSV or XLSX file first."}

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = [col for col in df.columns if col not in numeric_cols]

    if text_cols and numeric_cols:
        category_col = text_cols[0]
        value_col = numeric_cols[0]
        grouped = (
            df.groupby(category_col)[value_col]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )
        return {
            "title": f"Top {category_col} by {value_col}",
            "chart_type": "bar",
            "labels": [str(label) for label in grouped.index.tolist()],
            "values": [float(value) for value in grouped.values.tolist()],
            "x_column": category_col,
            "y_column": value_col,
        }

    if numeric_cols:
        totals = df[numeric_cols].sum(numeric_only=True).sort_values(ascending=False).head(10)
        return {
            "title": "Numeric column totals",
            "chart_type": "bar",
            "labels": [str(label) for label in totals.index.tolist()],
            "values": [float(value) for value in totals.values.tolist()],
            "x_column": "numeric_columns",
            "y_column": "total",
        }

    category_col = df.columns[0]
    counts = df[category_col].astype(str).value_counts().head(10)
    return {
        "title": f"Top values in {category_col}",
        "chart_type": "bar",
        "labels": [str(label) for label in counts.index.tolist()],
        "values": [int(value) for value in counts.values.tolist()],
        "x_column": category_col,
        "y_column": "count",
    }

def generate_insights():
    df = get_current_data()

    if df is None or df.empty:
        return ["No dataset available. Please upload a file first."]

    insights = []

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        top_col = numeric_cols[0]
        insights.append(f"The column '{top_col}' has strong numerical activity.")

    if "region" in df.columns and "sales" in df.columns:
        region_sales = df.groupby("region")["sales"].sum()
        top_region = region_sales.idxmax()
        low_region = region_sales.idxmin()
        insights.append(f"{top_region} has the highest sales performance.")
        insights.append(f"{low_region} has the lowest sales performance.")

    if "profit" in df.columns:
        profit_sum = df["profit"].sum()
        insights.append(f"Total profit across the dataset is {profit_sum:.2f}.")

    if not insights:
        insights.append("Dataset loaded successfully, but no clear pattern was detected.")

    return insights[:5]


def check_file_quality(question=None):
    df = get_current_data()
    if df is None or df.empty:
        return "No dataset loaded. Please upload a file first."

    missing_counts = df.isnull().sum()
    missing_cols = missing_counts[missing_counts > 0].to_dict()
    if missing_cols:
        missing_summary = f"Missing values detected in columns: {missing_cols}."
    else:
        missing_summary = "No missing values detected."

    duplicate_count = int(df.duplicated().sum())
    duplicate_summary = (
        f"Found {duplicate_count} duplicate row(s)." if duplicate_count else "No duplicate rows found."
    )

    normalized_headers = [c.strip().lower().replace(" ", "_") for c in df.columns]
    header_mismatches = [c for c, norm in zip(df.columns, normalized_headers) if c != norm]
    header_summary = (
        f"Header inconsistencies detected: {header_mismatches}."
        if header_mismatches
        else "Column headers appear consistent and normalized."
    )

    return " ".join([missing_summary, duplicate_summary, header_summary])
