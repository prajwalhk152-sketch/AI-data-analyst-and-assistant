import re
from services.db_service import TABLE_NAME
from services.state import get_current_data


def detect_id_column(columns):
    normalized_columns = [col.lower() for col in columns]
    if "order_id" in normalized_columns:
        return columns[normalized_columns.index("order_id")]
    if "id" in normalized_columns:
        return columns[normalized_columns.index("id")]

    id_columns = [col for col in columns if col.lower().endswith("_id")]
    return id_columns[0] if id_columns else None


def generate_id_sql(question):
    normalized = question.lower()
    match = re.search(r"(?:order[_\s]?id|id)\s*(?:=|is|:)?\s*([0-9]+)", normalized)
    if not match:
        return None

    df = get_current_data()
    if df is None:
        return None

    id_column = detect_id_column(df.columns.tolist())
    if not id_column:
        return None

    order_id = match.group(1)
    return f"SELECT * FROM {TABLE_NAME} WHERE {id_column} = {order_id};"


def summarize_result(question, sql, result):
    if not result:
        return None

    row_count = len(result)
    if row_count == 1:
        return f"Found 1 matching row for: {question}"
    return f"Found {row_count} matching rows for: {question}"


def generate_sql(question):
    if not question or not isinstance(question, str):
        return f"SELECT * FROM {TABLE_NAME} LIMIT 10;"

    id_sql_result = generate_id_sql(question)
    if id_sql_result:
        return id_sql_result

    try:
        from services.llm_service import generate_sql_with_llm, is_llm_configured
        if is_llm_configured():
            llm_result = generate_sql_with_llm(question)
            if llm_result.get("sql"):
                return llm_result["sql"]
    except Exception:
        pass

    return f"SELECT * FROM {TABLE_NAME} LIMIT 10;"
