from flask import Blueprint, jsonify
from services.ai_service import generate_insights

insights_bp = Blueprint("insights_bp", __name__)

@insights_bp.route("/insights", methods=["GET"])
def insights():
    return jsonify({"insights": generate_insights()}), 200