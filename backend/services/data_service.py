import pandas as pd

def load_data(file_path):
    if str(file_path).lower().endswith(".csv"):
        return pd.read_csv(file_path)
    return pd.read_excel(file_path)

def clean_data(df):
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.drop_duplicates()
    df = df.fillna(0)
    return df

def basic_summary(df):
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    return {
        "rows": int(len(df)),
        "columns": df.columns.tolist(),
        "numeric_columns": numeric_cols,
        "numeric_summary": df[numeric_cols].describe().to_dict() if numeric_cols else {}
    }