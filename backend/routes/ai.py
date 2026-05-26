from flask import Blueprint, request, jsonify
from services.ai_service import analyze_dataset_question, check_file_quality, generate_analysis_chart_data, generate_dataset_overview, generate_overview_table_data
from services.llm_service import generate_dataset_insights, generate_sql_answer, send_prompt

ai_bp = Blueprint("ai_bp", __name__)

@ai_bp.route("/analyze", methods=["POST"])
def analyze():
    """Generate an overview, or answer a question when one is supplied."""
    data = request.get_json() or {}
    question = data.get("question", "").strip()

    if not question:
        answer = generate_dataset_overview()
        return jsonify({
            "analysis": answer,
            "mode": "overview"
        }), 200

    answer = analyze_dataset_question(question)
    return jsonify({
        "question": question,
        "analysis": answer
    }), 200

@ai_bp.route("/analyze-chart", methods=["GET", "POST"])
def analyze_chart():
    result = generate_analysis_chart_data()
    if result.get("error"):
        return jsonify(result), 400

    return jsonify(result), 200

@ai_bp.route("/analyze-table", methods=["GET", "POST"])
def analyze_table():
    result = generate_overview_table_data()
    if result.get("error"):
        return jsonify(result), 400

    return jsonify(result), 200

@ai_bp.route("/check-file", methods=["POST"])
def check_file():
    data = request.get_json() or {}
    question = data.get("question", "").strip()

    result = check_file_quality(question)
    if result.startswith("AI error:"):
        return jsonify({"error": result}), 500

    return jsonify({"quality_check": result}), 200


@ai_bp.route("/llm/prompt", methods=["POST"])
def llm_prompt():
    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    include_data_context = data.get("include_data_context", True)

    result = send_prompt(prompt, include_data_context=include_data_context)
    if result.get("error"):
        return jsonify(result), 400

    return jsonify({"prompt": prompt, **result}), 200


@ai_bp.route("/llm/sql", methods=["POST"])
def llm_sql():
    data = request.get_json() or {}
    question = data.get("question", "").strip()
    execute = data.get("execute", True)

    if not question:
        return jsonify({"error": "Question is required"}), 400

    result = generate_sql_answer(question, execute=execute)
    if result.get("error"):
        return jsonify(result), 400

    return jsonify(result), 200


@ai_bp.route("/llm/insights", methods=["POST", "GET"])
def llm_insights():
    result = generate_dataset_insights()
    if result.get("error"):
        return jsonify(result), 400

    return jsonify(result), 200
