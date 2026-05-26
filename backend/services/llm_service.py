import re
import pandas as pd
from services.db_service import TABLE_NAME, engine, fetch_query
from services.state import get_current_data


def is_llm_configured():
    return True


def get_dataset_df():
    df = get_current_data()
    if df is not None and not df.empty:
        return df

    try:
        return pd.read_sql_query(f"SELECT * FROM {TABLE_NAME}", engine)
    except Exception:
        return None


def build_dataset_context(max_rows=12):
    df = get_dataset_df()
    if df is None or df.empty:
        return "No dataset is loaded."

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    context = {
        "table_name": TABLE_NAME,
        "rows": int(len(df)),
        "columns": df.columns.tolist(),
        "numeric_columns": numeric_cols,
        "sample_rows": df.head(max_rows).fillna("").to_dict(orient="records"),
        "missing_values": df.isnull().sum().to_dict(),
    }
    if numeric_cols:
        context["numeric_summary"] = df[numeric_cols].describe().fillna("").round(3).to_dict()
    return context


def normalize_name(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def singularize(token):
    token = token.lower()
    if len(token) > 3 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def tokenize(value):
    raw = re.findall(r"[a-z0-9]+", str(value).lower())
    return {singularize(token) for token in raw if token}


NUMERIC_ALIASES = {
    "revenue": {"revenue", "sales", "sale", "totalrevenue", "totalsales", "amount", "income"},
    "sales": {"sales", "sale", "revenue", "amount"},
    "profit": {"profit", "margin", "netprofit"},
    "cost": {"cost", "expense", "expenses"},
    "quantity": {"quantity", "qty", "unit", "units", "unitssold", "orderqty"},
    "price": {"price", "unitprice", "rate"},
    "discount": {"discount"},
}

CATEGORY_ALIASES = {
    "product": {"product", "products", "productname", "item", "itemtype", "sku"},
    "category": {"category", "categories", "subcategory", "sub_category", "segment", "itemtype"},
    "region": {"region", "territory", "market"},
    "country": {"country", "nation"},
    "state": {"state", "province"},
    "city": {"city", "town"},
    "customer": {"customer", "customername", "client"},
    "date": {"date", "orderdate", "shipdate", "month", "year"},
    "channel": {"channel", "saleschannel"},
}


def column_score(col, question_tokens, alias_groups=None):
    col_tokens = tokenize(col)
    normalized_col = normalize_name(col)
    score = 0

    if normalized_col in {normalize_name(token) for token in question_tokens}:
        score += 8
    score += 5 * len(col_tokens & question_tokens)

    for concept, aliases in (alias_groups or {}).items():
        normalized_aliases = {normalize_name(alias) for alias in aliases}
        alias_tokens = {singularize(alias) for alias in aliases}
        col_matches_alias = normalized_col in normalized_aliases or bool(col_tokens & alias_tokens)
        question_mentions_alias = bool(question_tokens & alias_tokens)
        if col_matches_alias and question_mentions_alias:
            score += 10

    return score


def find_column(df, question, numeric=None):
    numeric_cols = set(df.select_dtypes(include="number").columns.tolist())
    question_tokens = tokenize(question)
    alias_groups = NUMERIC_ALIASES if numeric is True else CATEGORY_ALIASES if numeric is False else {}
    candidates = []

    for col in df.columns:
        if numeric is True and col not in numeric_cols:
            continue
        if numeric is False and col in numeric_cols:
            continue
        candidates.append((column_score(col, question_tokens, alias_groups), col))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    if candidates[0][0] > 0:
        return candidates[0][1]

    if numeric is True:
        for preferred in ["revenue", "sales", "profit", "amount", "cost", "quantity", "price"]:
            for col in df.columns:
                if col in numeric_cols and preferred in normalize_name(col):
                    return col
    return None


def find_category_column(df, question):
    explicit_match = re.search(r"\b(?:by|per|for each|group(?:ed)? by)\s+([a-zA-Z0-9_ -]+)", question, flags=re.IGNORECASE)
    if explicit_match:
        explicit_text = explicit_match.group(1).strip()
        explicit_col = find_column(df, explicit_text, numeric=False)
        if explicit_col:
            return explicit_col

    col = find_column(df, question, numeric=False)
    if col:
        return col

    text_cols = [col for col in df.columns if col not in df.select_dtypes(include="number").columns]
    return text_cols[0] if text_cols else None


def parse_limit(question, default=10):
    q = question.lower()
    match = re.search(r"\b(?:top|bottom|first|last)\s+(\d{1,3})\b", q)
    if match:
        return max(1, min(int(match.group(1)), 100))
    if any(word in q for word in ["highest", "lowest", "largest", "smallest", "maximum", "minimum", "best", "worst"]):
        return 1
    return default


def sql_literal(value):
    return str(value).replace("'", "''")


def find_text_filter(df, question, excluded_col=None):
    q = question.lower()
    text_cols = [col for col in df.columns if col not in df.select_dtypes(include="number").columns]
    best = None
    for col in text_cols:
        if col == excluded_col:
            continue
        unique_values = df[col].dropna().astype(str).unique()[:500]
        for value in unique_values:
            value_text = value.strip()
            if len(value_text) < 3:
                continue
            if value_text.lower() in q:
                best = (col, value_text)
                break
        if best:
            break
    return best


def local_sql_for_question(question):
    df = get_dataset_df()
    if df is None or df.empty:
        return None

    q = question.lower()
    numeric_col = find_column(df, question, numeric=True)
    category_col = find_category_column(df, question)
    limit = parse_limit(question)
    grouping_intent = any(word in q for word in ["by", "per", "group", "top", "bottom", "highest", "lowest", "which"])
    text_filter = find_text_filter(df, question, excluded_col=category_col if grouping_intent else None)
    where_clause = ""
    if text_filter:
        where_clause = f" WHERE \"{text_filter[0]}\" = '{sql_literal(text_filter[1])}'"

    if "count" in q or "how many" in q or "number of rows" in q:
        return f"SELECT COUNT(*) AS row_count FROM {TABLE_NAME}{where_clause};"

    if numeric_col:
        safe_num = f'"{numeric_col}"'
        if any(word in q for word in ["average", "avg", "mean"]):
            return f"SELECT AVG({safe_num}) AS average_{normalize_name(numeric_col)} FROM {TABLE_NAME}{where_clause};"
        if "max" in q or "highest" in q or "largest" in q:
            if category_col and any(word in q for word in ["by", "top", "which"]):
                safe_cat = f'"{category_col}"'
                return (
                    f"SELECT {safe_cat}, SUM({safe_num}) AS total_{normalize_name(numeric_col)} "
                    f"FROM {TABLE_NAME}{where_clause} GROUP BY {safe_cat} "
                    f"ORDER BY total_{normalize_name(numeric_col)} DESC LIMIT {limit};"
                )
            return f"SELECT MAX({safe_num}) AS max_{normalize_name(numeric_col)} FROM {TABLE_NAME}{where_clause};"
        if "min" in q or "lowest" in q or "smallest" in q:
            if category_col and any(word in q for word in ["by", "bottom", "which"]):
                safe_cat = f'"{category_col}"'
                return (
                    f"SELECT {safe_cat}, SUM({safe_num}) AS total_{normalize_name(numeric_col)} "
                    f"FROM {TABLE_NAME}{where_clause} GROUP BY {safe_cat} "
                    f"ORDER BY total_{normalize_name(numeric_col)} ASC LIMIT {limit};"
                )
            return f"SELECT MIN({safe_num}) AS min_{normalize_name(numeric_col)} FROM {TABLE_NAME}{where_clause};"
        if "top" in q and category_col:
            safe_cat = f'"{category_col}"'
            return (
                f"SELECT {safe_cat}, SUM({safe_num}) AS total_{normalize_name(numeric_col)} "
                f"FROM {TABLE_NAME}{where_clause} GROUP BY {safe_cat} "
                f"ORDER BY total_{normalize_name(numeric_col)} DESC LIMIT {limit};"
            )
        if ("bottom" in q or "lowest" in q) and category_col:
            safe_cat = f'"{category_col}"'
            return (
                f"SELECT {safe_cat}, SUM({safe_num}) AS total_{normalize_name(numeric_col)} "
                f"FROM {TABLE_NAME}{where_clause} GROUP BY {safe_cat} "
                f"ORDER BY total_{normalize_name(numeric_col)} ASC LIMIT {limit};"
            )
        if any(word in q for word in ["sum", "total", "revenue", "sales", "profit", "amount"]):
            return f"SELECT SUM({safe_num}) AS total_{normalize_name(numeric_col)} FROM {TABLE_NAME}{where_clause};"

    return f"SELECT * FROM {TABLE_NAME}{where_clause} LIMIT {limit};"


def rows_to_sentence(question, rows):
    if not rows:
        return "I ran the query, but it did not return any rows."

    if len(rows) == 1:
        row = rows[0]
        parts = [f"{key}: {value}" for key, value in row.items()]
        return f"For your question, the result is {', '.join(parts)}."

    preview = rows[:5]
    formatted = []
    for row in preview:
        formatted.append(", ".join(f"{key}: {value}" for key, value in row.items()))
    return f"I found {len(rows)} matching rows. Top results: " + " | ".join(formatted)


def generate_local_response(prompt):
    df = get_dataset_df()
    if df is None or df.empty:
        return {
            "response": "Upload a dataset first, then I can answer questions, generate SQL, and produce insights for free using local analysis.",
            "model": "free-local-data-assistant",
        }

    q = prompt.lower()
    if "insight" in q or "summarize" in q or "summary" in q:
        return generate_dataset_insights()

    sql = local_sql_for_question(prompt)
    try:
        rows = fetch_query(sql)
    except Exception:
        rows = []

    response = rows_to_sentence(prompt, rows)
    if "column" in q or "field" in q:
        response = f"The dataset has {len(df.columns)} columns: {', '.join(df.columns)}."
    elif "row" in q and ("how many" in q or "count" in q):
        response = f"The dataset contains {len(df)} rows."

    return {
        "response": response,
        "sql": sql,
        "result": rows,
        "model": "free-local-data-assistant",
    }


def send_prompt(prompt, system_prompt=None, include_data_context=True, temperature=0.4, max_tokens=900):
    if not prompt or not prompt.strip():
        return {"error": "Prompt is required."}
    return generate_local_response(prompt)


def sanitize_select_sql(sql_text):
    if not sql_text or not isinstance(sql_text, str):
        return None

    sql = sql_text.strip()
    sql = re.sub(r"^```(?:sql)?", "", sql, flags=re.IGNORECASE).strip()
    sql = re.sub(r"```$", "", sql).strip()

    match = re.search(r"select\b", sql, flags=re.IGNORECASE)
    if match:
        sql = sql[match.start():].strip()

    sql = sql.split(";")[0].strip() + ";"
    if not sql.lower().startswith("select"):
        return None
    blocked = [" insert ", " update ", " delete ", " drop ", " alter ", " create ", " pragma ", " attach "]
    padded = f" {sql.lower()} "
    if any(token in padded for token in blocked):
        return None
    return sql


def generate_sql_with_llm(question):
    df = get_dataset_df()
    if df is None or df.empty:
        return {"error": "No dataset loaded. Please upload a CSV or XLSX file first."}

    sql = local_sql_for_question(question)
    if not sql:
        return {"error": "No dataset loaded. Please upload a CSV or XLSX file first."}
    return {"sql": sql, "model": "free-local-data-assistant"}


def generate_sql_answer(question, execute=True):
    sql_result = generate_sql_with_llm(question)
    if sql_result.get("error"):
        return sql_result

    response = {"question": question, "sql": sql_result["sql"], "model": sql_result.get("model")}
    if not execute:
        return response

    try:
        rows = fetch_query(sql_result["sql"])
    except Exception as exc:
        response["error"] = f"SQL execution failed: {exc}"
        return response

    response["result"] = rows
    if sql_result.get("model") == "free-local-data-assistant":
        response["insight"] = rows_to_sentence(question, rows)
        return response

    insight_prompt = (
        f"Question: {question}\n"
        f"SQL: {sql_result['sql']}\n"
        f"Result rows: {rows[:20]}\n\n"
        "Summarize the answer in plain language in 1-3 short sentences."
    )
    insight = send_prompt(insight_prompt, include_data_context=False, temperature=0.3, max_tokens=350)
    response["insight"] = insight.get("response") or f"Query returned {len(rows)} row(s)."
    return response


def generate_dataset_insights():
    df = get_dataset_df()
    if df is None or df.empty:
        return {"error": "No dataset loaded. Please upload a CSV or XLSX file first."}

    rows = len(df)
    columns = df.columns.tolist()
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = [col for col in columns if col not in numeric_cols]
    insights = [
        f"The dataset contains {rows} rows and {len(columns)} columns.",
        f"Available columns include: {', '.join(columns[:10])}.",
    ]

    missing = df.isnull().sum()
    missing = missing[missing > 0].to_dict()
    insights.append(
        f"Missing values were found in: {missing}." if missing else "No missing values were detected."
    )

    if numeric_cols:
        totals = df[numeric_cols].sum(numeric_only=True).sort_values(ascending=False)
        top_num = totals.index[0]
        insights.append(f"'{top_num}' has the largest numeric total at {totals.iloc[0]:,.2f}.")
        variable = df[numeric_cols].std(numeric_only=True).sort_values(ascending=False)
        if not variable.empty:
            insights.append(f"'{variable.index[0]}' varies the most across rows, so it may be useful for deeper analysis.")

    if text_cols and numeric_cols:
        cat = text_cols[0]
        num = numeric_cols[0]
        grouped = df.groupby(cat)[num].sum().sort_values(ascending=False).head(3)
        if not grouped.empty:
            leaders = ", ".join(f"{idx}: {val:,.2f}" for idx, val in grouped.items())
            insights.append(f"Top {cat} values by {num}: {leaders}.")

    response = "\n".join(f"{idx + 1}. {text}" for idx, text in enumerate(insights[:5]))
    return {"response": response, "model": "free-local-data-assistant"}
