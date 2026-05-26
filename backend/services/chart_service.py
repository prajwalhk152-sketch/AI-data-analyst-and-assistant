
from services.state import get_current_data

def get_dashboard_data():
    df = get_current_data()

    if df is None or df.empty:
        return {
            "kpis": {"rows": 0, "columns": 0, "numeric_fields": 0, "numeric_sum": 0},
            "charts": {}
        }

    rows = int(len(df))
    columns = len(df.columns)
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    numeric_fields = len(numeric_cols)
    numeric_sum = float(df[numeric_cols].sum().sum()) if numeric_cols else 0

    kpis = {
        "rows": rows,
        "columns": columns,
        "numeric_fields": numeric_fields,
        "numeric_sum": numeric_sum
    }

    charts = {}

    # Waterfall chart logic: use first numeric column and a categorical column if available
    if len(numeric_cols) > 0 and len(df.columns) > 1:
        num_col = numeric_cols[0]
        cat_col = [c for c in df.columns if c != num_col][0]
        grouped = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False).head(20)
        x = grouped.index.tolist()
        y = grouped.values.tolist()
        charts["waterfall"] = {
            "title": f"Waterfall Chart: {num_col} by {cat_col}",
            "x": x,
            "y": y,
            "cat_col": cat_col,
            "num_col": num_col
        }

    return {"kpis": kpis, "charts": charts}
