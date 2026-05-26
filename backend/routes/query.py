from flask import Blueprint, request, jsonify
from services.sql_service import generate_sql, summarize_result
from services.db_service import fetch_query
from services.state import get_current_data

query_bp = Blueprint("query_bp", __name__)

@query_bp.route("/query", methods=["POST"])
def query_data():
    data = request.get_json() or {}
    question = data.get("question", "")

    if not question:
        return jsonify({"error": "Question is required"}), 400

    df = get_current_data()
    if df is None or df.empty:
        return jsonify({"error": "No dataset loaded. Please upload a CSV or XLSX file first."}), 400

    sql = generate_sql(question)

    try:
        result = fetch_query(sql)
    except Exception as e:
        result = []
        sql = f"{sql} -- execution failed: {str(e)}"

    analysis = summarize_result(question, sql, result)

    return jsonify({
        "question": question,
        "sql": sql,
        "analysis": analysis or "",
        "result": result
    }), 200